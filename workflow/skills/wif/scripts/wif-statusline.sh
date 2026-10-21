#!/usr/bin/env bash
# Claude Code statusline entrypoint (stdin JSON). Renders up to 3 lines and
# dumps context usage to the session's ctx sidecar so `wif ctx` can read it.
# Fast path only: jq + small files, no git.
set -u
trap 'exit 0' ERR
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh" || exit 0
IN=$(cat 2>/dev/null) || exit 0
sid=$(jq -r '.session_id // ""' <<<"$IN"); cwd=$(jq -r '.workspace.current_dir // .cwd // ""' <<<"$IN")
model=$(jq -r '.model.display_name // "?"' <<<"$IN")
pct=$(jq -r '.context_window.used_percentage // 0 | floor' <<<"$IN")
cost=$(jq -r '.cost.total_cost_usd // 0' <<<"$IN")
wif_resolve "${cwd:-$PWD}"
col() { if [ "$pct" -ge "$WIF_ROTATE_PCT" ]; then printf '\033[31m'; elif [ "$pct" -ge 40 ]; then printf '\033[33m'; else printf '\033[32m'; fi; }
rst=$'\033[0m'; dim=$'\033[2m'
acct="$WIF_ACCOUNT/$WIF_SCOPE"; [ "$WIF_SERVED" = 1 ] || acct="$acct(unserved)"
if [ "$WIF_KIND" = none ] || [ "$WIF_SERVED" != 1 ]; then
  printf '%s[%s]%s %s · %s%d%%%s ctx · %s\n' "$dim" "$acct" "$rst" "${model}" "$(col)" "$pct" "$rst" "$(basename "${cwd:-$PWD}")"
  exit 0
fi
# dump ctx sidecar (statusline runs often; sidecar avoids racing the hook's session file)
if [ -n "$sid" ] && [ -d "$WIF_LEDGER/sessions" ]; then
  jq -n --argjson p "$pct" --arg m "$model" --argjson c "$cost" --arg t "$(wif_now)" --arg s "$WIF_ID" \
    '{used_pct:$p, model:$m, cost_usd:$c, t:$t, stream:$s}' > "$(wif_ctx_file "$sid").tmp" 2>/dev/null \
    && mv "$(wif_ctx_file "$sid").tmp" "$(wif_ctx_file "$sid")"
fi
st=""; g=""; n=""; p=""
if [ -f "$WIF_STREAM" ]; then st=$(wif_fm_get "$WIF_STREAM" status); g=$(wif_fm_get "$WIF_STREAM" goal); n=$(wif_fm_get "$WIF_STREAM" next); p=$(wif_fm_get "$WIF_STREAM" position); fi
sg=""; li=""
sf=$(wif_session_file "$sid"); if [ -f "$sf" ]; then sg=$(jq -r '.goal // ""' "$sf"); li=$(jq -r '(.ring|last)?.intent // ""' "$sf"); fi
w=${COLUMNS:-120}; trim() { local s=$1 m=$2; [ ${#s} -gt "$m" ] && s="${s:0:$((m-1))}…"; printf '%s' "$s"; }
printf '%s[%s]%s %s · %s%s · %s%d%%%s ctx · %s%s\n' "$dim" "$acct" "$rst" "$WIF_ID" "${st:-untracked}" "${p:+ · $p}" "$(col)" "$pct" "$rst" "$model" "$([ "$pct" -ge "$WIF_ROTATE_PCT" ] && printf ' · ROTATE')"
printf '%sgoal:%s %s   %snext:%s %s\n' "$dim" "$rst" "$(trim "${sg:-${g:--}}" $((w/2-8)))" "$dim" "$rst" "$(trim "${n:--}" $((w/2-8)))"
[ -n "$li" ] && printf '%s~%s %s\n' "$dim" "$rst" "$(trim "$li" $((w-4)))"
exit 0
