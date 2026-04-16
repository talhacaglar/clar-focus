"""Waybar integration helpers."""

from __future__ import annotations

import json

from .bootstrap import ServiceContainer
from .models import SessionPhase, SessionType
from .paths import APP_NAME
from .utils import progress_bar, remaining_seconds, seconds_to_clock


def build_waybar_payload(services: ServiceContainer) -> dict[str, object]:
    services.sync()
    pomodoro = services.pomodoro.snapshot()
    pending_break = services.pomodoro.pending_break()
    focus = services.focus.snapshot()
    stats = services.stats.snapshot()
    pending = services.tasks.count_pending()

    if pomodoro.phase == SessionPhase.RUNNING and pomodoro.session_type == SessionType.WORK:
        icon = "󰄉"
        text = f"{icon} {seconds_to_clock(pomodoro.remaining_seconds)}"
        if pomodoro.task_title:
            text += f" · {pomodoro.task_title[:20]}"
        tooltip = "\n".join(
            [
                "Focus Session",
                f"Time left: {seconds_to_clock(pomodoro.remaining_seconds)}",
                f"Task: {pomodoro.task_title or 'Unassigned'}",
                f"Pending tasks: {pending}",
                f"Today: {stats.today_completed_pomodoros} pomodoros · {stats.today_focus_minutes}m",
            ]
        )
        return {"text": text, "tooltip": tooltip, "class": "pomodoro"}

    if pomodoro.phase == SessionPhase.RUNNING and pomodoro.session_type in {SessionType.SHORT_BREAK, SessionType.LONG_BREAK}:
        label = "Long Break" if pomodoro.session_type == SessionType.LONG_BREAK else "Break"
        return {
            "text": f"󰁅 {seconds_to_clock(pomodoro.remaining_seconds)}",
            "tooltip": f"{label}\nTime left: {seconds_to_clock(pomodoro.remaining_seconds)}",
            "class": "break",
        }

    if pomodoro.phase == SessionPhase.PAUSED:
        return {
            "text": f"󰏤 {seconds_to_clock(pomodoro.remaining_seconds)}",
            "tooltip": f"Paused session\nResume from: {pomodoro.task_title or 'Unassigned'}",
            "class": "paused",
        }

    if pending_break:
        minutes = int(pending_break.get("minutes", 10))
        task_title = str(pending_break.get("task_title") or "") or "Unassigned"
        return {
            "text": f"󰁅 {minutes}m?",
            "tooltip": "\n".join(
                [
                    "Pomodoro Complete",
                    f"Break ready: {minutes} minute(s)",
                    f"Task: {task_title}",
                    "Open Clar Focus to confirm the break.",
                ]
            ),
            "class": "break-ready",
        }

    if focus.active:
        strict = " · strict" if focus.strict_mode else ""
        blocked_preview = ", ".join(list(focus.blocked_sites)[:3])
        time_left = seconds_to_clock(remaining_seconds(focus.ends_at)) if focus.ends_at else None
        text = f"󰈈 {time_left}" if time_left else f"󰈈 Focus{strict}"
        tooltip = "\n".join(
            [
                "Focus Mode",
                f"Time left: {time_left or 'manual'}",
                f"Blocked: {len(focus.blocked_sites)} site(s)",
                blocked_preview or "Custom site list is empty",
                f"Pending tasks: {pending}",
            ]
        )
        return {"text": text, "tooltip": tooltip, "class": "focus"}

    next_task = services.tasks.get_next_focus_candidate()
    task_label = next_task.title if next_task else "Idle"
    today_bar = progress_bar(stats.today_focus_minutes, max(stats.week_focus_minutes, 1), width=10)
    tooltip = "\n".join(
        [
            APP_NAME,
            f"Next task: {task_label}",
            f"Pending tasks: {pending}",
            f"Today: {stats.today_completed_pomodoros} pomodoros · {stats.today_focus_minutes}m",
            f"Week: {stats.week_focus_minutes}m",
            today_bar,
        ]
    )
    return {"text": f" {pending}", "tooltip": tooltip, "class": "idle"}


def render_waybar(services: ServiceContainer, *, json_mode: bool = True) -> str:
    payload = build_waybar_payload(services)
    if json_mode:
        return json.dumps(payload, ensure_ascii=False)
    return str(payload["text"])
