---
title: "Propose how to adopt Supply v2 device-model data"
summary: "Synthetic expected output of the model-change skill: a proposed, unapproved decision for the Supply v1 to v2 change, for the architect to review."
type: "decision"
decision_id: "DEC-2026-10-31-001"
status: "proposed"
owner: "Synthetic data architect"
created: "2026-10-31"
updated: "2026-10-31"
review_by: "2027-01-31"
confidentiality: "public"
source_refs:
  - "SUPPLY-ARCH-v1"
  - "SUPPLY-ARCH-v2"
  - "DEVICE-REGISTRY-ARCH-v1"
  - "CTMS-ARCH-v1"
  - "EDC-ARCH-v1"
  - "DEC-2026-10-24-001"
---

# Propose how to adopt Supply v2 device-model data

> Synthetic expected output, written by hand as a reference for the model-change skill. It is not a decision. Status is `proposed`; only the architect can approve.

## Decision

Proposal only. Inputs: `examples/expected/model-diff-supply-v1-v2.md`, `examples/expected/map.md`, `examples/expected/gaps.md`.

1. Supply: keep `device-model` as a linked concept in the Supply model. Supply v2 adds the field `device_model`, described as "Model code of the device packed in the kit" (SUPPLY-ARCH-v2; diff, body table row Kit / device_model).
2. Device Registry and Supply: keep one meaning for `device-model`. Both concept links use "Design version of the device" (DEVICE-REGISTRY-ARCH-v1, SUPPLY-ARCH-v2), and the gap list shows no meaning conflict for this term. The Supply field text still says "Model code of the device packed in the kit"; the steward should confirm that Supply stores the model code only, not a unit.
3. Glossary: do not use `device-unit` for the Supply field. The glossary marks `device-model` and `device-unit` as homonyms, and both appear in Device Registry (gaps: homonym risk).
4. Glossary: ask the data steward to settle `device`. CTMS defines it as a free-text note (CTMS-ARCH-v1) and EDC as a yes or no flag (EDC-ARCH-v1); the term is `Under Review` (gaps: link to a term that is not Approved).
5. Freshness: review notes that claim kits contain only drugs. Supply v2 states that such notes now require review (SUPPLY-ARCH-v2), and `supply-assessment` still cites SUPPLY-ARCH-v1.

## Reason

Supply v1 had no device field; Supply v2 adds a model code and supersedes v1 (diff, frontmatter `supersedes`). The model code is the same concept Device Registry holds as `device-model`, so the change creates a shared term between two systems (map, edge `device-registry` to `supply-v2`). The human decision `DEC-2026-10-24-001` keeps Device Model and Device Unit as separate concepts, which supports points 2 and 3.

## Scope

Impact on other systems, read from the map:

- Device Registry: owns the master data for `device-model`. It shares the term with Supply v2 (map). A shared term does not show that data flows between them; Device Registry has no interface to CTMS or EDC (DEVICE-REGISTRY-ARCH-v1).
- CTMS and EDC: they do not use `device-model`. They use `device` with different meanings and have no link to Device Registry (CTMS-ARCH-v1, EDC-ARCH-v1). Supply v2 sends shipment status to CTMS (SUPPLY-ARCH-v2), but the sources do not say that the model code reaches CTMS.
- Subject to unit: the sources do not define a link from a subject to a physical device unit. `Study Device Assignment` remains a proposed target concept (DEC-2026-10-24-001). Supply v2 does not close this gap, because it carries a model, not a unit.

Open questions:

- Does Supply need the model code only, or also the serial number of a unit? The sources do not say.
- Who owns the `device-model` master data when Supply and Device Registry both hold it? The sources name no owner.
- Should the Supply index note (`supply`) carry its own links, or stay an index? The gap list shows it with no approved links.
- `randomisation-number` is `Approved` but no system links to it. Is Supply the intended owner? The sources do not say.

## Approver

Pending: the architect decides. No approval has been given.
