"""Shared helpers for the data architecture design scripts.

Loads system notes, parses their YAML frontmatter and returns concept links
in a deterministic order. Requires Python 3.10+ and PyYAML.
"""

from __future__ import annotations

from pathlib import Path

import yaml

APPROVED = "approved"
VALID_STATUSES = ("proposed", "approved", "rejected")


class NoteError(ValueError):
    """Raised when a note has missing or malformed frontmatter."""


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise NoteError(f"missing frontmatter: {path}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise NoteError(f"unclosed frontmatter: {path}")
    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise NoteError(f"frontmatter is not a mapping: {path}")
    return data


def load_systems(systems_dir: Path) -> list[dict]:
    """Return frontmatter dicts of all notes in systems_dir, sorted by file name."""
    notes = []
    for path in sorted(Path(systems_dir).glob("*.md"), key=lambda p: p.name):
        note = parse_frontmatter(path)
        note["_file"] = path.name
        notes.append(note)
    return notes


def system_name(note: dict) -> str:
    """Display name: file stem without the version suffix, e.g. supply-v2 -> supply-v2."""
    return Path(note["_file"]).stem


def superseded_ids(notes: list[dict]) -> set[str]:
    return {str(n["supersedes"]) for n in notes if n.get("supersedes")}


def current_systems(notes: list[dict], include_superseded: bool = False) -> list[dict]:
    if include_superseded:
        return list(notes)
    gone = superseded_ids(notes)
    return [n for n in notes if n.get("source_id") not in gone]


def approved_links(notes: list[dict]) -> list[dict]:
    """Approved concept entries as dicts, sorted by term, system, source."""
    links = []
    for note in notes:
        for entry in note.get("concepts") or []:
            if entry.get("status") != APPROVED:
                continue
            links.append({
                "term": str(entry["term"]),
                "system": system_name(note),
                "meaning": " ".join(str(entry.get("meaning") or "").split()),
                "source": str(entry.get("source") or ""),
            })
    return sorted(links, key=lambda l: (l["term"], l["system"], l["source"], l["meaning"]))


def load_glossary(glossary_dir: Path) -> dict[str, dict]:
    """Return term frontmatter keyed by term id, read from <glossary_dir>/terms/*.md."""
    terms = {}
    for path in sorted((Path(glossary_dir) / "terms").glob("*.md"), key=lambda p: p.name):
        fm = parse_frontmatter(path)
        terms[str(fm.get("id", path.stem))] = fm
    return terms


def split_note(path: Path) -> tuple[dict, str]:
    """Return (frontmatter, body) of a note."""
    text = Path(path).read_text(encoding="utf-8")
    fm = parse_frontmatter(Path(path))
    end = text.find("\n---\n", 4)
    return fm, text[end + 5:]
