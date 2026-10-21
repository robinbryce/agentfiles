#!/usr/bin/env bash
# wif ctx [--session ID] [--json] — context usage from the statusline dump. Exit 0 always.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
sid="${CLAUDE_SESSION_ID:-}"; json=0
while [ $# -gt 0 ]; do case "$1" in --session) sid=$2; shift 2 ;; --json) json=1; shift ;; *) shift ;; esac; done
wif_resolve "$PWD"
[ -z "$sid" ] && [ -n "$WIF_STREAM" ] && sid=$(wif_fm_get "$WIF_STREAM" last_session)
case "$sid" in */*|.*) sid="" ;; esac
c=""; [ -n "$sid" ] && c=$(wif_ctx_file "$sid")
if [ -n "$c" ] && [ -f "$c" ]; then
  if [ $json = 1 ]; then cat "$c"; else
    pct=$(jq -r '.used_pct // "?"' "$c" 2>/dev/null || echo "?"); t=$(jq -r '.t // ""' "$c" 2>/dev/null || true)
    echo "ctx ${pct}% (session ${sid:0:8}, as of $t)"
    case "$pct" in *[!0-9]*|'') ;; *) [ "$pct" -ge "$WIF_ROTATE_PCT" ] && echo "ROTATE: at or past ${WIF_ROTATE_PCT}% — run the handoff protocol, then /clear" ;; esac
  fi
else
  [ $json = 1 ] && echo '{}' || echo "ctx ?% (no statusline dump for session '${sid:-unknown}'; is wif statusline installed?)"
fi
exit 0
