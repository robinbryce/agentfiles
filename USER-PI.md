<!--
This file is Robin's personal pi (pi.dev) global instructions — the analog
of USER-CLAUDE.md for the pi coding agent. pi loads AGENTS.md from its
config dir in every session (https://pi.dev/docs/latest).

It is symlinked into place by dotfiles/bin/agents-bootstrap.sh:

    ~/.pi/agent/AGENTS.md      -> ~/agentfiles/USER-PI.md   (default dir)
    ~/.pi-personal/AGENTS.md   -> ~/agentfiles/USER-PI.md   (PI_CODING_AGENT_DIR profiles,
    ~/.pi-justgames/AGENTS.md  -> ~/agentfiles/USER-PI.md    see dotfiles profiles/common/agents.sh)

Unlike Claude Code, pi has no @import mechanism, so this file instructs the
agent to read the router rather than inlining it. Paths are absolute
(`~/`-anchored) for the same symlink-resolution reason documented in
USER-CLAUDE.md. Keep it small: it costs context on every session.
-->

# User-level pi instructions — routes to agentfiles

This is a router, not content: all workflow/rule/skill/scope content lives in
[agentfiles](https://github.com/robinbryce/agentfiles) at `~/agentfiles/`.

Before starting any task, read `~/agentfiles/AGENTS.md` and follow its
loading order: determine scope from the working directory, then load **only**
that scope's `~/agentfiles/scopes/<scope>/AGENTS.md`, then the working repo's
own `AGENTS.md` overlay. Never load more than one scope per task.

If the project root already provided an `AGENTS.md` (pi loads repo-root and
parent-directory `AGENTS.md` files natively — e.g. one linked by
`agentfiles-link`), that file **is** the scope: skip cwd-based scope
inference and do not load a second scope.
