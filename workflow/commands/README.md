# workflow/commands

Cross-scope slash commands and prompt templates — things that make sense no
matter which scope you're in. Load only when invoked.

| Command | Purpose |
|---------|---------|
| [/plan-new](./plan-new.md) | Allocate the next date-cohort plan id and scaffold the doc (helper: [new-plan.sh](./new-plan.sh)). See [rules/planning.md](../rules/planning.md). |

Scope-specific commands live in `scopes/<scope>/workflow/commands/` instead.

Install in a project repo via [harness/cursor.md](../../harness/cursor.md) or
[harness/claude-code.md](../../harness/claude-code.md).
