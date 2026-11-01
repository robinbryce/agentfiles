#!/usr/bin/env bash
# new-plan.sh — allocate and scaffold a date-cohort doc (plan, status, ...).
# Scheme: <root>/<prefix>-YYMM-NN-<slug>.md  (see the core:planning skill)
# The id written to frontmatter is the filename stem: <prefix>-YYMM-NN-<slug>.
#
# Usage:
#   new-plan.sh <slug> [--prefix <type>] [--dir] [--root <dir>] [--date YYYY-MM-DD] [--offline]
#
#   <slug>          kebab-case slug, e.g. checkpoint-publisher
#   --prefix <type> doc type prefix: plan (default) or status
#   --dir           scaffold a directory plan (README + handoff); plan prefix only
#   --root <dir>    docs directory (default per prefix: plan -> ./docs/plans,
#                   ./plans, devdocs/plans; status -> ./docs/status, devdocs/status)
#   --date          override "today" (for tests/backfill); default = system date
#   --offline       skip the remote scan (also NEW_PLAN_OFFLINE=1)
#
# Allocation scans ONLY the current YYMM cohort, but everywhere an id of it
# can already be taken: the whole working tree (so archive/<YYMM>/ counts),
# and, when the root is in a git repo with an origin, origin's default branch
# (after a fetch) and the files of open GitHub PRs. A stale clone therefore
# cannot hand out an id that main or an open PR already holds.
set -euo pipefail

SLUG=""; MODE="file"; ROOT=""; DATE=""; PREFIX="plan"; OFFLINE="${NEW_PLAN_OFFLINE:-0}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) MODE="dir"; shift ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --root) ROOT="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    --offline) OFFLINE=1; shift ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) SLUG="$1"; shift ;;
  esac
done

[ -n "$SLUG" ] || { echo "usage: new-plan.sh <slug> [--prefix <type>] [--dir] [--root <dir>] [--date YYYY-MM-DD] [--offline]" >&2; exit 2; }
[ "$MODE" = "file" ] || [ "$PREFIX" = "plan" ] || { echo "--dir is only supported for --prefix plan" >&2; exit 2; }
# normalise slug to kebab-case
SLUG="$(printf '%s' "$SLUG" | tr '[:upper:] ' '[:lower:]-' | sed -E 's/[^a-z0-9-]+/-/g; s/-+/-/g; s/^-|-$//g')"

warn() { echo "new-plan.sh: warning: $*" >&2; }

# dox dispatch. When dox (https://github.com/robinbryce/dox) is on PATH,
# DOX_SCHEMA_REPO is set, and the git repo holding the docs root has a
# .dox.toml whose `types` include this prefix, dox owns allocation: run
# `dox new` there and print the path it prints. dox places the document by
# its schema, so --root only selects the repo. NEW_PLAN_NO_DOX=1 opts out.
# A dox config or remote error (exit 2 or 3) falls back to the scan below.
dox_repo() {
  [ "${NEW_PLAN_NO_DOX:-0}" = 1 ] && return 1
  command -v dox >/dev/null 2>&1 || return 1
  [ -n "${DOX_SCHEMA_REPO:-}" ] || return 1
  local d="${ROOT:-.}" top
  while [ ! -d "$d" ]; do d="$(dirname "$d")"; done
  top="$(git -C "$d" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [ -f "$top/.dox.toml" ] || return 1
  python3 - "$top/.dox.toml" "$PREFIX" <<'PY' || return 1
import sys
try:
    import tomllib
    with open(sys.argv[1], "rb") as f:
        types = tomllib.load(f).get("types", [])
except Exception:
    sys.exit(1)
sys.exit(0 if isinstance(types, list) and sys.argv[2] in types else 1)
PY
  printf '%s\n' "$top"
}
if DOX_TOP="$(dox_repo)"; then
  DOX_ARGS=(new "$PREFIX" "$SLUG")
  [ "$MODE" = "dir" ] && DOX_ARGS+=(--dir)
  [ -n "$DATE" ] && DOX_ARGS+=(--date "$DATE")
  [ "$OFFLINE" = 1 ] && DOX_ARGS+=(--offline)
  set +e
  DOX_OUT="$(cd "$DOX_TOP" && dox "${DOX_ARGS[@]}")"
  DOX_RC=$?
  set -e
  case "$DOX_RC" in
    0) printf '%s\n' "$DOX_OUT"; exit 0 ;;
    2|3) warn "dox new failed (exit $DOX_RC); allocating with the built-in scan" ;;
    *) exit "$DOX_RC" ;;
  esac
fi

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

# Print every path that may carry an id of this cohort. The output is noisy
# on purpose; the grep below extracts the ids. Paths cover the whole repo, so
# a plan already moved to archive/<YYMM>/ still holds its id.
taken_paths() {
  ls -d "$ROOT"/"$PREFIX"-"$YYMM"-* 2>/dev/null || true
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  git -C "$ROOT" ls-files --cached --others --exclude-standard --full-name -- ':/' 2>/dev/null || true
  [ "$OFFLINE" = 1 ] && return 0
  local url head slug
  url="$(git -C "$ROOT" remote get-url origin 2>/dev/null)" || return 0
  # Never prompt or hang: no credential prompts, and ssh fails fast offline.
  GIT_TERMINAL_PROMPT=0 \
    GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=5" \
    git -C "$ROOT" fetch origin --quiet >/dev/null 2>&1 \
    || warn "git fetch origin failed; using the last-fetched origin state"
  head="$(git -C "$ROOT" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  head="${head:-origin/main}"
  if git -C "$ROOT" rev-parse --verify --quiet "$head^{commit}" >/dev/null 2>&1; then
    git -C "$ROOT" ls-tree -r --name-only --full-tree "$head" 2>/dev/null || true
  else
    warn "no $head; allocating against the local tree only"
  fi
  case "$url" in *github.com[:/]*) ;; *) return 0 ;; esac
  command -v gh >/dev/null 2>&1 || { warn "gh not found; open PRs not scanned"; return 0; }
  slug="$(printf '%s' "$url" | sed -E 's#^(git@[^:]+:|https?://[^/]+/)##; s#\.git$##')"
  GH_PROMPT_DISABLED=1 gh pr list -R "$slug" --state open --limit 200 --json files \
    --jq '.[].files[].path' 2>/dev/null \
    || warn "could not list open PRs for $slug"
}

# highest ordinal in this month's cohort, wherever it was found
LAST="$(taken_paths | grep -oE "(^|/)$PREFIX-$YYMM-[0-9]{2}" | grep -oE '[0-9]{2}$' | sort -n | tail -1 || true)"
NEXT="$(printf '%02d' "$(( 10#${LAST:-0} + 1 ))")"
ID="$PREFIX-$YYMM-$NEXT-$SLUG"
TITLE="$(printf '%s' "$SLUG" | tr '-' ' ')"

# Locate the templates beside this skill (plan-new/templates/). The script may be
# invoked through a symlink (save-status/scripts/, a repo's .claude/skills/), so
# resolve the real path first. NEW_PLAN_TEMPLATES overrides for unusual layouts.
resolve_self() {
  local src="${BASH_SOURCE[0]}" dir
  while [ -L "$src" ]; do
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  cd -P "$(dirname "$src")" && pwd
}
SELF_DIR="$(resolve_self)"
TPL_DIR="${NEW_PLAN_TEMPLATES:-}"
if [ -z "$TPL_DIR" ] && [ -d "$SELF_DIR/../templates" ]; then
  TPL_DIR="$(cd "$SELF_DIR/../templates" && pwd)"
fi
[ -n "$TPL_DIR" ] || { echo "cannot locate rules/templates from $SELF_DIR (set NEW_PLAN_TEMPLATES)" >&2; exit 2; }
[ -f "$TPL_DIR/$PREFIX.md" ] || { echo "no template for prefix '$PREFIX' ($TPL_DIR/$PREFIX.md)" >&2; exit 2; }
render() { sed -e "s/{{ID}}/$ID/g" -e "s/{{DATE}}/$TODAY/g" -e "s/{{TITLE}}/$TITLE/g" "$1"; }

if [ "$MODE" = "dir" ]; then
  DEST="$ROOT/$ID"
  [ -e "$DEST" ] && { echo "refusing to overwrite $DEST" >&2; exit 1; }
  mkdir -p "$DEST"
  render "$TPL_DIR/plan-dir-README.md" > "$DEST/README.md"
  printf '# Handoff — %s\n\n**Bootstrap order:**\n\n**Locked decisions:**\n\n**Next slice:**\n\n**Resume prompt:**\n' "$ID" > "$DEST/handoff.md"
  echo "$DEST/"
else
  DEST="$ROOT/$ID.md"
  [ -e "$DEST" ] && { echo "refusing to overwrite $DEST" >&2; exit 1; }
  render "$TPL_DIR/$PREFIX.md" > "$DEST"
  echo "$DEST"
fi
