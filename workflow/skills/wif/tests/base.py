"""Shared fixture: an isolated HOME + CLAUDE_CONFIG_DIR in a TemporaryDirectory,
a fully patched environment, and helpers that build real git repos/worktrees.
Nothing here touches the real ~/.claude* directories."""
from __future__ import annotations
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERDR = ".worktrees-herdr"


class WifCase(unittest.TestCase):
    account = "justgames"            # which config dir name to use

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wif-test-")
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()          # macOS: /var -> /private/var
        self.home = self.base / "home"
        self.cfg = self.home / f".claude-{self.account}"
        self.root = self.home / ("Dev/justgames/code" if self.account == "justgames" else "Dev/personal")
        self.cont_root = self.root / HERDR
        for d in (self.home, self.cfg, self.cont_root):
            d.mkdir(parents=True, exist_ok=True)
        env = {"HOME": str(self.home), "CLAUDE_CONFIG_DIR": str(self.cfg), "PATH": os.environ.get("PATH", ""),
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
               "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "TMPDIR": str(self.base / "tmp")}
        (self.base / "tmp").mkdir(exist_ok=True)
        p = mock.patch.dict(os.environ, env, clear=True)
        p.start()
        self.addCleanup(p.stop)

    # ---- helpers
    @property
    def ledger(self) -> Path:
        return self.cfg / "wif" / ("justgames" if self.account == "justgames" else "personal")

    def git(self, repo: Path, *args: str) -> str:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def git_repo(self, path: Path, commits: int = 1, branch: str = "main") -> Path:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", "-b", branch, str(path)], check=True, capture_output=True)
        for i in range(commits):
            self.git(path, "commit", "-q", "--allow-empty", "-m", f"c{i}")
        return path

    def with_remote(self, repo: Path, push: bool = True) -> Path:
        bare = self.base / "remotes" / (repo.name + ".git")
        bare.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True, capture_output=True)
        self.git(repo, "remote", "add", "origin", str(bare))
        if push:
            self.git(repo, "push", "-q", "-u", "origin", "HEAD")
        return bare

    def container(self, name: str, repos=("repo-a",), direct: bool = False) -> Path:
        c = self.cont_root / name
        if direct:
            return self.git_repo(c)
        c.mkdir(parents=True, exist_ok=True)
        for r in repos:
            self.git_repo(c / r)
        return c

    def memory_dir(self, key: str, files: int = 1) -> Path:
        san = str(self.root).replace("/", "-").replace(".", "-")
        md = self.cfg / "projects" / f"{san}--worktrees-herdr-{key}" / "memory"
        md.mkdir(parents=True, exist_ok=True)
        for i in range(files):
            (md / f"m{i}.md").write_text("x")
        return md

    @staticmethod
    def capture(fn, *args, **kw):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = fn(*args, **kw)
        return rc, out.getvalue(), err.getvalue()

    @staticmethod
    def feed(fn, payload, env_extra=None):
        """Run a stdin-driven main() with payload (dict or str) on stdin."""
        text = payload if isinstance(payload, str) else json.dumps(payload)
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(text)), contextlib.redirect_stdout(out):
            with mock.patch.dict(os.environ, env_extra or {}):
                rc = fn([])
        return rc, out.getvalue()
