"""freshness-review.py: parses YAML properly, never overwrites an approved
status, adds each review_reason once, and has skips hidden folders by one general rule.
All data is synthetic."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "damapl-second-brain-kickoff" / "scripts" / "freshness-review.py"

NEW = '---\nsource_id: "S-v2"\nsupersedes: "S-v1"\nstatus: "approved"\n---\n\n# new\n'
NEW_TWO = '---\nsource_id: "T-v2"\nsupersedes: "T-v1"\nstatus: "approved"\n---\n\n# new\n'


def derived(status, refs='  - "S-v1"', extra=""):
    return (f'---\ntitle: "Derived: a title with a colon"\nsource_refs:\n{refs}\n'
            f'status: {status}\n{extra}---\n\n# derived\n')


def run(vault, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(vault), *extra],
                          capture_output=True, text=True)


def front(path):
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text[4:text.find("\n---\n", 4)])


class FreshnessReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.vault = Path(tmp.name)
        self.write("new.md", NEW)

    def write(self, name, content):
        path = self.vault / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_preview_lists_the_note_and_writes_nothing(self):
        note = self.write("d.md", derived("approved"))
        before = note.read_bytes()
        result = run(self.vault)
        self.assertIn("d.md: requires review; S-v1 -> S-v2", result.stdout)
        self.assertIn("affected notes: 1", result.stdout)
        self.assertEqual(note.read_bytes(), before)

    def test_approved_status_is_kept_and_reason_added(self):
        note = self.write("d.md", derived('"approved"'))
        self.assertEqual(run(self.vault, "--apply").returncode, 0)
        fm = front(note)
        self.assertEqual(fm["status"], "approved")
        self.assertEqual(fm["review_reason"], "S-v1 was superseded by S-v2")

    def test_capitalised_approved_is_kept_too(self):
        note = self.write("d.md", derived("Approved"))
        run(self.vault, "--apply")
        self.assertEqual(front(note)["status"], "Approved")

    def test_unapproved_status_becomes_review_needed(self):
        note = self.write("d.md", derived("draft"))
        run(self.vault, "--apply")
        fm = front(note)
        self.assertEqual(fm["status"], "review-needed")
        self.assertEqual(fm["review_reason"], "S-v1 was superseded by S-v2")

    def test_note_without_status_gets_review_needed(self):
        note = self.write("d.md", '---\nsource_refs: ["S-v1"]\n---\n\n# d\n')
        run(self.vault, "--apply")
        self.assertEqual(front(note)["status"], "review-needed")

    def test_apply_twice_changes_nothing_the_second_time(self):
        for status in ("approved", "draft"):
            with self.subTest(status):
                note = self.write("d.md", derived(status))
                run(self.vault, "--apply")
                once = note.read_bytes()
                run(self.vault, "--apply")
                self.assertEqual(note.read_bytes(), once)
                self.assertEqual(once.decode().count("review_reason"), 1)

    def test_two_superseded_sources_give_one_review_reason_line(self):
        self.write("t.md", NEW_TWO)
        note = self.write("d.md", derived("approved", '  - "S-v1"\n  - "T-v1"'))
        run(self.vault, "--apply")
        run(self.vault, "--apply")
        text = note.read_bytes().decode()
        self.assertEqual(text.count("review_reason"), 1)
        reason = front(note)["review_reason"]
        self.assertIn("S-v1 was superseded by S-v2", reason)
        self.assertIn("T-v1 was superseded by T-v2", reason)

    def test_existing_unrelated_review_reason_is_kept_in_the_line(self):
        note = self.write("d.md", derived("draft", extra='review_reason: "checked by hand"\n'))
        run(self.vault, "--apply")
        self.assertEqual(note.read_bytes().decode().count("review_reason"), 1)
        reason = front(note)["review_reason"]
        self.assertIn("checked by hand", reason)
        self.assertIn("S-v1 was superseded by S-v2", reason)

    def test_yaml_forms_the_old_parser_missed(self):
        self.write("a.md", derived("draft", refs='  - S-v1 # comment'))
        self.write("b.md", '---\nsource_refs: [S-v1, other]\nstatus: draft\n---\n\n# b\n')
        self.write("c.md", '---\nsource_refs: S-v1\nstatus: draft\n---\n\n# c\n')
        out = run(self.vault).stdout
        self.assertIn("affected notes: 3", out)

    def test_hidden_folders_are_skipped_by_one_general_rule(self):
        self.write("archive/d.md", derived("draft"))
        self.write(".obsidian/d.md", derived("draft"))
        self.write(".demo-history/x/d.md", derived("draft"))
        out = run(self.vault).stdout
        self.assertIn("archive/d.md", out)
        self.assertIn("affected notes: 1", out)
        self.assertNotIn(".demo-history", SCRIPT.read_text(encoding="utf-8"))

    def test_unreadable_note_is_reported_and_others_continue(self):
        self.write("d.md", derived("draft"))
        self.write("broken.md", "---\nsource_refs: [a: b: c\n---\n\n# x\n")
        (self.vault / "binary.md").write_bytes(b"---\ntitle: \xff\xfe\n---\n")
        result = run(self.vault)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("broken.md", result.stderr)
        self.assertIn("binary.md", result.stderr)
        self.assertIn("affected notes: 1", result.stdout)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
