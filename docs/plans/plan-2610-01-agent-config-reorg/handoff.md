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
- The July branch `robin/skills-as-slash-commands` is kept and merged first (Phase 0).

**Next slice:** Phase 0 — merge the July branch into `main`, then run Q1–Q5
and record the answers in `03-migration.md` (Q1 gates the shape of the
committed layer in Phase 2).

**Resume prompt:**

> Continue plan 2610-01 in `~/agentfiles` (branch `robin/agent-config-reorg`).
> Read `docs/plans/plan-2610-01-agent-config-reorg/README.md` and
> `03-migration.md`. Start Phase 0: merge `robin/skills-as-slash-commands`
> into this branch, then verify Q1–Q5 and record the answers. Do not start
> Phase 1 until Q1 and Q2 are answered.
