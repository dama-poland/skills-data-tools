#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
TARGET=${1:-"$SCRIPT_DIR/vault"}

if [ -d "$TARGET" ] && [ "$(find "$TARGET" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo "Refusing to overwrite non-empty target: $TARGET" >&2
  exit 1
fi

mkdir -p "$TARGET" "$TARGET/sources" "$TARGET/systems" "$TARGET/glossary" \
  "$TARGET/questions" "$TARGET/decisions" "$TARGET/inbox" "$TARGET/runs"
mkdir -p "$TARGET/skills" "$TARGET/templates"
KICKOFF="$REPO_ROOT/skills/damapl-second-brain-kickoff"
mkdir -p "$TARGET/spec" "$TARGET/rules"
cp "$KICKOFF/references/second-brain-spec.md" "$TARGET/spec/"
cp "$KICKOFF/references/answer-contract.md" "$KICKOFF/references/quality-and-currency.md" "$TARGET/rules/"
cp -R "$KICKOFF" "$REPO_ROOT/skills/damapl-concept-extraction" "$TARGET/skills/"
cp "$REPO_ROOT/skills/damapl-concept-extraction/templates/decision.md" \
  "$REPO_ROOT/skills/damapl-business-glossary/templates/glossary-entry.md" "$TARGET/templates/"
cp "$SCRIPT_DIR"/data/systems/*.md "$TARGET/sources/"
cp "$SCRIPT_DIR"/data/notes/*.md "$TARGET/systems/"
cp "$SCRIPT_DIR"/data/decisions/*.md "$TARGET/decisions/"

cat > "$TARGET/brain.md" <<'EOF'
---
title: "Synthetic demo brain"
summary: "Fresh vault for the reproducible two-act synthetic demonstration."
owner: "Demo operator"
status: "candidate"
updated: "2026-10-24"
review_by: "2027-01-24"
confidentiality: "public"
---

# Synthetic demo brain

Use only the supplied fictional sources. Follow `rules/quality-and-currency.md` and `rules/answer-contract.md`.
EOF

echo "Created fresh demo vault: $TARGET"
echo "Working directory: $TARGET"
echo "Next: ask the agent to read rules/answer-contract.md and demo instructions, then run Act 1."
