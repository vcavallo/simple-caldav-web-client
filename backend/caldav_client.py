"""CalDAV/iCalendar logic.

Split into two layers:

* Pure conversion helpers (``vevent_to_event``, ``expand_event``, ``build_ical``)
  that have no network dependency and are exhaustively unit-tested.
* ``CalDavClient`` which talks to a real CalDAV server via the ``caldav``
  library. It is dependency-injected into the API so tests can swap in a fake.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

import icalendar
from dateutil.rrule import rrulestr

from backend.config import Calendar, Config
from backend.models import EventCreate, EventUpdate


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class CalDavError(Exception):
    """Base class for CalDAV-related failures."""


class CalDavAuthError(CalDavError):
    """Credentials were rejected by the server."""


class CalDavUnreachable(CalDavError):
    """The CalDAV server could not be reached."""


class ETagConflict(CalDavError):
    """The event was modified elsewhere (HTTP 412)."""


class NotFoundError(CalDavError):
    """The requested event/calendar does not exist."""


# --------------------------------------------------------------------------- #
# Pure conversion helpers
# --------------------------------------------------------------------------- #
def _is_all_day(value) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _fmt(value) -> str:
    """Format a date/datetime as the ISO string used on the wire."""
    if _is_all_day(value):
        return value.isoformat()  # "2025-09-20"
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()  # "2025-09-15T14:00:00[+offset]"
    return str(value)


def _to_naive_datetime(value) -> datetime:
    if _is_all_day(value):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _event_duration(vevent) -> timedelta:
    dtstart = vevent.decoded("DTSTART")
    if "DTEND" in vevent:
        return vevent.decoded("DTEND") - dtstart
    if "DURATION" in vevent:
        return vevent.decoded("DURATION")
    return timedelta(days=1) if _is_all_day(dtstart) else timedelta(hours=1)


def vevent_to_event(vevent, calendar_id: str, etag: Optional[str] = None,
                    url: Optional[str] = None) -> dict:
    """Convert a single icalendar VEVENT component to our event dict."""
    dtstart = vevent.decoded("DTSTART")
    all_day = _is_all_day(dtstart)

    if "DTEND" in vevent:
        dtend = vevent.decoded("DTEND")
    else:
        dtend = dtstart + _event_duration(vevent)

    return {
        "id": str(vevent["UID"]),
        "calendar_id": calendar_id,
        "title": str(vevent.get("SUMMARY", "")),
        "start": _fmt(dtstart),
        "end": _fmt(dtend),
        "allDay": all_day,
        "location": str(vevent.get("LOCATION", "")),
        "description": str(vevent.get("DESCRIPTION", "")),
        "url": url or "",
        "etag": etag or "",
        "recurring": "RRULE" in vevent,
    }


def expand_event(vevent, calendar_id: str, range_start: datetime,
                 range_end: datetime, etag: Optional[str] = None,
                 url: Optional[str] = None) -> List[dict]:
    """Return one event dict per occurrence of ``vevent`` inside the range.

    Non-recurring events yield a single dict. Recurring events are expanded
    with synthetic ids of the form ``<uid>_<occurrence-date>``.
    """
    base = vevent_to_event(vevent, calendar_id, etag=etag, url=url)
    if "RRULE" not in vevent:
        return [base]

    dtstart = vevent.decoded("DTSTART")
    all_day = _is_all_day(dtstart)
    start_dt = _to_naive_datetime(dtstart)
    duration = _event_duration(vevent)

    rule_text = vevent["RRULE"].to_ical().decode()
    rule = rrulestr(rule_text, dtstart=start_dt)
    occurrences = rule.between(range_start, range_end, inc=True)

    result: List[dict] = []
    for occ in occurrences:
        end_dt = occ + duration
        if all_day:
            start_str = occ.date().isoformat()
            end_str = end_dt.date().isoformat()
        else:
            start_str = occ.replace(microsecond=0).isoformat()
            end_str = end_dt.replace(microsecond=0).isoformat()
        ev = dict(base)
        ev["id"] = f"{base['id']}_{occ.date().isoformat()}"
        ev["start"] = start_str
        ev["end"] = end_str
        ev["recurring"] = True
        result.append(ev)
    return result


def _parse_start_end(value: str, all_day: bool):
    if all_day:
        return date.fromisoformat(value[:10])
    return datetime.fromisoformat(value)


def build_ical(data: EventCreate, uid: str, dtstamp: Optional[datetime] = None) -> str:
    """Build a VCALENDAR/VEVENT iCalendar document for an event."""
    cal = icalendar.Calendar()
    cal.add("prodid", "-//caldav-web-client//EN")
    cal.add("version", "2.0")

    ev = icalendar.Event()
    ev.add("uid", uid)
    ev.add("summary", data.title)
    ev.add("dtstart", _parse_start_end(data.start, data.allDay))
    ev.add("dtend", _parse_start_end(data.end, data.allDay))
    if data.location:
        ev.add("location", data.location)
    if data.description:
        ev.add("description", data.description)
    if dtstamp is not None:
        ev.add("dtstamp", dtstamp)

    cal.add_component(ev)
    return cal.to_ical().decode()


# --------------------------------------------------------------------------- #
# Real network client
# --------------------------------------------------------------------------- #
class CalDavClient:
    """Talks to a real CalDAV server. Injected into the API layer."""

    def __init__(self, config: Config):
        self.config = config
        self._calendars: dict = {}  # calendar_id -> caldav.Calendar

    # -- connection management ------------------------------------------- #
    def _get_caldav_calendar(self, cal: Calendar):
        import caldav

        if cal.id not in self._calendars:
            dav = caldav.DAVClient(
                url=cal.url, username=cal.username, password=cal.password,
            )
            self._calendars[cal.id] = dav.calendar(url=cal.url)
        return self._calendars[cal.id]

    @staticmethod
    def _map_error(exc: Exception) -> CalDavError:
        import caldav.lib.error as dav_error

        if isinstance(exc, dav_error.AuthorizationError):
            return CalDavAuthError(str(exc))
        if isinstance(exc, dav_error.NotFoundError):
            return NotFoundError(str(exc))
        if isinstance(exc, dav_error.ConsistencyError):
            return ETagConflict(str(exc))
        # Connection-level problems from the underlying HTTP library.
        name = exc.__class__.__name__
        if "Connection" in name or "Timeout" in name:
            return CalDavUnreachable(str(exc))
        return CalDavError(str(exc))

    # -- read ------------------------------------------------------------- #
    def list_calendars(self) -> List[dict]:
        return [
            {"id": c.id, "name": c.name, "color": c.color}
            for c in self.config.calendars
        ]

    def _fetch_one(self, cal: Calendar, start: datetime, end: datetime) -> List[dict]:
        try:
            calendar = self._get_caldav_calendar(cal)
            found = calendar.search(start=start, end=end, event=True, expand=False)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._map_error(exc)

        events: List[dict] = []
        for obj in found:
            etag = getattr(obj, "etag", "") or ""
            url = str(getattr(obj, "url", "") or "")
            ical = icalendar.Calendar.from_ical(obj.data)
            for vevent in ical.walk("VEVENT"):
                events.extend(
                    expand_event(vevent, cal.id, start, end, etag=etag, url=url)
                )
        return events

    async def get_events(self, start: str, end: str,
                         calendar_ids: Optional[List[str]] = None) -> dict:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        targets = [
            c for c in self.config.calendars
            if not calendar_ids or c.id in calendar_ids
        ]
        # Fire one blocking search per calendar concurrently. A failing calendar
        # is reported separately rather than failing the whole request, so one
        # misconfigured/unreachable calendar never blanks the entire view.
        results = await asyncio.gather(
            *(asyncio.to_thread(self._fetch_one, cal, start_dt, end_dt)
              for cal in targets),
            return_exceptions=True,
        )
        events: List[dict] = []
        errors: List[dict] = []
        for cal, res in zip(targets, results):
            if isinstance(res, Exception):
                errors.append({"calendar_id": cal.id, "message": str(res)})
            else:
                events.extend(res)
        return {"events": events, "errors": errors}

    # -- write ------------------------------------------------------------ #
    def _create_sync(self, data: EventCreate) -> dict:
        cal = self.config.get(data.calendar_id)
        if cal is None:
            raise NotFoundError(f"Unknown calendar: {data.calendar_id}")
        uid = f"{uuid.uuid4()}@caldav-web-client"
        ical = build_ical(data, uid=uid, dtstamp=datetime.utcnow())
        try:
            calendar = self._get_caldav_calendar(cal)
            obj = calendar.save_event(ical)
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc)

        etag = getattr(obj, "etag", "") or ""
        url = str(getattr(obj, "url", "") or "")
        vevent = icalendar.Calendar.from_ical(obj.data).walk("VEVENT")[0]
        return vevent_to_event(vevent, cal.id, etag=etag, url=url)

    async def create_event(self, data: EventCreate) -> dict:
        return await asyncio.to_thread(self._create_sync, data)

    def _update_sync(self, event_id: str, data: EventUpdate) -> dict:
        cal = self.config.get(data.calendar_id) if data.calendar_id else None
        if cal is None:
            # Fall back to scanning configured calendars by url prefix.
            cal = self._calendar_for_url(data.url)
        if cal is None:
            raise NotFoundError(f"Unknown calendar for event {event_id}")

        create_shape = EventCreate(calendar_id=cal.id, **data.model_dump(
            include={"title", "start", "end", "allDay", "location", "description"}))
        ical = build_ical(create_shape, uid=event_id, dtstamp=datetime.utcnow())
        try:
            obj = self._put(data.url, ical, if_match=data.etag)
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc)
        etag = getattr(obj, "etag", "") or data.etag
        result = vevent_to_event(
            icalendar.Calendar.from_ical(ical).walk("VEVENT")[0],
            cal.id, etag=etag, url=data.url,
        )
        return result

    async def update_event(self, event_id: str, data: EventUpdate) -> dict:
        return await asyncio.to_thread(self._update_sync, event_id, data)

    def _delete_sync(self, event_id: str, url: str, etag: str) -> None:
        cal = self._calendar_for_url(url)
        if cal is None:
            raise NotFoundError(f"Unknown calendar for event {event_id}")
        try:
            self._delete(url, if_match=etag)
        except Exception as exc:  # noqa: BLE001
            raise self._map_error(exc)

    async def delete_event(self, event_id: str, url: str, etag: str) -> None:
        await asyncio.to_thread(self._delete_sync, event_id, url, etag)

    # -- low-level helpers ----------------------------------------------- #
    def _calendar_for_url(self, url: str) -> Optional[Calendar]:
        for cal in self.config.calendars:
            base = cal.url.split("/dav")[0] if "/dav" in cal.url else cal.url
            if url and (cal.id in url or base in url):
                return cal
        return self.config.calendars[0] if self.config.calendars else None

    def _dav_for_calendar(self, cal: Calendar):
        import caldav

        return caldav.DAVClient(
            url=cal.url, username=cal.username, password=cal.password,
        )

    def _put(self, url: str, ical: str, if_match: str):
        cal = self._calendar_for_url(url)
        dav = self._dav_for_calendar(cal)
        headers = {"Content-Type": "text/calendar; charset=utf-8"}
        if if_match:
            headers["If-Match"] = if_match
        resp = dav.put(url, ical, headers)
        self._raise_for_status(resp)
        return resp

    def _delete(self, url: str, if_match: str):
        cal = self._calendar_for_url(url)
        dav = self._dav_for_calendar(cal)
        headers = {}
        if if_match:
            headers["If-Match"] = if_match
        # DAVClient.delete() takes only a url; route through request() so the
        # If-Match header (ETag concurrency check) is actually sent.
        resp = dav.request(url, "DELETE", headers=headers)
        self._raise_for_status(resp)
        return resp

    @staticmethod
    def _raise_for_status(resp) -> None:
        status = getattr(resp, "status", 200)
        if status == 412:
            raise ETagConflict("Event was modified elsewhere")
        if status in (401, 403):
            raise CalDavAuthError("Authentication failed")
        if status == 404:
            raise NotFoundError("Event not found")
        if status >= 500:
            raise CalDavUnreachable(f"Server error {status}")
