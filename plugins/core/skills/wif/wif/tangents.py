"""A tangent's task name: the herdr container (and so the stream id) it would
become. Pinned with `wif tangent --as <task>`; derived from the text otherwise.
Read-only helpers shared by `wif tangent` and `wif show`."""
from __future__ import annotations
import os
import re
import unicodedata
from pathlib import Path

TASK_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")          # herdr-task's rule (branch == task name)
ISSUE_RE = re.compile(r"\b([A-Z]{2,6})-(\d{2,6})\b")        # ENG-2486, ARC-014 → name prefix
TANGENT_RE = re.compile(r"^- \[tangent(?: as=([^\]\s]+))?\] (?:(\d{4}-\d{2}-\d{2}) )?(.*)$")
STOP = set("""a an the to of for and or but in on at by with from into as is are be been was were it its this that
these those we i you they our your my me us please could should would can will do does make let also then than
there here own new just some any all more very so if not no yes which what who how when where why about over
under against via per pr prs stream streams issue task work thing things create include""".split())
MAX_WORDS, MAX_LEN = 4, 40


def derive(text: str) -> str:
    """Lowercase kebab name: `<issue>-` prefix when the text names one, then the
    first content words (stopwords dropped), at most 4 words / 40 chars."""
    raw = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    out: list[str] = []
    m = ISSUE_RE.search(raw)
    if m:
        out.append(f"{m.group(1).lower()}-{m.group(2)}")
        raw = raw[: m.start()] + " " + raw[m.end():]
    words = [w for w in re.split(r"[^a-z0-9]+", raw.lower()) if w and w not in STOP]
    n = 0
    for w in words:
        if n >= MAX_WORDS or len("-".join(out + [w])) > MAX_LEN:
            break
        out.append(w); n += 1
    return "-".join(out) or "tangent"


def parse(line: str) -> dict | None:
    """`- [tangent as=x] 2026-10-22 text` -> {"as", "date", "text"}; None for other notes."""
    m = TANGENT_RE.match(line)
    if not m:
        return None
    text = m.group(3) or ""
    return {"as": m.group(1) or "", "date": m.group(2) or "", "text": text}


def task_of(parsed: dict) -> str:
    return parsed.get("as") or derive(parsed.get("text", ""))


def last(streams: dict, cur: str = "") -> tuple[str, dict] | None:
    """The most recently recorded tangent across streams (from index.json's
    per-stream `notes`): newest date wins, the current stream breaks ties,
    then file order. -> (stream id, parsed) or None."""
    best, best_key = None, None
    for sid, s in streams.items():
        for i, ln in enumerate(s.get("notes") or []):
            p = parse(ln)
            if p is None:
                continue
            key = (p["date"], 1 if sid == cur else 0, i)
            if best_key is None or key > best_key:
                best, best_key = (sid, p), key
    return best


def collection_for(repos: list[str]) -> str | None:
    """The `HERDR_REPOS_<NAME>` collection whose repo set equals <repos>, as the
    token herdr-task takes (`oracle` for HERDR_REPOS_ORACLE); shortest wins."""
    want = set(repos)
    if not want:
        return None
    hits = [k[len("HERDR_REPOS_"):].lower().replace("_", "-")
            for k, v in os.environ.items() if k.startswith("HERDR_REPOS_") and set(v.split()) == want]
    return min(hits, key=len) if hits else None


def container_repos(path: Path | None) -> list[str]:
    """Repo names in a container, from disk (worktree dirs carry a `.git` entry)."""
    if not path:
        return []
    try:
        return sorted(e.name for e in Path(path).iterdir() if e.is_dir() and (e / ".git").exists())
    except OSError:
        return []


def shell_quote(text: str) -> str:
    """Single-quote <text> for a copy-pasteable shell line. Single quotes leave
    `$`, backticks, `"` and `!` (interactive history expansion) alone; an
    embedded single quote becomes the usual '\\'' splice."""
    return "'" + (text or "").replace("'", "'\\''") + "'"


def recommend(task: str, parent: str, parent_repos: list[str], container: dict | None, text: str = "") -> list[str]:
    """Dashboard / command tail for one tangent: the ONE command that makes it a
    stream. `wif adopt <task>` clears the `[tangent as=<task>]` note on the
    stream it was discovered from and inherits that stream as parent, so no
    `wif note --done` step is needed. <container> is the index entry for a
    container named <task>, if one exists."""
    if container and container.get("stream"):
        return [f"wif adopt {task}   (already a stream ({container['stream']}); re-adopting clears this note)"]
    if container:
        return [f"wif adopt {task}   (container exists, untracked)"]
    coll = collection_for(parent_repos)
    repos = coll or (" ".join(parent_repos) if parent_repos else "<repo>...")
    goal = f" -g {shell_quote(goal_text(text))}" if text else ""
    return [f"herdr-task {task} {repos} && wif adopt {task}{goal}"]


GOAL_MAX = 72


def goal_text(text: str, limit: int = GOAL_MAX) -> str:
    """The tangent text as a one-line goal: cut at a word boundary under <limit>
    chars, with no ellipsis, so the printed command stays valid shell."""
    t = " ".join((text or "").split())
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0] if " " in t[:limit] else t[:limit]
    return cut.rstrip(" ,;:-")
