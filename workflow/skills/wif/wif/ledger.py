"""Stream files (markdown + flat quoted frontmatter) and session JSON files."""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path

from . import config

FM_RE = re.compile(r'^([a-z_]+): (.*)$')
STREAM_KEYS = ("id", "scope", "status", "goal", "next", "position", "parent", "backing",
               "issue", "prs", "handoff_doc", "last_session", "created", "updated")
TEMPLATE_BODY = """## Now
<!-- goal / approach / done / failing — keep under 20 lines -->
## Notes
<!-- - [followup|tangent|reminder due=YYYY-MM-DD|landed] YYYY-MM-DD text -->
## Handoff
<!-- paste-ready kickoff prompt, under 25 lines; written at handoff -->
## Dead ends
"""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            v = json.load(fh)
        return default if v is None else v
    except (OSError, ValueError):
        return default


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=1))


def quote(v: str) -> str:
    v = (v or "").replace("\r", " ").replace("\n", " ")
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return re.sub(r'\\(["\\])', r'\1', v[1:-1])
    return v


def first_line(text: str, width: int = 120) -> str:
    for ln in (text or "").replace("\r", "").replace("\0", "").split("\n"):
        if ln.strip():
            return ln.strip()[:width]
    return ""


class Stream:
    """A stream file. `fm` is an ordered dict of frontmatter; `body` the rest."""

    def __init__(self, path: Path, fm: dict[str, str], body: str):
        self.path, self.fm, self.body = path, fm, body

    # ---- IO
    @classmethod
    def load(cls, path: Path) -> "Stream":
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        fm: dict[str, str] = {}
        body = text
        if lines and lines[0] == "---":
            for i, ln in enumerate(lines[1:], start=1):
                if ln == "---":
                    body = "\n".join(lines[i + 1:])
                    break
                m = FM_RE.match(ln)
                if m:
                    fm[m.group(1)] = unquote(m.group(2))
        return cls(path, fm, body)

    @classmethod
    def create(cls, path: Path, sid: str, scope: str, kind: str, bpath: str, status: str = "active") -> "Stream":
        if path.exists():
            return cls.load(path)
        fm = {k: "" for k in STREAM_KEYS}
        fm.update(id=sid, scope=scope, status=status, backing=f"{kind}:{bpath}", created=today(), updated=today())
        s = cls(path, fm, TEMPLATE_BODY)
        s.save()
        return s

    def save(self) -> None:
        head = "\n".join(f"{k}: {quote(v)}" for k, v in self.fm.items())
        body = self.body if self.body.endswith("\n") or not self.body else self.body + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path, f"---\n{head}\n---\n{body}")

    def get(self, key: str) -> str:
        return self.fm.get(key, "")

    def set(self, key: str, value: str, touch: bool = True) -> None:
        self.fm[key] = (value or "").replace("\r", " ").replace("\n", " ")
        if touch and key != "updated":
            self.fm["updated"] = today()

    @property
    def line_count(self) -> int:
        return len(self.fm) + 2 + len(self.body.rstrip("\n").split("\n")) if self.body.strip() else len(self.fm) + 2

    # ---- sections
    def section(self, name: str, keep_comments: bool = False) -> list[str]:
        out, on = [], False
        for ln in self.body.split("\n"):
            if ln == f"## {name}":
                on = True
                continue
            if on and ln.startswith("## "):
                break
            if on and ln and (keep_comments or not ln.startswith("<!--")):
                out.append(ln)
        return out

    def section_append(self, name: str, line: str) -> None:
        line = line.replace("\r", " ").replace("\n", " ")
        lines = self.body.split("\n")
        out, insec, done = [], False, False
        for ln in lines:
            if ln == f"## {name}":
                insec = True
                out.append(ln)
                continue
            if insec and ln.startswith("## "):
                if not done:
                    out.append(line)
                    done = True
                insec = False
            out.append(ln)
        if not done:
            if insec:
                # section was last: append before trailing blank lines
                while out and out[-1] == "":
                    out.pop()
                out.append(line)
                out.append("")
            else:
                out.extend(["", f"## {name}", line, ""])
        self.body = "\n".join(out)

    def section_remove(self, name: str, needle: str) -> str | None:
        lines = self.body.split("\n")
        out, insec, removed = [], False, None
        for ln in lines:
            if ln == f"## {name}":
                insec = True
                out.append(ln)
                continue
            if insec and ln.startswith("## "):
                insec = False
            if insec and removed is None and needle in ln:
                removed = ln
                continue
            out.append(ln)
        if removed is not None:
            self.body = "\n".join(out)
        return removed

    def set_section(self, name: str, lines: list[str]) -> None:
        src = self.body.split("\n")
        out, insec, done = [], False, False
        for ln in src:
            if ln == f"## {name}":
                insec = True
                out.append(ln)
                out.extend(lines)
                done = True
                continue
            if insec and ln.startswith("## "):
                insec = False
            if insec:
                continue
            out.append(ln)
        if not done:
            out.extend(["", f"## {name}", *lines, ""])
        self.body = "\n".join(out)

    def notes(self) -> list[str]:
        return self.section("Notes")


# ---- sessions ---------------------------------------------------------------

def session_file(ledger: Path, sid: str) -> Path:
    return ledger / "sessions" / f"{sid}.json"


def ctx_file(ledger: Path, sid: str) -> Path:
    return ledger / "sessions" / f"{sid}.ctx.json"


def safe_sid(sid: str) -> bool:
    return bool(sid) and "/" not in sid and not sid.startswith(".") and "\\" not in sid


def session_ensure(ledger: Path, sid: str, stream_id: str, scope: str) -> dict:
    f = session_file(ledger, sid)
    s = load_json(f, None)
    if isinstance(s, dict) and "ring" in s:
        return s
    s = {"session_id": sid, "scope": scope, "stream": stream_id, "started": now_iso(),
         "ended": None, "goal": None, "ring": []}
    dump_json(f, s)
    return s


def session_save(ledger: Path, s: dict) -> None:
    dump_json(session_file(ledger, s["session_id"]), s)


def ring_last(s: dict) -> dict:
    ring = s.get("ring") or []
    return ring[-1] if ring and isinstance(ring[-1], dict) else {}


def session_prev_for(ledger: Path, stream: Stream, exclude: str = "") -> dict | None:
    """The previous session of a stream: its recorded last_session unless that is
    <exclude>, else the most recently ended/started session file for the stream."""
    ls = stream.get("last_session")
    if ls and ls != exclude and safe_sid(ls):
        s = load_json(session_file(ledger, ls), None)
        if isinstance(s, dict):
            return s
    best, best_t = None, ""
    sd = ledger / "sessions"
    if not sd.is_dir():
        return None
    for f in sd.glob("*.json"):
        if f.name.endswith(".ctx.json") or f.stem == exclude:
            continue
        s = load_json(f, None)
        if not isinstance(s, dict) or s.get("stream") != stream.get("id"):
            continue
        t = s.get("ended") or s.get("started") or ""
        if t > best_t:
            best, best_t = s, t
    return best
