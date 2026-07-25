# Generic harness

Any agent that reads markdown can use this repo directly.

1. Read [AGENTS.md](../AGENTS.md)
2. Determine scope (forestrie / justgames / personal) from the working directory
3. Read `scopes/<scope>/AGENTS.md`
4. Read the working repo's own `AGENTS.md` overlay, if any
5. Load only the workflow skill invoked by the user

Skills follow the [Agent Skills](https://agentskills.io) standard — one
`<name>/SKILL.md` directory each, under [workflow/skills/](../workflow/skills/)
and `scopes/<scope>/workflow/skills/`. Any harness that reads that layout can
consume them directly; [`bin/agentfiles-sync`](../bin/agentfiles-sync) installs
them into the known discovery paths.

No harness-specific format required. Prefer plain markdown with relative
links, and never load more than one scope per task.
