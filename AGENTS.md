# agentfiles — agent bootstrap

**For agents:** determine scope first, then load **selectively**. Do not
bulk-read this repository, and never load more than one scope in a task
unless the user explicitly asks to cross-reference.

**For humans:** see [README.md](./README.md).

---

## Loading order

1. **This file** — routing only (~2 min read)
2. **Determine scope** — see table below; ask if ambiguous
3. **One** [scopes/\<scope\>/AGENTS.md](./scopes/) — never more than one
4. **Repo overlay** — the working project's own `AGENTS.md` / `forest/agents/AGENTS.md`
5. **Workflow** — only the invoked [command](./workflow/commands/) or [skill](./workflow/skills/)

**Precedence on conflict:** repo overlay → scope → common `workflow/` →
vendored → incubator (opt-in).

---

## Scope detection

| Working on... | Scope | Router |
|---|---|---|
| `~/Dev/personal/forestrie/**` (canopy, arbor, univocity, mandate, forest-1, devdocs, product, forestrie-agents) | forestrie | [scopes/forestrie/AGENTS.md](./scopes/forestrie/AGENTS.md) |
| `~/Dev/justgames/**` (Flip contracts, protocol deploy, JustGames/SentientDogs code) | justgames | [scopes/justgames/AGENTS.md](./scopes/justgames/AGENTS.md) |
| Anything else — other personal projects, dotfiles, home automation | personal | [scopes/personal/AGENTS.md](./scopes/personal/AGENTS.md) |

If the working directory doesn't clearly match a row above, ask which scope
applies rather than guessing. **Never** load a second scope's `arc-context/`
or `workflow/` in the same task without the user explicitly asking for it —
that's the entire reason scopes exist.

---

## Workflow index (cross-scope)

### Commands (explicit invocation)

See [workflow/commands/README.md](./workflow/commands/README.md).

### Skills (on demand — read SKILL.md only when task matches)

See [workflow/skills/README.md](./workflow/skills/README.md).

### Rules (requestable — not auto-loaded unless repo configures alwaysApply)

See [workflow/rules/README.md](./workflow/rules/README.md).

**Creating a plan / ADR / ARC?** Load
[workflow/rules/planning.md](./workflow/rules/planning.md) and use
[`/plan-new`](./workflow/commands/plan-new.md) — do not hand-number plan files.
Scopes override the `plans_root` / `decisions_home` params below.

---

## Context efficiency rules

1. **Scope first, always** — determine scope before reading anything scope-specific
2. **Link, don't restate** — point to authoritative docs; do not copy bodies into responses
3. **Skills on demand** — read a skill only when its description matches the task
4. **Commands on invoke** — user runs the command or pastes its content
5. **Incubator is opt-in** — never load `incubator/` (root or scoped) unless the user names a path

---

## Key external references

| Topic | Where |
|-------|-------|
| Shared Forestrie team agent guidance | [forestrie-agents](https://github.com/forestrie/forestrie-agents) |
