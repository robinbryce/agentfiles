"""`wif show`: render the dashboard from index.json. Read-only except the
cache/prev-shown.json used by --changes. Always exits 0."""
from __future__ import annotations
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

from . import config, paths, refs, tangents
from .ledger import Stream, dump_json, load_json

ORDER = {"active": 0, "blocked": 1, "landed": 2, "parked": 3, "closed": 9}


def age(ts, now: float | None = None) -> str:
    if not ts:
        return "?"
    d = int((now or time.time()) - int(ts))
    return f"{d // 86400}d" if d >= 86400 else (f"{d // 3600}h" if d >= 3600 else f"{d // 60}m")


def trim(s, n: int) -> str:
    s = (s or "-").replace("\n", " ")
    return s if len(s) <= n else s[: max(n - 1, 1)] + "…"


def mine(text: str | None) -> str:
    """`next` as the dashboard shows it: a leading `<owner>:` (the item is the
    reader's own) is dropped — the reader knows who they are and the column is
    narrow. Display only; the Ledger keeps the text as written."""
    t = (text or "").strip()
    owner = config.owner().strip()
    if not owner:
        return t
    pfx = owner.lower() + ":"
    return t[len(pfx):].lstrip() if t.lower().startswith(pfx) else t


def note_text(ln: str) -> str:
    return ln.split("] ", 1)[-1] if ln.startswith("- [") else ln


def due_notes(streams: dict, today: str) -> list[tuple[str, str]]:
    out = []
    for sid, s in streams.items():
        for ln in s.get("notes") or []:
            if not ln.startswith("- [reminder due="):
                continue
            due = ln[len("- [reminder due="):].split("]", 1)[0]
            if (due == "landed" and s.get("status") in ("landed", "closed")) or (due != "landed" and due <= today):
                out.append((sid, ln))
    return out


def last_tangent_lines(streams: dict, cont: dict, cur: str) -> list[str]:
    """`last → task: <name>` for the newest tangent, then the command(s) that
    make it a stream: `wif adopt <name>` once a container exists, else the
    `herdr-task` line first (repo set of the stream it was discovered from)."""
    hit = tangents.last(streams, cur)
    if not hit:
        return []
    parent, p = hit
    task = tangents.task_of(p)
    repos = [r.get("name") for r in (cont.get(parent) or {}).get("repos") or [] if isinstance(r, dict) and r.get("name")]
    rec = tangents.recommend(task, parent, repos, cont.get(task), p.get("text", ""))
    out = [f"  last → task: {task}" + (f" · issue {p['issue']}" if p.get("issue") else "")
           + ("" if p.get("as") else " (derived; pin with wif tangent --as <task> --for \"<substring>\")")]
    out.extend(f"    {ln}" for ln in rec)          # a command is never trimmed: cut text is not pasteable
    return out


def render(ctx: paths.Ctx, idx: dict, args: list[str], sid: str = "", now: float | None = None,
           today: str | None = None) -> list[str]:
    now = now or time.time()
    today = today or dt.date.today().isoformat()
    budget = config.budget_lines()
    cont = {c["task"]: c for c in idx.get("containers", []) if isinstance(c, dict) and "task" in c}
    streams = idx.get("streams") or {}; sess = idx.get("sessions") or {}
    mode = refs.mode_from(args)
    resolvers: dict[str, refs.Resolver] = {}
    def R(task: str, texts, own_issue: str = "") -> list[str]:
        """Reference lines for one item (md only): the item text stays as written;
        every resolved Reference in the UNTRIMMED <texts> is listed beneath it."""
        if mode != "md":
            return []
        if task not in resolvers:
            resolvers[task] = refs.Resolver.from_container(ctx.scope, cont.get(task))
        return refs.reference_lines(texts, resolvers[task], own_issue)
    extra = ""
    if not idx.get("prs_fetched"):
        extra += " · PRs cached/none (wif scan --prs)"
    if idx.get("pr_failures"):
        extra += f" · gh failed ×{len(idx['pr_failures'])}"
    lines = [f"wif · {ctx.account} @ {ctx.scope} · scanned {age(idx.get('scanned_at'), now)} ago{extra}"]
    cur = ctx.id or ""
    if cur:
        st = streams.get(cur); c = cont.get(cur)
        status = (st or {}).get("status") or ("closed" if ctx.archive_file.exists() else ("untracked" if c else "unknown"))
        iss = f"  · issue {st['issue']}" if st and st.get("issue") and mode != "md" else ""   # md: a Reference line instead
        lines.append(f"▶ {cur}  {status}" + (f"  [{' '.join(c['flags'])}]" if c and c.get("flags") else "") + iss)
        if st:
            lines.append(f"  goal: {trim(st.get('goal'), 70)}")
            lines.append(f"  next: {trim(mine(st.get('next')), 70)}   position: {trim(st.get('position'), 30)}")
            lines.extend(R(cur, [st.get("goal"), st.get("next"), st.get("position"), st.get("issue")], st.get("issue") or ""))
        s = sess.get(cur); cx = ""
        if sid and "/" not in sid:
            cj = load_json(ctx.ledger / "sessions" / f"{sid}.ctx.json", {})
            if cj:
                cx = f"  ctx {cj.get('used_pct', '?')}%"
        if s:
            lines.append(f"  session: {trim(s.get('goal') or 'goal unset', 50)}   ~ {trim(s.get('last_intent') or s.get('last_prompt'), 50)}{cx}")
        elif cx:
            lines.append(f" {cx}")
    else:
        lines.append(f"▶ (no stream here: {ctx.kind})")
    dn = due_notes(streams, today)
    if dn:
        lines.append("due:")
        for sid_, ln in dn[:5]:
            lines.append(f"  ! {sid_}: {trim(note_text(ln), 80)}")
            lines.extend(R(sid_, [note_text(ln)], (streams.get(sid_) or {}).get("issue") or ""))
    if "--brief" in args:
        return lines

    if "--changes" in args:
        prev_p = ctx.ledger / "cache" / "prev-shown.json"
        prev = load_json(prev_p, None)
        cur_sig = {t: [c.get("stream"), c.get("dirty"), c.get("ahead"), c.get("flags"),
                       [[p.get("state"), p.get("reviewDecision"), p.get("unresolved"), p.get("lastReviewAt")]
                        for p in (c.get("prs") or []) if isinstance(p, dict)]] for t, c in cont.items()}
        try:
            dump_json(prev_p, cur_sig)
        except OSError:
            pass
        if not isinstance(prev, dict):
            lines.append(f"baseline recorded ({len(cur_sig)} containers); changes show from the next tick")
            return lines
        changed = [t for t, v in cur_sig.items() if prev.get(t) != v]
        gone = [t for t in prev if t not in cur_sig]
        if not changed and not gone:
            lines.append("no changes")
            return lines
        if changed:
            lines.append(f"changed ({len(changed)}):")
            for t in changed[:15]:
                c = cont[t]
                lines.append(f"  {trim(t, 34):<34} {str(c.get('stream') or 'untracked'):<9} {age(c.get('last_activity_ts'), now):>4} {' '.join(c.get('flags') or [])}")
            if len(changed) > 15:
                lines.append(f"  … {len(changed) - 15} more")
        if gone:
            lines.append(f"removed ({len(gone)}): " + ", ".join(gone[:8]) + ("…" if len(gone) > 8 else ""))
        return lines

    tail: list[str] = []
    tang = [(k, ln) for k, s in streams.items() for ln in (s.get("notes") or []) if tangents.parse(ln)]
    if tang:
        tail.append(f"candidates ({len(tang)}):")
        for k, ln in tang[:4]:
            iss = (tangents.parse(ln) or {}).get("issue", "")
            tail.append(f"  ← {k}: {('[' + iss + '] ') if iss else ''}{trim(note_text(ln), 70)}")
            tail.extend(R(k, [note_text(ln), iss], (streams.get(k) or {}).get("issue") or ""))
        if len(tang) > 4:
            tail.append(f"  … {len(tang) - 4} more")
        tail.extend(last_tangent_lines(streams, cont, cur))
    un = sorted([c for c in cont.values() if not c.get("stream")], key=lambda c: -(c.get("last_activity_ts") or 0))
    lim = len(un) if "--all" in args else 8
    if un:
        tail.append(f"untracked containers ({len(un)}; wif adopt <task> [-s parked]):")
        for c in un[:lim]:
            h = c.get("herdr") or {}
            tail.append(f"  {trim(c['task'], 34):<34} {age(c.get('last_activity_ts'), now):>4} {c.get('shape', ''):<7} "
                        f"{'dirty ' + str(c.get('dirty')) if c.get('dirty') else '':<9} {('herdr:' + str(h.get('agent_status'))) if h else '':<13} "
                        f"{' '.join(f for f in (c.get('flags') or []) if f != 'dirty')}")
        if len(un) > lim:
            tail.append(f"  … {len(un) - lim} more (wif show --all)")
    ub = idx.get("unbound_memory") or []
    if ub:
        tail.append(f"unbound memory ({len(ub)}): " + ", ".join(f"{m.get('task')}({m.get('files')})" for m in ub[:6]) + ("…" if len(ub) > 6 else ""))

    rows = []
    for k, s in streams.items():
        if s.get("status") == "closed" or k == cur:
            continue
        c = cont.get(k, {})
        rows.append((ORDER.get(s.get("status"), 5), -(c.get("last_activity_ts") or 0), k, s, c))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    orphans = idx.get("orphan_streams") or []
    head_n = len(lines) + 2 + (1 if orphans else 0)
    room = max(4, budget - head_n - len(tail) - 1)          # lines, not rows: Reference lines count (plan-2610-04 D5)
    lines.append(f"streams ({len(rows) + (1 if cur in streams else 0)}):")
    lines.append(f"  {'id':<34} {'status':<8} {'age':>4} {'next':<40} flags")
    shown, used = 0, 0
    for _, _, k, s, c in rows:
        row = [f"  {trim(k, 34):<34} {s.get('status', ''):<8} {age(c.get('last_activity_ts') or 0, now):>4} {trim(mine(s.get('next')), 40):<40} {' '.join(c.get('flags', []))}"]
        row.extend(R(k, [s.get("next"), s.get("issue")], s.get("issue") or ""))
        if "--all" not in args and shown >= 1 and used + len(row) > room:
            break
        lines.extend(row); shown += 1; used += len(row)
    if len(rows) > shown:
        lines.append(f"  … {len(rows) - shown} more (wif show --all)")
    if orphans:
        lines.append(f"  (backing missing: {', '.join(orphans[:6])}{'…' if len(orphans) > 6 else ''})")
    lines.extend(tail)
    return lines


def main(args: list[str], out=None) -> int:
    out = out or sys.stdout
    try:
        ctx = paths.resolve()
        if not ctx.served:
            print(f"wif: scope {ctx.scope} is not served by account {ctx.account} — nothing to show", file=out); return 0
        idx = load_json(ctx.ledger / "index.json", None)
        if not isinstance(idx, dict) or "containers" not in idx:
            print(f"wif: no usable index for scope {ctx.scope} — run `wif scan`", file=out); return 0
        if "--json" in args:
            print(json.dumps(idx), file=out); return 0
        try:
            refs.mode_from(args)
        except ValueError as e:
            print(f"wif show: {e}", file=out); return 2
        sid = args[args.index("--session") + 1] if "--session" in args and args.index("--session") + 1 < len(args) else os.environ.get("CLAUDE_SESSION_ID", "")
        print("\n".join(render(ctx, idx, args, sid)), file=out)
    except Exception as e:
        print(f"wif show: failed: {e!r} — run `wif scan`", file=out)
    return 0


def ls_rows(ctx: paths.Ctx, idx: dict, archived: bool = False) -> list[dict]:
    """One row per container or stream id: status, goal, where it lives on disk."""
    streams = idx.get("streams") or {}
    rows: dict[str, dict] = {}
    for c in idx.get("containers") or []:
        s = streams.get(c["task"]) or {}
        rows[c["task"]] = {"id": c["task"], "status": c.get("stream") or "untracked", "goal": s.get("goal", ""),
                           "path": c.get("path", ""), "backing": "present"}
    for k, s in streams.items():
        if k not in rows:
            rows[k] = {"id": k, "status": s.get("status", ""), "goal": s.get("goal", ""),
                       "path": (s.get("backing") or "").partition(":")[2], "backing": "missing"}
    if archived:
        for f in sorted((ctx.ledger / "archive").glob("*.md")):
            if f.stem not in rows:
                s = Stream.load(f)
                rows[f.stem] = {"id": f.stem, "status": "closed", "goal": s.get("goal"),
                                "path": (s.get("backing") or "").partition(":")[2], "backing": "archived"}
    return sorted(rows.values(), key=lambda r: (ORDER.get(r["status"], 8 if r["status"] == "untracked" else 5), r["id"]))


def ls(args: list[str], out=None) -> int:
    """`wif ls [--archived] [--json]`: flat list of every stream and container in scope."""
    out = out or sys.stdout
    ctx = paths.resolve()
    if not ctx.served:
        print(f"wif: scope {ctx.scope} is not served by account {ctx.account} — nothing to list", file=out); return 0
    idx = load_json(ctx.ledger / "index.json", None)
    if not isinstance(idx, dict) or "containers" not in idx:
        print(f"wif: no usable index for scope {ctx.scope} — run `wif scan`", file=out); return 0
    rows = ls_rows(ctx, idx, "--archived" in args)
    if "--json" in args:
        print(json.dumps(rows), file=out); return 0
    root = str(ctx.root or "")
    print(f"{'id':<34} {'status':<9} {'backing':<8} {'path':<44} goal", file=out)
    for r in rows:
        path = r["path"]
        if root and path.startswith(root + "/"):
            path = path[len(root) + 1:]
        print(f"{trim(r['id'], 34):<34} {r['status']:<9} {r['backing']:<8} {trim(path, 44):<44} {trim(r['goal'], 60)}", file=out)
    return 0
