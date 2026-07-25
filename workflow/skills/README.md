# workflow/skills

Cross-scope **skills** — things that make sense no matter which scope you're
in. Each skill is a directory containing `SKILL.md`, following the
[Agent Skills](https://agentskills.io) open standard.

| Skill | Purpose |
|-------|---------|
| [/plan-new](./plan-new/SKILL.md) | Allocate the next date-cohort plan id and scaffold the doc (helper: [new-plan.sh](./plan-new/scripts/new-plan.sh)). See [rules/planning](../rules/planning/SKILL.md). |
| [/save-status](./save-status/SKILL.md) | Condense the session into a `status-YYMM-NN-*` doc (updated in place per workstream) that a fresh agent can resume from. |

Scope-specific skills live in `scopes/<scope>/workflow/skills/` instead, and
**shadow** a cross-scope skill of the same name.

## Commands are skills now

This directory replaces the former `workflow/commands/`. Claude Code has
merged custom commands into skills — `.claude/commands/deploy.md` and
`.claude/skills/deploy/SKILL.md` both produce `/deploy` — and Cursor reads the
same layout. The directory form is what every harness understands, and it lets
a skill carry its own scripts and reference files instead of pointing at paths
elsewhere in this repo.

## Anatomy

```text
workflow/skills/plan-new/
├── SKILL.md              # frontmatter + instructions; the whole contract
└── scripts/
    └── new-plan.sh       # reachable as ${CLAUDE_SKILL_DIR}/scripts/new-plan.sh
```

Frontmatter fields worth setting:

| Field | Why |
|-------|-----|
| `name` | Display label. The invocation name comes from the **directory**, so keep them equal. |
| `description` | How the agent decides to auto-apply the skill. Lead with the use case. |
| `when_to_use` | Trigger phrases — appended to `description` in the skill listing. |
| `argument-hint` | Autocomplete hint, e.g. `"<slug> [--dir]"`. |
| `disable-model-invocation` | `true` for workflows that should only ever run when the user types `/name`. |
| `allowed-tools` | Pre-approved tools for the invoking turn — cuts permission prompts. |

Reference arguments in the body with `$ARGUMENTS`, or `$0` / `$1` positionally.
Use `${CLAUDE_SKILL_DIR}` for bundled scripts so they resolve wherever the skill
is installed.

## Install

```bash
~/agentfiles/bin/agentfiles-sync <scope>       # in the repo you're working in
```

See [harness/claude-code.md](../../harness/claude-code.md),
[harness/cursor.md](../../harness/cursor.md), and
[harness/pi.md](../../harness/pi.md) for what that wires up and why per-repo is
the default.
