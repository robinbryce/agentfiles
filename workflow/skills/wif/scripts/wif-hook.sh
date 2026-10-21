#!/usr/bin/env bash
# Claude Code hook entrypoint (stdin JSON). Installed for UserPromptSubmit, Stop,
# SessionStart, SessionEnd. MUST be fast and MUST exit 0: a non-zero exit on
# UserPromptSubmit blocks Robin's prompt. Every path below ends in exit 0.
set -u
trap 'exit 0' ERR
. "$(dirname "${BASH_SOURCE[0]}")/wif-lib.sh" || exit 0
IN=$(cat 2>/dev/null) || exit 0
[ -n "${WIF_HOOK_DEBUG:-}" ] && printf '%s\n' "$IN" >> "$WIF_HOOK_DEBUG"
ev=$(jq -r '.hook_event_name // ""' <<<"$IN" 2>/dev/null) || exit 0
sid=$(jq -r '.session_id // ""' <<<"$IN")
cwd=$(jq -r '.cwd // ""' <<<"$IN")
[ -n "$sid" ] && [ -n "$cwd" ] || exit 0
# subagents share the session id; only the main agent records
[ "$(jq -r '.agent_id // ""' <<<"$IN")" = "" ] || exit 0
wif_resolve "$cwd"
wif_bindable || exit 0
wif_ledger_init "$WIF_SCOPE" >/dev/null
[ -f "$WIF_STREAM" ] || wif_stream_create "$WIF_ID" "$WIF_SCOPE" "$WIF_KIND" "$WIF_PATH" >/dev/null
f=$(wif_session_file "$sid"); tmp=$(mktemp)
ctx_line() { # one compact context line for the model
  local st g n p sg li
  st=$(wif_fm_get "$WIF_STREAM" status); g=$(wif_fm_get "$WIF_STREAM" goal)
  n=$(wif_fm_get "$WIF_STREAM" next); p=$(wif_fm_get "$WIF_STREAM" position)
  sg=$(jq -r '.goal // ""' "$f" 2>/dev/null); li=$(jq -r '(.ring|last)?.intent // ""' "$f" 2>/dev/null)
  printf '[wif] %s · %s · goal: %s · next: %s · position: %s · session: %s · last intent: %s' \
    "$WIF_ID" "${st:-active}" "${g:--}" "${n:--}" "${p:--}" "${sg:-unset}" "${li:--}"
}
case "$ev" in
  UserPromptSubmit)
    pt=$(jq -r '.prompt_text // .prompt // ""' <<<"$IN"); first=$(wif_first_line "$pt" 120)
    # ignore slash-only and trivial prompts for the ring; still inject context
    wif_session_ensure "$sid" "$WIF_ID"
    case "$first" in /*) first="" ;; esac   # slash commands are not intents
    if [ -n "$first" ]; then
      jq --arg t "$(wif_now)" --arg p "$first" --argjson n "$WIF_RING" '
        .ring += [{t:$t, prompt:$p, intent:null, pinned:false, outcome:null}] | .ring = .ring[-$n:]' "$f" > "$tmp" && mv "$tmp" "$f"
    fi
    line=$(ctx_line)
    sg=$(jq -r '.goal // ""' "$f"); hint=""
    if [ -z "$sg" ]; then hint=" — session goal unset: when this prompt states one, record it with \`wif mark -g \"<one line>\" --session $sid\`"
    else hint=" — if this prompt starts new work, record \`wif mark -i \"<one line>\" --session $sid\`; follow-ups inherit"; fi
    jq -n --arg c "$line$hint" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit", additionalContext:$c}}'
    ;;
  Stop)
    [ -f "$f" ] || exit 0
    msg=$(jq -r '.last_assistant_message // ""' <<<"$IN"); first=$(wif_first_line "$msg" 120)
    [ -n "$first" ] || exit 0
    jq --arg o "$first" 'if (.ring|length)>0 then .ring[-1].outcome=$o else . end' "$f" > "$tmp" && mv "$tmp" "$f"
    ;;
  SessionStart)
    src=$(jq -r '.source // "startup"' <<<"$IN")
    wif_session_ensure "$sid" "$WIF_ID"
    prev=$(wif_session_latest_for "$WIF_ID" "$sid")
    body=$(printf '[wif] session %s on stream %s (%s)\n' "$src" "$WIF_ID" "$(wif_fm_get "$WIF_STREAM" status)")
    body+=$(printf '\ngoal: %s\nnext: %s\nposition: %s\n' "$(wif_fm_get "$WIF_STREAM" goal)" "$(wif_fm_get "$WIF_STREAM" next)" "$(wif_fm_get "$WIF_STREAM" position)")
    if [ -n "$prev" ]; then
      body+=$(printf '\nprevious session: goal=%s · last intent=%s · last outcome=%s\n' \
        "$(jq -r '.goal // "-"' "$prev")" "$(jq -r '(.ring|last)?.intent // (.ring|last)?.prompt // "-"' "$prev")" "$(jq -r '(.ring|last)?.outcome // "-"' "$prev")")
      case "$src" in clear|compact) # carry the goal forward
        pg=$(jq -r '.goal // ""' "$prev"); [ -n "$pg" ] && { jq --arg g "$pg" '.goal=$g' "$f" > "$tmp" && mv "$tmp" "$f"; } ;; esac
    fi
    h=$(wif_section_get "$WIF_STREAM" Handoff | grep -v '^<!--' | head -30)
    [ -n "$h" ] && body+=$(printf '\n## Handoff (from stream file)\n%s\n' "$h")
    nw=$(wif_section_get "$WIF_STREAM" Now | grep -v '^<!--' | head -20)
    [ -n "$nw" ] && body+=$(printf '\n## Now\n%s\n' "$nw")
    body+=$(printf '\nstream file: %s · dashboard: /wif\n' "$WIF_STREAM")
    jq -n --arg c "$body" '{hookSpecificOutput:{hookEventName:"SessionStart", additionalContext:$c}}'
    ;;
  SessionEnd)
    [ -f "$f" ] || exit 0
    jq --arg t "$(wif_now)" --arg r "$(jq -r '.reason // ""' <<<"$IN")" '.ended=$t | .end_reason=$r' "$f" > "$tmp" && mv "$tmp" "$f"
    ;;
esac
exit 0
