#!/usr/bin/env bash
# wif adopt <task|.|path> [-s status] [-g goal] [-p parent] [-n next] [--scope S]
# Create a Stream for a herdr container (or the current repo checkout). On an
# existing stream only the fields you pass change. Re-opens an archived stream.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
target=""; status=""; goal=""; parent=""; next=""; scope=""
while [ $# -gt 0 ]; do case "$1" in
  -s) status=$2; shift 2 ;; -g) goal=$2; shift 2 ;; -p) parent=$2; shift 2 ;; -n) next=$2; shift 2 ;;
  --scope) scope=$2; shift 2 ;; -*) wif_die "unknown arg $1" ;; *) target=$1; shift ;; esac; done
case "$status" in ''|active|parked|blocked|landed|closed) ;; *) wif_die "status must be active|parked|blocked|landed|closed" ;; esac
wif_resolve "$PWD"
if [ -n "$scope" ]; then
  case " $(wif_known_scopes) " in *" $scope "*) ;; *) wif_die "unknown scope '$scope'" ;; esac
  WIF_SCOPE=$scope; WIF_ROOT=$(wif_scope_root "$scope"); WIF_LEDGER=$(wif_ledger "$scope")
  wif_account_serves "$WIF_ACCOUNT" "$scope" && WIF_SERVED=1 || WIF_SERVED=0
fi
if [ -n "$target" ] && [ "$target" != . ]; then
  if [ -d "$target" ]; then wif_resolve "$target"
  elif [ -d "$WIF_ROOT/.worktrees-herdr/$target" ]; then wif_resolve "$WIF_ROOT/.worktrees-herdr/$target"
  else wif_die "no container '$target' under $WIF_ROOT/.worktrees-herdr"; fi
fi
[ "$WIF_SERVED" = 1 ] || wif_die "scope $WIF_SCOPE is not served by account $WIF_ACCOUNT — nothing recorded"
[ "$WIF_KIND" = none ] && wif_die "no backing here (not a herdr container, not a git repo)"
wif_ledger_init "$WIF_SCOPE" >/dev/null
created=0
if [ ! -f "$WIF_STREAM" ] && [ -f "$WIF_LEDGER/archive/$WIF_ID.md" ]; then
  mv "$WIF_LEDGER/archive/$WIF_ID.md" "$WIF_STREAM"; echo "re-opened from archive"
fi
[ -f "$WIF_STREAM" ] || { wif_stream_create "$WIF_ID" "$WIF_SCOPE" "$WIF_KIND" "$WIF_PATH" "${status:-active}" >/dev/null; created=1; }
f=$WIF_STREAM
[ -n "$goal" ]   && wif_fm_set "$f" goal "$goal"
[ -n "$parent" ] && wif_fm_set "$f" parent "$parent"
[ -n "$next" ]   && wif_fm_set "$f" next "$next"
if [ -n "$status" ]; then wif_fm_set "$f" status "$status"; elif [ $created = 0 ] && [ "$(wif_fm_get "$f" status)" = closed ]; then wif_fm_set "$f" status active; fi
wif_stream_touch "$f"
if [ "$(wif_fm_get "$f" status)" = closed ]; then mv "$f" "$WIF_LEDGER/archive/$WIF_ID.md"; echo "archived → $WIF_LEDGER/archive/$WIF_ID.md"; else echo "$f"; fi
