#!/usr/bin/env bash
# Claude Code statusline entrypoint (stdin JSON). Renders up to 3 lines and,
# for a bindable stream, dumps context usage to the session's ctx sidecar so
# `wif ctx` can read it. Fast path only: jq + small files, no git.
set -u
trap 'exit 0' ERR
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh" || exit 0
IN=$(cat 2>/dev/null) || exit 0
j() { jq -r "$1" <<<"$IN" 2>/dev/null || true; }
sid=$(j '.session_id // ""'); cwd=$(j '.workspace.current_dir // .cwd // ""')
model=$(j '.model.display_name // "?"')
pct=$(j '(.context_window.used_percentage // 0) | (tonumber? // 0) | floor')
case "$pct" in ''|*[!0-9]*) pct=0 ;; esac
cost=$(j '(.cost.total_cost_usd // 0) | (tonumber? // 0)'); case "$cost" in ''|*[!0-9.]*) cost=0 ;; esac
wif_resolve "${cwd:-$PWD}"
col() { if [ "$pct" -ge "$WIF_ROTATE_PCT" ]; then printf '\033[31m'; elif [ "$pct" -ge 40 ]; then printf '\033[33m'; else printf '\033[32m'; fi; }
rst=$'\033[0m'; dim=$'\033[2m'
acct="$WIF_ACCOUNT/$WIF_SCOPE"; [ "$WIF_SERVED" = 1 ] || acct="$acct(unserved)"
if ! wif_bindable; then
  printf '%s[%s]%s %s · %s%d%%%s ctx · %s\n' "$dim" "$acct" "$rst" "$model" "$(col)" "$pct" "$rst" "$(basename "${cwd:-$PWD}")"
  exit 0
fi
case "$sid" in */*|.*|'') sid="" ;; esac
if [ -n "$sid" ] && [ -d "$WIF_LEDGER/sessions" ]; then
  c=$(wif_ctx_file "$sid")
  jq -n --argjson p "$pct" --arg m "$model" --argjson c "$cost" --arg t "$(wif_now)" --arg s "$WIF_ID" \
    '{used_pct:$p, model:$m, cost_usd:$c, t:$t, stream:$s}' > "$c.tmp" 2>/dev/null && mv "$c.tmp" "$c"
fi
st=$(wif_fm_get "$WIF_STREAM" status); g=$(wif_fm_get "$WIF_STREAM" goal); n=$(wif_fm_get "$WIF_STREAM" next); p=$(wif_fm_get "$WIF_STREAM" position)
sg=""; li=""
sf=$(wif_session_file "${sid:-none}"); if [ -f "$sf" ]; then sg=$(jq -r '.goal // ""' "$sf" 2>/dev/null || true); li=$(jq -r '(.ring|last)?.intent // ""' "$sf" 2>/dev/null || true); fi
w=${COLUMNS:-120}; case "$w" in ''|*[!0-9]*) w=120 ;; esac
trim() { local s=$1 m=$2; [ ${#s} -gt "$m" ] && s="${s:0:$((m-1))}…"; printf '%s' "$s"; }
printf '%s[%s]%s %s · %s%s · %s%d%%%s ctx · %s%s\n' "$dim" "$acct" "$rst" "$WIF_ID" "${st:-untracked}" "${p:+ · $p}" "$(col)" "$pct" "$rst" "$model" "$([ "$pct" -ge "$WIF_ROTATE_PCT" ] && printf ' · ROTATE')"
printf '%sgoal:%s %s   %snext:%s %s\n' "$dim" "$rst" "$(trim "${sg:-${g:--}}" $((w/2-8)))" "$dim" "$rst" "$(trim "${n:--}" $((w/2-8)))"
[ -n "$li" ] && printf '%s~%s %s\n' "$dim" "$rst" "$(trim "$li" $((w-4)))"
exit 0
