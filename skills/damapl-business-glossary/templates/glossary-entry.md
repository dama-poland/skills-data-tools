---
title: "<Term>"
summary: "<One sentence describing the term and where it is used.>"
type: "glossary-entry"
status: "Draft"
owner: ""
steward: ""
created: "YYYY-MM-DD"
updated: "YYYY-MM-DD"
review_by: "YYYY-MM-DD"
confidentiality: "<highest input classification>"
source_refs:
  - "<stable source ID or dated decision ID>"
---

# <Term>

This template is replaced by the single term schema in
`../references/term-schema.md`. A term is the file `terms/<id>.md`, created by
`bg_draft.py` rather than by hand, with the lifecycle `Draft`, `Under Review`,
`Approved`, `Deprecated` and `Archived`. Agents write `Draft` only, and term
ids never change.

Mapping from the v0.2 statuses: `candidate` is `Draft`, `proposed` is
`Under Review`, `approved` is `Approved`, `deprecated` is `Deprecated`.

Use the body sections that the schema defines (definition, Description
Details, What it is, What it is not). Keep one meaning per term and cite the
source of each claim.
