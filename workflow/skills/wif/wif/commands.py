"""Small CLI verbs: where, adopt, mark, note/tangent/remind, ctx, sessions."""
from __future__ import annotations
import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import config, paths
from .ledger import (Stream, ctx_file, load_json, now_iso, ring_last, safe_sid, session_ensure,
                     session_file, session_save, today)


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
    target, status, goal, parent, nxt, scope = "", "", "", "", "", ""
    it = iter(args)
    for a in it:
        if a == "-s": status = next(it, "")
        elif a == "-g": goal = next(it, "")
        elif a == "-p": parent = next(it, "")
        elif a == "-n": nxt = next(it, "")
        elif a == "--scope": scope = next(it, "")
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
        if Path(target).is_dir():
            cwd = target
        elif root and (root / paths.HERDR_DIR / target).is_dir():
            cwd = str(root / paths.HERDR_DIR / target)
        else:
            raise WifError(f"no container '{target}' under {root}/{paths.HERDR_DIR}")
    ctx = paths.resolve(cwd, scope or None)
    if not ctx.served:
        raise WifError(f"scope {ctx.scope} is not served by account {ctx.account} — nothing recorded")
    if ctx.kind == "none":
        raise WifError("no backing here (not a herdr container, not a git repo)")
    paths.ledger_init(ctx.scope, ctx.config_dir)
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
    if parent: s.set("parent", parent)
    if nxt: s.set("next", nxt)
    if status:
        s.set("status", status)
    elif not created and s.get("status") == "closed":
        s.set("status", "active")
    s.set("updated", today())
    s.save()
    if s.get("status") == "closed":
        _archive(ctx, out)
    else:
        print(str(ctx.stream_file), file=out)
    return 0


# ---- mark --------------------------------------------------------------------

def mark(args: list[str], out=None) -> int:
    out = out or sys.stdout
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    goal = intent = pos = nxt = status = done = ""
    it = iter(args)
    for a in it:
        if a == "-g": goal = next(it, "")
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
    ctx = _ctx_for_write()
    s = _stream_for_write(ctx)
    if status: s.set("status", status)
    if pos: s.set("position", pos)
    if nxt: s.set("next", nxt)
    if done: s.section_append("Now", f"- done {today()}: {done}"); s.set("updated", today())
    if status or pos or nxt or done:
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
        return (dt.date.today() + dt.timedelta(days=int(when[1:-1]))).isoformat()
    try:
        return dt.date.fromisoformat(when).isoformat()
    except ValueError:
        raise WifError("remind needs <when>: YYYY-MM-DD | +Nd | landed")


def note(args: list[str], kind: str = "followup", out=None) -> int:
    out = out or sys.stdout
    args = list(args)
    if args[:1] == ["--done"]:
        needle = args[1] if len(args) > 1 else ""
        if not needle:
            raise WifError("--done needs a substring")
        ctx = _ctx_for_write()
        s = _stream_for_write(ctx)
        removed = s.section_remove("Notes", needle)
        if removed is None:
            raise WifError(f"no note on {ctx.id} contains '{needle}'")
        s.set("updated", today()); s.save()
        print(f"removed from {ctx.id}: {removed}", file=out)
        return 0
    due = ""
    if kind == "reminder":
        if not args:
            raise WifError("remind needs <when>: YYYY-MM-DD | +Nd | landed")
        due = _due_from(args.pop(0))
    text = " ".join(args).strip()
    if not text:
        raise WifError("note text required")
    ctx = _ctx_for_write()
    s = _stream_for_write(ctx)
    tag = f"[{kind}{' due=' + due if due else ''}]"
    s.section_append("Notes", f"- {tag} {today()} {text}")
    s.set("updated", today()); s.save()
    print(f"noted on {ctx.id}: {tag} {text}", file=out)
    return 0


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
    if not sd.is_dir():
        return 0
    files = sorted((f for f in sd.glob("*.json") if not f.name.endswith(".ctx.json")),
                   key=lambda f: f.stat().st_mtime, reverse=True)
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
