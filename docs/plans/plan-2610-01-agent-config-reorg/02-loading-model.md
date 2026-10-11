# 02 — Loading model: what loads where

Part of [plan 2610-01](./README.md). Sources:
[memory](https://code.claude.com/docs/en/memory),
[skills](https://code.claude.com/docs/en/skills),
[plugin loading](https://code.claude.com/docs/en/plugins/loading),
[settings](https://code.claude.com/docs/en/settings),
[cloud environments](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup),
[pi configuration](https://pi.dev/docs/latest/configuration.md),
[vercel-labs/skills](https://github.com/vercel-labs/skills).

## Delivery matrix

Rows are the kinds of content in the design; columns are the surfaces Robin
uses. "via" names the mechanism that delivers it.

| Content | Claude terminal (profile) | Claude cloud session | claude.ai chat / Cowork | Claude + Ollama (`claude-local`) | pi (profile) | cursor-agent | Codex / OpenCode / Copilot |
|---|---|---|---|---|---|---|---|
| Profile instructions (`<config>/CLAUDE.md`) | yes | no¹ | no | yes | yes, via `<agent-dir>/AGENTS.md` | no | global `AGENTS.md` where the tool has one |
| Always-on rules (`<config>/rules/*.md`) | yes, every session | via synced repo `.claude/rules/` | no | yes | folded into profile `AGENTS.md` | no | no |
| Workspace `AGENTS.md` (`~/Dev/personal/forestrie/`) | yes, directory walk-up² | no (single repo clone) | no | yes | yes, parent-dir walk-up | unverified | Codex: yes (walk-up) |
| Repo `AGENTS.md` | yes² | yes | yes (cloud) | yes | yes | yes | yes |
| Repo `.claude/rules/` (synced; `paths:`-scoped) | yes | yes | yes (cloud) | yes | no | no | no |
| Plugin skills / agents / hooks / MCP (marketplace) | yes, `/plugin:skill` | **no** | **no** | yes | no | no | no |
| Repo `.agents/skills/` + `.claude/skills/` symlinks (synced) | yes, bare `/skill` | yes | yes (cloud) | yes | via `.pi/skills` link or `npx skills -a pi` (Q3) | yes (`.agents/skills`) | yes (`.agents/skills`) |
| claude.ai account skills | yes, `/anthropic-skills:x` (synced ≥ 2.1.273) | yes | yes | no³ | no | no | no |
| Auto memory | per profile, per repo | no | n/a | yes | n/a | n/a | n/a |
| Project MCP (`.mcp.json`) | yes | yes | yes (cloud) | yes | pi extensions instead | partial | tool-specific |

¹ A cloud **setup script** may write `~/.claude/CLAUDE.md` in the VM; use it
for a one-line profile marker, not for content.
² Claude Code reads `AGENTS.md` natively only when no `CLAUDE.md` is in the
cwd or above, unless `instructionFiles: claude-md-and-agents-md` is set, which
the profiles set. Repos therefore keep **`AGENTS.md` only**, or a `CLAUDE.md`
that is just `@AGENTS.md`.
³ Account sync is skipped when `ANTHROPIC_AUTH_TOKEN` supplies the credential.

Consequences that shape the plan:

- **Cloud parity requires a committed layer** (`AGENTS.md`, `.claude/rules/`,
  `.agents/skills/` + symlinks). This is why `agentfiles sync` exists and why
  forestrie-agents keeps `rules/` and `sync/` as sources distinct from
  `plugins/`.
- **Profiles are the only mechanism that separates personal from work on the
  terminal.** Account skills and the default `~/.claude` are shared across
  everything, so neither may carry scope-specific content.
- **Local models change nothing about loading.** The same profile, plugins
  and rules apply; only account sync is lost.

---

## Session start, forestrie profile, in `~/Dev/personal/forestrie/canopy/`

What is in context before the first message, in load order:

| Step | Source | Mechanism | Size target |
|------|--------|-----------|-------------|
| 1 | `~/.claude-forestrie/CLAUDE.md` | user instructions | ≤ 40 lines |
| 2 | `~/.claude-forestrie/rules/*.md` without `paths:` | user rules | ≤ 3 files |
| 3 | `~/Dev/personal/forestrie/AGENTS.md` | directory walk-up | ≤ 80 lines |
| 4 | `canopy/AGENTS.md` | project instructions | ≤ 120 lines |
| 5 | `canopy/.claude/rules/*.md` without `paths:` (platform rules-of-the-road, commit conventions) | project rules | ≤ 2 files |
| 6 | skill **metadata** for `core`, `forestrie-core`, `forestrie-linear`, `engineering`, synced repo skills, account skills | plugin + skills discovery | ~100 tokens each |
| 7 | plugin hooks registered (`validate-plan`, `require-worktree`) | plugin `hooks.json` | 0 tokens |
| 8 | auto memory for this repo under this profile | `<config>/projects/…/memory` | ≤ 200 lines |

Loaded **on demand**:

- `canopy/.claude/rules/typescript-comments.md` when a `*.ts` file is read or
  edited (`paths:`).
- `rules-of-the-road-canopy.md` is unconditional in canopy because the
  manifest marks it so; in a monorepo it would be path-scoped instead.
- Any skill body when its description matches or the user invokes it:
  `/forestrie-core:arc-canopy` when the task mentions SCRAPI or x402;
  `/core:planning` when a file under `plans/` is touched.
- A subdirectory `AGENTS.md` when Claude first reads a file there.
- The `reviewer` subagent, preloaded with `rules-of-the-road-review`, when
  `/forestrie-core:review-changes` forks it.

Compared with today: `USER-CLAUDE.md` + the agentfiles router + the scope
`AGENTS.md` + the forestrie-agents `AGENTS.md` are all read at runtime, and
the model then still has to pick glossaries and rules from tables. In the
target state, steps 1–5 are short and declarative and everything else is
mechanism.

---

## Same repo, cloud session (`claude --cloud` or claude.ai/code)

| Loaded | Not loaded |
|--------|------------|
| `canopy/AGENTS.md` | profile `CLAUDE.md` (stub via setup script at most) |
| `canopy/.claude/rules/*` | profile rules |
| `canopy/.claude/skills/*` → `.agents/skills/*` (synced subset) | plugins (`core`, `forestrie-core`, …) and their hooks/agents |
| `canopy/.mcp.json` | user MCP |
| `canopy/.claude/settings.json` hooks + permissions | workspace `AGENTS.md`, auto memory |
| account skills (`/anthropic-skills:*`) | |

So a cloud session in canopy has the platform and canopy rules-of-the-road,
the review and status skills, and the canopy glossary. That is enough for the
tasks cloud sessions are used for (execute a committed plan, fix a PR). The
forestrie-specific hooks are not there, which is acceptable: the worktree
rule is moot in a fresh VM, and plan naming is checked when the branch is
teleported or reviewed locally.

---

## Home profile

Most home work happens in claude.ai with the Gmail / Drive / Calendar
connectors and in Cowork, not in a terminal. Two deliveries cover it:

1. `agentfiles-home` plugins in `~/.claude-home` for terminal and
   `claude-local` sessions (e.g. normalising statements with a local model so
   nothing leaves the machine).
2. The non-sensitive admin skills uploaded as **account skills**, so claude.ai
   and Cowork sessions have the same procedures and checklists.

The privacy rule is always-on in the profile and is the first paragraph of
each admin skill, because account skills cannot carry rules.

---

## pi and cursor-agent

- **pi**: `~/.pi-<profile>/AGENTS.md` is a symlink to
  `profiles/<p>/AGENTS.md`; skills are symlinked into `~/.pi-<profile>/skills/`
  from the enabled plugins' `skills/` dirs by bootstrap (or installed by
  `npx skills -g -a pi` if Q3 confirms a target). pi walks parent directories
  for `AGENTS.md`, so the workspace file and repo file load as in Claude Code.
  pi has no rules or hooks; the always-on rules are appended to the profile
  `AGENTS.md` by bootstrap.
- **cursor-agent**: reads repo `AGENTS.md` and `.agents/skills/`. Nothing
  else is attempted; `.cursor/rules/*.mdc` generation is dropped. For a repo
  outside any workspace, `agentfiles link <profile>` still provides a root
  `AGENTS.md`.

---

## Context budget rule

Anything loaded at step 1–5 above costs every session. Keep it to facts that
apply to every task in that profile. If a paragraph only matters for some
files, give it `paths:`; if it only matters for some tasks, make it a skill
with a precise description; if it must never be skipped, make it a hook.
