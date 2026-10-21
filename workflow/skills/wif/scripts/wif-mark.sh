#!/usr/bin/env bash
# wif mark [-g goal] [-i intent] [-p position] [-n next] [-s status] [--done text] [--session ID]
# Session-level: -g (session goal), -i (intent of the current prompt).
# Stream-level: -p -n -s --done.  Creates the stream if bindable and missing.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
sid="${CLAUDE_SESSION_ID:-}"; goal=""; intent=""; pos=""; next=""; status=""; done_=""
while [ $# -gt 0 ]; do case "$1" in
  -g) goal=$2; shift 2 ;; -i) intent=$2; shift 2 ;; -p) pos=$2; shift 2 ;; -n) next=$2; shift 2 ;;
  -s) status=$2; shift 2 ;; --done) done_=$2; shift 2 ;; --session) sid=$2; shift 2 ;;
  *) wif_die "unknown arg $1" ;; esac; done
wif_resolve "$PWD"
[ "$WIF_SERVED" = 1 ] || wif_die "scope $WIF_SCOPE is not served by account $WIF_ACCOUNT — nothing recorded"
[ "$WIF_KIND" = none ] && wif_die "no backing here; run from a herdr container or a repo with a stream (wif adopt)"
wif_ledger_init "$WIF_SCOPE" >/dev/null
[ -f "$WIF_STREAM" ] || { [ "$WIF_KIND" = herdr ] || wif_die "no stream for $WIF_ID; wif adopt . first"; wif_stream_create "$WIF_ID" "$WIF_SCOPE" "$WIF_KIND" "$WIF_PATH" >/dev/null; }
if [ -n "$status" ]; then case "$status" in active|parked|blocked|landed|closed) ;; *) wif_die "bad status";; esac; wif_fm_set "$WIF_STREAM" status "$status"; fi
[ -n "$pos" ]  && wif_fm_set "$WIF_STREAM" position "$pos"
[ -n "$next" ] && wif_fm_set "$WIF_STREAM" next "$next"
[ -n "$done_" ] && wif_section_append "$WIF_STREAM" Now "- done $(wif_today): $done_"
[ -n "$pos$next$status$done_" ] && wif_stream_touch "$WIF_STREAM"
if [ "$status" = closed ]; then mkdir -p "$WIF_LEDGER/archive"; mv "$WIF_STREAM" "$WIF_LEDGER/archive/$WIF_ID.md"; echo "archived → $WIF_LEDGER/archive/$WIF_ID.md"; fi
if [ -n "$goal$intent" ]; then
  if [ -z "$sid" ]; then f=$(wif_session_latest_for "$WIF_ID"); sid=$(basename "${f:-}" .json); fi
  [ -n "$sid" ] || wif_die "no session id (pass --session) and no session on record for $WIF_ID"
  wif_session_ensure "$sid" "$WIF_ID"; f=$(wif_session_file "$sid"); tmp=$(mktemp)
  if [ -n "$goal" ]; then jq --arg g "$goal" '.goal=$g' "$f" > "$tmp" && mv "$tmp" "$f"; fi
  if [ -n "$intent" ]; then
    # attach to the latest ring entry (the prompt being answered), else push one
    jq --arg i "$intent" --arg t "$(wif_now)" '
      if (.ring|length)>0 then .ring[-1].intent=$i | .ring[-1].pinned=true
      else .ring += [{t:$t, prompt:null, intent:$i, pinned:true, outcome:null}] end' "$f" > "$tmp" && mv "$tmp" "$f"
  fi
fi
echo "marked $WIF_ID${status:+ status=$status}${pos:+ position=\"$pos\"}${next:+ next=\"$next\"}${goal:+ session-goal=\"$goal\"}${intent:+ intent=\"$intent\"}"
