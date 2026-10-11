# personal/workflow/skills

Scope-specific skills — each is a `<name>/SKILL.md` directory, invocable as
`/<name>` once installed by [`bin/agentfiles-sync`](../../../../bin/agentfiles-sync).

A skill here **shadows** a cross-scope skill of the same name from
[workflow/skills/](../../../../workflow/skills/), because scope sources are
applied after common ones.

| Skill | Purpose |
|-------|---------|
| (none yet) | — |

## Project-local skills elsewhere

Some personal projects carry their own Claude Code skills in a repo-local
`.claude/skills/`, because they are inseparable from that repo's tooling and
paths. Those are auto-discovered when working in that directory — there is
nothing to load from here. Listed so they are findable:

| Repo | Skills | What |
|------|--------|------|
| `~/Dev/personal/training` | `push-workouts`, `author-workout`, `update-training-log` | Push the stable Day A–D workouts to Garmin Connect, and the weekly fetch-recordings → update-log → render cycle. Design in that repo's `plans/plan-2608-02-workouts-as-data.md`. |
