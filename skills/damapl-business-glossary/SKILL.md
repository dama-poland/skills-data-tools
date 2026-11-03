---
name: damapl-business-glossary
description: "Creates or updates a business-glossary repo (one Markdown file per term) from knowledge-base sources such as an Obsidian second brain, note folders, Confluence exports, Word, CSV or Excel, then validates it against a swappable rule profile and builds an offline HTML site with search, A-Z, a relationship graph and type views. The default profile is `minimal`; `standard` (DAMA-DMBOK, ISO 704, ISO 1087) is planned. Use when the user wants to start a glossary, extract terms from notes, update terms by diff, validate terms or build the glossary site. Not for publishing: it exports terms.json and glossary.csv for your own publishing tool."
version: "0.3"
date: "2026-10-31"
summary: "Skill that builds, updates, validates and renders a governed business glossary from knowledge-base sources, for agents and data architects."
owner: "Data Architect AI Tools maintainers"
status: "candidate"
updated: "2026-10-31"
review_by: "2027-01-31"
confidentiality: "public"
---

# Business glossary

Turns scattered knowledge into a governed glossary repo plus a derived offline
viewer. The repo is canonical; every other output is a view generated from it.
Integration fields (DataHub URN, Confluence page id) and an owner email
domain are optional checks, off by default.

Scripts live in `scripts/` and need Python 3 with PyYAML (`pip install pyyaml`).
Run every script with `--help`; every writing script supports `--dry-run`.

## Hard rules

- Ids never change. A rename changes `name`, never `id`. Validation fails with
  ID-03 if an id that once existed is gone (`.glossary/ids.lock`).
- Agents write only `status: Draft`. Approval is a human act.
  `bg_update --allow-status` works only with the human-only signal
  `DAMAPL_HUMAN_APPROVAL=1`. Never set that variable, never put it in a
  command, config, Makefile or CI file, and never ask to have it set for
  you. `approved_by`, `approved_on` and `approved_version` are refused
  always.
- Update by diff. Edit the named fields or sections, never rewrite a term, and
  bump the version. Never use the model to copy or move files; use `cp`/`mv`.
- A term carries the highest `confidentiality` of its sources (a source
  without one counts as `internal`) and lists every source in
  `source_refs`. Never lower `confidentiality` or remove a `source_refs`
  entry; `bg_update` refuses both. Declassification is a dated human
  decision.
- Publishing is out of scope; use the `terms.json` / `glossary.csv` exports
  with your own publishing tool.
- Review prose that leaves the machine (plain wording, no invented facts)
  before you publish it.

## Step 0: ask the user (always, before any work)

Ask these as yes/no or pick-one questions, each with a default:

If `.ai/damapl.config.json` exists in the project root, read it first: `glossary` gives the repo path, `vault` the default source and `glossaryProfile` the rule profile. An explicit answer from the user wins over the config. The config is optional.

1. Create a new repo or update an existing one? (default: ask for the path)
2. Where is the repo and what is it called? (default: `./glossary`)
3. Which sources should I read? A list, one per line, as `kind:path`.
   Kinds: `obsidian`, `folder`, `csv`, `xlsx`, `confluence`, `docx`. A bare path
   is auto-detected, and anything unknown falls back to `folder`.
   Default for a second brain: the vault root. No dedicated vault is assumed.
4. Languages: English only, or English plus an optional Polish field?
   (default: English only; switchable later in `glossary.yaml`)
5. Rule profile: `minimal` (default) or the user's own YAML. `standard` is
   planned and refused by `bg_init`.
6. Author id to stamp as `changed_by`/owner (default: git email).
7. Which integration options apply? Confluence page id, DataHub URN, owner
   email domain (default: all off).

## Workflow: create

```bash
S=<this skill folder>/scripts   # the scripts/ folder of the folder this SKILL.md was loaded from
python3 $S/bg_init.py ./glossary --name "Acme Glossary" --languages en,pl
python3 $S/bg_discover.py --repo ./glossary --ask      # or --source kind:path
python3 $S/bg_draft.py --repo ./glossary --top 25      # Draft terms only
python3 $S/bg_relations.py --repo ./glossary --dry-run # tree, not mesh
python3 $S/bg_validate.py --repo ./glossary --lock
python3 $S/bg_site.py --repo ./glossary                # generated/site/index.html
```

1. `bg_init` scaffolds `glossary.yaml`, `rules/profile.yaml`, `terms/`,
   Makefile, README. It refuses to overwrite an existing repo.
2. `bg_discover` (with the `damapl-concept-extraction` skill, which lists every meaning
   found per term with citations and does not choose) reads the sources through adapters, merges duplicates by id,
   ranks by mentions, and writes `.glossary/candidates.yaml`. Show the user the
   top candidates and let them veto or set `accept: true`.
3. `bg_draft` creates term files from accepted candidates. It never overwrites
   an existing term. Placeholders say `TODO` and show up as `DRAFT-TODO`.
4. Complete each draft: a 1-2 sentence definition, Description Details,
   What it is, What it is not. Do it with `bg_update`, not by retyping files.
5. `bg_validate` reports MUST and SHOULD findings and the tier (Bronze, Silver,
   Gold) of every term when the profile defines tiers. `--lock` records the ids that must never disappear.
6. `bg_site` builds the viewer and the CSV, JSON and A-Z outputs.

## Workflow: update

See `references/update-workflow.md`. Short form:

```bash
python3 $S/bg_discover.py --repo G --source obsidian:path/to/vault   # refresh
python3 $S/bg_update.py --repo G --from-sources    # proposals only, no writes
python3 $S/bg_update.py --repo G --patch .glossary/proposals.yaml --dry-run
python3 $S/bg_update.py --repo G --patch .glossary/proposals.yaml
python3 $S/bg_validate.py --repo G --strict && python3 $S/bg_site.py --repo G
```

A patch op names an `id` and any of `set`, `add`, `remove`, `definition`,
`sections`, `level`. The tool edits only those lines, shows a unified diff,
and bumps `version`, `version_date` and `changed_by`. Any `set`, `add` or
`remove` of `id`, `created`, `created_by`, the bump fields or the approval
fields is refused, and `status` changes only through `set`. An Approved term edited at level a or b returns to
Under Review when the profile enables `approval_reset`.

## Outputs (all derived, in `generated/`)

| File | What |
|---|---|
| `site/index.html` | single offline page, D3 inlined: search, A-Z, graph, type/category/status/tier views, per-term pages, EN/PL switch |
| `terms.json`, `glossary.csv` | flat exports for other tools |
| `a-z.md` | Markdown index linking to the term files |
| `validation.json` | violations and tiers from the last build |

Only terms with `confidentiality: public` reach the site, `terms.json`,
`glossary.csv` and `a-z.md`. A term without the field counts as not public.
`bg_site` prints every excluded term and drops links to it from the views.

Open `generated/site/index.html` with a double click. No server, no network.

## Rule profiles

Rules live in YAML (`rules/profile.yaml` in the repo), not in code. Each rule
is `{id, level, check, params}` using a built-in check. Swap the profile by
pointing `profile:` in `glossary.yaml` at another file, or override options:

```yaml
profile_options: {owners: false, require_what_it_is_not: false}
```

The default is `minimal` (identity, one-sentence definition, resolvable links).
The `standard` profile is planned: it will be redesigned from DAMA-DMBOK,
ISO 704 and ISO 1087 and will cover identity, naming,
definition, classification, ownership, lifecycle, relations, traceability and
tiers. Until then `bg_init --profile standard` stops with a clear message.
Rules that need human judgment stay in `references/rules-profile.md`.

## Ontology method

Tree, not mesh: one structural parent per term (`is_a` or `has_a`), at most two
`related_terms`, one-way. `bg_relations` removes mirrored and redundant links.
Details in `references/ontology-method.md`.

## References

- `references/architecture.md`: core, adapters, repo layout, outputs
- `references/term-schema.md`: frontmatter fields and body sections
- `references/rules-profile.md`: profile format, planned `standard` coverage, tiers
- `references/source-adapters.md`: adapters and how to add one
- `references/update-workflow.md`: diff-based update, ids, versioning
- `references/ontology-method.md`: relations and the tree rule

## Gate 2

Program check, run from this skill folder:

```bash
python3 <this skill folder>/scripts/check_gate.py 2 --data DIR
```

`DIR` holds `systems/` and `glossary/`; take the paths from `.ai/damapl.config.json` in the project root if it exists (keys `systems`, `glossary`), otherwise ask the user. The human checklist is `references/gate-2-glossary.md`. A passing gate is not a sign-off; the data steward writes `gates/signoff-2.md`, never the agent.

## Tests

The end-to-end test (a synthetic second-brain vault through init, discover, draft, validate, update, relations and site under the `minimal` profile, and a check that `standard` is refused) runs in the source repository CI, not in the installed copy.
