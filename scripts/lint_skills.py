#!/usr/bin/env python3
"""Lint the skill folders (docs/install.md, "Lint rules").

Usage:
    lint_skills.py [--root DIR]

Checks:
  - every skills/*/SKILL.md has frontmatter with `name` and `description`;
  - `name` equals the folder name, starts with `damapl-`, is lowercase kebab-case, at most 64 characters;
  - a skill folder holds only SKILL.md, references/, templates/, scripts/ and assets/;
  - SKILL.md, the scripts and every file under references/, templates/ and
    assets/ use no `../`, no absolute or home paths, no `${CLAUDE_PLUGIN_ROOT}`
    and no repo-root folder (examples/, shared/, docs/, tests/, second-brain/,
    data-architecture-design/, business-glossary/, skills/);
  - scripts do not climb above their skill folder (`parents[2]` or higher);
  - every references/, templates/, scripts/ or assets/ path named in a SKILL.md exists inside the skill;
  - .ai/damapl.config.json has no key containing token, secret, password or key.

Exit code 0 means clean, 1 means findings. Requires Python 3.10 or later and PyYAML.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_ENTRIES = {"SKILL.md", "references", "templates", "scripts", "assets"}
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPO_ROOT_FOLDERS = ("examples", "shared", "docs", "tests", "second-brain",
                     "data-architecture-design", "business-glossary", "skills")
FORBIDDEN = {
    "parent folder (../)": re.compile(r"\.\./"),
    "absolute path": re.compile(r"(?<![\w:/.])/(?:Users|home|tmp|var|etc|opt|usr|mnt|srv)/"),
    "home path (~/)": re.compile(r"(?<![\w])~/"),
    "plugin root variable": re.compile(r"CLAUDE_PLUGIN_ROOT"),
    "repo-root folder": re.compile(r"(?<![\w./<>-])(?:%s)/[\w.-]" % "|".join(REPO_ROOT_FOLDERS)),
    "climbs above the skill folder": re.compile(r"parents\[\s*[2-9]"),
}
# Text that looks like a path but is not one the skill reads:
#  - bg_site.py writes a Markdown link from generated/a-z.md to terms/ (output text);
#  - bg_discover.py documents a user-supplied vault path in its usage example;
#  - source-adapters.md tells a maintainer where to add a test in the source
#    repository; the skill never reads that folder.
ALLOWED_LINES = (
    re.compile(r"\]\(\.\./terms/"),
    re.compile(r"--source obsidian:~/vault "),
    re.compile(r"`tests/test_glossary_e2e\.py` of the source repository"),
)
SKIPPED_DIRS = {"__pycache__"}
SKILL_PATH = re.compile(r"(?<![\w.-])((?:references|templates|scripts|assets)/[\w.-]+(?:/[\w.-]+)*)")
SECRET_KEY = re.compile(r"token|secret|password|key", re.I)


def frontmatter(text: str):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else None


def forbidden_hits(label: str, text: str) -> list[str]:
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("#!") or any(allowed.search(line) for allowed in ALLOWED_LINES):
            continue
        for kind, pattern in FORBIDDEN.items():
            if pattern.search(line):
                found.append(f"{label}:{number}: {kind}")
    return found


def folder_hits(folder: Path, root: Path) -> list[str]:
    """Every file in the skill except SKILL.md: scripts get the same path rules
    as the prose, and references, templates and assets are read by the agent, so
    they must not point outside the folder either. Binary files are skipped."""
    found = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        if path.name == "SKILL.md" or set(path.relative_to(folder).parts) & SKIPPED_DIRS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found += forbidden_hits(path.relative_to(root).as_posix(), text)
    return found


def lint_skill(folder: Path, root: Path) -> list[str]:
    rel = folder.relative_to(root).as_posix()
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        return [f"{rel}: SKILL.md is missing"]
    found = []
    text = skill_md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return [f"{rel}/SKILL.md: frontmatter is missing or not a mapping"]
    for key in ("name", "description"):
        if not str(fm.get(key) or "").strip():
            found.append(f"{rel}/SKILL.md: frontmatter has no {key}")
    name = str(fm.get("name") or "")
    if name != folder.name:
        found.append(f"{rel}/SKILL.md: name {name!r} does not equal the folder name")
    if not name.startswith("damapl-"):
        found.append(f"{rel}/SKILL.md: name does not start with damapl-")
    if not NAME.match(name) or len(name) > 64:
        found.append(f"{rel}/SKILL.md: name is not lowercase kebab-case of at most 64 characters")
    for entry in sorted(p.name for p in folder.iterdir()):
        if entry not in SKILL_ENTRIES:
            found.append(f"{rel}/{entry}: not allowed in a skill folder")
    found += forbidden_hits(f"{rel}/SKILL.md", text)
    found += folder_hits(folder, root)
    mentioned = {m.group(1).rstrip(".,:;)") for m in SKILL_PATH.finditer(text)}
    for path in sorted(mentioned):
        if not (folder / path).exists():
            found.append(f"{rel}/SKILL.md: mentions {path}, which does not exist in the skill")
    return found


def lint_config(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{rel}: invalid JSON: {error}"]

    def keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield str(key)
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    return [f"{rel}: key {key!r} looks like a secret" for key in keys(data) if SECRET_KEY.search(key)]


def lint(root: Path) -> list[str]:
    found = []
    folders = sorted(p for p in (root / "skills").iterdir() if p.is_dir())
    if not folders:
        found.append("skills/: no skill folders")
    for folder in folders:
        found += lint_skill(folder, root)
    config = root / ".ai" / "damapl.config.json"
    if config.is_file():
        found += lint_config(config, root)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    found = lint(args.root.resolve())
    print("\n".join(found) if found else "lint passed")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
