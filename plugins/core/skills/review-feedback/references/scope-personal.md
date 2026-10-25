# Overlay — personal (and home)

- **Scope root**: `~/Dev/personal` (home: `~/Dev/personal/home`); also the
  dotfiles and agentfiles checkouts (`robinbryce/*`).
- **Standards**: the repo's own `AGENTS.md` / `CLAUDE.md`, its docs/plans
  decision tables and DESIGN records (agentfiles skills keep theirs in the
  skill's `DESIGN.md`). No rules-of-the-road corpus.
- **Bots to expect**: none by default; Copilot review if enabled on the repo.
- **Tracker**: none. A **Defer** here records a `wif tangent` without
  `--issue` and says so in the reply; Robin promotes it later.
- **Test / lint for a Fix**: as the repo documents (wif: `python3 -m unittest
  discover -s tests -t .` from the skill dir; shell: `shellcheck -S warning`).
