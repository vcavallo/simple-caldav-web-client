"""Pydantic models for request/response bodies."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CalendarInfo(BaseModel):
    id: str
    name: str
    color: str


class EventBase(BaseModel):
    title: str = Field(min_length=1)
    # ISO 8601 strings. Timed events: "2025-09-16T10:00:00".
    # All-day events: date-only "2025-09-16".
    start: str
    end: str
    allDay: bool = False
    location: str = ""
    description: str = ""


class EventCreate(EventBase):
    calendar_id: str


class EventUpdate(EventBase):
    # calendar_id is accepted but not used to move events (not supported in v1).
    calendar_id: Optional[str] = None
    url: str
    etag: str


class EventDelete(BaseModel):
    url: str
    etag: str


class Event(EventBase):
    id: str
    calendar_id: str
    url: str = ""
    etag: str = ""
    recurring: bool = False


class CalendarError(BaseModel):
    calendar_id: str
    message: str


class EventsResponse(BaseModel):
    # Events from calendars that loaded successfully, plus per-calendar errors
    # for any that failed — so one bad calendar never blanks the whole view.
    events: List[Event]
    errors: List[CalendarError] = []
