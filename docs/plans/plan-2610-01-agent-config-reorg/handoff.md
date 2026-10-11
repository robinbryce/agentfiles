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

**Phase 2 PRs 2–3 and pilot (2026-10-11):** all open as drafts.

- [forestrie/forestrie-agents#9](https://github.com/forestrie/forestrie-agents/pull/9): `arc-*` glossary skills, copy-safe rules-of-the-road, `sync/<repo>.manifest` ×8, YAML frontmatter fix.
- [forestrie/forestrie-agents#10](https://github.com/forestrie/forestrie-agents/pull/10) (stacked on #9): `workspace/AGENTS.md`, AGENTS.md as org map + contributor guide, `harness/` cut to `claude-code.md` + `other-tools.md`.
- [forestrie/canopy#268](https://github.com/forestrie/canopy/pull/268): the synced layer, from #10's head. `/context` and path-scoped rules verified; `doctor --repo --ci` clean.
- `bin/agentfiles` sync/doctor fixes from the pilot: commit b20b48e. Details and deviations from 01-target-layout: [decisions.md](./decisions.md#phase-2-notes-prs-23-and-the-canopy-pilot-2026-10-11).

Worktrees: `~/Dev/personal/forestrie/.worktrees/{forestrie-agents-pr2,forestrie-agents-pr3,canopy-agent-layer}`.

**Next slice:**

1. Robin reviews and merges #9 → #10 → canopy#268 (re-sync canopy from forestrie-agents main first if #9/#10 changed). Then `/reload-plugins` or rebootstrap so the forestrie profile picks up the `arc-*` skills.
2. Verify a cloud session in canopy lists the six project skills (`claude --cloud "run /context and list skills"`); README verification items 3 and 4.
3. Phase 2 step 6: rerun `agentfiles bootstrap forestrie` so `~/Dev/personal/forestrie/AGENTS.md` links `workspace/AGENTS.md`, then delete `forestrie-agent-context.md`.
4. Phase 2 step 5: roll out to arbor, univocity, univocity-tools, mandate, forest-1, arbor-flux, devdocs (same PR shape; manifests already exist), and add the `agentfiles doctor --repo --ci` job.

**Resume prompt:**

> Continue plan 2610-01 in `~/agentfiles` (branch `robin/agent-config-reorg`).
> Read `docs/plans/plan-2610-01-agent-config-reorg/handoff.md` and
> `decisions.md`. Check whether forestrie-agents#9, #10 and canopy#268 have
> merged, then pick up the next slice above.
