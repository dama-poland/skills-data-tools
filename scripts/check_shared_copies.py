#!/usr/bin/env python3
"""Fail if any copy of a shared file differs byte for byte from shared/.

Usage:
    check_shared_copies.py

The mapping of shared files to skills lives in sync_shared.py. Fix a failure by
editing shared/ and running `python3 scripts/sync_shared.py`, never by editing a
copy. Exit code 0 means all copies are identical, 1 means at least one is not.
Requires Python 3.10 or later, standard library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_shared  # noqa: E402


def main() -> int:
    found = sync_shared.problems()
    if found:
        print("\n".join(found))
        print(f"{len(found)} problem(s). Edit shared/ and run: python3 scripts/sync_shared.py")
        return 1
    print(f"all {len(sync_shared.expected_copies())} shared copies are identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
