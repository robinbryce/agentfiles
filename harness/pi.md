# pi harness (pi.dev)

## Install

[dotfiles agents-bootstrap.sh](https://github.com/robinbryce/dotfiles) installs
the pi coding agent (npm global `@earendil-works/pi-coding-agent`, node from
mise via `languages-bootstrap.sh`) and wires the global hook below. Idempotent;
`--update` upgrades:

```bash
~/dotfiles/bin/agents-bootstrap.sh
```

## Global hook (machine-wide, zero per-repo setup)

pi loads `$PI_CODING_AGENT_DIR/AGENTS.md` (default `~/.pi/agent/AGENTS.md`) in
every session regardless of working directory. [USER-PI.md](../USER-PI.md) is
the maintained, version-controlled source — `agents-bootstrap.sh` symlinks it
into the default dir and both profile dirs:

```
~/.pi/agent/AGENTS.md      -> ~/agentfiles/USER-PI.md
~/.pi-personal/AGENTS.md   -> ~/agentfiles/USER-PI.md
~/.pi-justgames/AGENTS.md  -> ~/agentfiles/USER-PI.md
```

pi has no `@import` mechanism, so USER-PI.md *instructs* the agent to read
[AGENTS.md](../AGENTS.md) and route by scope (the generic-harness pattern in
[generic.md](./generic.md)), rather than inlining it the way USER-CLAUDE.md
does for Claude Code.

## Per-repo scope lock

pi natively loads repo-root `AGENTS.md` (and parent directories up the tree),
so the existing per-repo link serves pi with **no extra step** — the same
symlink that serves cursor-agent and locks scope for Claude Code:

```bash
agentfiles-link <scope>   # AGENTS.md -> scopes/<scope>/AGENTS.md
```

## Profiles / login

`pi` / `pi-personal` / `pi-justgames` (dotfiles `profiles/common/agents.sh`)
select `PI_CODING_AGENT_DIR` by `DOTFILES_ROLE`, mirroring `claude()`. Log in
once per profile (`pi-personal` then `/login`), or let project direnv supply
`ANTHROPIC_API_KEY` per tree — same key policy as the other harnesses: keys
live in project `.envrc`/`.env.secret`, never in dotfiles.

## Skills

pi implements the Agent Skills standard (`SKILL.md` directories) and loads
from `~/.pi/agent/skills/`, `~/.agents/skills/`, and repo `.pi/skills/` /
`.agents/skills/`. Install by copying or symlinking, same sources and same
one-scope rule as [claude-code.md](./claude-code.md#skills):

- `scopes/<scope>/workflow/skills/` (scope-specific overlays)
- `workflow/skills/` (cross-scope overlays)
- `vendored/<source>/skills/` (pinned third-party)

## cmux

cmux supports pi natively: `cmux hooks pi install` generates
`~/.pi/agent/extensions/cmux-session.ts` (a pi extension, not the legacy
hooks API) giving Feed tool telemetry (non-blocking — pi has no permission
prompts), session restore (`pi --session <id>`), and workspace auto-naming.
`agents-bootstrap.sh` runs the install and then links the extension into
`~/.pi-personal/extensions/` and `~/.pi-justgames/extensions/`, because pi
discovers extensions from `$PI_CODING_AGENT_DIR/extensions/` — without the
links the profile wrappers would silently lose the cmux integration.
`CMUX_PI_HOOKS_DISABLED=1` opts a shell out. A `pi` tab-bar button/action
lives in dotfiles `config/cmux/cmux.json` (`cmd+shift+i`).

## Trust

`defaultProjectTrust` in `~/.pi/agent/settings.json` gates loading of
project-local resources (`.pi/` settings, skills, extensions). Leave it on
`"ask"` — the repo overlay precedence in [AGENTS.md](../AGENTS.md) assumes
project files are deliberately trusted, not auto-loaded.
