---
title: Rules profile
summary: How rule profiles work, which rule checks exist and how the planned standard profile is meant to use them, which remain manual review, and how tiers are computed, for glossary maintainers.
---

# Rules profile

A profile is one YAML file. The repo copies its profile to `rules/profile.yaml`
at init, so it can be edited per repo without touching the skill.

```yaml
name: minimal   # default; `standard` is planned
options: {owners: true, integrations: false, require_what_it_is_not: true,
          owner_email_domain: ""}
types: [...]
statuses: [...]
template: {...}          # fields and defaults for new terms
sections: [...]          # body sections drafted for new terms
tiers: [...]             # Gold, Silver, Bronze
rules:
  - {id: DEF-01, check: sentence_max, params: {max: 2}}
```

Rule keys: `id`, `check`, `params`, `level` (MUST default, or SHOULD),
`group` (enabled when `options[group]` is true), `option` (same, for one rule),
`when` (`field` plus `equals`, `in` or `present`), `heuristic` (downgrades a
MUST to SHOULD), `enabled: false`.

Override options per repo in `glossary.yaml` under `profile_options`.

## Built-in checks

Term scope: `required`, `regex`, `enum`, `sentence_max`, `not_circular`,
`no_leading`, `section_nonempty`, `bullets_min`, `filename_id`, `title_case`,
`singular`, `not_acronym`, `paren_needs`, `when_then`, `forbidden_key`,
`forbidden_text`, `date`, `owner`, `concordance`, `external_cites`,
`approval`, `no_dash`, `polish`.

Corpus scope: `unique`, `resolves`, `bidirectional`, `relations`, `tree`,
`acyclic`, `related_oneway`, `ids_lock`.

A genuinely new kind of test needs a function in `bg_rules.py` registered in
`TERM_CHECKS` or `CORPUS_CHECKS`. Everything else is a profile edit.

## Standard profile coverage (planned)

The `standard` profile is planned and not shipped yet; it will be redesigned.
The sections below describe its intended basis. The `minimal`
profile is the default.

The `standard` profile will rest on DAMA-DMBOK (business glossary, owner and
steward roles, lifecycle) and on the terminology principles of ISO 704 and
ISO 1087 (one concept per term, a definition that names the broader concept,
no circular definitions, a permanent id).

Rule ids: ID (identity), NAME (naming), DEF (definition), TYPE
(classification), OWN (ownership), LIFE (lifecycle), REL (relations), SRC
(traceability), INT (integrations), FMT (format).

Checked by code:

| Group | Rules |
|---|---|
| Identity | ID-01 slug, ID-02 unique id, ID-03 id lock, ID-04 file name equals id |
| Naming | NAME-01 singular (heuristic), NAME-02 Title Case, NAME-03 not an acronym, NAME-04 unique name, NAME-05 homonym needs parentheses, NAME-06 unique acronyms |
| Definition | DEF-01 at most two sentences, DEF-02 not circular, DEF-03 not stated by exclusion, DEF-04 Description Details present, DEF-05 What it is present, DEF-06 no version or author lines in the body, DEF-07 What it is not present (option `require_what_it_is_not`) |
| Classification | TYPE-01 type from the list |
| Ownership | OWN-01..04 owners and creation fields (option `owners`), OWN-05 source origin (SHOULD), OWN-06..08 owner email domain (option `owner_email_domain`, off) |
| Lifecycle | LIFE-01 status, LIFE-02 successor for Deprecated, LIFE-03 version format, LIFE-04 version date, LIFE-05 changed_by, LIFE-06 approval reset |
| Relations | REL-01 links resolve, REL-02 and REL-03 bidirectional boundary and homonym links, REL-04 typed relations, REL-05 tree, REL-06 single parent (SHOULD), REL-07 acyclic, REL-08 one-way related terms |
| Traceability | SRC-01 term source, SRC-02 external terms cite a source, SRC-03 concordance entries |
| Integrations | INT-01 Confluence page id (SHOULD), INT-02 DataHub URN prefix; both behind the `integrations` option, off |
| Format | FMT-01 no em dash (SHOULD) |

Manual review (the checklist for a person or a review pass):

| Check | What to look at |
|---|---|
| Stands alone | the definition is understandable without opening another term |
| Essence only | no rationale, procedure, examples or history in the definition |
| Adds value | Description Details adds something, not a longer restatement |
| Positive form | the definition says what the concept is, in language readable outside the team, without system names |
| One home | one glossary per term; boundary terms cross-linked |
| Approval | status transitions happen by reviewed change, per term |
| Owners | `created_by` is never edited; owner confirmation is real |
| Mastership | views never feed changes back to the repo |

## Coverage caveats

- NAME-01 and NAME-02 are heuristics. NAME-01 only warns.
- DEF-02 flags a definition that opens with "<Name> is ...". The finding is
  real, not a tool error.
- Owner checks accept any email-shaped value. To restrict owners to one
  company domain, set `owner_email_domain` in `profile_options` to a regex
  such as `example\.com`. It is empty (off) by default.

## Tiers

Evaluated top down, first match wins.

| Tier | Needs |
|---|---|
| Bronze | id, name, type, definition; ID-01, DEF-01, 02, 03 and owner rules OWN-01, 02 pass |
| Silver | Bronze, `owner_confirmed: true`, a non-empty What it is |
| Gold | Silver, `status: Approved`, no MUST finding, reviewed within 12 months |

Below Bronze is reported as `Below`. The `minimal` profile drops the owner
requirements.

## Writing your own profile

Copy `assets/profiles/minimal.yaml`, change `types`, `rules` and `tiers`, set
`profile:` in `glossary.yaml`, run `bg_validate.py`. Keep rule ids stable;
never reuse an id for a different test.
