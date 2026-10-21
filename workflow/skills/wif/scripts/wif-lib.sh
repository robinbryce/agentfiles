#!/usr/bin/env bash
# wif shared helpers. Sourced by every subcommand; never executed directly.
# Contract: no helper exits non-zero for "no stream here" — that is a normal
# answer. Hooks run under `trap 'exit 0' ERR`, so every helper that can
# legitimately find nothing ends with `return 0`.
set -u

WIF_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
case "$WIF_CONFIG_DIR" in /*) ;; *) WIF_CONFIG_DIR="$PWD/$WIF_CONFIG_DIR" ;; esac
WIF_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# Tunables (also exported for the Python subcommands).
export WIF_RING="${WIF_RING:-10}"
export WIF_STREAM_CAP="${WIF_STREAM_CAP:-120}"
export WIF_STALE_DAYS="${WIF_STALE_DAYS:-14}"
export WIF_ROTATE_PCT="${WIF_ROTATE_PCT:-60}"
export WIF_PR_TTL="${WIF_PR_TTL:-$((6*3600))}"
export WIF_SESSION_KEEP_DAYS="${WIF_SESSION_KEEP_DAYS:-30}"
export GIT_OPTIONAL_LOCKS=0

wif_now()   { date -u +%Y-%m-%dT%H:%M:%SZ; }
wif_today() { date -u +%Y-%m-%d; }
wif_epoch() { date +%s; }
wif_phys()  { (cd "$1" 2>/dev/null && pwd -P); }
wif_die()   { echo "wif: $*" >&2; exit 1; }

# ---- account / scope -------------------------------------------------------

wif_account() {
  case "$(basename "$WIF_CONFIG_DIR")" in
    .claude-justgames) echo justgames ;;
    .claude-personal|.claude) echo personal ;;
    *) basename "$WIF_CONFIG_DIR" ;;
  esac
}

wif_known_scopes() { echo "${WIF_ACCOUNT_SCOPES:-justgames forestrie personal}"; }

# 0 if the account serves the scope.
wif_account_serves() {
  local a=$1 s=$2
  if [ -n "${WIF_ACCOUNT_SCOPES:-}" ]; then
    case " $WIF_ACCOUNT_SCOPES " in *" $s "*) return 0 ;; *) return 1 ;; esac
  fi
  case "$a:$s" in
    justgames:justgames|personal:personal|personal:forestrie) return 0 ;;
    *) return 1 ;;
  esac
}

wif_scope_root() {
  local s=$1 v
  v="WIF_ROOT_$(echo "$s" | tr '[:lower:]' '[:upper:]' | tr -c '[:alnum:]_\n' '_')"
  if [ -n "${!v:-}" ]; then echo "${!v}"; return 0; fi
  case "$s" in
    justgames) echo "$HOME/Dev/justgames/code" ;;
    forestrie) echo "$HOME/Dev/personal/forestrie" ;;
    personal)  echo "$HOME/Dev/personal" ;;
    *) echo "" ;;
  esac
}

# cwd -> scope name (mirrors agentfiles/AGENTS.md scope table)
wif_scope_of() {
  local p=$1
  case "$p" in
    "$HOME/Dev/personal/forestrie"|"$HOME/Dev/personal/forestrie/"*) echo forestrie ;;
    "$HOME/Dev/justgames"|"$HOME/Dev/justgames/"*) echo justgames ;;
    *) echo personal ;;
  esac
}

wif_ledger() { echo "$WIF_CONFIG_DIR/wif/$1"; }
wif_ledger_init() {
  local l; l=$(wif_ledger "$1")
  mkdir -p "$l/streams" "$l/sessions" "$l/archive" "$l/cache"
  echo "$l"
}

# ---- backing resolution ----------------------------------------------------
# Sets WIF_KIND (herdr|repo|none) WIF_ID WIF_PATH directly — no string
# round-trip, so spaces in names survive.
wif_backing_of() {
  local p=$1 phys task root top common repo branch
  WIF_KIND=none; WIF_ID=""; WIF_PATH=""
  phys=$(wif_phys "$p") || return 0
  case "$phys" in
    */.worktrees-herdr/*)
      root="${phys%%/.worktrees-herdr/*}"
      task="${phys#*/.worktrees-herdr/}"; task="${task%%/*}"
      WIF_KIND=herdr; WIF_ID=$task; WIF_PATH="$root/.worktrees-herdr/$task"; return 0 ;;
  esac
  top=$(git -C "$phys" rev-parse --show-toplevel 2>/dev/null) || return 0
  common=$(git -C "$phys" rev-parse --git-common-dir 2>/dev/null) || return 0
  case "$common" in /*) ;; *) common="$phys/$common" ;; esac
  common=$(wif_phys "$common" || echo "$common")
  case "$common" in
    */.git/modules/*) repo=$(basename "$top") ;;            # submodule checkout
    *) repo=$(basename "$(dirname "$common")") ;;
  esac
  branch=$(git -C "$phys" symbolic-ref --short -q HEAD 2>/dev/null) || branch=detached
  WIF_KIND=repo; WIF_ID="${repo}--$(printf '%s' "$branch" | tr '/ ' '--')"; WIF_PATH=$top
  return 0
}

# Resolve everything for a cwd. Sets WIF_SCOPE WIF_ROOT WIF_ACCOUNT WIF_SERVED
# WIF_KIND WIF_ID WIF_PATH WIF_LEDGER WIF_STREAM (file; may not exist).
wif_resolve() {
  local cwd=${1:-$PWD} phys
  WIF_ACCOUNT=$(wif_account)
  phys=$(wif_phys "$cwd") || phys=$cwd
  WIF_SCOPE=$(wif_scope_of "$phys")
  WIF_ROOT=$(wif_scope_root "$WIF_SCOPE")
  if wif_account_serves "$WIF_ACCOUNT" "$WIF_SCOPE"; then WIF_SERVED=1; else WIF_SERVED=0; fi
  WIF_LEDGER=$(wif_ledger "$WIF_SCOPE")
  wif_backing_of "$cwd"
  WIF_STREAM=""; [ "$WIF_KIND" = none ] || WIF_STREAM="$WIF_LEDGER/streams/$WIF_ID.md"
  return 0
}

# May a session auto-bind here? herdr: yes unless the stream was closed
# (archive/<id>.md exists — re-open with `wif adopt`). repo: only if a stream exists.
wif_bindable() {
  [ "${WIF_SERVED:-0}" = 1 ] || return 1
  [ -n "${WIF_ID:-}" ] || return 1
  [ -f "$WIF_LEDGER/archive/$WIF_ID.md" ] && [ ! -f "$WIF_STREAM" ] && return 1
  case "$WIF_KIND" in
    herdr) return 0 ;;
    repo) [ -f "$WIF_STREAM" ] ;;
    *) return 1 ;;
  esac
}

# ---- stream files (markdown + flat YAML frontmatter) -----------------------
# Values are stored as double-quoted scalars; `\` and `"` are escaped; newlines
# are flattened to spaces. awk receives values via ENVIRON (no -v escape mangling).

wif_fm_get() { # file key
  [ -f "$1" ] || return 0
  k="$2" awk '
    NR==1 && $0=="---" {infm=1; next}
    infm && $0=="---" {exit}
    infm && index($0, ENVIRON["k"] ": ")==1 {
      v=substr($0, length(ENVIRON["k"])+3); sub(/^"/, "", v); sub(/"$/, "", v)
      gsub(/\\"/, "\"", v); gsub(/\\\\/, "\\", v); print v; exit }
  ' "$1" 2>/dev/null
  return 0
}

wif_fm_set() { # file key value  (adds the key if absent) -> 0 on success
  local f=$1 k=$2 v=$3 tmp esc
  esc=$(printf '%s' "$v" | tr '\n\r' '  ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
  tmp=$(mktemp) || return 1
  if k="$k" v="$esc" awk '
    BEGIN{done=0}
    NR==1 && $0=="---" {infm=1; print; next}
    infm && $0=="---" { if(!done){print ENVIRON["k"] ": \"" ENVIRON["v"] "\""; done=1}; infm=0; print; next }
    infm && index($0, ENVIRON["k"] ": ")==1 { if(!done){print ENVIRON["k"] ": \"" ENVIRON["v"] "\""; done=1}; next }
    {print}
  ' "$f" > "$tmp"; then mv "$tmp" "$f"; else rm -f "$tmp"; return 1; fi
}

wif_stream_create() { # id scope kind path [status]
  local id=$1 scope=$2 kind=$3 path=$4 status=${5:-active} f
  f="$(wif_ledger "$scope")/streams/$id.md"
  [ -f "$f" ] && { echo "$f"; return 0; }
  mkdir -p "$(dirname "$f")"
  cat > "$f" <<EOT
---
id: "$id"
scope: "$scope"
status: "$status"
goal: ""
next: ""
position: ""
parent: ""
backing: "$kind:$path"
issue: ""
prs: ""
handoff_doc: ""
last_session: ""
created: "$(wif_today)"
updated: "$(wif_today)"
---
## Now
<!-- goal / approach / done / failing — keep under 20 lines -->
## Notes
<!-- - [followup|tangent|reminder due=YYYY-MM-DD|landed] YYYY-MM-DD text -->
## Handoff
<!-- paste-ready kickoff prompt, under 25 lines; written at handoff -->
## Dead ends
EOT
  echo "$f"
}

wif_stream_touch() { wif_fm_set "$1" updated "$(wif_today)"; }

# Append a line under "## <section>" (before the next "## " heading). 0 on success.
wif_section_append() { # file section line
  local f=$1 sec=$2 line=$3 tmp
  line=$(printf '%s' "$line" | tr '\n\r' '  ')
  tmp=$(mktemp) || return 1
  if sec="## $sec" line="$line" awk '
    BEGIN{insec=0; done=0}
    { if ($0==ENVIRON["sec"]) {insec=1; print; next}
      if (insec && /^## /) { if(!done){print ENVIRON["line"]; done=1}; insec=0 }
      print }
    END{ if(insec && !done) print ENVIRON["line"]; if(!insec && !done){print ""; print ENVIRON["sec"]; print ENVIRON["line"]} }
  ' "$f" > "$tmp"; then mv "$tmp" "$f"; else rm -f "$tmp"; return 1; fi
}

# Remove the first line in a section containing <needle>. Prints the removed
# line; returns 1 when nothing matched.
wif_section_remove() { # file section needle
  local f=$1 sec=$2 needle=$3 tmp removed
  removed=$(sec="## $sec" needle="$needle" awk '
    { if ($0==ENVIRON["sec"]) {insec=1; next}
      if (insec && /^## /) insec=0
      if (insec && index($0, ENVIRON["needle"])>0) { print; exit } }' "$f")
  [ -n "$removed" ] || return 1
  tmp=$(mktemp) || return 1
  if sec="## $sec" needle="$needle" awk '
    { if ($0==ENVIRON["sec"]) {insec=1; print; next}
      if (insec && /^## /) insec=0
      if (insec && !done && index($0, ENVIRON["needle"])>0) { done=1; next }
      print }' "$f" > "$tmp"; then mv "$tmp" "$f" && printf '%s\n' "$removed"; else rm -f "$tmp"; return 1; fi
}

wif_section_get() { # file section -> lines (no heading)
  [ -f "$1" ] || return 0
  sec="## $2" awk '$0==ENVIRON["sec"]{p=1;next} p&&/^## /{exit} p' "$1" 2>/dev/null
  return 0
}

# ---- sessions (JSON) -------------------------------------------------------

wif_session_file() { echo "$WIF_LEDGER/sessions/$1.json"; }
wif_ctx_file()     { echo "$WIF_LEDGER/sessions/$1.ctx.json"; }

# Create the session file if missing or unparsable.
wif_session_ensure() { # session_id stream_id
  local f; f=$(wif_session_file "$1")
  if [ -f "$f" ] && jq -e . "$f" >/dev/null 2>&1; then return 0; fi
  mkdir -p "$(dirname "$f")"
  jq -n --arg id "$1" --arg s "$2" --arg sc "$WIF_SCOPE" --arg t "$(wif_now)" \
    '{session_id:$id, scope:$sc, stream:$s, started:$t, ended:null, goal:null, ring:[]}' > "$f.tmp" && mv "$f.tmp" "$f"
  return 0
}

# Previous session for a stream: the stream's recorded last_session if it is
# not <exclude>, else the most recent *ended* session file for the stream.
# Prints a path or nothing; always returns 0.
wif_session_prev_for() { # stream_file stream_id [exclude_id]
  local sf=$1 s=$2 ex=${3:-} ls f best="" bestt=""
  ls=$(wif_fm_get "$sf" last_session)
  if [ -n "$ls" ] && [ "$ls" != "$ex" ] && [ -f "$(wif_session_file "$ls")" ]; then
    echo "$(wif_session_file "$ls")"; return 0
  fi
  for f in "$WIF_LEDGER/sessions"/*.json; do
    [ -f "$f" ] || continue
    case "$f" in *.ctx.json) continue ;; esac
    [ "$(basename "$f" .json)" = "$ex" ] && continue
    t=$(jq -r 'select(.stream==$s) | .ended // .started // ""' --arg s "$s" "$f" 2>/dev/null) || continue
    [ -n "$t" ] || continue
    if [ -z "$bestt" ] || [ "$t" \> "$bestt" ]; then bestt=$t; best=$f; fi
  done
  [ -n "$best" ] && echo "$best"
  return 0
}

wif_first_line() { printf '%s' "$1" | tr -d '\r\000' | awk 'NF{print; exit}' | cut -c1-${2:-120}; return 0; }

wif_rel_age() { # epoch -> "3d" / "5h" / "12m"
  local now d; now=$(wif_epoch); d=$(( now - ${1:-0} ))
  if [ "${1:-0}" -eq 0 ]; then echo "?"; elif [ $d -ge 86400 ]; then echo "$((d/86400))d"
  elif [ $d -ge 3600 ]; then echo "$((d/3600))h"; else echo "$((d/60))m"; fi
}
