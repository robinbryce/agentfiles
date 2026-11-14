# Overlay — forestrie profile

- **Log home**: the plan directory's `decisions.md` in a worktree of `~/Dev/personal/forestrie/work`
  (the task container's `work/` when present): `plans/<plan-id>/decisions.md`. It is a plan part, so
  it has no frontmatter (`forestrie-core:docs-layout`).
- **No plan directory yet**: keep the log beside the canvas in the scratchpad and offer to promote the
  work with `/core:plan-new --dir --root <work worktree>/plans`.
- **Never in canon**: not in devdocs, protocol or a code repo. Canon cites canon only, and the log
  cites FOR ids and plan slices.
- **Ids**: the grill's question ids (`Q1`…), Linear `FOR-*` issues. In `lands`, write `ARC §5.3`
  for the plan's own design doc and `devdocs:ADR-0076` across homes.
- **Link**: from the plan README's locked-decisions section.
- **Lint**: `dox lint` in the work worktree (`forestrie-core:dox`). Fix any finding for the plan; the
  baseline's older findings are not yours.
- **Commit**: `forestrie-core:commit-conventions`: title at most 79 characters, body lines at most 72,
  no `Co-Authored-By` trailer. Push only to a plan PR that is already open, and only when the session
  allows outward actions for that plan; otherwise offer.
- **Canvas**: a private Artifact.
