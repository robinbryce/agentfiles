# Overlay — justgames profile

- **Log home**: the plan directory in the repo that owns the plan, `docs/plans/<plan-id>/decisions.md`
  (`core:planning` defaults), in the task container's worktree under `~/Dev/justgames/code`. It is a
  plan part, so it has no frontmatter.
- **No plan directory yet**: keep the log beside the canvas in the scratchpad and offer
  `/core:plan-new --dir`.
- **Ids**: the session's own ids, plus Linear `ENG-NNNN` issues where they exist.
- **Link**: from the plan README.
- **Commit**: the repo's conventional-commit title as its log shows (`type(scope): summary (ENG-NNNN)`),
  a body that says why, and the session's `Co-Authored-By` line. On a branch in a worktree; never push
  without asking.
- **Canvas**: a private Artifact. It holds JustGames design detail, so do not share or embed the link
  anywhere unless Robin asks.
