"""Filesystem paths used by Omarchy Focus."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Clar Focus"
APP_SLUG = "omarchy-focus"

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / APP_SLUG
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share")) / APP_SLUG
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local" / "state")) / APP_SLUG
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / APP_SLUG

DB_PATH = DATA_DIR / "focus.db"
WAYBAR_SIGNAL = 12


def ensure_app_dirs() -> None:
    """Create app directories if they do not exist."""
    for path in (CONFIG_DIR, DATA_DIR, STATE_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)
