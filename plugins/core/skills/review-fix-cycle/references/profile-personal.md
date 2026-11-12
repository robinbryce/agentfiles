# Overlay — personal profile

- **Clones**: `~/Dev/personal`, plus the dotfiles and agentfiles checkouts.
- **Default `mode`**: `publish` on Robin's own repos.
- **Standing design sources**: the repo's `AGENTS.md` / `CLAUDE.md`, its `docs/plans` decision tables,
  and any `DESIGN.md` beside a skill.
- **`rules`**: the repo's `AGENTS.md` rules for changes. There is no rules-of-the-road corpus.
- **`commitRules`**: the repo's convention as its recent log shows; end with the session's attribution
  line.
- **`gates`**: as the repo documents. agentfiles: `claude plugin validate .` and `bin/agentfiles doctor`.
  wif: `python3 -m unittest discover -s tests -t .` from the skill dir. Shell: `shellcheck -S warning`.
- **`tdd`**: red, green, refactor; no named skill.
- **`postComment`**: `true`.
- **Tracker**: none. Record each deferred finding with `wif tangent` and say so in the comment.
