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
        self.assertIn("    herdr-task eng-2486-generic-drift-report-linter repo-a && wif adopt eng-2486-generic-drift-report-linter "
                      "-g 'ENG-2486 generic drift-report linter could be its own stream'\n", out)
        rc, out, _ = self.capture(commands.note, ["--as", "drift-linter", "a second idea"], "tangent")
        self.assertIn("[tangent as=drift-linter] ", out)
        with self.assertRaises(WifError): commands.note(["--as", "Drift_Linter", "x"], "tangent")
        with self.assertRaises(WifError): commands.note(["--for", "second"], "tangent")
        with self.assertRaises(WifError): commands.note(["--as", "x", "--for", "second", "text"], "tangent")
        with self.assertRaises(WifError): commands.note(["--as", "x", "--for", "nope"], "tangent")
        rc, out, _ = self.capture(commands.note, ["--as", "eng-2486-drift-linter", "--for", "generic drift"], "tangent")
        self.assertIn("re-tagged on eng-1: - [tangent as=eng-2486-drift-linter] ", out)
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
        self.assertIn("    herdr-task fresh-idea one && wif adopt fresh-idea -g 'x'\n", out)
        rc, out, _ = self.capture(commands.note, ["--as", "repo-b-task", "already made"], "tangent")
        self.assertIn("wif adopt repo-b-task   (container exists, untracked)", out)
        Stream.create(self.ledger / "streams" / "repo-b-task.md", "repo-b-task", "justgames", "herdr", str(self.cont_root / "repo-b-task"), "parked")
        rc, out, _ = self.capture(commands.note, ["--as", "repo-b-task", "made and adopted"], "tangent")
        self.assertIn("wif adopt repo-b-task   (already a stream (parked); re-adopting clears this note)", out)

    # ---- adopt finishes the tangent (plan-2610-02 C1)
    def test_adopt_clears_tangent_inherits_parent_goal_and_seeds_handoff(self):
        self.capture(commands.adopt, [".", "-g", "parent goal"])
        s = self.stream(); s.set("handoff_doc", "/abs/handoff.md"); s.save()
        self.memory_dir("eng-1")
        (self.memory_dir("eng-1") / "MEMORY.md").write_text("# idx")
        self.capture(commands.note, ["--as", "side-quest", "make the linter generic"], "tangent")
        self.container("side-quest")
        rc, out, _ = self.capture(commands.adopt, ["side-quest"])
        self.assertIn("cleared tangent on eng-1: make the linter generic", out)
        self.assertIn("seeded ## Handoff", out)
        self.assertEqual(self.stream().notes(), [])                       # note gone from the parent
        child = Stream.load(self.ledger / "streams" / "side-quest.md")
        self.assertEqual((child.get("parent"), child.get("goal")), ("eng-1", "make the linter generic"))
        h = child.section("Handoff")
        self.assertEqual(h[0], "objective: make the linter generic")
        self.assertTrue(h[1].startswith(f"discovered from: eng-1 ({self.c})"), h[1])
        self.assertIn("parent goal: parent goal", h); self.assertIn("parent handoff: /abs/handoff.md", h)
        self.assertTrue(any(l.startswith("memory bridge: Read ") and l.split("Read ")[1].startswith(str(self.cfg / "projects")) for l in h), h)
        self.assertEqual(h[-1], "re-invoke: /core:wif"); self.assertLessEqual(len(h), 12)

    def test_adopt_explicit_flags_win_and_handoff_never_clobbered(self):
        self.capture(commands.adopt, ["."])
        self.capture(commands.note, ["--as", "kid", "tangent text"], "tangent")
        self.capture(commands.note, ["--as", "kid", "second note, same name"], "tangent")
        self.container("kid")
        rc, out, _ = self.capture(commands.adopt, ["kid", "-g", "my goal", "-p", "ENG-7"])
        child = Stream.load(self.ledger / "streams" / "kid.md")
        self.assertEqual((child.get("parent"), child.get("goal")), ("ENG-7", "my goal"))
        self.assertEqual(len(self.stream().notes()), 1)                   # only the first as=kid note cleared
        h = child.section("Handoff")
        self.assertEqual(h[0], "objective: tangent text")
        self.assertTrue(h[1].startswith("discovered from: eng-1 ("), h)       # the stream the note was on…
        self.assertIn("parent: ENG-7", h)                                      # …and the label -p recorded
        before = child.section("Handoff")
        rc, out, _ = self.capture(commands.adopt, ["kid", "-n", "next"])    # re-adopt: clears the second note, keeps Handoff
        self.assertIn("cleared tangent on eng-1: second note", out); self.assertNotIn("seeded", out)
        self.assertEqual(self.stream().notes(), [])
        self.assertEqual(Stream.load(self.ledger / "streams" / "kid.md").section("Handoff"), before)

    def test_adopt_without_tangent_seeds_only_under_a_parent_stream(self):
        self.container("lone")
        rc, out, _ = self.capture(commands.adopt, ["lone", "-g", "g"])
        self.assertNotIn("seeded", out); self.assertNotIn("cleared", out)
        self.assertEqual(Stream.load(self.ledger / "streams" / "lone.md").section("Handoff"), [])
        self.capture(commands.adopt, [".", "-g", "pg"])
        self.container("under")
        rc, out, _ = self.capture(commands.adopt, ["under", "-p", "eng-1"])
        h = Stream.load(self.ledger / "streams" / "under.md").section("Handoff")
        self.assertEqual(h[0], "objective: -"); self.assertTrue(h[1].startswith("parent: eng-1 ("))
        self.assertIn("parent goal: pg", h); self.assertFalse(any(l.startswith("memory bridge") for l in h))

    def test_adopt_ignores_archived_streams_tangents(self):
        self.capture(commands.adopt, ["."])
        self.capture(commands.note, ["--as", "ghost", "from a closed stream"], "tangent")
        self.capture(commands.mark, ["-s", "closed"])
        self.container("ghost")
        rc, out, _ = self.capture(commands.adopt, ["ghost"])
        self.assertNotIn("cleared", out)
        self.assertEqual(Stream.load(self.ledger / "streams" / "ghost.md").get("parent"), "")

    def test_tangent_recommendation_goal_is_cut_at_a_word_and_stays_valid_shell(self):
        from wif import tangents
        long = "please add the --issue flag to wif mark per the correction, and wire it through the hooks and the statusline too"
        rc, out, _ = self.capture(commands.note, ["--as", "wif-issue", long], "tangent")
        cmd = [l for l in out.splitlines() if l.strip().startswith("herdr-task wif-issue")][0]
        goal = cmd.split(" -g '", 1)[1].rstrip("'")
        self.assertTrue(cmd.endswith("'") and len(goal) <= tangents.GOAL_MAX and long.startswith(goal) and not goal.endswith(","), cmd)
        self.assertEqual(tangents.goal_text('say "hi" $x!'), 'say "hi" $x!')
        self.assertEqual(tangents.shell_quote("""it's "x" $y!"""), """'it'\\''s "x" $y!'""")
        import subprocess
        echoed = subprocess.run(["bash", "-c", "echo " + tangents.shell_quote("""it's "x" $y! `z`""")], capture_output=True, text=True).stdout
        self.assertEqual(echoed.rstrip("\n"), """it's "x" $y! `z`""")

    def test_adopt_closed_does_not_consume_tangent_and_locks_only_matching_streams(self):
        self.capture(commands.adopt, ["."])
        self.container("other"); self.capture(commands.adopt, ["other"])
        self.capture(commands.note, ["--as", "kid", "keep me"], "tangent")
        self.container("kid")
        for lk in (self.ledger / "streams").glob("*.lock"): lk.unlink()
        rc, out, _ = self.capture(commands.adopt, ["kid", "-s", "closed"])
        self.assertNotIn("cleared", out); self.assertEqual(len(self.stream().notes()), 1)
        rc, out, _ = self.capture(commands.adopt, ["kid"])
        self.assertIn("cleared tangent on eng-1", out)
        locks = sorted(p.name for p in (self.ledger / "streams").glob("*.lock"))
        self.assertEqual(locks, ["eng-1.md.lock", "kid.md.lock"])              # `other` was read, never locked

    # ---- tangent --issue: the Linear id rides the note, the name, the stream and its handoff
    def test_tangent_issue_tag_name_and_retag(self):
        from wif import tangents
        rc, out, _ = self.capture(commands.note, ["--issue", "https://linear.app/sentientdogs/issue/ENG-2700/some-slug", "split the thing out"], "tangent")
        self.assertIn("[tangent as=eng-2700-split-out issue=ENG-2700] ", out)      # issue leads the derived name ("thing" is a stopword)
        n = self.stream().notes()[0]; p = tangents.parse(n)
        self.assertEqual((p["as"], p["issue"], p["text"]), ("eng-2700-split-out", "ENG-2700", "split the thing out"))
        with self.assertRaises(WifError): commands.note(["--issue", "nope-1", "x"], "tangent")
        with self.assertRaises(WifError): commands.note(["--for", "split"], "tangent")               # neither --as nor --issue
        rc, out, _ = self.capture(commands.note, ["--issue", "ENG-2701", "--for", "split"], "tangent")   # re-pin issue only: name kept
        self.assertIn("[tangent as=eng-2700-split-out issue=ENG-2701] ", out)
        rc, out, _ = self.capture(commands.note, ["--as", "better-name", "--for", "split"], "tangent")    # re-pin name only: issue kept
        self.assertIn("[tangent as=better-name issue=ENG-2701] ", out)
        self.capture(commands.note, ["an unnamed one"], "tangent")                                  # name derived at record time…
        rc, out, _ = self.capture(commands.note, ["--issue", "ENG-9", "--for", "unnamed"], "tangent")
        self.assertIn("[tangent as=unnamed-one issue=ENG-9] ", out)                                 # …and kept when only the issue is pinned
        s = self.stream(); s.section_append("Notes", "- [tangent] 2000-01-01 legacy bare note"); s.save()   # pre-as= format
        rc, out, _ = self.capture(commands.note, ["--issue", "ENG-10", "--for", "legacy bare"], "tangent")
        self.assertIn("[tangent as=eng-10-legacy-bare-note issue=ENG-10] ", out)                   # legacy line gets a name, issue first
        self.assertIn("  task: eng-10-legacy-bare-note\n", out)
        # --for never re-tags a followup, even when it is the first note containing the substring
        self.capture(commands.note, ["followup about legacy things"])
        with self.assertRaises(WifError): commands.note(["--issue", "ENG-11", "--for", "followup about"], "tangent")
        self.assertTrue(self.stream().notes()[-1].startswith("- [followup] "))
        # ids: URL with query/fragment, lowercase rejected, short id never repeated in the derived words
        self.assertEqual(tangents.issue_id("https://linear.app/sd/issue/ENG-7?x=1"), "ENG-7")
        self.assertEqual(tangents.issue_id("https://linear.app/sd/issue/ENG-7#c"), "ENG-7")
        self.assertEqual(tangents.issue_id("eng-7"), "")
        self.assertEqual(tangents.derive("ENG-5 fix the eng-5 widget", "ENG-5"), "eng-5-fix-widget")

    def test_adopt_carries_issue_into_stream_and_handoff_and_mark_sets_it(self):
        self.capture(commands.adopt, ["."])
        self.capture(commands.note, ["--as", "kid", "--issue", "ENG-77", "kid idea"], "tangent")
        self.container("kid")
        rc, out, _ = self.capture(commands.adopt, ["kid"])
        child = Stream.load(self.ledger / "streams" / "kid.md")
        self.assertEqual((child.get("issue"), child.get("parent")), ("ENG-77", "eng-1"))
        self.assertIn("issue: ENG-77", child.section("Handoff"))
        rc, out, _ = self.capture(commands.adopt, ["kid", "--issue", "https://linear.app/x/issue/ENG-78/slug"])  # explicit wins
        self.assertEqual(Stream.load(self.ledger / "streams" / "kid.md").get("issue"), "ENG-78")
        rc, out, _ = self.capture(commands.mark, ["--issue", "ENG-5"])
        self.assertEqual(self.stream().get("issue"), "ENG-5"); self.assertIn("issue=ENG-5", out)
        with self.assertRaises(WifError): commands.mark(["--issue", "bogus"])
        with self.assertRaises(WifError): commands.adopt(["kid", "--issue", "bogus"])

    def test_note_done_by_stream_from_anywhere(self):
        self.capture(commands.adopt, ["."])
        self.capture(commands.note, ["clear me remotely"])
        self.cd(self.home)                                                     # anywhere outside the container
        with self.assertRaises(WifError): commands.note(["--done", "remotely"])          # no backing at ~
        with self.assertRaises(WifError): commands.note(["--done", "remotely", "--scope", "justgames"])
        rc, out, _ = self.capture(commands.note, ["--done", "remotely", "--stream", "eng-1", "--scope", "justgames"])
        self.assertIn("removed from eng-1", out)
        self.assertEqual(Stream.load(self.ledger / "streams" / "eng-1.md").notes(), [])

    def test_note_tangent_remind_address_a_stream_from_anywhere(self):
        self.capture(commands.adopt, ["."])
        self.cd(self.home)
        with self.assertRaises(WifError): commands.note(["far away"])                       # no backing at ~
        self.capture(commands.note, ["far away", "--stream", "eng-1", "--scope", "justgames"])
        self.capture(commands.note, ["--as", "kid", "--stream", "eng-1", "--scope", "justgames", "an idea"], "tangent")
        rc, out, _ = self.capture(commands.note, ["--issue", "ENG-3", "--for", "an idea", "--stream", "eng-1", "--scope", "justgames"], "tangent")
        self.assertIn("[tangent as=kid issue=ENG-3] ", out)
        self.capture(commands.note, ["+1d", "ping", "--stream", "eng-1", "--scope", "justgames"], "reminder")
        notes = Stream.load(self.ledger / "streams" / "eng-1.md").notes()
        self.assertEqual(len(notes), 3); self.assertTrue(notes[0].startswith("- [followup] ") and notes[2].startswith("- [reminder due="))
        with self.assertRaises(WifError): commands.note(["x", "--scope", "justgames"])         # --scope needs --stream
        with self.assertRaises(WifError): commands.note(["x", "--stream", "nope", "--scope", "justgames"])

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
