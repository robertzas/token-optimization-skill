import contextlib
import io
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import prices as pc  # noqa: E402


class Data(unittest.TestCase):
    def test_every_model_has_the_same_derived_multipliers(self):
        for name, entry in pc.PRICES["models"].items():
            with self.subTest(model=name):
                self.assertAlmostEqual(entry["write_5m"], entry["input"] * 1.25, places=6)
                self.assertAlmostEqual(entry["write_1h"], entry["input"] * 2.0, places=6)
                self.assertAlmostEqual(entry["output"], entry["input"] * 5.0, places=6)
                self.assertAlmostEqual(entry["read"] / entry["input"],
                                       pc.MODELS[name][0], places=6)

    def test_models_tuple_is_the_calculator_contract(self):
        for name, (read_mult, input_price) in pc.MODELS.items():
            with self.subTest(model=name):
                self.assertGreater(read_mult, 0)
                self.assertGreater(input_price, 0)

    def test_ttl_multipliers_are_the_documented_ones(self):
        self.assertEqual(pc.WRITE_MULTIPLIERS, {"5m": 1.25, "1h": 2.0})


class Table(unittest.TestCase):
    def test_table_has_every_model_and_the_expected_columns(self):
        text = pc.table()
        self.assertTrue(text.startswith("| Model | Input |"))
        for entry in pc.PRICES["models"].values():
            self.assertIn(f"| {entry['label']} |", text)
        self.assertEqual(len(text.splitlines()), len(pc.PRICES["models"]) + 2)

    def test_doc_table_is_fresh(self):
        fresh, message = pc.check()
        self.assertTrue(fresh, message)

    def test_check_cli_passes(self):
        self.assertEqual(pc.main(["--check"]), 0)

    def test_table_cli_prints_the_table(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(pc.main(["--table"]), 0)
        self.assertEqual(out.getvalue().strip(), pc.table())


if __name__ == "__main__":
    unittest.main()
