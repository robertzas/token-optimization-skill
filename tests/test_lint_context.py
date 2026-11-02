import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gen_map as gm  # noqa: E402
import lint_context as lc  # noqa: E402


class Lint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "AGENTS.md").write_text(
            "# Project\n\n| Need | Read |\n|---|---|\n| Where we are | `docs/STATUS.md` |\n"
            "| Roadmap | `docs/ROADMAP.md` |\n", encoding="utf-8")
        (self.root / "docs" / "STATUS.md").write_text(
            "# Status\n\n**Milestone:** M0\n\n1. Read `docs/ROADMAP.md` §M0.\n", encoding="utf-8")
        (self.root / "docs" / "ROADMAP.md").write_text("# Roadmap\n\n## M0 — Start\n", encoding="utf-8")
        (self.root / "docs" / "small.md").write_text("# Small\n", encoding="utf-8")
        self.write_map()

    def tearDown(self):
        self.tmp.cleanup()

    def write_map(self):
        (self.root / "docs" / "MAP.md").write_text(
            gm.build_map(self.root, self.root / "docs" / "MAP.md"), encoding="utf-8")

    def run_lint(self, *args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = lc.main(["--root", str(self.root), *args])
        return code, stdout.getvalue()

    def test_clean_context_passes(self):
        code, out = self.run_lint()
        self.assertEqual(code, 0)
        self.assertIn("0 problem(s)", out)

    def test_entry_token_budget_fails(self):
        (self.root / "AGENTS.md").write_text("# A\n" + "detail line\n" * 2_500, encoding="utf-8")
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("tokens always loaded", out)

    def test_nested_import_fails(self):
        (self.root / "AGENTS.md").write_text("@CLAUDE.md\n", encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("@docs/ROADMAP.md\n", encoding="utf-8")
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("one level deep", out)

    def test_status_line_limit_and_dead_path(self):
        (self.root / "docs" / "STATUS.md").write_text(
            "\n".join(["# S"] + ["line"] * 45 + ["- Read `docs/GONE.md`."]), encoding="utf-8")
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("lines (limit 40)", out)
        self.assertIn("referenced path does not exist: docs/GONE.md", out)

    def test_large_doc_needs_sections(self):
        (self.root / "docs" / "long.md").write_text("# Long\n" + "prose\n" * 320, encoding="utf-8")
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("fewer than 3 `##` sections", out)
        (self.root / "docs" / "long.md").write_text(
            "# Long\n\n## A\n" + "prose\n" * 100
            + "\n## B\n" + "prose\n" * 100
            + "\n## C\n" + "prose\n" * 100, encoding="utf-8")
        self.write_map()
        self.assertEqual(self.run_lint()[0], 0)

    def test_section_longer_than_the_limit_fails(self):
        (self.root / "docs" / "wall.md").write_text(
            "# Wall\n\n## One\n" + "line\n" * 130, encoding="utf-8")
        self.write_map()
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("section `One` is 131 lines", out)
        self.assertEqual(self.run_lint("--max-section-lines", "0")[0], 0)

    def test_dead_paths_and_broken_links_in_docs(self):
        (self.root / "docs" / "notes.md").write_text(
            "# Notes\n\nSee `docs/GONE.md` and [the missing page](../GONE.md).\n", encoding="utf-8")
        self.write_map()
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("referenced path does not exist: docs/GONE.md", out)
        self.assertIn("link target does not exist: ../GONE.md", out)

    def test_duplicate_prose_warns_until_strict(self):
        paragraph = "This is a long duplicated paragraph. " * 20
        (self.root / "docs" / "one.md").write_text("# One\n\n" + paragraph + "\n", encoding="utf-8")
        (self.root / "docs" / "two.md").write_text("# Two\n\n" + paragraph + "\n", encoding="utf-8")
        self.write_map()
        code, out = self.run_lint()
        self.assertEqual(code, 0)
        self.assertIn("duplicate paragraph", out)
        self.assertEqual(self.run_lint("--strict")[0], 1)

    def test_stale_map_fails(self):
        (self.root / "new.py").write_text('"""New module."""\n', encoding="utf-8")
        code, out = self.run_lint()
        self.assertEqual(code, 1)
        self.assertIn("stale", out)

    def test_strict_turns_missing_files_into_failures(self):
        (self.root / "AGENTS.md").unlink()
        self.write_map()
        self.assertEqual(self.run_lint()[0], 0)
        self.assertEqual(self.run_lint("--strict")[0], 1)


if __name__ == "__main__":
    unittest.main()
