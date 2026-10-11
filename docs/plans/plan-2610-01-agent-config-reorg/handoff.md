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

**Phase 2 step 5 rollout (2026-10-11): seven draft PRs open**, branch `robin/agent-layer-sync` in each, synced from forestrie-agents main 797688a, `doctor --repo --ci` clean, headless session lists the project skills in every one:
[arbor#112](https://github.com/forestrie/arbor/pull/112),
[univocity#47](https://github.com/forestrie/univocity/pull/47),
[univocity-tools#32](https://github.com/forestrie/univocity-tools/pull/32),
[mandate#103](https://github.com/forestrie/mandate/pull/103),
[forest-1#42](https://github.com/forestrie/forest-1/pull/42),
[arbor-flux#62](https://github.com/forestrie/arbor-flux/pull/62),
[devdocs#219](https://github.com/forestrie/devdocs/pull/219).
Worktrees at `~/Dev/personal/forestrie/.worktrees/<repo>-agent-layer-sync`. Repo-specific fixes: devdocs `.gitignore` (ignored all of `.claude/`), mandate `.prettierignore` (`prettier --check .` failed on the copies). `bin/agentfiles` now flags a gitignored layer (commit 952cbef). See [decisions.md](./decisions.md#phase-2-step-5-rollout-2026-10-11).

**Direction change (2026-10-11): pointer, not copies.** Robin dropped the CI drift job and the per-repo copies for public repos: forestrie-agents goes public so a committed `.claude/settings.json` marketplace pointer works without auth. Private repos wait. Source split stays. See [decisions.md](./decisions.md#rethinking-d4-pointer-not-copies-2026-10-11). Sensitivity review done (nothing confidential); the one fix is [forestrie/forestrie-agents#11](https://github.com/forestrie/forestrie-agents/pull/11) (draft): MIT notice for the vendored mattpocock/skills. Robin chose no license for forestrie-agents itself.

**Next slice:**

1. Merge forestrie-agents#11, then switch forestrie-agents to public (confirm with Robin first; `gh repo edit forestrie/forestrie-agents --visibility public --accept-visibility-change-consequences`).
2. **Cloud check run 2026-10-11** (with forestrie-agents still private): synced skills and rules load; forestrie-core does not, the marketplace was never fetched. See [decisions.md](./decisions.md#cloud-check-in-canopy-2026-10-11-readme-verification-item-4). Next: Robin makes forestrie-agents public, then a canopy probe branch with a SessionStart hook that installs forestrie-core, two cloud sessions on it. Original command (part (3) was the gate): does a cloud session install `forestrie-core` from canopy's `.claude/settings.json` pointer?
   `cd ~/Dev/personal/forestrie/canopy && claude --cloud "Check the committed agent layer. Change no files. (1) List every skill available to you and mark which come from this repo's .claude/skills/. (2) List the .claude/rules/ files loaded as instructions and say which are path-scoped. (3) Say whether any forestrie-core@forestrie-agents plugin skills or hooks are present. Reply in chat only; do not commit or push."`
3. If yes: shrink the public-repo drafts ([arbor#112](https://github.com/forestrie/arbor/pull/112), [univocity#47](https://github.com/forestrie/univocity/pull/47), [univocity-tools#32](https://github.com/forestrie/univocity-tools/pull/32), [mandate#103](https://github.com/forestrie/mandate/pull/103)) to the pointer plus AGENTS.md edits, remove canopy's copies in a follow-up, and decide whether repo-specific rules of the road and `arc-<repo>` move into each repo as their own source. Hold or close the private-repo drafts ([forest-1#42](https://github.com/forestrie/forest-1/pull/42), [arbor-flux#62](https://github.com/forestrie/arbor-flux/pull/62), [devdocs#219](https://github.com/forestrie/devdocs/pull/219)); devdocs' `.gitignore` fix is worth keeping either way. If no: revisit (SessionStart-hook probe, or AGENTS.md links only).
4. Follow-ups, not blocking: `workflow/skills/fork-mandate` still describes `system-testing/manifests/lane-b.jsonc`, removed by [forestrie/system-testing#90](https://github.com/forestrie/system-testing/pull/90). canopy#268's commits carry `Co-Authored-By`, which the org `commit-conventions` rule forbids.
5. Stale worktrees: `~/Dev/personal/forestrie/.worktrees/forestrie-agents-marketplace`, `…/forestrie-agents-skills` (merged branches); `…/forestrie-agents-vendored-license` after #11 merges; the seven `<repo>-agent-layer-sync` worktrees once their PRs settle.

**Resume prompt:**

> Continue plan 2610-01 in `~/agentfiles` (branch `robin/agent-config-reorg`).
> Read `docs/plans/plan-2610-01-agent-config-reorg/handoff.md` and
> `decisions.md`, then pick up the next slice above.
