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

    def pr_entry(self, url: str) -> dict | None:
        """The cached PR whose url is <url> (title/state for a Reference line's note)."""
        for p in self.prs.values():
            if p.get("url") == url:
                return p
        return None

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


# ---- Reference lines (plan-2610-04) ------------------------------------------------
# On the dashboard the item text stays as written; each resolved Reference is
# listed once beneath the item as `    [ref](url) <note>`, derived from the
# UNTRIMMED text so a reference the column trim hides is still listed.

INDENT = "    "


def references(text: str | None, resolver: Resolver | None) -> list[tuple[str, str, str]]:
    """Resolved References in <text>, first-appearance order, de-duplicated by
    url. -> [(label, url, kind)] with kind "pr" | "issue"."""
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    if not text or resolver is None:
        return out
    hits: list[tuple[int, str, str, str]] = []
    for m in PR_RE.finditer(text):
        url = resolver.pr_url(int(m.group(2)), m.group(1))
        if url:
            hits.append((m.start(), m.group(0), url, "pr"))
    ire = resolver.issue_re()
    if ire:
        for m in ire.finditer(text):
            url = resolver.issue_url(m.group(0))
            if url:
                hits.append((m.start(), m.group(0), url, "issue"))
    for _, label, url, kind in sorted(hits):
        if url not in seen:
            seen.add(url); out.append((label, url, kind))
    return out


def reference_lines(texts, resolver: Resolver | None, own_issue: str = "", width: int = 120,
                    indent: str = INDENT) -> list[str]:
    """One line per distinct resolved Reference across <texts>: the link, then a
    note — a PR's cached `STATE · title`, `this stream` for the stream's own
    issue, else nothing. Trimmed so the line fits <width>. Unresolvable
    References get no line (they stay as written in the item text)."""
    if resolver is None:
        return []
    lines: list[str] = []
    seen: set[str] = set()
    for t in texts:
        for label, url, kind in references(t, resolver):
            if url in seen:
                continue
            seen.add(url)
            head = f"{indent}[{label}]({url})"
            note = ""
            if kind == "pr":
                p = resolver.pr_entry(url)
                if p:
                    bits = [str(p.get("state") or "").upper(),
                            "CHANGES_REQUESTED" if p.get("reviewDecision") == "CHANGES_REQUESTED" else "",
                            f"{p['unresolved']} open thread{'s' if p['unresolved'] != 1 else ''}" if p.get("unresolved") else "",
                            (p.get("title") or "").strip()]
                    note = " · ".join(b for b in bits if b)
            elif own_issue and label == own_issue:
                note = "this stream"
            if note:
                room = width - len(head) - 1
                if room < 8:
                    note = ""
                elif len(note) > room:
                    note = note[: room - 1].rstrip() + "…"
            lines.append(head + (" " + note if note else ""))
    return lines
