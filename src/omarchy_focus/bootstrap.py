"""Service bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from .database import Database
from .paths import ensure_app_dirs
from .services.focus import FocusService
from .services.pomodoro import PomodoroService
from .services.stats import StatsService
from .services.tasks import TaskService
from .settings import SettingsService


@dataclass(slots=True)
class ServiceContainer:
    db: Database
    settings: SettingsService
    tasks: TaskService
    focus: FocusService
    pomodoro: PomodoroService
    stats: StatsService

    def sync(self) -> None:
        self.focus.recover()
        self.focus.status()
        self.pomodoro.tick()


def build_services() -> ServiceContainer:
    ensure_app_dirs()
    db = Database()
    db.initialize()
    settings = SettingsService(db)
    tasks = TaskService(db)
    focus = FocusService(db, settings)
    pomodoro = PomodoroService(db, settings, tasks, focus)
    stats = StatsService(db)
    return ServiceContainer(
        db=db,
        settings=settings,
        tasks=tasks,
        focus=focus,
        pomodoro=pomodoro,
        stats=stats,
    )
