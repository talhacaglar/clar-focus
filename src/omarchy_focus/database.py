"""SQLite persistence layer."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from pathlib import Path
from typing import Iterator

from .paths import DB_PATH, ensure_app_dirs
from .utils import json_dumps, to_iso, utc_now

DEFAULT_BLOCKED_SITES = (
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "instagram.com",
    "www.instagram.com",
)


class Database:
    """Thin SQLite wrapper with migrations."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path

    def initialize(self) -> None:
        ensure_app_dirs()
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'pending',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    estimated_minutes INTEGER,
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    archived_at TEXT
                );

                CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    session_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_seconds INTEGER NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    interrupted INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS focus_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    strict_mode INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL,
                    ends_at TEXT,
                    ended_actual_at TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    blocked_sites_json TEXT NOT NULL,
                    auto_release INTEGER NOT NULL DEFAULT 1,
                    recovered INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS blocked_sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'user'
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            created_at = to_iso(utc_now())
            conn.executemany(
                """
                INSERT OR IGNORE INTO blocked_sites (domain, enabled, created_at, source)
                VALUES (?, 1, ?, 'default')
                """,
                [(domain, created_at) for domain in DEFAULT_BLOCKED_SITES],
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetchone(self, sql: str, params: tuple | list = ()) -> sqlite3.Row | None:
        with self.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple | list = ()) -> list[sqlite3.Row]:
        with self.connection() as conn:
            return list(conn.execute(sql, params).fetchall())

    def execute(self, sql: str, params: tuple | list = ()) -> None:
        with self.connection() as conn:
            conn.execute(sql, params)

    def upsert_state(self, key: str, value_json: str) -> None:
        now = to_iso(utc_now())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO app_state (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, value_json, now),
            )

    def delete_state(self, key: str) -> None:
        self.execute("DELETE FROM app_state WHERE key = ?", (key,))

    def get_state(self, key: str) -> sqlite3.Row | None:
        return self.fetchone("SELECT key, value_json, updated_at FROM app_state WHERE key = ?", (key,))

    def set_setting(self, key: str, value_json: str) -> None:
        now = to_iso(utc_now())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, value_json, now),
            )

    def seed_defaults(self, defaults: dict[str, object]) -> None:
        with self.connection() as conn:
            for key, value in defaults.items():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO settings (key, value_json, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, json_dumps(value), to_iso(utc_now())),
                )
