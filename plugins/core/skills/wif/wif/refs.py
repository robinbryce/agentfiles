"""References: PR numbers (`#1669`, `owner/repo#1669`) and team-keyed Issue ids
(`ENG-2654`) in Stream text, rendered as markdown links only where the text is
about to be rendered as markdown. The Ledger is never rewritten; this is a
display concern of `show` and the hook injections (plan-2610-03).

Mode: `--refs md|plain` beats `WIF_REFS`; the default is plain. No TTY
heuristic: `! wif show` inside Claude Code prints raw and is indistinguishable
from the agent's Bash tool, so the skill opts in with `--refs md` explicitly.
"""
from __future__ import annotations
import os
import re
from pathlib import Path

from . import config, proc

MODES = ("plain", "md")
LINK_RE = re.compile(r"\[[^\]]*\]\([^)\s]*\)")                      # an existing markdown link: never touched
# `(?!…)`: a reference cut by the dashboard's trim (`#16…`, `ENG-2…`) is a
# prefix of some other id — never link it (plan-2610-03 decision 6).
PR_RE = re.compile(r"(?<![\w/\[(])(?:([\w.-]+/[\w.-]+))?#(\d+)\b(?!…)")   # #1669 or owner/repo#1669
GITHUB_ORIGIN_RE = re.compile(r"^(?:git@github\.com:|https?://github\.com/|ssh://git@github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?$")


def mode_from(args: list[str], env=None) -> str:
    env = os.environ if env is None else env
    m = ""
    if "--refs" in args:
        i = args.index("--refs")
        m = args[i + 1] if i + 1 < len(args) else ""
    m = m or env.get("WIF_REFS", "") or "plain"
    if m not in MODES:
        raise ValueError(f"--refs must be md or plain, not '{m}'")
    return m


def slug_of_origin(origin: str | None) -> str | None:
    """`git@github.com:o/r.git` / `https://github.com/o/r` -> `o/r`; other hosts -> None."""
    if not origin:
        return None
    m = GITHUB_ORIGIN_RE.match(origin.strip())
    return m.group(1) if m else None


class Resolver:
    """What one container knows: its cached PRs (number -> url), its GitHub
    origins, and the scope's Linear workspace + team keys."""

    def __init__(self, scope: str, repos: list[dict] | None = None, prs: list[dict] | None = None):
        self.workspace, self.teams = config.linear_for(scope)
        self.prs: dict[int, dict] = {}
        for p in prs or []:
            if isinstance(p, dict) and p.get("url") and str(p.get("number", "")).isdigit():
                self.prs.setdefault(int(p["number"]), p)
        slugs = {slug_of_origin(r.get("origin")) for r in (repos or []) if isinstance(r, dict)}
        slugs.discard(None)
        self.slugs = slugs
        self.single_slug = next(iter(slugs)) if len(slugs) == 1 else None

    @classmethod
    def from_container(cls, scope: str, c: dict | None) -> "Resolver":
        c = c or {}
        return cls(scope, c.get("repos") or [], c.get("prs") or [])

    @classmethod
    def from_disk(cls, scope: str, path: Path | None) -> "Resolver":
        """Hook fallback when the index has no entry: origins read from the
        container's worktrees (no PR cache, so only a single-origin container links)."""
        repos: list[dict] = []
        if path:
            try:
                for e in sorted(Path(path).iterdir()):
                    if e.is_dir() and (e / ".git").exists():
                        rc, rem = proc.git(str(e), "remote", "get-url", "origin", timeout=3)
                        repos.append({"name": e.name, "origin": rem if rc == 0 and rem else None})
            except OSError:
                pass
        return cls(scope, repos, [])

    def pr_url(self, number: int, slug: str | None = None) -> str | None:
        if slug:
            return f"https://github.com/{slug}/pull/{number}"
        p = self.prs.get(number)
        if p:
            return p["url"]
        if self.single_slug:
            return f"https://github.com/{self.single_slug}/pull/{number}"
        return None

    def issue_url(self, ident: str) -> str | None:
        team = ident.split("-", 1)[0]
        if self.workspace and team in self.teams:
            return f"https://linear.app/{self.workspace}/issue/{ident}"
        return None

    def issue_re(self):
        if not self.teams:
            return None
        return re.compile(r"\b(" + "|".join(re.escape(t) for t in self.teams) + r")-(\d{1,6})\b(?!…)")


def _link_segment(seg: str, r: Resolver) -> str:
    def pr(m):
        slug, num = m.group(1), int(m.group(2))
        url = r.pr_url(num, slug)
        return f"[{m.group(0)}]({url})" if url else m.group(0)
    seg = PR_RE.sub(pr, seg)
    ire = r.issue_re()
    if ire:
        def iss(m):
            url = r.issue_url(m.group(0))
            return f"[{m.group(0)}]({url})" if url else m.group(0)
        seg = ire.sub(iss, seg)
    return seg


def linkify(text: str | None, resolver: Resolver | None, mode: str) -> str:
    """Link every Reference in <text> under mode "md"; return it unchanged under
    "plain". Existing markdown links are skipped, so the pass is idempotent."""
    if not text or mode != "md" or resolver is None:
        return text or ""
    out, pos = [], 0
    for m in LINK_RE.finditer(text):
        out.append(_link_segment(text[pos:m.start()], resolver))
        out.append(m.group(0))
        pos = m.end()
    out.append(_link_segment(text[pos:], resolver))
    return "".join(out)
