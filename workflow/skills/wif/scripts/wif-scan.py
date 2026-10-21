#!/usr/bin/env python3
"""wif scan [--prs] [--scope S] [--quiet] [--json]

Rebuild <ledger>/index.json from disk for one scope. Read-only everywhere
except the ledger (index.json, the PR cache, and pruning of old session
files). Joins: herdr containers + their repo worktrees (git facts), repo-kind
streams, stream files, session files, auto-memory dirs, herdr workspaces, and
(opt-in, cached) GitHub PRs. Never creates or edits stream files.
"""
import json, os, re, subprocess, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))
STREAM_CAP = int(os.environ.get("WIF_STREAM_CAP", "120"))
STALE_S = int(os.environ.get("WIF_STALE_DAYS", "14")) * 86400
PR_TTL = int(os.environ.get("WIF_PR_TTL", str(6 * 3600)))
KEEP_S = int(os.environ.get("WIF_SESSION_KEEP_DAYS", "30")) * 86400
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
STATUSES = ("active", "parked", "blocked", "landed", "closed")

def sh(args, cwd=None, timeout=20):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=GIT_ENV)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""

def load_json(path, default):
    try:
        with open(path) as fh:
            v = json.load(fh)
        return v if v is not None else default
    except Exception:
        return default

def where(cwd):
    rc, out = sh(["bash", os.path.join(HERE, "wif-where.sh"), "--json", cwd])
    try:
        return json.loads(out)
    except Exception:
        return {}

def unq(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return v

def fm(path):
    """flat yaml frontmatter -> dict (+ _lines = line count of the file)"""
    d = {}
    try:
        with open(path) as fh:
            lines = fh.read().splitlines()
    except OSError:
        return d
    if not lines or lines[0] != "---":
        return d
    for ln in lines[1:]:
        if ln == "---":
            break
        m = re.match(r'^([a-z_]+): (.*)$', ln)
        if m:
            d[m.group(1)] = unq(m.group(2))
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
    rc, s = sh(["git", "-C", repo, "status", "--porcelain", "--untracked-files=no"], timeout=30)
    f["dirty"] = len(s.splitlines()) if rc == 0 else -1
    # ahead/behind: upstream if configured, else origin/<branch>; else unknown
    f["ahead"], f["behind"], f["remote_ref"] = None, None, None
    for ref in ("@{u}", f"origin/{f['branch']}" if f["branch"] != "detached" else None):
        if not ref:
            continue
        rc, ab = sh(["git", "-C", repo, "rev-list", "--left-right", "--count", f"{ref}...HEAD"])
        if rc == 0 and ab:
            behind, ahead = ab.split()
            f["ahead"], f["behind"], f["remote_ref"] = int(ahead), int(behind), ref
            break
    rc, ts = sh(["git", "-C", repo, "log", "-1", "--format=%ct"])
    f["last_commit_ts"] = int(ts) if rc == 0 and ts.isdigit() else 0
    rc, rem = sh(["git", "-C", repo, "remote", "get-url", "origin"])
    f["origin"] = rem if rc == 0 and rem else None
    return f

def is_worktree_root(d):
    rc, out = sh(["git", "-C", d, "rev-parse", "--show-toplevel"])
    return rc == 0 and os.path.realpath(out) == os.path.realpath(d)

def prs_for(task, repos, cache_dir, want, failures, seen):
    """Returns (prs or None, from_cache). Failures are never cached."""
    cf = os.path.join(cache_dir, "prs", f"{task}.json")
    fresh = os.path.exists(cf) and (time.time() - os.path.getmtime(cf)) < PR_TTL
    if fresh or not want:
        return load_json(cf, None) if os.path.exists(cf) else None, True
    out, failed = [], False
    for r in repos:
        if not r.get("origin") or r["branch"] == "detached":
            continue
        key = (r["origin"], r["branch"])
        if key in seen:
            out.extend(seen[key]); continue
        rc, o = sh(["gh", "pr", "list", "--head", r["branch"], "--state", "all",
                    "--json", "number,state,url,title,mergedAt,headRefOid"], cwd=r["path"], timeout=40)
        if rc != 0:
            failed = True; failures.append(f"{task}/{r['name']}"); continue
        try:
            got = json.loads(o) if o else []
        except Exception:
            failed = True; failures.append(f"{task}/{r['name']}"); continue
        for p in got:
            p["repo"] = r["name"]
        seen[key] = got; out.extend(got)
    if failed:
        return load_json(cf, None) if os.path.exists(cf) else None, True
    os.makedirs(os.path.dirname(cf), exist_ok=True)
    tmp = cf + ".tmp"
    json.dump(out, open(tmp, "w")); os.replace(tmp, cf)
    return out, False

def herdr_workspaces():
    rc, out = sh(["herdr", "workspace", "list"], timeout=5)
    ws = {}
    if rc != 0 or not out:
        return ws
    try:
        for w in json.loads(out)["result"]["workspaces"]:
            key = (w.get("label") or "").lower()
            ws[key] = {"agent_status": w.get("agent_status"), "focused": w.get("focused"),
                       "path": (w.get("worktree") or {}).get("checkout_path")}
    except Exception:
        pass
    return ws

def sanitize(p):
    return re.sub(r"[/.]", "-", p)

def prune_sessions(ledger, now):
    """Delete ended session files older than KEEP_S and ctx sidecars whose session is gone (>1d)."""
    sd = os.path.join(ledger, "sessions"); n = 0
    for jf in glob.glob(os.path.join(sd, "*.json")):
        try:
            if jf.endswith(".ctx.json"):
                base = jf[:-len(".ctx.json")] + ".json"
                if not os.path.exists(base) and now - os.path.getmtime(jf) > 86400:
                    os.remove(jf); n += 1
                continue
            s = load_json(jf, {})
            if isinstance(s, dict) and s.get("ended") and now - os.path.getmtime(jf) > KEEP_S:
                os.remove(jf); n += 1
        except OSError:
            pass
    return n

def main():
    args = sys.argv[1:]
    want_prs = "--prs" in args; quiet = "--quiet" in args; as_json = "--json" in args
    scope = args[args.index("--scope") + 1] if "--scope" in args and args.index("--scope") + 1 < len(args) else None
    w = where(os.getcwd())
    if not w:
        print("wif: could not resolve scope (is jq installed?)", file=sys.stderr); return 1
    if scope and scope != w.get("scope"):
        rc, known = sh(["bash", "-c", f'. "{HERE}/wif-lib.sh"; wif_known_scopes'])
        if scope not in known.split():
            print(f"wif: unknown scope '{scope}' (known: {known})", file=sys.stderr); return 1
        rc, root = sh(["bash", "-c", f'. "{HERE}/wif-lib.sh"; wif_scope_root "$1"', "_", scope])
        rc, served = sh(["bash", "-c", f'. "{HERE}/wif-lib.sh"; wif_account_serves "$(wif_account)" "$1" && echo 1 || echo 0', "_", scope])
        w = {"scope": scope, "root": root, "account": w.get("account"), "config_dir": w.get("config_dir"),
             "ledger": os.path.join(w.get("config_dir", ""), "wif", scope), "served": served == "1"}
    if not w.get("served"):
        print(f"wif: scope {w.get('scope')} is not served by account {w.get('account')} — nothing recorded", file=sys.stderr)
        return 0
    ledger = w["ledger"]; root = w.get("root") or ""
    for sub in ("streams", "sessions", "archive", "cache"):
        os.makedirs(os.path.join(ledger, sub), exist_ok=True)
    cont_root = os.path.join(root, ".worktrees-herdr") if root else ""
    now = int(time.time())
    pruned = prune_sessions(ledger, now)

    # streams on record
    streams = {}
    for sf in glob.glob(os.path.join(ledger, "streams", "*.md")):
        d = fm(sf)
        if not d:
            continue
        d["file"] = sf; d["notes"] = section(sf, "Notes")
        try:
            d["updated_ts"] = int(time.mktime(time.strptime(d.get("updated", ""), "%Y-%m-%d")))
        except Exception:
            d["updated_ts"] = 0
        streams[d.get("id") or os.path.basename(sf)[:-3]] = d

    # sessions: latest per stream (by ended/started, then mtime)
    sess = {}
    for jf in glob.glob(os.path.join(ledger, "sessions", "*.json")):
        if jf.endswith(".ctx.json"):
            continue
        s = load_json(jf, None)
        if not isinstance(s, dict):
            continue
        st = s.get("stream"); mt = os.path.getmtime(jf)
        if st and (st not in sess or mt > sess[st]["mtime"]):
            ring = s.get("ring") or []
            last = ring[-1] if ring and isinstance(ring[-1], dict) else {}
            sess[st] = {"mtime": mt, "session_id": s.get("session_id"), "goal": s.get("goal"),
                        "last_intent": last.get("intent"), "last_prompt": last.get("prompt"),
                        "ended": s.get("ended")}

    # memory dirs: key = sanitized path suffix after "--worktrees-herdr-"
    cfg = w.get("config_dir") or os.path.dirname(os.path.dirname(ledger))
    san = sanitize(root) if root else None
    mem = {}
    if san:
        for md in glob.glob(os.path.join(cfg, "projects", f"{san}--worktrees-herdr-*", "memory")):
            key = os.path.basename(os.path.dirname(md))[len(san) + len("--worktrees-herdr-"):]
            try:
                n = len([x for x in os.listdir(md) if x.endswith(".md")])
            except OSError:
                n = 0
            mem.setdefault(key, []).append({"dir": md, "files": n})

    ws = herdr_workspaces()
    failures, seen = [], {}
    containers, tasks = [], []

    # --- herdr containers
    if cont_root and os.path.isdir(cont_root):
        for task in sorted(os.listdir(cont_root)):
            path = os.path.join(cont_root, task)
            if not os.path.isdir(path) or task.startswith("."):
                continue
            tasks.append(task)
            try:
                entries = [e for e in os.listdir(path) if e not in (".DS_Store",)]
            except OSError:
                entries = []
            repos, other = [], []
            if is_worktree_root(path):
                repos.append(git_facts(path)); shape = "direct"
            else:
                for e in sorted(entries):
                    p = os.path.join(path, e)
                    if os.path.isdir(p) and is_worktree_root(p):
                        repos.append(git_facts(p))
                    elif e not in (".envrc", ".claude", ".mcp.json"):
                        other.append(e)
                shape = "empty" if not entries else ("norepos" if not repos else ("docs" if other else "normal"))
            containers.append({"task": task, "path": path, "shape": shape, "repos": repos, "other": other, "kind": "herdr"})

    # --- repo-kind streams (plain checkouts) become containers too
    for sid_, st in streams.items():
        b = st.get("backing", "")
        if b.startswith("repo:") and sid_ not in tasks:
            p = b[len("repo:"):]
            if os.path.isdir(p) and is_worktree_root(p):
                containers.append({"task": sid_, "path": p, "shape": "repo", "repos": [git_facts(p)], "other": [], "kind": "repo"})
                tasks.append(sid_)

    # --- bind memory dirs by longest matching task (task == key, or key startswith task-)
    bound = {}
    for key in mem:
        cands = [t for t in tasks if key == sanitize(t) or key.startswith(sanitize(t) + "-")]
        if cands:
            bound.setdefault(max(cands, key=len), []).extend(mem[key])

    # --- facts per container
    for c in containers:
        task, repos = c["task"], c["repos"]
        last_commit = max((r["last_commit_ts"] for r in repos), default=0)
        last_ts = last_commit if repos else int(os.path.getmtime(c["path"]))
        dirty = sum(max(r["dirty"], 0) for r in repos)
        ahead_known = all(r["ahead"] is not None for r in repos) and bool(repos)
        ahead = sum(r["ahead"] or 0 for r in repos)
        prs, _cached = prs_for(task, repos, os.path.join(ledger, "cache"), want_prs, failures, seen)
        st = streams.get(task)
        sess_ts = int(sess[task]["mtime"]) if task in sess else 0
        upd_ts = st.get("updated_ts", 0) if st else 0
        last_activity = max(last_ts, sess_ts, upd_ts)
        stale = (now - last_activity) > STALE_S and dirty == 0
        landed_prop = (bool(prs) and all(p.get("state") == "MERGED" for p in prs)
                       and dirty == 0 and ahead_known and ahead == 0)
        flags = [f for f, on in (("stale", stale), ("dirty", dirty > 0),
                                 ("unpushed", ahead_known and ahead > 0),
                                 ("unpublished", any(r["origin"] and r["ahead"] is None and r["branch"] != "detached" for r in repos)),
                                 ("no-remote", any(not r["origin"] for r in repos)),
                                 ("landed?", landed_prop and (st or {}).get("status") not in ("landed", "closed")),
                                 ("over-cap", bool(st) and st.get("_lines", 0) > STREAM_CAP),
                                 ("bad-status", bool(st) and st.get("status") not in STATUSES)) if on]
        c.update({"dirty": dirty, "ahead": ahead if ahead_known else None, "last_activity_ts": last_activity,
                  "memory": bound.get(task, []), "herdr": ws.get(task.lower()), "prs": prs,
                  "stream": st.get("status") if st else None, "stream_file": st.get("file") if st else None,
                  "flags": flags})

    orphan_streams = [k for k, s in streams.items() if k not in tasks and s.get("status") != "closed"]
    bound_keys = {d["dir"] for lst in bound.values() for d in lst}
    unbound = [{"task": k, **v[0]} for k, v in mem.items() if not any(d["dir"] in bound_keys for d in v)]
    index = {"scanned_at": now, "scope": w["scope"], "account": w["account"], "root": root,
             "prs_fetched": want_prs, "pr_failures": failures, "pruned_sessions": pruned,
             "containers": containers,
             "streams": {k: {kk: vv for kk, vv in v.items() if kk != "updated_ts"} for k, v in streams.items()},
             "sessions": sess, "orphan_streams": orphan_streams, "unbound_memory": unbound}
    tmp = os.path.join(ledger, "index.json.tmp")
    json.dump(index, open(tmp, "w"), indent=1); os.replace(tmp, os.path.join(ledger, "index.json"))
    if as_json:
        print(json.dumps(index))
    elif not quiet:
        tracked = sum(1 for c in containers if c["stream"])
        print(f"wif scan: {w['scope']} · {len(containers)} containers ({tracked} tracked) · "
              f"{len(orphan_streams)} streams without container · {len(unbound)} unbound memory dirs"
              f"{' · PRs fetched' if want_prs else ' · PRs from cache only'}"
              f"{' · gh FAILED for ' + ', '.join(failures[:4]) + ('…' if len(failures) > 4 else '') if failures else ''}"
              f"{' · pruned ' + str(pruned) + ' old sessions' if pruned else ''} → {ledger}/index.json")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never leave a half-written index behind
        print(f"wif scan: failed: {e!r}", file=sys.stderr); sys.exit(1)
