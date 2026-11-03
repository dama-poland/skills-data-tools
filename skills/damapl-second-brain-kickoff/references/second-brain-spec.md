---
title: "Second brain specification"
summary: "Specification for an architect's second brain, including source metadata, two skills, governed answers and Business Glossary output."
version: "0.2"
date: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "DAMA Poland maintainers"
status: "candidate"
confidentiality: "public"
---

# Second brain specification

## 1. Purpose

Help an architect entering a new area to find sourced knowledge and keep it current. The tangible output is a Business Glossary. The second brain is the tool; the glossary is the goal.

This framework does not provide a full semantic layer, replace a data catalog or answer without sources.

## 2. Architecture

```text
Sources  ->  Skills  ->  Knowledge store  ->  Answers / Glossary
(models,     (kickoff,   (markdown notes,      (cited reply,
 docs,        extract)    one concept or        glossary entry,
 interviews)              system per note)      gap list)
```

## 3. Sources

Start with system data models and schema exports, then add architecture documents, process documents and interview notes. Each source note follows the canonical metadata in `references/quality-and-currency.md`, including a stable source ID, version, retrieval date, classification and hosted-model permission.

## 4. Skills

A skill is a folder with `SKILL.md`. This release contains two skills:

| Skill | Job |
|---|---|
| `damapl-second-brain-kickoff` | Asks setup questions and creates the vault structure and `brain.md` |
| `damapl-concept-extraction` | Proposes source-scoped business concepts and distinguishes conflicts, polysemy and open target concepts |

The user invokes a skill by asking the agent to read the named `SKILL.md` file and follow it from the vault root. This does not depend on an agent-specific installation path.

## 5. Knowledge store

Use plain markdown files with YAML front matter, one concept or system per file. The kickoff creates `sources/`, `systems/`, `glossary/`, `questions/`, `decisions/` and `inbox/`.

Every managed note uses the canonical metadata fields. Derived notes list stable source IDs in `source_refs`.

## 6. Answers

Every answer follows `references/answer-contract.md`: direct reply, sources and retrieval dates, confidence, open doubts and classification. If evidence is missing or conflicting, the answer says so. It does not fill the gap with a guess.

## 7. Business Glossary output

Entries follow `templates/glossary-entry.md` of the damapl-business-glossary skill. The lifecycle is `candidate` to `proposed` to `approved` to `deprecated`. Only a human moves an entry to `approved`.

Source meanings remain visible. A human may approve a new target concept by recording a dated decision with `templates/decision.md`.

## 8. Roles

- The architect owns the brain, approves entries and resolves escalations.
- A business or data owner confirms definitions.
- The agent drafts, links, checks and asks.

## 9. Acceptance checks

- A fresh vault can be created by following only `README.md`.
- A question about connected systems returns an answer that meets the answer contract.
- The same label used for different concepts is marked as polysemy without deleting either meaning.
- Loading Supply v2 identifies notes that cite Supply v1 and marks them for review.
- A restricted input produces restricted output, and public export is refused.
