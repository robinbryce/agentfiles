import contextlib
import json
import os
import time
from unittest import mock

from wif import ledger, paths, proc, scan, show
from wif.ledger import Stream
from .base import WifCase


def fake_run(gh_rc=0, gh_out="[]", herdr_out=None):
    """Intercept gh / herdr; pass git through to the real subprocess."""
    real = proc.run
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
        p = mock.patch("wif.proc.run", fake_run()); p.start(); self.addCleanup(p.stop)
        self._cd = contextlib.chdir(self.root); self._cd.__enter__()
        self.addCleanup(self._cd.__exit__, None, None, None)

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
        self.assertEqual(t["empty"]["last_activity_ts"] > 0, True)

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
        import subprocess
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
        p = mock.patch("wif.proc.run", fake_run()); p.start(); self.addCleanup(p.stop)
        self.c = self.container("eng-1")
        self._cd = contextlib.chdir(self.c); self._cd.__enter__()
        self.addCleanup(self._cd.__exit__, None, None, None)

    def scan(self):
        self.capture(scan.main, ["--quiet"])

    def show(self, *args):
        rc, out, _ = self.capture(show.main, list(args))
        self.assertEqual(rc, 0)
        return out.rstrip("\n").split("\n")

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
        brief = self.show("--brief", "--session", "s1")
        self.assertIn("due:", brief); self.assertFalse(any(l.startswith("streams") for l in brief))

    def test_budget_and_overflow_lines(self):
        for i in range(30):
            c = self.container(f"t{i:02d}")
            if i < 20:
                Stream.create(self.ledger / "streams" / f"t{i:02d}.md", f"t{i:02d}", "justgames", "herdr", str(c))
        self.scan()
        lines = self.show()
        self.assertLessEqual(len(lines), 40)
        self.assertTrue(any("more (wif show --all)" in l for l in lines))
        full = self.show("--all")
        self.assertGreater(len(full), len(lines))
        self.assertFalse(any("more (wif show --all)" in l for l in full))
        self.assertTrue(any(l.startswith("  t19 ") for l in full))

    def test_changes_baseline_nochange_changed_removed(self):
        self.container("other"); self.scan()
        self.assertIn("baseline recorded", self.show("--changes")[-1])
        self.assertEqual(self.show("--changes")[-1], "no changes")
        (self.c / "repo-a" / "f").write_text("x"); self.git(self.c / "repo-a", "add", "f"); self.scan()
        lines = self.show("--changes")
        self.assertTrue(any(l.startswith("changed (1):") for l in lines)); self.assertTrue(any("eng-1" in l and "dirty" in l for l in lines))
        import shutil; shutil.rmtree(self.cont_root / "other"); self.scan()
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
