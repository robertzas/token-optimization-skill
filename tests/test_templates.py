import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "token-optimization"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class Links(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        files = [ROOT / "README.md", SKILL / "SKILL.md",
                 *sorted((SKILL / "references").glob("*.md")),
                 *sorted((SKILL / "templates").glob("*.md"))]
        for path in files:
            for target in LINK.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = target.split("#", 1)[0]
                if not target or "<" in target:
                    continue
                with self.subTest(path=path.relative_to(ROOT).as_posix(), target=target):
                    self.assertTrue((path.parent / target).resolve().exists(),
                                    f"{path.relative_to(ROOT)}: missing link target {target}")

    def test_every_script_is_discoverable(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (
            ROOT / "README.md", SKILL / "SKILL.md",
            *sorted((SKILL / "references").glob("*.md")),
            *sorted((SKILL / "templates").glob("*.md")),
        ))
        for script in sorted((SKILL / "scripts").glob("*.py")):
            with self.subTest(script=script.name):
                self.assertIn(script.name, combined,
                              f"{script.name} is not mentioned in README or the skill docs")


class SettingsTemplate(unittest.TestCase):
    def test_guard_is_wired_and_permissions_deny_bulk_files(self):
        data = json.loads((SKILL / "templates" / "settings.template.json").read_text(encoding="utf-8"))
        self.assertTrue(data["permissions"]["deny"])
        hooks = data["hooks"]["PreToolUse"]
        read_hook = next(hook for hook in hooks if hook["matcher"] == "Read")
        command = read_hook["hooks"][0]["command"]
        self.assertIn("guard_read.py", command)
        self.assertIn("--max-lines", command)


class Manifest(unittest.TestCase):
    def test_plugin_version_is_semver_and_source_exists(self):
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "token-optimization")
        self.assertRegex(plugin["version"], SEMVER)
        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        source = marketplace["plugins"][0]["source"]
        self.assertTrue((ROOT / source).resolve().exists())


if __name__ == "__main__":
    unittest.main()
