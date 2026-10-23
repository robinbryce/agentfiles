import contextlib
import json
import os
from unittest import mock

from wif import commands, ledger
from wif.commands import WifError
from wif.ledger import Stream
from .base import WifCase


class CommandTests(WifCase):
    def setUp(self):
        super().setUp()
        self.c = self.container("eng-1")
        self.cd(self.c)

    def stream(self):
        return Stream.load(self.ledger / "streams" / "eng-1.md")

    # ---- where
    def test_where_text_and_json(self):
        rc, out, _ = self.capture(commands.where, [])
        self.assertIn("backing: herdr eng-1", out); self.assertIn("stream:  untracked", out)
        rc, out, _ = self.capture(commands.where, ["--json", str(self.home)])
        self.assertEqual(json.loads(out)["kind"], "none")

    # ---- adopt
    def test_adopt_creates_then_only_changes_given_fields(self):
        self.capture(commands.adopt, [".", "-s", "parked", "-g", "goal", "-p", "ENG-1"])
        self.capture(commands.adopt, ["eng-1", "-n", "next"])
        s = self.stream()
        self.assertEqual((s.get("status"), s.get("goal"), s.get("parent"), s.get("next")), ("parked", "goal", "ENG-1", "next"))

    def test_adopt_by_task_name_path_and_errors(self):
        self.container("eng-9")
        rc, out, _ = self.capture(commands.adopt, ["eng-9"])
        self.assertTrue(out.strip().endswith("eng-9.md"))
        rc, out, _ = self.capture(commands.adopt, [str(self.cont_root / "eng-9"), "-s", "blocked"])
        self.assertEqual(Stream.load(self.ledger / "streams" / "eng-9.md").get("status"), "blocked")
        with self.assertRaises(WifError): commands.adopt(["nope"])
        with self.assertRaises(WifError): commands.adopt([".", "-s", "bogus"])
        with self.assertRaises(WifError): commands.adopt([".", "--scope", "bogus"])

    def test_adopt_reopens_archive_and_closed_archives(self):
        self.capture(commands.adopt, ["."])
        self.capture(commands.mark, ["-s", "closed"])
        self.assertTrue((self.ledger / "archive" / "eng-1.md").exists())
        rc, out, _ = self.capture(commands.adopt, ["."])
        self.assertIn("re-opened", out)
        self.assertEqual(self.stream().get("status"), "active")
        self.capture(commands.adopt, [".", "-s", "closed"])
        self.assertFalse((self.ledger / "streams" / "eng-1.md").exists())

    def test_adopt_plain_repo_then_binds(self):
        r = self.git_repo(self.root / "flip-oracle")
        with contextlib.chdir(r):
            rc, out, _ = self.capture(commands.adopt, [".", "-g", "g"])
            self.assertTrue(out.strip().endswith("flip-oracle--main.md"))
            self.assertIn("repo:", Stream.load(self.ledger / "streams" / "flip-oracle--main.md").get("backing"))

    def test_unserved_scope_refuses(self):
        foreign = self.git_repo(self.home / "Dev/personal/foo")
        with contextlib.chdir(foreign):
            with self.assertRaises(WifError): commands.adopt(["."])
            with self.assertRaises(WifError): commands.mark(["-n", "x"])
        self.assertFalse((self.cfg / "wif" / "personal").exists())

    # ---- mark
    def test_mark_stream_fields_and_done(self):
        rc, out, _ = self.capture(commands.mark, ["-p", "slice 2/3", "-n", "nxt", "-s", "blocked", "--done", "thing"])
        s = self.stream()
        self.assertEqual((s.get("position"), s.get("next"), s.get("status")), ("slice 2/3", "nxt", "blocked"))
        self.assertEqual(s.section("Now"), [f"- done {ledger.today()}: thing"])
        self.assertIn("status=blocked", out)

    def test_mark_goal_and_intent_use_session(self):
        self.capture(commands.mark, ["-g", "session goal", "--session", "s1"])
        self.assertEqual(ledger.load_json(ledger.session_file(self.ledger, "s1"), {})["goal"], "session goal")
        self.capture(commands.mark, ["-i", "first intent", "--session", "s1"])
        ring = ledger.load_json(ledger.session_file(self.ledger, "s1"), {})["ring"]
        self.assertEqual((ring[-1]["intent"], ring[-1]["pinned"]), ("first intent", True))
        with mock.patch.dict(os.environ, {"CLAUDE_SESSION_ID": "s2"}):
            self.capture(commands.mark, ["-g", "g2"])
        self.assertEqual(ledger.load_json(ledger.session_file(self.ledger, "s2"), {})["goal"], "g2")

    def test_mark_falls_back_to_last_session_then_errors(self):
        self.capture(commands.adopt, ["."])
        s = self.stream(); s.set("last_session", "ls", touch=False); s.save()
        self.capture(commands.mark, ["-g", "via last"])
        self.assertEqual(ledger.load_json(ledger.session_file(self.ledger, "ls"), {})["goal"], "via last")
        s.set("last_session", "", touch=False); s.save()
        with self.assertRaises(WifError): commands.mark(["-g", "x"])
        with self.assertRaises(WifError): commands.mark(["--session", "../x", "-g", "y"])
        with self.assertRaises(WifError): commands.mark(["--bogus"])

    def test_mark_on_closed_refuses(self):
        self.capture(commands.mark, ["-s", "closed"])
        with self.assertRaises(WifError): commands.mark(["-n", "x"])
        with self.assertRaises(WifError): commands.note(["x"])

    def test_mark_by_stream_id_from_anywhere(self):
        self.capture(commands.adopt, ["."])
        gone = self.container("eng-2"); self.capture(commands.adopt, ["eng-2"])
        import shutil; shutil.rmtree(gone)                        # backing missing
        with contextlib.chdir(self.home):
            with self.assertRaises(WifError): commands.mark(["-n", "x"])       # no backing at ~
            self.capture(commands.mark, ["--stream", "eng-1", "--scope", "justgames", "-n", "far"])
            self.assertEqual(self.stream().get("next"), "far")
            rc, out, _ = self.capture(commands.mark, ["--stream", "eng-2", "--scope", "justgames", "-s", "closed"])
            self.assertIn("archived", out)
            self.assertTrue((self.ledger / "archive" / "eng-2.md").exists())
            with self.assertRaises(WifError): commands.mark(["--stream", "eng-2", "--scope", "justgames", "-n", "x"])
            with self.assertRaises(WifError): commands.mark(["--stream", "nope", "--scope", "justgames", "-n", "x"])
            with self.assertRaises(WifError): commands.mark(["--stream", "../x", "--scope", "justgames"])
            with self.assertRaises(WifError): commands.mark(["--stream", "eng-1", "--scope", "bogus"])
            with self.assertRaises(WifError): commands.mark(["--scope", "justgames", "-n", "x"])
        self.capture(commands.mark, ["--stream", "eng-1", "-n", "near"])  # scope from cwd
        self.assertEqual(self.stream().get("next"), "near")

    # ---- notes
    def test_note_kinds_and_done(self):
        self.capture(commands.note, ["check hockey"], "followup")
        self.capture(commands.note, ["could be its own stream"], "tangent")
        self.capture(commands.note, ["+2d", "ping reviewer"], "reminder")
        self.capture(commands.note, ["landed", "close issue"], "reminder")
        notes = self.stream().notes()
        self.assertEqual(len(notes), 4)
        self.assertTrue(notes[0].startswith("- [followup] "))
        self.assertTrue(notes[1].startswith("- [tangent as=tangent] "))      # every word was a stopword
        self.assertIn("[reminder due=20", notes[2]); self.assertIn("[reminder due=landed]", notes[3])
        rc, out, _ = self.capture(commands.note, ["--done", "hockey"])
        self.assertIn("removed", out)
        self.assertEqual(len(self.stream().notes()), 3)
        with self.assertRaises(WifError): commands.note(["--done", "zzz"])
        with self.assertRaises(WifError): commands.note(["soon", "x"], "reminder")
        with self.assertRaises(WifError): commands.note([""])

    def test_tangent_task_name_pinned_derived_and_renamed(self):
        rc, out, _ = self.capture(commands.note, ["ENG-2486 generic drift-report linter could be its own stream"], "tangent")
        self.assertIn("[tangent as=eng-2486-generic-drift-report-linter] ", out)
        self.assertIn("  task: eng-2486-generic-drift-report-linter\n", out)
        self.assertIn("    1. herdr-task eng-2486-generic-drift-report-linter repo-a\n", out)
        self.assertIn("    2. wif adopt eng-2486-generic-drift-report-linter -p eng-1\n", out)
        rc, out, _ = self.capture(commands.note, ["--as", "drift-linter", "a second idea"], "tangent")
        self.assertIn("[tangent as=drift-linter] ", out)
        with self.assertRaises(WifError): commands.note(["--as", "Drift_Linter", "x"], "tangent")
        with self.assertRaises(WifError): commands.note(["--for", "second"], "tangent")
        with self.assertRaises(WifError): commands.note(["--as", "x", "--for", "second", "text"], "tangent")
        with self.assertRaises(WifError): commands.note(["--as", "x", "--for", "nope"], "tangent")
        rc, out, _ = self.capture(commands.note, ["--as", "eng-2486-drift-linter", "--for", "generic drift"], "tangent")
        self.assertIn("renamed on eng-1: - [tangent as=eng-2486-drift-linter] ", out)
        notes = self.stream().notes()
        self.assertEqual(len(notes), 2)
        self.assertTrue(notes[0].startswith("- [tangent as=eng-2486-drift-linter] "))      # renamed in place
        self.assertTrue(notes[0].endswith(" ENG-2486 generic drift-report linter could be its own stream"))
        self.assertTrue(notes[1].startswith("- [tangent as=drift-linter] "))
        # --done still matches on text, never on the tag
        rc, out, _ = self.capture(commands.note, ["--done", "second idea"])
        self.assertEqual(len(self.stream().notes()), 1)

    def test_tangent_tail_uses_collection_and_existing_container(self):
        self.container("repo-b-task", repos=("repo-b",))
        with mock.patch.dict(os.environ, {"HERDR_REPOS_ONE": "repo-a", "HERDR_REPOS_A_B": "repo-a repo-b"}):
            rc, out, _ = self.capture(commands.note, ["--as", "fresh-idea", "x"], "tangent")
        self.assertIn("    1. herdr-task fresh-idea one\n", out)
        rc, out, _ = self.capture(commands.note, ["--as", "repo-b-task", "already made"], "tangent")
        self.assertIn("wif adopt repo-b-task -p eng-1   (container exists, untracked)", out)
        Stream.create(self.ledger / "streams" / "repo-b-task.md", "repo-b-task", "justgames", "herdr", str(self.cont_root / "repo-b-task"), "parked")
        rc, out, _ = self.capture(commands.note, ["--as", "repo-b-task", "made and adopted"], "tangent")
        self.assertIn("already a stream (parked)", out); self.assertIn('wif note --done "made and adopted"', out)

    def test_note_newline_flattened(self):
        self.capture(commands.note, ["line one\nline two"])
        self.assertEqual(self.stream().notes()[0].split(" ", 3)[-1], "line one line two")

    def test_adopt_prefers_container_name_over_local_dir(self):
        (self.c / "docs").mkdir(); self.container("docs")
        rc, out, _ = self.capture(commands.adopt, ["docs"])
        self.assertTrue(out.strip().endswith("/docs.md"))
        self.assertFalse((self.ledger / "streams" / "eng-1.md").exists())

    def test_remind_overflow_and_done_matches_text_only(self):
        with self.assertRaises(WifError): commands.note(["+99999999d", "x"], "reminder")
        self.capture(commands.note, ["landed", "ship it"], "reminder")
        with self.assertRaises(WifError): commands.note(["--done", "YYYY"])
        rc, out, _ = self.capture(commands.note, ["--done", "ship"])
        self.assertIn("ship it", out)

    def test_where_outside_git_text(self):
        rc, out, _ = self.capture(commands.where, [str(self.home)])
        self.assertIn("backing: none", out)

    # ---- ctx / sessions
    def test_ctx_reads_sidecar(self):
        rc, out, _ = self.capture(commands.ctx_cmd, ["--session", "s1"])
        self.assertIn("no statusline dump", out)
        (self.ledger / "sessions").mkdir(parents=True)
        ledger.dump_json(ledger.ctx_file(self.ledger, "s1"), {"used_pct": 64, "t": "T"})
        rc, out, _ = self.capture(commands.ctx_cmd, ["--session", "s1"])
        self.assertIn("ctx 64%", out); self.assertIn("ROTATE", out)
        self.capture(commands.adopt, ["."]); s = self.stream(); s.set("last_session", "s1", touch=False); s.save()
        rc, out, _ = self.capture(commands.ctx_cmd, ["--json"])
        self.assertEqual(json.loads(out)["used_pct"], 64)

    def test_sessions_listing(self):
        for sid, st in (("a", "eng-1"), ("b", "eng-1"), ("c", "other")):
            s = ledger.session_ensure(self.ledger, sid, st, "justgames"); s["goal"] = sid.upper(); ledger.session_save(self.ledger, s)
        ledger.session_file(self.ledger, "bad").write_text("{")
        with mock.patch("pathlib.Path.stat", side_effect=OSError("gone")):
            self.assertEqual(self.capture(commands.sessions, [])[0], 0)
        rc, out, _ = self.capture(commands.sessions, [])
        self.assertEqual(sorted(l.split()[0] for l in out.splitlines()), ["a", "b"])
        rc, out, _ = self.capture(commands.sessions, ["other", "-n", "1"])
        self.assertIn("goal=C", out)
