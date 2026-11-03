#!/usr/bin/env python3
"""Validate supplied metadata and core governance fixtures."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON = {"summary", "owner", "status", "updated", "review_by", "confidentiality"}
SOURCE = COMMON | {"source_id", "version", "retrieved", "hosted_model_allowed"}
SKILL = COMMON | {"name", "description", "version", "date"}


def keys(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"missing front matter: {path.relative_to(ROOT)}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError(f"unclosed front matter: {path.relative_to(ROOT)}")
    return set(re.findall(r"(?m)^([A-Za-z_][A-Za-z0-9_-]*):", text[4:end]))


def require(path, required):
    missing = required - keys(path)
    if missing:
        raise AssertionError(
            f"{path.relative_to(ROOT)} missing metadata: {', '.join(sorted(missing))}"
        )


CONCEPT_STATUSES = {"proposed", "approved", "rejected"}
CONCEPT_FIELDS = ("term", "meaning", "source", "status")


def frontmatter(path):
    import yaml  # PyYAML is a runtime requirement (SPEC section 9)

    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    return yaml.safe_load(text[4:end]) or {}


def known_source_ids():
    ids = set()
    for path in list((ROOT / "examples" / "data").rglob("*.md")) + sorted(
        (ROOT / "tests" / "fixtures").glob("*.md")
    ):
        source_id = frontmatter(path).get("source_id")
        if source_id:
            ids.add(str(source_id))
    return ids


def check_concepts():
    known = known_source_ids()
    for path in sorted((ROOT / "examples" / "data" / "systems").glob("*.md")):
        rel = path.relative_to(ROOT)
        concepts = frontmatter(path).get("concepts")
        if concepts is None:
            continue
        if not isinstance(concepts, list):
            raise AssertionError(f"{rel}: concepts must be a list")
        for index, entry in enumerate(concepts):
            if not isinstance(entry, dict):
                raise AssertionError(f"{rel}: concepts[{index}] must be a mapping")
            missing = [f for f in CONCEPT_FIELDS if not entry.get(f)]
            if missing:
                raise AssertionError(f"{rel}: concepts[{index}] missing {', '.join(missing)}")
            if entry["status"] not in CONCEPT_STATUSES:
                raise AssertionError(
                    f"{rel}: concepts[{index}] invalid status {entry['status']!r}"
                )
            if str(entry["source"]) not in known:
                raise AssertionError(
                    f"{rel}: concepts[{index}] unknown source_id {entry['source']!r}"
                )


def main():
    check_concepts()
    for path in sorted((ROOT / "examples" / "data" / "systems").glob("*.md")):
        require(path, SOURCE)
    for path in sorted(ROOT.glob("skills/*/SKILL.md")):
        require(path, SKILL)
    require(ROOT / "examples" / "data" / "notes" / "supply-assessment.md",
            COMMON | {"source_refs"})
    require(ROOT / "examples" / "data" / "decisions" / "2026-10-24-device-terms.md",
            COMMON | {"decision_id", "source_refs"})
    restricted_path = ROOT / "tests" / "fixtures" / "restricted-source.md"
    require(restricted_path, SOURCE)

    v2 = (ROOT / "examples" / "data" / "systems" / "supply-v2.md").read_text(encoding="utf-8")
    note = (ROOT / "examples" / "data" / "notes" / "supply-assessment.md").read_text(encoding="utf-8")
    if 'supersedes: "SUPPLY-ARCH-v1"' not in v2:
        raise AssertionError("Supply v2 does not supersede the stable v1 ID")
    if '"SUPPLY-ARCH-v1"' not in note:
        raise AssertionError("freshness fixture does not cite Supply v1")

    restricted = restricted_path.read_text(encoding="utf-8")
    expected_restricted = (ROOT / "tests" / "expected" / "restricted-output.md").read_text(encoding="utf-8")
    if 'confidentiality: "restricted"' not in restricted or "hosted_model_allowed: false" not in restricted:
        raise AssertionError("restricted fixture must forbid hosted-model use")
    if "Public export is refused" not in expected_restricted:
        raise AssertionError("restricted expected output must block public export")

    rules = (ROOT / "skills" / "damapl-second-brain-kickoff" / "references" / "quality-and-currency.md").read_text(encoding="utf-8")
    required_phrases = [
        "highest classification among all inputs",
        "hosted_model_allowed: true",
        "factual conflict",
        "mark polysemy",
        "dated human decision",
    ]
    for phrase in required_phrases:
        if phrase not in rules:
            raise AssertionError(f"governance rule missing: {phrase}")

    print("repository validation passed: canonical metadata, supply versions, freshness, restricted classification, concept links and governance rules")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print(f"repository validation failed: {error}", file=sys.stderr)
        sys.exit(1)
