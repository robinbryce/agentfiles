# agentfiles — for an agent editing this repository

This repo is a **Claude Code plugin marketplace plus profile templates**. It is
not loaded into sessions by reading this file; it is installed into
`~/.claude-<profile>` by `bin/agentfiles bootstrap`. See
[README.md](./README.md) for the model and
[docs/plans/plan-2610-01-agent-config-reorg/](./docs/plans/plan-2610-01-agent-config-reorg/README.md)
for the design.

## Layout

| Path | What |
|------|------|
| `.claude-plugin/marketplace.json` | marketplace `agentfiles`; entries resolve under `plugins/` |
| `plugins/<name>/` | one plugin: `.claude-plugin/plugin.json`, `skills/<skill>/SKILL.md`, optional `hooks/`, `agents/` |
| `rules/*.md` | always-on rule files, symlinked into every profile's `rules/` (plugins cannot ship rules) |
| `profiles/<p>/` | `CLAUDE.md` (≤ 40 lines), `settings.json` template, optional `rules/`; `AGENTS.md` → `CLAUDE.md` |
| `bin/agentfiles` | `bootstrap`, `doctor`, `sync`, `link` |
| `harness/` | short per-harness notes |
| `incubator/` | drafts, never installed |

## Rules for changes

- **A skill lives in the repo of the narrowest audience that needs it.** Team
  content goes to forestrie-agents, private content to agentfiles-home.
- Skill frontmatter follows the [Agent Skills spec](https://agentskills.io/specification):
  `name` equals the directory name; `description` says what and when.
  Background rules are skills with `user-invocable: false`; add `paths:` when
  they only matter for some files.
- A rule in `rules/` has at most a `paths:` frontmatter. Keep always-on rules
  to a handful: each costs every session in every profile.
- Reference scripts as `${CLAUDE_SKILL_DIR}/scripts/...` and hook scripts as
  `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...`.
- After any change: `claude plugin validate .` and `bin/agentfiles doctor`.
- Plans for this repo use `/core:plan-new` into `docs/plans/`.
