# Overlay — no profile, or an unknown one

- **Status skill**: `/core:save-status` if installed, else write the status
  doc by hand following `core:planning` naming.
- **Status root**: the active `CLAUDE.md`'s `status_root`, else the repo's
  `docs/status/`.
- **Plans root**: the active `CLAUDE.md`'s `plans_root`, else the repo's
  `docs/plans/`.
- If none of this resolves, ask the user where the handoff should go rather
  than inventing a location.
