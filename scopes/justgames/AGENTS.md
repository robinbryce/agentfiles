# scopes/justgames — router

**For agents:** load selectively. Do not bulk-read this scope.

1. **This file** — routing only
2. **One** [arc-context](./arc-context/) file — only if domain terms apply
3. **Repo overlay** — the working project's own `AGENTS.md`, if any
4. **Workflow** — only the invoked [command](./workflow/commands/) or [skill](./workflow/skills/)

## arc-context index

| File | Bounded context |
|------|-----------------|
| (none yet) | Add a glossary file here once JustGames domain terms need one |

## Workflow index

- [Commands](./workflow/commands/README.md)
- [Rules](./workflow/rules/README.md)
- [Skills](./workflow/skills/README.md)

## Notes

Do not reference Forestrie or personal-project details here — see the
isolation rule in [scopes/README.md](../README.md).
