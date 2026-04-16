"""Desktop notifications."""

from __future__ import annotations

import shutil
import subprocess

from .paths import APP_NAME


def notify(title: str, body: str = "", *, urgency: str = "normal", enabled: bool = True) -> None:
    if not enabled or not shutil.which("notify-send"):
        return
    subprocess.run(
        ["notify-send", "-a", APP_NAME, "-u", urgency, title, body],
        check=False,
        capture_output=True,
    )
