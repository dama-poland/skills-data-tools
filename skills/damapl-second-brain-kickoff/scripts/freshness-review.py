#!/usr/bin/env python3
"""Find notes affected by superseded source IDs and optionally mark them for review.

Front matter is read with yaml.safe_load. Notes in hidden folders (a name that
starts with a dot, such as .obsidian) are skipped. With --apply an affected note
gets `status: "review-needed"` and one `review_reason` line, except that an
approved note keeps its status and only gets the review_reason; applying again
changes nothing. A note that cannot be read is reported on stderr, the others
are still processed, and the exit code is 1.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

APPROVED = "approved"
REVIEW_NEEDED = "review-needed"


def frontmatter(text):
    """Return (data, end offset of the block); (None, None) if there is none."""
    if not text.startswith("---\n"):
        return None, None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, None
    data = yaml.safe_load(text[4:end])
    return (data if isinstance(data, dict) else {}), end


def read_note(path):
    return frontmatter(path.read_text(encoding="utf-8"))


def reason_text(superseded_id, replacement_id):
    return f"{superseded_id} was superseded by {replacement_id}"


def replace_or_add(block, key, value):
    """Set `key: "value"` in a front matter block; replace only a one-line value."""
    line = f"{key}: {json.dumps(value, ensure_ascii=False)}"
    lines = block.split("\n")
    for i, current in enumerate(lines):
        if current.startswith(f"{key}:"):
            lines[i] = line
            return "\n".join(lines)
    return block + "\n" + line


def mark_review_needed(path, superseded_id, replacement_id):
    """Mark one note; return True if the file changed."""
    text = path.read_text(encoding="utf-8")
    data, end = frontmatter(text)
    if end is None:
        raise ValueError(f"missing front matter: {path}")
    block = text[4:end]
    reason = reason_text(superseded_id, replacement_id)
    existing = data.get("review_reason")
    if existing is None or str(existing).strip() == "":
        new_reason = reason
    elif reason in str(existing):
        new_reason = str(existing)
    else:
        new_reason = f"{existing}; {reason}"
    if str(data.get("status", "")).strip().casefold() not in (APPROVED, REVIEW_NEEDED):
        block = replace_or_add(block, "status", REVIEW_NEEDED)
    if new_reason != existing:
        block = replace_or_add(block, "review_reason", new_reason)
    updated = text[:4] + block + text[end:]
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("vault", help="vault root")
    parser.add_argument("--apply", action="store_true",
                        help="mark affected notes for review (approved notes keep their status)")
    args = parser.parse_args()
    root = Path(args.vault).resolve()

    replacements = {}
    documents = []
    unreadable = 0
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts[:-1]):
            continue
        try:
            data, _ = read_note(path)
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            print(f"warning: skipped {relative}: cannot read front matter "
                  f"({exc.__class__.__name__})", file=sys.stderr)
            unreadable += 1
            continue
        if data is None:
            continue
        documents.append((path, data))
        if data.get("supersedes") and data.get("source_id"):
            replacements[str(data["supersedes"])] = str(data["source_id"])

    affected = []
    for path, data in documents:
        refs = data.get("source_refs") or []
        if not isinstance(refs, list):
            refs = [refs]
        refs = [str(r) for r in refs]
        for old_id, new_id in replacements.items():
            if old_id in refs:
                affected.append((path, old_id, new_id))
                if args.apply:
                    mark_review_needed(path, old_id, new_id)

    for path, old_id, new_id in affected:
        action = "marked for review" if args.apply else "requires review"
        print(f"{path.relative_to(root)}: {action}; {old_id} -> {new_id}")
    print(f"affected notes: {len(affected)}")
    return 1 if unreadable else 0


if __name__ == "__main__":
    raise SystemExit(main())
