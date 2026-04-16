"""Compatibility entrypoints."""

from __future__ import annotations

import sys

from .cli import main as cli_main


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "on":
        return cli_main(["focus", "on"])
    if args[0] in {"off", "status"}:
        return cli_main(["focus", args[0]])
    return cli_main(args)


def indicator_main() -> int:
    return cli_main(["waybar"])
