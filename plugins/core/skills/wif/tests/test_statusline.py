import json
from unittest import mock

from wif import ledger, statusline
from wif.ledger import Stream
from .base import WifCase


class StatuslineTests(WifCase):
    def test_unbound_cwd_renders_one_line_and_no_sidecar(self):
        lines = statusline.render({"session_id": "s9", "workspace": {"current_dir": str(self.home)},
                                   "context_window": {"used_percentage": "n/a"}}, 100)
        self.assertEqual(len(lines), 1)
        self.assertIn("0%", lines[0])
        self.assertIn("(unserved)", lines[0])
        self.assertFalse((self.ledger / "sessions").exists())

    def test_bound_cwd_writes_sidecar_and_three_lines(self):
        c = self.container("eng-1")
        (self.ledger / "sessions").mkdir(parents=True)
        s = Stream.create(self.ledger / "streams" / "eng-1.md", "eng-1", "justgames", "herdr", str(c))
        s.set("goal", "G"); s.set("next", "N"); s.set("position", "slice 1/2"); s.save()
        sess = ledger.session_ensure(self.ledger, "s1", "eng-1", "justgames")
        sess["goal"] = "SG"; sess["ring"] = [{"intent": "the intent"}]; ledger.session_save(self.ledger, sess)
        data = {"session_id": "s1", "workspace": {"current_dir": str(c / "repo-a")}, "model": {"display_name": "Fable"},
                "context_window": {"used_percentage": 63.7}, "cost": {"total_cost_usd": 1.5}}
        lines = statusline.render(data, 120)
        self.assertEqual(len(lines), 3)
        self.assertIn("eng-1 · active · slice 1/2", lines[0])
        self.assertIn("63%", lines[0]); self.assertIn("ROTATE", lines[0])
        self.assertIn("goal:", lines[1]); self.assertIn("SG", lines[1]); self.assertIn("N", lines[1])
        self.assertIn("the intent", lines[2])
        side = json.loads((self.ledger / "sessions" / "s1.ctx.json").read_text())
        self.assertEqual((side["used_pct"], side["stream"], side["cost_usd"]), (63, "eng-1", 1.5))

    def test_rotate_threshold_env(self):
        c = self.container("eng-1")
        with mock.patch.dict("os.environ", {"WIF_ROTATE_PCT": "90"}):
            lines = statusline.render({"session_id": "s1", "workspace": {"current_dir": str(c)}, "context_window": {"used_percentage": 70}})
        self.assertNotIn("ROTATE", lines[0])

    def test_main_tolerates_garbage(self):
        for payload in ("", "nope", "[]", "{}"):
            rc, out = self.feed(statusline.main, payload)
            self.assertEqual(rc, 0)

    def test_bad_session_id_does_not_write(self):
        c = self.container("eng-1"); (self.ledger / "sessions").mkdir(parents=True)
        statusline.render({"session_id": "../x", "workspace": {"current_dir": str(c)}})
        self.assertEqual(list((self.ledger / "sessions").iterdir()), [])
