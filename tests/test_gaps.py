"""Gap list: compare with the expected output, check determinism and each check."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "damapl-gap-list" / "scripts" / "gaps_build.py"
EXPECTED = ROOT / "examples" / "expected" / "gaps.md"
SYSTEMS = ROOT / "examples" / "data" / "systems"
GLOSSARY = ROOT / "examples" / "data" / "glossary"


def run(out, *extra):
    systems = [] if "--systems" in extra else ["--systems", str(SYSTEMS)]
    glossary = [] if "--glossary" in extra else ["--glossary", str(GLOSSARY)]
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), *systems, *glossary, *extra],
        capture_output=True, text=True, cwd=ROOT,
    )


def note(source_id, concepts):
    lines = ["---", f'source_id: "{source_id}"']
    if concepts:
        lines.append("concepts:")
        for term, status, source in concepts:
            lines += [f"  - term: {term}", '    meaning: "m"', f"    status: {status}"]
            if source:
                lines.append(f'    source: "{source}"')
    return "\n".join(lines + ["---", "", "# note", ""])


def term(term_id, status, extra=""):
    return f'---\nid: {term_id}\nname: {term_id.title()}\nstatus: {status}\n{extra}---\n\n# {term_id}\n'


class GapsBuildTest(unittest.TestCase):
    def test_matches_expected_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gaps.md"
            self.assertEqual(run(out).returncode, 0)
            self.assertEqual(out.read_bytes(), EXPECTED.read_bytes())

    def test_two_runs_are_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            run(Path(tmp) / "a.md")
            run(Path(tmp) / "b.md")
            self.assertEqual((Path(tmp) / "a.md").read_bytes(), (Path(tmp) / "b.md").read_bytes())

    def test_expected_counts_for_demo(self):
        text = EXPECTED.read_text(encoding="utf-8")
        for row in (
            "| meaning conflict | 1 |", "| homonym risk | 1 |",
            "| link to a term that is not Approved | 2 |",
            "| system with no approved links | 1 |",
            "| approved term used by no system | 1 |", "| link with no source | 0 |",
        ):
            self.assertIn(row, text)
        self.assertIn("| device | Under Review |", text)
        self.assertIn("- randomisation-number", text)

    def test_superseded_note_skipped_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            default = run(Path(tmp) / "a.md")
            full = run(Path(tmp) / "b.md", "--include-superseded")
            self.assertNotIn("supply-v1", (Path(tmp) / "a.md").read_text())
            self.assertEqual(full.returncode, 0)

    def test_synthetic_fixture_hits_every_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "systems").mkdir()
            (root / "glossary" / "terms").mkdir(parents=True)
            (root / "systems" / "a.md").write_text(note("A", [("t1", "approved", "A"), ("t2", "approved", ""), ("ghost", "approved", "A")]))
            (root / "systems" / "b.md").write_text(note("B", [("t1", "approved", "B")]))
            (root / "systems" / "c.md").write_text(note("C", None))
            (root / "glossary" / "terms" / "t1.md").write_text(term("t1", "Approved"))
            (root / "glossary" / "terms" / "t2.md").write_text(term("t2", "Draft", "homonym_of: [t1]\n"))
            (root / "glossary" / "terms" / "idle.md").write_text(term("idle", "Approved"))
            out = root / "gaps.md"
            result = run(out, "--systems", str(root / "systems"), "--glossary", str(root / "glossary"))
            self.assertEqual(result.returncode, 0, result.stderr)
            text = out.read_text()
            # b shares t1 with a only by wording "m", so no meaning conflict
            self.assertIn("| meaning conflict | 0 |", text)
            self.assertIn("| homonym risk | 1 |", text)
            self.assertIn("| ghost | missing from glossary | a |", text)
            self.assertIn("| t2 | Draft | a |", text)
            self.assertIn("- c", text)
            self.assertIn("- idle", text)
            self.assertIn("| a | t2 | approved |", text)

    def test_systems_and_glossary_arguments_are_required(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--systems", result.stderr)

    def test_missing_glossary_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(Path(tmp) / "a.md", "--glossary", str(Path(tmp) / "nope"))
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
