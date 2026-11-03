---
name: damapl-second-brain-kickoff
description: "Sets up an architect's second brain by asking about goal, scope, loading, processing and retrieval, then creates the vault structure and brain.md. Use when an architect starts a new second-brain vault or needs the existing one checked against the kickoff questions."
summary: "Portable kickoff instructions for a fresh second-brain vault."
version: "0.2"
date: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "DAMA Poland maintainers"
status: "candidate"
confidentiality: "public"
---

# Second brain kickoff

Run from the vault root. Run the scripts from the folder this SKILL.md was loaded
from (written `<this skill folder>` below). First read these files in the same
folder: `references/second-brain-spec.md`,
`references/quality-and-currency.md` and `references/answer-contract.md`.

Ask one group at a time and wait for the answers. Discovery questions may be open ended. If an answer is vague, ask once more. Each prompt below has a suggested default or says that no safe default exists.

## 1. Goal

- What decision or deliverable should this brain support? Suggested default: a Business Glossary for one business area.
- Who will use it, and who owns it? No safe default; name an accountable person or role.

## 2. Scope

- Which area, systems or processes are in scope, and which are out? Suggested default: one process and its directly connected systems; everything else is out.
- Which confidentiality levels apply? What must never be stored? Suggested default: public and internal content only; no credentials or personal data.
- May any source be sent to an externally hosted model? Suggested default: no, unless its metadata explicitly says `hosted_model_allowed: true`.

## 3. Loading

- Which sources come first? Suggested default: data models for the systems in scope.
- Where do they live, in what format and how often do they change? No safe default; record the actual location, format and expected cadence.

## 4. Processing

- What should be extracted? Suggested default: concepts, relations, owners and business rules.
- Who approves a glossary entry? Suggested default: the architect proposes and the accountable data owner approves.

## 5. Retrieval

- Which five questions should the brain answer in its first week? No safe default; use questions tied to the stated deliverable.
- What must an answer contain? Suggested default: follow `references/answer-contract.md` without omissions.

## Output

1. Create these folders if absent: `sources/`, `systems/`, `glossary/`, `questions/`, `decisions/` and `inbox/`.
2. Write `brain.md` in the vault root with canonical metadata, the answers above, the folder layout and a first-week task list.
3. Mark every unanswered discovery item `[[open]]`.
4. Do not overwrite an existing file. Ask for approval before changing an existing `brain.md`.

## Rules

- Follow `references/quality-and-currency.md` and `references/answer-contract.md`.
- Never invent an answer for the user.
- Apply the highest input classification to every derived artifact.

## Gate 1 and freshness

- Program check: `python3 <this skill folder>/scripts/check_gate.py 1 --data DIR --answers FILE`. `DIR` holds `sources/`, `systems/`, `notes/`, `decisions/` and `glossary/`. Take the paths from `.ai/damapl.config.json` in the project root if it exists (keys `systems`, `decisions`), otherwise ask the user. The human checklist is `references/gate-1-second-brain.md`.
- Superseded sources: `python3 <this skill folder>/scripts/freshness-review.py VAULT` lists notes that cite a superseded source id; `--apply` marks them for review: it sets `review-needed` and adds one `review_reason`, but an approved note keeps its status (only the human changes it). Hidden folders are skipped.
- A passing gate is not a sign-off. Never write `gates/signoff-1.md`; the architect does.
