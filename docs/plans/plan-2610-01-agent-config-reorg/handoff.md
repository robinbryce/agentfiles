# Handoff — plan 2610-01

**Bootstrap order:**

1. [README.md](./README.md) — context, goal, decisions D1–D8, open questions Q1–Q5
2. [01-target-layout.md](./01-target-layout.md) — trees and manifests
3. [02-loading-model.md](./02-loading-model.md) — delivery matrix per surface
4. [03-migration.md](./03-migration.md) — phases and file mapping

**Locked decisions:**

- Scope = Claude profile (`CLAUDE_CONFIG_DIR`), selected by direnv / wrapper, never inferred by the model (D1).
- Skill = unit of content, AGENTS.md = unit of routing, rules = always-on or `paths:`-scoped (D2).
- Plugin = unit of distribution, one marketplace per trust boundary: `agentfiles`, `forestrie-agents`, private `agentfiles-home` (D3).
- Cloud parity via a synced, committed repo layer (`AGENTS.md`, `.claude/rules/`, `.agents/skills/` + `.claude/skills/` symlinks) (D4).
- Cross-tool by SKILL.md + AGENTS.md only; no per-harness adapters (D5).
- The July branch `robin/skills-as-slash-commands` is kept and merged first (Phase 0). **Done** (merge commit on this branch).
- Robin's 2026-10-11 choices and Q2–Q5 answers: see [decisions.md](./decisions.md).

**Phase 1 status (2026-10-11):** repo restructured (commit e56ee15); `~/agentfiles` switched to this branch; `bin/agentfiles bootstrap personal forestrie --envrc` run on Robin's machine (core + research installed in both profiles; forestrie-agents skipped until it is a marketplace); `~/.claude/CLAUDE.md` stubbed and its dangling hook/permissions removed; dotfiles `profiles/common/agents.sh` sources the generated wrappers; `.envrc` exports appended at `~/Dev/personal` and `~/Dev/personal/forestrie` (need `direnv allow`).

**Phase 2 status (2026-10-11):** PR 1 open as draft, [forestrie/forestrie-agents#8](https://github.com/forestrie/forestrie-agents/pull/8). Sandboxed bootstrap against it installs forestrie-core (21 skills, 1 hook) and mattpocock-skills (3 skills).

**Phase 2 PRs 2–3 and pilot (2026-10-11): merged.**

- [forestrie/forestrie-agents#9](https://github.com/forestrie/forestrie-agents/pull/9) (squash 0e414ec): `arc-*` glossary skills, copy-safe rules-of-the-road, `sync/<repo>.manifest` ×8, YAML frontmatter fix. Review added: Go library links repointed from arbor's gitignored `services/_deps` to `forestrie/go-*`; agentfiles links pinned to a SHA.
- [forestrie/forestrie-agents#10](https://github.com/forestrie/forestrie-agents/pull/10) (squash 797688a): `workspace/AGENTS.md`, AGENTS.md as org map + contributor guide, `harness/` cut to `claude-code.md` + `other-tools.md`. Review added: the three unmapped workspace directories.
- [forestrie/canopy#268](https://github.com/forestrie/canopy/pull/268) (merge f61729a): the synced layer, re-synced from forestrie-agents main 797688a before merge. `/context` and path-scoped rules verified; `doctor --repo --ci` clean without `--source`.
- `bin/agentfiles` sync/doctor fixes from the pilot: commit b20b48e. Details and deviations from 01-target-layout: [decisions.md](./decisions.md#phase-2-notes-prs-23-and-the-canopy-pilot-2026-10-11).

Worktrees removed.

**Phase 2 step 6 (2026-10-11): done.** `agentfiles bootstrap forestrie` rerun; `~/Dev/personal/forestrie/AGENTS.md` → `forestrie-agents/workspace/AGENTS.md`; `forestrie-agent-context.md` deleted. A headless session in canopy loads the profile CLAUDE.md, the workspace AGENTS.md, canopy's AGENTS.md and the always-on `.claude/rules/`, and lists all seven `forestrie-core:arc-*` skills (README verification item 3, canopy).

**Next slice:**

1. Robin runs the cloud check in canopy (README verification item 4) and reports back:
   `cd ~/Dev/personal/forestrie/canopy && claude --cloud "Check the committed agent layer. Change no files. (1) List every skill available to you and mark which come from this repo's .claude/skills/. (2) List the .claude/rules/ files loaded as instructions and say which are path-scoped. (3) Say whether any forestrie-core@forestrie-agents plugin skills or hooks are present. Reply in chat only; do not commit or push."`
   Expected: the six project skills (`arc-canopy`, `persist-plan`, `pre-commit-checks`, `review-changes`, `rules-of-the-road-review`, `save-status`); probably no forestrie-core (private marketplace).
2. Phase 2 step 5: roll out to arbor, univocity, univocity-tools, mandate, forest-1, arbor-flux, devdocs (same PR shape; manifests exist), and add the `agentfiles doctor --repo --ci` job. Sync only from forestrie-agents **main**: the repo squash-merges, so a branch SHA in `.synced-from` would dangle.
3. Follow-ups found in review, not blocking: `workflow/skills/fork-mandate` still describes `system-testing/manifests/lane-b.jsonc`, which [forestrie/system-testing#90](https://github.com/forestrie/system-testing/pull/90) removed (lane B is now defined by promotion). The skill needs a rewrite, not a link swap. It is in no sync manifest.
4. Stale worktrees from PR 1 remain: `~/Dev/personal/forestrie/.worktrees/forestrie-agents-marketplace` (`robin/marketplace`) and `…/forestrie-agents-skills` (`robin/skills-as-slash-commands`). Both branches are merged; remove when convenient.

**Resume prompt:**

> Continue plan 2610-01 in `~/agentfiles` (branch `robin/agent-config-reorg`).
> Read `docs/plans/plan-2610-01-agent-config-reorg/handoff.md` and
> `decisions.md`, then pick up the next slice above.
