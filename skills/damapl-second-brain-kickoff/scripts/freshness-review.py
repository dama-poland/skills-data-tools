#!/usr/bin/env python3
"""Find notes affected by superseded source IDs and optionally mark them for review."""

import argparse
import os
import re
from pathlib import Path


def frontmatter(text):
    if not text.startswith("---\n"):
        return {}, None
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, None
    block = text[4:end]
    data = {}
    current_list = None
    for line in block.splitlines():
        list_item = re.match(r"^\s+-\s+[\"']?([^\"']+?)[\"']?\s*$", line)
        if list_item and current_list:
            data.setdefault(current_list, []).append(list_item.group(1))
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip().strip('"\'')
        if value:
            data[key] = value
            current_list = None
        else:
            data[key] = []
            current_list = key
    return data, end


def mark_review_needed(path, superseded_id, replacement_id):
    text = path.read_text(encoding="utf-8")
    data, end = frontmatter(text)
    if end is None:
        raise ValueError(f"missing front matter: {path}")
    if data.get("status") == "review-needed":
        return
    updated = re.sub(
        r'(?m)^status:\s*["\']?[^\n"\']+["\']?\s*$',
        'status: "review-needed"',
        text[:end],
        count=1,
    )
    reason = f'review_reason: "{superseded_id} was superseded by {replacement_id}"\n'
    updated = updated + "\n" + reason + text[end:]
    path.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("vault", help="vault root")
    parser.add_argument("--apply", action="store_true",
                        help="mark affected notes review-needed")
    args = parser.parse_args()
    root = Path(args.vault).resolve()

    replacements = {}
    documents = []
    for path in sorted(root.rglob("*.md")):
        if ".demo-history" in path.relative_to(root).parts:
            continue
        text = path.read_text(encoding="utf-8")
        data, _ = frontmatter(text)
        documents.append((path, data))
        if data.get("supersedes") and data.get("source_id"):
            replacements[data["supersedes"]] = data["source_id"]

    affected = []
    for path, data in documents:
        refs = data.get("source_refs", [])
        if isinstance(refs, str):
            refs = [refs]
        for old_id, new_id in replacements.items():
            if old_id in refs:
                affected.append((path, old_id, new_id))
                if args.apply:
                    mark_review_needed(path, old_id, new_id)

    for path, old_id, new_id in affected:
        action = "marked review-needed" if args.apply else "requires review"
        print(f"{path.relative_to(root)}: {action}; {old_id} -> {new_id}")
    print(f"affected notes: {len(affected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
