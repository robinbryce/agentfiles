# workflow/skills

Cross-scope skill overlays — extensions on [vendored/](../../vendored/)
skills, or original skills that apply regardless of scope. Do not edit
vendored files in place.

| Overlay | Purpose |
|---------|---------|
| [worktrees-closeout](./worktrees-closeout/SKILL.md) | `/worktrees-closeout [<container-path>\|<task>]` — confirm what merged, assess residual local changes, remove every provably-safe worktree/branch across a task's sibling repos (herdr `.worktrees-herdr/<task>` or any plain container). Activated via `~/.claude/skills/worktrees-closeout` symlink. |
| [wif](./wif/SKILL.md) | `/wif [status\|start\|mark\|note\|tangent\|remind\|scan\|tick\|handoff\|adopt\|where\|install]` — work-in-flight tracker: per-account, per-scope Ledger of streams (herdr containers), session goals and prompt intents inferred via hooks, terminal dashboard + statusline, `/loop`-able tick with context rotation. Activated via the `~/.claude/skills/wif` directory symlink (both config dirs share that tree); hooks/statusline via `wif install --apply`. |

Scope-specific skills live in `scopes/<scope>/workflow/skills/` instead.
