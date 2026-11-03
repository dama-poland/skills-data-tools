---
title: "Supply (synthetic), v2"
summary: "Synthetic investigational product supply system after device-model data was added."
type: "source"
source_id: "SUPPLY-ARCH-v2"
version: "v2"
supersedes: "SUPPLY-ARCH-v1"
retrieved: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "Synthetic demo maintainers"
status: "approved"
confidentiality: "public"
hosted_model_allowed: true
concepts:
  - term: kit
    meaning: "Drug package with a randomised number"
    source: "SUPPLY-ARCH-v2"
    status: approved
  - term: site
    meaning: "Site that takes part in a study"
    source: "SUPPLY-ARCH-v2"
    status: approved
  - term: device-model
    meaning: "Design version of the device"
    source: "SUPPLY-ARCH-v2"
    status: approved
---

# Supply v2

Ships investigational kits to sites.

| Entity | Field | Meaning |
|---|---|---|
| Kit | kit_id | Drug package with a randomised number |
| Kit | device_model | Model code of the device packed in the kit |
| Shipment | site_id | Destination site |

Change from v1: Supply v1 had no device field. Notes claiming that kits contain only drugs now require review. Interfaces: sends shipment status to CTMS.
