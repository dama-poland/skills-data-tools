---
name: damapl-concept-extraction
description: "Pipeline step that proposes meanings of a term from sources: lists every meaning found with citations, flags factual conflicts and polysemy, and does not choose. Output feeds bg_draft as Draft terms. Use when a term or label needs its meanings collected from the sources before a human decides which one to record."
summary: "Pipeline step that proposes meanings of a term from sources with citations, never chooses among them, and feeds Draft terms to the glossary."
version: "0.3"
date: "2026-10-31"
updated: "2026-10-31"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "candidate"
confidentiality: "public"
---

# Concept extraction

This is the step of the damapl-business-glossary pipeline that proposes meanings from sources. It sits between `bg_discover` (finds candidate terms) and `bg_draft` (writes Draft terms); both scripts belong to the damapl-business-glossary skill. For a given term it lists every meaning found in the sources, each with a citation, and it does not choose among them. A human decides.

## Input

Use one or more source notes from `sources/` or the sources configured for `bg_discover`. Each input must carry canonical source metadata, including `source_id`, version, retrieval date, classification and hosted-model permission. Ask for missing metadata before processing.

Do not send a source to an externally hosted model unless its metadata says `hosted_model_allowed: true`.

## Steps

1. Read each source and list nouns that carry business meaning rather than technical column names.
2. For each term, record every meaning found: the label, a source-scoped definition, the system, the exact source location and the stable source ID.
3. Search the existing glossary (`terms/`) and `systems/` for recorded meanings.
4. Classify each comparison as one of:
   - `duplicate`: the same concept and compatible claim;
   - `factual-conflict`: the same concept with contradictory claims;
   - `polysemy`: the same label used for different concepts;
   - `new`: a source-backed concept not yet recorded;
   - `proposed-target`: a useful concept that is not present in the supplied sources.
5. Preserve every source-scoped meaning. For a factual conflict, show both claims and ask for a dated decision. For polysemy, recommend distinct names rather than asking which meaning to delete. Never pick a winner.
6. Keep a proposed target as an open gap. Draft it only after a human records a dated decision in `decisions/` using `templates/decision.md` (in this skill).
7. Hand the result to `bg_draft` as Draft terms (see `references/term-schema.md`). Set the source references to all contributing source IDs and the confidentiality to the highest input classification.
8. Return the candidate table and open questions using `references/answer-contract.md`.

## Status mapping

The v0.2 lowercase statuses map to the glossary lifecycle:

| v0.2 | Glossary |
|---|---|
| `candidate` | `Draft` |
| `proposed` | `Under Review` |
| `approved` | `Approved` |
| `deprecated` | `Deprecated` |

This step writes `Draft` only. Moving a term to `Under Review` happens only at a human's request, and `Approved` is a human decision recorded with a date. `Archived` is the final lifecycle state.

## Export guard

Refuse public export if any input or dependency is internal or restricted. Name the dependency that caused the refusal. Never downgrade classification without a dated declassification decision.

## Rules

- Every definition cites a source or a dated human decision. No source means no entry.
- Leave owner empty rather than guessing.
- Follow `references/quality-and-currency.md`.
