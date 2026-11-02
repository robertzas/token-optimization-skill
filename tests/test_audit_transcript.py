import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_transcript as at  # noqa: E402


def assistant(usage, tool_calls=()):
    content = [{"type": "tool_use", "name": name, "input": arguments}
               for name, arguments in tool_calls]
    return {"type": "assistant", "message": {"role": "assistant", "usage": usage, "content": content}}


def user(text="go"):
    return {"type": "user", "message": {"role": "user", "content": text}}


def transcript():
    return "\n".join(json.dumps(line) for line in (
        user(),
        assistant({"input_tokens": 1000, "cache_creation_input_tokens": 2000,
                   "cache_read_input_tokens": 3000, "output_tokens": 500},
                  [("Read", {"file_path": "src/a.py"})]),
        assistant({"input_tokens": 0, "cache_creation_input_tokens": 0,
                   "cache_read_input_tokens": 6000, "output_tokens": 100},
                  [("Read", {"file_path": "src/a.py"}), ("Bash", {"command": "pytest -q"})]),
        user(),
        assistant({"input_tokens": 500, "cache_creation_input_tokens": 0,
                   "cache_read_input_tokens": 5500, "output_tokens": 50},
                  [("Read", {"file_path": "src/b.py"})]),
        user(),
    ))


class Parse(unittest.TestCase):
    def test_totals_requests_usage_and_tools(self):
        audit = at.parse(transcript())
        self.assertEqual(audit.requests, 3)
        self.assertEqual(audit.usage.input, 1500)
        self.assertEqual(audit.usage.creation, 2000)
        self.assertEqual(audit.usage.read, 14500)
        self.assertEqual(audit.usage.output, 650)
        self.assertEqual(audit.usage.prompt, 18000)
        self.assertEqual(audit.tools["Read"], 3)
        self.assertEqual(audit.tools["Bash"], 1)
        self.assertEqual(audit.files["src/a.py"], 2)
        self.assertEqual(audit.files["src/b.py"], 1)
        self.assertEqual(audit.turns, 3)
        self.assertEqual(audit.max_turn_tools, 3)

    def test_accepts_top_level_usage_and_cache_creation_dict(self):
        line = json.dumps({"type": "assistant", "usage": {
            "input_tokens": 10, "cache_creation": {"ephemeral_5m_input_tokens": 20,
                                                   "ephemeral_1h_input_tokens": 30},
            "cache_read_input_tokens": 40, "output_tokens": 50}})
        usage = at.usage_of(json.loads(line))
        self.assertEqual(usage.creation, 50)
        self.assertEqual(usage.prompt, 100)

    def test_bad_lines_do_not_crash(self):
        audit = at.parse("not json\n" + transcript() + "\n{broken")
        self.assertEqual(audit.requests, 3)


class Cost(unittest.TestCase):
    def test_cost_uses_the_cache_multipliers(self):
        usage = at.Usage(input=1500, creation=2000, read=14500, output=650)
        # 1500 + 2*2000 + 0.05*14500 + 5*650 = 9475 equivalents at $4/M
        self.assertAlmostEqual(at.cost_of(usage, "opus-5.5", "1h"), 0.0379, places=4)

    def test_render_names_the_leaks(self):
        out = at.render(at.parse(transcript()), "opus-5.5", "1h", 10)
        self.assertIn("3 requests", out)
        self.assertIn("81% cached", out)
        self.assertIn("files read: 2 unique · 1 re-reads", out)
        self.assertIn("2× src/a.py", out)
        self.assertIn("$0.04 at opus-5.5", out)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = at.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(transcript(), encoding="utf-8")
            code, out, _ = self.run_cli(str(path), "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["requests"], 3)
            self.assertEqual(data["usage"]["read"], 14500)
            self.assertAlmostEqual(data["cache_hit"], 14500 / 18000)
            self.assertAlmostEqual(data["cost_usd"], 0.0379, places=4)

    def test_budget_and_missing_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(transcript(), encoding="utf-8")
            self.assertEqual(self.run_cli(str(path), "--max-cost", "0.01")[0], 1)
            empty = Path(tmp) / "empty.jsonl"
            empty.write_text("", encoding="utf-8")
            self.assertEqual(self.run_cli(str(empty))[0], 1)


if __name__ == "__main__":
    unittest.main()
