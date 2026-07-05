#!/usr/bin/env bash
# new-plan.sh — allocate and scaffold a date-cohort doc (plan, status, ...).
# Scheme: <root>/<prefix>-YYMM-NN-<slug>.md  (see workflow/rules/planning.md)
#
# Usage:
#   new-plan.sh <slug> [--prefix <type>] [--dir] [--root <dir>] [--date YYYY-MM-DD]
#
#   <slug>          kebab-case slug, e.g. checkpoint-publisher
#   --prefix <type> doc type prefix: plan (default) or status
#   --dir           scaffold a directory plan (README + handoff); plan prefix only
#   --root <dir>    docs directory (default per prefix: plan -> ./docs/plans,
#                   ./plans, devdocs/plans; status -> ./docs/status, devdocs/status)
#   --date          override "today" (for tests/backfill); default = system date
#
# Allocation scans ONLY the current YYMM cohort, so it is safe under parallel
# branches: the only race is same-month-same-instant, and the slug disambiguates.
set -euo pipefail

SLUG=""; MODE="file"; ROOT=""; DATE=""; PREFIX="plan"
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) MODE="dir"; shift ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --root) ROOT="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) SLUG="$1"; shift ;;
  esac
done

[ -n "$SLUG" ] || { echo "usage: new-plan.sh <slug> [--prefix <type>] [--dir] [--root <dir>] [--date YYYY-MM-DD]" >&2; exit 2; }
[ "$MODE" = "file" ] || [ "$PREFIX" = "plan" ] || { echo "--dir is only supported for --prefix plan" >&2; exit 2; }
# normalise slug to kebab-case
SLUG="$(printf '%s' "$SLUG" | tr '[:upper:] ' '[:lower:]-' | sed -E 's/[^a-z0-9-]+/-/g; s/-+/-/g; s/^-|-$//g')"

# resolve docs root: plans live in a pluralised dir, other types in a dir named
# after the prefix (docs/status, devdocs/status, ...)
if [ -z "$ROOT" ]; then
  case "$PREFIX" in
    plan) CANDIDATES="./docs/plans ./plans ./devdocs/plans" ;;
    *)    CANDIDATES="./docs/$PREFIX ./$PREFIX ./devdocs/$PREFIX" ;;
  esac
  for C in $CANDIDATES; do
    [ -d "$C" ] && { ROOT="$C"; break; }
  done
  [ -n "$ROOT" ] || ROOT="${CANDIDATES%% *}"
fi
mkdir -p "$ROOT"

TODAY="${DATE:-$(date +%Y-%m-%d)}"
YYMM="$(printf '%s' "$TODAY" | sed -E 's/^[0-9]{2}([0-9]{2})-([0-9]{2})-.*/\1\2/')"

# highest ordinal in this month's cohort (files or dirs)
LAST="$(ls -d "$ROOT"/"$PREFIX"-"$YYMM"-* 2>/dev/null \
  | sed -E "s#.*/$PREFIX-$YYMM-([0-9]{2})-.*#\1#" | sort -n | tail -1 || true)"
NEXT="$(printf '%02d' "$(( 10#${LAST:-0} + 1 ))")"
ID="$YYMM-$NEXT"
TITLE="$(printf '%s' "$SLUG" | tr '-' ' ')"

TPL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../rules/templates" && pwd)"
[ -f "$TPL_DIR/$PREFIX.md" ] || { echo "no template for prefix '$PREFIX' ($TPL_DIR/$PREFIX.md)" >&2; exit 2; }
render() { sed -e "s/{{ID}}/$ID/g" -e "s/{{DATE}}/$TODAY/g" -e "s/{{TITLE}}/$TITLE/g" "$1"; }

if [ "$MODE" = "dir" ]; then
  DEST="$ROOT/plan-$ID-$SLUG"
  mkdir -p "$DEST"
  render "$TPL_DIR/plan-dir-README.md" > "$DEST/README.md"
  printf '# Handoff — plan %s\n\n**Bootstrap order:**\n\n**Locked decisions:**\n\n**Next slice:**\n\n**Resume prompt:**\n' "$ID" > "$DEST/handoff.md"
  echo "$DEST/"
else
  DEST="$ROOT/$PREFIX-$ID-$SLUG.md"
  [ -e "$DEST" ] && { echo "refusing to overwrite $DEST" >&2; exit 1; }
  render "$TPL_DIR/$PREFIX.md" > "$DEST"
  echo "$DEST"
fi
