---
title: "Synthetic demo runbook"
summary: "Reproducible two-act demo with four fictional systems, expected outputs, freshness scenario and non-destructive reset."
version: "0.2"
updated: "2026-10-25"
review_by: "2027-01-24"
owner: "DAMA Poland maintainers"
status: "release-candidate"
confidentiality: "public"
---

# Synthetic demo runbook

This demo uses four fictional systems. Nothing comes from a client or real company. The `device` examples and the missing subject-to-unit link are synthetic demo facts, not client evidence.

## Create a fresh demo vault

From the repository root:

```sh
examples/setup.sh /tmp/data-architect-demo
cd /tmp/data-architect-demo
```

The setup script refuses to overwrite a non-empty directory. It copies the specification, rules, templates and the two skills `damapl-second-brain-kickoff` and `damapl-concept-extraction` from `skills/` into a flat vault layout, places all six files from `examples/data/systems/` (CTMS, EDC, Device Registry, Supply v1, Supply v2 and the Supply index) under `sources/`, copies the derived Supply note under `systems/`, installs the dated synthetic decision under `decisions/`, and creates all required output folders.

Tell the agent:

```text
Read rules/quality-and-currency.md and rules/answer-contract.md.
Use only files in this vault. Follow the answer contract exactly.
```

## Dataset

The current system sources are CTMS, EDC, Device Registry and Supply. Supply has separate v1 and v2 files with stable IDs; v2 supersedes v1. The same label, `device`, names different concepts across the systems.

## Act 1: ask instead of searching

Ask these questions in order:

1. Which systems touch a subject who receives the device in a study, and how do they connect?
2. Where can I record which physical device unit a subject used?
3. What does `device` mean in each system?

The answer must cite source paths or IDs and retrieval dates, state confidence, list open doubts and report classification. The second answer must say that the supplied sources do not define a clean subject-to-device-unit link.

Compare the semantic result with `examples/expected/act-1-answer.md` in the repository. Exact prose may differ; the cited facts and uncertainty must not.

## Act 2: extract concepts

Tell the agent:

```text
Read skills/damapl-concept-extraction/SKILL.md and apply it to
sources/ctms.md, sources/edc.md and sources/device-registry.md.
Then read decisions/2026-10-24-device-terms.md and show how the dated
human decision changes the status of the proposed target concept.
```

The result must distinguish polysemy from contradictory facts. It must preserve all source meanings. `Device Model` and `Device Unit` are source-backed. `Study Device Assignment` is only an open gap until the dated decision source is loaded.

Compare the result with `examples/expected/act-2-concepts.md`.

## Freshness scenario

Supply v2 supersedes Supply v1. The derived note `systems/supply-assessment.md` cites v1.

Preview the impact:

```sh
python3 /path/to/repository/skills/damapl-second-brain-kickoff/scripts/freshness-review.py .
```

The output should match `examples/expected/freshness-review.txt`. To mark the note for human review without rewriting its claim (an approved note keeps its `approved` status and gets one `review_reason` line; running it again changes nothing):

```sh
python3 /path/to/repository/skills/damapl-second-brain-kickoff/scripts/freshness-review.py . --apply
```

## Reset without deletion

```sh
/path/to/repository/examples/reset.sh /tmp/data-architect-demo
```

The script moves generated `glossary/`, `questions/` and `runs/` content into a timestamped `.demo-history/` folder, then recreates empty output folders. It keeps all sources and decisions.

## Architecture outputs

The demo also carries a synthetic glossary in `examples/data/glossary/` (minimal profile, one file per term). Statuses `Approved` there stand for synthetic data steward decisions. Two terms are left unsettled on purpose: `device` is `Under Review` and `dose-event` is `Draft`, and `randomisation-number` is approved but unused.

Expected outputs in `examples/expected/`:

| File | Produced by |
|---|---|
| `map.md` | `map_build.py` |
| `gaps.md` | `gaps_build.py` |
| `model-diff-supply-v1-v2.md` | `model_diff.py` on `supply-v1.md` and `supply-v2.md` |
| `glossary/terms.json`, `glossary/glossary.csv` | `bg_site.py` on the demo glossary |
| `model-change-proposal.md` | written by hand as a sample of the `damapl-model-change` skill output; status `proposed` |

Regenerate from the repository root (the glossary site, about 300 KB with D3 inlined, is not kept):

```sh
S=skills/damapl-model-change/scripts
python3 $S/map_build.py --systems examples/data/systems --out examples/expected/map.md
python3 $S/gaps_build.py --systems examples/data/systems --glossary examples/data/glossary \
  --out examples/expected/gaps.md
python3 $S/model_diff.py examples/data/systems/supply-v1.md examples/data/systems/supply-v2.md \
  --out examples/expected/model-diff-supply-v1-v2.md
python3 skills/damapl-business-glossary/scripts/bg_site.py --repo examples/data/glossary --out /tmp/glossary-out
cp /tmp/glossary-out/terms.json /tmp/glossary-out/glossary.csv examples/expected/glossary/
python3 skills/damapl-business-glossary/scripts/bg_validate.py --repo examples/data/glossary
```

`python3 -m unittest discover -s tests -p 'test_*.py'` compares each script with its expected file.
