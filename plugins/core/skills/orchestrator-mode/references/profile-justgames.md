# Overlay — justgames profile

- **Status skill**: the just-agents `/save-status` when the checkout exposes
  it (team convention), else `/core:save-status` with the root below.
- **Status root**: `$JUST_CODE/agent-archive/status/`, the shared flat
  status root of the `agent-archive` clone (a sibling of the working repos).
  A repo's own `status_root` param overrides it.
- **Plans root**: the repo's `docs/plans/` (`core:planning` defaults).
- **Upstream**: this skill was copied from just-agents
  `skills/orchestrator-mode`; if that version is also loaded here, prefer
  this one (`/core:orchestrator-mode`) and do not apply both.
