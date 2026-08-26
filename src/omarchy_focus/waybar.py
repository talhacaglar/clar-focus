"""Deprecated Waybar-compatible aliases.

Use :mod:`omarchy_focus.bar` for new integrations.
"""

from .bar import build_bar_payload, render_bar

build_waybar_payload = build_bar_payload
render_waybar = render_bar

__all__ = ["build_waybar_payload", "render_waybar"]
