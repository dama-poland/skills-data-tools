"""Map build: compare with the expected output and check determinism."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "damapl-system-map" / "scripts" / "map_build.py"
SYSTEMS = ROOT / "examples" / "data" / "systems"
EXPECTED = ROOT / "examples" / "expected" / "map.md"


def run(out, *extra):
    systems = [] if "--systems" in extra else ["--systems", str(SYSTEMS)]
    subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out), *systems, *extra],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    return out.read_bytes()


class MapBuildTest(unittest.TestCase):
    def test_matches_expected_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run(Path(tmp) / "map.md"), EXPECTED.read_bytes())

    def test_two_runs_are_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = run(Path(tmp) / "a.md")
            second = run(Path(tmp) / "b.md")
            self.assertEqual(first, second)

    def test_superseded_system_excluded_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            default = run(Path(tmp) / "a.md").decode()
            full = run(Path(tmp) / "b.md", "--include-superseded").decode()
            self.assertNotIn("supply-v1", default)
            self.assertIn("supply-v1", full)

    def test_systems_argument_is_required(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--systems", result.stderr)

    def test_proposed_entries_are_not_mapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = run(Path(tmp) / "a.md").decode()
            self.assertNotIn("| visit |", text)
            self.assertNotIn("| complaint |", text)


if __name__ == "__main__":
    unittest.main()
