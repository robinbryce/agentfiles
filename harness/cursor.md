# Cursor harness

Canonical agent files live in this repo as plain markdown. Cursor-specific
`.cursor/` paths in a project repo are **adapters**, not sources of truth.

## Recommended layout (per project repo)

```text
AGENTS.md             # thin router at repo root
.cursor/
  rules/              # symlinks or copies from agentfiles workflow/rules/ or scopes/<scope>/workflow/rules/
  skills/             # symlinks or copies
  commands/           # symlinks or copies from agentfiles workflow/commands/ or scopes/<scope>/workflow/commands/
```

## Sync commands from agentfiles

From a project repo root, for a given scope:

```bash
AGENTFILES=~/Dev/personal/agentfiles
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

1. Repo `AGENTS.md` (thin pointer)
2. The scope's `AGENTS.md` in agentfiles, for scope-specific always-on rules
3. Repo-specific overlay rules only — prefer requestable rules for common content

Never symlink more than one scope's `.cursor/rules` into the same project.
