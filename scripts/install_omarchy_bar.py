"""Install or update Clar Focus in an Omarchy Shell bar layout."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def update_shell_config(config: dict[str, Any], module: dict[str, Any]) -> bool:
    bar = config.setdefault("bar", {})
    if not isinstance(bar, dict):
        raise ValueError("shell.json: 'bar' must be an object")
    layout = bar.setdefault("layout", {})
    if not isinstance(layout, dict):
        raise ValueError("shell.json: 'bar.layout' must be an object")
    center = layout.setdefault("center", [])
    if not isinstance(center, list):
        raise ValueError("shell.json: 'bar.layout.center' must be a list")

    matches = [index for index, item in enumerate(center) if isinstance(item, dict) and item.get("id") == "clarfocus"]
    if matches:
        first = matches[0]
        changed = center[first] != module or len(matches) > 1
        center[first] = module
        for index in reversed(matches[1:]):
            del center[index]
        return changed

    indicator_index = next(
        (
            index
            for index, item in enumerate(center)
            if isinstance(item, dict) and item.get("id") == "omarchy.indicators"
        ),
        len(center),
    )
    center.insert(indicator_index, module)
    return True


def write_atomic(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: install_omarchy_bar.py SHELL_CONFIG MODULE_JSON", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    module_path = Path(sys.argv[2])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    module = json.loads(module_path.read_text(encoding="utf-8"))
    if update_shell_config(config, module):
        write_atomic(config_path, config)
        print("updated")
    else:
        print("unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
