# Provenance

- **Origin.** The review-and-fix cycle was agreed on 2026-11-10 while delivering forestrie
  plan-2611-09-log-root-authority (FOR-603). It was run by hand on every slice PR of that plan, then
  saved on 2026-11-11 as the forestrie `review-fix-cycle` workflow script. Both are Robin's own work.
- **Changed here (2026-11-12).**
  - The script is profile-neutral. Rules of the road, commit conventions, quality gates, the TDD skill
    and the clones root arrive as `args` (`rules`, `commitRules`, `gates`, `tdd`, `clones`,
    `escalators`) from `references/profile-*.md`, loaded by this skill.
  - `postComment: false` lets the caller file follow-up issues before posting. Deferred rows carry a
    `follow-up pending [<id>]` placeholder for the issue id.
  - `maxAgents` is capped at 5.
  - The workflow is named `review-fix-cycle-run`, so it never shadows a profile's own
    `review-fix-cycle`.
  - **Design stop (Robin, 2026-11-12).** A cycle that confirms a Design finding first fixes the High and
    Medium findings whose fix does not depend on it, then stops. A sonnet classifier decides dependence, and
    if it fails everything is held. On flip-tools#125, two cycles in a row stopped on a new design question
    with a verified High and eight Medium findings unfixed.
  - **Model routing** follows /core:orchestrator-mode's tiers.
  - Otherwise the review, verify and fix logic, the severities and the comment format are unchanged.
- **Sync.** Upstream edits to the forestrie script are not synced automatically: re-diff when it changes.
