"""CLI entrypoint."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from typing import Any

from .bootstrap import build_services
from .exceptions import FocusModeError, OmarchyFocusError, PomodoroError, TaskNotFoundError
from .models import TaskFilters, TaskPriority, TaskStatus
from .paths import APP_NAME
from .utils import (
    acquire_tui_lock,
    clear_tui_window_state,
    focus_existing_tui,
    format_datetime,
    minutes_to_label,
    seconds_to_clock,
)
from .waybar import render_waybar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clar-focus", description=f"{APP_NAME} tasklist + pomodoro + focus manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("tui")
    subparsers.add_parser("raise")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--json", action="store_true")

    waybar_parser = subparsers.add_parser("waybar")
    waybar_parser.add_argument("--plain", action="store_true")

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--task-id", type=int)
    start_parser.add_argument("--minutes", type=int)
    start_parser.add_argument("--focus", action="store_true")
    start_parser.add_argument("--strict", action="store_true")

    subparsers.add_parser("pause")
    subparsers.add_parser("resume")
    subparsers.add_parser("stop")
    subparsers.add_parser("toggle")

    add_task_parser = subparsers.add_parser("add-task")
    add_task_parser.add_argument("title")
    add_task_parser.add_argument("--description", default="")
    add_task_parser.add_argument("--priority", choices=[item.value for item in TaskPriority], default="medium")
    add_task_parser.add_argument("--tags", default="")
    add_task_parser.add_argument("--estimate", type=int)
    add_task_parser.add_argument("--due")

    stats_parser = subparsers.add_parser("stats")
    stats_parser.add_argument("--json", action="store_true")

    tasks_parser = subparsers.add_parser("tasks")
    tasks_subparsers = tasks_parser.add_subparsers(dest="tasks_command", required=True)

    tasks_list = tasks_subparsers.add_parser("list")
    tasks_list.add_argument("--search", default="")
    tasks_list.add_argument("--status", choices=[item.value for item in TaskStatus])
    tasks_list.add_argument("--today", action="store_true")
    tasks_list.add_argument("--completed", action="store_true")
    tasks_list.add_argument("--sort", default="updated_desc")

    tasks_done = tasks_subparsers.add_parser("done")
    tasks_done.add_argument("task_id", type=int)

    tasks_delete = tasks_subparsers.add_parser("delete")
    tasks_delete.add_argument("task_id", type=int)

    tasks_edit = tasks_subparsers.add_parser("edit")
    tasks_edit.add_argument("task_id", type=int)
    tasks_edit.add_argument("--title")
    tasks_edit.add_argument("--description")
    tasks_edit.add_argument("--priority", choices=[item.value for item in TaskPriority])
    tasks_edit.add_argument("--tags")
    tasks_edit.add_argument("--estimate", type=int)
    tasks_edit.add_argument("--due")
    tasks_edit.add_argument("--status", choices=[item.value for item in TaskStatus])

    focus_parser = subparsers.add_parser("focus")
    focus_subparsers = focus_parser.add_subparsers(dest="focus_command", required=True)

    focus_on = focus_subparsers.add_parser("on")
    focus_on.add_argument("--minutes", type=int)
    focus_on.add_argument("--strict", action="store_true")
    focus_on.add_argument("--site", action="append", default=[])

    focus_off = focus_subparsers.add_parser("off")
    focus_off.add_argument("--force", action="store_true")

    focus_status = focus_subparsers.add_parser("status")
    focus_status.add_argument("--json", action="store_true")

    focus_subparsers.add_parser("recover")

    focus_add_site = focus_subparsers.add_parser("add-site")
    focus_add_site.add_argument("domain")
    focus_add_site.add_argument("--disabled", action="store_true")

    focus_edit_site = focus_subparsers.add_parser("edit-site")
    focus_edit_site.add_argument("domain")
    focus_edit_site.add_argument("--new-domain")
    focus_edit_site.add_argument("--enabled", choices=["true", "false"])

    focus_enable_site = focus_subparsers.add_parser("enable-site")
    focus_enable_site.add_argument("domain")

    focus_disable_site = focus_subparsers.add_parser("disable-site")
    focus_disable_site.add_argument("domain")

    focus_remove_site = focus_subparsers.add_parser("remove-site")
    focus_remove_site.add_argument("domain")

    settings_parser = subparsers.add_parser("settings")
    settings_subparsers = settings_parser.add_subparsers(dest="settings_command", required=True)

    settings_show = settings_subparsers.add_parser("show")
    settings_show.add_argument("--json", action="store_true")

    settings_set = settings_subparsers.add_parser("set")
    settings_set.add_argument("key")
    settings_set.add_argument("value")

    return parser


def _launch_tui() -> int:
    try:
        from .tui.app import OmarchyFocusApp
    except ImportError as exc:
        print(
            "Textual is not installed. Install dependencies with `python -m pip install -e .` first.",
            file=sys.stderr,
        )
        if "--debug-import" in sys.argv:
            raise exc
        return 1

    lock_handle = acquire_tui_lock()
    if lock_handle is None:
        focus_existing_tui()
        return 0

    app = OmarchyFocusApp()
    try:
        app.run()
    finally:
        clear_tui_window_state()
        lock_handle.close()
    return 0


def _render_status(services: Any, *, as_json: bool = False) -> str:
    services.sync()
    pomodoro = services.pomodoro.snapshot()
    pending_break = services.pomodoro.pending_break()
    focus = services.focus.snapshot()
    pending = services.tasks.count_pending()
    stats = services.stats.snapshot()
    payload = {
        "pending_tasks": pending,
        "pomodoro": {
            "phase": pomodoro.phase.value,
            "type": pomodoro.session_type.value if pomodoro.session_type else None,
            "remaining_seconds": pomodoro.remaining_seconds,
            "task_title": pomodoro.task_title,
        },
        "pending_break": pending_break,
        "focus": {
            "active": focus.active,
            "strict": focus.strict_mode,
            "sites": list(focus.blocked_sites),
            "ends_at": focus.ends_at.isoformat() if focus.ends_at else None,
        },
        "stats": {
            "today_pomodoros": stats.today_completed_pomodoros,
            "today_focus_minutes": stats.today_focus_minutes,
        },
    }
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if pomodoro.phase.value == "running" and pomodoro.session_type:
        session_label = "Pomodoro" if pomodoro.session_type.value == "work" else "Break"
        task_suffix = f" | {pomodoro.task_title}" if pomodoro.task_title else ""
        return f"{session_label}: {seconds_to_clock(pomodoro.remaining_seconds)} left{task_suffix}"
    if pending_break:
        minutes = int(pending_break.get("minutes", 10))
        return f"Pomodoro complete | Break ready: {minutes}m"
    if focus.active:
        strict = " | strict" if focus.strict_mode else ""
        return f"Focus: ON{strict} | {len(focus.blocked_sites)} site(s) blocked"
    return f"Idle | {pending} pending task(s)"


def _coerce_setting(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.isdigit():
        return int(value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        return _launch_tui()

    services = build_services()

    try:
        if args.command == "tui":
            return _launch_tui()
        if args.command == "raise":
            return 0 if focus_existing_tui() else 1
        if args.command == "status":
            print(_render_status(services, as_json=args.json))
            return 0
        if args.command == "waybar":
            print(render_waybar(services, json_mode=not args.plain))
            return 0
        if args.command == "start":
            snapshot = services.pomodoro.start(
                task_id=args.task_id,
                minutes=args.minutes,
                auto_focus=args.focus,
                strict_focus=args.strict,
            )
            print(f"Started {snapshot.session_type.value} for {seconds_to_clock(snapshot.remaining_seconds)}")
            return 0
        if args.command == "pause":
            snapshot = services.pomodoro.pause()
            print(f"Paused at {seconds_to_clock(snapshot.remaining_seconds)}")
            return 0
        if args.command == "resume":
            snapshot = services.pomodoro.resume()
            print(f"Resumed {snapshot.session_type.value}")
            return 0
        if args.command == "stop":
            services.pomodoro.stop()
            print("Pomodoro stopped")
            return 0
        if args.command == "toggle":
            snapshot = services.pomodoro.toggle()
            print(snapshot.phase.value)
            return 0
        if args.command == "add-task":
            task = services.tasks.add_task(
                args.title,
                description=args.description,
                priority=args.priority,
                tags=args.tags,
                estimated_minutes=args.estimate,
                due_at=args.due,
            )
            print(f"Created task #{task.id}: {task.title}")
            return 0
        if args.command == "stats":
            stats = services.stats.snapshot()
            if args.json:
                print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))
            else:
                print(
                    "\n".join(
                        [
                            f"Today: {stats.today_completed_pomodoros} pomodoros / {stats.today_focus_minutes}m",
                            f"Week focus: {stats.week_focus_minutes}m",
                            f"Completed tasks today: {stats.completed_tasks_today}",
                            f"Streak: {stats.streak_days} day(s)",
                        ]
                    )
                )
            return 0
        if args.command == "tasks":
            if args.tasks_command == "list":
                filters = TaskFilters(
                    search=args.search,
                    status=TaskStatus(args.status) if args.status else None,
                    today=args.today,
                    completed=args.completed,
                    sort_by=args.sort,
                )
                tasks = services.tasks.list_tasks(filters)
                if not tasks:
                    print("No tasks found.")
                    return 0
                for task in tasks:
                    tags = f" [{' '.join('#' + tag for tag in task.tags)}]" if task.tags else ""
                    due = f" | due {format_datetime(task.due_at)}" if task.due_at else ""
                    estimate = f" | est {minutes_to_label(task.estimated_minutes)}" if task.estimated_minutes else ""
                    print(
                        f"{task.id:>3}  {task.priority.value:<6}  {task.status.value:<11}  {task.title}{tags}{estimate}{due}"
                    )
                return 0
            if args.tasks_command == "done":
                task = services.tasks.complete_task(
                    args.task_id,
                    notifications_enabled=services.settings.get("notifications_enabled"),
                )
                print(f"Completed: {task.title}")
                return 0
            if args.tasks_command == "delete":
                services.tasks.delete_task(args.task_id)
                print(f"Deleted task #{args.task_id}")
                return 0
            if args.tasks_command == "edit":
                task = services.tasks.update_task(
                    args.task_id,
                    title=args.title,
                    description=args.description,
                    priority=args.priority,
                    tags=args.tags,
                    estimated_minutes=args.estimate,
                    due_at=args.due,
                    status=args.status,
                )
                print(f"Updated task #{task.id}: {task.title}")
                return 0
        if args.command == "focus":
            if args.focus_command == "on":
                snapshot = services.focus.start(
                    minutes=args.minutes,
                    strict_mode=args.strict,
                    sites=args.site or None,
                )
                print(f"Focus mode active with {len(snapshot.blocked_sites)} site(s)")
                return 0
            if args.focus_command == "off":
                services.focus.stop(force=args.force)
                print("Focus mode disabled")
                return 0
            if args.focus_command == "status":
                snapshot = services.focus.status()
                if args.json:
                    print(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, default=str))
                else:
                    if snapshot.active:
                        print(
                            f"Focus ON | strict={snapshot.strict_mode} | blocked={len(snapshot.blocked_sites)}"
                        )
                    else:
                        print("Focus OFF")
                return 0
            if args.focus_command == "recover":
                snapshot = services.focus.recover()
                print("recovered" if snapshot.active else "idle")
                return 0
            if args.focus_command == "add-site":
                services.focus.add_site(args.domain, enabled=not args.disabled)
                print(f"Added blocked site: {args.domain}")
                return 0
            if args.focus_command == "edit-site":
                enabled = None
                if args.enabled is not None:
                    enabled = args.enabled == "true"
                updated = services.focus.update_site(
                    args.domain,
                    new_domain=args.new_domain,
                    enabled=enabled,
                )
                print(f"Updated blocked site: {updated}")
                return 0
            if args.focus_command == "enable-site":
                services.focus.toggle_site(args.domain, True)
                print(f"Enabled blocked site: {args.domain}")
                return 0
            if args.focus_command == "disable-site":
                services.focus.toggle_site(args.domain, False)
                print(f"Disabled blocked site: {args.domain}")
                return 0
            if args.focus_command == "remove-site":
                services.focus.remove_site(args.domain)
                print(f"Removed blocked site: {args.domain}")
                return 0
        if args.command == "settings":
            if args.settings_command == "show":
                values = services.settings.all()
                if args.json:
                    print(json.dumps(values, ensure_ascii=False, indent=2))
                else:
                    for key, value in values.items():
                        print(f"{key}={value}")
                return 0
            if args.settings_command == "set":
                services.settings.set(args.key, _coerce_setting(args.value))
                print(f"Updated setting: {args.key}")
                return 0
    except (OmarchyFocusError, TaskNotFoundError, PomodoroError, FocusModeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
