#!/usr/bin/env bash
# wif ctx [--session ID] [--json] — context usage from the statusline dump. Exit 0 always.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
sid="${CLAUDE_SESSION_ID:-}"; json=0
while [ $# -gt 0 ]; do case "$1" in --session) sid=$2; shift 2 ;; --json) json=1; shift ;; *) shift ;; esac; done
wif_resolve "$PWD"
if [ -z "$sid" ] && [ -n "$WIF_ID" ]; then f=$(wif_session_latest_for "$WIF_ID"); sid=$(basename "${f:-}" .json); fi
c=""; [ -n "$sid" ] && c=$(wif_ctx_file "$sid")
if [ -n "$c" ] && [ -f "$c" ]; then
  if [ $json = 1 ]; then cat "$c"; else
    pct=$(jq -r '.used_pct // "?"' "$c"); t=$(jq -r '.t // ""' "$c")
    echo "ctx ${pct}% (session ${sid:0:8}, as of $t)"
    [ "$pct" != "?" ] && [ "$pct" -ge "$WIF_ROTATE_PCT" ] && echo "ROTATE: at or past ${WIF_ROTATE_PCT}% — run the handoff protocol, then /clear"
  fi
else
  [ $json = 1 ] && echo '{}' || echo "ctx ?% (no statusline dump for session '${sid:-unknown}'; is wif statusline installed?)"
fi
exit 0
