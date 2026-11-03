"""Model diff: compare with the expected output and check determinism."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "damapl-model-change" / "scripts" / "model_diff.py"
EXPECTED = ROOT / "examples" / "expected" / "model-diff-supply-v1-v2.md"
V1 = ROOT / "examples" / "data" / "systems" / "supply-v1.md"
V2 = ROOT / "examples" / "data" / "systems" / "supply-v2.md"


def run(old, new, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(old), str(new), *extra],
        capture_output=True, text=True, cwd=ROOT,
    )


class ModelDiffTest(unittest.TestCase):
    def test_matches_expected_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "d.md"
            self.assertEqual(run(V1, V2, "--out", str(out)).returncode, 0)
            self.assertEqual(out.read_bytes(), EXPECTED.read_bytes())

    def test_two_runs_are_identical(self):
        self.assertEqual(run(V1, V2).stdout, run(V1, V2).stdout)

    def test_reports_added_device_model(self):
        text = run(V1, V2).stdout
        self.assertIn("| device-model | added |", text)
        self.assertIn("| Kit / device_model | added |", text)
        self.assertIn("| supersedes | added |", text)

    def test_reverse_direction_reports_removal(self):
        text = run(V2, V1).stdout
        self.assertIn("| device-model | removed |", text)
        self.assertIn("| Kit / device_model | removed |", text)

    def test_identical_notes_have_no_changes(self):
        text = run(V1, V1).stdout
        self.assertIn("| frontmatter fields | 0 |", text)
        self.assertIn("| concept links | 0 |", text)

    def test_missing_file_is_an_error(self):
        self.assertEqual(run(V1, ROOT / "nope.md").returncode, 2)


if __name__ == "__main__":
    unittest.main()
