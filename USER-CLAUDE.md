<!--
This file is Robin's personal Claude Code "User instructions" memory:
https://code.claude.com/docs/en/memory.md#choose-where-to-put-claude-md-files

It is symlinked into place at ~/.claude/CLAUDE.md:

    ln -s ~/agentfiles/USER-CLAUDE.md ~/.claude/CLAUDE.md

Because of that symlink, this file's content loads into EVERY Claude Code
session on this machine, in every project, regardless of working directory
or how deeply nested the shell is (tmux/nvim/cmux don't matter — this isn't
cwd-driven). Keep it small: it costs context on every single session. Put
project- or scope-specific content in scopes/, not here.

The @import below uses an absolute `~/`-anchored path rather than a path
relative to this file. That's deliberate: this file is reached through a
symlink, and relying on relative-import resolution behaving one particular
way (relative to the symlink's location vs. its target's real location) is
an assumption not worth making when an absolute path sidesteps the question
entirely.

This comment is stripped from injected session context (per the docs above)
but stays visible via `cat`, `git show`, or the Read tool — so an agent
inspecting this file directly still gets the full picture.
-->

# User-level Claude Code memory — routes to agentfiles

This is a router, not content: it hands off to
[agentfiles](https://github.com/robinbryce/agentfiles), which is where all
actual workflow/rule/skill/scope content lives. See
[README.md](./README.md) for what that repo is.

@~/agentfiles/AGENTS.md
