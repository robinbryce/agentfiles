"""Small CLI verbs: where, adopt, mark, note/tangent/remind, ctx, sessions."""
from __future__ import annotations
import dataclasses
import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import config, paths, scan, tangents
from .ledger import (Stream, ctx_file, load_json, now_iso, ring_last, safe_sid, session_ensure,
                     session_file, session_save, stream_lock, today)


class WifError(Exception):
    pass


def _ctx_for_write(cwd: str | None = None) -> paths.Ctx:
    ctx = paths.resolve(cwd)
    if not ctx.served:
        raise WifError(f"scope {ctx.scope} is not served by account {ctx.account} — nothing recorded")
    if ctx.kind == "none":
        raise WifError("no backing here (not a herdr container, not a git repo)")
    paths.ledger_init(ctx.scope, ctx.config_dir)
    return ctx


def _ctx_for_stream(stream_id: str, scope: str = "") -> paths.Ctx:
    """Address an existing stream by id from any cwd (its backing may be gone)."""
    if not safe_sid(stream_id):
        raise WifError("bad stream id")
    if scope and scope not in paths.known_scopes():
        raise WifError(f"unknown scope '{scope}'")
    ctx = paths.resolve(None, scope or None)
    if not ctx.served:
        raise WifError(f"scope {ctx.scope} is not served by account {ctx.account} — pass --scope")
    ctx = dataclasses.replace(ctx, id=stream_id, stream_file=ctx.ledger / "streams" / f"{stream_id}.md")
    if not ctx.stream_file.exists():
        if ctx.archive_file.exists():
            raise WifError(f"stream {stream_id} is closed (archived)")
        raise WifError(f"no stream {stream_id} in scope {ctx.scope}")
    # The context's backing is the TARGET stream's, not the cwd's: a tangent
    # recorded here must name the target container's repo set, not ours.
    kind, _, bpath = (Stream.load(ctx.stream_file).get("backing") or "").partition(":")
    return dataclasses.replace(ctx, kind=kind or "none", path=Path(bpath) if bpath else None)


def _stream_for_write(ctx: paths.Ctx) -> Stream:
    """Load or (for herdr) create the stream; refuse archived and unadopted repos."""
    if ctx.stream_file.exists():
        return Stream.load(ctx.stream_file)
    if ctx.archive_file.exists():
        raise WifError(f"stream {ctx.id} is closed (archived); re-open with: wif adopt .")
    if ctx.kind != "herdr":
        raise WifError(f"no stream for {ctx.id}; wif adopt . first")
    return Stream.create(ctx.stream_file, ctx.id, ctx.scope, ctx.kind, str(ctx.path))


def _archive(ctx: paths.Ctx, out) -> None:
    ctx.archive_file.parent.mkdir(parents=True, exist_ok=True)
    os.replace(ctx.stream_file, ctx.archive_file)
    print(f"archived → {ctx.archive_file} (hooks stop recording here until wif adopt)", file=out)


# ---- where -------------------------------------------------------------------

def where(args: list[str], out=None) -> int:
    out = out or sys.stdout
    as_json = "--json" in args
    rest = [a for a in args if a != "--json"]
    ctx = paths.resolve(rest[0] if rest else None)
    if as_json:
        print(json.dumps(ctx.as_json()), file=out)
        return 0
    print(f"account: {ctx.account}   scope: {ctx.scope}   served: {'yes' if ctx.served else 'NO'}", file=out)
    print(f"ledger:  {ctx.ledger}", file=out)
    if ctx.kind == "none":
        print("backing: none (not a herdr container, not a git repo)", file=out)
    else:
        print(f"backing: {ctx.kind} {ctx.id}  ({ctx.path})", file=out)
        st = ctx.status() or ("closed" if ctx.archive_file.exists() else "untracked")
        print(f"stream:  {st}  {ctx.stream_file}", file=out)
    return 0


# ---- adopt -------------------------------------------------------------------

def adopt(args: list[str], out=None) -> int:
    out = out or sys.stdout
    target, status, goal, parent, nxt, scope, issue = "", "", "", "", "", "", ""
    it = iter(args)
    for a in it:
        if a == "-s": status = next(it, "")
        elif a == "-g": goal = next(it, "")
        elif a == "-p": parent = next(it, "")
        elif a == "-n": nxt = next(it, "")
        elif a == "--scope": scope = next(it, "")
        elif a == "--issue": issue = _issue_arg(next(it, ""))
        elif a.startswith("-"): raise WifError(f"unknown arg {a}")
        else: target = a
    if status and status not in config.STATUSES:
        raise WifError("status must be " + "|".join(config.STATUSES))
    if scope and scope not in paths.known_scopes():
        raise WifError(f"unknown scope '{scope}'")
    base = paths.resolve(None, scope or None)
    cwd = None
    if target and target != ".":
        root = base.root
        if root and (root / paths.HERDR_DIR / target).is_dir() and "/" not in target:
            cwd = str(root / paths.HERDR_DIR / target)        # a container name wins
        elif Path(target).is_dir():
            cwd = target
        else:
            raise WifError(f"no container '{target}' under {root}/{paths.HERDR_DIR}")
    ctx = paths.resolve(cwd, scope or None)
    if not ctx.served:
        raise WifError(f"scope {ctx.scope} is not served by account {ctx.account} — nothing recorded")
    if ctx.kind == "none":
        raise WifError("no backing here (not a herdr container, not a git repo)")
    paths.ledger_init(ctx.scope, ctx.config_dir)
    # The tangent this container was promoted from: clear it on the stream it was
    # discovered from, and let that stream stand in for -p / -g when they were
    # not given. Exact `as=<task>` match only (a derived name is a fallback,
    # never an authority). Done before this stream's lock is taken, so only one
    # stream file is ever locked at a time. Closing a container is not promotion.
    origin = _clear_tangent(ctx, out) if status != "closed" else None
    if origin and not parent:
        parent = origin["parent"]
    with stream_lock(ctx.stream_file):
        created = False
        if not ctx.stream_file.exists() and ctx.archive_file.exists():
            os.replace(ctx.archive_file, ctx.stream_file)
            print("re-opened from archive", file=out)
        if ctx.stream_file.exists():
            s = Stream.load(ctx.stream_file)
        else:
            s = Stream.create(ctx.stream_file, ctx.id, ctx.scope, ctx.kind, str(ctx.path), status or "active")
            created = True
        if goal: s.set("goal", goal)
        elif origin and not s.get("goal"): s.set("goal", origin["text"])
        if parent: s.set("parent", parent)
        if issue: s.set("issue", issue)
        elif origin and origin.get("issue") and not s.get("issue"): s.set("issue", origin["issue"])
        if nxt: s.set("next", nxt)
        if status:
            s.set("status", status)
        elif not created and s.get("status") == "closed":
            s.set("status", "active")
        if not s.section("Handoff"):
            seed = _handoff_seed(ctx, s, origin, parent)
            if seed:
                s.set_section("Handoff", seed)
                print(f"seeded ## Handoff ({len(seed)} lines; injected by the SessionStart hook)", file=out)
        s.set("updated", today())
        s.save()
        if s.get("status") == "closed":
            _archive(ctx, out)
        else:
            print(str(ctx.stream_file), file=out)
    return 0


def _clear_tangent(ctx: paths.Ctx, out) -> dict | None:
    """Remove the first `[tangent as=<ctx.id>]` note found on any other open stream
    in scope. -> {"parent": <stream id>, "text": <note text>} or None."""
    sd = ctx.ledger / "streams"
    try:
        files = sorted(sd.glob("*.md"))
    except OSError:
        return None
    def is_mine(ln: str) -> bool:
        return (tangents.parse(ln) or {}).get("as") == ctx.id
    for f in files:
        if f == ctx.stream_file:
            continue
        try:                                   # unlocked read first: no lock file for streams that don't match
            if not any(is_mine(ln) for ln in Stream.load(f).notes()):
                continue
        except OSError:
            continue
        with stream_lock(f):                   # re-check under the lock; another writer may have beaten us
            if not f.exists():
                continue
            ps = Stream.load(f)
            hit = ps.section_remove_if("Notes", is_mine)
            if hit is None:
                continue
            ps.set("updated", today()); ps.save()
        p = tangents.parse(hit) or {}
        print(f"cleared tangent on {ps.get('id') or f.stem}: {p.get('text', '')}", file=out)
        return {"parent": ps.get("id") or f.stem, "text": p.get("text", ""), "issue": p.get("issue", "")}
    return None


def _issue_arg(raw: str) -> str:
    v = tangents.issue_id(raw)
    if not v:
        raise WifError(f"--issue '{raw}': need an id like ENG-123 or a Linear issue URL")
    return v


MEMORY_BRIDGE = ("Read {md}/MEMORY.md and the memories it indexes, then re-save what's still "
                 "relevant to this workspace's own memory.")


def _handoff_seed(ctx: paths.Ctx, s: Stream, origin: dict | None, parent: str) -> list[str]:
    """First-session kickoff for a stream born from a tangent or under a parent
    stream: objective, where it came from, the parent's pointers and the
    memory bridge. Empty when neither applies (nothing to say yet)."""
    # The stream whose pointers we carry: the one the tangent was found on, else
    # the -p value when it names a stream. `parent` may also be a plain label
    # (a Linear id); then it is recorded as such and carries no pointers.
    src = origin["parent"] if origin else parent
    pf = (ctx.ledger / "streams" / f"{src}.md") if src and safe_sid(src) else None
    if not origin and not (pf and pf.exists()):
        return []
    lines = [f"objective: {origin['text'] if origin else (s.get('goal') or '-')}"]
    if s.get("issue"):
        lines.append(f"issue: {s.get('issue')}")
    label = "discovered from" if origin else "parent"
    if pf and pf.exists():
        ps = Stream.load(pf)
        bpath = ps.get("backing").split(":", 1)[-1]
        lines.append(f"{label}: {src}" + (f" ({bpath})" if bpath else ""))
        if ps.get("goal"):
            lines.append(f"parent goal: {ps.get('goal')}")
        if ps.get("handoff_doc"):
            lines.append(f"parent handoff: {ps.get('handoff_doc')}")
        if bpath:
            md = ctx.config_dir / "projects" / scan.sanitize(bpath) / "memory"
            if (md / "MEMORY.md").is_file():
                lines.append("memory bridge: " + MEMORY_BRIDGE.format(md=md))
    else:
        lines.append(f"{label}: {src}")
    if parent and parent != src:
        lines.append(f"parent: {parent}")
    lines.append("re-invoke: /core:wif")
    return lines


# ---- mark --------------------------------------------------------------------

def mark(args: list[str], out=None) -> int:
    out = out or sys.stdout
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    goal = intent = pos = nxt = status = done = stream_id = scope = issue = ""
    it = iter(args)
    for a in it:
        if a == "--stream": stream_id = next(it, "")
        elif a == "--scope": scope = next(it, "")
        elif a == "--issue": issue = _issue_arg(next(it, ""))
        elif a == "-g": goal = next(it, "")
        elif a == "-i": intent = next(it, "")
        elif a == "-p": pos = next(it, "")
        elif a == "-n": nxt = next(it, "")
        elif a == "-s": status = next(it, "")
        elif a == "--done": done = next(it, "")
        elif a == "--session": sid = next(it, "")
        else: raise WifError(f"unknown arg {a} (wif help)")
    if sid and not safe_sid(sid):
        raise WifError("bad session id")
    if status and status not in config.STATUSES:
        raise WifError("bad status (" + "|".join(config.STATUSES) + ")")
    if scope and not stream_id:
        raise WifError("--scope needs --stream")
    ctx = _ctx_for_stream(stream_id, scope) if stream_id else _ctx_for_write()
    with stream_lock(ctx.stream_file):
        s = _stream_for_write(ctx)
        if status: s.set("status", status)
        if pos: s.set("position", pos)
        if nxt: s.set("next", nxt)
        if issue: s.set("issue", issue)
        if done: s.section_append("Now", f"- done {today()}: {done}"); s.set("updated", today())
        if status or pos or nxt or done or issue:
            s.save()
    if goal or intent:
        sid = sid or s.get("last_session")
        if not sid:
            raise WifError(f"no session id (pass --session) and no session on record for {ctx.id}")
        sess = session_ensure(ctx.ledger, sid, ctx.id, ctx.scope)
        if goal:
            sess["goal"] = goal
        if intent:
            ring = sess.setdefault("ring", [])
            if ring and isinstance(ring[-1], dict):
                ring[-1]["intent"] = intent; ring[-1]["pinned"] = True
            else:
                ring.append({"t": now_iso(), "prompt": None, "intent": intent, "pinned": True, "outcome": None})
        session_save(ctx.ledger, sess)
    bits = [f"marked {ctx.id}"]
    if status: bits.append(f"status={status}")
    if pos: bits.append(f'position="{pos}"')
    if nxt: bits.append(f'next="{nxt}"')
    if issue: bits.append(f"issue={issue}")
    if goal: bits.append(f'session-goal="{goal}"')
    if intent: bits.append(f'intent="{intent}"')
    print(" ".join(bits), file=out)
    if status == "closed":
        _archive(ctx, out)
    return 0


# ---- note / tangent / remind ---------------------------------------------------

def _due_from(when: str) -> str:
    if when == "landed":
        return "landed"
    if when.startswith("+") and when.endswith("d") and when[1:-1].isdigit():
        try:
            return (dt.date.today() + dt.timedelta(days=int(when[1:-1]))).isoformat()
        except OverflowError:
            raise WifError("remind: that many days is not a date")
    try:
        return dt.date.fromisoformat(when).isoformat()
    except ValueError:
        raise WifError("remind needs <when>: YYYY-MM-DD | +Nd | landed")


def note(args: list[str], kind: str = "followup", out=None) -> int:
    out = out or sys.stdout
    args = list(args)
    # --stream ID [--scope S]: address a stream from any directory (as `mark` does)
    stream_id = scope = ""
    rest, it = [], iter(args)
    for a in it:
        if a == "--stream":
            stream_id = next(it, "")
            if not stream_id or stream_id.startswith("-"):
                raise WifError("--stream needs a stream id")
        elif a == "--scope": scope = next(it, "")
        else: rest.append(a)
    args = rest
    if scope and not stream_id:
        raise WifError("--scope needs --stream")
    def target():
        return _ctx_for_stream(stream_id, scope) if stream_id else _ctx_for_write()
    if args[:1] == ["--done"]:
        needle = args[1] if len(args) > 1 else ""
        if not needle:
            raise WifError("--done needs a substring")
        if args[2:]:
            raise WifError(f"unknown arg {args[2]} (note --done \"<substring>\" [--stream ID [--scope S]])")
        ctx = target()
        with stream_lock(ctx.stream_file):
            s = _stream_for_write(ctx)
            removed = s.section_remove("Notes", needle)
            if removed is None:
                raise WifError(f"no note on {ctx.id} contains '{needle}'")
            s.set("updated", today()); s.save()
        print(f"removed from {ctx.id}: {removed}", file=out)
        return 0
    due = task = for_ = issue = ""
    if kind == "reminder":
        if not args:
            raise WifError("remind needs <when>: YYYY-MM-DD | +Nd | landed")
        due = _due_from(args.pop(0))
    if kind == "tangent":
        rest = []
        it = iter(args)
        for a in it:
            if a == "--as": task = next(it, "")
            elif a == "--for": for_ = next(it, "")
            elif a == "--issue": issue = _issue_arg(next(it, ""))
            else: rest.append(a)
        args = rest
        if task and not tangents.TASK_RE.match(task):
            raise WifError(f"--as '{task}': task name must be lowercase kebab-case (a-z, 0-9, single dashes)")
        if for_ and not task and not issue:
            raise WifError("--for needs --as <task> and/or --issue <id>")
    text = " ".join(args).strip()
    if for_:                                   # re-pin the name / issue of a recorded tangent
        if text:
            raise WifError("--for takes no text; it re-tags the tangent containing <substring>")
        ctx = target()
        with stream_lock(ctx.stream_file):
            s = _stream_for_write(ctx)
            hit = s.section_edit("Notes", for_, lambda ln: _retag_tangent(ln, task, issue),
                                 only=lambda ln: tangents.parse(ln) is not None)    # followups/reminders never match
            if hit is None:
                raise WifError(f"no tangent on {ctx.id} contains '{for_}'")
            s.set("updated", today()); s.save()
        print(f"re-tagged on {ctx.id}: {hit[1]}", file=out)
        p = tangents.parse(hit[1]) or {"text": "", "issue": ""}
        _tangent_tail(ctx, tangents.task_of(p), p["text"], out)
        return 0
    if not text:
        raise WifError("note text required")
    ctx = target()
    if kind == "tangent":
        task = task or tangents.derive(text, issue)
    tag = f"[{kind}{' due=' + due if due else ''}{' as=' + task if task else ''}{' issue=' + issue if issue else ''}]"
    with stream_lock(ctx.stream_file):
        s = _stream_for_write(ctx)
        s.section_append("Notes", f"- {tag} {today()} {text}")
        s.set("updated", today()); s.save()
    print(f"noted on {ctx.id}: {tag} {text}", file=out)
    if kind == "tangent":
        _tangent_tail(ctx, task, text, out)
    return 0


def _retag_tangent(ln: str, task: str, issue: str = "") -> str:
    """Re-pin the task name and/or issue of a tangent line; untouched fields keep
    their value, and a tangent that had no name gets one derived now."""
    p = tangents.parse(ln)
    if p is None:
        return ln
    issue = issue or p["issue"]
    task = task or p["as"] or tangents.derive(p["text"], issue)
    return f"- {tangents.tag(task, issue)} " + (p["date"] + " " if p["date"] else "") + p["text"]


def _tangent_tail(ctx: paths.Ctx, task: str, text: str, out) -> None:
    """What makes this tangent a stream: the container name for `wif adopt`,
    and the `herdr-task` line that creates it with this stream's repo set."""
    exists = None
    if ctx.root and (ctx.root / paths.HERDR_DIR / task).is_dir():
        st = ctx.ledger / "streams" / f"{task}.md"
        exists = {"stream": Stream.load(st).get("status") if st.exists() else None}
    print(f"  task: {task}", file=out)
    for ln in tangents.recommend(task, ctx.id, tangents.container_repos(ctx.path if ctx.kind == "herdr" else None), exists, text):
        print(f"    {ln}", file=out)


# ---- ctx / sessions -----------------------------------------------------------

def ctx_cmd(args: list[str], out=None) -> int:
    out = out or sys.stdout
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    as_json = "--json" in args
    if "--session" in args:
        i = args.index("--session")
        sid = args[i + 1] if i + 1 < len(args) else ""
    ctx = paths.resolve()
    if not sid and ctx.stream_file and ctx.stream_file.exists():
        sid = Stream.load(ctx.stream_file).get("last_session")
    c = load_json(ctx_file(ctx.ledger, sid), None) if safe_sid(sid) else None
    if as_json:
        print(json.dumps(c or {}), file=out)
        return 0
    if not isinstance(c, dict):
        print(f"ctx ?% (no statusline dump for session '{sid or 'unknown'}'; is wif statusline installed?)", file=out)
        return 0
    pct = c.get("used_pct", "?")
    print(f"ctx {pct}% (session {sid[:8]}, as of {c.get('t', '')})", file=out)
    if isinstance(pct, (int, float)) and pct >= config.rotate_pct():
        print(f"ROTATE: at or past {config.rotate_pct()}% — run the handoff protocol, then /clear", file=out)
    return 0


def sessions(args: list[str], out=None) -> int:
    out = out or sys.stdout
    n, want = 8, ""
    it = iter(args)
    for a in it:
        if a == "-n":
            try: n = int(next(it, "8"))
            except ValueError: n = 8
        else: want = a
    ctx = paths.resolve()
    want = want or ctx.id
    sd = ctx.ledger / "sessions"
    try:
        if not sd.is_dir():
            return 0
    except OSError:
        return 0
    def mtime(f: Path) -> float:
        try:
            return f.stat().st_mtime
        except OSError:
            return 0.0
    files = sorted((f for f in sd.glob("*.json") if not f.name.endswith(".ctx.json")), key=mtime, reverse=True)
    shown = 0
    for f in files:
        s = load_json(f, None)
        if not isinstance(s, dict) or (want and s.get("stream") != want):
            continue
        last = ring_last(s)
        print(f"{str(s.get('session_id'))[:8]}  {str(s.get('started'))[:16]}  {s.get('stream')}  goal={s.get('goal') or '-'}  "
              f"last={last.get('intent') or last.get('prompt') or '-'}  ended={s.get('ended') or 'no'}", file=out)
        shown += 1
        if shown >= n:
            break
    return 0
