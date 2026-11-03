---
name: damapl-system-map
description: "Proposes concepts entries for system notes and builds the system map from approved links. Use when a system note needs term links or the concept-to-system map must be regenerated."
version: "0.1.0"
date: "2026-10-31"
summary: "Skill that tells an agent how to propose concept links in system notes for human approval and then build the deterministic system map."
owner: "Data Architect AI Tools maintainers"
status: "release-candidate"
updated: "2026-10-31"
review_by: "2027-01-31"
confidentiality: "public"
---

# System map

Turn system notes into a map of which systems use which glossary terms.

## Paths

Run the scripts from the folder this SKILL.md was loaded from (written `<this skill folder>` below). Take the data folders from the user or, if the file exists, from `.ai/damapl.config.json` in the project root (keys `systems`, `glossary`, `generated`). If neither gives a path, ask the user. Never assume a demo folder.

## Steps

1. Read the system note and its source note. Use only what the source states.
2. Add or extend a `concepts:` list in the note's frontmatter. One entry per term:

   ```yaml
   concepts:
     - term: device-unit      # glossary term id, kebab-case
       meaning: "Physical unit with a serial number"
       source: "DEVICE-REGISTRY-ARCH-v1"   # source_id of the cited note
       status: proposed
   ```

3. Always write `status: proposed`. Never write `approved`; a human sets it after review. Never set `rejected` on your own.
4. Every entry needs `term`, `meaning`, `source` and a status. The source must be an existing `source_id`.
5. If the same term id has different meanings in two systems, or two term ids look alike (for example `device-model` and `device-unit`), keep both entries and tell the human. Do not merge or pick one.
6. After the human has approved entries, run:

   ```bash
   python3 <this skill folder>/scripts/map_build.py --systems SYSTEMS_DIR --out GENERATED_DIR/architecture/map.md
   ```

   Add `--include-superseded` to include older versions of a system note. By default a note whose `source_id` is named in another note's `supersedes` is skipped.
7. Check each entry yourself: it has `term`, `meaning`, `source` and a status, and the `source` is an existing `source_id`.

## Rules

- The map uses approved entries only.
- Shared-term links do not prove an observed data flow. Say so when you present the map.
- Cite the source for every claim.
