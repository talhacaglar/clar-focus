from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.install_omarchy_bar import update_shell_config, write_atomic

MODULE = {
    "id": "clarfocus",
    "type": "command",
    "exec": "~/.local/bin/clar-focus-bar status",
    "interval": 2,
    "onClick": "~/.local/bin/clar-focus-bar open",
    "onRightClick": "~/.local/bin/clar-focus-bar toggle-pomodoro",
    "onMiddleClick": "~/.local/bin/clar-focus-bar toggle-focus",
}


class OmarchyBarInstallTest(unittest.TestCase):
    def test_updates_existing_widget_without_touching_layout(self) -> None:
        config = {
            "version": 1,
            "bar": {
                "position": "top",
                "layout": {
                    "left": [{"id": "clar.workspaces"}],
                    "center": [
                        {"id": "clarfocus", "type": "command", "exec": "old-waybar-name"},
                        {"id": "omarchy.indicators"},
                    ],
                    "right": [{"id": "omarchy.tray"}],
                },
            },
        }

        self.assertTrue(update_shell_config(config, MODULE))
        self.assertEqual(config["bar"]["position"], "top")
        self.assertEqual(config["bar"]["layout"]["left"], [{"id": "clar.workspaces"}])
        self.assertEqual(config["bar"]["layout"]["right"], [{"id": "omarchy.tray"}])
        self.assertEqual(config["bar"]["layout"]["center"][0], MODULE)
        self.assertFalse(update_shell_config(config, MODULE))

    def test_inserts_before_indicators_and_writes_valid_json(self) -> None:
        config = {
            "version": 1,
            "bar": {"layout": {"center": [{"id": "omarchy.indicators"}]}},
        }
        self.assertTrue(update_shell_config(config, MODULE))
        ids = [item["id"] for item in config["bar"]["layout"]["center"]]
        self.assertEqual(ids, ["clarfocus", "omarchy.indicators"])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "shell.json"
            write_atomic(path, config)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), config)


if __name__ == "__main__":
    unittest.main()
