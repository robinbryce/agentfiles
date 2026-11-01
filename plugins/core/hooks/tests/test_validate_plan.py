"""validate-plan.sh: the built-in name check and the dox lint mode.

Each test feeds the hook a tool-call event in an isolated HOME with temp git
repos and, for dox mode, a fake `dox` that records its call and prints a
canned `lint --json` report.
Run: python3 -m unittest discover -s plugins/core/hooks/tests
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "validate-plan.sh"

FAKE_DOX = """#!/usr/bin/env bash
{ printf '%s\\n' "$PWD"; printf '%s\\n' "$@"; } > "$FAKE_DOX_LOG"
[ -n "${FAKE_DOX_RC:-}" ] && { echo "dox: no schema" >&2; exit "$FAKE_DOX_RC"; }
cat "$FAKE_DOX_REPORT"
[ -n "${FAKE_DOX_LINT_RC:-}" ] && exit "$FAKE_DOX_LINT_RC"
exit 0
"""


def path_without_dox() -> str:
    return os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                           if p and not os.path.exists(os.path.join(p, "dox")))


def finding(path, check="naming", message="bad", baselined=False, severity="error"):
    return {"check": check, "path": path, "line": 1, "message": message, "fix": "rename it",
            "severity": severity, "baselined": baselined}


class HookCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="validate-plan-test-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        (self.base / "home").mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "dox.log"
        self.report = self.base / "report.json"
        self.env = {
            "HOME": str(self.base / "home"), "PATH": path_without_dox(),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(self.base.parent),
            "FAKE_DOX_LOG": str(self.log), "FAKE_DOX_REPORT": str(self.report),
        }
        self.repo = self.base / "repo"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True,
                       capture_output=True, env=self.env)
        (self.repo / "plans").mkdir()

    def use_dox(self, findings=(), lint_rc=None):
        (self.repo / ".dox.toml").write_text('schema_ref = "v1.0.0"\nnamespace = "repo"\ntypes = ["plan"]\n')
        dox = self.bin / "dox"
        dox.write_text(FAKE_DOX)
        dox.chmod(0o755)
        self.env["PATH"] = f"{self.bin}{os.pathsep}{self.env['PATH']}"
        self.env["DOX_SCHEMA_REPO"] = "example-org/doc-schema"
        self.report.write_text(json.dumps({"findings": list(findings)}))
        if lint_rc is not None:
            self.env["FAKE_DOX_LINT_RC"] = str(lint_rc)

    def hook(self, event, path, tool="Write", response=None, **env):
        payload = {"hook_event_name": event, "tool_name": tool, "tool_input": {"file_path": str(path)}}
        if response is not None:
            payload["tool_response"] = response
        return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), capture_output=True,
                              text=True, env={**self.env, **env})

    def written(self, rel, text="x\n"):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p


class BuiltinMode(HookCase):
    def test_blocks_misnamed_new_plan(self):
        r = self.hook("PreToolUse", self.repo / "plans" / "my-plan.md")
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not match the plan naming scheme", r.stderr)

    def test_event_name_defaults_to_pre(self):
        payload = {"tool_input": {"file_path": str(self.repo / "plans" / "my-plan.md")}}
        r = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), capture_output=True,
                           text=True, env=self.env)
        self.assertEqual(r.returncode, 2)

    def test_passes_good_names_and_existing_files(self):
        for rel in ("plans/plan-2611-01-x.md", "plans/plan-2611-01-x/02-slice.md", "plans/README.md",
                    "docs/notes.md"):
            self.assertEqual(self.hook("PreToolUse", self.repo / rel).returncode, 0, rel)
        self.assertEqual(self.hook("PreToolUse", self.written("plans/legacy.md"), "Edit").returncode, 0)

    def test_post_is_silent_without_dox(self):
        r = self.hook("PostToolUse", self.written("plans/my-plan.md"), response={"type": "create"})
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        self.assertFalse(self.log.exists())


class DoxMode(HookCase):
    def test_pre_defers_to_dox(self):
        self.use_dox()
        r = self.hook("PreToolUse", self.repo / "plans" / "my-plan.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.log.exists(), "PreToolUse must not run dox")

    def test_post_reports_unbaselined_findings_for_the_file(self):
        self.use_dox([finding("plans/my-plan.md", message="name is not an id"),
                      finding("plans/my-plan.md", message="old debt", baselined=True),
                      finding("plans/other.md", message="not this file")], lint_rc=1)
        p = self.written("plans/my-plan.md")
        r = self.hook("PostToolUse", p, response={"type": "create"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("plans/my-plan.md:1: [naming] name is not an id", r.stderr)
        self.assertIn("fix: rename it", r.stderr)
        self.assertNotIn("old debt", r.stderr)
        self.assertNotIn("not this file", r.stderr)
        self.assertEqual(self.log.read_text().splitlines(), [str(self.repo), "lint", "--json"])

    def test_post_clean_file_passes(self):
        self.use_dox([finding("plans/other.md")], lint_rc=1)
        r = self.hook("PostToolUse", self.written("plans/plan-2611-01-x.md"), "Edit")
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_post_any_markdown_in_the_repo(self):
        self.use_dox([finding("docs/adr/x.md", check="frontmatter")], lint_rc=1)
        r = self.hook("PostToolUse", self.written("docs/adr/x.md"), "Edit")
        self.assertEqual(r.returncode, 2)
        self.assertIn("[frontmatter]", r.stderr)

    def test_post_config_error_falls_back_for_new_file(self):
        self.use_dox()
        p = self.written("plans/my-plan.md")
        r = self.hook("PostToolUse", p, response={"type": "create"}, FAKE_DOX_RC="2")
        self.assertEqual(r.returncode, 2)
        self.assertIn("dox lint exit 2: dox: no schema; falling back to the built-in name check", r.stderr)
        self.assertIn("does not match the plan naming scheme", r.stderr)

    def test_post_remote_error_passes_edit_of_existing_file(self):
        self.use_dox()
        r = self.hook("PostToolUse", self.written("plans/my-plan.md"), "Edit",
                      response={"filePath": "x"}, FAKE_DOX_RC="3")
        self.assertEqual(r.returncode, 0)
        self.assertIn("falling back", r.stderr)

    def test_opt_out_restores_builtin_check(self):
        self.use_dox()
        r = self.hook("PreToolUse", self.repo / "plans" / "my-plan.md", NEW_PLAN_NO_DOX="1")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
