# Overlay — forestrie profile

- **Clones**: `~/Dev/personal/forestrie`. Checkouts live on morgan; if that root is absent here, stop
  with one line ("forestrie checkouts are on morgan; run this there").
- **Default `mode`**: `publish` (fix, push, post the cycle comment).
- **Standing design sources**: the ARC, ADRs and protocol spec the slice cites, and the plan README.
- **`rules`**: the `forestrie-core:rules-of-the-road-review` skill; cite rule ids and doc sections.
- **`escalators`**: none beyond the workflow's defaults.
- **`commitRules`**: `forestrie-core:commit-conventions`. The title is at most 79 characters, body lines
  at most 72, and there is no `Co-Authored-By` trailer.
- **`gates`**: `forestrie-core:pre-commit-checks`.
- **`tdd`**: `mattpocock-skills:tdd`.
- **`postComment`**: `false`. File the deferred issues first so the comment carries their ids.
- **Tracker**: Linear team `FOR`, key via `direnv exec ~/Dev/personal/forestrie printenv LINEAR_API_KEY`;
  never the justgames key.
  - State Backlog, no project, priority 3 for a Medium and 4 for a Low.
  - Related to the PR's issue.
