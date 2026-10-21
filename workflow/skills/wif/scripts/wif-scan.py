#!/usr/bin/env python3
"""wif scan [--prs] [--scope S] [--quiet] [--json]

Rebuild <ledger>/index.json from disk for one scope. Read-only everywhere
except the ledger. Joins: herdr containers + their repo worktrees (git facts),
stream files, session files, auto-memory dirs, herdr workspaces, and (opt-in,
cached) GitHub PRs. Never creates or edits stream files.
"""
import json, os, re, subprocess, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))

def sh(args, cwd=None, timeout=20):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""

def where(cwd):
    rc, out = sh(["bash", os.path.join(HERE, "wif-where.sh"), "--json", cwd])
    return json.loads(out) if out else {}

def fm(path):
    """flat yaml frontmatter -> dict"""
    d = {}
    try:
        with open(path) as fh:
            lines = fh.read().split("\n")
    except OSError:
        return d
    if not lines or lines[0] != "---":
        return d
    for ln in lines[1:]:
        if ln == "---":
            break
        m = re.match(r'^([a-z_]+): (.*)$', ln)
        if m:
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1].replace('\\"', '"')
            d[m.group(1)] = v
    d["_lines"] = len(lines)
    return d

def section(path, name):
    out, on = [], False
    try:
        for ln in open(path):
            ln = ln.rstrip("\n")
            if ln == f"## {name}":
                on = True; continue
            if on and ln.startswith("## "):
                break
            if on and ln and not ln.startswith("<!--"):
                out.append(ln)
    except OSError:
        pass
    return out

def git_facts(repo):
    f = {"path": repo, "name": os.path.basename(repo)}
    rc, b = sh(["git", "-C", repo, "symbolic-ref", "--short", "-q", "HEAD"])
    f["branch"] = b if rc == 0 else "detached"
    rc, s = sh(["git", "-C", repo, "status", "--porcelain", "--untracked-files=no"], timeout=60)
    f["dirty"] = len(s.splitlines()) if rc == 0 else -1
    rc, ab = sh(["git", "-C", repo, "rev-list", "--left-right", "--count", "@{u}...HEAD"])
    if rc == 0 and ab:
        behind, ahead = ab.split()
        f["ahead"], f["behind"] = int(ahead), int(behind)
    else:
        f["ahead"], f["behind"] = None, None   # no upstream
    rc, ts = sh(["git", "-C", repo, "log", "-1", "--format=%ct"])
    f["last_commit_ts"] = int(ts) if rc == 0 and ts else 0
    rc, rem = sh(["git", "-C", repo, "remote", "get-url", "origin"])
    f["has_origin"] = rc == 0 and bool(rem)
    return f

def is_worktree(d):
    rc, out = sh(["git", "-C", d, "rev-parse", "--is-inside-work-tree"])
    return rc == 0 and out == "true"

def prs_for(task, repos, cache_dir, want):
    cf = os.path.join(cache_dir, "prs", f"{task}.json")
    if os.path.exists(cf) and (time.time() - os.path.getmtime(cf)) < 6 * 3600:
        try:
            return json.load(open(cf)), True
        except Exception:
            pass
    if not want:
        return (json.load(open(cf)) if os.path.exists(cf) else None), True
    out = []
    for r in repos:
        if not r.get("has_origin") or r["branch"] == "detached":
            continue
        rc, o = sh(["gh", "pr", "list", "--head", r["branch"], "--state", "all",
                    "--json", "number,state,url,title,mergedAt,headRefOid"], cwd=r["path"], timeout=40)
        if rc == 0 and o:
            try:
                for p in json.loads(o):
                    p["repo"] = r["name"]; out.append(p)
            except Exception:
                pass
    os.makedirs(os.path.dirname(cf), exist_ok=True)
    json.dump(out, open(cf, "w"))
    return out, False

def herdr_workspaces():
    rc, out = sh(["herdr", "workspace", "list"], timeout=5)
    ws = {}
    if rc != 0 or not out:
        return ws
    try:
        for w in json.loads(out)["result"]["workspaces"]:
            key = w.get("label", "").lower()
            ws[key] = {"agent_status": w.get("agent_status"), "focused": w.get("focused"),
                       "path": (w.get("worktree") or {}).get("checkout_path")}
    except Exception:
        pass
    return ws

def main():
    args = sys.argv[1:]
    want_prs = "--prs" in args; quiet = "--quiet" in args; as_json = "--json" in args
    scope = args[args.index("--scope") + 1] if "--scope" in args else None
    w = where(os.getcwd())
    if scope and scope != w.get("scope"):
        env = dict(os.environ)
        rc, out = sh(["bash", "-c", f'. "{HERE}/wif-lib.sh"; wif_scope_root {scope}'])
        w = {"scope": scope, "root": out, "account": w.get("account"),
             "ledger": os.path.join(w.get("config_dir", ""), "wif", scope), "served": True}
        rc, s = sh(["bash", "-c", f'. "{HERE}/wif-lib.sh"; wif_account_serves $(wif_account) {scope} && echo 1 || echo 0'])
        w["served"] = s == "1"
    if not w.get("served"):
        print(f"wif: scope {w.get('scope')} is not served by account {w.get('account')} — nothing recorded", file=sys.stderr)
        return 0
    ledger = w["ledger"]; root = w.get("root") or ""
    for sub in ("streams", "sessions", "archive", "cache"):
        os.makedirs(os.path.join(ledger, sub), exist_ok=True)
    cont_root = os.path.join(root, ".worktrees-herdr") if root else ""
    now = int(time.time())

    # streams on record
    streams = {}
    for sf in glob.glob(os.path.join(ledger, "streams", "*.md")):
        d = fm(sf); d["file"] = sf
        d["notes"] = section(sf, "Notes")
        streams[d.get("id", os.path.basename(sf)[:-3])] = d

    # sessions: latest per stream
    sess = {}
    for jf in glob.glob(os.path.join(ledger, "sessions", "*.json")):
        if jf.endswith(".ctx.json"):
            continue
        try:
            s = json.load(open(jf))
        except Exception:
            continue
        st = s.get("stream"); mt = os.path.getmtime(jf)
        if st and (st not in sess or mt > sess[st]["mtime"]):
            ring = s.get("ring") or []
            last = ring[-1] if ring else {}
            sess[st] = {"mtime": mt, "session_id": s.get("session_id"), "goal": s.get("goal"),
                        "last_intent": last.get("intent"), "last_prompt": last.get("prompt"),
                        "ended": s.get("ended")}

    # memory dirs keyed by task
    cfg = os.path.dirname(os.path.dirname(ledger))
    san = re.sub(r"[/.]", "-", root) if root else None
    mem = {}
    if san:
        for md in glob.glob(os.path.join(cfg, "projects", f"{san}--worktrees-herdr-*", "memory")):
            key = os.path.basename(os.path.dirname(md))[len(san) + len("--worktrees-herdr-"):]
            n = len([x for x in os.listdir(md) if x.endswith(".md")])
            mem.setdefault(key, []).append({"dir": md, "files": n})

    ws = herdr_workspaces()

    containers = []
    tasks = set()
    if cont_root and os.path.isdir(cont_root):
        for task in sorted(os.listdir(cont_root)):
            path = os.path.join(cont_root, task)
            if not os.path.isdir(path) or task.startswith("."):
                continue
            tasks.add(task)
            entries = [e for e in os.listdir(path) if e not in (".DS_Store",)]
            repos, other = [], []
            if is_worktree(path):
                repos.append(git_facts(path)); shape = "direct"
            else:
                for e in sorted(entries):
                    p = os.path.join(path, e)
                    if os.path.isdir(p) and is_worktree(p):
                        repos.append(git_facts(p))
                    elif e not in (".envrc", ".claude", ".mcp.json"):
                        other.append(e)
                shape = "empty" if not entries else ("norepos" if not repos else ("docs" if other else "normal"))
            last_ts = max(r["last_commit_ts"] for r in repos) if repos else int(os.path.getmtime(path))
            dirty = sum(max(r["dirty"], 0) for r in repos)
            ahead = sum(r["ahead"] or 0 for r in repos)
            prs, cached = prs_for(task, repos, os.path.join(ledger, "cache"), want_prs)
            # memory keys: exact task, or task-<repo>
            mems = []
            for k, v in mem.items():
                if k == task or any(k == f"{task}-{r['name']}" for r in repos):
                    mems.extend(v)
            st = streams.get(task)
            sess_ts = sess[task]["mtime"] if task in sess else 0
            stale = (now - max(last_ts, int(sess_ts))) > 14 * 86400
            landed_prop = bool(prs) and all(p.get("state") == "MERGED" for p in prs) and dirty == 0 and ahead == 0
            containers.append({
                "task": task, "path": path, "shape": shape, "repos": repos, "other": other,
                "dirty": dirty, "ahead": ahead, "last_activity_ts": max(last_ts, int(sess_ts)),
                "memory": mems, "herdr": ws.get(task.lower()), "prs": prs,
                "stream": st.get("status") if st else None,
                "stream_file": st.get("file") if st else None,
                "flags": [f for f, on in (("stale", stale), ("dirty", dirty > 0), ("unpushed", ahead > 0),
                                           ("landed?", landed_prop and (st or {}).get("status") not in ("landed", "closed")),
                                           ("over-cap", bool(st) and st.get("_lines", 0) > 120)) if on],
            })
    orphan_streams = [s for k, s in streams.items() if k not in tasks and s.get("status") != "closed"]
    unbound = [{"task": k, **v[0]} for k, v in mem.items()
               if k not in tasks and not any(k.startswith(t + "-") for t in tasks)]
    index = {"scanned_at": now, "scope": w["scope"], "account": w["account"], "root": root,
             "prs_fetched": want_prs, "containers": containers,
             "streams": {k: {kk: vv for kk, vv in v.items() if kk != "notes"} | {"notes": v["notes"]} for k, v in streams.items()},
             "sessions": sess, "orphan_streams": [s.get("id") for s in orphan_streams], "unbound_memory": unbound}
    tmp = os.path.join(ledger, "index.json.tmp")
    json.dump(index, open(tmp, "w"), indent=1); os.replace(tmp, os.path.join(ledger, "index.json"))
    if as_json:
        print(json.dumps(index))
    elif not quiet:
        tracked = sum(1 for c in containers if c["stream"])
        print(f"wif scan: {w['scope']} · {len(containers)} containers ({tracked} tracked) · "
              f"{len(orphan_streams)} streams without container · {len(unbound)} unbound memory dirs"
              f"{' · PRs fetched' if want_prs else ' · PRs from cache only'} → {ledger}/index.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
