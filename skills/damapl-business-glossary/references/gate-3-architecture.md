---
title: "Gate 3 checklist: architecture"
summary: "Human checklist for gate 3: are the concept links, map, gaps and model-change decision ready; for the data architect who signs off."
updated: "2026-10-31"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "release-candidate"
confidentiality: "public"
---

# Gate 3 checklist: architecture

Run `python3 scripts/check_gate.py 3 --data DIR` from the damapl-model-change skill folder first. It checks that every approved `concepts:` entry points to an `Approved` glossary term, and that the map and gap list build without errors. It cannot judge whether a link is right or a model change is wise. You do that here.

Sign-off by: the data architect. Record it in `gates/signoff-3.md` yourself.

The synthetic demo fails this gate on purpose (`device` is `Under Review`, `dose-event` is `Draft`). Treat a failure as a question to answer: who settles each term, and until then should the link stay unapproved?

## Checklist

- [ ] The program check passed, or each failure has a written reason and an owner.
- [ ] You set each `approved` link yourself, after reading its meaning and source. An agent only proposes links as `proposed`.
- [ ] Each approved link cites a source that really says that.
- [ ] Every finding in the gap list has a decision: fix, accept, or ask the owner. Meaning conflicts are checked against the sources, since the script compares text only.
- [ ] You read the map as shared terms, not as observed data flows.
- [ ] For the model change, the diff, map and gaps support the proposal, every claim cites a source, and open questions have owners.
- [ ] The decision is recorded in `decision.md` by you. The agent did not write `approved`.
- [ ] Impact on other systems is understood and the owners of those systems are informed.

## Decision

Sign off only if links, gaps and the model-change decision are ready to act on. Otherwise list what stays open.
