---
title: "Name mapping"
summary: "Old paths and names in data-architect-ai-tools v0.3 and the new damapl-* skill folders, for users of the old repository."
updated: "2026-11-03"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "draft"
confidentiality: "public"
---

# Name mapping

| Old path in data-architect-ai-tools v0.3 | Old name | New folder | Source version |
|---|---|---|---|
| `second-brain/skills/second-brain-kickoff/` | second-brain-kickoff | `skills/damapl-second-brain-kickoff/` | 0.2 |
| `business-glossary/` (root SKILL.md) | business-glossary | `skills/damapl-business-glossary/` | 0.3 |
| `business-glossary/skills/concept-extraction/` | concept-extraction | `skills/damapl-concept-extraction/` | 0.3 |
| `data-architecture-design/skills/system-map/` | system-map | `skills/damapl-system-map/` | 0.1.0 |
| `data-architecture-design/skills/gap-list/` | gap-list | `skills/damapl-gap-list/` | 0.1.0 |
| `data-architecture-design/skills/model-change/` | model-change | `skills/damapl-model-change/` | 0.1.0 |

Only skill names changed. Script names (`bg_*.py`, `map_build.py`, `gaps_build.py`, `model_diff.py`, `check_gate.py`), file formats, rule profiles and output names are the same.

## Where the old shared files went

| Old path | New location |
|---|---|
| `gates/check_gate.py`, `gates/answer_contract.py` | `scripts/` of damapl-second-brain-kickoff, damapl-business-glossary, damapl-model-change |
| `gates/gate-<n>-*.md` | `references/` of the same three skills |
| `gates/README.md` | `docs/gates.md` |
| `data-architecture-design/scripts/arch_common.py` | `scripts/` of damapl-second-brain-kickoff, damapl-business-glossary, damapl-system-map, damapl-gap-list, damapl-model-change |
| `data-architecture-design/scripts/map_build.py` | `scripts/` of damapl-system-map, damapl-gap-list, damapl-model-change |
| `data-architecture-design/scripts/gaps_build.py` | `scripts/` of damapl-gap-list, damapl-model-change |
| `data-architecture-design/scripts/model_diff.py` | `scripts/` of damapl-model-change |
| `second-brain/rules/*.md` | `references/` of damapl-second-brain-kickoff and damapl-concept-extraction |
| `second-brain/spec/second-brain-spec.md` | `references/second-brain-spec.md` of damapl-second-brain-kickoff |
| `second-brain/templates/decision.md` | `templates/` of damapl-concept-extraction and damapl-model-change |
| `second-brain/scripts/freshness-review.py` | `scripts/` of damapl-second-brain-kickoff |
| `business-glossary/references/term-schema.md` | `references/` of damapl-business-glossary and damapl-concept-extraction |
| `business-glossary/tests/` | `tests/test_glossary_e2e.py` and `tests/fixtures/` |

## Changed calls

| Old | New |
|---|---|
| `python3 data-architecture-design/scripts/map_build.py` | `python3 <skill folder>/scripts/map_build.py --systems DIR` |
| `python3 data-architecture-design/scripts/gaps_build.py` | `python3 <skill folder>/scripts/gaps_build.py --systems DIR --glossary DIR` |
| `python3 gates/check_gate.py 1` | `python3 <kickoff folder>/scripts/check_gate.py 1 --data DIR --answers FILE` |
| `python3 gates/check_gate.py 2` | `python3 <glossary folder>/scripts/check_gate.py 2 --data DIR` |
| `python3 gates/check_gate.py 3` | `python3 <model-change folder>/scripts/check_gate.py 3 --data DIR` |

The demo defaults (`examples/data`, `examples/expected/act-1-answer.md`) were removed so that installed skills never depend on demo data.
