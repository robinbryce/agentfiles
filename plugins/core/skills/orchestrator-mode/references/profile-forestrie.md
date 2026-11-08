# Overlay — forestrie profile

- **Status skill**: `/forestrie-core:save-status` (it adds FOR issues,
  worktrees and plan refs on top of `core:save-status`).
- **Status root**: `forestrie/work` `status/`, in a worktree of
  `~/Dev/personal/forestrie/work` (the task container's `work/` if present),
  on a branch. Never in a code repo or devdocs.
- **Plans root**: `forestrie/work` `plans/`, same worktree; always pass
  `--root` to `/core:plan-new`. A plan directory's `handoff.md` lives there.
- **Doc rules**: `forestrie-core:docs-layout` for frontmatter and status
  values; lint with dox where the repo opts in (`forestrie-core:dox`).
- **Kick-off prompt extras**: the FOR issue id, and the wif stream name if
  the session is on one.
