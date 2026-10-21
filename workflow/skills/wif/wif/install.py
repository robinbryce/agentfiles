"""`wif install`: merge hooks + statusLine into settings.json files (diff first,
write only with --apply, timestamped backup), link the CLI into ~/.local/bin."""
from __future__ import annotations
import copy
import difflib
import json
import os
import sys
import time
from pathlib import Path

from . import config, paths


def entry_point() -> Path:
    return Path(__file__).resolve().parent.parent / "scripts" / "wif"


def patch_for(ep: Path) -> dict:
    h, s = f"{ep} hook", f"{ep} statusline"
    hk = lambda t: [{"hooks": [{"type": "command", "command": h, "timeout": t}]}]
    return {"statusLine": {"type": "command", "command": s, "refreshInterval": 30},
            "hooks": {"UserPromptSubmit": hk(10), "Stop": hk(10),
                      "SessionStart": [{"matcher": "startup|resume|clear|compact|fork", "hooks": [{"type": "command", "command": h, "timeout": 10}]}],
                      "SessionEnd": hk(5)}}


def is_wif_hook(cmd, hook_cmd: str) -> bool:
    """This checkout's hook, or one installed from another checkout of wif."""
    return isinstance(cmd, str) and (cmd == hook_cmd or cmd == "wif hook" or cmd.endswith("/scripts/wif hook"))


def strip_wif(settings: dict, hook_cmd: str) -> dict:
    out = copy.deepcopy(settings)
    hooks = out.get("hooks")
    hooks = hooks if isinstance(hooks, dict) else {}
    new_hooks = {}
    for ev, groups in hooks.items():
        kept = []
        for g in (groups if isinstance(groups, list) else []):
            if not isinstance(g, dict):
                continue
            inner = [x for x in (g.get("hooks") if isinstance(g.get("hooks"), list) else [])
                     if not (isinstance(x, dict) and is_wif_hook(x.get("command"), hook_cmd))]
            if inner:
                g2 = dict(g); g2["hooks"] = inner; kept.append(g2)
        if kept:
            new_hooks[ev] = kept
    if new_hooks:
        out["hooks"] = new_hooks
    else:
        out.pop("hooks", None)
    return out


def merged(settings: dict, ep: Path, force_statusline: bool = False) -> tuple[dict, bool]:
    """-> (new settings, statusline_kept) ; statusline_kept means a foreign one stayed."""
    p = patch_for(ep)
    hook_cmd = p["hooks"]["Stop"][0]["hooks"][0]["command"]
    out = strip_wif(settings, hook_cmd)
    sl = out.get("statusLine")
    sl = sl if isinstance(sl, dict) else None
    kept = False
    if sl is None or "wif statusline" in str(sl.get("command", "")) or force_statusline:
        out["statusLine"] = p["statusLine"]
    else:
        kept = True
    hooks = out.setdefault("hooks", {})
    for ev, groups in p["hooks"].items():
        hooks[ev] = (hooks.get(ev) or []) + groups
    return out, kept


def removed(settings: dict, ep: Path) -> dict:
    p = patch_for(ep)
    out = strip_wif(settings, p["hooks"]["Stop"][0]["hooks"][0]["command"])
    sl = out.get("statusLine")
    if isinstance(sl, dict) and "wif statusline" in str(sl.get("command", "")):
        out.pop("statusLine")
    return out


def main(args: list[str], out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    apply = "--apply" in args; remove = "--remove" in args; force = "--force-statusline" in args
    dirs: list[Path] = []; bin_dir = Path(os.environ.get("HOME", "~")).expanduser() / ".local" / "bin"
    it = iter(args)
    for a in it:
        if a == "--config-dir": dirs.append(Path(next(it, "")))
        elif a == "--bin": bin_dir = Path(next(it, ""))
        elif a in ("--apply", "--remove", "--force-statusline"): pass
        else:
            print(f"wif: unknown arg {a}", file=err); return 1
    if not dirs:
        h = paths.home()
        dirs = [h / f".claude-{p}" for p in config.PROFILES if (h / f".claude-{p}").is_dir()]
        if not dirs:
            print("wif: no ~/.claude-<profile> config dirs found; pass --config-dir", file=err); return 1
    ep = entry_point()
    rc = 0
    for d in dirs:
        f = d / "settings.json"
        cur_text = f.read_text(encoding="utf-8") if f.exists() else "{}"
        try:
            cur = json.loads(cur_text)
            if not isinstance(cur, dict):
                raise ValueError("not an object")
        except ValueError:
            print(f"== {f}: not valid JSON — skipped", file=err); rc = 1; continue
        if remove:
            new = removed(cur, ep)
        else:
            new, kept = merged(cur, ep, force)
            if kept:
                print(f"== {f}: keeping your existing statusLine ({cur['statusLine'].get('command')}); pass --force-statusline to replace", file=err)
        new_text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
        print(f"== {f}", file=out)
        if json.dumps(cur, sort_keys=True) == json.dumps(new, sort_keys=True):
            print("   (no change)", file=out)
        else:
            for ln in list(difflib.unified_diff(cur_text.splitlines(), new_text.splitlines(), lineterm="", n=2))[:80]:
                print(f"   {ln}", file=out)
        if apply:
            d.mkdir(parents=True, exist_ok=True)
            if f.exists():
                stamp = time.strftime("%Y%m%d%H%M%S"); n = 0
                while True:
                    bak = f.with_name(f"settings.json.bak.{stamp}" + (f"-{n}" if n else ""))
                    if not bak.exists():
                        break
                    n += 1
                bak.write_text(cur_text, encoding="utf-8")
            tmp = f.with_name("settings.json.tmp"); tmp.write_text(new_text, encoding="utf-8"); os.replace(tmp, f)
            print("   applied (backup kept)", file=out)
    if not remove:
        link = bin_dir / "wif"
        print(f"== {link} -> {ep}", file=out)
        if apply:
            bin_dir.mkdir(parents=True, exist_ok=True)
            if link.exists() and not link.is_symlink():
                print(f"   refusing to replace a regular file at {link}", file=err); return 1
            if link.is_symlink():
                link.unlink()
            link.symlink_to(ep)
            print("   linked", file=out)
        else:
            print("   (would link)", file=out)
    if not apply:
        print("dry run — re-run with --apply to write", file=out)
    return rc
