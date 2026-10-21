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
| `plans_root` | repo `docs/plans/` for repo-local work; `devdocs/plans/` for cross-repo platform plans |
| `decisions_home` | central: `devdocs/adr/`, `devdocs/arc/` (repos keep stub redirects only) |
| `id_scheme.plans` | date-cohort `plan-YYMM-NN-<slug>` |
| `id_scheme.decisions` | absolute `adr-NNNN` / `arc-NNNN` |
| `issue_refs` | Linear `FOR-*` |

Cross-repo vs repo-local split follows `devdocs/AGENTS.md` "Documentation
ownership". Legacy `plan-NNNN` ids are frozen, forward-only.

## Linear

Direct GraphQL keyed by `LINEAR_API_KEY` from `~/Dev/personal/forestrie/.envrc`
(`core:linear-direct-api` has the mechanism; `forestrie-core:linear-mcp-forestrie`
the MCP identity pre-flight for the fallback case). Never MCP or interactive login by default.
