#!/usr/bin/env python3
"""wif show [--brief] [--changes] [--json] [--all] [--session ID]

Render the dashboard from index.json (run `wif scan` to refresh). Fits in
40 lines by default; --all lifts the caps; --changes prints only containers
whose state changed since the previous --changes call (the /loop tick output);
--brief is the header block only. Read-only except cache/prev-shown.json.
Always exits 0.
"""
import json, os, sys, time, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = {"active": 0, "blocked": 1, "landed": 2, "parked": 3, "closed": 9}
BUDGET = 40

def sh(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""

def load_json(path, default):
    try:
        with open(path) as fh:
            v = json.load(fh)
        return v if v is not None else default
    except Exception:
        return default

def age(ts):
    if not ts: return "?"
    d = int(time.time()) - int(ts)
    return f"{d//86400}d" if d >= 86400 else (f"{d//3600}h" if d >= 3600 else f"{d//60}m")

def trim(s, n):
    s = (s or "-").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"

def note_text(ln):
    return ln.split("] ", 1)[-1] if ln.startswith("- [") else ln

def due_notes(streams, today):
    out = []
    for sid, s in streams.items():
        for ln in s.get("notes") or []:
            if not ln.startswith("- [reminder due="): continue
            due = ln[len("- [reminder due="):].split("]", 1)[0]
            if (due == "landed" and s.get("status") in ("landed", "closed")) or (due != "landed" and due <= today):
                out.append((sid, ln))
    return out

def main():
    a = sys.argv[1:]
    w = load_json_str(sh(["bash", os.path.join(HERE, "wif-where.sh"), "--json", os.getcwd()]))
    if not w:
        print("wif: could not resolve scope (is jq installed?)"); return 0
    if not w.get("served"):
        print(f"wif: scope {w.get('scope')} is not served by account {w.get('account')} — nothing to show"); return 0
    ledger = w["ledger"]; idx_path = os.path.join(ledger, "index.json")
    idx = load_json(idx_path, None)
    if not isinstance(idx, dict) or "containers" not in idx:
        print(f"wif: no usable index for scope {w['scope']} — run `wif scan`"); return 0
    if "--json" in a:
        print(json.dumps(idx)); return 0
    today = datetime.date.today().isoformat()
    cont = {c["task"]: c for c in idx.get("containers", []) if isinstance(c, dict) and "task" in c}
    streams = idx.get("streams") or {}; sess = idx.get("sessions") or {}
    sid = a[a.index("--session") + 1] if "--session" in a and a.index("--session") + 1 < len(a) else os.environ.get("CLAUDE_SESSION_ID", "")

    # ---- header: where am I
    extra = ""
    if not idx.get("prs_fetched"): extra += " · PRs cached/none (wif scan --prs)"
    if idx.get("pr_failures"): extra += f" · gh failed ×{len(idx['pr_failures'])}"
    lines = [f"wif · {w['account']} @ {w['scope']} · scanned {age(idx.get('scanned_at'))} ago{extra}"]
    cur = w.get("id") or ""
    if cur:
        st = streams.get(cur); c = cont.get(cur)
        status = (st or {}).get("status") or ("untracked" if c else ("closed" if os.path.exists(os.path.join(ledger, "archive", cur + ".md")) else "unknown"))
        lines.append(f"▶ {cur}  {status}" + (f"  [{' '.join(c['flags'])}]" if c and c.get("flags") else ""))
        if st:
            lines.append(f"  goal: {trim(st.get('goal'), 70)}")
            lines.append(f"  next: {trim(st.get('next'), 70)}   position: {trim(st.get('position'), 30)}")
        s = sess.get(cur); ctx = ""
        if sid and "/" not in sid:
            cj = load_json(os.path.join(ledger, "sessions", f"{sid}.ctx.json"), {})
            if cj: ctx = f"  ctx {cj.get('used_pct', '?')}%"
        if s:
            lines.append(f"  session: {trim(s.get('goal') or 'goal unset', 50)}   ~ {trim(s.get('last_intent') or s.get('last_prompt'), 50)}{ctx}")
        elif ctx:
            lines.append(f" {ctx}")
    else:
        lines.append(f"▶ (no stream here: {w.get('kind')})")
    dn = due_notes(streams, today)
    if dn:
        lines.append("due:")
        for sid_, ln in dn[:5]:
            lines.append(f"  ! {sid_}: {trim(note_text(ln), 80)}")
    if "--brief" in a:
        print("\n".join(lines)); return 0

    # ---- --changes: tick output
    if "--changes" in a:
        prev_p = os.path.join(ledger, "cache", "prev-shown.json")
        prev = load_json(prev_p, None)
        cur_sig = {c["task"]: [c.get("stream"), c.get("dirty"), c.get("ahead"), c.get("flags"),
                               [p.get("state") for p in (c.get("prs") or []) if isinstance(p, dict)]] for c in cont.values()}
        try:
            os.makedirs(os.path.dirname(prev_p), exist_ok=True)
            json.dump(cur_sig, open(prev_p + ".tmp", "w")); os.replace(prev_p + ".tmp", prev_p)
        except OSError:
            pass
        if prev is None:
            lines.append(f"baseline recorded ({len(cur_sig)} containers); changes show from the next tick")
            print("\n".join(lines)); return 0
        changed = [t for t, v in cur_sig.items() if prev.get(t) != v]
        gone = [t for t in prev if t not in cur_sig]
        if not changed and not gone:
            print("\n".join(lines)); print("no changes"); return 0
        if changed:
            lines.append(f"changed ({len(changed)}):")
            for t in changed[:15]:
                c = cont[t]; lines.append(f"  {trim(t,34):<34} {str(c.get('stream') or 'untracked'):<9} {age(c.get('last_activity_ts')):>4} {' '.join(c.get('flags') or [])}")
            if len(changed) > 15: lines.append(f"  … {len(changed) - 15} more")
        if gone:
            lines.append(f"removed ({len(gone)}): " + ", ".join(gone[:8]) + ("…" if len(gone) > 8 else ""))
        print("\n".join(lines)); return 0

    # ---- build the lower sections first, then give streams the remaining budget
    tail = []
    tang = [(k, ln) for k, s in streams.items() for ln in (s.get("notes") or []) if ln.startswith("- [tangent]")]
    if tang:
        tail.append(f"candidates ({len(tang)}):")
        for k, ln in tang[:4]:
            tail.append(f"  ← {k}: {trim(note_text(ln), 70)}")
        if len(tang) > 4: tail.append(f"  … {len(tang) - 4} more")
    un = sorted([c for c in cont.values() if not c.get("stream")], key=lambda c: -(c.get("last_activity_ts") or 0))
    lim = len(un) if "--all" in a else 8
    if un:
        tail.append(f"untracked containers ({len(un)}; wif adopt <task> [-s parked]):")
        for c in un[:lim]:
            h = c.get("herdr") or {}
            tail.append(f"  {trim(c['task'],34):<34} {age(c.get('last_activity_ts')):>4} {c.get('shape',''):<7} "
                        f"{'dirty ' + str(c.get('dirty')) if c.get('dirty') else '':<9} {('herdr:' + str(h.get('agent_status'))) if h else '':<13} {' '.join(f for f in (c.get('flags') or []) if f != 'dirty')}")
        if len(un) > lim: tail.append(f"  … {len(un) - lim} more (wif show --all)")
    ub = idx.get("unbound_memory") or []
    if ub:
        tail.append(f"unbound memory ({len(ub)}): " + ", ".join(f"{m.get('task')}({m.get('files')})" for m in ub[:6]) + ("…" if len(ub) > 6 else ""))

    rows = []
    for k, s in streams.items():
        if s.get("status") == "closed" or k == cur: continue
        c = cont.get(k, {})
        rows.append((ORDER.get(s.get("status"), 5), -(c.get("last_activity_ts") or 0), k, s, c))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    orphans = idx.get("orphan_streams") or []
    head_n = len(lines) + 2 + (1 if orphans else 0)
    room = len(rows) if "--all" in a else max(4, BUDGET - head_n - len(tail) - 1)
    lines.append(f"streams ({len(rows) + (1 if cur in streams else 0)}):")
    lines.append(f"  {'id':<34} {'status':<8} {'age':>4} {'next':<40} flags")
    for _, _, k, s, c in rows[:room]:
        lines.append(f"  {trim(k,34):<34} {s.get('status',''):<8} {age(c.get('last_activity_ts') or 0):>4} {trim(s.get('next'),40):<40} {' '.join(c.get('flags', []))}")
    if len(rows) > room: lines.append(f"  … {len(rows) - room} more (wif show --all)")
    if orphans:
        lines.append(f"  (backing missing: {', '.join(orphans[:6])}{'…' if len(orphans) > 6 else ''})")
    lines.extend(tail)
    print("\n".join(lines)); return 0

def load_json_str(s):
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"wif show: failed: {e!r} — run `wif scan`"); sys.exit(0)
