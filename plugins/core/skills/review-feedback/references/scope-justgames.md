# Overlay — justgames (SentientDogs)

- **Scope root**: `~/Dev/justgames/code`; containers under `.worktrees-herdr/`.
  Checkouts are on this machine (banks-7 and morgan both).
- **Standards**: apply the posture of `review-pr-justgames` (just-agents
  `review-pull-request` / `review-changes`, the repo's `AGENTS.md`, ADRs and
  rules of the road). When the PR touches curator ingestion / CRE / odds / live
  workers, or the market-queue schema, routes, binding table or consumers,
  the `rotd-review-curator-changes` / `rotd-review-market-queue-changes`
  skills (available inside flip-oracle containers via `SKILLS_PATH`) define
  the rules a Fix must not break; cite rule ids in refutations. Market extras
  (`docs/market-extras.md`, ME-* rules): side names, totals constraints and
  the participant index are immutable after the CRE create.
- **Bots to expect**: Cursor Bugbot, CodeRabbit, GitHub Copilot review,
  GitHub Advanced Security. All triaged as Feedback; refutations autonomous.
- **Tracker**: Linear workspace `justgames`, team `ENG`. Key per the profile's
  `linear-auth` rule: `$LINEAR_API_KEY` in the environment (containers inherit
  `code/.envrc`), else `direnv exec ~/Dev/justgames printenv LINEAR_API_KEY`,
  else `direnv exec ~/Dev/justgames/code …`. Confirm `viewer` once per
  session; never print the key. Deferred Findings become ENG issues in the
  PR's issue's project when it has one.
- **Test / lint for a Fix**: the repo's own (`task` targets in flip-*; curator
  `tsc` is not in CI and has a known baseline — run the touched package's
  tests, not the whole tree). For flip-oracle generated files, regenerate;
  never hand-edit.
- **Merge etiquette** (not this skill's job, but never undermine it): squash
  merges; never the GitHub rebase-merge button on flip-protocol audit rounds.
