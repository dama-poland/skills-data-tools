"""Shared files: copies in the skills equal shared/, and the checker catches drift."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_shared_copies.py"
sys.path.insert(0, str(ROOT / "scripts"))

import sync_shared  # noqa: E402


def copy_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    for folder in ("scripts", "shared", "skills"):
        shutil.copytree(ROOT / folder, repo / folder, ignore=shutil.ignore_patterns("__pycache__"))
    return repo


def check(repo: Path):
    return subprocess.run([sys.executable, str(repo / "scripts" / "check_shared_copies.py")],
                          capture_output=True, text=True)


class SharedCopiesTest(unittest.TestCase):
    def test_repository_copies_are_identical(self):
        result = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_edited_copy_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(Path(tmp))
            target = repo / "skills" / "damapl-gap-list" / "scripts" / "map_build.py"
            target.write_text(target.read_text() + "\n# drift\n")
            result = check(repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("damapl-gap-list/scripts/map_build.py differs", result.stdout)

    def test_missing_copy_is_reported_and_sync_restores_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(Path(tmp))
            (repo / "skills" / "damapl-model-change" / "templates" / "decision.md").unlink()
            self.assertEqual(check(repo).returncode, 1)
            sync = subprocess.run([sys.executable, str(repo / "scripts" / "sync_shared.py")],
                                  capture_output=True, text=True)
            self.assertEqual(sync.returncode, 0, sync.stderr)
            self.assertEqual(check(repo).returncode, 0)

    def test_unmapped_shared_file_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = copy_repo(Path(tmp))
            (repo / "shared" / "scripts" / "stray.py").write_text("x = 1\n")
            result = check(repo)
            self.assertEqual(result.returncode, 1)
            self.assertIn("shared/scripts/stray.py has no entry", result.stdout)

    def test_every_mapped_skill_exists(self):
        for skills in sync_shared.COPIES.values():
            for skill in skills:
                self.assertTrue((ROOT / "skills" / skill).is_dir(), skill)


if __name__ == "__main__":
    unittest.main()
