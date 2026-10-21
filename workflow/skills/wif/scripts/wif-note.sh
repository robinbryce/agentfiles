#!/usr/bin/env bash
# wif note "<text>" | wif note --done "<substring>"
# wif tangent "<text>" | wif remind <when> "<text>"   (when = YYYY-MM-DD | +Nd | landed)
# Appends one line to (or removes one line from) the stream's ## Notes section.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
kind=${WIF_NOTE_KIND:-followup}; due=""; done_=""
if [ "${1:-}" = --done ]; then done_=${2:-}; [ -n "$done_" ] || wif_die "--done needs a substring"; shift 2; fi
if [ "$kind" = reminder ] && [ -z "$done_" ]; then
  when=${1:-}; shift || true
  case "$when" in
    landed) due=landed ;;
    +[0-9]*d) n=${when#+}; n=${n%d}; due=$(date -u -v+"${n}"d +%Y-%m-%d 2>/dev/null || date -u -d "+${n} days" +%Y-%m-%d) ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) due=$when ;;
    *) wif_die "remind needs <when>: YYYY-MM-DD | +Nd | landed" ;;
  esac
fi
text="$*"
[ -n "$text$done_" ] || wif_die "note text required"
wif_resolve "$PWD"
[ "$WIF_SERVED" = 1 ] || wif_die "scope $WIF_SCOPE is not served by account $WIF_ACCOUNT — nothing recorded"
[ "$WIF_KIND" = none ] && wif_die "no backing here"
wif_ledger_init "$WIF_SCOPE" >/dev/null
if [ ! -f "$WIF_STREAM" ]; then
  [ -f "$WIF_LEDGER/archive/$WIF_ID.md" ] && wif_die "stream $WIF_ID is closed (archived); re-open with: wif adopt ."
  [ "$WIF_KIND" = herdr ] || wif_die "no stream for $WIF_ID; wif adopt . first"
  wif_stream_create "$WIF_ID" "$WIF_SCOPE" "$WIF_KIND" "$WIF_PATH" >/dev/null
fi
if [ -n "$done_" ]; then
  removed=$(wif_section_remove "$WIF_STREAM" Notes "$done_") || wif_die "no note on $WIF_ID contains '$done_'"
  wif_stream_touch "$WIF_STREAM"; echo "removed from $WIF_ID: $removed"; exit 0
fi
tag="[$kind${due:+ due=$due}]"
wif_section_append "$WIF_STREAM" Notes "- $tag $(wif_today) $text" || wif_die "write failed"
wif_stream_touch "$WIF_STREAM"
echo "noted on $WIF_ID: $tag $text"
