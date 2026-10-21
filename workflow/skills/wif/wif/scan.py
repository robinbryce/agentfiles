"""`wif scan`: rebuild <ledger>/index.json for one scope. Read-only everywhere
except the ledger (index, PR cache, pruning of old session files). Never
creates or edits stream files."""
from __future__ import annotations
import json
import os
import re
import sys
import time
from pathlib import Path

from . import config, paths, proc
from .ledger import Stream, dump_json, load_json


def git_facts(repo: Path) -> dict:
    r = str(repo)
    f: dict = {"path": r, "name": repo.name}
    rc, b = proc.git(r, "symbolic-ref", "--short", "-q", "HEAD")
    f["branch"] = b if rc == 0 and b else "detached"
    rc, s = proc.git(r, "status", "--porcelain", "--untracked-files=no", timeout=30)
    f["dirty"] = len(s.splitlines()) if rc == 0 else -1
    f["ahead"] = f["behind"] = f["remote_ref"] = None
    for ref in ("@{u}", f"origin/{f['branch']}" if f["branch"] != "detached" else None):
        if not ref:
            continue
        rc, ab = proc.git(r, "rev-list", "--left-right", "--count", f"{ref}...HEAD")
        if rc == 0 and ab:
            try:
                behind, ahead = ab.split()
                f["ahead"], f["behind"], f["remote_ref"] = int(ahead), int(behind), ref
                break
            except ValueError:
                pass
    rc, ts = proc.git(r, "log", "-1", "--format=%ct")
    f["last_commit_ts"] = int(ts) if rc == 0 and ts.isdigit() else 0
    rc, rem = proc.git(r, "remote", "get-url", "origin")
    f["origin"] = rem if rc == 0 and rem else None
    return f


def is_worktree_root(d: Path) -> bool:
    rc, out = proc.git(str(d), "rev-parse", "--show-toplevel")
    try:
        return rc == 0 and bool(out) and Path(out).resolve() == d.resolve()
    except OSError:
        return False


def prs_for(task: str, repos: list[dict], cache_dir: Path, want: bool, failures: list, seen: dict):
    """-> (prs or None). Failures are reported, never cached."""
    cf = cache_dir / "prs" / f"{task}.json"
    fresh = cf.exists() and (time.time() - cf.stat().st_mtime) < config.pr_ttl()
    if fresh or not want:
        return load_json(cf, None) if cf.exists() else None
    out, failed = [], False
    for r in repos:
        if not r.get("origin") or r["branch"] == "detached":
            continue
        key = (r["origin"], r["branch"])
        if key in seen:
            out.extend(seen[key]); continue
        rc, o = proc.run(["gh", "pr", "list", "--head", r["branch"], "--state", "all",
                          "--json", "number,state,url,title,mergedAt,headRefOid"], cwd=r["path"], timeout=40)
        try:
            got = json.loads(o) if rc == 0 and o else ([] if rc == 0 else None)
        except ValueError:
            got = None
        if got is None:
            failed = True; failures.append(f"{task}/{r['name']}"); continue
        for p in got:
            p["repo"] = r["name"]
        seen[key] = got; out.extend(got)
    if failed:
        return load_json(cf, None) if cf.exists() else None
    dump_json(cf, out)
    return out


def herdr_workspaces() -> dict:
    rc, out = proc.run(["herdr", "workspace", "list"], timeout=5)
    ws = {}
    if rc != 0 or not out:
        return ws
    try:
        for w in json.loads(out)["result"]["workspaces"]:
            ws[(w.get("label") or "").lower()] = {"agent_status": w.get("agent_status"), "focused": w.get("focused"),
                                                   "path": (w.get("worktree") or {}).get("checkout_path")}
    except (ValueError, KeyError, TypeError):
        pass
    return ws


def sanitize(p: str) -> str:
    """Claude Code's project-dir sanitizer: every non-alphanumeric byte -> '-'."""
    return re.sub(r"[^a-zA-Z0-9]", "-", p)


def prune_sessions(ledger: Path, now: float) -> int:
    sd = ledger / "sessions"
    n = 0
    keep = config.session_keep_days() * 86400
    for jf in sd.glob("*.json"):
        try:
            if jf.name.endswith(".ctx.json"):
                base = jf.with_name(jf.name[:-len(".ctx.json")] + ".json")
                if not base.exists() and now - jf.stat().st_mtime > 86400:
                    jf.unlink(); n += 1
                continue
            s = load_json(jf, {})
            if isinstance(s, dict) and s.get("ended") and now - jf.stat().st_mtime > keep:
                jf.unlink(); n += 1
        except OSError:
            pass
    return n


def memory_dirs(cfg: Path, root: Path | None) -> dict[str, list[dict]]:
    mem: dict[str, list[dict]] = {}
    if not root:
        return mem
    san = sanitize(str(root))
    prefix = f"{san}--worktrees-herdr-"
    for md in (cfg / "projects").glob(f"{prefix}*/memory"):
        key = md.parent.name[len(prefix):]
        try:
            n = len([x for x in md.iterdir() if x.suffix == ".md"])
        except OSError:
            n = 0
        mem.setdefault(key, []).append({"dir": str(md), "files": n})
    return mem


def build_index(ctx: paths.Ctx, want_prs: bool = False) -> dict:
    ledger = paths.ledger_init(ctx.scope, ctx.config_dir)
    root = ctx.root
    now = time.time()
    pruned = prune_sessions(ledger, now)

    streams: dict[str, dict] = {}
    for sf in (ledger / "streams").glob("*.md"):
        try:
            s = Stream.load(sf)
        except (OSError, UnicodeDecodeError):
            continue
        if not s.fm:
            continue
        d = dict(s.fm)
        d["file"] = str(sf); d["notes"] = s.notes(); d["_lines"] = s.line_count
        try:
            d["_updated_ts"] = time.mktime(time.strptime(d.get("updated", ""), "%Y-%m-%d"))
        except (ValueError, OverflowError):
            d["_updated_ts"] = 0
        streams[d.get("id") or sf.stem] = d

    sess: dict[str, dict] = {}
    for jf in (ledger / "sessions").glob("*.json"):
        if jf.name.endswith(".ctx.json"):
            continue
        s = load_json(jf, None)
        if not isinstance(s, dict) or not s.get("stream"):
            continue
        mt = jf.stat().st_mtime
        st = s["stream"]
        if st not in sess or mt > sess[st]["mtime"]:
            ring = s.get("ring") or []
            last = ring[-1] if ring and isinstance(ring[-1], dict) else {}
            sess[st] = {"mtime": mt, "session_id": s.get("session_id"), "goal": s.get("goal"),
                        "last_intent": last.get("intent"), "last_prompt": last.get("prompt"), "ended": s.get("ended")}

    mem = memory_dirs(ctx.config_dir, root)
    ws = herdr_workspaces()
    failures: list[str] = []; seen: dict = {}
    containers: list[dict] = []; tasks: list[str] = []

    cont_root = root / paths.HERDR_DIR if root else None
    if cont_root and cont_root.is_dir():
        for path in sorted(cont_root.iterdir()):
            task = path.name
            if not path.is_dir() or task.startswith("."):
                continue
            tasks.append(task)
            try:
                entries = [e for e in path.iterdir() if e.name != ".DS_Store"]
            except OSError:
                entries = []
            repos, other = [], []
            if not path.is_dir():
                continue
            if is_worktree_root(path):
                repos.append(git_facts(path)); shape = "direct"
            else:
                for e in sorted(entries):
                    if e.is_dir() and is_worktree_root(e):
                        repos.append(git_facts(e))
                    elif e.name not in (".envrc", ".claude", ".mcp.json"):
                        other.append(e.name)
                shape = "empty" if not entries else ("norepos" if not repos else ("docs" if other else "normal"))
            containers.append({"task": task, "path": str(path), "shape": shape, "repos": repos, "other": other, "kind": "herdr"})

    for sid_, st in streams.items():
        b = st.get("backing", "")
        if b.startswith("repo:") and sid_ not in tasks:
            p = Path(b[len("repo:"):])
            if p.is_dir() and is_worktree_root(p):
                containers.append({"task": sid_, "path": str(p), "shape": "repo", "repos": [git_facts(p)], "other": [], "kind": "repo"})
                tasks.append(sid_)

    bound: dict[str, list[dict]] = {}
    for key, lst in mem.items():
        cands = [t for t in tasks if key == sanitize(t) or key.startswith(sanitize(t) + "-")]
        if cands:
            bound.setdefault(max(cands, key=len), []).extend(lst)
    bound_dirs = {d["dir"] for lst in bound.values() for d in lst}

    stale_s = config.stale_days() * 86400
    cap = config.stream_cap()
    for c in containers:
        task, repos = c["task"], c["repos"]
        last_commit = max((r["last_commit_ts"] for r in repos), default=0)
        try:
            dir_ts = int(Path(c["path"]).stat().st_mtime)
        except OSError:                     # container vanished mid-scan
            dir_ts = 0
        last_ts = last_commit if repos else dir_ts
        dirty = sum(max(r["dirty"], 0) for r in repos)
        ahead_known = bool(repos) and all(r["ahead"] is not None for r in repos)
        ahead = sum(r["ahead"] or 0 for r in repos)
        prs = prs_for(task, repos, ledger / "cache", want_prs, failures, seen)
        st = streams.get(task)
        sess_ts = int(sess[task]["mtime"]) if task in sess else 0
        upd_ts = int(st.get("_updated_ts", 0)) if st else 0
        last_activity = max(last_ts, sess_ts, upd_ts)
        stale = (now - last_activity) > stale_s and dirty == 0
        landed_prop = (bool(prs) and all(p.get("state") == "MERGED" for p in prs) and dirty == 0 and ahead_known and ahead == 0)
        flags = [f for f, on in (
            ("stale", stale), ("dirty", dirty > 0), ("unpushed", ahead_known and ahead > 0),
            ("unpublished", any(r["origin"] and r["ahead"] is None and r["branch"] != "detached" for r in repos)),
            ("no-remote", any(not r["origin"] for r in repos)),
            ("landed?", landed_prop and (st or {}).get("status") not in ("landed", "closed")),
            ("over-cap", bool(st) and st.get("_lines", 0) > cap),
            ("bad-status", bool(st) and st.get("status") not in config.STATUSES)) if on]
        c.update({"dirty": dirty, "ahead": ahead if ahead_known else None, "last_activity_ts": last_activity,
                  "memory": bound.get(task, []), "herdr": ws.get(task.lower()), "prs": prs,
                  "stream": st.get("status") if st else None, "stream_file": st.get("file") if st else None, "flags": flags})

    orphan = [k for k, s in streams.items() if k not in tasks and s.get("status") != "closed"]
    unbound = [{"task": k, **v[0]} for k, v in mem.items() if not any(d["dir"] in bound_dirs for d in v)]
    return {"scanned_at": int(now), "scope": ctx.scope, "account": ctx.account, "root": str(root or ""),
            "prs_fetched": want_prs, "pr_failures": failures, "pruned_sessions": pruned, "containers": containers,
            "streams": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in streams.items()},
            "sessions": sess, "orphan_streams": orphan, "unbound_memory": unbound}


def main(args: list[str], out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    want_prs = "--prs" in args; quiet = "--quiet" in args; as_json = "--json" in args
    scope = args[args.index("--scope") + 1] if "--scope" in args and args.index("--scope") + 1 < len(args) else None
    if scope and scope not in paths.known_scopes():
        print(f"wif: unknown scope '{scope}' (known: {' '.join(paths.known_scopes())})", file=err); return 1
    ctx = paths.resolve(None, scope)
    if not ctx.served:
        print(f"wif: scope {ctx.scope} is not served by account {ctx.account} — nothing recorded", file=err); return 0
    index = build_index(ctx, want_prs)
    dump_json(ctx.ledger / "index.json", index)
    if as_json:
        print(json.dumps(index), file=out)
    elif not quiet:
        c = index["containers"]
        tracked = sum(1 for x in c if x["stream"])
        f = index["pr_failures"]
        print(f"wif scan: {ctx.scope} · {len(c)} containers ({tracked} tracked) · {len(index['orphan_streams'])} streams without "
              f"container · {len(index['unbound_memory'])} unbound memory dirs · "
              f"{'PRs fetched' if want_prs else 'PRs from cache only'}"
              f"{' · gh FAILED for ' + ', '.join(f[:4]) + ('…' if len(f) > 4 else '') if f else ''}"
              f"{' · pruned ' + str(index['pruned_sessions']) + ' old sessions' if index['pruned_sessions'] else ''}"
              f" → {ctx.ledger}/index.json", file=out)
    return 0
