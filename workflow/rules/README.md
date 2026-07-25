# workflow/rules

Cross-scope rules. Each is a `<name>/SKILL.md` directory, exactly like a
[skill](../skills/) — because on every current harness a rule *is* a skill.
What distinguishes them is frontmatter, not location:

| Frontmatter | Effect |
|-------------|--------|
| `user-invocable: false` | Background knowledge; hidden from the `/` menu |
| `paths: [...]` | Loaded **only** when the session touches a matching file |
| `description` / `when_to_use` | How the agent decides to apply an unscoped rule |

| Rule | Applies when |
|------|--------------|
| [clickable-references](./clickable-references/SKILL.md) | Always — any output naming a file, line, PR, issue, commit, or symbol |
| [planning](./planning/SKILL.md) | Touching `plans/`, `adr/`, `arc/`. Owns [templates/](./planning/templates/) |
| [linear-direct-api](./linear-direct-api/SKILL.md) | Any Linear work — direct GraphQL keyed by the scope's `LINEAR_API_KEY`, not MCP |

Scope-specific rules live in `scopes/<scope>/workflow/rules/` and shadow a
cross-scope rule of the same name.

## Why `paths:` replaced `alwaysApply`

The old model was Cursor's: a rule was either always injected or requestable by
name. `paths:` is strictly better — a rule costs **zero context** until the
session touches a file it governs, then loads automatically without anyone
having to remember it. `typescript-comments` is absent in a Terraform repo and
present the moment you open a `.ts` file.

Only [clickable-references](./clickable-references/SKILL.md) is genuinely
always-on. It has no `paths`, so it loads on description alone.

**Honest limit:** Claude Code has no hard `alwaysApply` for skills. The
guarantee for always-on content is the pointer in
[AGENTS.md](../../AGENTS.md), which is loaded every session — the skill form is
what makes the body available without spending context on it up front.

## Cursor

`bin/agentfiles-sync --cursor-rules` generates `.cursor/rules/<name>.mdc`
shims: `paths:` becomes Cursor's native `globs:`, `cursor-always-apply: true`
becomes `alwaysApply: true`, and the body is a one-line pointer at the same
`SKILL.md` — so there is no duplicated content to drift.

It is opt-in and **never overwrites a `.mdc` it did not generate**: files
lacking its marker are skipped, and generated ones are excluded individually
via `.git/info/exclude` so a repo that tracks `.cursor/rules/` stays clean.
