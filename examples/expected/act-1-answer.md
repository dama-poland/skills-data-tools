---
title: "Expected Act 1 answer"
summary: "Semantic fixture for the cited answer about synthetic system connections and the missing device-unit assignment."
owner: "Synthetic demo maintainers"
status: "approved"
updated: "2026-10-24"
review_by: "2027-01-24"
confidentiality: "public"
---

# Expected Act 1 answer

## Answer

CTMS sends subject and visit data to EDC. Supply sends shipment status to CTMS. Device Registry has no interface to CTMS or EDC. The supplied sources do not define a field that links a subject to a physical device unit.

## Sources

- `sources/ctms.md`, `CTMS-ARCH-v1`, retrieved 2026-10-24.
- `sources/edc.md`, `EDC-ARCH-v1`, retrieved 2026-10-24.
- `sources/device-registry.md`, `DEVICE-REGISTRY-ARCH-v1`, retrieved 2026-10-24.
- `sources/supply-v2.md`, `SUPPLY-ARCH-v2`, retrieved 2026-10-24.

## Confidence

High for what the four synthetic source notes contain. Low for any process or interface not represented in those notes.

## Open doubts

The sources do not say whether an external process records the assignment outside these systems.

## Classification

Public.
