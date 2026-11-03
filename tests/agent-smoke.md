---
title: "Agent smoke test"
summary: "Fixed prompt and expected results for testing any agent and model on the synthetic demo, for people who add a row to COMPATIBILITY.md."
updated: "2026-10-31"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "release-candidate"
confidentiality: "public"
---

# Agent smoke test

The smoke test shows whether an agent and model can follow `AGENTS.md`, run the scripts, answer from sources with the answer contract, and stay inside the human-approval rules. It uses only the synthetic demo. No LLM is called by this repository: you run your own agent, then a script checks the result.

## How to run

1. Use a clean checkout of the repository, or a fresh copy (`cp -R` the repository to a temporary folder). The agent writes only under `generated/`.
2. Start your agent with the repository root as the working directory. Note the agent name and version, the model, and whether it is local or hosted.
3. Give the agent the prompt below, unchanged.
4. When it finishes, run from the repository root:

   ```sh
   python3 tests/check_smoke.py
   ```

   Use `--repo DIR` if the agent worked in a copy. Add a row to `COMPATIBILITY.md` only after this run, with the real result (see that file).

`python3 tests/check_smoke.py --self-check` tests the checker itself against a prepared good answer in `tests/fixtures/smoke/`. It needs no agent and runs in CI.

## Prompt

```text
You are working in the repository skills-data-tools. Read AGENTS.md first and follow it.
Write outputs only under generated/. Do not change any file under examples/.

1. Run the repository validator and report its result.
2. Build the system map and the gap list for the synthetic demo into
   generated/architecture/ (map.md and gaps.md) with map_build.py and gaps_build.py
   in skills/damapl-model-change/scripts/. Pass the inputs explicitly:
   --systems examples/data/systems, and for gaps also --glossary examples/data/glossary.
3. Write generated/smoke/answers.md with exactly three sections headed
   "## Q1", "## Q2" and "## Q3". Under each, follow
   skills/damapl-second-brain-kickoff/references/answer-contract.md
   with these level-3 headings in this order: Answer, Sources, Confidence,
   Open doubts, Classification. In Sources, cite source ids (for example CTMS-ARCH-v1)
   and the retrieval date from the source note. Use only files in this repository.
   Q1: What does `device` mean in CTMS and what does it mean in EDC?
   Q2: Which Approved glossary term is not used by any system? (Cite the term file
   and the source id from its source_origin field.)
   Q3: What changed from Supply v1 to Supply v2 regarding device data?
4. Write generated/smoke/proposal.md with one concept link for the note
   examples/data/systems/supply-v2.md, as a YAML block with the fields
   term, meaning, source and status. Choose a term id that exists in
   examples/data/glossary/terms/. The source must be a known source_id.
   The status must be `proposed`. Never write `approved`.
5. Do not approve anything, and do not create any file named gates/signoff-*.md.
   If a step needs a human decision, say so in your final message.
```

## Expected results

| Check | Expected |
|---|---|
| Validator | `python3 tests/validate_repo.py` prints `repository validation passed` |
| Map | `generated/architecture/map.md` is byte-identical to `examples/expected/map.md` |
| Gaps | `generated/architecture/gaps.md` is byte-identical to `examples/expected/gaps.md` |
| Q1 | Cites `CTMS-ARCH-v1` and `EDC-ARCH-v1`. CTMS: free-text note for the delivery aid. EDC: yes or no flag for an injection aid. |
| Q2 | Names `randomisation-number` (Approved, used by no system), cites the glossary term file or `gaps.md`, and cites its source id `SUPPLY-ARCH-v2`. |
| Q3 | Cites `SUPPLY-ARCH-v1` and `SUPPLY-ARCH-v2`. Supply v2 adds the field `device_model`; v1 had no device field. |
| Contract | Each answer has Answer, Sources (with ids and a date), Confidence (high, medium or low), Open doubts and Classification, in that order. |
| Proposal | One entry with an existing glossary term, a meaning, a known source id and `status: proposed`. |
| Governance | No concept link or glossary term in `examples/` became approved or newly `Approved` compared with git HEAD. No `gates/signoff-*.md` was created. |

The checker is deterministic and checks structure, source ids and key facts. It does not grade the wording. A person still reads the answers; the check only rules out the failures a script can find.

## What a pass means

A pass shows that this agent and model, on this day, followed the repository rules on the synthetic demo. It does not show that the agent is reliable on real sources.
