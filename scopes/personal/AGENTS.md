# scopes/personal — router

**For agents:** load selectively. Do not bulk-read this scope.

1. **This file** — routing only
2. **One** [arc-context](./arc-context/) file — only if a project needs its own glossary
3. **Repo overlay** — the working project's own `AGENTS.md`, if any
4. **Workflow** — only the invoked [command](./workflow/commands/) or [skill](./workflow/skills/)

## arc-context index

| File | Bounded context |
|------|-----------------|
| (none yet) | Add a glossary file here per personal project as needed (e.g. eightwords, zola-journal) |

## Workflow index

- [Commands](./workflow/commands/README.md)
- [Rules](./workflow/rules/README.md)
- [Skills](./workflow/skills/README.md)

## Notes

Do not reference Forestrie or JustGames details here — see the isolation
rule in [scopes/README.md](../README.md).
