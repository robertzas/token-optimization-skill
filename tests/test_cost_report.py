import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cost_report as cr  # noqa: E402

HEADER = ("| Date | WP | Model | Requests | Prompt tokens | Cached | Output | Cost | Decision |\n"
          "|---|---|---|---|---|---|---|---|---|\n")


def ledger(costs):
    rows = [HEADER]
    for index, cost in enumerate(costs, start=1):
        rows.append(f"| 2026-10-{index:02d} | M{index} | opus-5.5 | {index * 10} | 100k | 50% | 1k | "
                    f"${cost:.2f} | /clear |\n")
    return "".join(rows)


class Parse(unittest.TestCase):
    def test_reads_the_ledger_columns(self):
        rows = cr.parse_table(ledger([1.0, 2.0]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].wp, "M1")
        self.assertEqual(rows[0].cost, 1.0)
        self.assertEqual(rows[0].requests, 10)
        self.assertEqual(rows[0].prompt, 100_000)
        self.assertEqual(rows[0].cached, 50.0)
        self.assertEqual(rows[0].decision, "/clear")

    def test_skips_the_separator_and_placeholders(self):
        text = HEADER + "| <date> | <WP> | <model> | 1 | 1k | 50% | 1k | $<n> | <decision> |\n"
        self.assertEqual(cr.parse_table(text), [])

    def test_missing_table_returns_nothing(self):
        self.assertEqual(cr.parse_table("# Cost\n\nNo table yet.\n"), [])


class Summary(unittest.TestCase):
    def setUp(self):
        # 12 evenly spaced costs plus one outlier; median 2.20, p75 2.80.
        self.rows = cr.parse_table(ledger([round(1.0 + 0.2 * i, 1) for i in range(12)] + [5.0]))

    def test_median_p75_and_total(self):
        data = cr.summarize(self.rows)
        self.assertAlmostEqual(data["median"], 2.2)
        self.assertAlmostEqual(data["p75"], 2.8)
        self.assertAlmostEqual(data["total"], 30.2)

    def test_outlier_is_flagged(self):
        data = cr.summarize(self.rows)
        self.assertEqual([row.wp for row in data["outliers"]], ["M13"])

    def test_render_names_the_signal(self):
        out = cr.render(cr.summarize(self.rows), Path("docs/COST.md"))
        self.assertIn("13 WPs", out)
        self.assertIn("median $2.20/WP", out)
        self.assertIn("M13 $5.00 (2.3×)", out)
        self.assertIn("Outliers (>2× median)", out)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cr.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "COST.md"
            path.write_text(ledger([1.0, 2.0, 3.0]), encoding="utf-8")
            code, out, _ = self.run_cli("--path", str(path), "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["count"], 3)
            self.assertAlmostEqual(data["median"], 2.0)
            self.assertEqual(len(data["rows"]), 3)

    def test_budget_fails_above_the_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "COST.md"
            path.write_text(ledger([2.0, 2.0, 2.0]), encoding="utf-8")
            code, _, err = self.run_cli("--path", str(path), "--max-median", "1.00")
            self.assertEqual(code, 1)
            self.assertIn("exceeds", err)

    def test_missing_or_empty_ledger_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "COST.md"
            path.write_text("# Cost\n", encoding="utf-8")
            self.assertEqual(self.run_cli("--path", str(path))[0], 1)
            self.assertEqual(self.run_cli("--path", str(Path(tmp) / "nope.md"))[0], 1)


if __name__ == "__main__":
    unittest.main()
