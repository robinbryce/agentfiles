#!/usr/bin/env bash
# wif shared helpers. Sourced by every subcommand; never executed directly.
# Contract: nothing here exits non-zero on "no stream here" — that is a
# normal answer, not an error. Hooks depend on that.
set -u

WIF_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
WIF_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
WIF_RING=10
WIF_STREAM_CAP=120
WIF_STALE_DAYS=14
WIF_ROTATE_PCT=60
WIF_PR_TTL=$((6*3600))

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
  v="WIF_ROOT_$(echo "$s" | tr '[:lower:]' '[:upper:]')"
  if [ -n "${!v:-}" ]; then echo "${!v}"; return; fi
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
# Prints: "<kind> <id> <path>" with kind herdr|repo, or "none" .
wif_backing_of() {
  local p=$1 phys task root top common repo branch
  phys=$(wif_phys "$p") || { echo none; return; }
  case "$phys" in
    */.worktrees-herdr/*)
      root="${phys%%/.worktrees-herdr/*}"
      task="${phys#*/.worktrees-herdr/}"; task="${task%%/*}"
      echo "herdr $task $root/.worktrees-herdr/$task"; return ;;
  esac
  top=$(git -C "$phys" rev-parse --show-toplevel 2>/dev/null) || { echo none; return; }
  common=$(git -C "$phys" rev-parse --git-common-dir 2>/dev/null)
  case "$common" in /*) ;; *) common="$phys/$common" ;; esac
  repo=$(basename "$(dirname "$(wif_phys "$common")")")
  branch=$(git -C "$phys" symbolic-ref --short -q HEAD 2>/dev/null || echo detached)
  echo "repo ${repo}--$(echo "$branch" | tr '/' '-') $top"
}

# Resolve everything for a cwd. Sets WIF_SCOPE WIF_ROOT WIF_ACCOUNT WIF_SERVED
# WIF_KIND WIF_ID WIF_PATH WIF_LEDGER WIF_STREAM (file, may not exist).
wif_resolve() {
  local cwd=${1:-$PWD} b
  WIF_ACCOUNT=$(wif_account)
  WIF_SCOPE=$(wif_scope_of "$(wif_phys "$cwd" || echo "$cwd")")
  WIF_ROOT=$(wif_scope_root "$WIF_SCOPE")
  if wif_account_serves "$WIF_ACCOUNT" "$WIF_SCOPE"; then WIF_SERVED=1; else WIF_SERVED=0; fi
  WIF_LEDGER=$(wif_ledger "$WIF_SCOPE")
  b=$(wif_backing_of "$cwd")
  WIF_KIND=${b%% *}
  if [ "$WIF_KIND" = none ]; then WIF_ID=""; WIF_PATH=""; WIF_STREAM=""; return; fi
  WIF_ID=$(echo "$b" | awk '{print $2}')
  WIF_PATH=$(echo "$b" | cut -d' ' -f3-)
  WIF_STREAM="$WIF_LEDGER/streams/$WIF_ID.md"
}

# A session may auto-bind here? herdr: yes. repo: only if stream exists.
wif_bindable() {
  [ "$WIF_SERVED" = 1 ] || return 1
  case "$WIF_KIND" in
    herdr) return 0 ;;
    repo) [ -f "$WIF_STREAM" ] ;;
    *) return 1 ;;
  esac
}

# ---- stream files (markdown + flat YAML frontmatter) -----------------------

wif_fm_get() { # file key
  awk -v k="$2" '
    NR==1 && $0=="---" {infm=1; next}
    infm && $0=="---" {exit}
    infm && index($0, k ": ")==1 {
      v=substr($0, length(k)+3); gsub(/^"|"$/, "", v); gsub(/\\"/, "\"", v); print v; exit }
  ' "$1" 2>/dev/null
}

wif_fm_set() { # file key value  (adds the key if absent)
  local f=$1 k=$2 v=$3 tmp esc
  esc=$(printf '%s' "$v" | sed 's/"/\\"/g')
  tmp=$(mktemp)
  awk -v k="$k" -v v="$esc" '
    BEGIN{done=0}
    NR==1 && $0=="---" {infm=1; print; next}
    infm && $0=="---" { if(!done){print k ": \"" v "\""; done=1} ; infm=0; print; next }
    infm && index($0, k ": ")==1 { if(!done){print k ": \"" v "\""; done=1}; next }
    {print}
  ' "$f" > "$tmp" && mv "$tmp" "$f"
}

wif_stream_create() { # id scope kind path [status]
  local id=$1 scope=$2 kind=$3 path=$4 status=${5:-active} f
  f="$(wif_ledger "$scope")/streams/$id.md"
  [ -f "$f" ] && { echo "$f"; return; }
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

# Append a line under "## <section>" (before the next "## " heading).
wif_section_append() { # file section line
  local f=$1 sec=$2 line=$3 tmp
  tmp=$(mktemp)
  awk -v sec="## $sec" -v line="$line" '
    BEGIN{insec=0; done=0}
    { if ($0==sec) {insec=1; print; next}
      if (insec && /^## /) { if(!done){print line; done=1}; insec=0 }
      print }
    END{ if(insec && !done) print line; if(!insec && !done){print ""; print sec; print line} }
  ' "$f" > "$tmp" && mv "$tmp" "$f"
}

wif_section_get() { # file section -> lines (no heading)
  awk -v sec="## $2" '$0==sec{p=1;next} p&&/^## /{exit} p' "$1" 2>/dev/null
}

# ---- sessions (JSON) -------------------------------------------------------

wif_session_file() { echo "$WIF_LEDGER/sessions/$1.json"; }
wif_ctx_file()     { echo "$WIF_LEDGER/sessions/$1.ctx.json"; }

wif_session_ensure() { # session_id stream_id
  local f; f=$(wif_session_file "$1")
  [ -f "$f" ] && return
  mkdir -p "$(dirname "$f")"
  jq -n --arg id "$1" --arg s "$2" --arg sc "$WIF_SCOPE" --arg t "$(wif_now)" \
    '{session_id:$id, scope:$sc, stream:$s, started:$t, ended:null, goal:null, ring:[]}' > "$f"
}

# Most recent session file for a stream (by mtime), excluding one id.
wif_session_latest_for() { # stream_id [exclude_id]
  local s=$1 ex=${2:-} f
  for f in $(ls -t "$WIF_LEDGER/sessions"/*.json 2>/dev/null | grep -v '\.ctx\.json$'); do
    [ "$(basename "$f" .json)" = "$ex" ] && continue
    [ "$(jq -r .stream "$f" 2>/dev/null)" = "$s" ] && { echo "$f"; return; }
  done
}

wif_first_line() { printf '%s' "$1" | tr -d '\r' | awk 'NF{print; exit}' | cut -c1-${2:-120}; }

wif_rel_age() { # epoch -> "3d" / "5h" / "12m"
  local now d; now=$(wif_epoch); d=$(( now - ${1:-0} ))
  if [ "${1:-0}" -eq 0 ]; then echo "?"; elif [ $d -ge 86400 ]; then echo "$((d/86400))d"
  elif [ $d -ge 3600 ]; then echo "$((d/3600))h"; else echo "$((d/60))m"; fi
}
