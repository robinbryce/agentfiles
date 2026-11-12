# Overlay — no profile, or an unknown one

- **Default `mode`**: `report`. Ask Robin before running `fix` or `publish`.
- **`rules`**, **`commitRules`**, **`gates`**: leave them unset; the workflow falls back to the repo's
  `AGENTS.md`, its ADRs, its git log and its documented test commands.
- **`postComment`**: `false`; return the comment text instead of posting it.
- **Tracker**: none. List deferred findings in the reply.
