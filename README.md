# agentfiles

Robin's agent configuration: **dotfiles for coding agents.** One repo holds
the cross-profile skills, the always-on rules, and a template for each
isolated *profile* (personal, forestrie, home, justgames). It is a Claude Code
plugin marketplace and follows the open [Agent Skills](https://agentskills.io)
and [AGENTS.md](https://agents.md) standards, so pi, cursor-agent, Codex and
friends read the same files.

Design and migration plan:
[docs/plans/plan-2610-01-agent-config-reorg/](./docs/plans/plan-2610-01-agent-config-reorg/README.md).

## The model in one paragraph

A **profile** is a Claude Code config directory (`CLAUDE_CONFIG_DIR`), chosen
by the shell (direnv at a workspace root, or a `claude-<profile>` wrapper),
never inferred by the model. Each profile has its own tiny `CLAUDE.md`, its
always-on `rules/`, and a `settings.json` that enables exactly the plugin
marketplaces that profile may see: this repo for everyone, forestrie-agents
for forestrie work, a private agentfiles-home for life admin. **Skills** carry
content, **AGENTS.md** files carry routing (workspace and repo), **rules** carry
constraints, **hooks** enforce. What a repo commits (`AGENTS.md`,
`.claude/rules/`, `.agents/skills/`) is what cloud sessions and other tools
see; `agentfiles sync` produces that layer from the marketplace.

## Install

```bash
git clone git@github.com:robinbryce/agentfiles.git ~/agentfiles
~/agentfiles/bin/agentfiles bootstrap            # personal + forestrie (+ home if ~/agentfiles-home exists)
~/agentfiles/bin/agentfiles doctor               # what each profile will load
```

Then source `~/.config/agentfiles/wrappers.sh` from your shell rc (dotfiles
does this) and add the two `export` lines bootstrap prints to each workspace
`.envrc`, or rerun with `--envrc`.

Reduce `~/.claude/CLAUDE.md` to the stub in
[harness/claude-code.md](./harness/claude-code.md); it loads into every
profile.

## What lives here

| Path | Purpose |
|------|---------|
| [plugins/core](./plugins/core/) | `/core:plan-new`, `/core:save-status`, `/core:wif` (work-in-flight tracker; hooks via `wif install --apply`), `/core:worktrees-closeout`; planning, PR-description, fan-out and Linear rules; plan-naming hook |
| [plugins/research](./plugins/research/) | `/research:research-brief` |
| [rules/](./rules/) | always-on: clickable references; path-scoped: herdr handoff offers |
| [profiles/](./profiles/) | per-profile `CLAUDE.md` + `settings.json` templates |
| [bin/agentfiles](./bin/agentfiles) | `bootstrap`, `doctor`, `sync`, `link` |
| [harness/](./harness/) | Claude Code, pi, cursor-agent, local models |
| [incubator/](./incubator/) | drafts, not installed |

## Profiles

| Profile | Marketplaces | Selected by |
|---------|-------------|-------------|
| personal | agentfiles | `~/Dev/personal/.envrc`, or default |
| forestrie | agentfiles + [forestrie-agents](https://github.com/forestrie/forestrie-agents) | `~/Dev/personal/forestrie/.envrc` |
| home | agentfiles + agentfiles-home (private) | `~/Dev/personal/home/.envrc` |
| justgames | agentfiles (+ just-agents later) | `~/Dev/justgames/.envrc`; migration deferred |

## Using skills from other tools

```bash
npx skills add robinbryce/agentfiles -a pi -a cursor -g     # global, any supported agent
```

The skills CLI discovers skills through `marketplace.json`, so the same repo
serves 75+ agents without adapters.
