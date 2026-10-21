import contextlib
import json
import os
import subprocess
from pathlib import Path
from unittest import mock

from wif import cli, install
from .base import WifCase


class InstallTests(WifCase):
    def settings(self, name, obj):
        d = self.base / name; d.mkdir(exist_ok=True)
        f = d / "settings.json"
        f.write_text(obj if isinstance(obj, str) else json.dumps(obj))
        return d

    def inst(self, *args):
        return self.capture(install.main, list(args))

    def read(self, d):
        return json.loads((d / "settings.json").read_text())

    def test_dry_run_writes_nothing(self):
        d = self.base / "A"
        rc, out, err = self.inst("--config-dir", str(d), "--bin", str(self.base / "bin"))
        self.assertEqual(rc, 0); self.assertIn("dry run", out); self.assertIn("+  \"hooks\"", out)
        self.assertFalse(d.exists()); self.assertFalse((self.base / "bin").exists())

    def test_apply_merges_keeps_user_hooks_and_statusline(self):
        d = self.settings("B", {"statusLine": {"type": "command", "command": "mine.sh"},
                                "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "my-stop.sh"}]}]}})
        rc, out, err = self.inst("--apply", "--config-dir", str(d), "--bin", str(self.base / "bin"))
        self.assertIn("keeping your existing statusLine", err)
        s = self.read(d)
        self.assertEqual(s["statusLine"]["command"], "mine.sh")
        self.assertEqual([h["command"] for g in s["hooks"]["Stop"] for h in g["hooks"]], ["my-stop.sh", f"{install.entry_point()} hook"])
        self.assertEqual(sorted(s["hooks"]), ["SessionEnd", "SessionStart", "Stop", "UserPromptSubmit"])
        self.assertTrue(list(d.glob("settings.json.bak.*")))
        link = self.base / "bin" / "wif"
        self.assertTrue(link.is_symlink()); self.assertEqual(Path(os.readlink(link)), install.entry_point())
        # re-apply: no duplicates
        self.inst("--apply", "--config-dir", str(d), "--bin", str(self.base / "bin"))
        self.assertEqual(len(self.read(d)["hooks"]["Stop"]), 2)
        # force statusline
        self.inst("--apply", "--force-statusline", "--config-dir", str(d), "--bin", str(self.base / "bin"))
        self.assertIn("wif statusline", self.read(d)["statusLine"]["command"])
        # remove: only ours go, user's stay, statusline (ours) removed
        self.inst("--remove", "--apply", "--config-dir", str(d))
        s = self.read(d)
        self.assertEqual(s, {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "my-stop.sh"}]}]}})

    def test_remove_on_file_without_hooks_stays_valid(self):
        d = self.settings("C", {"theme": "dark"})
        self.inst("--remove", "--apply", "--config-dir", str(d))
        self.assertEqual(self.read(d), {"theme": "dark"})

    def test_invalid_json_skipped(self):
        d = self.settings("D", "{bad")
        rc, out, err = self.inst("--apply", "--config-dir", str(d), "--bin", str(self.base / "bin"))
        self.assertEqual(rc, 1); self.assertIn("not valid JSON", err)
        self.assertEqual((d / "settings.json").read_text(), "{bad")

    def test_default_dirs_are_both_accounts(self):
        rc, out, err = self.inst("--bin", str(self.base / "bin"))
        self.assertIn(str(self.home / ".claude-justgames" / "settings.json"), out)
        self.assertIn(str(self.home / ".claude-personal" / "settings.json"), out)

    def test_unknown_arg(self):
        rc, out, err = self.inst("--nope")
        self.assertEqual(rc, 1)

    def test_backups_do_not_collide_within_a_second(self):
        d = self.settings("E", {"a": 1})
        with mock.patch("wif.install.time.strftime", return_value="20260101000000"):
            self.inst("--apply", "--config-dir", str(d), "--bin", str(self.base / "bin"))
            (d / "settings.json").write_text(json.dumps({"a": 2}))
            self.inst("--apply", "--force-statusline", "--config-dir", str(d), "--bin", str(self.base / "bin"))
        baks = sorted(p.name for p in d.glob("settings.json.bak.*"))
        self.assertEqual(baks, ["settings.json.bak.20260101000000", "settings.json.bak.20260101000000-1"])
        self.assertEqual(json.loads((d / baks[0]).read_text()), {"a": 1})

    def test_malformed_hooks_tolerated_and_fork_in_matcher(self):
        d = self.settings("F", {"hooks": ["not", "a", "dict"], "statusLine": "str"})
        rc, out, err = self.inst("--apply", "--config-dir", str(d), "--bin", str(self.base / "bin"))
        self.assertEqual(rc, 0)
        s = self.read(d)
        self.assertEqual(s["hooks"]["SessionStart"][0]["matcher"], "startup|resume|clear|compact|fork")
        d2 = self.settings("G", {"hooks": {"Stop": [{"hooks": "str"}, "junk"]}})
        self.assertEqual(self.inst("--remove", "--apply", "--config-dir", str(d2))[0], 0)
        self.assertEqual(self.read(d2), {})

    def test_refuses_to_replace_regular_file_in_bin(self):
        b = self.base / "bin"; b.mkdir(); (b / "wif").write_text("#!/bin/sh")
        rc, out, err = self.inst("--apply", "--config-dir", str(self.base / "H"), "--bin", str(b))
        self.assertEqual(rc, 1); self.assertIn("refusing", err)
        self.assertEqual((b / "wif").read_text(), "#!/bin/sh")

    def test_default_bin_is_under_patched_home(self):
        rc, out, err = self.inst()
        self.assertIn(str(self.home / ".local" / "bin" / "wif"), out)


class CliTests(WifCase):
    def test_help_version_unknown(self):
        rc, out, _ = self.capture(cli.main, ["help"]); self.assertEqual(rc, 0); self.assertIn("wif <command>", out)
        rc, out, _ = self.capture(cli.main, ["version"]); self.assertEqual(rc, 0)
        rc, out, err = self.capture(cli.main, ["bogus"]); self.assertEqual(rc, 1); self.assertIn("unknown command", err)

    def test_wif_error_becomes_rc1(self):
        with contextlib.chdir(self.home):
            rc, out, err = self.capture(cli.main, ["mark", "-n", "x"])
        self.assertEqual(rc, 1); self.assertTrue(err.startswith("wif: "))

    def test_default_command_is_show(self):
        with contextlib.chdir(self.root):
            rc, out, _ = self.capture(cli.main, [])
        self.assertEqual(rc, 0); self.assertIn("run `wif scan`", out)

    def test_entry_point_script_runs(self):
        ep = install.entry_point()
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}      # keep the repo clean
        r = subprocess.run([str(ep), "version"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0); self.assertTrue(r.stdout.strip())

    def test_cli_dispatches_hook_and_statusline(self):
        c = self.container("eng-1")
        rc, out = self.feed(lambda a: cli.main(["hook"]), {"hook_event_name": "UserPromptSubmit", "session_id": "s", "cwd": str(c), "prompt": "x"})
        self.assertEqual(rc, 0); self.assertIn("hookSpecificOutput", json.loads(out))
        rc, out = self.feed(lambda a: cli.main(["statusline"]), {"session_id": "s", "workspace": {"current_dir": str(c)}})
        self.assertEqual(rc, 0); self.assertIn("eng-1", out)
