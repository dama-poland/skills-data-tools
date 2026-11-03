---
title: "EDC (synthetic)"
summary: "Synthetic electronic data capture system used in the demo."
type: "source"
source_id: "EDC-ARCH-v1"
version: "v1"
retrieved: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "Synthetic demo maintainers"
status: "approved"
confidentiality: "public"
hosted_model_allowed: true
concepts:
  - term: subject
    meaning: "Enrolled participant"
    source: "EDC-ARCH-v1"
    status: approved
  - term: dose-event
    meaning: "Administered drug dose captured on the case report form"
    source: "EDC-ARCH-v1"
    status: approved
  - term: device
    meaning: "Yes or no flag showing whether an injection aid was used"
    source: "EDC-ARCH-v1"
    status: approved
---

# EDC

Captures case report form data.

| Entity | Field | Meaning |
|---|---|---|
| Subject | subject_id | Same code as in CTMS |
| Dose event | dose_date, dose_amount | Administered drug dose |
| Dose event | device | Yes or no flag showing whether an injection aid was used |

Interfaces: receives subjects from CTMS. It has no link to the Device Registry.
