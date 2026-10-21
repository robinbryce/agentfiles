# pi (pi.dev)

`bin/agentfiles bootstrap <profile>` mirrors each Claude profile to
`~/.pi-<profile>`:

- `AGENTS.md`: generated from `profiles/<profile>/CLAUDE.md` plus the
  always-on rules (pi has no rules concept; path-scoped rules are omitted).
  Regenerate with bootstrap; do not edit in place.
- `skills/<name>` → the skill directories of every plugin the profile enables
  (pi loads `<agent-dir>/skills/`). Project skills in `.agents/skills/` and
  `.pi/skills/` are read natively.

`PI_CODING_AGENT_DIR` is exported by the same `.envrc` lines as
`CLAUDE_CONFIG_DIR`; the `pi` wrapper honours it first. pi walks parent
directories for `AGENTS.md`, so the forestrie workspace file and each repo's
`AGENTS.md` load as in Claude Code.

Alternative for the skills: `npx skills add robinbryce/agentfiles -a pi -g`
(skills CLI ≥ 1.7 has a `pi` target).

Local models: a provider block in `~/.pi-<profile>/models.json`, see
[local-models.md](./local-models.md). cmux integration is unchanged:
`cmux hooks pi install`, then link the extension into each profile dir.
