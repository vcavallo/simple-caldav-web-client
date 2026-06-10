"""Tests for the pure iCalendar <-> event-dict conversion layer."""
from datetime import date, datetime

import icalendar
import pytest

from backend.caldav_client import (
    vevent_to_event,
    expand_event,
    build_ical,
)
from backend.models import EventCreate


def make_vevent(ics_body):
    cal = icalendar.Calendar.from_ical(
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n"
        + ics_body
        + "END:VCALENDAR\r\n"
    )
    for comp in cal.walk("VEVENT"):
        return comp
    raise AssertionError("no VEVENT found")


TIMED = """\
BEGIN:VEVENT
UID:abc123@baikal
SUMMARY:Dentist
DTSTART:20250915T140000
DTEND:20250915T150000
LOCATION:123 Main St
DESCRIPTION:6-month checkup
END:VEVENT
"""

ALLDAY = """\
BEGIN:VEVENT
UID:allday1@baikal
SUMMARY:Vacation
DTSTART;VALUE=DATE:20250920
DTEND;VALUE=DATE:20250921
END:VEVENT
"""

RECURRING = """\
BEGIN:VEVENT
UID:weekly1@baikal
SUMMARY:Standup
DTSTART:20250901T090000
DTEND:20250901T091500
RRULE:FREQ=WEEKLY;COUNT=4
END:VEVENT
"""


def test_timed_event_basic_fields():
    ev = vevent_to_event(make_vevent(TIMED), calendar_id="personal")
    assert ev["id"] == "abc123@baikal"
    assert ev["calendar_id"] == "personal"
    assert ev["title"] == "Dentist"
    assert ev["start"] == "2025-09-15T14:00:00"
    assert ev["end"] == "2025-09-15T15:00:00"
    assert ev["allDay"] is False
    assert ev["location"] == "123 Main St"
    assert ev["description"] == "6-month checkup"
    assert ev["recurring"] is False


def test_all_day_event_uses_date_values():
    ev = vevent_to_event(make_vevent(ALLDAY), calendar_id="personal")
    assert ev["allDay"] is True
    assert ev["title"] == "Vacation"
    # date-only, no time component
    assert ev["start"] == "2025-09-20"
    assert ev["end"] == "2025-09-21"


def test_missing_optional_fields_default_empty():
    ev = vevent_to_event(make_vevent("""\
BEGIN:VEVENT
UID:bare@baikal
SUMMARY:Bare
DTSTART:20250915T140000
DTEND:20250915T150000
END:VEVENT
"""), calendar_id="personal")
    assert ev["location"] == ""
    assert ev["description"] == ""


def test_etag_attached_when_provided():
    ev = vevent_to_event(make_vevent(TIMED), calendar_id="personal", etag='"xyz"', url="/dav/personal/abc123.ics")
    assert ev["etag"] == '"xyz"'
    assert ev["url"] == "/dav/personal/abc123.ics"


def test_recurring_event_detected():
    ev = vevent_to_event(make_vevent(RECURRING), calendar_id="personal")
    assert ev["recurring"] is True


def test_expand_event_produces_occurrences_in_range():
    vevent = make_vevent(RECURRING)
    occurrences = expand_event(
        vevent,
        calendar_id="personal",
        range_start=datetime(2025, 9, 1),
        range_end=datetime(2025, 9, 30),
    )
    # FREQ=WEEKLY;COUNT=4 starting 2025-09-01 -> Sep 1, 8, 15, 22
    assert len(occurrences) == 4
    starts = [o["start"] for o in occurrences]
    assert starts[0] == "2025-09-01T09:00:00"
    assert starts[1] == "2025-09-08T09:00:00"
    assert starts[3] == "2025-09-22T09:00:00"
    for o in occurrences:
        assert o["recurring"] is True
        # synthetic id: <uid>_<occurrence date>
        assert o["id"].startswith("weekly1@baikal_")


def test_expand_event_respects_range_bounds():
    vevent = make_vevent(RECURRING)
    occurrences = expand_event(
        vevent,
        calendar_id="personal",
        range_start=datetime(2025, 9, 10),
        range_end=datetime(2025, 9, 30),
    )
    # only Sep 15 and Sep 22 fall in [Sep 10, Sep 30]
    assert len(occurrences) == 2
    assert occurrences[0]["start"] == "2025-09-15T09:00:00"


def test_non_recurring_expand_returns_single_event():
    vevent = make_vevent(TIMED)
    occurrences = expand_event(
        vevent,
        calendar_id="personal",
        range_start=datetime(2025, 9, 1),
        range_end=datetime(2025, 9, 30),
    )
    assert len(occurrences) == 1
    assert occurrences[0]["recurring"] is False
    assert occurrences[0]["id"] == "abc123@baikal"


def test_build_ical_round_trips_timed_event():
    data = EventCreate(
        calendar_id="personal",
        title="Team meeting",
        start="2025-09-16T10:00:00",
        end="2025-09-16T11:00:00",
        allDay=False,
        location="Room 4",
        description="weekly sync",
    )
    raw = build_ical(data, uid="generated-uid@baikal")
    # Parse what we built and confirm it survives a round-trip.
    cal = icalendar.Calendar.from_ical(raw)
    comp = cal.walk("VEVENT")[0]
    assert str(comp["SUMMARY"]) == "Team meeting"
    assert str(comp["UID"]) == "generated-uid@baikal"
    assert comp.decoded("DTSTART") == datetime(2025, 9, 16, 10, 0, 0)
    assert comp.decoded("DTEND") == datetime(2025, 9, 16, 11, 0, 0)
    assert str(comp["LOCATION"]) == "Room 4"


def test_build_ical_all_day_uses_date_value():
    data = EventCreate(
        calendar_id="personal",
        title="Holiday",
        start="2025-12-25",
        end="2025-12-26",
        allDay=True,
        location="",
        description="",
    )
    raw = build_ical(data, uid="holiday@baikal")
    cal = icalendar.Calendar.from_ical(raw)
    comp = cal.walk("VEVENT")[0]
    assert comp.decoded("DTSTART") == date(2025, 12, 25)
    assert comp.decoded("DTEND") == date(2025, 12, 26)
