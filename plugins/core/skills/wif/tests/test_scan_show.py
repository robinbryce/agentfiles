import contextlib
import json
import os
import shutil
import subprocess
import time
from unittest import mock

from wif import ledger, paths, proc, scan, show
from wif.ledger import Stream
from .base import WifCase


REAL_RUN = proc.run          # captured before any patching


def fake_run(gh_rc=0, gh_out="[]", herdr_out=None):
    """Intercept gh / herdr; pass git through to the real subprocess."""
    real = REAL_RUN
    def _run(args, cwd=None, timeout=20):
        if args[0] == "gh":
            return gh_rc, gh_out
        if args[0] == "herdr":
            return (0, herdr_out) if herdr_out is not None else (1, "")
        return real(args, cwd, timeout)
    return _run


class ScanTests(WifCase):
    def setUp(self):
        super().setUp()
        self.patch_run(fake_run())
        self.cd(self.root)

    def index(self, *args):
        rc, out, err = self.capture(scan.main, list(args))
        self.assertEqual(rc, 0, err)
        return ledger.load_json(self.ledger / "index.json", None)

    def by_task(self, idx):
        return {c["task"]: c for c in idx["containers"]}

    def test_shapes(self):
        self.container("two", repos=("repo-a", "repo-b"))
        (self.cont_root / "two" / "NOTES.md").write_text("x")
        self.container("direct", direct=True)
        (self.cont_root / "empty").mkdir()
        (self.cont_root / "envonly").mkdir(); (self.cont_root / "envonly" / ".envrc").write_text("")
        self.container("my task")
        idx = self.index()
        t = self.by_task(idx)
        self.assertEqual({k: v["shape"] for k, v in t.items()},
                         {"two": "docs", "direct": "direct", "empty": "empty", "envonly": "norepos", "my task": "normal"})
        self.assertEqual(len(t["two"]["repos"]), 2)
        self.assertIn("no-remote", t["two"]["flags"])
        self.assertEqual(t["two"]["ahead"], None)
        self.assertEqual(idx["unbound_memory"], [])
        self.assertGreater(t["empty"]["last_activity_ts"], 0)

    def test_root_that_is_itself_a_repo_does_not_make_containers_direct(self):
        self.git_repo(self.root)
        (self.cont_root / "plain").mkdir(parents=True)
        self.assertEqual(self.by_task(self.index())["plain"]["shape"], "empty")

    def test_remote_fallback_unpushed_unpublished(self):
        c = self.container("pushed"); r = c / "repo-a"
        self.with_remote(r)                                       # upstream set
        self.git(r, "commit", "-q", "--allow-empty", "-m", "local")
        c2 = self.container("nobranch"); r2 = c2 / "repo-a"
        self.with_remote(r2); self.git(r2, "checkout", "-q", "-b", "never-pushed")
        c3 = self.container("originref"); r3 = c3 / "repo-a"
        self.with_remote(r3); self.git(r3, "branch", "--unset-upstream")     # origin/main exists, no @{u}
        t = self.by_task(self.index())
        self.assertEqual(t["pushed"]["ahead"], 1); self.assertIn("unpushed", t["pushed"]["flags"])
        self.assertIsNone(t["nobranch"]["ahead"]); self.assertIn("unpublished", t["nobranch"]["flags"])
        self.assertEqual(t["originref"]["repos"][0]["remote_ref"], "origin/main")

    def test_fresh_refetches_only_the_current_container_with_review_facts_and_feedback_flag(self):
        c = self.container("eng-1"); self.with_remote(c / "repo-a"); self.git(c / "repo-a", "remote", "set-url", "origin", "git@github.com:o/a.git")
        c2 = self.container("eng-2"); self.with_remote(c2 / "repo-a"); self.git(c2 / "repo-a", "remote", "set-url", "origin", "git@github.com:o/b.git")
        for t in ("eng-1", "eng-2"):
            Stream.create(self.ledger / "streams" / f"{t}.md", t, "justgames", "herdr", str(self.cont_root / t))
        calls = []
        def gh(args, cwd=None, timeout=20):
            if args[0] != "gh": return REAL_RUN(args, cwd, timeout)
            calls.append(args[:3])
            if args[1:3] == ["pr", "list"]:
                self.assertIn("reviewDecision,isDraft,updatedAt", args[-1])                  # new fields requested
                n = 11 if cwd and cwd.endswith("eng-1/repo-a") else 22
                return 0, json.dumps([{"number": n, "state": "OPEN", "url": f"https://github.com/o/x/pull/{n}", "title": "t", "reviewDecision": "CHANGES_REQUESTED", "isDraft": False}])
            if args[1:3] == ["api", "graphql"]:
                return 0, json.dumps({"data": {"repository": {"pullRequest": {
                    "reviewThreads": {"nodes": [{"isResolved": False, "isOutdated": False, "comments": {"nodes": [{"createdAt": "2026-10-25T10:00:00Z", "author": {"login": "bob"}}]}},
                                                {"isResolved": True, "isOutdated": False, "comments": {"nodes": [{"createdAt": "2026-10-24T09:00:00Z", "author": {"login": "bugbot"}}]}}]},
                    "latestReviews": {"nodes": [{"state": "CHANGES_REQUESTED", "submittedAt": "2026-10-25T11:00:00Z", "author": {"login": "bob"}}]}}}}})
            return 1, ""
        with mock.patch("wif.proc.run", gh):
            t = self.by_task(self.index("--prs"))                           # scope-wide: fields cached, no graphql
        self.assertFalse(any(c_[1:3] == ["api", "graphql"] for c_ in calls))
        self.assertEqual(t["eng-1"]["prs"][0]["reviewDecision"], "CHANGES_REQUESTED")
        self.assertIn("feedback", t["eng-1"]["flags"])                       # CHANGES_REQUESTED alone raises the flag
        self.assertNotIn("unresolved", t["eng-1"]["prs"][0])
        calls.clear()
        with contextlib.chdir(c), mock.patch("wif.proc.run", gh):
            rc, _, err = self.capture(scan.main, ["--fresh"])                 # inside eng-1: TTL bypassed there only, graphql there only
            self.assertEqual(rc, 0, err)
        lists = [c_ for c_ in calls if c_[1:3] == ["pr", "list"]]; gql = [c_ for c_ in calls if c_[1:3] == ["api", "graphql"]]
        self.assertEqual((len(lists), len(gql)), (1, 1))
        t = self.by_task(ledger.load_json(self.ledger / "index.json", {}))
        p1 = t["eng-1"]["prs"][0]
        self.assertEqual((p1["unresolved"], p1["lastReviewAt"], p1["requestedChangesBy"]), (1, "2026-10-25T11:00:00Z", ["bob"]))
        self.assertNotIn("unresolved", t["eng-2"]["prs"][0])                  # the other container came from its cache
        with contextlib.chdir(self.root):                                     # served scope, but not a container
            rc, _, err = self.capture(scan.main, ["--fresh"])
            self.assertEqual(rc, 1); self.assertIn("inside a herdr container", err)

    def test_landed_proposal_requires_merged_prs_clean_and_known_remote(self):
        c = self.container("eng-1"); r = c / "repo-a"; self.with_remote(r)
        Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(c))
        merged = json.dumps([{"number": 1, "state": "MERGED"}])
        with mock.patch("wif.proc.run", fake_run(gh_out=merged)):
            t = self.by_task(self.index("--prs"))
        self.assertIn("landed?", t["eng-1"]["flags"])
        self.assertTrue((self.ledger / "cache" / "prs" / "eng-1.json").exists())
        # dirty -> no proposal; cache still used without --prs
        (r / "f").write_text("x"); self.git(r, "add", "f")
        t = self.by_task(self.index())
        self.assertNotIn("landed?", t["eng-1"]["flags"]); self.assertIn("dirty", t["eng-1"]["flags"])
        self.assertEqual(t["eng-1"]["prs"][0]["state"], "MERGED")

    def test_gh_failure_is_reported_not_cached(self):
        c = self.container("eng-2"); self.with_remote(c / "repo-a")
        with mock.patch("wif.proc.run", fake_run(gh_rc=1)):
            idx = self.index("--prs")
        self.assertEqual(idx["pr_failures"], ["eng-2/repo-a"])
        self.assertFalse((self.ledger / "cache" / "prs" / "eng-2.json").exists())
        with mock.patch("wif.proc.run", fake_run(gh_out="{not json")):
            idx = self.index("--prs")
        self.assertEqual(idx["pr_failures"], ["eng-2/repo-a"])

    def test_stale_corrupt_pr_cache_is_tolerated(self):
        self.container("eng-3")
        cf = self.ledger / "cache" / "prs" / "eng-3.json"; cf.parent.mkdir(parents=True)
        cf.write_text("{bad"); os.utime(cf, (0, 0))
        self.assertIsNone(self.by_task(self.index())["eng-3"]["prs"])

    def test_memory_binding_longest_prefix_and_unbound(self):
        self.container("eng-2437"); self.container("eng-2437-impl")
        for k in ("eng-2437", "eng-2437-repo-a", "eng-2437-impl-repo-a-deep", "eng-2437-impl-extra", "orphan-x"):
            self.memory_dir(k)
        idx = self.index(); t = self.by_task(idx)
        self.assertEqual(len(t["eng-2437"]["memory"]), 2)
        self.assertEqual(len(t["eng-2437-impl"]["memory"]), 2)
        self.assertEqual([m["task"] for m in idx["unbound_memory"]], ["orphan-x"])

    def test_repo_stream_is_a_container_and_missing_backing_is_orphan(self):
        r = self.git_repo(self.root / "flip-oracle")
        Stream.create(self.ledger / "streams" / "flip-oracle--main.md", "flip-oracle--main", "justgames", "repo", str(r))
        Stream.create(self.ledger / "streams" / "gone.md", "gone", "justgames", "herdr", "/nowhere")
        idx = self.index(); t = self.by_task(idx)
        self.assertEqual(t["flip-oracle--main"]["shape"], "repo")
        self.assertEqual(idx["orphan_streams"], ["gone"])

    def test_herdr_join_stale_sessions_prune_and_flags(self):
        c = self.container("eng-5")
        subprocess.run(["git", "-C", str(c / "repo-a"), "commit", "-q", "--allow-empty", "-m", "old"], check=True,
                       env={**os.environ, "GIT_COMMITTER_DATE": "2020-01-01T00:00:00", "GIT_AUTHOR_DATE": "2020-01-01T00:00:00"})
        ws = json.dumps({"result": {"workspaces": [{"label": "ENG-5", "agent_status": "idle"}]}})
        s = Stream.create(self.ledger / "streams" / "eng-5.md", "eng-5", "justgames", "herdr", str(c))
        s.fm["status"] = "weird"; s.fm["updated"] = "2020-01-02"; s.body += "x\n" * 130; s.save()
        old = ledger.session_ensure(self.ledger, "old", "eng-5", "justgames"); old["ended"] = "2020-01-01T00:00:00Z"; ledger.session_save(self.ledger, old)
        f = ledger.session_file(self.ledger, "old"); os.utime(f, (0, 0))
        ledger.dump_json(ledger.ctx_file(self.ledger, "ghost"), {}); os.utime(ledger.ctx_file(self.ledger, "ghost"), (0, 0))
        with mock.patch("wif.proc.run", fake_run(herdr_out=ws)):
            idx = self.index()
        t = self.by_task(idx)["eng-5"]
        self.assertEqual(t["herdr"]["agent_status"], "idle")
        for fl in ("stale", "over-cap", "bad-status"):
            self.assertIn(fl, t["flags"])
        self.assertEqual(idx["pruned_sessions"], 2)
        self.assertFalse(f.exists())

    def test_null_session_and_unreadable_stream_tolerated(self):
        self.container("eng-6")
        (self.ledger / "sessions").mkdir(parents=True); ledger.session_file(self.ledger, "x").write_text("null")
        (self.ledger / "streams").mkdir(parents=True); (self.ledger / "streams" / "junk.md").write_text("no frontmatter")
        self.assertEqual(len(self.index()["containers"]), 1)

    def test_sanitizer_matches_claude_code_and_binds_odd_names(self):
        self.assertEqual(scan.sanitize("/a/b.c_d e"), "-a-b-c-d-e")
        self.container("eng_2407 x"); self.container("eng")
        self.memory_dir("eng-2407-x-repo-a"); self.memory_dir("eng-repo-a")
        t = self.by_task(self.index())
        self.assertEqual(len(t["eng_2407 x"]["memory"]), 1)
        self.assertEqual(len(t["eng"]["memory"]), 1)

    def test_vanished_container_mid_scan_is_tolerated(self):
        self.container("gone"); self.container("stays")
        real_facts = scan.git_facts
        def facts(repo):
            if repo.name == "repo-a" and "gone" in str(repo):
                shutil.rmtree(self.cont_root / "gone")
            return real_facts(repo)
        with mock.patch("wif.scan.git_facts", facts):
            idx = self.index()
        self.assertIn("stays", self.by_task(idx))

    def test_scope_flag_served_path(self):
        self.container("eng-8")
        rc, out, err = self.capture(scan.main, ["--scope", "justgames", "--quiet"])
        self.assertEqual(rc, 0); self.assertTrue((self.ledger / "index.json").exists())

    def test_scope_flag_validation_and_unserved(self):
        rc, out, err = self.capture(scan.main, ["--scope", "bogus"])
        self.assertEqual(rc, 1); self.assertIn("unknown scope", err)
        rc, out, err = self.capture(scan.main, ["--scope", "personal"])
        self.assertEqual(rc, 0); self.assertIn("not served", err)
        self.assertFalse((self.cfg / "wif" / "personal").exists())

    def test_summary_line_and_json(self):
        self.container("eng-7")
        rc, out, _ = self.capture(scan.main, [])
        self.assertIn("1 containers (0 tracked)", out)
        rc, out, _ = self.capture(scan.main, ["--json"])
        self.assertEqual(json.loads(out)["scope"], "justgames")


class ShowTests(WifCase):
    def setUp(self):
        super().setUp()
        self.patch_run(fake_run())
        self.c = self.container("eng-1")
        self.cd(self.c)

    def scan(self):
        self.capture(scan.main, ["--quiet"])

    def show(self, *args):
        rc, out, _ = self.capture(show.main, list(args))
        self.assertEqual(rc, 0)
        return out.rstrip("\n").split("\n")

    def test_ls_lists_containers_streams_and_archive(self):
        self.container("eng-2")
        Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c)).save()
        Stream.create(self.ledger / "streams" / "gone.md", "gone", "justgames", "herdr", str(self.cont_root / "gone")).save()
        a = Stream.create(self.ledger / "archive" / "old.md", "old", "justgames", "herdr", str(self.cont_root / "old"))
        a.set("status", "closed"); a.set("goal", "OG"); a.save()
        self.scan()
        rc, out, _ = self.capture(show.ls, ["--json"])
        rows = {r["id"]: r for r in json.loads(out)}
        self.assertEqual({k: (r["status"], r["backing"]) for k, r in rows.items()},
                         {"eng-1": ("active", "present"), "gone": ("active", "missing"), "eng-2": ("untracked", "present")})
        rc, out, _ = self.capture(show.ls, ["--archived", "--json"])
        self.assertEqual([r for r in json.loads(out) if r["id"] == "old"][0]["goal"], "OG")
        rc, out, _ = self.capture(show.ls, [])
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("id")); self.assertTrue(lines[-1].startswith("eng-2"))
        self.assertIn(".worktrees-herdr/eng-1", out); self.assertNotIn(str(self.root) + "/", out)

    def test_no_index_and_truncated_index(self):
        self.assertIn("run `wif scan`", self.show()[0])
        (self.ledger).mkdir(parents=True, exist_ok=True); (self.ledger / "index.json").write_text('{"cont')
        self.assertIn("no usable index", self.show()[0])

    def test_header_current_stream_session_ctx_due_candidates(self):
        s = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c))
        s.set("goal", "G"); s.set("next", "N"); s.set("position", "P")
        s.section_append("Notes", "- [reminder due=2000-01-01] 2000-01-01 overdue ] with bracket")
        s.section_append("Notes", "- [reminder due=2999-01-01] 2000-01-01 future")
        s.section_append("Notes", "- [tangent] 2000-01-01 side idea"); s.save()
        sess = ledger.session_ensure(self.ledger, "s1", "eng-1", "justgames"); sess["goal"] = "SG"; sess["ring"] = [{"intent": "I"}]; ledger.session_save(self.ledger, sess)
        ledger.dump_json(ledger.ctx_file(self.ledger, "s1"), {"used_pct": 42})
        self.scan()
        lines = self.show("--session", "s1")
        self.assertTrue(lines[1].startswith("▶ eng-1  active"))
        self.assertEqual(lines[2], "  goal: G")
        self.assertIn("session: SG   ~ I  ctx 42%", lines[4])
        self.assertIn("due:", lines); self.assertTrue(any("overdue ] with bracket" in l for l in lines))
        self.assertFalse(any("future" in l for l in lines))
        self.assertTrue(any(l.startswith("candidates (1)") for l in lines))
        self.assertTrue(any("← eng-1: 2000-01-01 side idea" in l for l in lines))
        self.assertIn("  last → task: side-idea (derived; pin with wif tangent --as <task> --for \"<substring>\")", lines)
        self.assertTrue(any(l.startswith("    herdr-task side-idea repo-a && wif adopt side-idea -g '") for l in lines), lines)
        brief = self.show("--brief", "--session", "s1")
        self.assertIn("due:", brief); self.assertFalse(any(l.startswith("streams") for l in brief))

    def test_last_tangent_newest_date_current_stream_tiebreak_and_container_states(self):
        c2 = self.container("eng-2")
        s1 = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c))
        s2 = Stream.create(self.ledger / "streams" / "eng-2.md", "eng-2", "justgames", "herdr", str(c2))
        s2.section_append("Notes", "- [tangent as=newer-one] 2001-01-01 newer on the other stream"); s2.save()
        s1.section_append("Notes", "- [tangent as=older-one] 2000-01-01 older here"); s1.save()
        self.scan()
        lines = self.show()
        self.assertIn("  last → task: newer-one", lines)                      # newest date wins over current stream
        self.assertTrue(any(l.startswith("    herdr-task newer-one ") and "&& wif adopt newer-one " in l for l in lines), lines)
        s1.section_append("Notes", "- [tangent as=same-day] 2001-01-01 same day, current stream"); s1.save()
        self.scan()
        self.assertIn("  last → task: same-day", self.show())                # tie → current stream
        # container for the task already there: untracked, then tracked
        self.container("same-day")
        self.scan()
        self.assertIn("    wif adopt same-day   (container exists, untracked)", self.show())
        Stream.create(self.ledger / "streams" / "same-day.md", "same-day", "justgames", "herdr", str(self.cont_root / "same-day"))
        self.scan()
        self.assertTrue(any(l.startswith("    wif adopt same-day   (already a stream (active); re-adopting clears this note)") for l in self.show()))

    def test_refs_md_lists_reference_lines_under_items_and_plain_is_unchanged(self):
        self.git(self.c / "repo-a", "remote", "add", "origin", "git@github.com:o/repo-a.git")
        s1 = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c))
        s1.set("issue", "ENG-1"); s1.set("goal", "fewer writes per ENG-1"); s1.set("next", "merge #1669 and #1672"); s1.set("position", "#1669 awaiting")
        s1.section_append("Notes", "- [reminder due=2000-01-01] 2000-01-01 ping on #5")
        s1.section_append("Notes", "- [tangent as=kid issue=ENG-9] 2000-01-02 split #6 out"); s1.save()
        c2 = self.container("eng-2"); s2 = Stream.create(self.ledger / "streams" / "eng-2.md", "eng-2", "justgames", "herdr", str(c2))
        s2.set("next", "a long next whose reference sits past the forty character trim #3 here"); s2.save()
        ledger.dump_json(self.ledger / "cache" / "prs" / "eng-1.json", [{"number": 1669, "state": "OPEN", "title": "odds-writer: mirror the odds book", "url": "https://github.com/o/repo-a/pull/1669", "repo": "repo-a"}])
        self.scan()
        plain = self.show()
        self.assertTrue(plain[1].startswith("▶ eng-1  active") and plain[1].endswith("  · issue ENG-1"), plain[1])
        self.assertFalse(any("](http" in l for l in plain))
        md = self.show("--refs", "md")
        P = "https://github.com/o/repo-a/pull"
        self.assertFalse(any("](http" in l for l in md if not l.startswith("    [")))      # never inline: links only on Reference lines
        self.assertTrue(md[1].startswith("▶ eng-1  active") and "issue" not in md[1], md[1])   # marker moved to a Reference line
        self.assertIn("  goal: fewer writes per ENG-1", md)
        i = md.index("  next: merge #1669 and #1672   position: #1669 awaiting")
        self.assertEqual(md[i + 1:i + 4], ["    [ENG-1](https://linear.app/justgames/issue/ENG-1) this stream",
                                           f"    [#1669]({P}/1669) OPEN · odds-writer: mirror the odds book",
                                           f"    [#1672]({P}/1672)"])                     # goal first (own issue), then next; #1669 once; no cache -> link only
        j = [k for k, l in enumerate(md) if l.startswith("  ! eng-1: ")][0]
        self.assertEqual(md[j + 1], f"    [#5]({P}/5)")
        j = [k for k, l in enumerate(md) if l.startswith("  ← eng-1: [ENG-9] ")][0]
        self.assertEqual(md[j + 1:j + 3], [f"    [#6]({P}/6)", "    [ENG-9](https://linear.app/justgames/issue/ENG-9)"])
        row = [k for k, l in enumerate(md) if l.startswith("  eng-2 ")][0]
        self.assertNotIn("#3", md[row])                                                   # trimmed out of the 40-char cell
        self.assertFalse(md[row + 1].startswith("    ["))                                 # eng-2's repo has no origin: unresolvable -> no Reference line
        self.git(c2 / "repo-a", "remote", "add", "origin", "https://github.com/o/two.git"); self.scan()
        plain = self.show(); md = self.show("--refs", "md"); row = [k for k, l in enumerate(md) if l.startswith("  eng-2 ")][0]
        self.assertEqual(md[row + 1], "    [#3](https://github.com/o/two/pull/3)")        # hidden by the trim, still listed
        with mock.patch.dict(os.environ, {"WIF_REFS": "md"}):
            self.assertEqual(self.show(), md)                                             # env default
            self.assertEqual(self.show("--refs", "plain"), plain)                         # flag beats env
        rc, out, _ = self.capture(show.main, ["--refs", "html"])
        self.assertEqual(rc, 2); self.assertIn("--refs must be md or plain", out)
        brief = self.show("--brief", "--refs", "md")
        self.assertIn("    [ENG-1](https://linear.app/justgames/issue/ENG-1) this stream", brief)   # --brief keeps the header's Reference lines
        self.assertFalse(any(l.startswith("streams") for l in brief))

    def test_owner_prefix_dropped_from_next_on_display_only(self):
        s1 = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c))
        s1.set("next", "Robin: merge #1665 when S1 review closes"); s1.save()
        c2 = self.container("eng-2"); s2 = Stream.create(self.ledger / "streams" / "eng-2.md", "eng-2", "justgames", "herdr", str(c2))
        s2.set("next", "robin:  review first"); s2.save()
        c3 = self.container("eng-3"); s3 = Stream.create(self.ledger / "streams" / "eng-3.md", "eng-3", "justgames", "herdr", str(c3))
        s3.set("next", "owner: re-approve; Robin: then merge"); s3.save()
        self.scan()
        out = self.show()
        self.assertIn("  next: merge #1665 when S1 review closes   position: -", out)              # header: prefix dropped
        self.assertTrue(any(l.startswith("  eng-2 ") and " review first " in l and "robin" not in l for l in out), out)   # case-insensitive, extra space
        self.assertTrue(any(l.startswith("  eng-3 ") and "owner: re-approve; Robin: then merge" in l for l in out), out)  # only a leading prefix
        self.assertEqual(Stream.load(self.ledger / "streams" / "eng-1.md").get("next"), "Robin: merge #1665 when S1 review closes")   # Ledger untouched
        with mock.patch.dict(os.environ, {"WIF_OWNER": "owner"}):
            out = self.show()
            self.assertTrue(any(l.startswith("  eng-3 ") and "re-approve; Robin: then merge" in l and "owner:" not in l for l in out), out)
            self.assertIn("  next: Robin: merge #1665 when S1 review closes   position: -", out)
        s1.set("next", ": odd leading colon"); s1.save(); self.scan()
        with mock.patch.dict(os.environ, {"WIF_OWNER": ""}):
            self.assertIn("  next: : odd leading colon   position: -", self.show())      # empty owner strips nothing

    def test_review_state_in_changes_signature_and_reference_note(self):
        self.git(self.c / "repo-a", "remote", "add", "origin", "git@github.com:o/r.git")
        s1 = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c)); s1.set("next", "address #9"); s1.save()
        cf = self.ledger / "cache" / "prs" / "eng-1.json"
        pr = {"number": 9, "state": "OPEN", "title": "the change", "url": "https://github.com/o/r/pull/9", "repo": "repo-a", "reviewDecision": "CHANGES_REQUESTED", "unresolved": 2, "lastReviewAt": "T1"}
        ledger.dump_json(cf, [pr]); self.scan()
        self.assertIn("    [#9](https://github.com/o/r/pull/9) OPEN · CHANGES_REQUESTED · 2 open threads · the change", self.show("--refs", "md"))
        self.show("--changes")                                                   # baseline
        self.assertEqual(self.show("--changes")[-1], "no changes")
        pr["unresolved"] = 1; pr["lastReviewAt"] = "T2"; ledger.dump_json(cf, [pr]); self.scan()
        out = self.show("--changes")
        self.assertTrue(any(l.startswith("changed (1)") for l in out), out)       # a resolved thread is a change
        pr["unresolved"] = 0; pr["reviewDecision"] = "APPROVED"; ledger.dump_json(cf, [pr]); self.scan()
        self.assertIn("    [#9](https://github.com/o/r/pull/9) OPEN · the change", self.show("--refs", "md"))
        t = {c["task"]: c for c in ledger.load_json(self.ledger / "index.json", {})["containers"]}
        self.assertNotIn("feedback", t["eng-1"]["flags"])

    def test_reference_lines_count_toward_the_budget(self):
        self.git(self.c / "repo-a", "remote", "add", "origin", "git@github.com:o/r.git")
        for i in range(30):
            c = self.container(f"t{i:02d}"); self.git(c / "repo-a", "remote", "add", "origin", "git@github.com:o/r.git")
            st = Stream.create(self.ledger / "streams" / f"t{i:02d}.md", f"t{i:02d}", "justgames", "herdr", str(c)); st.set("next", f"merge #{i} and #{i + 100}"); st.save()
        self.scan()
        plain = self.show(); md = self.show("--refs", "md")
        rows = lambda lines: len([l for l in lines if l.startswith("  t")])
        self.assertEqual(rows(plain), 30)                                                 # plain: every row fits the budget
        self.assertLess(rows(md), 30)                                                     # md: each shown row costs 3 lines
        self.assertTrue(any("more (wif show --all)" in l for l in md))
        self.assertLessEqual(len(md), 42)                                                 # budget held (same header slack as today)
        self.assertEqual(len([l for l in self.show("--refs", "md", "--all") if l.startswith("    [#")]), 60)   # --all lifts it

    def test_scan_prs_resolves_cited_numbers_across_origins_exactly(self):
        c = self.container("eng-1", repos=("repo-a", "repo-b")); self.with_remote(c / "repo-a"); self.with_remote(c / "repo-b")
        self.git(c / "repo-a", "remote", "set-url", "origin", "git@github.com:o/a.git"); self.git(c / "repo-b", "remote", "set-url", "origin", "git@github.com:o/b.git")
        s = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(c))
        s.set("next", "merge #7 and #8; o/x#9 is named already"); s.section_append("Now", "- done: #10 landed in b"); s.save()
        def gh(args, cwd=None, timeout=20):
            if args[0] != "gh": return REAL_RUN(args, cwd, timeout)
            if args[1:3] == ["pr", "list"]: return 0, json.dumps([{"number": 1, "state": "OPEN", "url": "https://github.com/o/a/pull/1"}])
            n, slug = args[3], args[5]
            table = {("7", "o/a"): "OPEN", ("8", "o/a"): "MERGED", ("8", "o/b"): "MERGED", ("10", "o/b"): "MERGED"}   # 8 exists in both -> ambiguous
            if (n, slug) in table: return 0, json.dumps({"number": int(n), "state": table[(n, slug)], "url": f"https://github.com/{slug}/pull/{n}"})
            return 1, "GraphQL: Could not resolve to a PullRequest"
        with mock.patch("wif.proc.run", gh):
            rc, _, err = self.capture(scan.main, ["--prs"]); self.assertEqual(rc, 0, err)
        t = {c["task"]: c for c in ledger.load_json(self.ledger / "index.json", {})["containers"]}
        prs = {p["number"]: p for p in t["eng-1"]["prs"]}
        self.assertEqual(sorted(prs), [1, 7, 10])                                  # 8 ambiguous -> omitted; 9 named its repo -> not looked up
        self.assertEqual((prs[7]["url"], prs[7]["cited"], prs[10]["repo"]), ("https://github.com/o/a/pull/7", True, "repo-b"))
        self.assertNotIn("cited", prs[1])
        self.assertNotIn("landed?", t["eng-1"]["flags"])                             # own PR #1 is OPEN; cited MERGED #10 does not count
        md = self.show("--refs", "md")                                             # eng-1 is the current stream: header block
        i = md.index("  next: merge #7 and #8; o/x#9 is named already   position: -")
        self.assertEqual(md[i + 1:i + 3], ["    [#7](https://github.com/o/a/pull/7) OPEN", "    [o/x#9](https://github.com/o/x/pull/9)"])   # #8 ambiguous: no line

    def test_budget_cuts_streams_table_and_all_lifts_it(self):
        for i in range(45):
            c = self.container(f"t{i:02d}")
            s = Stream.create(self.ledger / "streams" / f"t{i:02d}.md", f"t{i:02d}", "justgames", "herdr", str(c))
            if i < 6:
                s.section_append("Notes", "- [reminder due=2000-01-01] 2000-01-01 due"); s.section_append("Notes", "- [tangent] 2000-01-01 t"); s.save()
        for i in range(10):
            self.container(f"u{i}")
        self.memory_dir("zzz-unbound")
        self.scan()
        lines = self.show()
        self.assertEqual(len(lines), 40)
        cut = [i for i, l in enumerate(lines) if l.startswith("  … ") and "more (wif show --all)" in l]
        streams_hdr = next(i for i, l in enumerate(lines) if l.startswith("streams ("))
        untracked_hdr = next(i for i, l in enumerate(lines) if l.startswith("untracked containers"))
        self.assertTrue(any(streams_hdr < i < untracked_hdr for i in cut), "streams table was not the section cut")
        full = self.show("--all")
        self.assertGreater(len(full), 40)
        self.assertFalse(any("more (wif show --all)" in l for l in full))
        self.assertTrue(any(l.startswith("  t44 ") for l in full))

    def test_changes_over_fifteen_and_header_extras(self):
        for i in range(18):
            self.container(f"c{i:02d}")
        self.scan(); self.show("--changes")
        for i in range(18):
            r = self.cont_root / f"c{i:02d}" / "repo-a"; (r / "f").write_text("x"); self.git(r, "add", "f")
        self.scan()
        lines = self.show("--changes")
        self.assertTrue(any(l.startswith("changed (18):") for l in lines)); self.assertIn("  … 3 more", lines)
        idx = ledger.load_json(self.ledger / "index.json", {}); idx["pr_failures"] = ["a/b"]; ledger.dump_json(self.ledger / "index.json", idx)
        self.assertIn("gh failed ×1", self.show()[0])

    def test_changes_baseline_nochange_changed_removed(self):
        self.container("other"); self.scan()
        self.assertIn("baseline recorded", self.show("--changes")[-1])
        self.assertEqual(self.show("--changes")[-1], "no changes")
        (self.c / "repo-a" / "f").write_text("x"); self.git(self.c / "repo-a", "add", "f"); self.scan()
        lines = self.show("--changes")
        self.assertTrue(any(l.startswith("changed (1):") for l in lines)); self.assertTrue(any("eng-1" in l and "dirty" in l for l in lines))
        shutil.rmtree(self.cont_root / "other"); self.scan()
        self.assertTrue(any(l.startswith("removed (1): other") for l in self.show("--changes")))

    def test_due_reminder_does_not_block_no_changes(self):
        s = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c))
        s.section_append("Notes", "- [reminder due=2000-01-01] 2000-01-01 x"); s.save(); self.scan()
        self.show("--changes")
        lines = self.show("--changes")
        self.assertEqual(lines[-1], "no changes"); self.assertIn("due:", lines)

    def test_closed_current_and_unserved(self):
        (self.ledger / "archive").mkdir(parents=True); (self.ledger / "archive" / "eng-1.md").write_text("---\n---\n")
        self.scan()
        self.assertTrue(self.show()[1].startswith("▶ eng-1  closed"))
        with contextlib.chdir(self.home):
            self.assertIn("not served", self.show()[0])

    def test_json_passthrough(self):
        self.scan()
        rc, out, _ = self.capture(show.main, ["--json"])
        self.assertIn("containers", json.loads(out))
