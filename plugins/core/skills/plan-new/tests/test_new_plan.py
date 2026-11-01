"""new-plan.sh: dox dispatch and the built-in allocator.

Each test runs the real script in an isolated HOME with temp git repos and a
fake `dox` on PATH that records its argv and working directory.
Run: python3 -m unittest discover -s plugins/core/skills/plan-new/tests
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
NEW_PLAN = SKILLS / "plan-new" / "scripts" / "new-plan.sh"
SAVE_STATUS = SKILLS / "save-status" / "scripts" / "new-plan.sh"

FAKE_DOX = """#!/usr/bin/env bash
{ printf '%s\\n' "$PWD"; printf '%s\\n' "$@"; } > "$FAKE_DOX_LOG"
[ -n "${FAKE_DOX_RC:-}" ] && { echo "fake dox: failing" >&2; exit "$FAKE_DOX_RC"; }
echo "$PWD/$2s/$2-2611-07-$3.md"
"""

DATE = "2026-11-01"


def path_without_dox() -> str:
    """The test runner's PATH minus any directory that holds a real dox."""
    return os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep)
                           if p and not os.path.exists(os.path.join(p, "dox")))


class NewPlanCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="new-plan-test-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "dox.log"
        self.env = {
            "HOME": str(self.home), "PATH": path_without_dox(),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "GIT_CEILING_DIRECTORIES": str(self.base.parent),
            "FAKE_DOX_LOG": str(self.log),
        }

    def install_dox(self, schema_repo: str = "example-org/doc-schema") -> None:
        dox = self.bin / "dox"
        dox.write_text(FAKE_DOX)
        dox.chmod(0o755)
        self.env["PATH"] = f"{self.bin}{os.pathsep}{self.env['PATH']}"
        self.env["DOX_SCHEMA_REPO"] = schema_repo

    def repo(self, name: str = "repo", types: list[str] | None = None) -> Path:
        r = self.base / name
        r.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(r)], check=True,
                       capture_output=True, env=self.env)
        if types is not None:
            listed = ", ".join(f'"{t}"' for t in types)
            (r / ".dox.toml").write_text(f'schema_ref = "v1.0.0"\nnamespace = "{name}"\ntypes = [{listed}]\n')
        return r

    def run_script(self, *args: str, script: Path = NEW_PLAN, cwd: Path | None = None, **env):
        return subprocess.run(["bash", str(script), *args], cwd=cwd or self.base, capture_output=True,
                              text=True, env={**self.env, **env})

    def dox_call(self) -> list[str] | None:
        return self.log.read_text().splitlines() if self.log.exists() else None


class DoxDispatch(NewPlanCase):
    def test_delegates_plan_with_flags(self):
        self.install_dox()
        r = self.repo(types=["plan", "status"])
        out = self.run_script("Checkpoint Publisher", "--dir", "--root", str(r / "plans"),
                              "--date", DATE, "--offline")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), f"{r}/plans/plan-2611-07-checkpoint-publisher.md")
        self.assertEqual(self.dox_call(), [str(r), "new", "plan", "checkpoint-publisher",
                                           "--dir", "--date", DATE, "--offline"])
        self.assertFalse((r / "plans").exists(), "the built-in allocator must not run")

    def test_delegates_status_through_save_status_link(self):
        self.install_dox()
        r = self.repo(types=["plan", "status"])
        out = self.run_script("for-1-thing", "--prefix", "status", "--root", str(r / "status"),
                              script=SAVE_STATUS)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.dox_call(), [str(r), "new", "status", "for-1-thing"])

    def test_repo_from_cwd_without_root(self):
        self.install_dox()
        r = self.repo(types=["plan"])
        (r / "sub").mkdir()
        out = self.run_script("x", cwd=r / "sub")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(self.dox_call()[0], str(r))

    def test_remote_error_falls_back(self):
        self.install_dox()
        r = self.repo(types=["plan"])
        out = self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline",
                              FAKE_DOX_RC="3")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("dox new failed (exit 3)", out.stderr)
        self.assertTrue((r / "plans" / "plan-2611-01-x.md").is_file())

    def test_other_dox_failure_propagates(self):
        self.install_dox()
        r = self.repo(types=["plan"])
        out = self.run_script("x", "--root", str(r / "plans"), FAKE_DOX_RC="1")
        self.assertEqual(out.returncode, 1)
        self.assertFalse((r / "plans").exists())


class BuiltinAllocator(NewPlanCase):
    def assert_builtin(self, out, r: Path, name: str = "plan-2611-01-x.md"):
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIsNone(self.dox_call(), "dox must not be called")
        dest = r / "plans" / name
        self.assertEqual(out.stdout.strip(), str(dest))
        self.assertIn("id: plan-2611-01-x", dest.read_text())

    def test_no_dox_on_path(self):
        r = self.repo(types=["plan"])
        self.env["DOX_SCHEMA_REPO"] = "example-org/doc-schema"
        self.assert_builtin(self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline"), r)

    def test_no_schema_repo(self):
        self.install_dox()
        del self.env["DOX_SCHEMA_REPO"]
        r = self.repo(types=["plan"])
        self.assert_builtin(self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline"), r)

    def test_no_dox_toml(self):
        self.install_dox()
        r = self.repo()
        self.assert_builtin(self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline"), r)

    def test_prefix_not_in_types(self):
        self.install_dox()
        r = self.repo(types=["status"])
        self.assert_builtin(self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline"), r)

    def test_opt_out(self):
        self.install_dox()
        r = self.repo(types=["plan"])
        self.assert_builtin(self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline",
                                            NEW_PLAN_NO_DOX="1"), r)

    def test_next_ordinal_in_cohort(self):
        r = self.repo()
        (r / "plans").mkdir()
        (r / "plans" / "plan-2611-04-old.md").write_text("x")
        (r / "plans" / "plan-2610-09-older.md").write_text("x")
        out = self.run_script("x", "--root", str(r / "plans"), "--date", DATE, "--offline")
        self.assertEqual(out.stdout.strip(), str(r / "plans" / "plan-2611-05-x.md"))


if __name__ == "__main__":
    unittest.main()
