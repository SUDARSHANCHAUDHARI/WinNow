#!/usr/bin/env bash
# build-skill.sh - package Winnow as a self-contained .skill bundle.
#
# Produces dist/winnow.skill, a zip with a single top-level winnow/ directory
# containing SKILL.md and the engine/ runtime (deref'd from the symlink), so
# the skill works on hosts that install only the skill dir (npx skills, the
# claude.ai upload UI). The Claude Code plugin install uses the repo directly
# and resolves the engine via the repo-checkout fallback in SKILL.md.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
DEST="$STAGE/winnow"
mkdir -p "$DEST/engine"

cp skills/winnow/SKILL.md "$DEST/SKILL.md"
# -L dereferences the engine symlink so the bundle is self-contained.
cp -RL engine/winnow.py engine/trends.py engine/lib "$DEST/engine/"

# Drop non-runtime cruft.
find "$DEST" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -type f -name '*.pyc' -delete 2>/dev/null || true

mkdir -p dist
OUT="$REPO_ROOT/dist/winnow.skill"
rm -f "$OUT"
( cd "$STAGE" && zip -rq "$OUT" winnow )

COUNT="$(unzip -l "$OUT" | tail -1 | awk '{print $2}')"
SKILL_MD_COUNT="$(unzip -l "$OUT" | grep -c '/SKILL.md$' || true)"

if [ "$COUNT" -gt 200 ]; then
  echo "error: $COUNT files in bundle, claude.ai cap is 200" >&2
  exit 1
fi
if [ "$SKILL_MD_COUNT" -ne 1 ]; then
  echo "error: expected exactly one SKILL.md, found $SKILL_MD_COUNT" >&2
  exit 1
fi

SIZE="$(du -h "$OUT" | cut -f1)"
echo "built dist/winnow.skill ($COUNT files, $SIZE)"
echo "upload via the claude.ai Skills UI, or test with: unzip -l dist/winnow.skill"
