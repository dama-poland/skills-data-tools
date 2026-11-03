---
title: "Expected Act 2 concept result"
summary: "Semantic fixture that distinguishes device polysemy from conflicting facts and requires a dated decision for the target assignment concept."
owner: "Synthetic demo maintainers"
status: "approved"
updated: "2026-10-24"
review_by: "2027-01-24"
confidentiality: "public"
---

# Expected Act 2 concept result

| Label | Source-scoped meaning | Classification |
|---|---|---|
| device | CTMS free-text delivery aid used in a study | polysemy |
| device | EDC yes or no indication that an injection aid was used | polysemy |
| device | Device Registry physical unit with a serial number | polysemy |
| Device Model | Device Registry design version; Supply v2 model packed in a kit | source-backed concept |
| Device Unit | Device Registry physical unit with a serial number | source-backed concept |
| Study Device Assignment | Link between a subject, study and physical device unit | proposed target backed by `DEC-2026-10-24-001` |

The result must preserve all three source meanings. It must not ask the human which meaning to delete. There is no contradictory factual claim in this fixture, so the label is polysemous rather than a factual conflict.

Before the decision note exists, `Study Device Assignment` remains an open gap and no glossary candidate may be emitted for it. After the supplied dated decision is loaded, it may be drafted with that decision ID as provenance.
