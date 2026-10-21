#!/usr/bin/env bash
# validate-plan.sh — Claude Code PreToolUse guardrail for plan doc writes.
#
# Wired by the core plugin's hooks/hooks.json (matcher Write|Edit).
#
# Reads the tool-call JSON on stdin. Only acts on a *new* `.md` file directly
# inside a `plans/` directory or inside a `plans/plan-YYMM-NN-<slug>/` directory.
# Blocks (exit 2) a filename that matches NEITHER:
#   - new date-cohort scheme:  plan-YYMM-NN-<slug>.md   (plan-2607-01-foo.md)
#   - legacy absolute scheme:  plan-NNNN-<slug>.md
#   - directory sub-doc:       NN-<slug>.md             (01-foo.md, in a plan dir)
#   - a README.md / handoff.md / decisions.md
# Edits to existing files and anything else (code, deeper dirs) pass.
# The path is never handed to the shell: the whole check runs in Python.
set -euo pipefail

exec python3 -c '
import json, os, re, sys

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") if isinstance(d, dict) else None
fp = (ti or {}).get("file_path") if isinstance(ti, dict) else None
if not isinstance(fp, str) or not fp.endswith(".md") or os.path.exists(fp):
    sys.exit(0)

base = os.path.basename(fp)
parent_dir = os.path.dirname(fp)
parent = os.path.basename(parent_dir)
in_plans = parent == "plans"
in_plan_dir = (re.match(r"^plan-[0-9]{4}-[0-9]{2}-", parent) is not None
               and os.path.basename(os.path.dirname(parent_dir)) == "plans")
if not (in_plans or in_plan_dir):
    sys.exit(0)

if base in ("README.md", "handoff.md", "decisions.md"):
    sys.exit(0)
if in_plan_dir and re.match(r"^[0-9]{2}-.+\.md$", base):
    sys.exit(0)
if in_plans and (re.match(r"^plan-[0-9]{4}-[0-9]{2}-[a-z0-9-]+\.md$", base)
                 or re.match(r"^plan-[0-9]{4}-[a-z0-9-]+\.md$", base)):
    sys.exit(0)

sys.stderr.write(f"""Blocked: "{base}" does not match the plan naming scheme.
  new:    plan-YYMM-NN-<slug>.md   e.g. plan-2607-01-checkpoint-publisher.md
  subdoc: NN-<slug>.md             (inside a plan-YYMM-NN-<slug>/ directory)
Use  /core:plan-new <slug>  (or new-plan.sh) to allocate the id.
See the core:planning skill.
""")
sys.exit(2)
'
