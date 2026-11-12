# Overlay — justgames profile

- **Clones**: `~/Dev/justgames/code`; task containers under `.worktrees-herdr/<task>/<repo>`.
- **Author**: on Robin's own PRs the default `mode` is `publish`. On anyone else's PR use `report` and
  post nothing; reviewing other people's PRs is `/justgames:review-pr-justgames`.
- **Standing design sources** (add the ones the PR touches): the repo's `AGENTS.md` and `docs/adr/`;
  flip-oracle `docs/arc/`; flip-contracts `CONTEXT.md` for release, pin and deployment terms; infra-flip
  `docs/adr/` and `docs/design-iac-secrets-config.md` for Doppler and tofu.
- **`rules`**: the just-agents review posture (`workflow/commands/review-pull-request.md`,
  `review-changes.md`) and the repo's rules of the road. For curator ingestion, CRE, odds, live workers
  or the market queue use the `rotd-review-curator-changes` / `rotd-review-market-queue-changes`
  skills and cite rule ids. Market extras: `docs/market-extras.md` (ME-* rules). Code comments follow
  just-agents `workflow/rules/comment-doctrine.md`.
- **`escalators`**:
  - breaking a rules-of-the-road rule is at least Medium;
  - an ME-* violation on extras that are immutable after the CRE create is High;
  - a step that has an agent mint, sign, apply or approve, or that prints a secret, is High;
  - a hard-coded contract address, chain, token or Safe value that the pinned release supplies is Medium
    (Robin, 2026-11-12).
- **`commitRules`**: the repo's conventional-commit title as its log shows (`type(scope): summary
  (ENG-NNNN)`); a body that says why; end with the `Co-Authored-By` attribution line the session gives.
- **`gates`**: just-agents `workflow/commands/pre-commit-checks.md` where the checkout has it, else the
  touched package's own targets (`task …` in flip-*, `bun run lint` and the package tests in
  flip-dao-console). Curator `tsc` has a known baseline, so run the touched package, not the tree.
- **`tdd`**: the just-agents vendored `tdd` skill (`vendored/matt-skills/skills/engineering/tdd`).
- **`postComment`**: `false`. File the deferred issues first so the comment carries their ids.
- **Tracker**: Linear workspace `justgames`, team `ENG`. Resolve the key per the profile's `linear-auth`
  rule (environment, then `direnv exec ~/Dev/justgames`, then `~/Dev/justgames/code`); never print it.
  - State Backlog, priority 3 for a Medium and 4 for a Low.
  - Related to the PR's issue, and in that issue's project when it has one.
- **Never**: approve as `robinbryce`, merge, push to main, force-push, or dispatch a deploy.
