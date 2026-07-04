#!/usr/bin/env bash
# new-plan.sh — allocate and scaffold a date-cohort plan doc.
# Scheme: plans/plan-YYMM-NN-<slug>.md  (see workflow/rules/planning.md)
#
# Usage:
#   new-plan.sh <slug> [--dir] [--root <plans-dir>] [--date YYYY-MM-DD]
#
#   <slug>          kebab-case slug, e.g. checkpoint-publisher
#   --dir           scaffold a directory plan (README + handoff) instead of one file
#   --root <dir>    plans directory (default: ./docs/plans, else ./plans, else devdocs/plans)
#   --date          override "today" (for tests/backfill); default = system date
#
# Allocation scans ONLY the current YYMM cohort, so it is safe under parallel
# branches: the only race is same-month-same-instant, and the slug disambiguates.
set -euo pipefail

SLUG=""; MODE="file"; ROOT=""; DATE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) MODE="dir"; shift ;;
    --root) ROOT="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) SLUG="$1"; shift ;;
  esac
done

[ -n "$SLUG" ] || { echo "usage: new-plan.sh <slug> [--dir] [--root <dir>] [--date YYYY-MM-DD]" >&2; exit 2; }
# normalise slug to kebab-case
SLUG="$(printf '%s' "$SLUG" | tr '[:upper:] ' '[:lower:]-' | sed -E 's/[^a-z0-9-]+/-/g; s/-+/-/g; s/^-|-$//g')"

# resolve plans root
if [ -z "$ROOT" ]; then
  if   [ -d ./docs/plans ]; then ROOT=./docs/plans
  elif [ -d ./plans ];      then ROOT=./plans
  elif [ -d ./devdocs/plans ]; then ROOT=./devdocs/plans
  else ROOT=./docs/plans; fi
fi
mkdir -p "$ROOT"

TODAY="${DATE:-$(date +%Y-%m-%d)}"
YYMM="$(printf '%s' "$TODAY" | sed -E 's/^[0-9]{2}([0-9]{2})-([0-9]{2})-.*/\1\2/')"

# highest ordinal in this month's cohort (files or dirs)
LAST="$(ls -d "$ROOT"/plan-"$YYMM"-* 2>/dev/null \
  | sed -E "s#.*/plan-$YYMM-([0-9]{2})-.*#\1#" | sort -n | tail -1 || true)"
NEXT="$(printf '%02d' "$(( 10#${LAST:-0} + 1 ))")"
ID="$YYMM-$NEXT"
TITLE="$(printf '%s' "$SLUG" | tr '-' ' ')"

TPL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../rules/templates" && pwd)"
render() { sed -e "s/{{ID}}/$ID/g" -e "s/{{DATE}}/$TODAY/g" -e "s/{{TITLE}}/$TITLE/g" "$1"; }

if [ "$MODE" = "dir" ]; then
  DEST="$ROOT/plan-$ID-$SLUG"
  mkdir -p "$DEST"
  render "$TPL_DIR/plan-dir-README.md" > "$DEST/README.md"
  printf '# Handoff — plan %s\n\n**Bootstrap order:**\n\n**Locked decisions:**\n\n**Next slice:**\n\n**Resume prompt:**\n' "$ID" > "$DEST/handoff.md"
  echo "$DEST/"
else
  DEST="$ROOT/plan-$ID-$SLUG.md"
  [ -e "$DEST" ] && { echo "refusing to overwrite $DEST" >&2; exit 1; }
  render "$TPL_DIR/plan.md" > "$DEST"
  echo "$DEST"
fi
