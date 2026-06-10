"""Unit tests for CalDavClient.get_events aggregation (no network).

We monkeypatch the per-calendar fetch so we can exercise the partial-failure
path without a real CalDAV server.
"""
from backend.caldav_client import CalDavClient, CalDavUnreachable
from backend.config import Calendar, Config


def make_config():
    return Config(calendars=[
        Calendar(id="a", name="A", url="https://x/dav.php/calendars/u/a/",
                 username="u", password="p", color="#000000"),
        Calendar(id="b", name="B", url="https://x/dav.php/calendars/u/b/",
                 username="u", password="p", color="#111111"),
    ])


def _event(cal_id, title):
    return {
        "id": f"{cal_id}-1", "calendar_id": cal_id, "title": title,
        "start": "2025-09-15T10:00:00", "end": "2025-09-15T11:00:00",
        "allDay": False, "location": "", "description": "",
        "url": "", "etag": "", "recurring": False,
    }


async def test_get_events_tolerates_one_failing_calendar(monkeypatch):
    client = CalDavClient(make_config())

    def fake_fetch(cal, start, end):
        if cal.id == "b":
            raise CalDavUnreachable("could not reach calendar b")
        return [_event("a", "from-a")]

    monkeypatch.setattr(client, "_fetch_one", fake_fetch)

    result = await client.get_events(
        "2025-09-01T00:00:00", "2025-09-30T00:00:00",
    )

    assert [e["title"] for e in result["events"]] == ["from-a"]
    assert len(result["errors"]) == 1
    assert result["errors"][0]["calendar_id"] == "b"
    assert "could not reach" in result["errors"][0]["message"]


async def test_get_events_all_success_has_no_errors(monkeypatch):
    client = CalDavClient(make_config())
    monkeypatch.setattr(client, "_fetch_one",
                        lambda cal, s, e: [_event(cal.id, cal.id)])

    result = await client.get_events("2025-09-01T00:00:00", "2025-09-30T00:00:00")

    assert sorted(e["calendar_id"] for e in result["events"]) == ["a", "b"]
    assert result["errors"] == []
