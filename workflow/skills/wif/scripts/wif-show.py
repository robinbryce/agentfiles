#!/usr/bin/env python3
"""wif show [--brief] [--changes] [--json] [--all] [--session ID]

Render the dashboard from index.json (run `wif scan` to refresh). Fits in ~40
lines by default; --all lists every untracked container; --changes prints only
rows that changed since the last --changes call (for /loop ticks); --brief is
the two-line header only. Always exits 0.
"""
import json, os, sys, time, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = {"active": 0, "blocked": 1, "landed": 2, "parked": 3, "closed": 9}

def sh(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""

def age(ts):
    if not ts: return "?"
    d = int(time.time()) - int(ts)
    return f"{d//86400}d" if d >= 86400 else (f"{d//3600}h" if d >= 3600 else f"{d//60}m")

def trim(s, n):
    s = (s or "-").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"

def due_notes(streams, today):
    out = []
    for sid, s in streams.items():
        for ln in s.get("notes") or []:
            if "[reminder due=" not in ln: continue
            due = ln.split("due=", 1)[1].split("]", 1)[0]
            if (due == "landed" and s.get("status") in ("landed", "closed")) or (due != "landed" and due <= today):
                out.append((sid, ln))
    return out

def main():
    a = sys.argv[1:]
    w = json.loads(sh(["bash", os.path.join(HERE, "wif-where.sh"), "--json", os.getcwd()]) or "{}")
    if not w.get("served"):
        print(f"wif: scope {w.get('scope')} is not served by account {w.get('account')} — nothing to show"); return 0
    ledger = w["ledger"]; idx_path = os.path.join(ledger, "index.json")
    if not os.path.exists(idx_path):
        print(f"wif: no index for scope {w['scope']} yet — run `wif scan`"); return 0
    idx = json.load(open(idx_path))
    if "--json" in a:
        print(json.dumps(idx)); return 0
    today = datetime.date.today().isoformat()
    cont = {c["task"]: c for c in idx["containers"]}
    streams = idx.get("streams", {}); sess = idx.get("sessions", {})
    sid = a[a.index("--session") + 1] if "--session" in a else os.environ.get("CLAUDE_SESSION_ID", "")

    # ---- header: where am I
    lines = [f"wif · {w['account']} @ {w['scope']} · scanned {age(idx['scanned_at'])} ago"
             f"{'' if idx.get('prs_fetched') else ' · PRs cached/none (wif scan --prs)'}"]
    cur = w.get("id") or ""
    if cur:
        st = streams.get(cur); c = cont.get(cur)
        status = (st or {}).get("status") or ("untracked" if c else "unknown")
        lines.append(f"▶ {cur}  {status}" + (f"  [{' '.join(c['flags'])}]" if c and c.get("flags") else ""))
        if st:
            lines.append(f"  goal: {trim(st.get('goal'), 70)}")
            lines.append(f"  next: {trim(st.get('next'), 70)}   position: {trim(st.get('position'), 30)}")
        s = sess.get(cur)
        ctx = ""
        if sid:
            cf = os.path.join(ledger, "sessions", f"{sid}.ctx.json")
            if os.path.exists(cf):
                try: ctx = f"  ctx {json.load(open(cf)).get('used_pct', '?')}%"
                except Exception: pass
        if s:
            lines.append(f"  session: {trim(s.get('goal') or 'goal unset', 50)}   ~ {trim(s.get('last_intent') or s.get('last_prompt'), 50)}{ctx}")
        elif ctx:
            lines.append(f" {ctx}")
    else:
        lines.append(f"▶ (no stream here: {w.get('kind')})")
    if "--brief" in a:
        print("\n".join(lines)); return 0

    # ---- due reminders
    dn = due_notes(streams, today)
    if dn:
        lines.append("due:")
        for sid_, ln in dn[:5]:
            lines.append(f"  ! {sid_}: {trim(ln.split('] ', 1)[-1], 80)}")

    # ---- tracked streams
    rows = []
    for k, s in streams.items():
        if s.get("status") == "closed": continue
        c = cont.get(k, {})
        rows.append((ORDER.get(s.get("status"), 5), -(c.get("last_activity_ts") or 0), k, s, c))
    rows.sort()
    if "--changes" in a:
        prev_p = os.path.join(ledger, "cache", "prev-shown.json")
        prev = json.load(open(prev_p)) if os.path.exists(prev_p) else {}
        cur_sig = {c["task"]: [c["stream"], c["dirty"], c["ahead"], c["flags"], len(c["prs"] or []),
                               [p.get("state") for p in (c["prs"] or [])]] for c in idx["containers"]}
        changed = [t for t, v in cur_sig.items() if prev.get(t) != v]
        gone = [t for t in prev if t not in cur_sig]
        json.dump(cur_sig, open(prev_p, "w"))
        if not changed and not gone and not dn:
            print("\n".join(lines)); print("no changes"); return 0
        lines.append(f"changed ({len(changed)}):")
        for t in changed[:15]:
            c = cont[t]; lines.append(f"  {t:<34} {str(c['stream'] or 'untracked'):<9} {age(c['last_activity_ts']):>4} {' '.join(c['flags'])}")
        for t in gone: lines.append(f"  {t:<34} removed")
        print("\n".join(lines)); return 0

    lines.append(f"streams ({len(rows)}):")
    lines.append(f"  {'id':<34} {'status':<8} {'age':>4} {'next':<40} flags")
    for _, _, k, s, c in rows[:14]:
        if k == cur: continue
        lines.append(f"  {trim(k,34):<34} {s.get('status',''):<8} {age(c.get('last_activity_ts') or 0):>4} {trim(s.get('next'),40):<40} {' '.join(c.get('flags', []))}")
    orphans = idx.get("orphan_streams") or []
    if orphans:
        lines.append(f"  (no container: {', '.join(orphans[:6])}{'…' if len(orphans) > 6 else ''})")

    # ---- tangents (candidates)
    tang = [(k, ln) for k, s in streams.items() for ln in (s.get("notes") or []) if "[tangent]" in ln]
    if tang:
        lines.append(f"candidates ({len(tang)}):")
        for k, ln in tang[:4]:
            lines.append(f"  ← {k}: {trim(ln.split('] ', 1)[-1], 70)}")

    # ---- untracked containers
    un = sorted([c for c in idx["containers"] if not c["stream"]], key=lambda c: -c["last_activity_ts"])
    lim = len(un) if "--all" in a else 8
    if un:
        lines.append(f"untracked containers ({len(un)}; wif adopt <task> [-s parked]):")
        for c in un[:lim]:
            h = c.get("herdr") or {}
            lines.append(f"  {trim(c['task'],34):<34} {age(c['last_activity_ts']):>4} {c['shape']:<7} "
                         f"{'dirty ' + str(c['dirty']) if c['dirty'] else '':<9} {('herdr:' + str(h.get('agent_status'))) if h else '':<13} {' '.join(f for f in c['flags'] if f != 'dirty')}")
        if len(un) > lim: lines.append(f"  … {len(un) - lim} more (wif show --all)")
    ub = idx.get("unbound_memory") or []
    if ub:
        lines.append(f"unbound memory ({len(ub)}): " + ", ".join(f"{m['task']}({m['files']})" for m in ub[:6]) + ("…" if len(ub) > 6 else ""))
    print("\n".join(lines)); return 0

if __name__ == "__main__":
    sys.exit(main())
