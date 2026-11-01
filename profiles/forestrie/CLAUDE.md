# Profile: forestrie

This session runs in Robin's **forestrie** profile (`~/.claude-forestrie`).
Team conventions arrive as the `forestrie-core` and `mattpocock-skills`
plugin skills and as each repo's committed `AGENTS.md` and
`.claude/rules/`. Personal conventions arrive as `core` plugin skills and the
rules in this profile. Nothing from the personal, home or justgames profiles is
installed here; do not go looking for it.

The workspace map at `~/Dev/personal/forestrie/AGENTS.md` loads automatically
when you start beneath it: repo roles, primary clones, where devdocs lives.

## Planning params (override `core:planning` defaults)

| Param | Value |
|-------|-------|
| `plans_root` | `forestrie/work` `plans/`, in a worktree of `~/Dev/personal/forestrie/work` (the task container's `work/` if present) |
| `status_root` | `forestrie/work` `status/`, same worktree |
| `decisions_home` | repo `docs/adr/`, `docs/arc/`; devdocs when cross-repo; protocol when implementation independent |
| `id_scheme.plans` | date-cohort `plan-YYMM-NN-<slug>`, allocated against origin |
| `id_scheme.decisions` | absolute `adr-NNNN` / `arc-NNNN`, namespaced by home (`devdocs:ADR-0071`) |
| `issue_refs` | Linear `FOR-*`, in `issues:` |

Layout, frontmatter and status values: `forestrie-core:docs-layout`
(devdocs ADR-0071). No plans in code repos or devdocs. Forward-only does not
apply: each repo gets one normalisation change.

## Linear

Direct GraphQL keyed by `LINEAR_API_KEY` from `~/Dev/personal/forestrie/.envrc`
(`core:linear-direct-api` has the mechanism; `forestrie-core:linear-mcp-forestrie`
the MCP identity pre-flight for the fallback case). Never MCP or interactive login by default.
