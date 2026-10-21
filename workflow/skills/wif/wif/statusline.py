"""Claude Code statusline entrypoint: up to three lines, plus a ctx sidecar for
bindable streams so `wif ctx` knows the real context usage."""
from __future__ import annotations
import json
import os
import sys

from . import config, paths
from .ledger import Stream, ctx_file, dump_json, load_json, now_iso, ring_last, safe_sid, session_file

DIM, RST = "\033[2m", "\033[0m"


def _num(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _col(pct: int) -> str:
    return "\033[31m" if pct >= config.rotate_pct() else ("\033[33m" if pct >= 40 else "\033[32m")


def _trim(s: str, n: int) -> str:
    s = s or "-"
    return s if len(s) <= n else s[: max(n - 1, 1)] + "…"


def render(data: dict, columns: int = 120, write_sidecar: bool = True) -> list[str]:
    sid = str(data.get("session_id") or "")
    ws = data.get("workspace") or {}
    cwd = ws.get("current_dir") or data.get("cwd") or os.getcwd()
    model = (data.get("model") or {}).get("display_name") or "?"
    cw = data.get("context_window") or {}
    pct = max(0, _num(cw.get("used_percentage"), 0))
    try:
        cost = round(float((data.get("cost") or {}).get("total_cost_usd") or 0), 4)
    except (TypeError, ValueError):
        cost = 0.0
    ctx = paths.resolve(cwd)
    acct = f"{ctx.account}/{ctx.scope}" + ("" if ctx.served else "(unserved)")
    rot = config.rotate_pct()
    if not ctx.bindable():
        return [f"{DIM}[{acct}]{RST} {model} · {_col(pct)}{pct}%{RST} ctx · {os.path.basename(cwd.rstrip('/')) or cwd}"]
    if write_sidecar and safe_sid(sid) and (ctx.ledger / "sessions").is_dir():
        dump_json(ctx_file(ctx.ledger, sid), {"used_pct": pct, "model": model, "cost_usd": cost, "t": now_iso(), "stream": ctx.id})
    st = g = n = p = ""
    if ctx.stream_file and ctx.stream_file.exists():
        s = Stream.load(ctx.stream_file)
        st, g, n, p = s.get("status"), s.get("goal"), s.get("next"), s.get("position")
    sg = li = ""
    sess = load_json(session_file(ctx.ledger, sid), None) if safe_sid(sid) else None
    if isinstance(sess, dict):
        sg = sess.get("goal") or ""
        li = ring_last(sess).get("intent") or ""
    w = max(40, columns)
    lines = [f"{DIM}[{acct}]{RST} {ctx.id} · {st or 'untracked'}{' · ' + p if p else ''} · {_col(pct)}{pct}%{RST} ctx · {model}"
             + (" · ROTATE" if pct >= rot else ""),
             f"{DIM}goal:{RST} {_trim(sg or g, w // 2 - 8)}   {DIM}next:{RST} {_trim(n, w // 2 - 8)}"]
    if li:
        lines.append(f"{DIM}~{RST} {_trim(li, w - 4)}")
    return lines


def main(argv: list[str] | None = None) -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        if not isinstance(data, dict):
            data = {}
        cols = _num(os.environ.get("COLUMNS"), 120) or 120
        for ln in render(data, cols):
            print(ln)
    except Exception:
        pass
    return 0
