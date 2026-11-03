"""check_smoke.py: the self-check passes and the checker rejects bad agent output."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import check_smoke  # noqa: E402


class CheckSmokeTest(unittest.TestCase):
    def test_self_check_passes(self):
        result = subprocess.run([sys.executable, str(ROOT / "tests" / "check_smoke.py"),
                                 "--self-check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_good_fixture_repo_passes_every_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = check_smoke.build_fixture_repo(Path(tmp))
            for name, problems, _note in check_smoke.run_checks(repo):
                self.assertEqual(problems, [], name)

    def test_empty_repo_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = check_smoke.build_fixture_repo(Path(tmp))
            (repo / "generated" / "smoke" / "answers.md").unlink()
            self.assertTrue(check_smoke.check_answers(
                repo / "generated" / "smoke" / "answers.md", repo))

    def test_new_approvals_detected(self):
        found = check_smoke.new_approvals({"a": "approved", "b": "proposed", "c": "Approved"},
                                          {"a": "approved", "b": "proposed", "c": "Draft"})
        self.assertEqual(found, ["c"])


if __name__ == "__main__":
    unittest.main()
