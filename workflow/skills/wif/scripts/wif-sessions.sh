#!/usr/bin/env bash
# wif sessions [stream] [-n N] — recent sessions with goal and last intent.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
n=8; want=""
while [ $# -gt 0 ]; do case "$1" in -n) n=$2; shift 2 ;; *) want=$1; shift ;; esac; done
wif_resolve "$PWD"; [ -z "$want" ] && want=$WIF_ID
for f in $(ls -t "$WIF_LEDGER/sessions"/*.json 2>/dev/null | grep -v '\.ctx\.json$' | head -40); do
  s=$(jq -r .stream "$f"); [ -n "$want" ] && [ "$s" != "$want" ] && continue
  jq -r '"\(.session_id[0:8])  \(.started[0:16])  \(.stream)  goal=\(.goal // "-")  last=\((.ring|last)?.intent // (.ring|last)?.prompt // "-")  ended=\(.ended // "no")"' "$f"
  n=$((n-1)); [ $n -le 0 ] && break
done
exit 0
