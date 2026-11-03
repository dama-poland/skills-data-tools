---
title: "Gate 1 checklist: second brain"
summary: "Human checklist for gate 1: are the sources complete enough to answer from; for the data architect who signs off."
updated: "2026-10-31"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "release-candidate"
confidentiality: "public"
---

# Gate 1 checklist: second brain

Run `python3 scripts/check_gate.py 1 --data DIR --answers FILE` from the damapl-second-brain-kickoff skill folder first. It checks that every note in `sources/` and every source note in `systems/` has an owner, a date and a classification, and that sample answers follow the answer contract. It cannot judge content. You do that here.

Sign-off by: the data architect. Record it in `gates/signoff-1.md` yourself.

## Checklist

- [ ] The program check passed, or each failure has a written reason.
- [ ] The sources cover the systems in scope. No system you rely on is missing.
- [ ] Each owner is a real person or team who can still answer for the source.
- [ ] Each retrieval or update date is recent enough for the decisions you will make. Notes past `review_by` are renewed or marked.
- [ ] Each classification is right. Derived notes carry the highest classification of their inputs.
- [ ] Sources set to `hosted_model_allowed: true` may really go to a hosted model. Restricted and internal sources stay with local models.
- [ ] Superseded sources are marked, and derived notes that cite them are reviewed (run `scripts/freshness-review.py` of the damapl-second-brain-kickoff skill).
- [ ] You asked three real questions and checked the cited facts against the sources. Citations are correct, uncertainty is stated, and gaps are reported as gaps.
- [ ] No client data, credentials or personal data in the sources you intend to share.

## Decision

Sign off only if the sources are complete enough for the questions you will ask. Otherwise list what is missing and who adds it.
