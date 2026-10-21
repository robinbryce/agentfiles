import json
import os
from unittest import mock

from wif import hooks, ledger
from wif.ledger import Stream
from .base import WifCase


class HookTests(WifCase):
    def setUp(self):
        super().setUp()
        self.c = self.container("eng-1")
        self.d = self.container("eng-2")

    def ev(self, name, sid="s1", cwd=None, **kw):
        return {"hook_event_name": name, "session_id": sid, "cwd": str(cwd or self.c), **kw}

    def sess(self, sid):
        return ledger.load_json(ledger.session_file(self.ledger, sid), None)

    def test_prompt_creates_stream_session_ring_and_context(self):
        out = hooks.handle(self.ev("UserPromptSubmit", prompt="fix the drift test\nmore"))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(ctx.startswith("[wif] eng-1 · active"))
        self.assertIn("session goal unset", ctx)
        self.assertIn("--session s1", ctx)
        self.assertTrue((self.ledger / "streams" / "eng-1.md").exists())
        self.assertEqual(self.sess("s1")["ring"][0]["prompt"], "fix the drift test")
        self.assertEqual(Stream.load(self.ledger / "streams" / "eng-1.md").get("last_session"), "s1")

    def test_prompt_text_key_also_accepted_and_ring_bounded(self):
        with mock.patch.dict(os.environ, {"WIF_RING": "3"}):
            for i in range(5):
                hooks.handle(self.ev("UserPromptSubmit", prompt_text=f"p{i}"))
        self.assertEqual([r["prompt"] for r in self.sess("s1")["ring"]], ["p2", "p3", "p4"])

    def test_slash_commands_skipped_paths_kept(self):
        hooks.handle(self.ev("UserPromptSubmit", prompt="/wif status"))
        hooks.handle(self.ev("UserPromptSubmit", prompt="/Users/r/x.md please read"))
        self.assertEqual([r["prompt"] for r in self.sess("s1")["ring"]], ["/Users/r/x.md please read"])

    def test_stop_records_outcome(self):
        hooks.handle(self.ev("UserPromptSubmit", prompt="do"))
        self.assertIsNone(hooks.handle(self.ev("Stop", last_assistant_message="Done.\n\ndetails")))
        self.assertEqual(self.sess("s1")["ring"][-1]["outcome"], "Done.")

    def test_session_start_with_foreign_session_file_still_outputs(self):
        hooks.handle(self.ev("UserPromptSubmit", sid="s1", cwd=self.c, prompt="work on one"))
        out = hooks.handle(self.ev("SessionStart", sid="s2", cwd=self.d, source="startup"))
        self.assertIn("session startup on stream eng-2", out["hookSpecificOutput"]["additionalContext"])

    def test_compact_does_not_carry_or_overwrite_goal(self):
        hooks.handle(self.ev("UserPromptSubmit", sid="old", prompt="x"))
        old = self.sess("old"); old["goal"] = "OLD"; ledger.session_save(self.ledger, old)
        hooks.handle(self.ev("UserPromptSubmit", sid="cur", prompt="y"))
        cur = self.sess("cur"); cur["goal"] = "CUR"; ledger.session_save(self.ledger, cur)
        out = hooks.handle(self.ev("SessionStart", sid="cur", source="compact"))
        self.assertEqual(self.sess("cur")["goal"], "CUR")
        self.assertNotIn("previous session", out["hookSpecificOutput"]["additionalContext"])

    def test_clear_carries_predecessor_goal_and_shows_previous(self):
        hooks.handle(self.ev("UserPromptSubmit", sid="s1", prompt="work"))
        s1 = self.sess("s1"); s1["goal"] = "G1"; s1["ring"][-1]["intent"] = "I1"; s1["ring"][-1]["outcome"] = "O1"; ledger.session_save(self.ledger, s1)
        hooks.handle(self.ev("SessionEnd", sid="s1", reason="clear"))
        out = hooks.handle(self.ev("SessionStart", sid="s2", source="clear"))
        text = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("previous session: goal=G1 · last intent=I1 · last outcome=O1", text)
        self.assertEqual(self.sess("s2")["goal"], "G1")
        self.assertEqual(self.sess("s1")["end_reason"], "clear")

    def test_session_start_injects_handoff_and_now(self):
        s = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(self.c))
        s.set_section("Handoff", ["kickoff line"]); s.set_section("Now", ["goal: g"]); s.save()
        text = hooks.handle(self.ev("SessionStart", source="startup"))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("## Handoff (from stream file)\nkickoff line", text)
        self.assertIn("## Now\ngoal: g", text)

    def test_closed_stream_is_not_resurrected(self):
        hooks.handle(self.ev("UserPromptSubmit", prompt="x"))
        sf = self.ledger / "streams" / "eng-1.md"
        (self.ledger / "archive").mkdir(exist_ok=True)
        sf.rename(self.ledger / "archive" / "eng-1.md")
        for name in ("UserPromptSubmit", "Stop", "SessionStart", "SessionEnd"):
            self.assertIsNone(hooks.handle(self.ev(name, prompt="y", last_assistant_message="z")))
        self.assertFalse(sf.exists())

    def test_unserved_scope_records_nothing(self):
        foreign = self.home / "Dev/personal/foo"; self.git_repo(foreign)
        self.assertIsNone(hooks.handle(self.ev("UserPromptSubmit", cwd=foreign, prompt="x")))
        self.assertFalse((self.cfg / "wif" / "personal").exists())

    def test_subagent_and_bad_ids_ignored(self):
        self.assertIsNone(hooks.handle(self.ev("UserPromptSubmit", prompt="x", agent_id="sub")))
        self.assertIsNone(hooks.handle(self.ev("UserPromptSubmit", sid="../evil", prompt="x")))
        self.assertIsNone(hooks.handle({"hook_event_name": "Stop"}))
        self.assertFalse((self.ledger / "sessions").exists())

    def test_corrupt_session_recovers(self):
        hooks.handle(self.ev("UserPromptSubmit", prompt="x"))
        ledger.session_file(self.ledger, "s1").write_text("null")
        out = hooks.handle(self.ev("UserPromptSubmit", prompt="recover"))
        self.assertIn("[wif] eng-1", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.sess("s1")["ring"][-1]["prompt"], "recover")

    def test_main_never_fails_and_prints_json_only(self):
        for payload in ("not json", "", "null", "[]", json.dumps(self.ev("UserPromptSubmit", prompt="a\"b\\c"))):
            with self.subTest(payload=payload[:10]):
                rc, out = self.feed(hooks.main, payload)
                self.assertEqual(rc, 0)
                if out.strip():
                    self.assertIn("hookSpecificOutput", json.loads(out))

    def test_debug_tap(self):
        tap = self.base / "tap.jsonl"
        self.feed(hooks.main, self.ev("Stop"), {"WIF_HOOK_DEBUG": str(tap)})
        self.assertEqual(json.loads(tap.read_text())["hook_event_name"], "Stop")

    def test_is_slash_command(self):
        self.assertTrue(hooks.is_slash_command("/wif"))
        self.assertTrue(hooks.is_slash_command("/wif tick now"))
        self.assertFalse(hooks.is_slash_command("/Users/robin/x"))
        self.assertFalse(hooks.is_slash_command("plain"))
