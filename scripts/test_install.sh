#!/bin/sh
# Install all skills with the pinned skills CLI into a temp project and test the installed copies.
#
# Usage: scripts/test_install.sh [REPO_PATH]
#
# Proves self-containment: every entry-point script is run from the installed copy with --help,
# the three gates run from the installed copies against examples/data, and the outputs
# regenerated from the installed copies equal examples/expected byte for byte.
# Needs network access once, to fetch the pinned skills CLI (and PyYAML for Python).
# Environment: PYTHON (default python3), SKILLS_CLI_VERSION (default below).
set -eu

SKILLS_CLI_VERSION=${SKILLS_CLI_VERSION:-1.7.6}
PYTHON=${PYTHON:-python3}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPO=${1:-$ROOT}
REPO=$(CDPATH= cd -- "$REPO" && pwd)
EXAMPLES="$REPO/examples"

SKILLS="damapl-second-brain-kickoff damapl-business-glossary damapl-concept-extraction damapl-system-map damapl-gap-list damapl-model-change"

PROJECT=$(mktemp -d)
trap 'rm -rf "$PROJECT"' EXIT
OUT="$PROJECT/out"
mkdir -p "$OUT"
FAILED=0

fail() { echo "FAIL  $1" >&2; FAILED=1; }
pass() { echo "PASS  $1"; }

cd "$PROJECT"
DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 npx --yes "skills@$SKILLS_CLI_VERSION" add "$REPO" \
  --skill '*' --agent claude-code --copy --yes > "$OUT/install.log" 2>&1 || {
  cat "$OUT/install.log" >&2
  echo "FAIL  npx skills add" >&2
  exit 1
}
INSTALLED="$PROJECT/.claude/skills"

# 1. exactly the six skills, each with a SKILL.md
for skill in $SKILLS; do
  [ -f "$INSTALLED/$skill/SKILL.md" ] && pass "installed $skill" || fail "missing $skill"
done
COUNT=$(find "$INSTALLED" -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')
[ "$COUNT" = 6 ] && pass "exactly 6 skill folders installed" || fail "expected 6 skill folders, found $COUNT"
[ -e "$INSTALLED/../../examples" ] && fail "demo data was installed" || pass "no demo data installed"

# 2. every entry-point script runs with --help from the installed copy
for script in "$INSTALLED"/*/scripts/*.py; do
  case $(basename "$script") in
    bg_core.py|bg_adapters.py|bg_rules.py|arch_common.py|answer_contract.py) continue ;;
  esac
  if "$PYTHON" "$script" --help > /dev/null 2>&1; then
    pass "--help ${script#"$INSTALLED"/}"
  else
    fail "--help ${script#"$INSTALLED"/}"
  fi
done

# 3. the three gates, from the installed copies
DATA="$EXAMPLES/data"
G1="$INSTALLED/damapl-second-brain-kickoff/scripts/check_gate.py"
G2="$INSTALLED/damapl-business-glossary/scripts/check_gate.py"
G3="$INSTALLED/damapl-model-change/scripts/check_gate.py"
"$PYTHON" "$G1" 1 --data "$DATA" --answers "$EXAMPLES/expected/act-1-answer.md" > "$OUT/gate1.txt" && pass "gate 1 passes" || fail "gate 1"
"$PYTHON" "$G2" 2 --data "$DATA" > "$OUT/gate2.txt" && pass "gate 2 passes" || fail "gate 2"
set +e
"$PYTHON" "$G3" 3 --data "$DATA" > "$OUT/gate3.txt"
CODE=$?
set -e
if [ "$CODE" = 1 ] && grep -q "device in ctms" "$OUT/gate3.txt" \
   && grep -q "dose-event in edc" "$OUT/gate3.txt" && grep -q "1 failed" "$OUT/gate3.txt"; then
  pass "gate 3 fails on the demo as designed"
else
  fail "gate 3 should fail on the demo for device and dose-event"
fi
set +e
"$PYTHON" "$INSTALLED/damapl-second-brain-kickoff/scripts/check_gate.py" 3 --data "$DATA" > /dev/null 2>&1
[ $? = 2 ] && pass "gate 3 from a skill without its scripts exits 2" || fail "gate 3 in kickoff should exit 2"
set -e

# 4. regenerated outputs equal examples/expected
"$PYTHON" "$INSTALLED/damapl-system-map/scripts/map_build.py" --systems "$DATA/systems" --out "$OUT/map.md" > /dev/null
"$PYTHON" "$INSTALLED/damapl-gap-list/scripts/gaps_build.py" --systems "$DATA/systems" --glossary "$DATA/glossary" --out "$OUT/gaps.md" > /dev/null
"$PYTHON" "$INSTALLED/damapl-model-change/scripts/model_diff.py" "$DATA/systems/supply-v1.md" "$DATA/systems/supply-v2.md" --out "$OUT/model-diff.md" > /dev/null
"$PYTHON" "$INSTALLED/damapl-business-glossary/scripts/bg_site.py" --repo "$DATA/glossary" --out "$OUT/glossary" > /dev/null
cmp -s "$OUT/map.md" "$EXAMPLES/expected/map.md" && pass "map.md matches expected" || fail "map.md differs"
cmp -s "$OUT/gaps.md" "$EXAMPLES/expected/gaps.md" && pass "gaps.md matches expected" || fail "gaps.md differs"
cmp -s "$OUT/model-diff.md" "$EXAMPLES/expected/model-diff-supply-v1-v2.md" && pass "model diff matches expected" || fail "model diff differs"
cmp -s "$OUT/glossary/terms.json" "$EXAMPLES/expected/glossary/terms.json" && pass "terms.json matches expected" || fail "terms.json differs"
cmp -s "$OUT/glossary/glossary.csv" "$EXAMPLES/expected/glossary/glossary.csv" && pass "glossary.csv matches expected" || fail "glossary.csv differs"

if [ "$FAILED" = 0 ]; then echo "install test passed (skills@$SKILLS_CLI_VERSION)"; else echo "install test FAILED" >&2; exit 1; fi
