"""Dispatcher for the `wif` command."""
from __future__ import annotations
import sys

from . import commands, hooks, install, scan, show, statusline
from .commands import WifError

HELP = """wif <command> [args]
  show [--brief|--changes|--json|--all] [--session ID]   dashboard for the current scope (default)
  ls [--archived] [--json]          every stream and container in scope, with paths
  where [--json] [dir]              what stream/scope/account a directory resolves to
  scan [--prs] [--scope S] [--quiet] [--json]   rebuild index.json from disk (read-only elsewhere)
  adopt <task|.|path> [-s status] [-g goal] [-p parent] [-n next] [--scope S]   create/re-open a stream
  mark [-g goal] [-i intent] [-p position] [-n next] [-s status] [--done text] [--session ID]
                                    [--stream ID [--scope S]]   target a stream by id from anywhere
  note "<text>"                     followup for this stream;  note --done "<substring>" removes one
  tangent [--as <task>] "<text>"    candidate for a new stream (discovered-from this one); --as pins the
                                    container/task name (lowercase kebab) it becomes, else one is derived
  tangent --as <task> --for "<substring>"   re-pin the name of a recorded tangent
  remind <when> "<text>"            when = YYYY-MM-DD | +Nd | landed
  ctx [--session ID] [--json]       context % from the statusline dump (for rotation)
  sessions [stream] [-n N]          recent sessions and their goals/intents
  install [--apply] [--remove] [--force-statusline] [--config-dir DIR]... [--bin DIR]
  hook                              (stdin JSON) Claude Code hook entrypoint
  statusline                        (stdin JSON) Claude Code statusline entrypoint
  version
"""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv else "show"
    try:
        if cmd in ("help", "-h", "--help"):
            print(HELP, end=""); return 0
        if cmd == "version":
            from . import __version__
            print(__version__); return 0
        if cmd == "show": return show.main(argv)
        if cmd == "ls": return show.ls(argv)
        if cmd == "where": return commands.where(argv)
        if cmd == "scan": return scan.main(argv)
        if cmd == "adopt": return commands.adopt(argv)
        if cmd == "mark": return commands.mark(argv)
        if cmd == "note": return commands.note(argv, "followup")
        if cmd == "tangent": return commands.note(argv, "tangent")
        if cmd == "remind": return commands.note(argv, "reminder")
        if cmd == "ctx": return commands.ctx_cmd(argv)
        if cmd == "sessions": return commands.sessions(argv)
        if cmd == "install": return install.main(argv)
        if cmd == "hook": return hooks.main(argv)
        if cmd == "statusline": return statusline.main(argv)
        print(f"wif: unknown command '{cmd}' (try: wif help)", file=sys.stderr); return 1
    except WifError as e:
        print(f"wif: {e}", file=sys.stderr); return 1
