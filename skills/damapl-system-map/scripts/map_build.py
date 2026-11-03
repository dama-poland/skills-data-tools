#!/usr/bin/env python3
"""Build the system map from approved concept links.

Usage:
    map_build.py --systems DIR [--out FILE] [--include-superseded]

Choice on superseded notes: a system note whose source_id appears in another
note's `supersedes` is skipped (supply-v1 is superseded by supply-v2). Notes
without a `concepts:` list, such as the supply.md index, contribute no rows,
so they need no special handling. Use --include-superseded to keep old versions.
Output is deterministic: no timestamps, stable sorting.
"""

from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch_common import NoteError, approved_links, current_systems, load_systems  # noqa: E402

DEFAULT_OUT = Path("generated/architecture/map.md")


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def node_id(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)


def edges(links: list[dict]) -> list[tuple[str, str, list[str]]]:
    by_term: dict[str, set[str]] = {}
    for link in links:
        by_term.setdefault(link["term"], set()).add(link["system"])
    pairs: dict[tuple[str, str], list[str]] = {}
    for term in sorted(by_term):
        for a, b in combinations(sorted(by_term[term]), 2):
            pairs.setdefault((a, b), []).append(term)
    return [(a, b, terms) for (a, b), terms in sorted(pairs.items())]


def render(links: list[dict]) -> str:
    lines = [
        "# System and concept map",
        "",
        "Generated from approved `concepts:` entries in system notes. "
        "Shared-term links do not prove an observed data flow between systems.",
        "",
        "| term | system | meaning | source |",
        "|---|---|---|---|",
    ]
    for l in links:
        lines.append(
            f"| {l['term']} | {l['system']} | {escape_cell(l['meaning'])} | {l['source']} |"
        )
    lines += ["", "```mermaid", "graph LR"]
    for name in sorted({l["system"] for l in links}):
        lines.append(f'  {node_id(name)}["{name}"]')
    for a, b, terms in edges(links):
        lines.append(f'  {node_id(a)} ---|"{", ".join(terms)}"| {node_id(b)}')
    lines += ["```", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--systems", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-superseded", action="store_true")
    args = parser.parse_args(argv)
    if not args.systems.is_dir():
        print(f"error: systems directory not found: {args.systems}", file=sys.stderr)
        return 2
    try:
        notes = current_systems(load_systems(args.systems), args.include_superseded)
    except NoteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = render(approved_links(notes))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
