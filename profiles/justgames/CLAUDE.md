# Profile: justgames

This session runs in Robin's **justgames** profile (`~/.claude-justgames`):
JustGames / SentientDogs work. Robin's own justgames skills arrive as the
`justgames` plugin from agentfiles (`/justgames:review-pr-justgames` for any
PR review in a justgames repo), plus `core`. Team conventions come from the
[just-agents](https://github.com/SentientDogs/just-agents) checkout. Nothing
from the personal, forestrie or home profiles is installed here.

## Planning params

Defaults from `core:planning`: `plans_root` = repo `docs/plans/`,
`decisions_home` = repo `docs/{adr,arc}/`, date-cohort plan ids, absolute
ADR/ARC. No `issue_refs` prefix yet.

## Linear

See the `linear-auth` rule in this profile: resolve `LINEAR_API_KEY` from
`~/Dev/justgames` via direnv, and stop if none is defined. Never reuse another
profile's key.
