#!/bin/sh
# Lint the skill folders and the optional .ai config. No network, no LLM.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$ROOT/scripts/lint_skills.py" --root "$ROOT"
