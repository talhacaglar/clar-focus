"""Application settings."""

from __future__ import annotations

import json
from typing import Any

from .database import Database

DEFAULT_SETTINGS: dict[str, Any] = {
    "pomodoro_work_minutes": 50,
    "pomodoro_short_break_minutes": 10,
    "pomodoro_long_break_minutes": 25,
    "pomodoro_long_break_every": 4,
    "default_view": "dashboard",
    "theme_variant": "midnight-gold",
    "notifications_enabled": True,
    "waybar_output_mode": "json",
    "strict_mode_default": False,
    "focus_auto_release": True,
    "focus_on_pomodoro_start": False,
}


class SettingsService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.db.seed_defaults(DEFAULT_SETTINGS)

    def get(self, key: str, default: Any = None) -> Any:
        row = self.db.fetchone("SELECT value_json FROM settings WHERE key = ?", (key,))
        if not row:
            return DEFAULT_SETTINGS.get(key, default)
        return json.loads(row["value_json"])

    def all(self) -> dict[str, Any]:
        rows = self.db.fetchall("SELECT key, value_json FROM settings ORDER BY key")
        values = dict(DEFAULT_SETTINGS)
        values.update({row["key"]: json.loads(row["value_json"]) for row in rows})
        return values

    def set(self, key: str, value: Any) -> None:
        self.db.set_setting(key, json.dumps(value))

    def update_many(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)
