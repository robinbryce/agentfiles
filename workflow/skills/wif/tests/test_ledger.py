import json
from pathlib import Path

from wif import ledger
from wif.ledger import Stream
from .base import WifCase


class FrontmatterTests(WifCase):
    def setUp(self):
        super().setUp()
        self.f = self.base / "s.md"
        self.s = Stream.create(self.f, "eng-1", "justgames", "herdr", "/p/eng-1")

    def test_create_is_idempotent_and_has_template(self):
        self.s.set("goal", "G"); self.s.save()
        again = Stream.create(self.f, "eng-1", "justgames", "herdr", "/p/eng-1")
        self.assertEqual(again.get("goal"), "G")
        for sec in ("Now", "Notes", "Handoff", "Dead ends"):
            self.assertIn(f"## {sec}", again.body)

    def test_round_trip_escapes_quotes_backslashes_colons_unicode(self):
        for v in ['C:\\new\\tab "quoted" x:y', 'naïve — “smart”', 'a\\"b', '', '"', '\\']:
            with self.subTest(v=v):
                self.s.set("next", v); self.s.save()
                self.assertEqual(Stream.load(self.f).get("next"), v)

    def test_newlines_are_flattened(self):
        self.s.set("next", "one\ntwo\r\nthree"); self.s.save()
        self.assertEqual(Stream.load(self.f).get("next"), "one two  three")
        self.assertEqual(self.f.read_text().count("\nnext:"), 1)

    def test_set_touches_updated_except_when_asked(self):
        self.s.fm["updated"] = "2000-01-01"
        self.s.set("last_session", "abc", touch=False)
        self.assertEqual(self.s.get("updated"), "2000-01-01")
        self.s.set("goal", "x")
        self.assertEqual(self.s.get("updated"), ledger.today())

    def test_unknown_keys_survive_save(self):
        self.f.write_text(self.f.read_text().replace("---\n## Now", 'custom: "keep"\n---\n## Now'))
        s = Stream.load(self.f); s.set("goal", "g"); s.save()
        self.assertEqual(Stream.load(self.f).get("custom"), "keep")

    def test_file_without_frontmatter(self):
        self.f.write_text("just text\n")
        s = Stream.load(self.f)
        self.assertEqual(s.fm, {})
        self.assertEqual(s.body, "just text\n")


class SectionTests(WifCase):
    def setUp(self):
        super().setUp()
        self.s = Stream.create(self.base / "s.md", "x", "justgames", "herdr", "/p")

    def test_append_goes_before_next_heading_and_skips_comments(self):
        self.s.section_append("Notes", "- [followup] 2026-01-01 a")
        self.s.section_append("Notes", "- [followup] 2026-01-01 b")
        self.assertEqual(self.s.section("Notes"), ["- [followup] 2026-01-01 a", "- [followup] 2026-01-01 b"])
        body = self.s.body
        self.assertLess(body.index("- [followup] 2026-01-01 b"), body.index("## Handoff"))

    def test_append_to_last_section_and_missing_section(self):
        self.s.section_append("Dead ends", "- tried x")
        self.assertEqual(self.s.section("Dead ends"), ["- tried x"])
        self.s.section_append("Brand new", "line")
        self.assertEqual(self.s.section("Brand new"), ["line"])

    def test_remove_first_match_only(self):
        for t in ("alpha one", "alpha two"):
            self.s.section_append("Notes", f"- [followup] 2026-01-01 {t}")
        self.assertEqual(self.s.section_remove("Notes", "alpha"), "- [followup] 2026-01-01 alpha one")
        self.assertEqual(self.s.section("Notes"), ["- [followup] 2026-01-01 alpha two"])
        self.assertIsNone(self.s.section_remove("Notes", "zzz"))
        self.assertIsNone(self.s.section_remove("Now", "alpha"))      # other section untouched

    def test_set_section_replaces_contents(self):
        self.s.section_append("Now", "old")
        self.s.set_section("Now", ["goal: g", "done: d"])
        self.assertEqual(self.s.section("Now"), ["goal: g", "done: d"])
        self.assertIn("## Notes", self.s.body)

    def test_line_count_counts_whole_file(self):
        self.s.save()
        wc = len(self.s.path.read_text().rstrip("\n").split("\n"))
        self.assertEqual(self.s.line_count, wc)


class SessionTests(WifCase):
    def test_ensure_creates_and_repairs_corrupt(self):
        led = self.ledger
        s = ledger.session_ensure(led, "s1", "eng", "justgames")
        self.assertEqual(s["ring"], [])
        f = ledger.session_file(led, "s1")
        f.write_text("null")
        self.assertEqual(ledger.session_ensure(led, "s1", "eng", "justgames")["stream"], "eng")
        f.write_text("{bad")
        self.assertEqual(ledger.session_ensure(led, "s1", "eng", "justgames")["session_id"], "s1")

    def test_safe_sid(self):
        for bad in ("", "../x", ".hidden", "a/b", "a\\b"):
            self.assertFalse(ledger.safe_sid(bad), bad)
        self.assertTrue(ledger.safe_sid("262a2561-7950"))

    def test_prev_for_uses_last_session_then_newest_ended(self):
        led = self.ledger
        st = Stream.create(self.base / "s.md", "eng", "justgames", "herdr", "/p")
        a = ledger.session_ensure(led, "a", "eng", "justgames"); a["ended"] = "2026-01-02T00:00:00Z"; a["goal"] = "A"; ledger.session_save(led, a)
        b = ledger.session_ensure(led, "b", "eng", "justgames"); b["ended"] = "2026-01-03T00:00:00Z"; b["goal"] = "B"; ledger.session_save(led, b)
        ledger.session_ensure(led, "other", "different-stream", "justgames")
        self.assertEqual(ledger.session_prev_for(led, st, exclude="c")["goal"], "B")
        self.assertEqual(ledger.session_prev_for(led, st, exclude="b")["goal"], "A")
        st.set("last_session", "a", touch=False)
        self.assertEqual(ledger.session_prev_for(led, st, exclude="zzz")["goal"], "A")
        self.assertEqual(ledger.session_prev_for(led, st, exclude="a")["goal"], "B")   # excluded -> fallback

    def test_first_line(self):
        self.assertEqual(ledger.first_line("\n\n  hello world \nmore"), "hello world")
        self.assertEqual(ledger.first_line("x" * 300, 5), "xxxxx")
        self.assertEqual(ledger.first_line("\r\n \0"), "")
