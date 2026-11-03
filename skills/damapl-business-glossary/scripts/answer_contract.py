"""Deterministic checks for the answer contract (references/answer-contract.md).

Shared by check_gate.py and the repository smoke checker. The contract requires five
parts in a fixed order: Answer, Sources, Confidence, Open doubts, Classification.
These checks look at structure and markers only. They cannot judge whether an
answer is true; that stays with the human.
"""

from __future__ import annotations

import re

SECTIONS = ("Answer", "Sources", "Confidence", "Open doubts", "Classification")
CONFIDENCE_LEVELS = ("high", "medium", "low")
CLASSIFICATIONS = ("public", "internal", "restricted")
SOURCE_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-v\d+\b")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NO_ANSWER = "The supplied sources do not establish this."

_NAMES = "Answer|Sources|Confidence|Open doubts|Classification"
# Three heading forms: "## Name", "**Name**" (optional colon), "Name:". Plain prose that
# merely starts with one of these words is not a heading.
_HEADING = re.compile(
    r"(?im)^[ \t]*(?:"
    r"#{1,6}[ \t]*(?P<h>" + _NAMES + r")[ \t]*:?[ \t]*$"
    r"|\*\*(?P<b>" + _NAMES + r"):?\*\*:?"
    r"|(?P<c>" + _NAMES + r"):"
    r")"
)


def _name(match: re.Match) -> str:
    raw = match.group("h") or match.group("b") or match.group("c")
    return next(s for s in SECTIONS if s.lower() == raw.lower())


def split_sections(text: str) -> dict[str, str]:
    """Return {section name: body text} for the first occurrence of each contract part."""
    found = []
    for match in _HEADING.finditer(text):
        found.append((_name(match), match.start(), match.end()))
    found.sort(key=lambda item: item[1])
    sections: dict[str, str] = {}
    for index, (name, _start, end) in enumerate(found):
        stop = found[index + 1][1] if index + 1 < len(found) else len(text)
        sections.setdefault(name, text[end:stop].strip())
    return sections


def check_answer(text: str, known_source_ids: set[str] | None = None,
                 classification_of: dict[str, str] | None = None) -> list[str]:
    """Return a list of problems; an empty list means the answer follows the contract."""
    problems: list[str] = []
    sections = split_sections(text)
    for name in SECTIONS:
        if name not in sections:
            problems.append(f"missing part: {name}")
    if problems:
        return problems

    positions = [_heading_pos(text, name) for name in SECTIONS]
    if positions != sorted(positions):
        problems.append("parts are not in contract order")

    if not sections["Answer"]:
        problems.append("Answer is empty")

    sources = sections["Sources"]
    ids = sorted(set(SOURCE_ID.findall(sources)))
    if not ids and NO_ANSWER not in sections["Answer"]:
        problems.append("Sources cites no source id")
    if not DATE.search(sources) and NO_ANSWER not in sections["Answer"]:
        problems.append("Sources has no retrieval date")
    if known_source_ids is not None:
        unknown = [i for i in ids if i not in known_source_ids]
        if unknown:
            problems.append("Sources cites unknown source id: " + ", ".join(unknown))

    confidence = sections["Confidence"].lower()
    if not any(re.match(r"\W*" + level + r"\b", confidence) for level in CONFIDENCE_LEVELS):
        problems.append("Confidence does not start with high, medium or low")

    if not sections["Open doubts"]:
        problems.append("Open doubts is empty (write None if there are none)")

    stated = sections["Classification"].lower()
    stated_level = next((c for c in CLASSIFICATIONS if re.search(r"\b" + c + r"\b", stated)), None)
    if stated_level is None:
        problems.append("Classification is not public, internal or restricted")
    elif classification_of:
        rank = {c: i for i, c in enumerate(CLASSIFICATIONS)}
        needed = max((rank.get(classification_of.get(i, "public"), 0) for i in ids), default=0)
        if rank[stated_level] < needed:
            problems.append(
                "Classification is lower than the highest classification of the cited sources"
            )
    return problems


def _heading_pos(text: str, name: str) -> int:
    for match in _HEADING.finditer(text):
        if _name(match) == name:
            return match.start()
    return -1
