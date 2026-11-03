# Agent instructions

Entry point for any AI agent working on this repository (not for agents that only use the installed skills; those follow each `SKILL.md`).

## Governing rule

The agent proposes; a human decides and stays accountable. Draft content, run checks and report results. Do not approve, sign off or decide on a person's behalf.

## Where things are

- `skills/damapl-*/`: the six installable skills. Each folder is self-contained.
- `shared/`: canonical copies of files that several skills need. Never installed.
- `scripts/`: lint, shared-file sync and check, install test.
- `examples/`: synthetic demo data and expected outputs. Never installed.
- `tests/`: unit, end-to-end, gate, scan and smoke tests.
- `docs/`: install notes, gates, old-to-new name mapping.

## Hard rules

- A skill must not read or run anything outside its own folder: no `../`, no repo-root or absolute paths. Scripts find their files with `Path(__file__).resolve().parent`.
- Edit shared files in `shared/` only, then run `python3 scripts/sync_shared.py`. Never edit a copy inside a skill.
- Glossary terms: write only with status `Draft`. Concept links: never set `approved`. Gates: never write `signoff-*.md`. Decisions: never write an approval in `decision.md`.
- Term IDs never change. Update existing files by diff.
- Derived content inherits the highest classification of its inputs. Restricted or internal sources go only to local models; a hosted model receives a source only when its metadata sets `hosted_model_allowed: true`.
- Synthetic data only. No client data, credentials, personal data or speaker-employer figures in any file, including `.ai/` config and CI.
- Do not create folders or stub files for planned skills (see README "Planned").

## Runtime

Python 3.10 or later and `pip install -r requirements.txt` (PyYAML). `scripts/test_install.sh` also needs Node.js and network access to fetch the pinned skills CLI.

## How to check your work

```sh
scripts/lint.sh
python3 scripts/check_shared_copies.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/scan_repo.py
scripts/test_install.sh
```

## Reporting

State what you changed, which files, which checks you ran with their results, what you could not verify, and which step needs a human decision.
