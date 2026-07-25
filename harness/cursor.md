# Cursor harness

Canonical agent files live in this repo as plain markdown. Cursor-specific
`.cursor/` paths in a project repo are **adapters**, not sources of truth.

## Skills — the shared format

Cursor loads skills from all of these, and treats `SKILL.md` directories the
same way Claude Code does:

| Path | Notes |
|------|-------|
| `.cursor/skills/<name>/` | project |
| `~/.cursor/skills/<name>/` | global |
| `.agents/skills/<name>/` | project, [Agent Skills](https://agentskills.io) standard |
| `~/.agents/skills/<name>/` | global, same standard |
| `.claude/skills/`, `~/.claude/skills/` | compatibility paths — Cursor reads these too |

The last row is the important one: **a single `.claude/skills/` directory
serves Claude Code and Cursor at once.** [`bin/agentfiles-sync`](../bin/agentfiles-sync)
writes all of them anyway, since the symlinks are free and it removes any
dependence on which compatibility path a given Cursor build honours.

### Install

```bash
~/agentfiles/bin/agentfiles-sync <scope>       # run in the repo you're working in
```

Per repo, that produces:

```text
.claude/skills/<name>      -> ~/agentfiles/workflow/skills/<name>   # Claude Code + Cursor
.cursor/skills/<name>      -> same target                           # Cursor, native path
.agents/skills/<name>      -> same target                           # Cursor + pi, open standard
.cursor/commands/<name>.md -> that skill's SKILL.md                 # Cursor's older command menu
```

all excluded via `.git/info/exclude`, so they never show up in `git status` or
get committed into a repo that doesn't own them.

The `.cursor/commands/` links are belt-and-braces for Cursor builds that
predate skills support. They point at the same `SKILL.md`, so there is nothing
to keep in sync.

## Rules and scope routing

`cursor-agent` (the CLI) reads `AGENTS.md` / `CLAUDE.md` / `.cursor/rules` at
the project root. Unlike Claude Code it has no `@import`, so scope routing is
set per repo:

```bash
agentfiles-link <scope>   # AGENTS.md -> scopes/<scope>/AGENTS.md; CLAUDE.md -> AGENTS.md
```

**Unverified caveat:** it isn't confirmed whether `cursor-agent` walks up to
the git root for `AGENTS.md`/`CLAUDE.md`, or only checks the literal cwd (the
`--workspace <path>` flag defaults to cwd, which hints it might not walk up).
If scope routing doesn't seem to be picked up from a nested subdirectory,
launch from the repo root or pass
`--workspace $(git rev-parse --show-toplevel)` explicitly.

### Rules

Rules are skills too — `workflow/rules/<name>/SKILL.md`, annotated with
`user-invocable: false` and, where file-type scoped, `paths:`. They install
with everything else, and Cursor reads them from `.claude/skills/` /
`.cursor/skills/` like any other skill.

For Cursor's **native** glob scoping, generate `.mdc` shims:

```bash
~/agentfiles/bin/agentfiles-sync <scope> --cursor-rules
```

`paths:` maps onto Cursor's `globs:`, `cursor-always-apply: true` onto
`alwaysApply: true`, and the shim body is a one-line pointer at the same
`SKILL.md` — nothing is duplicated, so nothing can drift. The generator never
overwrites a `.mdc` it did not write, and excludes the ones it does write
individually, so a repo tracking `.cursor/rules/` stays clean.

## Recommended layout (per project repo)

```text
AGENTS.md             # symlink to the scope's AGENTS.md  (agentfiles-link)
CLAUDE.md             # symlink to ./AGENTS.md            (agentfiles-link)
.claude/skills/       # symlinks to canonical skills      (agentfiles-sync)
.cursor/
  skills/             # symlinks to canonical skills      (agentfiles-sync)
  commands/           # symlinks to each SKILL.md         (agentfiles-sync)
  rules/              # generated .mdc shims (opt-in) + repo-specific overlays
.agents/skills/       # symlinks to canonical skills      (agentfiles-sync)
```

Two commands wire a repo completely:

```bash
agentfiles-link <scope>    # routing  (dotfiles/bin)
agentfiles-sync <scope>    # skills   (agentfiles/bin)
```

## Known drift

canopy, univocity, mandate, and curator each track hand-written
`.cursor/rules/*.mdc` duplicating
[forestrie-agents/workflow/rules/](https://github.com/forestrie/forestrie-agents/tree/main/workflow/rules).
`--cursor-rules` skips those files rather than clobbering them, so it is safe
to adopt before they are retired. Retiring one is then a delete plus a re-run.

Never symlink more than one scope's rules or skills into the same project.

## Bootstrap

Point always-applied workspace rules at:

1. Repo `AGENTS.md` (symlink to the scope, per above)
2. Repo-specific overlay rules only — prefer requestable rules for common content
