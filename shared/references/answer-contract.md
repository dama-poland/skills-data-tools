---
title: "Answer contract"
summary: "Required structure for every governed answer produced from second-brain sources."
version: "0.2"
date: "2026-10-24"
updated: "2026-10-25"
review_by: "2027-01-24"
owner: "DAMA Poland maintainers"
status: "candidate"
confidentiality: "public"
---

# Answer contract

Return every governed answer in this order:

1. `Answer`: a direct response supported by the cited sources.
2. `Sources`: source path or stable ID, version and retrieval date for every claim.
3. `Confidence`: `high`, `medium` or `low`, followed by one sentence explaining why.
4. `Open doubts`: unresolved questions, or `None`.
5. `Classification`: the highest classification among all inputs.

If the sources do not answer the question, write `The supplied sources do not establish this.` Do not guess.

Before using an externally hosted model, verify `hosted_model_allowed: true` on every input. Before public export, verify that every dependency is public.
