import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import guard_read as gr  # noqa: E402


class Decide(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "big.py"
        self.path.write_text("x = 1\n" * 100, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, **arguments):
        return {"tool_name": "Read", "tool_input": {"file_path": str(self.path), **arguments}}

    def test_small_file_is_allowed(self):
        small = Path(self.tmp.name) / "small.py"
        small.write_text("x = 1\n" * 10, encoding="utf-8")
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(small)}}
        self.assertIsNone(gr.decide(payload, max_lines=50))

    def test_large_whole_file_is_denied_with_a_range_hint(self):
        decision = gr.decide(self.payload(), max_lines=50)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("offset/limit", decision["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_range_is_allowed(self):
        self.assertIsNone(gr.decide(self.payload(offset=10, limit=20), max_lines=50))
        self.assertIsNone(gr.decide(self.payload(limit=20), max_lines=50))

    def test_other_tools_and_missing_files_are_allowed(self):
        self.assertIsNone(gr.decide({"tool_name": "Bash", "tool_input": {"command": "ls"}}, max_lines=1))
        payload = self.payload()
        payload["tool_input"]["file_path"] = str(Path(self.tmp.name) / "nope.py")
        self.assertIsNone(gr.decide(payload, max_lines=1))

    def test_binary_is_allowed(self):
        binary = Path(self.tmp.name) / "blob.bin"
        binary.write_bytes(b"\0\x01\x02")
        payload = {"tool_name": "Read", "tool_input": {"file_path": str(binary)}}
        self.assertIsNone(gr.decide(payload, max_lines=1))

    def test_main_prints_only_on_denial(self):
        allowed = io.StringIO()
        with contextlib.redirect_stdout(allowed), \
                contextlib.redirect_stderr(io.StringIO()):
            old = sys.stdin
            sys.stdin = io.StringIO(json.dumps(self.payload()))
            try:
                self.assertEqual(gr.main(["--max-lines", "50"]), 0)
            finally:
                sys.stdin = old
        self.assertIn("permissionDecision", allowed.getvalue())

        quiet = io.StringIO()
        with contextlib.redirect_stdout(quiet):
            old = sys.stdin
            sys.stdin = io.StringIO(json.dumps(self.payload(offset=1, limit=10)))
            try:
                self.assertEqual(gr.main(["--max-lines", "50"]), 0)
            finally:
                sys.stdin = old
        self.assertEqual(quiet.getvalue(), "")

    def test_invalid_json_is_allowed(self):
        old = sys.stdin
        sys.stdin = io.StringIO("not json")
        try:
            self.assertEqual(gr.main([]), 0)
        finally:
            sys.stdin = old


if __name__ == "__main__":
    unittest.main()
