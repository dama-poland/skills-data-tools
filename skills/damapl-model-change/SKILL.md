---
name: damapl-model-change
description: "Proposes a model change from a note diff, the system map and the gap list, as a decision.md with status proposed. Use when a system note has a new version and the architect needs to know what to change in which system and model."
version: "0.1.0"
date: "2026-10-31"
summary: "Skill that tells an agent how to turn a model diff, map and gap list into a cited change proposal that only a human can approve."
owner: "DAMA Poland maintainers"
status: "release-candidate"
updated: "2026-10-31"
review_by: "2027-01-31"
confidentiality: "public"
---

# Model change

Turn what changed between two versions of a system note into a proposal the architect can accept, change or reject.

## Paths

Run the scripts from the folder this SKILL.md was loaded from (written `<this skill folder>` below). Take the data folders from the user or, if the file exists, from `.ai/damapl.config.json` in the project root (keys `systems`, `glossary`, `generated`). If neither gives a path, ask the user. Never assume a demo folder.

## Steps

1. Build the three inputs:

   ```bash
   python3 <this skill folder>/scripts/model_diff.py OLD.md NEW.md --out GENERATED_DIR/architecture/model-diff.md
   python3 <this skill folder>/scripts/map_build.py --systems SYSTEMS_DIR --out GENERATED_DIR/architecture/map.md
   python3 <this skill folder>/scripts/gaps_build.py --systems SYSTEMS_DIR --glossary GLOSSARY_DIR --out GENERATED_DIR/architecture/gaps.md
   ```

2. Read the diff, the map and the gaps. Read the cited source notes when a claim depends on them.
3. Copy `templates/decision.md` (in this skill folder) to a new file with `cp`, then fill it in. Set `status: "proposed"`.
4. In the body, propose:
   - what to change, in which system and in which model, and why;
   - the impact on other systems, using the map (shared terms show a possible link, not an observed data flow);
   - open questions the sources cannot answer.
5. Cite a source id or a generated file for every claim. If no source supports a statement, move it to the open questions.
6. List every source id used in `source_refs`. Set `confidentiality` to the highest classification among the inputs.
7. Leave the approver section as `Pending: the architect decides.` and stop.

## Rules

- The agent never writes `status: "approved"` and never names an approver or an approval date. The architect decides.
- Do not edit the system notes, the glossary or the link statuses as part of the proposal. Propose them.
- Keep every source meaning. If two systems define a term differently, say so and do not pick one.
- Do not invent systems, fields or sources. Use synthetic or supplied data only.

## Gate 3

Program check, run from this skill folder (`DIR` holds `systems/` and `glossary/`):

```bash
python3 <this skill folder>/scripts/check_gate.py 3 --data DIR
```

The human checklist is `references/gate-3-architecture.md`. A failing gate is a prompt for a human decision, not an error to hide. A passing gate is not a sign-off; the architect writes `gates/signoff-3.md`, never the agent.
