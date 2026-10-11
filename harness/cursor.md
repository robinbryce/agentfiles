# cursor-agent

Nothing is generated for Cursor any more. It reads the two standard files a
repo commits:

- `AGENTS.md` at the repo root (routing)
- `.agents/skills/<name>/SKILL.md` (skills), which `agentfiles sync` vendors
  from the marketplace, or `npx skills add <repo> -a cursor`

For a repo outside any profile workspace, `agentfiles link <profile>` creates
`AGENTS.md` → the profile's `CLAUDE.md` (and `CLAUDE.md` → `AGENTS.md`).

Unverified: whether `cursor-agent` walks up to the git root for `AGENTS.md`
from a nested cwd. If routing seems missing, launch from the repo root or
pass `--workspace $(git rev-parse --show-toplevel)`.
