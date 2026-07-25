# scopes/justgames — router

**For agents:** load selectively. Do not bulk-read this scope.

1. **This file** — routing only
2. **One** [arc-context](./arc-context/) file — only if domain terms apply
3. **Repo overlay** — the working project's own `AGENTS.md`, if any
4. **Workflow** — only the invoked [skill](./workflow/skills/)

## arc-context index

| File | Bounded context |
|------|-----------------|
| (none yet) | Add a glossary file here once JustGames domain terms need one |

## Workflow index

- [Rules](./workflow/rules/README.md)
- [Skills](./workflow/skills/README.md)

## Linear

Any Linear work → follow
[workflow/rules/linear-direct-api](../../workflow/rules/linear-direct-api/SKILL.md)
for the mechanism (direct GraphQL, not MCP / interactive login), and
[workflow/rules/linear-auth](./workflow/rules/linear-auth/SKILL.md) for how the
key is resolved in this scope: via `direnv exec ~/Dev/justgames`, never a
hardcoded `.envrc` path. If this scope defines no `LINEAR_API_KEY` — it
currently does not — stop and say so; never reuse the forestrie key here.

## Planning params (overrides [workflow/rules/planning](../../workflow/rules/planning/SKILL.md))

Uses the defaults: `plans_root` = repo `docs/plans/`, `decisions_home` =
repo `docs/{adr,arc}/`, date-cohort plan ids, absolute ADR/ARC. Set
`issue_refs` here if/when JustGames adopts a tracker prefix.

## Notes

Do not reference Forestrie or personal-project details here — see the
isolation rule in [scopes/README.md](../README.md).
