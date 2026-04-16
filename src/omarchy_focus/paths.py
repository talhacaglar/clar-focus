"""Filesystem paths used by Clar Focus."""

from __future__ import annotations

import os
from pathlib import Path
import shutil

APP_NAME = "Clar Focus"
APP_SLUG = "clar-focus"
LEGACY_APP_SLUG = "omarchy-focus"

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / APP_SLUG
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share")) / APP_SLUG
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local" / "state")) / APP_SLUG
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / APP_SLUG
LEGACY_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / LEGACY_APP_SLUG
LEGACY_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share")) / LEGACY_APP_SLUG
LEGACY_STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local" / "state")) / LEGACY_APP_SLUG
LEGACY_CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / LEGACY_APP_SLUG

DB_PATH = DATA_DIR / "focus.db"
WAYBAR_SIGNAL = 12


def ensure_app_dirs() -> None:
    """Create app directories if they do not exist."""
    for legacy_path, new_path in (
        (LEGACY_CONFIG_DIR, CONFIG_DIR),
        (LEGACY_DATA_DIR, DATA_DIR),
        (LEGACY_STATE_DIR, STATE_DIR),
        (LEGACY_CACHE_DIR, CACHE_DIR),
    ):
        if legacy_path.exists() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy_path), str(new_path))
    for path in (CONFIG_DIR, DATA_DIR, STATE_DIR, CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)
