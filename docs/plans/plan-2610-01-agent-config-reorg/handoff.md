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

**Next slice:** after #8 merges and `~/Dev/personal/forestrie/forestrie-agents` is on main, rerun `~/agentfiles/bin/agentfiles bootstrap forestrie`. Then PR 2 (arc-context as skills, rules-of-the-road sources, sync manifests) and PR 3 (workspace AGENTS.md); pilot `agentfiles sync` in canopy. Q1 still open, see decisions.md.

**Resume prompt:**

> Continue plan 2610-01 in `~/agentfiles` (branch `robin/agent-config-reorg`).
> Read `docs/plans/plan-2610-01-agent-config-reorg/README.md`, `decisions.md`
> and `03-migration.md`. If Q1 in `decisions.md` is still pending, fetch
> `probe/result` from robinbryce/draft-bryce-cose-receipts-mmr-profile and
> record it. Then execute Phase 1 of `03-migration.md`.