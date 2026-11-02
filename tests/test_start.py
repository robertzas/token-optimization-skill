import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "token-optimization" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import start  # noqa: E402


class Render(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "STATUS.md").write_text(
            "# Status\n\n**Milestone:** M1 — Two\n**Next WP:** M1.2 — Beta\n", encoding="utf-8")
        (self.root / "docs" / "ROADMAP.md").write_text(
            "# Roadmap\n\n## M0 — Old\n- old\n\n## M1 — Two\n- new\n\n## M2 — Later\n- later\n",
            encoding="utf-8")
        (self.root / "AGENTS.md").write_text(
            "# A\n\n| Need | Read |\n|---|---|\n| Where we are | `docs/STATUS.md` |\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_prints_status_current_section_and_doc_map(self):
        out = start.render(self.root, "docs/STATUS.md", "docs/ROADMAP.md", "AGENTS.md")
        self.assertIn("=== docs/STATUS.md ===", out)
        self.assertIn("M1 — Two", out)
        self.assertIn("§M1", out)
        self.assertNotIn("M2 — Later", out)
        self.assertNotIn("## M0 — Old", out)
        self.assertIn("| Where we are | `docs/STATUS.md` |", out)

    def test_next_wp_falls_back_to_its_milestone_section(self):
        (self.root / "docs" / "ROADMAP.md").write_text("# R\n\n## M1 — Two\n- new\n", encoding="utf-8")
        out = start.render(self.root, "docs/STATUS.md", "docs/ROADMAP.md", "AGENTS.md")
        self.assertIn("§M1", out)
        self.assertIn("- new", out)

    def test_missing_files_are_named(self):
        empty = self.root / "empty"
        empty.mkdir()
        out = start.render(empty, "docs/STATUS.md", "docs/ROADMAP.md", "AGENTS.md")
        self.assertIn("(no docs/STATUS.md)", out)
        self.assertIn("(no AGENTS.md)", out)

    def test_long_files_are_capped(self):
        (self.root / "docs" / "STATUS.md").write_text("\n".join("line" for _ in range(150)), encoding="utf-8")
        out = start.render(self.root, "docs/STATUS.md", "docs/ROADMAP.md", "AGENTS.md", limit=10)
        self.assertIn("(140 more lines)", out)


if __name__ == "__main__":
    unittest.main()
