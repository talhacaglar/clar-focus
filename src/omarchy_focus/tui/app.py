"""Main Textual application."""

from __future__ import annotations

import math
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from ..bootstrap import build_services
from ..models import FocusStateSnapshot, PomodoroStateSnapshot, SessionPhase, SessionType, StatsSnapshot, Task, TaskFilters
from ..paths import APP_NAME
from ..utils import (
    format_datetime,
    minutes_to_label,
    progress_bar,
    register_tui_window,
    remaining_seconds,
    seconds_to_clock,
    sparkline,
)
from .dialogs import (
    BlockedSitesScreen,
    BreakPromptScreen,
    ConfirmScreen,
    FilterScreen,
    QuickAddTaskScreen,
    SearchScreen,
    SettingEditScreen,
    TaskEditorResult,
    TaskEditorScreen,
)


class OmarchyFocusApp(App[None]):
    """Clar Focus premium TUI."""

    CSS_PATH = "app.tcss"
    TITLE = APP_NAME
    SUB_TITLE = "Tasklist + Pomodoro + Focus Manager"

    BINDINGS = [
        Binding("q", "app_quit", "Quit"),
        Binding("a", "add_task", "Add Task"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("x", "complete_selected", "Done"),
        Binding("slash", "search_tasks", "Search"),
        Binding("f", "filter_tasks", "Filter"),
        Binding("s", "toggle_pomodoro", "Start/Stop"),
        Binding("p", "pause_resume", "Pause/Resume"),
        Binding("m", "toggle_focus", "Focus"),
        Binding("b", "show_blocked_sites", "Blocked Sites"),
        Binding("t", "show_tasks", "Tasks"),
        Binding("g", "show_dashboard", "Dashboard"),
        Binding("i", "show_statistics", "Statistics"),
        Binding("comma", "show_settings", "Settings"),
        Binding("question_mark", "show_help", "Help"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.services = build_services()
        self.filters = TaskFilters(sort_by="priority_desc")
        self.selected_task_id: int | None = None
        self.selected_focus_domain: str | None = None
        self.selected_setting_key: str | None = None
        self._pending_break_prompt_id: str | None = None
        self._cached_pomodoro = PomodoroStateSnapshot()
        self._cached_focus = FocusStateSnapshot()
        self._cached_stats = StatsSnapshot()
        self._cached_pending_break: dict[str, object] | None = None
        self._cached_pending_count = 0
        self._cached_done_today = 0
        self._task_row_map: dict[str, list[int]] = {}
        self._site_row_map: list[str] = []
        self._setting_row_map: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="app-shell"):
            with Horizontal(id="status-bar"):
                yield Static(
                    f"󰄛  {APP_NAME}\nPremium terminal productivity for Hyprland",
                    id="brand-card",
                )
                yield Static(id="pomodoro-chip", classes="status-chip")
                yield Static(id="focus-chip", classes="status-chip")
                yield Static(id="task-chip", classes="status-chip")
                yield Static(id="summary-chip", classes="status-chip")
            with TabbedContent(initial=str(self.services.settings.get("default_view")), id="views"):
                with TabPane("Dashboard", id="dashboard"):
                    with Grid(id="dashboard-grid"):
                        yield Static(id="dashboard-summary", classes="panel")
                        yield Static(id="dashboard-detail", classes="panel")
                        with Vertical(id="dashboard-tasks-panel", classes="panel"):
                            yield Static("Today Queue", classes="panel-title")
                            yield DataTable(id="dashboard-tasks")
                        yield Static(id="dashboard-pomodoro", classes="panel")
                        yield Static(id="dashboard-focus", classes="panel")
                        yield Static(id="dashboard-stats", classes="panel")
                with TabPane("Tasks", id="tasks"):
                    with Horizontal(id="tasks-layout"):
                        with Vertical(id="tasks-main"):
                            yield Static("Task Explorer", classes="panel panel-title")
                            yield Input(placeholder="Search tasks…", id="task-search")
                            yield Static(id="task-filter-summary", classes="panel")
                            yield DataTable(id="tasks-table")
                        with Vertical(id="tasks-side"):
                            yield Static(id="task-detail", classes="panel")
                            yield Static(id="task-quick-actions", classes="panel")
                with TabPane("Focus Session", id="focus"):
                    with Horizontal(id="focus-layout"):
                        with Vertical(id="focus-main"):
                            yield Static(id="focus-status", classes="panel")
                            yield DataTable(id="focus-sites-table")
                        with Vertical(id="focus-side"):
                            yield Static(id="focus-controls", classes="panel")
                            yield Static(id="focus-history", classes="panel")
                with TabPane("Statistics", id="statistics"):
                    with Horizontal(id="statistics-layout"):
                        with Vertical(id="stats-main"):
                            yield Static(id="stats-overview", classes="panel")
                            yield Static(id="stats-charts", classes="panel")
                        with Vertical(id="stats-side"):
                            yield Static(id="stats-tasks", classes="panel")
                            yield Static(id="stats-focus", classes="panel")
                with TabPane("Settings", id="settings"):
                    with Horizontal(id="settings-layout"):
                        with Vertical(id="settings-main"):
                            yield Static(id="settings-summary", classes="panel")
                            yield DataTable(id="settings-table")
                        with Vertical(id="settings-side"):
                            yield Static(id="settings-hints", classes="panel")
                with TabPane("Help", id="help"):
                    yield Static(id="help-pane")
        yield Footer()

    def on_mount(self) -> None:
        self._configure_tables()
        register_tui_window()
        self.set_timer(0.5, register_tui_window)
        self.set_interval(1.0, self.refresh_data)
        self.refresh_data()

    def _configure_tables(self) -> None:
        for table_id in ("dashboard-tasks", "tasks-table"):
            table = self.query_one(f"#{table_id}", DataTable)
            table.cursor_type = "row"
            table.add_columns("ID", "Title", "Priority", "Status", "Due")
        sites_table = self.query_one("#focus-sites-table", DataTable)
        sites_table.cursor_type = "row"
        sites_table.add_columns("Domain", "Enabled", "Source")
        settings_table = self.query_one("#settings-table", DataTable)
        settings_table.cursor_type = "row"
        settings_table.add_columns("Setting", "Value")

    def refresh_data(self) -> None:
        self.services.sync()
        self._cached_pomodoro = self.services.pomodoro.snapshot()
        self._cached_pending_break = self.services.pomodoro.pending_break()
        self._cached_focus = self.services.focus.snapshot()
        self._cached_stats = self.services.stats.snapshot()
        self._cached_pending_count = self.services.tasks.count_pending()
        self._cached_done_today = self.services.tasks.count_done_today()
        self._refresh_top_chips()
        self._refresh_dashboard()
        self._refresh_tasks()
        self._refresh_focus()
        self._refresh_stats()
        self._refresh_settings()
        self._refresh_help()
        self._handle_pending_break_prompt()

    def _refresh_top_chips(self) -> None:
        pomodoro = self._cached_pomodoro
        focus = self._cached_focus
        stats = self._cached_stats
        pending = self._cached_pending_count
        pending_break = self._cached_pending_break
        pomodoro_text = "󰄉 Idle\nReady for deep work"
        if pomodoro.phase == SessionPhase.RUNNING:
            label = "Work" if pomodoro.session_type == SessionType.WORK else "Break"
            pomodoro_text = f"󰄉 {label}\n{seconds_to_clock(pomodoro.remaining_seconds)} left"
        elif pomodoro.phase == SessionPhase.PAUSED:
            pomodoro_text = f"󰄉 Paused\n{seconds_to_clock(pomodoro.remaining_seconds)} left"
        elif pending_break:
            pomodoro_text = f"󰁅 Break Ready\n{pending_break.get('minutes', 10)}m waiting"
        focus_text = "󰈈 Focus\nOff"
        if focus.active:
            strict = "strict" if focus.strict_mode else "adaptive"
            left = seconds_to_clock(remaining_seconds(focus.ends_at)) if focus.ends_at else "manual"
            focus_text = f"󰈈 {strict.title()}\n{left} · {len(focus.blocked_sites)} sites"
        task_text = f" Queue\n{pending} active task(s)"
        summary_text = (
            f"󰔟 Today\n{stats.today_completed_pomodoros} pomo · {stats.today_focus_minutes}m\n"
            f"Streak {stats.streak_days} day(s)"
        )
        self.query_one("#pomodoro-chip", Static).update(pomodoro_text)
        self.query_one("#focus-chip", Static).update(focus_text)
        self.query_one("#task-chip", Static).update(task_text)
        self.query_one("#summary-chip", Static).update(summary_text)

    def _handle_pending_break_prompt(self) -> None:
        pending_break = self.services.pomodoro.pending_break()
        if not pending_break:
            self._pending_break_prompt_id = None
            return

        prompt_id = str(pending_break.get("prompt_id") or "")
        if not prompt_id or prompt_id == self._pending_break_prompt_id:
            return

        self._pending_break_prompt_id = prompt_id
        self.show_view("dashboard")
        self.push_screen(
            BreakPromptScreen(
                minutes=int(pending_break.get("minutes", 10)),
                task_title=str(pending_break.get("task_title") or "") or None,
            ),
            lambda accepted: self._handle_break_prompt_result(prompt_id, accepted),
        )

    def _handle_break_prompt_result(self, prompt_id: str, accepted: bool) -> None:
        pending_break = self.services.pomodoro.pending_break()
        if not pending_break or str(pending_break.get("prompt_id") or "") != prompt_id:
            self.refresh_data()
            return

        if accepted:
            self.services.pomodoro.start_break(minutes=int(pending_break.get("minutes", 10)))
        else:
            self.services.pomodoro.clear_pending_break()
        self.refresh_data()

    def _task_table_rows(self) -> list[Task]:
        tasks = self.services.tasks.list_tasks(self.filters)
        if not tasks and self.filters.search:
            self.filters.search = ""
            tasks = self.services.tasks.list_tasks(self.filters)
        return tasks

    def _populate_task_table(self, table_id: str, tasks: list[Task]) -> None:
        table = self.query_one(f"#{table_id}", DataTable)
        table.clear()
        self._task_row_map[table_id] = []
        for task in tasks:
            self._task_row_map[table_id].append(task.id)
            table.add_row(
                str(task.id),
                task.title[:28],
                task.priority.value,
                task.status.value.replace("_", " "),
                format_datetime(task.due_at) if task.due_at else "—",
            )
        if tasks and self.selected_task_id is None:
            self.selected_task_id = tasks[0].id

    def _get_task_by_selection(self) -> Task | None:
        if self.selected_task_id is None:
            candidate = self.services.tasks.get_next_focus_candidate()
            if candidate:
                self.selected_task_id = candidate.id
            else:
                return None
        try:
            return self.services.tasks.get_task(self.selected_task_id)
        except Exception:
            return None

    def _refresh_dashboard(self) -> None:
        tasks_today = self.services.tasks.list_tasks(
            TaskFilters(today=True, sort_by="priority_desc", include_archived=False)
        )[:8]
        self._populate_task_table("dashboard-tasks", tasks_today)
        stats = self._cached_stats
        pomodoro = self._cached_pomodoro
        focus = self._cached_focus
        next_task = self.services.tasks.get_next_focus_candidate()
        self.query_one("#dashboard-summary", Static).update(
            "\n".join(
                [
                    "Dashboard",
                    "",
                    f"Next task      {next_task.title if next_task else 'Nothing queued'}",
                    f"Pending        {self._cached_pending_count}",
                    f"Done today     {self._cached_done_today}",
                    f"Focus minutes  {stats.today_focus_minutes}",
                    f"Weekly total   {stats.week_focus_minutes}m",
                ]
            )
        )
        self.query_one("#dashboard-pomodoro", Static).update(
            "\n".join(
                [
                    "Pomodoro Engine",
                    "",
                    f"Phase          {pomodoro.phase.value}",
                    f"Type           {pomodoro.session_type.value if pomodoro.session_type else 'idle'}",
                    f"Remaining      {seconds_to_clock(pomodoro.remaining_seconds)}",
                    f"Task           {pomodoro.task_title or 'Unassigned'}",
                ]
            )
        )
        self.query_one("#dashboard-focus", Static).update(
            "\n".join(
                [
                    "Focus Lock",
                    "",
                    f"Status         {'ACTIVE' if focus.active else 'OFF'}",
                    f"Strict         {'yes' if focus.strict_mode else 'no'}",
                    f"Blocked        {len(focus.blocked_sites)} site(s)",
                    f"Auto release   {'yes' if focus.auto_release else 'no'}",
                ]
            )
        )
        self.query_one("#dashboard-stats", Static).update(
            "\n".join(
                [
                    "Weekly Pulse",
                    "",
                    f"{' '.join(f'{day}:{minutes}m' for day, minutes in stats.focus_days)}",
                    sparkline([minutes for _, minutes in stats.focus_days]),
                    "",
                    f"Top streak     {stats.streak_days} day(s)",
                    f"Focus sessions {stats.focus_sessions_week}",
                ]
            )
        )
        self._update_task_detail("#dashboard-detail")

    def _refresh_tasks(self) -> None:
        tasks = self._task_table_rows()
        self._populate_task_table("tasks-table", tasks)
        search = self.query_one("#task-search", Input).value
        if search != self.filters.search:
            self.query_one("#task-search", Input).value = self.filters.search
        summary_lines = [
            "Task Filters",
            "",
            f"Search         {self.filters.search or '—'}",
            f"Status         {self.filters.status.value if self.filters.status else 'any'}",
            f"Priority       {self.filters.priority.value if self.filters.priority else 'any'}",
            f"Today          {'yes' if self.filters.today else 'no'}",
            f"Completed      {'yes' if self.filters.completed else 'no'}",
            f"Sort           {self.filters.sort_by}",
        ]
        self.query_one("#task-filter-summary", Static).update("\n".join(summary_lines))
        self.query_one("#task-quick-actions", Static).update(
            "\n".join(
                [
                    "Quick Actions",
                    "",
                    "a  add new task",
                    "e  edit selected task",
                    "x  mark selected done",
                    "d  delete selected task",
                    "s  start pomodoro on selection",
                    "/  search",
                    "f  advanced filter",
                ]
            )
        )
        self._update_task_detail("#task-detail")

    def _update_task_detail(self, widget_id: str) -> None:
        task = self._get_task_by_selection()
        if not task:
            self.query_one(widget_id, Static).update("No task selected.")
            return
        lines = [
            f"{task.title}",
            "",
            f"Status         {task.status.value.replace('_', ' ')}",
            f"Priority       {task.priority.value}",
            f"Estimate       {minutes_to_label(task.estimated_minutes)}",
            f"Due            {format_datetime(task.due_at)}",
            f"Tags           {' '.join('#' + tag for tag in task.tags) if task.tags else '—'}",
            "",
            "Notes",
            task.description or "No extra notes.",
        ]
        self.query_one(widget_id, Static).update("\n".join(lines))

    def _refresh_focus(self) -> None:
        focus = self._cached_focus
        sites = self.services.focus.list_sites()
        table = self.query_one("#focus-sites-table", DataTable)
        table.clear()
        self._site_row_map = []
        for domain, enabled, source in sites:
            self._site_row_map.append(domain)
            table.add_row(domain, "yes" if enabled else "no", source)
        if self.selected_focus_domain is None and self._site_row_map:
            self.selected_focus_domain = self._site_row_map[0]
        if self.selected_focus_domain:
            for index, domain in enumerate(self._site_row_map):
                if domain == self.selected_focus_domain:
                    table.move_cursor(row=index)
                    break
        remaining = seconds_to_clock(remaining_seconds(focus.ends_at)) if focus.ends_at else "manual"
        self.query_one("#focus-status", Static).update(
            "\n".join(
                [
                    "Focus Session",
                    "",
                    f"Active         {'yes' if focus.active else 'no'}",
                    f"Strict         {'yes' if focus.strict_mode else 'no'}",
                    f"Time left      {remaining}",
                    f"Blocked sites  {len(focus.blocked_sites)}",
                    f"Recovered      {'yes' if focus.recovered else 'no'}",
                    "",
                    "Middle click in Waybar can toggle focus mode.",
                ]
            )
        )
        self.query_one("#focus-controls", Static).update(
            "\n".join(
                [
                    "Focus Controls",
                    "",
                    "m  toggle focus mode",
                    "b  open blocked site manager",
                    "s  start pomodoro + focus manually",
                    "",
                    "Default mode uses your configured blocked sites.",
                ]
            )
        )
        stats = self._cached_stats
        top_blocked = ", ".join(f"{site} ({count})" for site, count in stats.blocked_sites) or "No recent focus sessions"
        self.query_one("#focus-history", Static).update(
            "\n".join(
                [
                    "Focus Analytics",
                    "",
                    f"Week sessions  {stats.focus_sessions_week}",
                    f"Week focus     {stats.week_focus_minutes}m",
                    f"Top blocks     {top_blocked}",
                ]
            )
        )

    def _refresh_stats(self) -> None:
        stats = self._cached_stats
        self.query_one("#stats-overview", Static).update(
            "\n".join(
                [
                    "Performance Overview",
                    "",
                    f"Today pomodoros    {stats.today_completed_pomodoros}",
                    f"Today focus        {stats.today_focus_minutes}m",
                    f"Week focus         {stats.week_focus_minutes}m",
                    f"Tasks today        {stats.completed_tasks_today}",
                    f"Tasks this week    {stats.completed_tasks_week}",
                    f"Streak             {stats.streak_days} day(s)",
                ]
            )
        )
        chart_values = [minutes for _, minutes in stats.focus_days]
        chart = sparkline(chart_values)
        labels = " ".join(day[:2] for day, _ in stats.focus_days)
        self.query_one("#stats-charts", Static).update(
            "\n".join(
                [
                    "Weekly Rhythm",
                    "",
                    chart,
                    labels,
                    "",
                    "Daily load",
                    " ".join(
                        f"{day} {progress_bar(minutes, max(chart_values) or 1, width=8)} {minutes:>3}m"
                        for day, minutes in stats.focus_days
                    ),
                ]
            )
        )
        top_tasks = "\n".join(
            f"{title[:22]:<22} {minutes:>4}m" for title, minutes in stats.top_task_focus
        ) or "No task-linked sessions yet."
        self.query_one("#stats-tasks", Static).update(
            "\n".join(
                [
                    "Top Tasks",
                    "",
                    top_tasks,
                ]
            )
        )
        blocked = "\n".join(
            f"{site:<26} {count}" for site, count in stats.blocked_sites
        ) or "No blocked site hits yet."
        self.query_one("#stats-focus", Static).update(
            "\n".join(
                [
                    "Blocked Domains",
                    "",
                    blocked,
                ]
            )
        )

    def _refresh_settings(self) -> None:
        values = self.services.settings.all()
        table = self.query_one("#settings-table", DataTable)
        table.clear()
        self._setting_row_map = []
        for key, value in values.items():
            self._setting_row_map.append(key)
            table.add_row(key, str(value))
        self.selected_setting_key = self.selected_setting_key or (self._setting_row_map[0] if self._setting_row_map else None)
        self.query_one("#settings-summary", Static).update(
            "\n".join(
                [
                    "Settings",
                    "",
                    "Select a row and press e to edit.",
                    "Booleans accept true/false.",
                    "Integers are parsed automatically.",
                ]
            )
        )
        self.query_one("#settings-hints", Static).update(
            "\n".join(
                [
                    "Recommended Profiles",
                    "",
                    "50 / 10 / 25 / every 4 cycles",
                    "Theme: midnight-gold",
                    "Waybar output: json",
                    "Strict focus default: false",
                    "",
                    "Use CLI for bulk changes if you prefer scripting.",
                ]
            )
        )

    def _refresh_help(self) -> None:
        self.query_one("#help-pane", Static).update(
            "\n".join(
                [
                    f"{APP_NAME} Shortcuts",
                    "",
                    "g dashboard      t tasks          i statistics      , settings",
                    "a add task       e edit           d delete          x complete",
                    "/ search         f filter         s pomodoro        p pause/resume",
                    "m toggle focus   b blocked sites  ? help            q quit",
                    "",
                    "Waybar integration",
                    "Left click opens the TUI.",
                    "Right click toggles pomodoro.",
                    "Middle click toggles focus mode.",
                ]
            )
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        cursor_row = max(0, table.cursor_row)
        if table.id in {"dashboard-tasks", "tasks-table"}:
            row_map = self._task_row_map.get(str(table.id), [])
            if cursor_row < len(row_map):
                self.selected_task_id = row_map[cursor_row]
                self._update_task_detail("#dashboard-detail")
                self._update_task_detail("#task-detail")
        elif table.id == "focus-sites-table":
            if cursor_row < len(self._site_row_map):
                self.selected_focus_domain = self._site_row_map[cursor_row]
        elif table.id == "settings-table" and cursor_row < len(self._setting_row_map):
            self.selected_setting_key = self._setting_row_map[cursor_row]

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "task-search":
            self.filters.search = event.value.strip()
            self.show_view("tasks")
            self.refresh_data()

    def show_view(self, view_id: str) -> None:
        tabs = self.query_one("#views", TabbedContent)
        tabs.active = view_id

    def action_show_dashboard(self) -> None:
        self.show_view("dashboard")

    def action_show_tasks(self) -> None:
        self.show_view("tasks")
        self.query_one("#task-search", Input).focus()

    def action_show_statistics(self) -> None:
        self.show_view("statistics")

    def action_show_settings(self) -> None:
        self.show_view("settings")

    def action_show_help(self) -> None:
        self.show_view("help")

    def action_app_quit(self) -> None:
        self.exit()

    def action_add_task(self) -> None:
        self.push_screen(QuickAddTaskScreen(), self._handle_add_task)

    def _handle_add_task(self, result: str | None) -> None:
        if not isinstance(result, str) or not result.strip():
            return
        self.services.tasks.add_task(result.strip())
        self.show_view("tasks")
        self.refresh_data()

    def action_edit_selected(self) -> None:
        active = self.query_one("#views", TabbedContent).active
        if active == "settings":
            self._edit_selected_setting()
            return
        if active == "focus":
            self.action_show_blocked_sites()
            return
        task = self._get_task_by_selection()
        if not task:
            return
        self.push_screen(TaskEditorScreen(task=task), lambda result: self._handle_edit_task(task.id, result))

    def _handle_edit_task(self, task_id: int, result: TaskEditorResult | None) -> None:
        if not isinstance(result, TaskEditorResult) or not result.title:
            return
        self.services.tasks.update_task(
            task_id,
            title=result.title,
            description=result.description,
            priority=result.priority,
            tags=result.tags,
            estimated_minutes=result.estimate,
            due_at=result.due,
        )
        self.refresh_data()

    def _edit_selected_setting(self) -> None:
        if not self.selected_setting_key:
            return
        current = str(self.services.settings.get(self.selected_setting_key))
        key = self.selected_setting_key
        self.push_screen(
            SettingEditScreen(key, current),
            lambda result: self._handle_setting_edit(key, result),
        )

    def _handle_setting_edit(self, key: str, result: str | None) -> None:
        if not isinstance(result, str):
            return
        lowered = result.lower()
        value: Any
        if lowered in {"true", "false"}:
            value = lowered == "true"
        elif result.isdigit():
            value = int(result)
        else:
            value = result
        self.services.settings.set(key, value)
        self.refresh_data()

    def action_delete_selected(self) -> None:
        task = self._get_task_by_selection()
        if not task:
            return
        self.push_screen(
            ConfirmScreen("Delete Task", f"Delete “{task.title}”? This cannot be undone."),
            lambda confirmed: self._handle_delete_confirm(task.id, confirmed),
        )

    def _handle_delete_confirm(self, task_id: int, confirmed: bool) -> None:
        if not confirmed:
            return
        self.services.tasks.delete_task(task_id)
        self.selected_task_id = None
        self.refresh_data()

    def action_complete_selected(self) -> None:
        task = self._get_task_by_selection()
        if not task:
            return
        self.services.tasks.complete_task(
            task.id,
            notifications_enabled=self.services.settings.get("notifications_enabled"),
        )
        self.refresh_data()

    def action_search_tasks(self) -> None:
        self.push_screen(SearchScreen(self.filters.search), self._handle_search_result)

    def _handle_search_result(self, result: str | None) -> None:
        if result is None:
            return
        self.filters.search = result
        self.show_view("tasks")
        self.refresh_data()

    def action_filter_tasks(self) -> None:
        self.push_screen(FilterScreen(self.filters), self._handle_filter_result)

    def _handle_filter_result(self, result: TaskFilters | None) -> None:
        if not isinstance(result, TaskFilters):
            return
        result.search = self.filters.search
        self.filters = result
        self.show_view("tasks")
        self.refresh_data()

    def action_toggle_pomodoro(self) -> None:
        snapshot = self.services.pomodoro.status()
        if snapshot.phase == SessionPhase.IDLE:
            task = self._get_task_by_selection()
            self.services.pomodoro.start(task_id=task.id if task else None)
        else:
            self.services.pomodoro.stop(reason="stopped from TUI")
        self.refresh_data()

    def action_pause_resume(self) -> None:
        snapshot = self.services.pomodoro.status()
        if snapshot.phase == SessionPhase.RUNNING:
            self.services.pomodoro.pause()
        elif snapshot.phase == SessionPhase.PAUSED:
            self.services.pomodoro.resume()
        self.refresh_data()

    def action_toggle_focus(self) -> None:
        from ..exceptions import FocusModeError

        try:
            with self.suspend():
                focus = self.services.focus.status()
                if focus.active:
                    self.services.focus.stop(force=False)
                else:
                    pomodoro = self.services.pomodoro.status()
                    minutes = None
                    if pomodoro.phase == SessionPhase.RUNNING and pomodoro.session_type == SessionType.WORK:
                        minutes = max(1, math.ceil(pomodoro.remaining_seconds / 60))
                    self.services.focus.start(minutes=minutes)
        except FocusModeError as exc:
            self.notify(str(exc), title="Focus Mode", severity="error")
        self.show_view("focus")
        self.refresh_data()

    def action_show_blocked_sites(self) -> None:
        self.show_view("focus")
        self.push_screen(
            BlockedSitesScreen(self.selected_focus_domain),
            lambda _: self.refresh_data(),
        )
