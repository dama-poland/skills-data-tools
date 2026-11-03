---
title: Term schema
summary: Frontmatter fields and body sections of a glossary term file, with which profile requires what, for authors and agents writing terms.
---

# Term schema

A term is `terms/<id>.md`: YAML frontmatter, an H1 equal to `name`, a
definition paragraph, then fixed `##` sections.

```markdown
---
id: customer-journey
name: Customer Journey
type: Process
status: Draft
...
---

# Customer Journey

One or two sentences that state what the term means.

## Description Details

Rationale, usage or scope. Not a longer restatement of the definition.

## What it is

- essential characteristic

## What it is not

- Not X; that is Y
```

## Frontmatter

| Field | Meaning | Rules |
|---|---|---|
| `id` | permanent lowercase slug, equals the file name | ID-01..04; never changes |
| `name` | singular, Title Case, expanded form | NAME-01..05 |
| `name_pl` | optional Polish name | only with `pl` in languages |
| `description_pl` | optional Polish definition | same |
| `type` | one value from the profile's type list | TYPE-01 |
| `category` | optional free grouping for the category view | none |
| `acronyms` | short forms, unique across the repo | NAME-06 |
| `alternative_names` | synonyms in active use | none |
| `status` | Draft, Under Review, Approved, Deprecated, Archived | LIFE-01; agents write Draft |
| `term_source` | INTERNAL or EXTERNAL | SRC-01, SRC-02 |
| `source_origin` | where the definition came from | OWN-05 |
| `created_by`, `created` | set once, never edited | OWN-04 |
| `business_owner`, `technical_owner`, `data_steward` | one named person each | OWN-01, 02, 03 (profile option `owners`) |
| `owner_confirmed` | true only after the owners accepted the role | Silver tier |
| `concordance` | list of `{url, label}` source citations, no duplicate urls | SRC-03 |
| `related_terms` | at most 2, one-way | REL-01, REL-08 |
| `relations` | `is_a`, `has_a`, `values`, `realized_by`, `implemented_by` | REL-04..07 |
| `homonym_of` | other meanings that share the base name | NAME-05, REL-03 |
| `boundary_term_ref` | counterpart term in another perspective | REL-02 |
| `successor_term` | required when Deprecated | LIFE-02 |
| `last_reviewed` | ISO date | tiers |
| `version`, `version_date`, `changed_by` | managed by the bump | LIFE-03..05 |
| `approved_version` | version at last approval, or null | LIFE-06 |
| `approved_by`, `approved_on` | optional: the human who approved and the ISO date of the decision; written by a human, never by an agent | none |
| `confluence_page_id`, `datahub_urn` | optional integrations | INT-01, 02 (option `integrations`) |

The profile's `template:` block decides which fields a new term gets and in
which order. A field a profile does not list is allowed but unchecked.

## Version rule (a.b.c)

- `a`: structure generation of the whole glossary; bump together.
- `b`: any value or prose meaning changed.
- `c`: typography, formatting, link repair only.

`bg_update` and `bg_relations` bump `b` by default; pass `level: c` for
editorial fixes.

## Types

Default list: Entity, Record, Event, Metric, Role, Process, Product,
Component, Pattern, Protocol, Concept. The `minimal` profile adds System and
Document and drops the types it does not need. Edit `types:` in the repo profile.
