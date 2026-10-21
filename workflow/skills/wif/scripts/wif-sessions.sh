#!/usr/bin/env bash
# wif sessions [stream] [-n N] — recent sessions with goal and last intent.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
n=8; want=""
while [ $# -gt 0 ]; do case "$1" in -n) n=$2; shift 2 ;; *) want=$1; shift ;; esac; done
wif_resolve "$PWD"; [ -z "$want" ] && want=$WIF_ID
[ -d "$WIF_LEDGER/sessions" ] || exit 0
ls -t "$WIF_LEDGER/sessions" 2>/dev/null | while IFS= read -r name; do
  case "$name" in *.ctx.json|*.tmp) continue ;; *.json) ;; *) continue ;; esac
  f="$WIF_LEDGER/sessions/$name"
  s=$(jq -r '.stream // ""' "$f" 2>/dev/null) || continue
  [ -n "$want" ] && [ "$s" != "$want" ] && continue
  jq -r '"\(.session_id[0:8])  \(.started[0:16])  \(.stream)  goal=\(.goal // "-")  last=\((.ring|last)?.intent // (.ring|last)?.prompt // "-")  ended=\(.ended // "no")"' "$f" 2>/dev/null
  n=$((n-1)); [ $n -le 0 ] && break
done
exit 0
