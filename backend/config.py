"""Configuration loading: reads config.yaml and applies env-var overrides."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


def _slugify(name: str) -> str:
    """Derive a calendar id from its name: lowercase alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


@dataclass
class Calendar:
    name: str
    url: str
    username: str
    password: str
    color: str
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _slugify(self.name)


@dataclass
class Config:
    calendars: List[Calendar] = field(default_factory=list)

    def get(self, calendar_id: str) -> Optional[Calendar]:
        for cal in self.calendars:
            if cal.id == calendar_id:
                return cal
        return None


def load_config(path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text()) or {}
    calendars: List[Calendar] = []
    for index, entry in enumerate(raw.get("calendars", [])):
        password = os.environ.get(
            f"CALDAV_CAL_{index}_PASSWORD",
            entry.get("password", ""),
        )
        calendars.append(Calendar(
            id=entry.get("id", ""),
            name=entry["name"],
            url=entry["url"],
            username=entry.get("username", ""),
            password=password,
            color=entry.get("color", "#3788d8"),
        ))
    return Config(calendars=calendars)
