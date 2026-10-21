"""The one seam to the outside world. Tests patch `wif.proc.run`."""
from __future__ import annotations
import os
import subprocess


def run(args: list[str], cwd: str | None = None, timeout: float = 20) -> tuple[int, str]:
    """Return (rc, stdout.strip()). Never raises; failures are rc=1, ''."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def git(repo: str, *args: str, timeout: float = 20) -> tuple[int, str]:
    return run(["git", "-C", repo, *args], timeout=timeout)
