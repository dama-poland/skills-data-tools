---
title: "Compatibility"
summary: "Table of agents and models that ran the smoke test on the skills collection, with date, result and who ran it."
updated: "2026-11-03"
review_by: "2027-01-31"
owner: "DAMA Poland maintainers"
status: "draft"
confidentiality: "public"
---

# Compatibility

The skills are built to work with any agent that can read files and run a command. That is a design rule, not evidence. This table records the evidence: one row per real run of the smoke test in `tests/agent-smoke.md`. This repository starts its own table; results of `data-architect-ai-tools` do not carry over.

| Agent | Agent version | Model | Local or hosted | Date | Result | Run by |
|---|---|---|---|---|---|---|
| pi | 1.5.0 | anthropic/claude-haiku-4-5 | hosted | 2026-11-03 | pass | DAMA Poland maintainers (pi agent) |
| pi | 1.5.0 | anthropic/claude-haiku-4-5 | hosted | 2026-11-03 | fail: Q2 Sources had no retrieval date | DAMA Poland maintainers (pi agent) |
| pi | 1.5.0 | anthropic/claude-sonnet-5-5 | hosted | 2026-11-03 | pass | DAMA Poland maintainers (pi agent) |

## Rules for this table

- Add a row only after a real run. Never add a configuration because it should work, and never copy a result from another run.
- Result is `pass` or `fail`. For a fail, write one line on what broke.
- Fill every column. Use the output of `python3 tests/check_smoke.py` as the evidence.
- Local models (Ollama, mlx and similar) are first-class. They are the only allowed option for internal or restricted sources.
- A pass applies to the agent version, model and date in the row only.
