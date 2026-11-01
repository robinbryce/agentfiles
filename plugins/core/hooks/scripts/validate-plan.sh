#!/usr/bin/env bash
# validate-plan.sh — Claude Code guardrail for plan doc writes.
#
# Wired by the core plugin's hooks/hooks.json (matcher Write|Edit) for both
# PreToolUse and PostToolUse; the event name on stdin selects the mode.
#
# dox mode. When the file's git repo has a .dox.toml, dox is on PATH and
# DOX_SCHEMA_REPO is set, dox's schema decides what is valid:
#   - PreToolUse passes (the file does not exist yet, and dox has no
#     single-file mode);
#   - PostToolUse runs `dox lint --json` in the repo and reports the
#     findings for the written .md file that are not baselined (exit 2,
#     which hands them to the agent). On a dox config or remote error
#     (exit 2 or 3) or a timeout it says so on stderr and falls back to the
#     name check below for a newly created file.
#
# Built-in mode (no dox). PreToolUse only. Acts on a *new* `.md` file
# directly inside a `plans/` directory or inside a
# `plans/plan-YYMM-NN-<slug>/` directory. Blocks (exit 2) a filename that
# matches NEITHER:
#   - new date-cohort scheme:  plan-YYMM-NN-<slug>.md   (plan-2607-01-foo.md)
#   - legacy absolute scheme:  plan-NNNN-<slug>.md
#   - directory sub-doc:       NN-<slug>.md             (01-foo.md, in a plan dir)
#   - a README.md / handoff.md / decisions.md
# Edits to existing files and anything else (code, deeper dirs) pass.
# The path is never handed to the shell: the whole check runs in Python.
set -euo pipefail

exec python3 -c '
import json, os, re, shutil, subprocess, sys

DOX_TIMEOUT = float(os.environ.get("VALIDATE_PLAN_DOX_TIMEOUT", "20"))

def name_problem(fp):
    """The built-in naming check: a message when fp is a misnamed plan doc."""
    base = os.path.basename(fp)
    parent_dir = os.path.dirname(fp)
    parent = os.path.basename(parent_dir)
    in_plans = parent == "plans"
    in_plan_dir = (re.match(r"^plan-[0-9]{4}-[0-9]{2}-", parent) is not None
                   and os.path.basename(os.path.dirname(parent_dir)) == "plans")
    if not (in_plans or in_plan_dir):
        return None
    if base in ("README.md", "handoff.md", "decisions.md"):
        return None
    if in_plan_dir and re.match(r"^[0-9]{2}-.+\.md$", base):
        return None
    if in_plans and (re.match(r"^plan-[0-9]{4}-[0-9]{2}-[a-z0-9-]+\.md$", base)
                     or re.match(r"^plan-[0-9]{4}-[a-z0-9-]+\.md$", base)):
        return None
    return f"""Blocked: "{base}" does not match the plan naming scheme.
  new:    plan-YYMM-NN-<slug>.md   e.g. plan-2607-01-checkpoint-publisher.md
  subdoc: NN-<slug>.md             (inside a plan-YYMM-NN-<slug>/ directory)
Use  /core:plan-new <slug>  (or new-plan.sh) to allocate the id.
See the core:planning skill.
"""

def dox_repo(fp):
    """The repo top-level when dox governs fp, else None. No subprocess."""
    if os.environ.get("NEW_PLAN_NO_DOX") == "1":
        return None
    if not os.environ.get("DOX_SCHEMA_REPO") or not shutil.which("dox"):
        return None
    d = os.path.dirname(os.path.abspath(fp))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d if os.path.isfile(os.path.join(d, ".dox.toml")) else None
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up

def dox_findings(top, fp):
    """(findings for fp, None) or (None, reason dox could not be used)."""
    try:
        r = subprocess.run(["dox", "lint", "--json"], cwd=top, capture_output=True,
                           text=True, timeout=DOX_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"dox lint timed out after {DOX_TIMEOUT:g}s"
    except OSError as e:
        return None, f"dox lint could not run: {e}"
    if r.returncode not in (0, 1):
        why = (r.stderr.strip().splitlines() or [""])[-1]
        return None, f"dox lint exit {r.returncode}: {why}"
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return None, "dox lint --json gave unreadable output"
    rel = os.path.relpath(os.path.realpath(fp), os.path.realpath(top)).replace(os.sep, "/")
    return [f for f in data.get("findings", [])
            if f.get("path") == rel and not f.get("baselined")], None

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not isinstance(d, dict):
    sys.exit(0)
event = d.get("hook_event_name") or "PreToolUse"
ti = d.get("tool_input")
fp = ti.get("file_path") if isinstance(ti, dict) else None
if not isinstance(fp, str) or not fp.endswith(".md"):
    sys.exit(0)
top = dox_repo(fp)

if event == "PreToolUse":
    if top or os.path.exists(fp):
        sys.exit(0)
    msg = name_problem(fp)
    if msg:
        sys.stderr.write(msg)
        sys.exit(2)
    sys.exit(0)

if event != "PostToolUse" or not top or not os.path.isfile(fp):
    sys.exit(0)
found, err = dox_findings(top, fp)
if err:
    sys.stderr.write(f"validate-plan: {err}; falling back to the built-in name check\n")
    resp = d.get("tool_response")
    created = isinstance(resp, dict) and resp.get("type") == "create"
    msg = name_problem(fp) if created else None
    if msg:
        sys.stderr.write(msg)
        sys.exit(2)
    sys.exit(0)
if not found:
    sys.exit(0)
lines = [f"dox lint: {len(found)} finding(s) in {os.path.relpath(fp, top)}:"]
for f in found:
    lines.append("  %s:%s: [%s] %s" % (f.get("path"), f.get("line"), f.get("check"), f.get("message")))
    if f.get("fix"):
        lines.append("      fix: %s" % f.get("fix"))
lines.append("Fix these, or allocate a new document with `dox new` (/core:plan-new).")
sys.stderr.write("\n".join(lines) + "\n")
sys.exit(2)
'
