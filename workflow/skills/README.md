# workflow/skills

Cross-scope skill overlays — extensions on [vendored/](../../vendored/)
skills, or original skills that apply regardless of scope. Do not edit
vendored files in place.

| Overlay | Purpose |
|---------|---------|
| [worktrees-closeout](./worktrees-closeout/SKILL.md) | `/worktrees-closeout [<container-path>\|<task>]` — confirm what merged, assess residual local changes, remove every provably-safe worktree/branch across a task's sibling repos (herdr `.worktrees-herdr/<task>` or any plain container). Activated via `~/.claude/skills/worktrees-closeout` symlink. |

Scope-specific skills live in `scopes/<scope>/workflow/skills/` instead.
