---
title: Update workflow
summary: How to update an existing glossary repo by diff, keeping ids stable, bumping versions and returning approved terms to review, for agents and maintainers.
---

# Update workflow

Updating never rewrites a term. It changes named fields or sections, shows the
diff, bumps the version, and leaves everything else byte for byte alone.

## Flow

1. Refresh candidates: `bg_discover.py --repo G` (sources come from
   `glossary.yaml`).
2. New terms: `bg_draft.py --repo G --top N`. Existing ids are skipped.
3. Changed meaning: `bg_update.py --repo G --from-sources` writes
   `.glossary/proposals.yaml`. It applies nothing.
4. Review the proposals. Delete the ones you reject. Agree each with the user.
5. Preview: `bg_update.py --repo G --patch FILE --dry-run` prints a unified
   diff per term.
6. Apply without `--dry-run`, then run `bg_validate.py --strict`.
7. Rebuild views with `bg_site.py`.

## Patch format

```yaml
- id: candidate
  set: {type: Role, last_reviewed: "2026-10-31"}
  add: {alternative_names: [Job Seeker]}
  remove: {related_terms: [recruiter]}
  definition: "One or two sentences."
  sections:
    What it is: "- Essential trait one"
  level: b          # a, b or c; b default; c for typography or link fixes
  reason: free text, ignored by the tool
```

## Guards

| Guard | Behavior |
|---|---|
| unknown id | error; update never creates terms |
| patch op without `id` | error |
| term whose frontmatter cannot be read | refused: fix the YAML by hand, then run `bg_validate.py` |
| `set`, `add` or `remove` of `id`, `created`, `created_by` | refused: ids and creation facts never change |
| `set`, `add` or `remove` of `version`, `version_date`, `changed_by` | refused: managed by the bump |
| `set`, `add` or `remove` of `approved_by`, `approved_on`, `approved_version` | always refused: a human records approval |
| `add` or `remove` of `status` | refused: status is a single value, change it with `set` |
| `set` of `status` other than `Draft` | refused unless `--allow-status` and `DAMAPL_HUMAN_APPROVAL=1` |
| profile `agent_status` other than `Draft` | refused before any change: the profile is a repo file and cannot grant approval |
| `--allow-status` without `DAMAPL_HUMAN_APPROVAL=1` | refused before any change |
| `level` other than `a`, `b` or `c` | refused, even when the op changes nothing |
| no real change | reported as `unchanged`, no bump |

`DAMAPL_HUMAN_APPROVAL=1` is a human-only signal. A person sets it in their
own shell when they decide a status change. An agent never sets it, never
asks for it to be exported in a command it runs, and never adds it to a
config, Makefile or CI file.

## Versions and approval

`b` bumps for any value or meaning change, `c` for editorial fixes, `a` only
when the structure of every term changes (`bg_update --bump-only ... --level a`
for each term). When the profile sets `approval_reset` and an Approved term gets
an `a` or `b` bump, `status` returns to `Under Review` (LIFE-06).

## Renaming a term

Change `name` with `set`. Keep `id`. If the old name should still be found, add
it to `alternative_names`. Never rename the file. Never edit the id: validation
reports `ID-03` for any id in `.glossary/ids.lock` that disappears.

## Removing a term

Do not delete. Set `status: Deprecated` and `successor_term`, later `Archived`.
Archived terms drop out of the site. A real deletion is a human decision made in
git, and it needs `.glossary/ids.lock` edited by hand.

## Relations cleanup

`bg_relations.py --dry-run` then without the flag drops redundant and mirrored
`related_terms` and caps them at three. Each changed term gets a `b` bump (use
`--no-bump` to skip).

## After the update

Do not commit for the user. Report which `terms/` files changed, the validation
result, and that `generated/` is gitignored.
