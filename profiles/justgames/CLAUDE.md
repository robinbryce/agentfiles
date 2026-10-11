# Profile: justgames

This session runs in Robin's **justgames** profile (`~/.claude-justgames`):
JustGames / SentientDogs work. Team conventions come from the
[just-agents](https://github.com/SentientDogs/just-agents) marketplace once it
is plugin-shaped; until then this profile is deliberately minimal and the old
wrappers remain in use (see plan 2610-01, decisions). Nothing from the
personal, forestrie or home profiles is installed here.

## Planning params

Defaults from `core:planning`: `plans_root` = repo `docs/plans/`,
`decisions_home` = repo `docs/{adr,arc}/`, date-cohort plan ids, absolute
ADR/ARC. No `issue_refs` prefix yet.

## Linear

See the `linear-auth` rule in this profile: resolve `LINEAR_API_KEY` from
`~/Dev/justgames` via direnv, and stop if none is defined. Never reuse another
profile's key.
