# Claude Code harness

## This repo's own root

`CLAUDE.md` at the root of agentfiles is a one-line pointer to `AGENTS.md` —
read that first.

## Wiring a project repo to agentfiles

Add a thin pointer at the project repo's root `CLAUDE.md`:

```markdown
# Claude Code

Read [AGENTS.md](./AGENTS.md) before making changes.
Common process: [agentfiles](https://github.com/robinbryce/agentfiles),
scope: <forestrie|justgames|personal>.
```

## Skills

Install skills by copying or symlinking from:

- `scopes/<scope>/workflow/skills/` (scope-specific overlays)
- `workflow/skills/` (cross-scope overlays)
- `vendored/<source>/skills/` (pinned third-party)

Only ever load skills from **one** scope plus the cross-scope `workflow/` and
`vendored/` — never mix two scopes' skills into the same session.

## Forestrie note

For Forestrie project repos, the canonical skills/commands source is still
[forestrie-agents](https://github.com/forestrie/forestrie-agents). This
repo's `scopes/forestrie/` only supplies Robin's personal additions on top.
