# Cursor harness

Canonical agent files live in this repo as plain markdown. Cursor-specific
`.cursor/` paths in a project repo are **adapters**, not sources of truth.

## No global hook — confirmed, not a gap in this repo

Unlike Claude Code, `cursor-agent` (the CLI) has **no user-level rules file**
and **no environment variable** that selects config — confirmed via the CLI's
own `--help` output and the Cursor community forum, not assumed. It only
reads `AGENTS.md` / `CLAUDE.md` / `.cursor/rules` at the project root. So
scope routing for cursor-agent has to be set per repo — see below.

**Unverified caveat:** it isn't confirmed whether `cursor-agent` walks up to
the git root for `AGENTS.md`/`CLAUDE.md`, or only checks the literal cwd (the
`--workspace <path>` flag defaults to cwd, which hints it might not walk
up). If scope routing doesn't seem to be picked up from a nested
subdirectory, launch from the repo root or pass `--workspace
$(git rev-parse --show-toplevel)` explicitly.

## Per-repo scope lock (required for cursor-agent, optional for Claude Code)

```bash
ln -s ~/agentfiles/scopes/<scope>/AGENTS.md AGENTS.md
ln -s AGENTS.md CLAUDE.md
```

Do this once per repo you want `cursor-agent` to understand. See
[claude-code.md](./claude-code.md) for how this interacts with Claude's
global hook.

## Recommended layout (per project repo)

```text
AGENTS.md             # symlink to the scope's AGENTS.md (above)
CLAUDE.md             # symlink to ./AGENTS.md
.cursor/
  rules/              # symlinks or copies from agentfiles workflow/rules/ or scopes/<scope>/workflow/rules/
  skills/             # symlinks or copies
  commands/           # symlinks or copies from agentfiles workflow/commands/ or scopes/<scope>/workflow/commands/
```

## Sync commands from agentfiles

From a project repo root, for a given scope:

```bash
AGENTFILES=~/agentfiles
SCOPE=personal   # or forestrie / justgames
mkdir -p .cursor/commands
for f in "$AGENTFILES"/workflow/commands/*.md "$AGENTFILES"/scopes/"$SCOPE"/workflow/commands/*.md; do
  base=$(basename "$f" .md)
  [ "$base" = README ] && continue
  ln -sf "$f" ".cursor/commands/$base.md"
done
```

For rules, Cursor expects `.mdc` with YAML frontmatter — maintain a thin
`.mdc` that `@include`s or links to the agentfiles markdown, rather than
duplicating content.

## Bootstrap

Point always-applied workspace rules at:

1. Repo `AGENTS.md` (symlink to the scope, per above)
2. Repo-specific overlay rules only — prefer requestable rules for common content

Never symlink more than one scope's `.cursor/rules` into the same project.
