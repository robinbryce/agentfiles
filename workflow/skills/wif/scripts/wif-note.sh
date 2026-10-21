#!/usr/bin/env bash
# wif note "<text>"  |  wif tangent "<text>"  |  wif remind <when> "<text>"
# Appends one line to the stream's ## Notes section. when = YYYY-MM-DD | +Nd | landed
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
kind=${WIF_NOTE_KIND:-followup}; due=""
if [ "$kind" = reminder ]; then
  when=${1:-}; shift || true
  case "$when" in
    landed) due=landed ;;
    +[0-9]*d) n=${when#+}; n=${n%d}; due=$(date -u -v+"${n}"d +%Y-%m-%d 2>/dev/null || date -u -d "+${n} days" +%Y-%m-%d) ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) due=$when ;;
    *) wif_die "remind needs <when>: YYYY-MM-DD | +Nd | landed" ;;
  esac
fi
text="$*"; [ -n "$text" ] || wif_die "note text required"
wif_resolve "$PWD"
[ "$WIF_SERVED" = 1 ] || wif_die "scope $WIF_SCOPE is not served by account $WIF_ACCOUNT — nothing recorded"
[ "$WIF_KIND" = none ] && wif_die "no backing here"
wif_ledger_init "$WIF_SCOPE" >/dev/null
[ -f "$WIF_STREAM" ] || { [ "$WIF_KIND" = herdr ] || wif_die "no stream for $WIF_ID; wif adopt . first"; wif_stream_create "$WIF_ID" "$WIF_SCOPE" "$WIF_KIND" "$WIF_PATH" >/dev/null; }
tag="[$kind${due:+ due=$due}]"
wif_section_append "$WIF_STREAM" Notes "- $tag $(wif_today) $text"
wif_stream_touch "$WIF_STREAM"
echo "noted on $WIF_ID: $tag $text"
