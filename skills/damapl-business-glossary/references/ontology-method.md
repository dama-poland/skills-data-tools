---
title: Ontology method
summary: The tree-not-mesh method for term relations and the generic rules the relations tool enforces, for glossary authors and agents.
---

# Ontology method

## Target shape

- A tree, not a mesh. Each term has one structural parent: `is_a` (subtype) or
  `has_a` (part).
- At most two plain `related_terms` per term, only where no typed relation fits.
  Typical: a link to the hub term, or to the other side of a market.
- `related_terms` is one-way. Store the link on the more specific term, pointing
  at the hub. Never store it on both, and never repeat a typed relation as a
  plain link.
- No plain link where a typed chain already connects the terms. If CV `is_a`
  Document and Candidate `has_a` Document, a CV to Candidate link is redundant.
- Allowed typed keys: `is_a`, `has_a`, `values`, `realized_by`,
  `implemented_by`. Targets must exist and never be the term itself.
- `is_a` and `has_a` graphs must be acyclic; at most two `is_a` parents; no
  term under both `is_a` and `has_a` of the same target.

```yaml
related_terms: [job-offer]      # max 2, one-way
relations:
  is_a: [candidate-document]
  has_a: [candidate-cv]
```

## Steps per domain

1. Pick the seed terms (a domain slice). Edit only those; their neighbors are
   link targets.
2. Propose relations for each seed term with the catalog of names and
   definitions in view. Record evidence quoted from the definitions.
3. Review: decide event subtypes and `has_a` on the core entity explicitly.
4. Write the final relations by hand with `bg_update.py --patch`, one op per
   term (`set: {relations: {...}}`).
5. Run `bg_relations.py` to drop mirrored and redundant links.
6. Run `bg_validate.py --strict`; REL-04..08 must be clean.
7. Rebuild the site and look at the graph: one root per tree, few cross links.

## What discovery does with links

`bg_discover` turns wikilinks into candidate `links`. `bg_draft` copies at most
two per term and drops mirrored pairs. These are plain `related_terms`, a
starting point. Typed `is_a` and `has_a` need a decision from a person or a
review pass; the tools never guess them.

## Where the method stops

Cross-glossary relations (`realized_by`, `implemented_by`) are only for terms
that directly represent each other. External vocabularies (Schema.org, ESCO)
are not used.
