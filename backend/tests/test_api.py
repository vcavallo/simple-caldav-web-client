"""API-level tests using a fake CalDAV backend injected via dependency override."""
import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.config import Config, Calendar
from backend.caldav_client import ETagConflict, CalDavAuthError, NotFoundError


class FakeClient:
    """In-memory stand-in for CalDavClient with the same public interface."""

    def __init__(self, config):
        self.config = config
        self._store = {}  # id -> event dict
        self._counter = 0
        self.fail_with = None  # exception instance to raise on next mutation

    def list_calendars(self):
        return [
            {"id": c.id, "name": c.name, "color": c.color}
            for c in self.config.calendars
        ]

    async def get_events(self, start, end, calendar_ids=None):
        events = list(self._store.values())
        if calendar_ids:
            events = [e for e in events if e["calendar_id"] in calendar_ids]
        return events

    async def create_event(self, data):
        if self.fail_with:
            raise self.fail_with
        self._counter += 1
        eid = f"evt{self._counter}@baikal"
        ev = {
            "id": eid,
            "calendar_id": data.calendar_id,
            "title": data.title,
            "start": data.start,
            "end": data.end,
            "allDay": data.allDay,
            "location": data.location,
            "description": data.description,
            "url": f"/dav/{data.calendar_id}/{eid}.ics",
            "etag": '"etag1"',
            "recurring": False,
        }
        self._store[eid] = ev
        return ev

    async def update_event(self, event_id, data):
        if self.fail_with:
            raise self.fail_with
        if event_id not in self._store:
            raise NotFoundError(event_id)
        ev = self._store[event_id]
        ev.update({
            "title": data.title,
            "start": data.start,
            "end": data.end,
            "allDay": data.allDay,
            "location": data.location,
            "description": data.description,
            "etag": '"etag2"',
        })
        return ev

    async def delete_event(self, event_id, url, etag):
        if self.fail_with:
            raise self.fail_with
        if event_id not in self._store:
            raise NotFoundError(event_id)
        del self._store[event_id]


@pytest.fixture
def config():
    return Config(calendars=[
        Calendar(id="personal", name="Personal",
                 url="https://baikal.example/dav.php/calendars/user/personal/",
                 username="user", password="pw", color="#4A90D9"),
        Calendar(id="work", name="Work",
                 url="https://baikal.example/dav.php/calendars/user/work/",
                 username="user", password="pw", color="#F5A623"),
    ])


@pytest.fixture
def fake(config):
    return FakeClient(config)


@pytest.fixture
def client(config, fake):
    main.app.dependency_overrides[main.get_config] = lambda: config
    main.app.dependency_overrides[main.get_client] = lambda: fake
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_list_calendars_excludes_credentials(client):
    r = client.get("/api/calendars")
    assert r.status_code == 200
    data = r.json()
    assert data == [
        {"id": "personal", "name": "Personal", "color": "#4A90D9"},
        {"id": "work", "name": "Work", "color": "#F5A623"},
    ]
    # never leak credentials
    assert "password" not in r.text
    assert "username" not in r.text
    assert "url" not in r.text


def test_create_then_list_event(client):
    body = {
        "calendar_id": "personal",
        "title": "Team meeting",
        "start": "2025-09-16T10:00:00",
        "end": "2025-09-16T11:00:00",
        "allDay": False,
        "location": "",
        "description": "",
    }
    r = client.post("/api/events", json=body)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["id"]
    assert created["title"] == "Team meeting"
    assert created["etag"]
    assert created["url"]

    r2 = client.get("/api/events?start=2025-09-01T00:00:00&end=2025-09-30T00:00:00")
    assert r2.status_code == 200
    events = r2.json()
    assert len(events) == 1
    assert events[0]["title"] == "Team meeting"


def test_create_requires_title(client):
    body = {
        "calendar_id": "personal",
        "title": "",
        "start": "2025-09-16T10:00:00",
        "end": "2025-09-16T11:00:00",
        "allDay": False,
    }
    r = client.post("/api/events", json=body)
    assert r.status_code == 422


def test_events_filtered_by_calendar(client, fake):
    client.post("/api/events", json={
        "calendar_id": "personal", "title": "P",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
    })
    client.post("/api/events", json={
        "calendar_id": "work", "title": "W",
        "start": "2025-09-16T12:00:00", "end": "2025-09-16T13:00:00", "allDay": False,
    })
    r = client.get("/api/events?start=2025-09-01T00:00:00&end=2025-09-30T00:00:00&calendars=work")
    titles = [e["title"] for e in r.json()]
    assert titles == ["W"]


def test_update_event(client):
    created = client.post("/api/events", json={
        "calendar_id": "personal", "title": "Old",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
    }).json()
    eid = created["id"]
    r = client.put(f"/api/events/{eid}", json={
        "calendar_id": "personal", "title": "New",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
        "location": "Room 9", "description": "updated",
        "url": created["url"], "etag": created["etag"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "New"
    assert r.json()["location"] == "Room 9"


def test_delete_event(client):
    created = client.post("/api/events", json={
        "calendar_id": "personal", "title": "Doomed",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
    }).json()
    eid = created["id"]
    r = client.request("DELETE", f"/api/events/{eid}", json={
        "url": created["url"], "etag": created["etag"],
    })
    assert r.status_code == 204, r.text
    remaining = client.get("/api/events?start=2025-09-01T00:00:00&end=2025-09-30T00:00:00").json()
    assert remaining == []


def test_etag_conflict_returns_412(client, fake):
    created = client.post("/api/events", json={
        "calendar_id": "personal", "title": "X",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
    }).json()
    fake.fail_with = ETagConflict("conflict")
    r = client.put(f"/api/events/{created['id']}", json={
        "calendar_id": "personal", "title": "Y",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
        "url": created["url"], "etag": created["etag"],
    })
    assert r.status_code == 412
    assert "error" in r.json()


def test_auth_failure_returns_502(client, fake):
    fake.fail_with = CalDavAuthError("bad creds")
    r = client.post("/api/events", json={
        "calendar_id": "personal", "title": "X",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
    })
    assert r.status_code == 502
    assert "error" in r.json()


def test_update_missing_event_returns_404(client):
    r = client.put("/api/events/nope@baikal", json={
        "calendar_id": "personal", "title": "Y",
        "start": "2025-09-16T10:00:00", "end": "2025-09-16T11:00:00", "allDay": False,
        "url": "/dav/x.ics", "etag": '"e"',
    })
    assert r.status_code == 404
