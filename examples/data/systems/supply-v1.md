---
title: "Supply (synthetic), v1"
summary: "Synthetic investigational product supply system before device-model data was added."
type: "source"
source_id: "SUPPLY-ARCH-v1"
version: "v1"
retrieved: "2026-09-01"
updated: "2026-09-01"
review_by: "2026-12-01"
owner: "Synthetic demo maintainers"
status: "approved"
confidentiality: "public"
hosted_model_allowed: true
concepts:
  - term: kit
    meaning: "Drug package with a randomised number"
    source: "SUPPLY-ARCH-v1"
    status: approved
  - term: site
    meaning: "Site that takes part in a study"
    source: "SUPPLY-ARCH-v1"
    status: approved
---

# Supply v1

Ships investigational drug kits to sites.

| Entity | Field | Meaning |
|---|---|---|
| Kit | kit_id | Drug package with a randomised number |
| Shipment | site_id | Destination site |

Supply v1 has no device field. Interfaces: sends shipment status to CTMS.
