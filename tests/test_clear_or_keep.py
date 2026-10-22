import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import clear_or_keep as ck  # noqa: E402

OPUS_55_1H = {"read_mult": 0.05, "write_mult": 2.0}


class ParseTokens(unittest.TestCase):
    def test_suffixes_and_separators(self):
        self.assertEqual(ck.parse_tokens("60k"), 60_000)
        self.assertEqual(ck.parse_tokens("60K"), 60_000)
        self.assertEqual(ck.parse_tokens("1.5M"), 1_500_000)
        self.assertEqual(ck.parse_tokens("25,000"), 25_000)
        self.assertEqual(ck.parse_tokens(" 25000 "), 25_000)

    def test_rejects_garbage(self):
        for text in ("lots", "-5k", "", "5x"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ck.parse_tokens(text)


class FormatTokens(unittest.TestCase):
    def test_compact_forms(self):
        cases = {950: "950", 7_500: "7.5k", 60_000: "60k", 350_000: "350k",
                 999_499: "999k", 999_500: "1M", 1_500_000: "1.5M"}
        for n, text in cases.items():
            with self.subTest(n=n):
                self.assertEqual(ck.fmt_tokens(n), text)


class Decide(unittest.TestCase):
    def test_full_work_package_with_unused_context_clears(self):
        v = ck.decide(60_000, 25_000, 100, **OPUS_55_1H)
        self.assertTrue(v.clear)
        self.assertAlmostEqual(v.keep_cost, 300_000)
        self.assertAlmostEqual(v.clear_cost, 50_000)
        self.assertAlmostEqual(v.ratio, 40)

    def test_short_follow_up_keeps(self):
        self.assertFalse(ck.decide(60_000, 25_000, 10, **OPUS_55_1H).clear)

    def test_skill_table_thresholds(self):
        # Ratio 40 and R = 25k give 100k at 10 requests, 20k at 50 and 10k at 100.
        for requests, threshold in ((10, 100_000), (50, 20_000), (100, 10_000)):
            with self.subTest(requests=requests):
                self.assertFalse(ck.decide(threshold * 0.9, 25_000, requests, **OPUS_55_1H).clear)
                self.assertTrue(ck.decide(threshold * 1.1, 25_000, requests, **OPUS_55_1H).clear)

    def test_break_even(self):
        self.assertAlmostEqual(ck.decide(50_000, 25_000, 100, **OPUS_55_1H).break_even_requests, 20.0)

    def test_nothing_unused_keeps(self):
        v = ck.decide(0, 25_000, 100, **OPUS_55_1H)
        self.assertFalse(v.clear)
        self.assertIsNone(v.break_even_requests)

    def test_cold_cache_clears_even_for_short_work(self):
        v = ck.decide(30_000, 25_000, 5, cold=True, **OPUS_55_1H)
        self.assertTrue(v.clear)
        self.assertAlmostEqual(v.keep_cost, 2 * 30_000 + 0.05 * 30_000 * 5)
        self.assertAlmostEqual(v.clear_cost, 2 * 10_000)

    def test_rejects_negative_and_zero_prices(self):
        with self.assertRaises(ValueError):
            ck.decide(-1, 25_000, 10, **OPUS_55_1H)
        with self.assertRaises(ValueError):
            ck.decide(1_000, 25_000, 10, read_mult=0, write_mult=2.0)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / "clear_or_keep.py"), *args],
                                capture_output=True, encoding="utf-8", check=True)
        return result.stdout

    def test_json_verdict(self):
        data = json.loads(self.run_cli("--unused", "60k", "--requests", "100", "--json"))
        self.assertEqual(data["verdict"], "clear")
        self.assertEqual(data["ratio"], 40)
        self.assertAlmostEqual(data["keep_usd"], 1.2)
        self.assertIn("/clear recommended", data["checkpoint_line"])

    def test_keep_line_names_next_task_and_ttl(self):
        out = self.run_cli("--unused", "5k", "--requests", "10", "--next", "M0.3 — Web skeleton")
        self.assertIn("keep context", out)
        self.assertIn("Next: M0.3 — Web skeleton.", out)
        self.assertIn("within 1 h", out)

    def test_model_and_ttl_change_the_ratio(self):
        data = json.loads(self.run_cli("--unused", "10k", "--requests", "10",
                                       "--model", "opus-5", "--ttl", "5m", "--json"))
        self.assertAlmostEqual(data["ratio"], 12.5)

    def test_bad_input_exits_with_usage_error(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "clear_or_keep.py"), "--unused", "lots"],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a token count", result.stderr)


if __name__ == "__main__":
    unittest.main()
