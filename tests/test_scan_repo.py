"""scan_repo.py: the repository is clean and the scanner finds what it should."""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import scan_repo  # noqa: E402

BLOCK = [re.compile(r"\bacmecorp\b", re.I)]


def kinds(text):
    return [kind for _n, kind, _m in scan_repo.scan_text(text, BLOCK)]


class ScanRepoTest(unittest.TestCase):
    def test_repository_is_clean(self):
        result = subprocess.run([sys.executable, str(ROOT / "tests" / "scan_repo.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_flags_real_looking_email(self):
        self.assertEqual(kinds("write to " + "jan.kowalski" + "@" + "firma.pl"), ["email"])

    def test_allows_example_and_noreply_emails(self):
        self.assertEqual(kinds("a@example.com b@example.org noreply@anthropic.com"), [])

    def test_flags_token_shapes(self):
        fake_aws = "AKIA" + "A" * 16
        fake_gh = "ghp_" + "a" * 36
        fake_sk = "sk-" + "b" * 30
        self.assertEqual(kinds(f"{fake_aws} {fake_gh} {fake_sk}"),
                         ["aws access key", "github token", "api key (sk-)"])

    def test_flags_long_secret_near_key_word(self):
        self.assertEqual(kinds("api_key = " + "Ab1" * 12), ["secret near key word"])

    def test_flags_blocklisted_name_case_insensitively(self):
        self.assertEqual(kinds("Built for ACMECORP."), ["blocklisted name"])

    def test_blocklist_uses_whole_words(self):
        self.assertEqual(kinds("acmecorporation is a different word"), [])


if __name__ == "__main__":
    unittest.main()
