"""Statistics service."""

from __future__ import annotations

import json
from collections import Counter
from datetime import timedelta

from ..database import Database
from ..models import StatsSnapshot
from ..utils import local_now, parse_dt, start_of_day, start_of_week


class StatsService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def snapshot(self) -> StatsSnapshot:
        today = start_of_day()
        week = start_of_week()
        today_iso = today.astimezone().isoformat()
        week_iso = week.astimezone().isoformat()

        today_pomodoros = self.db.fetchone(
            """
            SELECT COUNT(*) AS count, COALESCE(SUM(duration_seconds), 0) AS total
            FROM pomodoro_sessions
            WHERE session_type = 'work'
              AND completed = 1
              AND started_at >= ?
            """,
            (today_iso,),
        )
        week_pomodoros = self.db.fetchone(
            """
            SELECT COALESCE(SUM(duration_seconds), 0) AS total, COUNT(*) AS count
            FROM pomodoro_sessions
            WHERE session_type = 'work'
              AND completed = 1
              AND started_at >= ?
            """,
            (week_iso,),
        )
        week_focus_sessions = self.db.fetchone(
            """
            SELECT COUNT(*) AS count
            FROM focus_sessions
            WHERE started_at >= ?
            """,
            (week_iso,),
        )
        completed_tasks_today = self.db.fetchone(
            """
            SELECT COUNT(*) AS count
            FROM tasks
            WHERE completed_at IS NOT NULL
              AND completed_at >= ?
            """,
            (today_iso,),
        )
        completed_tasks_week = self.db.fetchone(
            """
            SELECT COUNT(*) AS count
            FROM tasks
            WHERE completed_at IS NOT NULL
              AND completed_at >= ?
            """,
            (week_iso,),
        )

        top_rows = self.db.fetchall(
            """
            SELECT COALESCE(tasks.title, 'Unassigned') AS title, SUM(duration_seconds) AS total
            FROM pomodoro_sessions
            LEFT JOIN tasks ON tasks.id = pomodoro_sessions.task_id
            WHERE pomodoro_sessions.session_type = 'work'
              AND pomodoro_sessions.completed = 1
              AND pomodoro_sessions.started_at >= ?
            GROUP BY pomodoro_sessions.task_id
            ORDER BY total DESC
            LIMIT 5
            """,
            (week_iso,),
        )
        top_task_focus = [(row["title"], int(row["total"] // 60)) for row in top_rows]

        day_rows = self.db.fetchall(
            """
            SELECT date(started_at, 'localtime') AS day, SUM(duration_seconds) AS total
            FROM pomodoro_sessions
            WHERE session_type = 'work'
              AND completed = 1
              AND started_at >= ?
            GROUP BY date(started_at, 'localtime')
            ORDER BY day ASC
            """,
            ((local_now() - timedelta(days=6)).astimezone().isoformat(),),
        )
        totals_by_day = {row["day"]: int(row["total"] // 60) for row in day_rows}
        focus_days: list[tuple[str, int]] = []
        for offset in range(6, -1, -1):
            day = (local_now() - timedelta(days=offset)).date()
            label = day.strftime("%a")
            focus_days.append((label, totals_by_day.get(day.isoformat(), 0)))

        focus_rows = self.db.fetchall(
            """
            SELECT blocked_sites_json
            FROM focus_sessions
            WHERE started_at >= ?
            """,
            (week_iso,),
        )
        blocked_counter: Counter[str] = Counter()
        for row in focus_rows:
            blocked_counter.update(json.loads(row["blocked_sites_json"]))
        blocked_sites = blocked_counter.most_common(5)

        streak = self._compute_streak()

        return StatsSnapshot(
            today_completed_pomodoros=int(today_pomodoros["count"]) if today_pomodoros else 0,
            today_focus_minutes=int(today_pomodoros["total"] // 60) if today_pomodoros else 0,
            week_focus_minutes=int(week_pomodoros["total"] // 60) if week_pomodoros else 0,
            completed_tasks_today=int(completed_tasks_today["count"]) if completed_tasks_today else 0,
            completed_tasks_week=int(completed_tasks_week["count"]) if completed_tasks_week else 0,
            streak_days=streak,
            focus_sessions_week=int(week_focus_sessions["count"]) if week_focus_sessions else 0,
            top_task_focus=top_task_focus,
            focus_days=focus_days,
            blocked_sites=blocked_sites,
        )

    def _compute_streak(self) -> int:
        rows = self.db.fetchall(
            """
            SELECT DISTINCT date(started_at, 'localtime') AS day
            FROM pomodoro_sessions
            WHERE session_type = 'work'
              AND completed = 1
            ORDER BY day DESC
            """
        )
        if not rows:
            return 0
        streak = 0
        expected = local_now().date()
        valid_days = {row["day"] for row in rows}
        if expected.isoformat() not in valid_days:
            expected = expected - timedelta(days=1)
        while expected.isoformat() in valid_days:
            streak += 1
            expected = expected - timedelta(days=1)
        return streak
