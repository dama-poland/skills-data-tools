#!/usr/bin/env python3
"""Copy the canonical files in shared/ into the skills that use them.

Usage:
    sync_shared.py          write the copies
    sync_shared.py --check  write nothing; exit 1 if any copy is missing or differs

Edit shared files in shared/ only, then run this script. Installers copy one skill
folder, so each skill needs its own identical copy (docs/install.md).
Requires Python 3.10 or later, standard library only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"

KICKOFF = "damapl-second-brain-kickoff"
GLOSSARY = "damapl-business-glossary"
CONCEPTS = "damapl-concept-extraction"
SYSTEM_MAP = "damapl-system-map"
GAP_LIST = "damapl-gap-list"
MODEL_CHANGE = "damapl-model-change"

GATE_SKILLS = (KICKOFF, GLOSSARY, MODEL_CHANGE)

# Path inside shared/ (and inside each skill) -> skills that receive a copy.
COPIES: dict[str, tuple[str, ...]] = {
    "scripts/answer_contract.py": GATE_SKILLS,
    "scripts/arch_common.py": (KICKOFF, GLOSSARY, SYSTEM_MAP, GAP_LIST, MODEL_CHANGE),
    "scripts/check_gate.py": GATE_SKILLS,
    "scripts/map_build.py": (SYSTEM_MAP, GAP_LIST, MODEL_CHANGE),
    "scripts/gaps_build.py": (GAP_LIST, MODEL_CHANGE),
    "references/answer-contract.md": (KICKOFF, CONCEPTS),
    "references/quality-and-currency.md": (KICKOFF, CONCEPTS),
    "references/term-schema.md": (GLOSSARY, CONCEPTS),
    "references/gate-1-second-brain.md": GATE_SKILLS,
    "references/gate-2-glossary.md": GATE_SKILLS,
    "references/gate-3-architecture.md": GATE_SKILLS,
    "templates/decision.md": (CONCEPTS, MODEL_CHANGE),
}


def expected_copies() -> list[tuple[Path, Path]]:
    return [(SHARED / rel, SKILLS / skill / rel)
            for rel, skills in COPIES.items() for skill in skills]


def problems() -> list[str]:
    """Missing canonical files, files in shared/ with no mapping, missing or differing copies."""
    found = []
    mapped = set(COPIES)
    on_disk = {p.relative_to(SHARED).as_posix() for p in SHARED.rglob("*")
               if p.is_file() and "__pycache__" not in p.parts}
    for rel in sorted(on_disk - mapped):
        found.append(f"shared/{rel} has no entry in COPIES")
    for rel in sorted(mapped - on_disk):
        found.append(f"shared/{rel} does not exist")
    for source, target in expected_copies():
        label = target.relative_to(ROOT).as_posix()
        if not source.is_file():
            continue
        if not target.is_file():
            found.append(f"{label} is missing")
        elif target.read_bytes() != source.read_bytes():
            found.append(f"{label} differs from shared/{source.relative_to(SHARED).as_posix()}")
    return found


def sync() -> int:
    errors = [p for p in problems() if p.endswith("no entry in COPIES") or p.endswith("does not exist")]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    count = 0
    for source, target in expected_copies():
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            count += 1
            print(f"wrote {target.relative_to(ROOT).as_posix()}")
    print(f"sync done: {count} file(s) written, {len(expected_copies())} copies in place")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="write nothing; fail on any difference")
    args = parser.parse_args(argv)
    if args.check:
        found = problems()
        print("\n".join(found) if found else f"all {len(expected_copies())} shared copies are identical")
        return 1 if found else 0
    return sync()


if __name__ == "__main__":
    sys.exit(main())
