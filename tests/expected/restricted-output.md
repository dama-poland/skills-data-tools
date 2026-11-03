---
title: "Expected restricted classification result"
summary: "Expected governance result when concept extraction uses a restricted source that cannot be sent to a hosted model."
owner: "Synthetic test maintainers"
status: "approved"
updated: "2026-10-24"
review_by: "2027-01-24"
confidentiality: "restricted"
source_refs:
  - "RESTRICTED-FIXTURE-v1"
---

# Expected restricted classification result

- Any derived entry has `confidentiality: restricted`.
- The input must not be sent to an externally hosted model because `hosted_model_allowed` is false.
- Public export is refused and identifies `RESTRICTED-FIXTURE-v1` as the blocking dependency.
- No automatic downgrade is allowed.
