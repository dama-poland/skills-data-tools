---
title: "CTMS (synthetic)"
summary: "Synthetic clinical trial management system used in the demo."
type: "source"
source_id: "CTMS-ARCH-v1"
version: "v1"
retrieved: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "Synthetic demo maintainers"
status: "approved"
confidentiality: "public"
hosted_model_allowed: true
concepts:
  - term: study
    meaning: "Unique study code"
    source: "CTMS-ARCH-v1"
    status: approved
  - term: subject
    meaning: "Enrolled participant"
    source: "CTMS-ARCH-v1"
    status: approved
  - term: site
    meaning: "Site that takes part in a study"
    source: "CTMS-ARCH-v1"
    status: approved
  - term: visit
    meaning: "Planned or actual subject visit"
    source: "CTMS-ARCH-v1"
    status: proposed
  - term: device
    meaning: "Free-text note for the delivery aid used in the study"
    source: "CTMS-ARCH-v1"
    status: approved
---

# CTMS

Manages studies, sites and subject visits.

| Entity | Field | Meaning |
|---|---|---|
| Study | study_id | Unique study code |
| Subject | subject_id | Enrolled participant |
| Visit | visit_date | Planned or actual visit |
| Study | device | Free-text note for the delivery aid used in the study |

Interfaces: sends subject and visit data to EDC daily. Receives kit shipment status from Supply.
