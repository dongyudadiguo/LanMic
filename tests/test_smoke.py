"""Stdlib-only smoke checks. No microphone, no pip extras."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SmokeTests(unittest.TestCase):
    def test_version(self):
        from lanmic import __version__
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+")

    def test_python_files_parse(self):
        files = list((ROOT / "lanmic").glob("*.py"))
        files += list((ROOT / "tests").glob("*.py"))
        self.assertGreaterEqual(len(files), 6)
        for path in files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_web_pages_exist_and_are_js(self):
        phone = (ROOT / "web" / "phone.html").read_text(encoding="utf-8")
        host = (ROOT / "web" / "host.html").read_text(encoding="utf-8")
        self.assertIn("getUserMedia", phone)
        self.assertIn("RTCPeerConnection", phone)
        self.assertNotIn("let stream = None", phone)
        self.assertIn("/api/offer", phone)
        self.assertIn("Win+H", host)
        self.assertIn("/api/status", host)

    def test_license_is_mit(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", text)


if __name__ == "__main__":
    unittest.main()
