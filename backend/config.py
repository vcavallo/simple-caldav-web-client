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


def _resolve_password(index: int, entry: dict) -> str:
    """Resolve a calendar's password.

    Precedence (highest first):
      1. CALDAV_CAL_<index>_PASSWORD environment variable
      2. `password_file`: path to a file holding the password (newline stripped)
      3. inline `password`
    """
    env = os.environ.get(f"CALDAV_CAL_{index}_PASSWORD")
    if env is not None:
        return env

    pw_file = entry.get("password_file")
    if pw_file:
        pw_path = Path(os.path.expanduser(pw_file))
        if not pw_path.exists():
            raise FileNotFoundError(f"password_file not found: {pw_path}")
        return pw_path.read_text().strip()

    return entry.get("password", "")


def load_config(path) -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = yaml.safe_load(path.read_text()) or {}
    calendars: List[Calendar] = []
    for index, entry in enumerate(raw.get("calendars", [])):
        password = _resolve_password(index, entry)
        calendars.append(Calendar(
            id=entry.get("id", ""),
            name=entry["name"],
            url=entry["url"],
            username=entry.get("username", ""),
            password=password,
            color=entry.get("color", "#3788d8"),
        ))
    return Config(calendars=calendars)
