import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "token-optimization"

# Bytes, not tokens: ~4 bytes per token. Limits are deliberately tight enough
# to force a decision before a doc grows another section.
BUDGETS = {
    "skills/token-optimization/SKILL.md": 7_200,
    "skills/token-optimization/references/cost-model.md": 16_500,
    "skills/token-optimization/references/repo-setup.md": 13_500,
    "skills/token-optimization/references/reading-playbook.md": 7_000,
    "skills/token-optimization/references/prompt-patterns.md": 5_500,
    "skills/token-optimization/templates/AGENTS.template.md": 3_700,
    "skills/token-optimization/templates/CHECKPOINTS.template.md": 3_500,
    "skills/token-optimization/templates/CLAUDE.template.md": 1_900,
    "skills/token-optimization/templates/COST.template.md": 1_300,
    "skills/token-optimization/templates/ROADMAP.template.md": 900,
    "skills/token-optimization/templates/STATUS.template.md": 800,
    "README.md": 7_800,
}


class Budgets(unittest.TestCase):
    def test_docs_stay_within_their_token_budget(self):
        for relative, limit in BUDGETS.items():
            path = ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file(), relative)
                size = len(path.read_bytes())
                self.assertLessEqual(
                    size, limit,
                    f"{relative}: {size} bytes (~{size / 4:.0f} tokens) exceeds "
                    f"{limit} bytes (~{limit / 4:.0f} tokens); cut something before growing it")

    def test_skill_description_is_short(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        description = match.group(1)
        self.assertLessEqual(len(description), 360,
                             f"description is {len(description)} chars; it is paid on every session")


if __name__ == "__main__":
    unittest.main()
