"""Claude Code hook entrypoint. MUST exit 0 and MUST print only JSON (or nothing):
a non-zero exit on UserPromptSubmit blocks the user's prompt."""
from __future__ import annotations
import json
import os
import sys

from . import config, paths
from .ledger import (Stream, first_line, now_iso, ring_last, session_ensure, session_file,
                     session_prev_for, session_save, load_json, safe_sid, stream_lock)


def _ctx_line(stream: Stream, sess: dict, sid: str) -> str:
    st = stream.get("status") or "active"
    g, n, p = stream.get("goal") or "-", stream.get("next") or "-", stream.get("position") or "-"
    sg = sess.get("goal") or ""
    li = ring_last(sess).get("intent") or "-"
    line = (f"[wif] {stream.get('id')} · {st} · goal: {g} · next: {n} · position: {p} · "
            f"session: {sg or 'unset'} · last intent: {li}")
    if not sg:
        line += f' — session goal unset: when this prompt states one, record it with `wif mark -g "<one line>" --session {sid}`'
    else:
        line += f' — if this prompt starts new work, record `wif mark -i "<one line>" --session {sid}`; follow-ups inherit'
    return line


def is_slash_command(first: str) -> bool:
    """`/wif status` is a command; `/Users/x/f.md please` is a path."""
    if not first.startswith("/"):
        return False
    word = first.split(" ", 1)[0]
    return word.count("/") == 1


def handle(event: dict) -> dict | None:
    ev = event.get("hook_event_name") or ""
    sid = str(event.get("session_id") or "")
    cwd = event.get("cwd") or ""
    if not sid or not cwd or not safe_sid(sid):
        return None
    if event.get("agent_id"):            # subagents share the id; only the main agent records
        return None
    ctx = paths.resolve(cwd)
    if not ctx.bindable():
        return None
    # Only the first prompt creates a stream; other events need one to exist.
    if ev != "UserPromptSubmit" and not ctx.stream_file.exists():
        return None
    paths.ledger_init(ctx.scope, ctx.config_dir)
    led = ctx.ledger

    if ev == "UserPromptSubmit":
        sess = session_ensure(led, sid, ctx.id, ctx.scope)
        first = first_line(event.get("prompt_text") or event.get("prompt") or "")
        if first and not is_slash_command(first):
            ring = sess.setdefault("ring", [])
            ring.append({"t": now_iso(), "prompt": first, "intent": None, "pinned": False, "outcome": None})
            del ring[:-config.ring()]
            session_save(led, sess)
        with stream_lock(ctx.stream_file):             # RMW of last_session vs. other sessions' writes
            stream = Stream.create(ctx.stream_file, ctx.id, ctx.scope, ctx.kind, str(ctx.path))
            if stream.get("last_session") != sid:
                stream.set("last_session", sid, touch=False)
                stream.save()
        return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                       "additionalContext": _ctx_line(stream, sess, sid)}}
    stream = Stream.load(ctx.stream_file)

    if ev == "Stop":
        sess = load_json(session_file(led, sid), None)
        if not isinstance(sess, dict):
            return None
        first = first_line(event.get("last_assistant_message") or "")
        last = ring_last(sess)
        if first and last:
            last["outcome"] = first
            session_save(led, sess)
        return None

    if ev == "SessionStart":
        src = event.get("source") or "startup"
        sess = session_ensure(led, sid, ctx.id, ctx.scope)
        if src != "compact" and sess.get("ended"):      # a resumed session is live again
            sess["ended"] = None
            sess.pop("end_reason", None)
            session_save(led, sess)
        prev = None if src == "compact" else session_prev_for(led, stream, exclude=sid)
        body = [f"[wif] session {src} on stream {ctx.id} ({stream.get('status')})",
                f"goal: {stream.get('goal')}", f"next: {stream.get('next')}", f"position: {stream.get('position')}"]
        if prev:
            pl = ring_last(prev)
            body.append(f"previous session: goal={prev.get('goal') or '-'} · last intent="
                        f"{pl.get('intent') or pl.get('prompt') or '-'} · last outcome={pl.get('outcome') or '-'}")
            if src == "clear" and prev.get("goal") and not sess.get("goal"):
                sess["goal"] = prev["goal"]
                session_save(led, sess)
        h = stream.section("Handoff")[:30]
        if h:
            body += ["## Handoff (from stream file)", *h]
        nw = stream.section("Now")[:20]
        if nw:
            body += ["## Now", *nw]
        body.append(f"stream file: {ctx.stream_file} · dashboard: /wif")
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(body)}}

    if ev == "SessionEnd":
        sess = load_json(session_file(led, sid), None)
        if isinstance(sess, dict):
            sess["ended"] = now_iso()
            sess["end_reason"] = event.get("reason") or ""
            session_save(led, sess)
        return None
    return None


def main(argv: list[str] | None = None) -> int:
    try:
        raw = sys.stdin.read()
        if os.environ.get("WIF_HOOK_DEBUG"):
            with open(os.environ["WIF_HOOK_DEBUG"], "a", encoding="utf-8") as fh:
                fh.write(raw.rstrip("\n") + "\n")
        event = json.loads(raw)
        if not isinstance(event, dict):
            return 0
        out = handle(event)
        if out:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    except BaseException:                      # never let a hook fail loudly
        pass
    return 0
