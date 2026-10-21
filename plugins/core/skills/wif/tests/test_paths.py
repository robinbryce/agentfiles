import os
from pathlib import Path
from unittest import mock

from wif import paths
from .base import WifCase, HERDR


class ScopeAccountTests(WifCase):
    def test_account_from_config_dir_name(self):
        self.assertEqual(paths.account(), "justgames")
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.home / ".claude-personal")}):
            self.assertEqual(paths.account(), "personal")
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.home / ".claude")}):
            self.assertEqual(paths.account(), "personal")
        for p in ("forestrie", "home"):
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.home / f".claude-{p}")}):
                self.assertEqual(paths.account(), p)

    def test_empty_config_dir_env_falls_back_to_home(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": ""}):
            self.assertEqual(paths.config_dir(), self.home / ".claude")
            self.assertEqual(paths.account(), "personal")

    def test_task_name_is_nfc_normalised(self):
        import unicodedata
        nfd = unicodedata.normalize("NFD", "café")
        c = self.container(nfd)
        self.assertEqual(paths.backing_of(c)[1], unicodedata.normalize("NFC", "café"))

    def test_config_tunables_fall_back_on_junk(self):
        from wif import config
        with mock.patch.dict(os.environ, {"WIF_RING": "lots", "WIF_STALE_DAYS": ""}):
            self.assertEqual((config.ring(), config.stale_days()), (10, 14))

    def test_relative_config_dir_is_made_absolute(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "rel-cfg"}):
            self.assertTrue(paths.config_dir().is_absolute())

    def test_scope_of_mirrors_router_table(self):
        self.assertEqual(paths.scope_of(self.home / "Dev/justgames/code/x"), "justgames")
        self.assertEqual(paths.scope_of(self.home / "Dev/personal/forestrie/canopy"), "forestrie")
        self.assertEqual(paths.scope_of(self.home / "Dev/personal/home/tax"), "home")
        self.assertEqual(paths.scope_of(self.home / "Dev/personal/other"), "personal")
        self.assertEqual(paths.scope_of(self.home), "personal")
        self.assertEqual(paths.scope_of(Path("/tmp/justgames")), "personal")   # prefix, not substring

    def test_account_serves(self):
        self.assertTrue(paths.account_serves("justgames", "justgames"))
        self.assertFalse(paths.account_serves("justgames", "personal"))
        self.assertTrue(paths.account_serves("forestrie", "forestrie"))
        self.assertTrue(paths.account_serves("home", "home"))
        self.assertFalse(paths.account_serves("forestrie", "personal"))
        # personal stands in for a profile this machine does not have, and only then
        self.assertTrue(paths.account_serves("personal", "forestrie"))
        self.assertTrue(paths.account_serves("personal", "home"))
        self.assertFalse(paths.account_serves("personal", "justgames"))
        (self.home / ".claude-forestrie").mkdir()
        self.assertFalse(paths.account_serves("personal", "forestrie"))
        self.assertTrue(paths.account_serves("personal", "home"))
        with mock.patch.dict(os.environ, {"WIF_ACCOUNT_SCOPES": "a b"}):
            self.assertTrue(paths.account_serves("anything", "b"))
            self.assertFalse(paths.account_serves("justgames", "justgames"))
            self.assertEqual(paths.known_scopes(), ("a", "b"))

    def test_scope_root_override(self):
        self.assertEqual(paths.scope_root("justgames"), self.home / "Dev/justgames/code")
        with mock.patch.dict(os.environ, {"WIF_ROOT_JUSTGAMES": "/elsewhere"}):
            self.assertEqual(paths.scope_root("justgames"), Path("/elsewhere"))
        self.assertIsNone(paths.scope_root("bogus"))


class BackingTests(WifCase):
    def test_herdr_container_and_subdir(self):
        c = self.container("eng-1")
        for p in (c, c / "repo-a", c / "repo-a" / "deep"):
            p.mkdir(exist_ok=True)
            self.assertEqual(paths.backing_of(p), ("herdr", "eng-1", c))

    def test_space_in_task_name_survives(self):
        c = self.container("my task")
        self.assertEqual(paths.backing_of(c / "repo-a"), ("herdr", "my task", c))

    def test_plain_repo_id_is_repo_and_branch(self):
        r = self.git_repo(self.root / "flip-oracle")
        self.git(r, "checkout", "-q", "-b", "feat/x_y")
        kind, sid, top = paths.backing_of(r)
        self.assertEqual((kind, sid, top), ("repo", "flip-oracle--feat-x_y", r))

    def test_linked_worktree_resolves_to_main_repo_name(self):
        r = self.git_repo(self.root / "flip-oracle")
        wt = self.root / "wt"
        self.git(r, "worktree", "add", "-q", "-b", "topic", str(wt))
        self.assertEqual(paths.backing_of(wt)[:2], ("repo", "flip-oracle--topic"))

    def test_detached_head(self):
        r = self.git_repo(self.root / "r", commits=2)
        self.git(r, "checkout", "-q", "HEAD~1")
        self.assertEqual(paths.backing_of(r)[1], "r--detached")

    def test_none_outside_git(self):
        self.assertEqual(paths.backing_of(self.home), ("none", "", None))
        self.assertEqual(paths.backing_of(self.home / "missing"), ("none", "", None))

    def test_symlinked_cwd_resolves(self):
        c = self.container("eng-2")
        link = self.home / "link"
        link.symlink_to(c)
        self.assertEqual(paths.backing_of(link / "repo-a")[1], "eng-2")


class ResolveTests(WifCase):
    def test_resolve_in_container(self):
        c = self.container("eng-3")
        ctx = paths.resolve(c)
        self.assertEqual((ctx.account, ctx.scope, ctx.served, ctx.kind, ctx.id), ("justgames", "justgames", True, "herdr", "eng-3"))
        self.assertEqual(ctx.ledger, self.ledger)
        self.assertEqual(ctx.stream_file, self.ledger / "streams" / "eng-3.md")
        self.assertTrue(ctx.bindable())

    def test_unserved_scope_is_not_bindable(self):
        c = self.home / "Dev/personal/foo"
        self.git_repo(c)
        ctx = paths.resolve(c)
        self.assertEqual((ctx.scope, ctx.served), ("personal", False))
        self.assertFalse(ctx.bindable())

    def test_repo_binds_only_once_stream_exists(self):
        r = self.git_repo(self.root / "flip-oracle")
        ctx = paths.resolve(r)
        self.assertFalse(ctx.bindable())
        ctx.stream_file.parent.mkdir(parents=True)
        ctx.stream_file.write_text("---\nid: \"x\"\n---\n")
        self.assertTrue(paths.resolve(r).bindable())

    def test_archived_stream_is_not_bindable(self):
        c = self.container("eng-4")
        (self.ledger / "archive").mkdir(parents=True)
        (self.ledger / "archive" / "eng-4.md").write_text("---\n---\n")
        self.assertFalse(paths.resolve(c).bindable())

    def test_as_json_shape(self):
        j = paths.resolve(self.container("eng-5")).as_json()
        self.assertEqual(j["id"], "eng-5")
        self.assertFalse(j["stream_exists"])
        self.assertIn("ledger", j)
