# Generic harness

Any agent that reads markdown can use this repo directly.

1. Read [AGENTS.md](../AGENTS.md)
2. Determine scope (forestrie / justgames / personal) from the working directory
3. Read `scopes/<scope>/AGENTS.md`
4. Read the working repo's own `AGENTS.md` overlay, if any
5. Load only the workflow command or skill invoked by the user

No harness-specific format required. Prefer plain markdown with relative
links, and never load more than one scope per task.
