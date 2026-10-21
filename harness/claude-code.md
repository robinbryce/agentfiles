# Claude Code

## Profiles

`bin/agentfiles bootstrap <profile>` creates `~/.claude-<profile>` with:

- `CLAUDE.md` → `profiles/<profile>/CLAUDE.md` (user instructions, every session)
- `rules/*.md` → `rules/` and `profiles/<profile>/rules/` (user rules; `paths:`-scoped ones load on demand)
- `settings.json` rendered from `profiles/<profile>/settings.json`: marketplaces
  (`extraKnownMarketplaces`, `directory` source so plugins load **in place**
  from the checkout), `enabledPlugins`, and
  `instructionFiles: claude-md-and-agents-md` so repo `AGENTS.md` files load
  even when a `CLAUDE.md` exists somewhere above
- the marketplaces registered and plugins installed with `claude plugin …`

Select a profile by directory (direnv exports `CLAUDE_CONFIG_DIR`) or by
wrapper (`claude-forestrie`). The plain `claude` wrapper honours direnv first.

## The default `~/.claude`

Verified (plan 2610-01, Q2): `~/.claude/CLAUDE.md` loads **in addition** to
the profile's `CLAUDE.md`. Keep it to this stub:

```markdown
# Unprofiled Claude Code session
No profile is active. Prefer `claude-personal`, `claude-forestrie` or `claude-home`
(see ~/agentfiles). Nothing else is configured here on purpose.
```

Move hooks and permissions out of `~/.claude/settings.json`; they belong in a
profile template or ship with a plugin.

## Plugins

- Skills are namespaced: `/core:plan-new`, `/forestrie-core:review-changes`.
- Edit a skill in the checkout, then `/reload-plugins`. No version bump.
- `claude plugin validate ~/agentfiles` after structural changes.
- Hooks ship with the plugin (`plugins/core/hooks/hooks.json`); nothing to
  wire by hand.

## Cloud sessions

Plugins and user config never load in a cloud session. A repo gets parity by
committing `AGENTS.md`, `.claude/rules/` and `.agents/skills/` (with
`.claude/skills/` symlinks); `agentfiles sync <repo> --manifest …` produces
that layer. Account skills enabled on claude.ai load everywhere you are
signed in.
