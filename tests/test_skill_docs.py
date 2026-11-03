"""Skill documentation and metadata: every description says when to use the
skill, all SKILL.md files name the same owner, the decision template leaves
the approver pending for a human, the glossary-entry template points inside
its own skill, the kickoff names its own script folder and the second-brain
spec no longer describes the retired two-skill layout.

Run: python3 -m unittest tests.test_skill_docs
"""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
SHARED = ROOT / "shared"
KICKOFF = ROOT / "skills" / "damapl-second-brain-kickoff"


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text[4:text.find("\n---\n", 4)]) or {}


class SkillDocs(unittest.TestCase):
    def test_every_description_says_when_to_use_the_skill(self):
        for path in SKILLS:
            description = str(frontmatter(path).get("description") or "")
            with self.subTest(skill=path.parent.name):
                self.assertIn("Use when", description)

    def test_every_skill_names_the_repository_owner(self):
        owner = frontmatter(ROOT / "README.md")["owner"]
        for path in SKILLS:
            with self.subTest(skill=path.parent.name):
                self.assertEqual(frontmatter(path).get("owner"), owner)

    def test_decision_template_leaves_the_approver_pending(self):
        text = (SHARED / "templates" / "decision.md").read_text(encoding="utf-8")
        approver = text.split("## Approver", 1)[1]
        self.assertIn("Pending: the architect decides.", approver)

    def test_glossary_entry_template_points_inside_its_skill(self):
        text = (ROOT / "skills" / "damapl-business-glossary" / "templates" /
                "glossary-entry.md").read_text(encoding="utf-8")
        self.assertNotIn("../", text)
        self.assertIn("`references/term-schema.md`", text)

    def test_kickoff_names_its_own_script_folder(self):
        text = (KICKOFF / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`python3 <this skill folder>/scripts/check_gate.py 1",
                      text)
        self.assertIn("`python3 <this skill folder>/scripts/freshness-review.py",
                      text)
        self.assertIsNone(re.search(r"python3 scripts/", text))

    def test_second_brain_spec_is_current(self):
        text = (KICKOFF / "references" / "second-brain-spec.md").read_text(
            encoding="utf-8")
        self.assertNotIn("two skills", text)
        self.assertIn("six skills", text)
        self.assertIn("of the damapl-business-glossary skill", text)
        self.assertNotIn("`templates/glossary-entry.md`", text)


if __name__ == "__main__":
    unittest.main()
