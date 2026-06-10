"""FastAPI application: REST proxy in front of one or more CalDAV calendars."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.caldav_client import (
    CalDavAuthError,
    CalDavClient,
    CalDavError,
    CalDavUnreachable,
    ETagConflict,
    NotFoundError,
)
from backend.config import Config, load_config
from backend.models import (
    CalendarInfo,
    Event,
    EventCreate,
    EventDelete,
    EventsResponse,
    EventUpdate,
)

app = FastAPI(title="CalDAV Web Client")


# --------------------------------------------------------------------------- #
# Dependencies (overridden in tests)
# --------------------------------------------------------------------------- #
@lru_cache
def get_config() -> Config:
    path = os.environ.get("CALDAV_CONFIG", "config.yaml")
    return load_config(path)


@lru_cache
def _build_client() -> CalDavClient:
    return CalDavClient(get_config())


def get_client() -> CalDavClient:
    return _build_client()


# --------------------------------------------------------------------------- #
# Error handling
# --------------------------------------------------------------------------- #
_STATUS_FOR = {
    ETagConflict: 412,
    NotFoundError: 404,
    CalDavAuthError: 502,
    CalDavUnreachable: 503,
}


@app.exception_handler(CalDavError)
async def caldav_error_handler(request: Request, exc: CalDavError):
    status = 500
    for kind, code in _STATUS_FOR.items():
        if isinstance(exc, kind):
            status = code
            break
    message = str(exc) or exc.__class__.__name__
    return JSONResponse(status_code=status, content={"error": message})


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/calendars", response_model=List[CalendarInfo])
async def list_calendars(client: CalDavClient = Depends(get_client)):
    return client.list_calendars()


@app.get("/api/events", response_model=EventsResponse)
async def list_events(
    start: str = Query(...),
    end: str = Query(...),
    calendars: Optional[str] = Query(None),
    client: CalDavClient = Depends(get_client),
):
    calendar_ids = [c for c in calendars.split(",") if c] if calendars else None
    return await client.get_events(start, end, calendar_ids)


@app.post("/api/events", response_model=Event, status_code=201)
async def create_event(
    data: EventCreate,
    client: CalDavClient = Depends(get_client),
):
    return await client.create_event(data)


@app.put("/api/events/{event_id}", response_model=Event)
async def update_event(
    event_id: str,
    data: EventUpdate,
    client: CalDavClient = Depends(get_client),
):
    return await client.update_event(event_id, data)


@app.delete("/api/events/{event_id}", status_code=204)
async def delete_event(
    event_id: str,
    data: EventDelete,
    client: CalDavClient = Depends(get_client),
):
    await client.delete_event(event_id, data.url, data.etag)
    return Response(status_code=204)


# --------------------------------------------------------------------------- #
# Static frontend (built React app). Mounted last so /api takes precedence.
# --------------------------------------------------------------------------- #
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
