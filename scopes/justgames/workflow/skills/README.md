# justgames/workflow/skills

Scope-specific skills — each is a `<name>/SKILL.md` directory, invocable as
`/<name>` once installed by [`bin/agentfiles-sync`](../../../../bin/agentfiles-sync).

A skill here **shadows** a cross-scope skill of the same name from
[workflow/skills/](../../../../workflow/skills/), because scope sources are
applied after common ones.

| Skill | Purpose |
|-------|---------|
| [/review-pr-justgames](./review-pr-justgames/SKILL.md) | Any PR review / re-review in a justgames repo. |
