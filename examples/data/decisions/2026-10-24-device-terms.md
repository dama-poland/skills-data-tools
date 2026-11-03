---
title: "Split device meanings and define the assignment gap"
summary: "Synthetic human decision that separates device model and unit meanings and names Study Device Assignment as a target concept."
type: "decision"
decision_id: "DEC-2026-10-24-001"
status: "approved"
owner: "Demo data owner"
created: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
confidentiality: "public"
source_refs:
  - "CTMS-ARCH-v1"
  - "EDC-ARCH-v1"
  - "DEVICE-REGISTRY-ARCH-v1"
---

# Split device meanings and define the assignment gap

## Decision

Keep `Device Model` and `Device Unit` as separate concepts. Add `Study Device Assignment` as a proposed target concept for linking a subject, study and physical device unit.

## Reason

The source systems use the label `device` for different concepts. None of the source notes defines the target assignment concept, so the dated human decision is its provenance.

## Scope

The decision applies only to the synthetic demo glossary.

## Approver

Demo data owner, 2026-10-24.
