# workflow/commands

Cross-scope slash commands and prompt templates — things that make sense no
matter which scope you're in. Load only when invoked.

| Command | Purpose |
|---------|---------|
| [/plan-new](./plan-new.md) | Allocate the next date-cohort plan id and scaffold the doc (helper: [new-plan.sh](./new-plan.sh)). See [rules/planning.md](../rules/planning.md). |
| [/worktrees-closeout](../skills/worktrees-closeout/SKILL.md) | Close out a workstream staged as sibling-repo worktrees under one container: confirm merges, assess residuals, clean up. Lives under skills (invoked as a slash command). |
| [/save-status](./save-status.md) | Condense the session into a `status-YYMM-NN-*` doc (updated in place per workstream) that a fresh agent can resume from. |

Scope-specific commands live in `scopes/<scope>/workflow/commands/` instead.

Install in a project repo via [harness/cursor.md](../../harness/cursor.md) or
[harness/claude-code.md](../../harness/claude-code.md).
