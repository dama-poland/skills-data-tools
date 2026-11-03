#!/usr/bin/env python3
"""Scan tracked text files for emails, token-like strings and blocklisted names.

Usage:
    scan_repo.py [--root DIR]

Reads the file list from `git ls-files` (tracked files plus new files that are not ignored; falls back to walking the folder), skips the
vendored d3.min.js, LICENSE, binary files and the blocklist files themselves. Reports
file, line and kind of each hit, with the matched text shortened. No network, no LLM.
Exit code 0 means no hits, 1 means hits. Python 3.10 or later, standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKLIST = Path("tests") / "blocklist.txt"
LOCAL_BLOCKLIST = Path("tests") / "blocklist.local.txt"  # gitignored, private names
BLOCKLIST_ENV = "SCAN_BLOCKLIST"  # comma-separated, e.g. from a CI secret
SKIP_NAMES = {"d3.min.js", "LICENSE"}
SKIP_PATHS = {BLOCKLIST.as_posix(), LOCAL_BLOCKLIST.as_posix()}

ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org"}
ALLOWED_EMAILS = {"noreply@anthropic.com"}  # add author addresses listed in NOTICE only

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
TOKENS = {
    "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    "api key (sk-)": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "secret near key word": re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret|passw(?:or)?d|credential)s?\b[\"']?\s*[:=]\s*[\"']?"
        r"([A-Za-z0-9+/_=-]{32,})"
    ),
}


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            capture_output=True, text=True)
    if result.returncode == 0:
        return [root / n for n in result.stdout.split("\0") if n]
    return [p for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts]


def load_blocklist(root: Path) -> list[re.Pattern]:
    """Names from tests/blocklist.txt, the gitignored local list and $SCAN_BLOCKLIST.

    Private names (employers, clients) belong in the local file or the CI secret,
    never in the tracked list, because the tracked list is public.
    """
    names: list[str] = []
    for rel in (BLOCKLIST, LOCAL_BLOCKLIST):
        path = root / rel
        if path.is_file():
            names += [l.strip() for l in path.read_text(encoding="utf-8").splitlines()]
    names += [n.strip() for n in os.environ.get(BLOCKLIST_ENV, "").split(",")]
    return [re.compile(r"\b" + re.escape(n) + r"\b", re.I) for n in names if n and not n.startswith("#")]


def email_allowed(address: str) -> bool:
    lowered = address.lower()
    return lowered in ALLOWED_EMAILS or lowered.rsplit("@", 1)[-1] in ALLOWED_EMAIL_DOMAINS


def short(text: str) -> str:
    return text if len(text) <= 12 else text[:6] + "..." + text[-2:]


def scan_text(text: str, blocklist: list[re.Pattern]) -> list[tuple[int, str, str]]:
    """Return (line number, kind, shortened match) for every hit in the text."""
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in EMAIL.finditer(line):
            if not email_allowed(match.group(0)):
                hits.append((number, "email", short(match.group(0))))
        for kind, pattern in TOKENS.items():
            for match in pattern.finditer(line):
                hits.append((number, kind, short(match.group(0))))
        for pattern in blocklist:
            for match in pattern.finditer(line):
                hits.append((number, "blocklisted name", match.group(0)))
    return hits


def scan(root: Path) -> list[tuple[str, int, str, str]]:
    blocklist = load_blocklist(root)
    results = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if path.name in SKIP_NAMES or rel in SKIP_PATHS or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        results += [(rel, n, kind, found) for n, kind, found in scan_text(text, blocklist)]
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    hits = scan(args.root.resolve())
    for rel, number, kind, found in hits:
        print(f"{rel}:{number}: {kind}: {found}")
    print(f"scan found {len(hits)} hit(s)" if hits else "scan passed: no hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
