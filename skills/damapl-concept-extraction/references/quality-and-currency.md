---
title: "Quality and currency rules"
summary: "Canonical metadata, source handling, freshness, conflict, answer and confidentiality rules for the second brain."
version: "0.2"
date: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "DAMA Poland maintainers"
status: "candidate"
confidentiality: "public"
---

# Quality and currency rules

## Canonical metadata

Every managed markdown artifact has these fields:

- `summary`: one sentence describing the artifact.
- `owner`: a person or accountable role. An empty value is allowed only for a candidate glossary entry.
- `status`: `candidate`, `proposed`, `approved`, `review-needed` or `deprecated`.
- `updated`: the last content change date.
- `review_by`: the next human review date.
- `confidentiality`: `public`, `internal` or `restricted`.

Source notes also have `source_id`, `version`, `retrieved` and `hosted_model_allowed`. A superseding source adds `supersedes`. Notes derived from sources list stable IDs in `source_refs`.

Skill files keep the required `name` and `description` fields and also carry `summary`, `version`, `date`, `review_by`, `owner`, `status` and `confidentiality`.

## Sources and dates

1. Every claim names its source and retrieval date. No source means no claim.
2. Every source version has a stable `source_id`. Do not reuse an ID for changed content.
3. A skill past `review_by` is flagged for human review before use.

## Duplicates, conflicts and polysemy

4. Store the same fact once and link it to all supporting sources.
5. When sources make contradictory claims about the same concept, preserve both claims, mark a factual conflict and ask a human to resolve it.
6. When the same label names different concepts, preserve both source meanings and mark polysemy. Recommend a split instead of asking which definition to delete.
7. A proposed target concept that does not appear in a source remains an open gap. It becomes a candidate only after a dated human decision note names and defines it.
8. Prefer the source closer to the system of record, then the newer source, but state this choice in the answer. Do not remove the other provenance.

## Currency

9. When a new source version arrives, list every note whose `source_refs` includes the superseded ID. Mark those notes `review-needed`; do not rewrite their claims automatically.
10. A human chooses to update, keep or deprecate each affected note.
11. Do not delete governed knowledge. Mark it `deprecated` with a date and reason.

## Asking the human

12. Ask when a definition is ambiguous, an owner is unknown, sources conflict, a new target concept needs approval, or classification is unclear.
13. Escalation and approval questions must be short, propose a default when one is safe, and permit a yes or no answer. Discovery questions may be open ended. If no safe default exists, say so.

## Answer contract

14. Every answer contains:
   - a direct reply;
   - source paths or IDs with retrieval dates;
   - a confidence statement;
   - open doubts or `None`;
   - a classification line.
15. State when the sources do not support an answer. Do not infer a missing fact or number.
16. Separate observed source facts, human decisions and proposed gaps.

## Confidentiality and hosted models

17. Output confidentiality equals the highest classification among all inputs: `restricted` is higher than `internal`, which is higher than `public`.
18. The agent must not downgrade classification. Declassification requires explicit, dated human authorization recorded as a decision source.
19. Block public export if any dependency is `internal` or `restricted`, and identify the dependency that caused the block.
20. A source may be sent to an externally hosted model only when `hosted_model_allowed: true`. Missing permission means `false`. Restricted sources require explicit written approval for the named service and purpose.
21. Public examples use synthetic or public data only. Do not store credentials, tokens or personal data in notes.
