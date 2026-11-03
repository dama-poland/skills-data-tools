"""Skill lint: the repository is clean and each rule catches what it should."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import lint_skills  # noqa: E402

SKILL = '---\nname: damapl-demo\ndescription: "Demo."\n---\n\n# Demo\n\n{body}\n'


def make_repo(tmp: Path, body="Run `scripts/run.py`.", name="damapl-demo", script="print('ok')\n") -> Path:
    folder = tmp / "skills" / "damapl-demo"
    (folder / "scripts").mkdir(parents=True)
    (folder / "SKILL.md").write_text(SKILL.format(body=body).replace("damapl-demo", name, 1))
    (folder / "scripts" / "run.py").write_text(script)
    return tmp


class LintTest(unittest.TestCase):
    def lint(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            return lint_skills.lint(make_repo(Path(tmp), **kwargs))

    def test_repository_is_clean(self):
        result = subprocess.run([str(ROOT / "scripts" / "lint.sh")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_minimal_skill_is_clean(self):
        self.assertEqual(self.lint(), [])

    def test_name_must_equal_folder_and_have_prefix(self):
        found = "\n".join(self.lint(name="other-demo"))
        self.assertIn("does not equal the folder name", found)
        self.assertIn("does not start with damapl-", found)

    def test_parent_absolute_and_repo_root_paths_are_rejected(self):
        for body, kind in (
            ("Read `../shared/x.md`.", "parent folder"),
            ("Read /Users/someone/x.md.", "absolute path"),
            ("Read ~/x.md.", "home path"),
            ("Use ${CLAUDE_PLUGIN_ROOT}/x.", "plugin root"),
            ("Run python3 examples/data/x.py.", "repo-root folder"),
        ):
            self.assertIn(kind, "\n".join(self.lint(body=body)), body)

    def test_script_climbing_above_skill_is_rejected(self):
        found = "\n".join(self.lint(script="from pathlib import Path\nR = Path(__file__).resolve().parents[2]\n"))
        self.assertIn("climbs above the skill folder", found)

    def test_missing_mentioned_file_is_rejected(self):
        found = "\n".join(self.lint(body="Read `references/nope.md`."))
        self.assertIn("references/nope.md", found)

    def test_secret_like_config_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            (repo / ".ai").mkdir()
            (repo / ".ai" / "damapl.config.json").write_text(json.dumps({"glossary": "g", "apiToken": "x"}))
            found = "\n".join(lint_skills.lint(repo))
            self.assertIn("apiToken", found)


if __name__ == "__main__":
    unittest.main()
