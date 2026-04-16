from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from omarchy_focus.focus_hosts_helper import apply_blocks, clear_blocks, inspect_hosts_file


class FocusHostsHelperTest(unittest.TestCase):
    def test_apply_and_clear_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hosts_path = Path(tmpdir) / "hosts"
            hosts_path.write_text("127.0.0.1 localhost\n", encoding="utf-8")

            status = apply_blocks(
                hosts_path=hosts_path,
                session_id="abc123",
                sites=["reddit.com"],
                strict=True,
                started_at="2026-04-13T10:00:00+00:00",
                owner="clar",
            )

            self.assertTrue(status.active)
            self.assertEqual(status.session_id, "abc123")
            self.assertEqual(status.sites, ("reddit.com", "www.reddit.com"))
            content = hosts_path.read_text(encoding="utf-8")
            self.assertIn("0.0.0.0 reddit.com www.reddit.com", content)
            self.assertIn("::1 reddit.com www.reddit.com", content)

            inspected = inspect_hosts_file(hosts_path)
            self.assertTrue(inspected.active)
            self.assertTrue(inspected.strict)
            self.assertEqual(inspected.sites, ("reddit.com", "www.reddit.com"))

            cleared = clear_blocks(hosts_path)
            self.assertFalse(cleared.active)
            self.assertNotIn("OMARCHY_FOCUS", hosts_path.read_text(encoding="utf-8"))

    def test_inspect_legacy_ipv4_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hosts_path = Path(tmpdir) / "hosts"
            hosts_path.write_text(
                "\n".join(
                    [
                        "127.0.0.1 localhost",
                        "# >>> OMARCHY_FOCUS START",
                        '# OMARCHY_FOCUS_META {"session_id":"legacy","strict":false,"started_at":"2026-04-13T10:00:00+00:00","owner":"clar"}',
                        "127.0.0.1 reddit.com www.reddit.com",
                        "# <<< OMARCHY_FOCUS END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            status = inspect_hosts_file(hosts_path)
            self.assertTrue(status.active)
            self.assertEqual(status.session_id, "legacy")
            self.assertEqual(status.sites, ("reddit.com", "www.reddit.com"))


if __name__ == "__main__":
    unittest.main()
