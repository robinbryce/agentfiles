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
scheme from [workflow/rules/planning](../workflow/rules/planning/SKILL.md). On any
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

## Skills (this is where slash commands come from)

Claude Code has merged custom commands into skills: a directory
`<skills-dir>/<name>/SKILL.md` becomes the slash command `/<name>`, and Claude
may also apply it automatically when its `description` matches the task.

Discovery locations, in Claude Code's own precedence order:

| Level | Path | Applies to |
|-------|------|-----------|
| Personal | `~/.claude/skills/<name>/SKILL.md` | every project |
| Project | `<repo>/.claude/skills/<name>/SKILL.md` | that repo (walks up to the repo root) |

Entries may be **symlinks** to directories elsewhere on disk — Claude Code
follows them and reads `SKILL.md` from the target. That is exactly how this
repo installs: one canonical skill directory, symlinked into each harness.

### Install

```bash
~/agentfiles/bin/agentfiles-sync <scope>       # run in the repo you're working in
```

That links the cross-scope [workflow/skills/](../workflow/skills/) and
[workflow/rules/](../workflow/rules/), plus their `scopes/<scope>/` overlays
(and anything listed in the scope's `skills.sources`), into the repo's `.claude/skills/`, `.cursor/skills/`,
`.agents/skills/`, and `.cursor/commands/`, then adds those paths to
`.git/info/exclude` so they never get committed into a repo that doesn't own
them.

### Why per-repo, not machine-wide

**Personal skills override project skills.** A machine-wide `/save-status`
would shadow the Forestrie-specific one that
[forestrie-agents](https://github.com/forestrie/forestrie-agents) ships. Since
scope isolation is the whole point of this repo, install per-repo and let the
scope decide which `/save-status` you get.

`agentfiles-sync --global` exists for genuinely universal skills. Use it
sparingly, and never for a name a scope also defines.

### Optional: install as a plugin instead

[.claude-plugin/marketplace.json](../.claude-plugin/marketplace.json) exposes
each scope as a Claude Code plugin, if you would rather manage this through
`/plugin` than through symlinks:

```bash
claude plugin marketplace add ~/agentfiles
claude plugin install agentfiles-forestrie@agentfiles     # per-project scope
```

Plugin skills are namespaced (`/agentfiles-forestrie:save-status`), so they
cannot collide with personal or project skills — which also means they do not
participate in the shadowing described above. This path is Claude Code only;
`agentfiles-sync` is what serves Cursor and pi as well.

### Rules are skills with a narrower trigger

[workflow/rules/](../workflow/rules/) uses the same `<name>/SKILL.md` form,
annotated `user-invocable: false` (hidden from the `/` menu) and, where the
rule is file-type scoped, `paths:` — so `typescript-comments` costs no context
until the session touches a `.ts` file, then loads by itself. That replaces
Cursor's always-inject-or-forget `alwaysApply` model.

Only ever load skills from **one** scope plus the cross-scope `workflow/` and
`vendored/` — never mix two scopes' skills into the same session.

## Forestrie note

For Forestrie project repos, the canonical skills/commands source is still
[forestrie-agents](https://github.com/forestrie/forestrie-agents). This
repo's `scopes/forestrie/` only supplies Robin's personal additions on top.
