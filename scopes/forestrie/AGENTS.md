# scopes/forestrie — router

**Canonical team guidance lives in
[forestrie-agents](https://github.com/forestrie/forestrie-agents) — read
that repo's own `AGENTS.md` first.** Typical local path:
`~/Dev/personal/forestrie/forestrie-agents/AGENTS.md`.

This file only covers what's specific to *this* repo's forestrie scope:

1. Nothing here overrides forestrie-agents — it's additive only
2. [incubator/](./incubator/) holds pre-PR drafts; not loaded by default
3. If a task is purely Forestrie work with no personal-preference angle,
   you likely don't need anything from this scope folder at all — go
   straight to forestrie-agents

## Linear

Any Linear work (create/query issues, projects, initiatives, documents) →
follow [workflow/rules/linear-direct-api.md](../../workflow/rules/linear-direct-api.md):
direct GraphQL keyed by `LINEAR_API_KEY` from `~/Dev/personal/forestrie/.envrc`,
not MCP / interactive login. Takes precedence over forestrie-agents'
`linear-mcp-forestrie.md`.

## Planning params (overrides [workflow/rules/planning.md](../../workflow/rules/planning.md))

| Param | Value |
|-------|-------|
| `plans_root` | repo `docs/plans/` for repo-local work; `devdocs/plans/` for cross-repo platform plans |
| `decisions_home` | central: `devdocs/adr/`, `devdocs/arc/` (repos keep stub redirects only) |
| `id_scheme.plans` | date-cohort `plan-YYMM-NN-<slug>` (default) |
| `id_scheme.decisions` | absolute `adr-NNNN` / `arc-NNNN` |
| `issue_refs` | Linear `FOR-*` |

Cross-repo vs repo-local split follows `devdocs/AGENTS.md` "Documentation
ownership". Legacy `plan-NNNN` ids are frozen — forward-only (see the rule).
This mirrors what belongs in the shared
[forestrie-agents](https://github.com/forestrie/forestrie-agents) repo; keep
personal-only tweaks here.

See [../README.md](../README.md) for why this split exists.
