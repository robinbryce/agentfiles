# 03 — Migration

Part of [plan 2610-01](./README.md). Five phases; each is independently
shippable and leaves the previous state working. Phase 1 is personal and
needs no one else; Phase 2 touches the forestrie org and goes through PRs.

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| 0 | decisions verified (Q1–Q5), July branch merged | — |
| 1 | agentfiles as marketplace + profiles + `bin/agentfiles`; three profiles bootstrapped; router retired | 0 |
| 2 | forestrie-agents as marketplace; committed layer synced into canopy (pilot), then all repos; workspace `AGENTS.md` | 1, Q1 |
| 3 | agentfiles-home private marketplace; `home` profile; account skill uploads | 1 |
| 4 | pi profiles, cursor-agent, `claude-local` / `pi-local` | 1 |
| 5 | delete legacy layouts and docs | 2, 3, 4 |

---

## Phase 0 — verify and converge

1. Merge or rebase [`robin/skills-as-slash-commands`](https://github.com/robinbryce/agentfiles/tree/7b28622)
   into `main`. It already has the skills-as-directories conversion, the
   `paths:`-scoped rules, and a working `marketplace.json`; Phase 1 moves
   those files rather than re-creating them.
2. Run the Q1–Q5 checks from the [README](./README.md#open-questions--verify-before-phase-2).
   Record answers in this file. Q1 decides whether a repo's committed layer
   can be a whole plugin (hooks included) or plain skills + rules.
3. Decide the `home` profile's root directory (`~/Home` assumed) and whether
   `justgames` moves now or stays on the old wrappers.

Done when: `main` contains the July branch, Q1–Q5 have recorded answers.

## Phase 1 — agentfiles

1. **Restructure** (git mv, keep history):
   - `workflow/skills/*` and `workflow/rules/*` (skill form) → `plugins/core/skills/*`
   - `harness/hooks/{hooks.json,validate-plan.sh}` → `plugins/core/hooks/`
   - `workflow/rules/clickable-references`, `herdr-session-handoff` → `rules/*.md`
     (back to plain rule files; `herdr-session-handoff.md` gets
     `paths: ["**/.worktrees-herdr/**"]`)
   - `scopes/<s>/AGENTS.md` planning-params tables → `profiles/<s>/CLAUDE.md`
   - `scopes/forestrie/incubator/*` → `incubator/forestrie/*`
   - `scopes/justgames/workflow/rules/linear-auth` → stays personal; becomes
     `profiles/justgames/rules/linear-auth.md` (profile-local rule) or moves
     to `just-agents`
   - delete `scopes/`, `USER-CLAUDE.md`, `USER-PI.md`, `workflow/`,
     `vendored/README.md` (nothing vendored here)
2. **Manifests**: rewrite `.claude-plugin/marketplace.json` with
   `pluginRoot: ./plugins` and entries `core`, `research`; write
   `plugins/core/.claude-plugin/plugin.json`; `claude plugin validate .`.
3. **Profiles**: write `profiles/{personal,forestrie,home,justgames}/{CLAUDE.md,AGENTS.md,settings.json}`
   per [01-target-layout.md](./01-target-layout.md#profilesforestriesettingsjson-template).
4. **`bin/agentfiles`**: `bootstrap`, `doctor`, `sync`, `link`. Reuse
   `bin/agentfiles-sync` from the July branch as the basis of `sync`, but
   switch the skills step to `npx skills add` and add the rules + marker
   steps; keep its `.git/info/exclude` behaviour only for `link`.
5. **Bootstrap this machine**: `bin/agentfiles bootstrap personal forestrie`.
   Expect `~/.claude-forestrie` to be created, `claude plugin list` under it
   to show `core@agentfiles`, and `/context` to show the profile `CLAUDE.md`
   and `rules/`.
6. **Retire the router**: remove `~/.claude/CLAUDE.md` symlink; replace with a
   two-line file pointing at the wrappers; move the hook and Linear permission
   out of `~/.claude/settings.json` (the hook now ships with `core`; the
   permission lives in the profile templates). Resolve Q2 here.
7. **dotfiles**: `profiles/common/agents.sh` sources
   `~/.config/agentfiles/wrappers.sh`; add `.envrc` exports at
   `~/Dev/personal/forestrie/`, `~/Dev/personal/`, `~/Dev/justgames/`.
8. **Research plugin**: seed `plugins/research/skills/research-brief` from the
   existing deep-research habits (brief template, source-triage checklist).
   Small; the point is to have the slot.

Done when: README verification items 1, 2 (agentfiles), and 7 pass; a session
started in `~/Dev/personal/forestrie/canopy` under `claude` (no explicit
wrapper) runs in the forestrie profile.

## Phase 2 — forestrie-agents (org PRs)

1. **PR 1 — marketplace skeleton** (additive, nothing moves yet):
   `.claude-plugin/marketplace.json`, `plugins/forestrie-core/` with
   `plugin.json` and `hooks/` (`require-worktree.sh` moves in),
   `plugins/forestrie-linear/`. Skills are **copied** in this PR so existing
   paths keep working for anyone on the old layout.
2. **PR 2 — content moves**: `workflow/commands/*` → `plugins/forestrie-core/skills/<name>/SKILL.md`
   (each gets `description` / `argument-hint`); `arc-context/*.md` →
   `skills/arc-<name>/SKILL.md` with the old "task touches" text as
   `description` and `user-invocable: false`; `workflow/skills/*` → skills;
   `workflow/rules/*` → `rules/{common,lang}/` with `paths:` added to the
   language ones; `rules-of-the-road/*` → `rules/rules-of-the-road/`;
   `vendored/skills/` deleted (duplicate); `vendored/matt-skills` becomes
   either an `engineering` marketplace entry pinned by `sha` (Q4) or
   `plugins/engineering/` with `VENDOR.md`.
3. **PR 3 — sync manifests + workspace file**: `sync/<repo>.manifest` for
   each org repo; `workspace/AGENTS.md` generated from
   `forestrie-agent-context.md`; `AGENTS.md` rewritten as org map + contributor
   guide (no routing prose); `harness/` cut to two pages.
4. **Pilot in canopy**: `agentfiles sync ~/Dev/personal/forestrie/canopy --manifest canopy`;
   commit `AGENTS.md` (trimmed to repo facts), `.claude/settings.json`,
   `.claude/rules/`, `.agents/skills/`, `.claude/skills/` symlinks. Verify
   terminal `/context`, then `claude --cloud "run /context and list skills"`.
5. **Roll out** to arbor, univocity, univocity-tools, mandate, forest-1,
   arbor-flux, devdocs with the same PR shape. Add a CI job
   (`agentfiles doctor --repo --ci`) that fails on drift from the pinned
   source SHA.
6. Install `workspace/AGENTS.md` at `~/Dev/personal/forestrie/AGENTS.md`
   (bootstrap does this when the forestrie profile is present); delete
   `forestrie-agent-context.md`.

Done when: README verification items 3 and 4 pass in canopy and arbor;
`claude plugin validate` passes on forestrie-agents.

## Phase 3 — home

1. Create private `robinbryce/agentfiles-home` with the layout in
   [01-target-layout.md](./01-target-layout.md#agentfiles-home-private).
   First skills: `uk-self-assessment` (references: deadlines, allowances,
   evidence checklist; script: statement normaliser), `household-records`,
   `statement-reconcile`. Write the `privacy.md` rule first.
2. `agentfiles bootstrap home`; `~/Home/.envrc` exports the profile.
3. Upload the non-sensitive admin skills to the claude.ai account (Q5) so
   chat, Cowork and cloud sessions see them as `/anthropic-skills:<name>`.
4. Try one real task under `claude-local` to confirm the statement normaliser
   runs fully offline.

Done when: `claude-home` lists `admin@agentfiles-home`; a claude.ai chat can
invoke the uploaded skill; `claude-forestrie` shows none of it.

## Phase 4 — other harnesses and local models

1. **pi**: bootstrap creates `~/.pi-<profile>/AGENTS.md` → `profiles/<p>/AGENTS.md`
   (profile `CLAUDE.md` content + always-on rules appended) and links each
   enabled plugin's `skills/*` into `~/.pi-<profile>/skills/`. `PI_CODING_AGENT_DIR`
   is set by the same `.envrc` lines. Re-link the cmux extension per profile
   as today.
2. **cursor-agent**: nothing beyond the committed layer; `agentfiles link`
   for repos outside a workspace. Delete `harness/cursor.md`'s `.mdc`
   generation section.
3. **Local models**: `harness/local-models.md` with the `claude-local`
   wrapper, `OLLAMA_CONTEXT_LENGTH=32768` (or higher), model choices that
   support tool calling (`qwen3-coder`, `gpt-oss:20b`), and a pi `models.json`
   provider block (`openai-completions`, `baseUrl` `http://localhost:11434/v1`).
   Note that account sync is off in this mode and that Claude Code still
   makes a few non-inference calls to Anthropic.

Done when: README verification items 5 and 6 pass.

## Phase 5 — retire

- agentfiles: `scopes/`, `workflow/`, `USER-*.md`, `harness/hooks/`,
  old `harness/*.md` sections, `bin/agentfiles-sync` (folded into `bin/agentfiles`).
- forestrie-agents: `workflow/`, `arc-context/`, `rules-of-the-road/` (moved),
  `vendored/skills/`, `harness/hooks/`, `forestrie-agent-context.md` in the
  workspace.
- Machine: `~/.claude/settings.json` hook and permissions; `~/.claude/CLAUDE.md`
  symlink; `agentfiles-link` in dotfiles replaced by `agentfiles link`.
- Update this plan's `status:` to `complete` and add a `decisions.md` with
  the Q1–Q5 answers.

---

## File mapping

### agentfiles (from `main` + July branch)

| Today | Target |
|-------|--------|
| `AGENTS.md` (router) | `AGENTS.md` (contributor guide for this repo only) |
| `USER-CLAUDE.md`, `USER-PI.md` | `profiles/<p>/CLAUDE.md`, `profiles/<p>/AGENTS.md` |
| `scopes/<s>/AGENTS.md` | planning params → `profiles/<s>/CLAUDE.md`; rest deleted |
| `scopes/forestrie/skills.sources` | `profiles/forestrie/settings.json` `enabledPlugins` |
| `scopes/forestrie/incubator/*` | `incubator/forestrie/*` |
| `scopes/justgames/workflow/rules/linear-auth` | `profiles/justgames/rules/linear-auth.md` |
| `workflow/skills/{plan-new,save-status}` | `plugins/core/skills/…` |
| `workflow/rules/{planning,pr-descriptions,multi-repo-fanout,linear-direct-api}` | `plugins/core/skills/…` (skill form, `user-invocable: false`) |
| `workflow/rules/{clickable-references,herdr-session-handoff}` | `rules/*.md` (always-on; the second with `paths:`) |
| `workflow/rules/templates/*` | `plugins/core/skills/plan-new/templates/` |
| `harness/hooks/{hooks.json,validate-plan.sh}` | `plugins/core/hooks/` |
| `.claude-plugin/{marketplace,plugin}.json` | rewritten: `pluginRoot ./plugins`; per-plugin manifests |
| `bin/agentfiles-sync` | `bin/agentfiles sync` (+ `bootstrap`, `doctor`, `link`) |
| `harness/{claude-code,cursor,pi,generic}.md` | shortened; + `harness/local-models.md` |
| `vendored/`, `incubator/README.md` | `vendored/` deleted; incubator kept |

### forestrie-agents

| Today | Target |
|-------|--------|
| `AGENTS.md` (router) | `AGENTS.md` (org map + contributing) |
| `arc-context/<x>.md` | `plugins/forestrie-core/skills/arc-<x>/SKILL.md` |
| `rules-of-the-road/*.md` | `rules/rules-of-the-road/*.md` (synced into repos' `.claude/rules/`) |
| `workflow/commands/*.md` | `plugins/forestrie-core/skills/<name>/SKILL.md` |
| `workflow/skills/{persist-plan,rules-of-the-road-review}.md` | `plugins/forestrie-core/skills/<name>/SKILL.md` |
| `workflow/rules/linear-mcp-forestrie.md` | `plugins/forestrie-linear/skills/linear-forestrie/SKILL.md` |
| `workflow/rules/{go,typescript,solidity}-comments.md` etc. | `rules/lang/*.md` with `paths:` |
| `workflow/rules/{commit-conventions,branch-naming,breaking-changes,adr-format,plan-docs}.md` | `rules/common/*.md` |
| `vendored/matt-skills/`, `vendored/skills/` | `engineering` marketplace entry (sha-pinned) **or** `plugins/engineering/` + `VENDOR.md`; the duplicate goes |
| `harness/hooks/require-worktree.sh` | `plugins/forestrie-core/hooks/` |
| `harness/{claude-code,cursor,generic}.md` | two short pages |
| `incubator/robin/*` | unchanged |
| `~/Dev/personal/forestrie/forestrie-agent-context.md` | `workspace/AGENTS.md`, installed by bootstrap |
| per-repo `forest/agents/` | repo `AGENTS.md` + `.claude/` + `.agents/skills/` (synced) |

### Machine

| Today | Target |
|-------|--------|
| `~/.claude/CLAUDE.md` → `USER-CLAUDE.md` | two-line stub |
| `~/.claude/settings.json` hook + Linear allow | profile templates; hook via `core` plugin |
| `~/.claude-personal`, `~/.claude-justgames` | kept; rendered by bootstrap |
| — | `~/.claude-forestrie`, `~/.claude-home`, `~/.pi-forestrie`, `~/.pi-home` |
| `claude()` on `DOTFILES_ROLE` | direnv `CLAUDE_CONFIG_DIR` first, role second |
| `agentfiles-link` (dotfiles) | `agentfiles link` |
