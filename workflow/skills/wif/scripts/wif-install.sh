#!/usr/bin/env bash
# wif install [--apply] [--remove] [--config-dir DIR]... [--bin DIR]
# Merges wif hooks + statusLine into each config dir's settings.json (shows a
# diff; writes only with --apply, after a timestamped backup) and links the
# `wif` CLI into ~/.local/bin. Default config dirs: ~/.claude-justgames ~/.claude-personal
set -u
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh"
apply=0; remove=0; dirs=(); bin="$HOME/.local/bin"
while [ $# -gt 0 ]; do case "$1" in
  --apply) apply=1; shift ;; --remove) remove=1; shift ;; --config-dir) dirs+=("$2"); shift 2 ;; --bin) bin=$2; shift 2 ;;
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
for d in "${dirs[@]}"; do
  f="$d/settings.json"; mkdir -p "$d"; [ -f "$f" ] || echo '{}' > "$f"
  if [ $remove = 1 ]; then
    new=$(jq --arg h "$hook" '
      del(.statusLine | select(.command|tostring|test("wif statusline")))
      | .hooks |= (with_entries(.value |= map(select(any(.hooks[]?; .command==$h)|not)))
                   | with_entries(select(.value|length>0)))
      | if .hooks=={} then del(.hooks) else . end' "$f")
  else
    # replace any prior wif entries, keep everything else, append ours per event
    new=$(jq --argjson p "$patch" --arg h "$hook" '
      .statusLine = $p.statusLine
      | .hooks = ((.hooks // {}) | with_entries(.value |= map(select(any(.hooks[]?; .command==$h)|not))))
      | reduce ($p.hooks|to_entries[]) as $e (.; .hooks[$e.key] = ((.hooks[$e.key] // []) + $e.value))' "$f")
  fi
  echo "== $f"
  if diff -u "$f" <(echo "$new") >/dev/null; then echo "   (no change)"; else diff -u "$f" <(echo "$new") | sed 's/^/   /' | head -80; fi
  if [ $apply = 1 ]; then cp "$f" "$f.bak.$(date +%Y%m%d%H%M%S)"; echo "$new" > "$f"; echo "   applied (backup kept)"; fi
done
if [ $remove = 0 ]; then
  echo "== $bin/wif -> $WIF_SKILL_DIR/scripts/wif"
  if [ $apply = 1 ]; then mkdir -p "$bin"; ln -sfn "$WIF_SKILL_DIR/scripts/wif" "$bin/wif"; echo "   linked"; else echo "   (would link)"; fi
fi
[ $apply = 1 ] || echo "dry run — re-run with --apply to write"
