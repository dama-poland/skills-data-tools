---
title: "DAMA Poland skills (DAMA Day 2026 trial)"
summary: "Installable skill collection for data architects: second brain kickoff, business glossary, concept extraction, system map, gap list and model change, copied from data-architect-ai-tools v0.3."
version: "0.3-trial"
updated: "2026-11-03"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "draft"
confidentiality: "public"
---

# DAMA Poland skills (DAMA Day 2026 trial)

Six self-contained skills for data architects who work with AI agents on their own sources. The agent proposes; a human decides and stays accountable. Three quality gates sit between the steps, and a human signs off each one.

## Trial status

- Private repository in the `dama-poland` organisation while the trial runs. Making it public needs the same content review as `data-architect-ai-tools` (secrets, client data, blocklist scan) and both authors' agreement.
- The content is copied from `dama-poland/data-architect-ai-tools` v0.3. That repository stays unchanged.
- If the trial is dropped, the repository is archived.

## Install

```bash
npx skills add dama-poland/skills-data-tools --skill '*'                  # all skills
npx skills add dama-poland/skills-data-tools --skill 'damapl-business-glossary'
npx skills add ./skills-dama-day-2026 --skill '*'                            # local path (dev, CI)
```

Python 3.10 or later and PyYAML are needed to run the scripts (`pip install -r requirements.txt`). Details: [`docs/install.md`](docs/install.md).

## Skills

| Skill | What it does | Gate |
|---|---|---|
| [`damapl-second-brain-kickoff`](skills/damapl-second-brain-kickoff/SKILL.md) | Asks setup questions, creates the vault structure and `brain.md`; holds the answer contract, quality rules and freshness review | 1 |
| [`damapl-business-glossary`](skills/damapl-business-glossary/SKILL.md) | Discover, draft, update, validate and render a governed glossary (`bg_*` scripts); profile `minimal` | 2 |
| [`damapl-concept-extraction`](skills/damapl-concept-extraction/SKILL.md) | Lists every meaning of a term per source with citations; never chooses | |
| [`damapl-system-map`](skills/damapl-system-map/SKILL.md) | Proposes concept links in system notes; builds the system map from approved links | |
| [`damapl-gap-list`](skills/damapl-gap-list/SKILL.md) | Builds the gap list from approved links and the glossary | |
| [`damapl-model-change`](skills/damapl-model-change/SKILL.md) | Turns a model diff, map and gaps into a `decision.md` proposal; only a human approves | 3 |

Old names and paths: [`docs/mapping.md`](docs/mapping.md). Gates: [`docs/gates.md`](docs/gates.md).

## Planned (not created)

No folders or stub files exist for these.

| Planned skill | Origin |
|---|---|
| damapl-brain-interview, damapl-brain-ingest, damapl-brain-ask, damapl-brain-lint | architect-brain; needs the co-author's agreement and a content review first |
| damapl-draft-adr, damapl-impact-analysis, damapl-design-review, damapl-tech-radar-check | architect-tasks; not designed yet |

The `standard` glossary profile is also planned. Only `minimal` exists.

## Layout

```text
skills/damapl-*/     six skills: SKILL.md, references/, templates/, scripts/, assets/
shared/              canonical copies of shared files; never installed
examples/            synthetic demo data and expected outputs; never installed
tests/               unit, end-to-end, gate, scan and smoke tests
scripts/             lint.sh, sync_shared.py, check_shared_copies.py, test_install.sh
docs/                install.md, gates.md, mapping.md
.ai/                 optional path config for this repository's own tests
```

## Check

```bash
pip install -r requirements.txt
scripts/lint.sh
python3 scripts/check_shared_copies.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/scan_repo.py
scripts/test_install.sh        # needs Node.js and network once (pinned skills CLI)
```

Gate 3 fails on the synthetic demo on purpose (`device` is `Under Review`, `dose-event` is `Draft`). A failing gate is a prompt for a human decision (see `docs/gates.md`). To test your own agent and model, follow `tests/agent-smoke.md`.

## What this is not

- Not a source of truth: the second brain keeps essentials and links to sources.
- Metadata quality only, not business data quality.
- No live connectors and no publishing to external catalogues; the glossary exports `terms.json` and `glossary.csv`.
- All example data is synthetic.

## Licence

Apache License 2.0. See `LICENSE` and `NOTICE`. Copyright belongs to Arkadiusz Dąbkowski and Michał Krzyżanowski as individuals. DAMA Poland hosts the repository.
