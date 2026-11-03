---
title: "Device Registry (synthetic)"
summary: "Synthetic device master data and complaints system used in the demo."
type: "source"
source_id: "DEVICE-REGISTRY-ARCH-v1"
version: "v1"
retrieved: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "Synthetic demo maintainers"
status: "approved"
confidentiality: "public"
hosted_model_allowed: true
concepts:
  - term: device-unit
    meaning: "Physical unit with a serial number"
    source: "DEVICE-REGISTRY-ARCH-v1"
    status: approved
  - term: device-model
    meaning: "Design version of the device"
    source: "DEVICE-REGISTRY-ARCH-v1"
    status: approved
  - term: complaint
    meaning: "Complaint that references a device unit"
    source: "DEVICE-REGISTRY-ARCH-v1"
    status: proposed
---

# Device Registry

Stores master data for device models and manufactured units, plus complaints.

| Entity | Field | Meaning |
|---|---|---|
| Device | device_id | A physical unit with a serial number |
| Device model | model_code | Design version of the device |
| Complaint | device_id | Unit referenced by the complaint |

Interfaces: none to CTMS or EDC. Complaints are exported monthly as a spreadsheet.
