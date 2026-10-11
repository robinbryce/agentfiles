---
id: 2610-01
status: draft
created: 2026-10-11
refs: []
---

# Plan 2610-01 — agent config reorg: profiles, marketplaces, skills

**Status:** DRAFT · **Created:** 2026-10-11

Reorganise [agentfiles](https://github.com/robinbryce/agentfiles) and
[forestrie-agents](https://github.com/forestrie/forestrie-agents) from the
ground up so that skills and routing load **automatically and
deterministically per context** (personal / work / home), reach **every
surface** Robin uses (Claude Code terminal, Claude cloud sessions and
claude.ai, pi, cursor-agent, local models), and are managed from **one source
of truth per trust boundary**.

| Doc | What it covers |
|-----|----------------|
| this README | context, goal, the eight design decisions, profiles, open questions |
| [01-target-layout.md](./01-target-layout.md) | repos, directory trees, manifests, profile files, direnv |
| [02-loading-model.md](./02-loading-model.md) | what loads where on each surface; the session-start routing sequence |
| [03-migration.md](./03-migration.md) | phased plan, concrete commands, file-by-file mapping of today's content |
| [handoff.md](./handoff.md) | resume prompt for the next session |

---

## Context

### Where we are (2026-10-11)

Two repos, same shape, both built on a **model-side router**: a small
`AGENTS.md` imported into every session tells the agent to look at a cwd
table, pick one "scope", and then read only that scope's index. Content is
mostly tables of links; commands are markdown prompts the user pastes; the one
hook is wired by hand into `~/.claude/settings.json`.

- [agentfiles `main`](https://github.com/robinbryce/agentfiles/tree/084df8f3) —
  `scopes/{forestrie,justgames,personal}`, `workflow/{commands,rules,skills}`,
  `harness/`, `USER-CLAUDE.md` (`@import`ed from `~/.claude/CLAUDE.md`),
  `USER-PI.md`.
- [forestrie-agents `main`](https://github.com/forestrie/forestrie-agents/tree/32cad83) —
  `arc-context/` glossaries, `rules-of-the-road/` per-repo invariants,
  `workflow/{commands,rules,skills}`, `vendored/matt-skills` (the engineering
  skills are present **twice**: `vendored/skills/` and
  `vendored/matt-skills/skills/`), `harness/hooks/require-worktree.sh`.
- An unmerged branch,
  [`robin/skills-as-slash-commands`](https://github.com/robinbryce/agentfiles/tree/7b28622)
  (2026-07-25), already did the first step: commands → `<name>/SKILL.md`
  skills, rules → skills with `paths:` and `user-invocable: false`, a
  [`marketplace.json`](https://github.com/robinbryce/agentfiles/blob/7b28622/.claude-plugin/marketplace.json)
  exposing each scope as a plugin, and
  [`bin/agentfiles-sync`](https://github.com/robinbryce/agentfiles/blob/7b28622/bin/agentfiles-sync)
  which symlinks skills into `.claude/skills`, `.cursor/skills`, `.agents/skills`
  per repo (git-excluded). **This plan keeps that work and builds on it.**
- Machine state: three Claude config dirs (`~/.claude` default,
  `~/.claude-personal`, `~/.claude-justgames`) selected by `claude()` wrappers
  in dotfiles on `DOTFILES_ROLE`; pi profiles the same way; `cursor-agent`
  and `ollama` installed; `codex`/`opencode` not installed. The default
  `~/.claude` still carries the plan hook and Linear permissions, so
  configuration is split across the default dir and the profile dirs.

What creaks:

1. **Scope is inferred by the model** from a path table. It costs context on
   every session, it is probabilistic, and it is the thing most likely to leak
   one context into another.
2. **Nothing reaches cloud sessions.** User-level `CLAUDE.md`, skills, hooks
   and plugins all live on the laptop. A `claude --cloud` run or a claude.ai
   session sees only what the repo commits.
3. **Installation is manual** (symlink this, paste that hook JSON). No single
   command produces a known-good machine, and no command tells you what a given
   profile will load.
4. **Routing docs restate content** (tables of links the model must read and
   choose from) rather than letting the harness load by path or description.
5. **Three audiences are mixed** in one layout: team standards (forestrie), a
   personal overlay, and life admin that does not exist yet.

### What changed in the ecosystem

- **Agent Skills is an open standard** ([agentskills.io](https://agentskills.io/specification)):
  `name` + `description` frontmatter, `scripts/ references/ assets/`,
  progressive disclosure (metadata ≈100 tokens at startup, body on activation).
  Adopted by 40+ tools including Claude Code, Codex, Cursor, Gemini CLI,
  GitHub Copilot, OpenCode and pi. `SKILL.md` is the portable unit.
- **AGENTS.md is the portable instruction file** (Linux Foundation / AAIF,
  60k+ repos). Claude Code ≥ 2.1.277
  [reads it natively](https://code.claude.com/docs/en/memory#agents-md) when no
  `CLAUDE.md` is present, walking **up** the directory tree at launch and
  **down** on demand. pi, cursor-agent, Codex and OpenCode read it too.
- **Claude Code plugins + marketplaces** are the distribution mechanism
  ([plugin loading reference](https://code.claude.com/docs/en/plugins/loading),
  [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference)):
  a plugin bundles `skills/ agents/ hooks/ .mcp.json settings.json`; a
  marketplace is any git repo with `.claude-plugin/marketplace.json`; a
  marketplace added from a **local path loads plugins in place** (edits are
  live, no version bump); `enabledPlugins` and `extraKnownMarketplaces` work at
  user, project (`.claude/settings.json`, committed) and local scope, so a
  **repo can declare which marketplace and plugins its collaborators get**.
  Plugins cannot ship `CLAUDE.md` or `rules/`; instructions in a plugin are
  skills.
- **`CLAUDE_CONFIG_DIR` is complete isolation**: settings, `CLAUDE.md`,
  `rules/`, `skills/`, plugins cache, marketplaces, sessions, auto-memory and
  login all move with it.
- **Cloud sessions load only what the repo commits** plus claude.ai account
  skills ([what carries over](https://code.claude.com/docs/en/cloud-environments#what-carries-over-from-your-setup)):
  repo `CLAUDE.md`/`AGENTS.md`, `.claude/{rules,skills,agents,commands}`,
  `.mcp.json`, repo `settings.json` hooks. **Plugins never load in cloud
  sessions**, whether user- or repo-declared. A setup script may write
  `~/.claude/CLAUDE.md` in the VM.
- **claude.ai account skills sync to the terminal** (≥ 2.1.273) into
  `<config>/skills/synced/`, invoked as `/anthropic-skills:<name>`; they also
  load in cloud sessions and Cowork. One account, so not scope-separated.
- **`npx skills`** ([vercel-labs/skills](https://github.com/vercel-labs/skills))
  installs a skills repo into any of 75+ agents' directories, discovering
  skills from `marketplace.json` / `plugin.json` too. It is the generic
  replacement for hand-rolled symlink loops.
- **Local models**: Ollama ≥ 0.14 speaks the Anthropic Messages API
  ([ollama blog](https://ollama.com/blog/claude)), so **Claude Code itself,
  with its full plugin and skill stack, runs against a local model** via
  `ANTHROPIC_BASE_URL`. pi reaches any OpenAI-compatible endpoint via
  `models.json`.

---

## Goal

A fresh machine runs one bootstrap and gets three isolated Claude profiles,
each of which automatically loads exactly its own skills, rules, hooks and
instructions — in the terminal, in cloud sessions, under pi or cursor-agent,
and against a local model — with every piece of content authored once in the
marketplace repo that owns it.

---

## Design decisions

| # | Decision | Replaces |
|---|----------|----------|
| **D1** | **Scope is a profile, selected by the shell, never inferred by the model.** `CLAUDE_CONFIG_DIR=~/.claude-<profile>` (and `PI_CODING_AGENT_DIR`) is set by direnv at each workspace root and by the `claude-<profile>` wrappers. The profile dir carries that scope's `CLAUDE.md`, `rules/`, `settings.json` (marketplaces + enabled plugins), plugin cache, sessions and memory. | the cwd table in `AGENTS.md`, "determine scope first" |
| **D2** | **Skill is the unit of content; AGENTS.md is the unit of routing; rules are for always-on or path-scoped constraints.** No `commands/` directory, no link-table routers. A skill's `description` is its trigger; a rule's `paths:` is its trigger; AGENTS.md carries only what must be read every session. | commands as pasted prompts, index tables, requestable rules |
| **D3** | **Plugin is the unit of distribution; one marketplace per trust boundary.** `robinbryce/agentfiles` (personal, public), `forestrie/forestrie-agents` (org), `robinbryce/agentfiles-home` (private: tax, finance, admin, research). Each profile adds only its marketplaces. | per-repo symlink installs as the primary path; vendored copies |
| **D4** | **Repos carry what cloud needs; profiles carry what is personal; the marketplace is the source of truth for both.** A repo commits `AGENTS.md`, `.claude/rules/`, and a vendored `.agents/skills/` (with `.claude/skills/` relative symlinks) produced by a sync, plus `.claude/settings.json` declaring the org marketplace and plugins for terminal users. | nothing reaching cloud sessions |
| **D5** | **Cross-tool by standard, not by adapter.** `SKILL.md` + `AGENTS.md` serve every harness. Claude-only extras (`hooks/`, `agents/`, plugin `settings.json`) live in the plugin and are ignored elsewhere. `.cursor/rules/*.mdc` generation is dropped. | per-harness adapter docs and shims |
| **D6** | **Mechanism over instruction.** Hooks enforce (plan naming, worktree-required); `paths:` loads rules by file; descriptions load skills by task; `claudeMdExcludes` trims noise. Prose like "never load a second scope" disappears because it cannot happen. | AGENTS.md prose guardrails |
| **D7** | **One bootstrap, one doctor.** `agentfiles bootstrap` creates/updates profile dirs and shell wrappers; `agentfiles doctor` reports, per profile, which marketplaces, plugins, rules and instruction files will load; `agentfiles sync <repo>` vendors a repo's committed layer. All thin shells over `claude plugin …` and `npx skills`. | README install steps |
| **D8** | **Local models are a profile variant, not a different stack.** `claude-local` (and `pi-local`) are the same profiles pointed at Ollama; every skill and hook still applies. | nothing |

### Why profiles rather than one dir with a router

- Isolation is structural: a forestrie session cannot see the home tax skill
  because it is not installed in that config dir.
- Auto-memory, sessions, permissions and plugin state are per profile for
  free.
- Different accounts per profile become possible (e.g. a Team seat for
  forestrie later) without touching content.
- The model reads one small `CLAUDE.md` per session instead of a router plus
  a scope index.

### Why marketplace-first, with symlinks demoted

The July branch chose symlinked, unnamespaced skills so a scope's
`/save-status` could shadow the common one. With profiles there is no
cross-scope collision to arbitrate: each profile enables exactly its own
plugins. Plugins give in-place loading from a local checkout (same "edit and it
is live" property as symlinks), auto-installed hooks, agents and MCP, a
`claude plugin validate` check, and repo-declared installs for collaborators.
The cost is namespacing: `/core:plan-new` rather than `/plan-new`. The
`npx skills` path remains for the committed repo layer and for non-Claude
harnesses, so nothing is lost.

---

## Profiles

| Profile | Config dir | Marketplaces | Selected by | Typical work |
|---------|-----------|--------------|-------------|--------------|
| `personal` | `~/.claude-personal` | `agentfiles` | default; `~/Dev/personal/.envrc` (excluding forestrie) | robinbryce repos, OSS, drafts such as the COSE receipts profile |
| `forestrie` | `~/.claude-forestrie` | `agentfiles` + `forestrie-agents` | `~/Dev/personal/forestrie/.envrc` | all forestrie org repos |
| `home` | `~/.claude-home` | `agentfiles` + `agentfiles-home` (private) | `~/Home/.envrc` (or wrapper `claude-home`) | tax, finance, household admin, research briefs |
| `justgames` | `~/.claude-justgames` | `agentfiles` + `SentientDogs/just-agents` | `~/Dev/justgames/.envrc` | unchanged; follows the same pattern, not in scope for Phase 1–3 |

The default `~/.claude` is retired as a working profile; it keeps only what
Claude Code needs to exist and a `CLAUDE.md` that says "you are in the
unprofiled default; run `claude-<profile>`".

---

## Non-goals

- Rewriting the content of existing rules and skills. They move; they are not
  re-authored, except to split router prose from substance.
- Changing forestrie-agents' promotion policy or Linear conventions.
- Supporting harnesses Robin does not run (Codex, OpenCode, Gemini CLI get the
  standard layout for free and nothing more).

---

## Open questions — verify before Phase 2

| # | Question | Why it matters | How to check |
|---|----------|----------------|--------------|
| Q1 | Does a plugin directory under a repo's `.claude/skills/` (a `@skills-dir` plugin) load in **cloud sessions**? | If yes, repos can commit a whole plugin incl. hooks; if no, repos commit plain skills + rules only (the plan assumes **no**). | Commit a `.claude/skills/probe/` with `.claude-plugin/plugin.json` + one hook; run `claude --cloud "run /context"`. |
| Q2 | Does `~/.claude/CLAUDE.md` load **in addition** to `$CLAUDE_CONFIG_DIR/CLAUDE.md`? | This session (`CLAUDE_CONFIG_DIR=~/.claude-personal`) had `~/.claude/CLAUDE.md` in context. If both load, the default dir must be emptied in Phase 1. | `/context` under each wrapper after bootstrap. |
| Q3 | Does `npx skills` have a pi target, and does pi read `~/.agents/skills`? | Decides whether pi profiles get skills via `npx skills -a pi -g` or via bootstrap symlinks into `~/.pi-<profile>/skills/`. | `npx skills add --help`; pi docs list only `<agent-dir>/skills` and `.pi/skills`. |
| Q4 | Can a marketplace entry with `source: github` + `sha` and `plugin.json`-less upstream declare `skills: [...]` paths (for pinning `matt-skills` without vendoring)? | Removes the duplicated vendored copies in forestrie-agents. | Add the entry; `claude plugin install`; `claude plugin details`. |
| Q5 | Which claude.ai account skills to upload so cloud/Cowork sessions get the cross-scope set (`planning`, `pr-descriptions`, `clickable-references`)? | They are account-wide, not profile-scoped; only truly generic content belongs there. | Decide list; upload via claude.ai Skills settings. |

---

## Verification

- `agentfiles doctor` run under each of `claude-personal`, `claude-forestrie`,
  `claude-home` prints exactly the expected marketplaces, plugins, rules and
  instruction files, and nothing from another profile.
- `claude plugin validate ~/agentfiles`, `… ~/Dev/personal/forestrie/forestrie-agents`,
  `… ~/agentfiles-home` all pass.
- In a forestrie repo: `/context` shows `AGENTS.md` (repo), the workspace
  `AGENTS.md`, `.claude/rules/*`, and `forestrie-core` skills; no `scopes/`
  router text.
- `claude --cloud "run /context"` on a synced forestrie repo shows the same
  rules and the vendored skills.
- `pi` and `cursor-agent` in the same repo list `/plan-new`-equivalent skills.
- `claude-local` (Ollama) starts, lists the same plugins, and `/core:plan-new`
  works.
- The old `~/.claude/CLAUDE.md` `@import` router is gone and no session
  prints "determine scope".
