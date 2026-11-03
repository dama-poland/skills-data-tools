#!/usr/bin/env python3
"""Compare two versions of a system note.

Usage:
    model_diff.py OLD NEW [--out FILE]

Reports changes in frontmatter fields, in `concepts:` entries (added, removed,
changed meaning, status or source, keyed by term; a repeated term is compared entry by entry) and in the body:
rows of Markdown tables (keyed by their first two cells; the header row of any
table is skipped; repeated keys are compared row by row) and other body lines.
Output is deterministic Markdown; without --out it goes to stdout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch_common import NoteError, split_note  # noqa: E402
from map_build import escape_cell  # noqa: E402

SKIP_FIELDS = {"concepts"}


def fmt(value) -> str:
    return "-" if value is None else " ".join(str(value).split())


def field_changes(old: dict, new: dict) -> list[list[str]]:
    rows = []
    for key in sorted((set(old) | set(new)) - SKIP_FIELDS):
        if key not in old:
            rows.append([key, "added", "-", fmt(new[key])])
        elif key not in new:
            rows.append([key, "removed", fmt(old[key]), "-"])
        elif old[key] != new[key]:
            rows.append([key, "changed", fmt(old[key]), fmt(new[key])])
    return rows


def concept_map(fm: dict) -> dict[str, list[dict]]:
    mapped: dict[str, list[dict]] = {}
    for entry in fm.get("concepts") or []:
        mapped.setdefault(str(entry["term"]), []).append(entry)
    return mapped


def describe(entry: dict) -> str:
    return f"{fmt(entry.get('meaning'))} [{fmt(entry.get('status'))}, {fmt(entry.get('source'))}]"


def concept_changes(old: dict, new: dict) -> list[list[str]]:
    a, b = concept_map(old), concept_map(new)
    rows = []
    for term in sorted(set(a) | set(b)):
        old_entries, new_entries = a.get(term, []), b.get(term, [])
        for i in range(max(len(old_entries), len(new_entries))):
            if i >= len(old_entries):
                rows.append([term, "added", "-", describe(new_entries[i])])
            elif i >= len(new_entries):
                rows.append([term, "removed", describe(old_entries[i]), "-"])
            else:
                for field in ("meaning", "status", "source"):
                    before, after = old_entries[i].get(field), new_entries[i].get(field)
                    if fmt(before) != fmt(after):
                        rows.append([term, f"{field} changed", fmt(before), fmt(after)])
    return rows


def split_body(body: str) -> tuple[dict[str, list[str]], list[str]]:
    """Table rows keyed by first two cells, and remaining non-heading lines.

    The header row of a table is the row followed by a separator row; it is
    skipped whatever its column names are. A key that repeats keeps every row.
    """
    tables: dict[str, list[str]] = {}
    prose: list[str] = []
    lines = [line.strip() for line in body.splitlines()]
    for i, line in enumerate(lines):
        if not line or line.startswith("#"):
            continue
        if not line.startswith("|"):
            prose.append(line)
            continue
        cells = split_cells(line)
        if is_separator(cells):
            continue
        if i + 1 < len(lines) and lines[i + 1].startswith("|") and is_separator(split_cells(lines[i + 1])):
            continue
        tables.setdefault(" / ".join(cells[:2]), []).append(" | ".join(cells[2:]))
    return tables, prose


def split_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip("|").split("|")]


def is_separator(cells: list[str]) -> bool:
    return all(set(c) <= set("-: ") for c in cells)


def body_changes(old_body: str, new_body: str) -> tuple[list[list[str]], list[list[str]]]:
    ta, pa = split_body(old_body)
    tb, pb = split_body(new_body)
    rows = []
    for key in sorted(set(ta) | set(tb)):
        old_rows, new_rows = ta.get(key, []), tb.get(key, [])
        for i in range(max(len(old_rows), len(new_rows))):
            if i >= len(old_rows):
                rows.append([key, "added", "-", new_rows[i]])
            elif i >= len(new_rows):
                rows.append([key, "removed", old_rows[i], "-"])
            elif old_rows[i] != new_rows[i]:
                rows.append([key, "changed", old_rows[i], new_rows[i]])
    lines = [["removed", x] for x in pa if x not in pb] + [["added", x] for x in pb if x not in pa]
    return rows, lines


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["None.", ""]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(escape_cell(c) for c in r) + " |" for r in rows]
    return lines + [""]


def render(old_path: Path, new_path: Path) -> str:
    old_fm, old_body = split_note(old_path)
    new_fm, new_body = split_note(new_path)
    fields = field_changes(old_fm, new_fm)
    concepts = concept_changes(old_fm, new_fm)
    tables, lines = body_changes(old_body, new_body)
    out = [
        f"# Model diff: {old_path.stem} to {new_path.stem}", "",
        "Generated by comparing two system notes. A diff lists what changed; it does not say what to do about it.", "",
        "| area | changes |", "|---|---|",
        f"| frontmatter fields | {len(fields)} |",
        f"| concept links | {len(concepts)} |",
        f"| body table rows | {len(tables)} |",
        f"| other body lines | {len(lines)} |", "",
        "## Frontmatter fields", "",
        *table(["field", "change", "old", "new"], fields),
        "## Concept links", "",
        *table(["term", "change", "old", "new"], concepts),
        "## Body table rows", "",
        *table(["entity / field", "change", "old", "new"], tables),
        "## Other body lines", "",
        *table(["change", "line"], lines),
    ]
    return "\n".join(out).rstrip("\n") + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    for path in (args.old, args.new):
        if not path.is_file():
            print(f"error: note not found: {path}", file=sys.stderr)
            return 2
    try:
        text = render(args.old, args.new)
    except NoteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.out is None:
        sys.stdout.write(text)
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
