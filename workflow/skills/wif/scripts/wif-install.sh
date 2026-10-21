#!/usr/bin/env bash
# wif install [--apply] [--remove] [--force-statusline] [--config-dir DIR]... [--bin DIR]
# Merges wif hooks + statusLine into each config dir's settings.json (shows a
# diff; writes only with --apply, after a timestamped backup) and links the
# `wif` CLI into ~/.local/bin. Default config dirs: ~/.claude-justgames ~/.claude-personal
# A statusLine that is not wif's is kept unless --force-statusline.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
apply=0; remove=0; force=0; dirs=(); bin="$HOME/.local/bin"
while [ $# -gt 0 ]; do case "$1" in
  --apply) apply=1; shift ;; --remove) remove=1; shift ;; --force-statusline) force=1; shift ;;
  --config-dir) dirs+=("$2"); shift 2 ;; --bin) bin=$2; shift 2 ;;
  *) wif_die "unknown arg $1" ;; esac; done
[ ${#dirs[@]} -gt 0 ] || dirs=("$HOME/.claude-justgames" "$HOME/.claude-personal")
hook="$WIF_SKILL_DIR/scripts/wif hook"; sl="$WIF_SKILL_DIR/scripts/wif statusline"
patch=$(jq -n --arg h "$hook" --arg s "$sl" '{
  statusLine:{type:"command", command:$s, refreshInterval:30},
  hooks:{
    UserPromptSubmit:[{hooks:[{type:"command", command:$h, timeout:10}]}],
    Stop:[{hooks:[{type:"command", command:$h, timeout:10}]}],
    SessionStart:[{matcher:"startup|resume|clear|compact", hooks:[{type:"command", command:$h, timeout:10}]}],
    SessionEnd:[{hooks:[{type:"command", command:$h, timeout:5}]}]
  }}')
# strip wif's own hook commands from every group; drop groups left empty; drop events left empty
strip='.hooks = ((.hooks // {}) | with_entries(.value |= (map(.hooks |= map(select(.command != $h))) | map(select((.hooks|length) > 0)))) | with_entries(select((.value|length) > 0)))'
rc=0
for d in "${dirs[@]}"; do
  f="$d/settings.json"
  if [ -f "$f" ]; then cur=$(cat "$f"); else cur='{}'; fi
  if ! jq -e . <<<"$cur" >/dev/null 2>&1; then echo "== $f: not valid JSON — skipped" >&2; rc=1; continue; fi
  if [ $remove = 1 ]; then
    new=$(jq --arg h "$hook" "$strip"' | if (.statusLine.command // "" | test("wif statusline")) then del(.statusLine) else . end
      | if .hooks == {} then del(.hooks) else . end' <<<"$cur") || { echo "== $f: jq failed" >&2; rc=1; continue; }
  else
    forcej=false; [ $force = 1 ] && forcej=true
    new=$(jq --argjson p "$patch" --arg h "$hook" --argjson force "$forcej" "$strip"'
      | if (.statusLine == null) or (.statusLine.command // "" | test("wif statusline")) or $force then .statusLine = $p.statusLine else . end
      | reduce ($p.hooks|to_entries[]) as $e (.; .hooks[$e.key] = ((.hooks[$e.key] // []) + $e.value))' <<<"$cur") || { echo "== $f: jq failed" >&2; rc=1; continue; }
    if ! jq -e '.statusLine.command // "" | test("wif statusline")' <<<"$new" >/dev/null; then
      echo "== $f: keeping your existing statusLine ($(jq -r '.statusLine.command' <<<"$cur")); pass --force-statusline to replace" >&2
    fi
  fi
  [ -n "$new" ] && jq -e . <<<"$new" >/dev/null 2>&1 || { echo "== $f: refusing to write empty/invalid result" >&2; rc=1; continue; }
  echo "== $f"
  if diff -u <(echo "$cur") <(echo "$new") >/dev/null; then echo "   (no change)"; else diff -u <(echo "$cur") <(echo "$new") | sed 's/^/   /' | head -80; fi
  if [ $apply = 1 ]; then
    mkdir -p "$d"; [ -f "$f" ] && cp "$f" "$f.bak.$(date +%Y%m%d%H%M%S)"
    printf '%s\n' "$new" > "$f.tmp" && mv "$f.tmp" "$f"; echo "   applied (backup kept)"
  fi
done
if [ $remove = 0 ]; then
  echo "== $bin/wif -> $WIF_SKILL_DIR/scripts/wif"
  if [ $apply = 1 ]; then mkdir -p "$bin"; ln -sfn "$WIF_SKILL_DIR/scripts/wif" "$bin/wif"; echo "   linked"; else echo "   (would link)"; fi
fi
[ $apply = 1 ] || echo "dry run — re-run with --apply to write"
exit $rc
