---
title: "Gate 2 checklist: glossary"
summary: "Human checklist for gate 2: are the glossary terms correct and approved; for the data steward who signs off."
updated: "2026-10-31"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "release-candidate"
confidentiality: "public"
---

# Gate 2 checklist: glossary

Run `python3 scripts/check_gate.py 2 --data DIR` from the damapl-business-glossary skill folder first. It runs `bg_validate` with the profile from `glossary.yaml` and checks that every term used by an approved concept link reaches at least the lowest tier. It cannot judge whether a definition is right. You do that here.

Sign-off by: the data steward. Record it in `gates/signoff-2.md` yourself.

## Checklist

- [ ] The program check passed, or each failure has a written reason.
- [ ] Each term you approve has a definition that you agree with, in one or two sentences, without circular wording.
- [ ] Each meaning cites a source, or a dated human decision where no source defines it.
- [ ] Where one label stands for several concepts, the glossary lists them as separate terms and links them as homonyms, rather than choosing one.
- [ ] Terms used by systems are `Approved`. Terms still `Draft` or `Under Review` are listed with an owner and a next step.
- [ ] You moved each term to `Approved` yourself and recorded the date. An agent only writes `Draft`.
- [ ] Term ids did not change. Renames changed the name only.
- [ ] Relations follow the tree rule: one structural parent, at most three one-way related terms.
- [ ] Exports (`terms.json`, `glossary.csv`) were rebuilt after the last change.

## Decision

Sign off only if every term that systems depend on is `Approved` by you. Otherwise list the open terms.
