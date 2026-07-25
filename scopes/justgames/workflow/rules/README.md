# justgames/workflow/rules

Scope-specific rules — each a `<name>/SKILL.md` directory, annotated with
`user-invocable: false` and, where the rule is file-type scoped, `paths:`.
See [workflow/rules/README.md](../../../../workflow/rules/README.md) for the
conventions.

A rule here **shadows** a cross-scope rule of the same name.

| Rule | Applies when |
|------|--------------|
| [linear-auth](./linear-auth/SKILL.md) | Any direct Linear API call in JustGames work — key resolution and the no-cross-scope-fallback guardrail |
