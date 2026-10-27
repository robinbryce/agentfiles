"""Account, Scope and Backing resolution. Pure functions of env + filesystem."""
from __future__ import annotations
import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from . import config, proc

HERDR_DIR = ".worktrees-herdr"


def home() -> Path:
    return Path(os.environ.get("HOME") or os.path.expanduser("~")).resolve()


def config_dir(scope: str | None = None) -> Path:
    """The account's config dir. Inside a Claude session CLAUDE_CONFIG_DIR says
    which profile this is. In a bare shell (a herdr pane, `herdr-task`'s child
    `wif adopt`) it is unset; then the account is the profile that serves the
    directory's <scope> — `~/.claude-<scope>` when it exists — the same rule
    the `claude` launcher uses to pick a profile from the directory. Only when
    no such profile exists does the unprofiled `~/.claude` (personal) apply."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else Path.cwd() / p
    if scope:
        prof = home() / f".claude-{scope}"
        if prof.is_dir():
            return prof
    return home() / ".claude"


def account(cfg: Path | None = None) -> str:
    """~/.claude-<profile> -> <profile>; the unprofiled ~/.claude counts as personal."""
    name = (cfg or config_dir()).name
    if name == ".claude":
        return "personal"
    return name[len(".claude-"):] if name.startswith(".claude-") and len(name) > len(".claude-") else name


def known_scopes() -> tuple[str, ...]:
    raw = os.environ.get("WIF_ACCOUNT_SCOPES")
    return tuple(raw.split()) if raw else config.DEFAULT_SCOPES


def account_serves(acct: str, scope: str) -> bool:
    raw = os.environ.get("WIF_ACCOUNT_SCOPES")
    if raw:
        return scope in raw.split()
    if acct == scope:
        return True
    # personal stands in for a forestrie or home profile not set up on this machine
    return acct == "personal" and scope in ("forestrie", "home") and not (home() / f".claude-{scope}").is_dir()


def scope_root(scope: str) -> Path | None:
    override = os.environ.get("WIF_ROOT_" + "".join(c if c.isalnum() else "_" for c in scope.upper()))
    if override:
        return Path(override)
    h = home()
    return {"justgames": h / "Dev/justgames/code", "forestrie": h / "Dev/personal/forestrie",
            "home": h / "Dev/personal/home", "personal": h / "Dev/personal"}.get(scope)


def scope_of(path: Path) -> str:
    """Workspace roots per scope; each agentfiles profile selects its own via direnv."""
    h = home()
    p = Path(path)
    def under(base: Path) -> bool:
        try:
            p.relative_to(base)
            return True
        except ValueError:
            return False
    if under(h / "Dev/personal/forestrie"):
        return "forestrie"
    if under(h / "Dev/personal/home"):
        return "home"
    if under(h / "Dev/justgames"):
        return "justgames"
    return "personal"


def ledger_dir(scope: str, cfg: Path | None = None) -> Path:
    return (cfg or config_dir(scope)) / "wif" / scope


def ledger_init(scope: str, cfg: Path | None = None) -> Path:
    l = ledger_dir(scope, cfg)
    for sub in ("streams", "sessions", "archive", "cache"):
        (l / sub).mkdir(parents=True, exist_ok=True)
    return l


def backing_of(cwd: Path) -> tuple[str, str, Path | None]:
    """-> (kind, id, path). kind in herdr|repo|none. Spaces in names survive."""
    try:
        phys = Path(cwd).resolve(strict=True)
    except (OSError, RuntimeError):
        return "none", "", None
    parts = phys.parts
    if HERDR_DIR in parts:
        i = parts.index(HERDR_DIR)
        if i + 1 < len(parts):
            task = unicodedata.normalize("NFC", parts[i + 1])
            return "herdr", task, Path(*parts[: i + 2])
    rc, top = proc.git(str(phys), "rev-parse", "--show-toplevel", timeout=3)
    if rc != 0 or not top:
        return "none", "", None
    rc, common = proc.git(str(phys), "rev-parse", "--git-common-dir", timeout=3)
    if rc != 0 or not common:
        return "none", "", None
    cpath = Path(common)
    if not cpath.is_absolute():
        cpath = phys / cpath
    try:
        cpath = cpath.resolve()
    except OSError:
        pass
    if ".git" in cpath.parts and "modules" in cpath.parts and cpath.parts.index("modules") == cpath.parts.index(".git") + 1:
        repo = Path(top).name                       # submodule checkout
    else:
        repo = cpath.parent.name
    rc, branch = proc.git(str(phys), "symbolic-ref", "--short", "-q", "HEAD", timeout=3)
    if rc != 0 or not branch:
        branch = "detached"
    sid = unicodedata.normalize("NFC", f"{repo}--{branch.replace('/', '-').replace(' ', '-')}")
    return "repo", sid, Path(top)


@dataclass
class Ctx:
    account: str
    scope: str
    root: Path | None
    served: bool
    kind: str
    id: str
    path: Path | None
    config_dir: Path
    ledger: Path
    stream_file: Path | None = None
    extra: dict = field(default_factory=dict)

    @property
    def archive_file(self) -> Path | None:
        return self.ledger / "archive" / f"{self.id}.md" if self.id else None

    def bindable(self) -> bool:
        """May a session auto-bind here? herdr: yes unless the stream is closed
        (archived and not re-opened). repo: only once a stream exists."""
        if not self.served or not self.id:
            return False
        if self.archive_file and self.archive_file.exists() and not (self.stream_file and self.stream_file.exists()):
            return False
        if self.kind == "herdr":
            return True
        return bool(self.stream_file and self.stream_file.exists())

    def status(self) -> str:
        from .ledger import Stream
        if self.stream_file and self.stream_file.exists():
            return Stream.load(self.stream_file).get("status") or ""
        return ""

    def as_json(self) -> dict:
        st = self.status()
        return {"account": self.account, "scope": self.scope, "root": str(self.root or ""),
                "served": self.served, "kind": self.kind, "id": self.id, "path": str(self.path or ""),
                "ledger": str(self.ledger), "stream_file": str(self.stream_file or ""),
                "stream_exists": bool(st), "status": st, "bindable": self.bindable(),
                "config_dir": str(self.config_dir)}


def resolve(cwd: str | Path | None = None, scope: str | None = None) -> Ctx:
    p = Path(cwd) if cwd else Path.cwd()
    try:
        phys = p.resolve()
    except OSError:
        phys = p
    sc = scope or scope_of(phys)
    cfg = config_dir(sc)
    acct = account(cfg)
    kind, sid, bpath = backing_of(p)
    led = ledger_dir(sc, cfg)
    return Ctx(account=acct, scope=sc, root=scope_root(sc), served=account_serves(acct, sc),
               kind=kind, id=sid, path=bpath, config_dir=cfg, ledger=led,
               stream_file=(led / "streams" / f"{sid}.md") if sid else None)
