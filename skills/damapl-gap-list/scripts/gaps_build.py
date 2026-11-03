#!/usr/bin/env python3
"""Build the gap list from concept links and the glossary.

Usage:
    gaps_build.py --systems DIR --glossary DIR [--out FILE] [--include-superseded]

Checks, all on approved links of current system notes
unless stated otherwise:
  1. meaning conflict: one term id, different meaning text in different systems
  2. homonym risk: two term ids that share a name or a homonym_of link and are
     used in one system or in two systems linked by a shared term
  3. link to a term that is not Approved in the glossary (or missing from it)
  4. system with no approved links
  5. Approved glossary term that no system links to
  6. link with no source (any status except rejected)

The meaning check compares text, so a difference in wording is reported as a
candidate; a human decides whether the concept differs. Superseded notes are
skipped as in map_build.py. Output is deterministic.
"""

from __future__ import annotations

import argparse
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch_common import (  # noqa: E402
    approved_links, current_systems, load_glossary, load_systems, system_name,
)
from map_build import edges, escape_cell  # noqa: E402

DEFAULT_OUT = Path("generated/architecture/gaps.md")
GLOSSARY_APPROVED = "Approved"


def meaning_conflicts(links: list[dict]) -> list[dict]:
    by_term: dict[str, list[dict]] = {}
    for link in links:
        by_term.setdefault(link["term"], []).append(link)
    found = []
    for term in sorted(by_term):
        rows = by_term[term]
        systems = {r["system"] for r in rows}
        meanings = {r["meaning"].casefold() for r in rows}
        if len(systems) > 1 and len(meanings) > 1:
            found.append({"term": term, "rows": rows})
    return found


def name_keys(fm: dict) -> set[str]:
    names = [fm.get("name"), *(fm.get("alternative_names") or [])]
    return {str(n).strip().casefold() for n in names if n}


def homonym_pairs(glossary: dict[str, dict], used: set[str]) -> dict[tuple[str, str], list[str]]:
    """Pairs of used term ids with the reasons they are homonym candidates."""
    reasons: dict[tuple[str, str], list[str]] = {}
    ids = sorted(t for t in glossary if t in used)
    for a, b in combinations(ids, 2):
        why = []
        shared = sorted(name_keys(glossary[a]) & name_keys(glossary[b]))
        if shared:
            why.append("shared name " + ", ".join(f"'{s}'" for s in shared))
        linked = b in (glossary[a].get("homonym_of") or []) or a in (glossary[b].get("homonym_of") or [])
        if linked:
            why.append("homonym_of link")
        if why:
            reasons[(a, b)] = why
    return reasons


def homonym_risks(links: list[dict], glossary: dict[str, dict]) -> list[dict]:
    usage: dict[str, set[str]] = {}
    for link in links:
        usage.setdefault(link["term"], set()).add(link["system"])
    adjacent = {(a, b) for a, b, _ in edges(links)}
    found = []
    for (a, b), why in sorted(homonym_pairs(glossary, set(usage)).items()):
        same = sorted(usage[a] & usage[b])
        linked = sorted({
            tuple(sorted((s, t))) for s in usage[a] for t in usage[b]
            if s != t and tuple(sorted((s, t))) in adjacent
        })
        if same or linked:
            found.append({"pair": (a, b), "why": why, "same": same, "linked": linked})
    return found


def glossary_status(term: str, glossary: dict[str, dict]) -> str:
    return str(glossary[term].get("status")) if term in glossary else "missing from glossary"


def unapproved_terms(links: list[dict], glossary: dict[str, dict]) -> list[dict]:
    systems: dict[str, set[str]] = {}
    for link in links:
        systems.setdefault(link["term"], set()).add(link["system"])
    found = []
    for term in sorted(systems):
        status = glossary_status(term, glossary)
        if status != GLOSSARY_APPROVED:
            found.append({"term": term, "status": status, "systems": sorted(systems[term])})
    return found


def systems_without_links(notes: list[dict], links: list[dict]) -> list[str]:
    linked = {l["system"] for l in links}
    return sorted(system_name(n) for n in notes if system_name(n) not in linked)


def unused_terms(links: list[dict], glossary: dict[str, dict]) -> list[str]:
    used = {l["term"] for l in links}
    return sorted(
        t for t, fm in glossary.items()
        if str(fm.get("status")) == GLOSSARY_APPROVED and t not in used
    )


def links_without_source(notes: list[dict]) -> list[dict]:
    found = []
    for note in notes:
        for entry in note.get("concepts") or []:
            if entry.get("status") == "rejected" or str(entry.get("source") or "").strip():
                continue
            found.append({
                "system": system_name(note), "term": str(entry.get("term")),
                "status": str(entry.get("status")),
            })
    return sorted(found, key=lambda r: (r["system"], r["term"], r["status"]))


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(escape_cell(c) for c in r) + " |" for r in rows]
    return lines


def section(title: str, count: int, note: str, body: list[str]) -> list[str]:
    lines = [f"## {title} ({count})", "", note, ""]
    return lines + (body if count else ["None.", ""]) + ([""] if count else [])


def render(notes: list[dict], glossary: dict[str, dict]) -> str:
    links = approved_links(notes)
    conflicts = meaning_conflicts(links)
    homonyms = homonym_risks(links, glossary)
    unapproved = unapproved_terms(links, glossary)
    empty = systems_without_links(notes, links)
    unused = unused_terms(links, glossary)
    nosrc = links_without_source(notes)

    out = [
        "# Gap list", "",
        "Generated from approved `concepts:` entries in system notes and the glossary. "
        "Each finding is a prompt for a human decision, not a verdict.", "",
        "| check | findings |", "|---|---|",
        f"| meaning conflict | {len(conflicts)} |",
        f"| homonym risk | {len(homonyms)} |",
        f"| link to a term that is not Approved | {len(unapproved)} |",
        f"| system with no approved links | {len(empty)} |",
        f"| approved term used by no system | {len(unused)} |",
        f"| link with no source | {len(nosrc)} |", "",
    ]
    rows = [[c["term"], glossary_status(c["term"], glossary), r["system"], r["meaning"], r["source"]]
            for c in conflicts for r in c["rows"]]
    out += section(
        "Meaning conflict", len(conflicts),
        "One term id has different meaning text in different systems. "
        "Compare text only: a human decides whether the wording or the concept differs. "
        "An `Approved` glossary term suggests the wording differs; any other status suggests an open meaning.",
        table(["term", "glossary status", "system", "meaning", "source"], rows))
    rows = [[f"{a} / {b}", "; ".join(h["why"]), ", ".join(h["same"]) or "-",
             ", ".join(f"{s} - {t}" for s, t in h["linked"]) or "-"]
            for h in homonyms for a, b in [h["pair"]]]
    out += section(
        "Homonym risk", len(homonyms),
        "Different term ids that share a name or a `homonym_of` link and are used in one "
        "system or in two systems linked by a shared term.",
        table(["terms", "reason", "same system", "linked systems"], rows))
    rows = [[u["term"], u["status"], ", ".join(u["systems"])] for u in unapproved]
    out += section(
        "Link to a term that is not Approved", len(unapproved),
        "An approved link points to a glossary term whose status is not `Approved`, or to no term.",
        table(["term", "glossary status", "systems"], rows))
    out += section(
        "System with no approved links", len(empty),
        "The system note has no approved `concepts:` entry, so the map cannot place it.",
        [f"- {s}" for s in empty])
    out += section(
        "Approved term used by no system", len(unused),
        "The term is `Approved` in the glossary, but no current system note links to it.",
        [f"- {t}" for t in unused])
    rows = [[r["system"], r["term"], r["status"]] for r in nosrc]
    out += section(
        "Link with no source", len(nosrc),
        "A concept entry has no `source`, so its meaning cannot be traced.",
        table(["system", "term", "link status"], rows))
    return "\n".join(out).rstrip("\n") + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--systems", type=Path, required=True)
    parser.add_argument("--glossary", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--include-superseded", action="store_true")
    args = parser.parse_args(argv)
    for label, path in (("systems", args.systems), ("glossary", args.glossary / "terms")):
        if not path.is_dir():
            print(f"error: {label} directory not found: {path}", file=sys.stderr)
            return 2
    notes = current_systems(load_systems(args.systems), args.include_superseded)
    text = render(notes, load_glossary(args.glossary))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
