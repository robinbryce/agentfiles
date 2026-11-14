#!/usr/bin/env python3
"""Build a thematic decision log (Markdown) and graph canvas (HTML) from one JSON data file.

Usage:
  build.py profile                        print the active profile and the overlay to load
  build.py init                           print a skeleton data file to start from
  build.py check DATA                     validate the data file only
  build.py build DATA --html OUT [--md OUT] [--canvas-url URL]
  build.py extract HTML                   print the data embedded in a built canvas

The data format is references/data-format.md. Python 3.9+, standard library only.
"""
import html
import json
import os
import re
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
STATUSES = ("in force", "amended", "superseded", "proposed")
PROFILES = ("forestrie", "justgames", "personal", "home")
MAX_THEMES = 8
TITLE_MAX = 36
COMPONENT_MAX = 32
DATA_TAG = '<script type="application/json" id="decision-data">'
COMPUTED = ("supersedes", "amends", "slot")


def detect_profile():
    """Profile from CLAUDE_CONFIG_DIR (~/.claude-<profile>), else the wif account."""
    base = os.path.basename(os.environ.get("CLAUDE_CONFIG_DIR", "").rstrip("/"))
    raw = base[len(".claude-"):] if base.startswith(".claude-") else ""
    if not raw:
        try:
            out = subprocess.run(["wif", "where", "--json"], capture_output=True, text=True, timeout=10)
            raw = (json.loads(out.stdout or "{}").get("account") or "").strip()
        except (OSError, ValueError, subprocess.SubprocessError):
            raw = ""
    return (raw if raw in PROFILES else "default"), raw


def cmd_profile():
    p, raw = detect_profile()
    print(f"profile: {p}" + (f" (unrecognised: {raw})" if raw and p == "default" else ""))
    print(f"overlay: {os.path.join(SKILL, 'references', f'profile-{p}.md')}")


SKELETON = {
    "meta": {
        "title": "Example Decisions",
        "eyebrow": "plan-YYMM-NN · design session · as of YYYY-MM-DD",
        "lede": "Every decision from the session, grouped by the design area it belongs to, traced to the parts of the system it shapes.",
        "pivot": {"id": "D2", "text": "D2 is the pivot: it replaced D1 and shapes both stores."},
    },
    "themes": [
        {"id": "storage", "name": "Storage", "blurb": "Where data lives and how long it is kept."},
        {"id": "access", "name": "Access", "blurb": "Who may read and write, and how that is checked."},
    ],
    "layers": [{"id": "svc", "name": "Services"}, {"id": "data", "name": "Data"}],
    "components": [
        {"id": "api", "name": "API", "layer": "svc", "desc": "The public HTTP API."},
        {"id": "cache", "name": "Cache", "layer": "data", "desc": "The read-through cache."},
        {"id": "db", "name": "Database", "layer": "data", "desc": "The system of record."},
    ],
    "decisions": [
        {"id": "D1", "theme": "storage", "title": "Cache writes through", "status": "superseded",
         "text": "Writes went to the cache and the database together. Replaced by D2.",
         "impacts": [], "lands": "(replaced)", "supersededBy": ["D2"], "amendedBy": []},
        {"id": "D2", "theme": "storage", "title": "Invalidate on write", "status": "in force",
         "text": "Writes go to the database only and invalidate the cache entry.",
         "impacts": ["cache", "db", "api"], "lands": "docs/adr/adr-0003", "supersededBy": [], "amendedBy": []},
        {"id": "D3", "theme": "access", "title": "Tokens checked at the edge", "status": "proposed",
         "text": "The API checks bearer tokens before any read; awaiting a ruling.",
         "impacts": ["api"], "lands": "plan slice 02", "supersededBy": [], "amendedBy": []},
    ],
    "open": [
        {"id": "D4", "title": "Cache TTL", "text": "D2 says nothing about how long an entry lives.",
         "rec": "Five minutes, matching the upstream feed.", "relates": ["D2"]},
    ],
    "resolved": ["D1 against D2 (write path): D2 replaced D1."],
    "fold": ["The architecture doc still describes write-through caching."],
}


def validate(d):
    errs = []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    meta = d.get("meta") or {}
    need(isinstance(meta.get("title"), str) and 0 < len(meta["title"]) <= 60, "meta.title: required, at most 60 characters")
    themes, layers, comps, decs = d.get("themes") or [], d.get("layers") or [], d.get("components") or [], d.get("decisions") or []
    need(1 <= len(themes) <= MAX_THEMES, f"themes: 1 to {MAX_THEMES} design areas (got {len(themes)})")
    need(len(layers) >= 1, "layers: at least one")
    need(len(comps) >= 1, "components: at least one")
    need(len(decs) >= 1, "decisions: at least one")
    tids = [t.get("id") for t in themes]
    lids = [l.get("id") for l in layers]
    cids = [c.get("id") for c in comps]
    ids = [x.get("id") for x in decs]
    for name, seq in (("theme", tids), ("layer", lids), ("component", cids), ("decision", ids)):
        dup = sorted({x for x in seq if seq.count(x) > 1})
        need(not dup, f"duplicate {name} ids: {dup}")
        need(all(isinstance(x, str) and x for x in seq), f"every {name} needs a string id")
    for t in themes:
        need(t.get("name") and t.get("blurb") is not None, f"theme {t.get('id')}: name and blurb")
    for l in layers:
        need(l.get("name"), f"layer {l.get('id')}: name")
    for c in comps:
        need(c.get("layer") in lids, f"component {c.get('id')}: unknown layer {c.get('layer')!r}")
        need(isinstance(c.get("name"), str) and 0 < len(c["name"]) <= COMPONENT_MAX,
             f"component {c.get('id')}: name at most {COMPONENT_MAX} characters")
        need(isinstance(c.get("desc"), str), f"component {c.get('id')}: desc")
    idset = set(ids)
    for x in decs:
        i = x.get("id")
        need(x.get("theme") in tids, f"{i}: unknown theme {x.get('theme')!r}")
        need(x.get("status") in STATUSES, f"{i}: status must be one of {STATUSES}")
        need(isinstance(x.get("title"), str) and 0 < len(x["title"]) <= TITLE_MAX,
             f"{i}: title at most {TITLE_MAX} characters (got {len(x.get('title') or '')})")
        need(isinstance(x.get("text"), str) and x["text"].strip(), f"{i}: text")
        need(isinstance(x.get("lands"), str), f"{i}: lands (where it is recorded)")
        for k in ("impacts", "supersededBy", "amendedBy"):
            x.setdefault(k, [])
            need(isinstance(x[k], list), f"{i}: {k} must be a list")
        bad = [c for c in x["impacts"] if c not in cids]
        need(not bad, f"{i}: impacts unknown components {bad}")
        bad = [r for r in x["supersededBy"] + x["amendedBy"] if r not in idset]
        need(not bad, f"{i}: refers to unknown decisions {bad}")
        need((x.get("status") == "superseded") == bool(x["supersededBy"]), f"{i}: superseded if and only if supersededBy is set")
        need((x.get("status") == "amended") == bool(x["amendedBy"]), f"{i}: amended if and only if amendedBy is set")
        need(x.get("status") == "superseded" or x["impacts"], f"{i}: a decision that is not superseded shapes at least one component")
    for q in d.get("open") or []:
        need(q.get("id") and q.get("title") and q.get("text") and q.get("rec"), f"open {q.get('id')}: id, title, text, rec")
        need(q.get("id") not in idset, f"open {q.get('id')}: reuses a decision id")
        bad = [r for r in q.get("relates") or [] if r not in idset]
        need(not bad, f"open {q.get('id')}: relates to unknown decisions {bad}")
    for k in ("resolved", "fold"):
        need(all(isinstance(s, str) for s in d.get(k) or []), f"{k}: a list of strings")
    pivot = meta.get("pivot")
    if pivot:
        need(pivot.get("id") in idset and pivot.get("text"), "meta.pivot: id of a decision, and text")
    return errs


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    errs = validate(d)
    if errs:
        sys.stderr.write("decision data is invalid:\n" + "".join(f"  - {e}\n" for e in errs))
        sys.exit(1)
    for k in ("open", "resolved", "fold"):
        d.setdefault(k, [])
    return d


def enrich(d):
    d = json.loads(json.dumps(d))
    for n, t in enumerate(d["themes"], 1):
        t["slot"] = n
    by = {x["id"]: x for x in d["decisions"]}
    for x in d["decisions"]:
        x["supersedes"], x["amends"] = [], []
    for x in d["decisions"]:
        for s in x["supersededBy"]:
            by[s]["supersedes"].append(x["id"])
        for a in x["amendedBy"]:
            by[a]["amends"].append(x["id"])
    return d


def render_html(d):
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        tpl = f.read()
    m = d["meta"]
    data = json.dumps(enrich(d), ensure_ascii=False).replace("</", "<\\/")
    return (tpl.replace("__TITLE__", html.escape(m["title"]))
               .replace("__H1__", html.escape(m["title"]))
               .replace("__EYEBROW__", html.escape(m.get("eyebrow", "")))
               .replace("__LEDE__", html.escape(m.get("lede", "")))
               .replace("__DATA__", data))


def cell(s):
    return s.replace("|", "\\|").replace("\n", " ")


def wrap(s):
    return textwrap.fill(s, 72, break_on_hyphens=False, break_long_words=False)


def render_md(d, canvas_url):
    e = enrich(d)
    cname = {c["id"]: c["name"] for c in e["components"]}
    m = e["meta"]
    out = ["# Decision log", ""]
    if m.get("lede"):
        out += [wrap(m["lede"]), ""]
    if canvas_url:
        out += [wrap(f"The graph canvas ({canvas_url}) shows the same data: each decision traced to the parts of the system it shapes."), ""]
    out += [wrap("Status: in force; amended (in force, changed by a later decision); superseded (replaced, and kept so it is not reopened); proposed (not yet ruled)."), ""]
    counts = {s: sum(1 for x in e["decisions"] if x["status"] == s) for s in STATUSES}
    out += [", ".join([f"{len(e['decisions'])} decisions"] + [f"{n} {s}" for s, n in counts.items() if n]) + ".", ""]
    for t in e["themes"]:
        rows = [x for x in e["decisions"] if x["theme"] == t["id"]]
        if not rows:
            continue
        out += [f"## {t['name']}", ""]
        if t.get("blurb"):
            out += [wrap(t["blurb"]), ""]
        out += ["| Id | Decision | Status | Shapes | Recorded in |", "|---|---|---|---|---|"]
        for x in rows:
            st = x["status"] + "".join(f" by {', '.join(x[k])}" for k in ("supersededBy", "amendedBy") if x[k])
            shapes = "–" if x["status"] == "superseded" else ", ".join(cname[c] for c in x["impacts"])
            out.append(f"| {x['id']} | **{cell(x['title'])}.** {cell(x['text'])} | {st} | {cell(shapes)} | {cell(x['lands'])} |")
        out.append("")
    if e["open"]:
        out += ["## Open questions", "", "| Id | Question | Recommendation | Relates to |", "|---|---|---|---|"]
        for q in e["open"]:
            out.append(f"| {q['id']} | **{cell(q['title'])}.** {cell(q['text'])} | {cell(q['rec'])} | {', '.join(q.get('relates') or [])} |")
        out.append("")
    if e["resolved"] or e["fold"]:
        out += ["## Checked for contradictions", ""]
        if e["resolved"]:
            out += ["Resolved by supersession:", ""] + [f"- {s}" for s in e["resolved"]] + [""]
        if e["fold"]:
            out += ["Text to fix where the decisions land:", ""] + [f"- {s}" for s in e["fold"]] + [""]
    return "\n".join(out).rstrip() + "\n"


def cmd_extract(path):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    m = re.search(re.escape(DATA_TAG) + r"(.*?)</script>", s, re.S)
    if not m:
        sys.exit("no embedded decision data found (was this canvas built by decision-map?)")
    d = json.loads(m.group(1))
    for t in d.get("themes", []):
        t.pop("slot", None)
    for x in d.get("decisions", []):
        for k in COMPUTED:
            x.pop(k, None)
    print(json.dumps(d, indent=2, ensure_ascii=False))


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "profile":
        cmd_profile()
    elif cmd == "init":
        print(json.dumps(SKELETON, indent=2, ensure_ascii=False))
    elif cmd == "check" and len(rest) == 1:
        d = load(rest[0])
        print(f"ok: {len(d['decisions'])} decisions, {len(d['themes'])} design areas, {len(d['components'])} components")
    elif cmd == "build" and rest:
        opts = {"--html": None, "--md": None, "--canvas-url": ""}
        args = rest[1:]
        while args:
            k = args.pop(0)
            if k not in opts or not args:
                sys.exit(f"build: unknown or incomplete option {k}")
            opts[k] = args.pop(0)
        if not opts["--html"]:
            sys.exit("build: --html OUT is required")
        d = load(rest[0])
        with open(opts["--html"], "w", encoding="utf-8") as f:
            f.write(render_html(d))
        print(f"wrote {opts['--html']}")
        if opts["--md"]:
            with open(opts["--md"], "w", encoding="utf-8") as f:
                f.write(render_md(d, opts["--canvas-url"]))
            print(f"wrote {opts['--md']}")
    elif cmd == "extract" and len(rest) == 1:
        cmd_extract(rest[0])
    else:
        sys.exit(__doc__.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
