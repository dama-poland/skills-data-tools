---
title: "Quality gates"
summary: "How the three quality gates work in the skills collection: a program check, a human checklist and a human-only sign-off file; for architects, stewards and agents."
updated: "2026-11-03"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "draft"
confidentiality: "public"
---

# Quality gates

Each gate has a program check and a human check. The program check finds what a script can find. The human check decides whether the result is good enough to rely on.

Each gate runs from one skill. `check_gate.py` sits in three skills as an identical copy, and a gate whose helper scripts are missing in that skill exits with code 2.

| Gate | Skill that runs it | Program check (run from the skill folder) | Human checklist | Human signs off |
|---|---|---|---|---|
| 1. Second brain | damapl-second-brain-kickoff | `python3 scripts/check_gate.py 1 --data DIR --answers FILE` | `references/gate-1-second-brain.md` | Architect: sources are complete enough |
| 2. Glossary | damapl-business-glossary | `python3 scripts/check_gate.py 2 --data DIR` | `references/gate-2-glossary.md` | Data steward: terms are `Approved` |
| 3. Architecture | damapl-model-change (holds the map, gaps and diff scripts) | `python3 scripts/check_gate.py 3 --data DIR` | `references/gate-3-architecture.md` | Architect: `decision.md` for the model change |

## What the program checks

- Gate 1: every source note, derived note and decision has an owner, a date (`updated` or `retrieved`) and a `confidentiality` value. The sample answer has the five answer-contract parts in order, cites known source ids with a retrieval date, states a confidence level, and does not state a lower classification than its sources.
- Gate 2: `bg_validate` reports no MUST findings for the glossary, using the profile named in its `glossary.yaml`. Every term used by an approved `concepts:` entry reaches at least the lowest tier of that profile.
- Gate 3: every approved `concepts:` entry points to a glossary term with status `Approved`. `map_build.py` and `gaps_build.py` run without errors (output goes to a temporary folder).

Options: `--data DIR` is required and holds `systems/`, `notes/`, `decisions/` and `glossary/`. `--systems DIR` and `--glossary DIR` override the two sub-folders. Gate 1 also requires `--answers FILE`. There are no defaults: the demo data in this repository is `examples/data`, with the sample answer `examples/expected/act-1-answer.md`. Exit code 0 means all program checks passed, 1 means at least one failed, 2 means the gate could not run.

## The demo fails gate 3 on purpose

The synthetic demo has `device` as `Under Review` and `dose-event` as `Draft`, yet approved concept links use both. Gate 3 therefore fails with exit code 1, and gates 1 and 2 pass. This is the point of the demo: a failing gate is a prompt for a human decision. The steward settles the two terms (approve, split or replace them), or the architect keeps the links unapproved. Nobody edits the check to make it pass.

CI runs gate 3 on the demo and asserts that it fails with exactly these two terms. If you change the demo data so that it passes, update that CI step in the same change.

## Sign-off

A passing program check is not a sign-off. A person records the human decision in `gates/signoff-<n>.md` in the project that holds the data (for example `gates/signoff-2.md`), with their name and the date.

An agent never writes a sign-off file, never copies the template below into a `signoff-*.md` file, and never changes a gate check to get a pass. `tests/check_smoke.py` fails if an agent run created a sign-off file.

Template (copy it by hand into `gates/signoff-<n>.md` after you have done the human check):

```markdown
---
title: "Gate <n> sign-off"
summary: "Human sign-off for gate <n>, recorded by the named person."
gate: <n>
name: "<full name of the person who signs off>"
role: "<architect or data steward>"
date: "<YYYY-MM-DD>"
---

# Gate <n> sign-off

I ran `check_gate.py <n>` and completed the checklist in
`references/gate-<n>-<name>.md`.

Result of the program check: <pass or fail, with the output pasted below>

Findings I accept, with the reason: <none, or list>

Signed: <name>, <date>
```
