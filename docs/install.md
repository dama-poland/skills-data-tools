---
title: "Install"
summary: "How to install the damapl skills with npx skills, how the self-contained layout works, and what to do after an update."
updated: "2026-11-03"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "draft"
confidentiality: "public"
---

# Install

## Commands

```bash
npx skills add dama-poland/skills-dama-day-2026 --skill '*'        # all skills (needs repo access while the trial is private)
npx skills add dama-poland/skills-dama-day-2026 --skill 'damapl-business-glossary'
npx skills add ./skills-dama-day-2026 --skill '*'                  # local path (dev, CI)
npx skills add ./skills-dama-day-2026 --list                       # list without installing
```

`scripts/test_install.sh` runs the local-path form non-interactively with a pinned skills CLI version and tests the installed copies.

Requirements on the machine that runs the scripts: Python 3.10 or later and PyYAML (`pip install -r requirements.txt`). The agent runs the scripts; you do not need to.

## Self-contained skills

The installer copies one skill folder. Everything a skill uses sits inside it: scripts, references, templates, assets. A skill never reads `../`, the repo root or an absolute path. Scripts find their own files relative to `__file__`.

Files that several skills need (for example `check_gate.py`, `arch_common.py`, the answer contract) exist once in `shared/` and as identical copies in each skill that uses them. `scripts/sync_shared.py` writes the copies and `scripts/check_shared_copies.py` fails CI if any copy differs. Edit `shared/` only.

`shared/`, `examples/`, `tests/` and `docs/` are never installed. The scripts take data paths as arguments (`--systems`, `--glossary`, `--data`) and have no demo defaults. Gate 1 also needs `--answers FILE`.

## Optional `.ai/damapl.config.json`

A project may keep `.ai/damapl.config.json` in its root with `vault`, `glossary`, `systems`, `decisions`, `generated` and `glossaryProfile` (default `minimal`). It holds paths and choices only, no secrets (lint rejects any key containing `token`, `secret`, `password` or `key`). No skill needs it. Scripts never read it; the SKILL.md tells the agent to read it, with this order: explicit argument, then config, then ask the user. This repository's own `.ai/damapl.config.json` points at `examples/data`.

## After `npx skills update`

`bg_init.py` writes a Makefile with no machine paths, and puts the absolute path of the skill's `scripts/` folder in `.glossary/local.mk`, which it also adds to the new repo's `.gitignore`. A fresh clone, or a skill folder that an update moved, needs that one file fixed: edit `SK` in `.glossary/local.mk`, or run `make SK=<skill folder>/scripts validate`. The Makefile stops with a message when `SK` is not set. `glossary.yaml` holds no author unless `BG_AUTHOR` was set at init; the author is found when a term is written (`BG_AUTHOR`, then the config, then `git config user.email`, then `$USER`).

## Lint rules

`scripts/lint.sh` fails when a `SKILL.md` lacks `name` or `description`; the name differs from the folder or lacks the `damapl-` prefix; SKILL.md or a script contains `../`, an absolute path, `~/`, `${CLAUDE_PLUGIN_ROOT}` or a repo-root folder path; or a SKILL.md names a `references/`, `templates/`, `scripts/` or `assets/` file that does not exist in the skill.
