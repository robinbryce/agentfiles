# Claude Code harness

## This repo's own root

`CLAUDE.md` at the root of agentfiles is a one-line pointer to `AGENTS.md` —
read that first.

## Global hook (machine-wide, zero per-repo setup)

Claude Code loads `~/.claude/CLAUDE.md` in every session regardless of
working directory. [USER-CLAUDE.md](../USER-CLAUDE.md) is the maintained,
version-controlled source for that file — symlink it into place once per
machine:

```bash
ln -s ~/agentfiles/USER-CLAUDE.md ~/.claude/CLAUDE.md
```

This makes scope routing available in every Claude Code session, in every
project, regardless of nesting (tmux/nvim/cmux don't matter — it isn't
cwd-driven), with no changes to any downstream repo. The first time Claude
Code encounters the `@import` inside it, it shows a one-time approval
dialog — accept it.

## Per-repo scope lock (optional, explicit)

The global hook makes Claude infer scope from cwd against the table in
[AGENTS.md](../AGENTS.md). To skip that inference entirely for a specific
project repo — or to give `cursor-agent` the same content, since it has no
global hook — symlink the repo root to the scope directly:

```bash
ln -s ~/agentfiles/scopes/<scope>/AGENTS.md AGENTS.md
ln -s AGENTS.md CLAUDE.md
```

Both tools then read the correct scope unambiguously, without depending on
path-matching heuristics.

## Hooks

### Plan-doc guardrail (`PreToolUse`)

[hooks/validate-plan.sh](./hooks/validate-plan.sh) enforces the plan naming
scheme from [workflow/rules/planning.md](../workflow/rules/planning.md). On any
`Write`/`Edit` whose path is inside a `plans/` directory, it blocks (exit 2) a
filename that matches neither the date-cohort scheme (`plan-YYYY-NN-<slug>.md`),
the frozen legacy scheme (`plan-NNNN-<slug>.md`), a directory sub-doc
(`NN-<slug>.md`), nor `README.md`/`handoff.md`/`decisions.md`. Missing
frontmatter on a new-scheme file is a soft, non-blocking nudge. Non-plan paths
pass straight through.

Wire it once in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [ { "type": "command",
                     "command": "bash ~/agentfiles/harness/hooks/validate-plan.sh" } ] }
    ]
  }
}
```

The primary path is still `/plan-new` (allocates the id + scaffolds
frontmatter); the hook is the backstop for direct writes that skip it.

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
