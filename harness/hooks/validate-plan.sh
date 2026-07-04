#!/usr/bin/env bash
# validate-plan.sh — Claude Code PreToolUse guardrail for plan doc writes.
#
# Wire in ~/.claude/settings.json:
#   "hooks": {
#     "PreToolUse": [
#       { "matcher": "Write|Edit",
#         "hooks": [ { "type": "command",
#                      "command": "bash ~/agentfiles/harness/hooks/validate-plan.sh" } ] }
#     ]
#   }
#
# Reads the tool-call JSON on stdin. Only acts on writes whose path is inside a
# `plans/` directory. Blocks (exit 2) a filename that matches NEITHER:
#   - new date-cohort scheme:  plan-YYYY-NN-<slug>.md   (plan-2607-01-foo.md)
#   - legacy absolute scheme:  plan-NNNN-<slug>.md      (edits to frozen legacy ok)
#   - directory sub-doc:       NN-<slug>.md             (01-foo.md)
#   - a README.md / handoff.md / decisions.md
# Missing frontmatter on a new-scheme file is a soft warning (non-blocking).
set -euo pipefail

read -r -d '' INPUT || true

eval "$(printf '%s' "$INPUT" | python3 -c '
import json, sys, os, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input", {}) or {}
path = ti.get("file_path", "") or ""
content = ti.get("content", "") or ""
# shell-safe exports
print("FP=%s" % json.dumps(path))
print("HAS_FM=%d" % (1 if content.lstrip().startswith("---") else 0))
print("HAS_CONTENT=%d" % (1 if content else 0))
' 2>/dev/null)"

# Not a plans-dir write → nothing to check.
case "$FP" in
  */plans/*) : ;;
  *) exit 0 ;;
esac

base="$(basename "$FP")"

# Accept sub-docs and companion files inside a plan directory.
case "$base" in
  README.md|handoff.md|decisions.md) exit 0 ;;
esac
[[ "$base" =~ ^[0-9]{2}-.+\.md$ ]] && exit 0

# Accept new date-cohort or legacy absolute plan filenames.
if [[ "$base" =~ ^plan-[0-9]{4}-[0-9]{2}-[a-z0-9-]+\.md$ ]]; then
  # new scheme: nudge on missing frontmatter, but don't block
  if [ "${HAS_CONTENT:-0}" = "1" ] && [ "${HAS_FM:-0}" = "0" ]; then
    echo "note: $base is missing YAML frontmatter (id/status/created) — see workflow/rules/planning.md" >&2
  fi
  exit 0
fi
if [[ "$base" =~ ^plan-[0-9]{4}-[a-z0-9-]+\.md$ ]]; then
  exit 0  # legacy plan-NNNN-… — frozen, edits allowed
fi

# Anything else in a plans dir is off-scheme → block.
cat >&2 <<EOF
Blocked: "$base" does not match the plan naming scheme.
  new:    plan-YYYY-NN-<slug>.md   e.g. plan-2607-01-checkpoint-publisher.md
  subdoc: NN-<slug>.md             (inside a plan-YYYY-NN-<slug>/ directory)
Use  /plan-new <slug>  (or new-plan.sh) to allocate the id.
See workflow/rules/planning.md.
EOF
exit 2
