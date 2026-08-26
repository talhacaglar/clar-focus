from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Button, DataTable, Input, Static

from omarchy_focus.bootstrap import ServiceContainer
from omarchy_focus.database import Database
from omarchy_focus.services.focus import FocusService
from omarchy_focus.services.pomodoro import PomodoroService
from omarchy_focus.services.stats import StatsService
from omarchy_focus.services.tasks import TaskService
from omarchy_focus.settings import SettingsService
from omarchy_focus.tui.app import OmarchyFocusApp
from omarchy_focus.tui.dialogs import TaskEditorScreen


def build_test_services(path: Path) -> ServiceContainer:
    db = Database(path)
    db.initialize()
    settings = SettingsService(db)
    tasks = TaskService(db)
    focus = FocusService(db, settings)
    pomodoro = PomodoroService(db, settings, tasks, focus)
    stats = StatsService(db)
    return ServiceContainer(db, settings, tasks, focus, pomodoro, stats)


class TuiExperienceTest(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_leads_with_next_task_and_search_keeps_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            services = build_test_services(Path(tmpdir) / "focus.db")
            services.tasks.add_task("Draft launch notes", estimated_minutes=40)
            with (
                patch("omarchy_focus.tui.app.build_services", return_value=services),
                patch("omarchy_focus.tui.app.register_tui_window"),
                patch.object(ServiceContainer, "sync", return_value=None),
            ):
                app = OmarchyFocusApp()
                async with app.run_test(size=(140, 46)) as pilot:
                    await pilot.pause()
                    self.assertIn("Draft launch notes", str(app.query_one("#dashboard-now", Static).render()))

                    app.show_view("tasks")
                    search = app.query_one("#task-search", Input)
                    search.value = "no-such-task"
                    await pilot.pause(0.3)

                    self.assertEqual(app.filters.search, "no-such-task")
                    self.assertEqual(app.query_one("#tasks-table", DataTable).row_count, 0)
                    self.assertTrue(app.query_one("#tasks-empty", Static).display)

                    app.refresh_live_data()
                    self.assertEqual(search.value, "no-such-task")

                    focus_button = app.query_one("#focus-toggle", Button)
                    self.assertIn("Start focus guard", str(focus_button.label))
                    app._cached_focus = app._cached_focus.__class__(active=True)
                    app._refresh_dashboard_focus()
                    self.assertIn("Stop focus guard", str(focus_button.label))
                    self.assertEqual(focus_button.variant, "warning")

    async def test_compact_layout_and_task_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            services = build_test_services(Path(tmpdir) / "focus.db")
            with (
                patch("omarchy_focus.tui.app.build_services", return_value=services),
                patch("omarchy_focus.tui.app.register_tui_window"),
                patch.object(ServiceContainer, "sync", return_value=None),
            ):
                app = OmarchyFocusApp()
                async with app.run_test(size=(90, 40)) as pilot:
                    await pilot.pause()
                    self.assertTrue(app.has_class("compact"))
                    self.assertFalse(app.query_one("#brand-card", Static).display)

                    app.push_screen(TaskEditorScreen())
                    await pilot.pause()
                    app.screen.query_one("#title", Input).value = "Plan release"
                    app.screen.query_one("#estimate", Input).value = "soon"
                    await pilot.click("#save")
                    await pilot.pause()

                    self.assertIsInstance(app.screen, TaskEditorScreen)
                    error = str(app.screen.query_one("#task-editor-error", Static).render())
                    self.assertIn("whole number", error)


if __name__ == "__main__":
    unittest.main()
