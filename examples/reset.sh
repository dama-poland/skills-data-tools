#!/bin/sh
set -eu

TARGET=${1:-"$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/vault"}
[ -d "$TARGET" ] || {
  echo "Vault does not exist: $TARGET" >&2
  exit 1
}

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE="$TARGET/.demo-history/$STAMP"
mkdir -p "$ARCHIVE"

for name in glossary questions runs; do
  if [ -d "$TARGET/$name" ] && [ "$(find "$TARGET/$name" -mindepth 1 -print -quit)" ]; then
    mv "$TARGET/$name" "$ARCHIVE/$name"
  fi
  mkdir -p "$TARGET/$name"
done

echo "Archived prior generated outputs without deleting them: $ARCHIVE"
