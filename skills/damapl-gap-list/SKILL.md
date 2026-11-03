---
name: damapl-gap-list
description: "Builds the gap list from approved concept links and the glossary, and helps a human work through the findings. Use when the architecture needs a check for meaning conflicts, homonyms, unapproved terms, unlinked systems, unused terms or links without sources."
version: "0.1.0"
date: "2026-10-31"
summary: "Skill that tells an agent how to run the deterministic gap list and present its findings to a human without resolving them."
owner: "DAMA Poland maintainers"
status: "release-candidate"
updated: "2026-10-31"
review_by: "2027-01-31"
confidentiality: "public"
---

# Gap list

Check the concept links against the glossary and list what a human must decide.

## Paths

Run the scripts from the folder this SKILL.md was loaded from (written `<this skill folder>` below). Take the data folders from the user or, if the file exists, from `.ai/damapl.config.json` in the project root (keys `systems`, `glossary`, `generated`). If neither gives a path, ask the user. Never assume a demo folder.

## Steps

1. Confirm the inputs: system notes with approved `concepts:` entries and a glossary with a `terms/` folder. If the map has not been built yet, use the `damapl-system-map` skill first.
2. Run:

   ```bash
   python3 <this skill folder>/scripts/gaps_build.py \
     --systems SYSTEMS_DIR --glossary GLOSSARY_DIR \
     --out GENERATED_DIR/architecture/gaps.md
   ```

   Add `--include-superseded` to include older versions of a system note.
3. Read the output group by group. The six checks are meaning conflict, homonym risk, link to a term that is not `Approved`, system with no approved links, approved term used by no system, and link with no source.
4. Present the findings with their counts. For each finding, cite the system note and the source id shown in the table.
5. Separate what the script established from what you suggest. The meaning check compares text only, so say when a difference may be wording rather than a different concept.
6. Name the human decision each group needs, for example: approve or reject a term, link an unused term, add a source, split a term.

## Rules

- Do not change a link status, a term status or any note to make a finding disappear. The agent proposes; a human decides.
- Never write `approved` on a link, and never set a glossary term beyond `Draft`.
- A gap is not proof of an error in the systems. Say so when you present the list.
- Cite the source for every claim. Do not invent a source.
