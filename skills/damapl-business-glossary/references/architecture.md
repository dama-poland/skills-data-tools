---
title: Business glossary architecture
summary: Design note for the business-glossary skill covering the source-agnostic core, source adapters, repo layout and derived outputs, for maintainers and agents extending it.
---

# Architecture

Status: decided. Critical step: the split between core, adapters and views.

## Goal

One skill that builds or updates a glossary repo from any knowledge base, with
a lightweight `minimal` quality profile as the default (a `standard` profile is planned), and no dependency on any
company system.

## Three layers

```
sources ──adapters──▶ candidates ──draft──▶  CANONICAL REPO  ──build──▶ views
(vault, notes,        (ranked, merged,        terms/<id>.md             site, json,
 CSV, XLSX, docx,      not yet terms)         glossary.yaml             csv, a-z.md
 Confluence HTML)                             rules/profile.yaml
                                                   ▲
                                          validate / update / relations
```

1. Core (`bg_core.py`, `bg_rules.py`): term schema, parsing, surgical editing,
   rule engine, tiers. Knows nothing about where terms came from.
2. Adapters (`bg_adapters.py`): each turns one source kind into candidate
   dicts. Adding a source means one function and one registry entry.
3. Views (`bg_site.py`): read the repo, never write to it.

## Decisions

| Decision | Reason |
|---|---|
| The repo is canonical, views are derived | One-way flow from repo to views; avoids bidirectional sync conflicts |
| One Markdown file per term, id = file name | Diffable in git, reviewable, id cannot drift from the name (ID-04) |
| Ids are permanent and locked in `.glossary/ids.lock` | Changing an id breaks links and leaves orphaned terms |
| Rules are data (YAML profile), checks are code | Swap the standard per repo without touching Python |
| `minimal` is the default profile | `standard` (DMBOK, ISO 704/1087) is planned; integrations and owner domain are options, off by default |
| Updates are surgical text edits, not parse-and-dump | A rewrite churns every line and hides real changes |
| Discover proposes, draft creates, update patches | Three separate acts; nothing overwrites an existing term |
| Agents write `Draft` only | Approval stays a human decision (LIFE-06) |
| Static HTML with D3 inlined | Opens offline from a file, no server or network |
| History in git tags, no version folders | Git already keeps the history; version folders duplicate it |
| Publishing is not in this skill | Use the `terms.json` and `glossary.csv` exports with your own publishing tool |

## Repo layout

```
glossary/
  glossary.yaml          config: name, languages, profile, options, sources
  rules/profile.yaml     the active rule set (copied from assets/profiles)
  terms/<id>.md          canonical terms
  .glossary/
    candidates.yaml      ranked candidates from the last discover run
    proposals.yaml       update proposals (never applied automatically)
    ids.lock             every id that ever existed
  generated/             derived, gitignored by default
    site/index.html  terms.json  glossary.csv  a-z.md  validation.json
  Makefile  README.md
```

## Languages

`languages: [en]` or `[en, pl]`. With `pl`, drafts get `name_pl` and
`description_pl` frontmatter fields, the site shows an EN/PL switch, and
`polish_required: true` turns a missing Polish field into a SHOULD finding.
Term bodies stay in English.

## Out of scope

Publishing, DataHub URN generation, Confluence page sync, owner directory
lookups. The profile keeps the matching fields (`datahub_urn`,
`confluence_page_id`) as optional checks so other tools can use the repo.

## Known limits

- Plural and Title Case checks are heuristics; plural findings are SHOULD.
- Adapters extract candidates; they do not judge quality. A person or the
  model completes the definition sections.
- PDF is not read. Convert to text or docx first.
