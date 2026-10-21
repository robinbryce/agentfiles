#!/usr/bin/env bash
# wif adopt <task|.> [-s status] [-g goal] [-p parent] [-n next] [--scope S]
# Create a Stream file for a herdr container (or the current repo checkout).
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
target=""; status=active; goal=""; parent=""; next=""; scope=""
while [ $# -gt 0 ]; do case "$1" in
  -s) status=$2; shift 2 ;; -g) goal=$2; shift 2 ;; -p) parent=$2; shift 2 ;; -n) next=$2; shift 2 ;;
  --scope) scope=$2; shift 2 ;; *) target=$1; shift ;; esac; done
case "$status" in active|parked|blocked|landed|closed) ;; *) wif_die "status must be active|parked|blocked|landed|closed" ;; esac
if [ -z "$target" ] || [ "$target" = . ]; then wif_resolve "$PWD"
else
  wif_resolve "$PWD"; [ -n "$scope" ] && { WIF_SCOPE=$scope; WIF_ROOT=$(wif_scope_root "$scope"); WIF_LEDGER=$(wif_ledger "$scope"); }
  if [ -d "$target" ]; then wif_resolve "$target"
  elif [ -d "$WIF_ROOT/.worktrees-herdr/$target" ]; then wif_resolve "$WIF_ROOT/.worktrees-herdr/$target"
  else wif_die "no container '$target' under $WIF_ROOT/.worktrees-herdr"; fi
fi
[ "$WIF_SERVED" = 1 ] || wif_die "scope $WIF_SCOPE is not served by account $WIF_ACCOUNT — nothing recorded"
[ "$WIF_KIND" = none ] && wif_die "no backing here (not a herdr container, not a git repo)"
wif_ledger_init "$WIF_SCOPE" >/dev/null
f=$(wif_stream_create "$WIF_ID" "$WIF_SCOPE" "$WIF_KIND" "$WIF_PATH" "$status")
[ -n "$goal" ]   && wif_fm_set "$f" goal "$goal"
[ -n "$parent" ] && wif_fm_set "$f" parent "$parent"
[ -n "$next" ]   && wif_fm_set "$f" next "$next"
wif_fm_set "$f" status "$status"; wif_stream_touch "$f"
echo "$f"
