# agentfiles

Personal home for agentic coding workflows, rules, and skills — **dotfiles,
but for agentic use.** Harness-neutral markdown for Claude Code, Cursor, and
other coding agents.

This is a mix of professional and personal contexts, so the repo is split
into isolated **scopes** — see below. If you're an agent, start at
[AGENTS.md](./AGENTS.md), not this file.

## What lives here

| Path | Purpose |
|------|---------|
| [AGENTS.md](./AGENTS.md) | Agent bootstrap router — read first |
| [USER-CLAUDE.md](./USER-CLAUDE.md) | Machine-wide Claude Code hook — symlinked from `~/.claude/CLAUDE.md` |
| [scopes/](./scopes/) | Isolated workstreams: forestrie, justgames, personal |
| [workflow/](./workflow/) | Cross-scope [skills](./workflow/skills/) (= slash commands) and [rules](./workflow/rules/) |
| [bin/](./bin/) | [`agentfiles-sync`](./bin/agentfiles-sync) — installs skills into every harness |
| [vendored/](./vendored/) | Pinned third-party agent content |
| [incubator/](./incubator/) | Provisional guidance, not yet promoted |
| [harness/](./harness/) | Per-harness install notes |

## Scopes

A **scope** keeps a workstream's context, rules, and glossary completely
separate from the others — different employers/orgs and confidentiality
boundaries live side by side in one repo without leaking into each other.

| Scope | Role |
|-------|------|
| [forestrie](./scopes/forestrie/) | Personal overlay on the shared [forestrie-agents](https://github.com/forestrie/forestrie-agents) repo |
| [justgames](./scopes/justgames/) | JustGames/SentientDogs work |
| [personal](./scopes/personal/) | Personal projects and life admin automation |

See [scopes/README.md](./scopes/README.md) for the isolation rule and how an
agent detects which scope applies.

## Layer model

1. **Repo overlay** — an `AGENTS.md`/`forest/agents/`-style router in the
   working project repo itself (wins on conflict)
2. **Scope** — `scopes/<scope>/` in this repo
3. **Common workflow** — this repo's root `workflow/`
4. **Vendored** — upstream skills; extend via overlay, do not edit in place
5. **Incubator** — opt-in only; never default

## Promotion policy

Draft guidance starts in `incubator/` (repo-wide) or a scope's own
`incubator/` (e.g. `scopes/forestrie/incubator/`, for drafts destined for the
shared forestrie-agents repo rather than this one). To promote:

1. Sanitize for the target audience (no cross-scope references)
2. Open a PR moving content into the right scope's `workflow/`/`arc-context/`
   — or into this repo's root `workflow/` if it's genuinely cross-scope
3. Update the relevant README/AGENTS.md indexes

## Clone layout

Clone directly under home, as a sibling of `~/dotfiles`, so shell rc files,
symlink targets, and `@import` paths can all reference it via a short,
stable path:

```text
~/
├── agentfiles/     # this repo
└── dotfiles/
```

## Install

**Once per machine** — the Claude Code hook that makes scope routing available
in every session:

```bash
ln -s ~/agentfiles/USER-CLAUDE.md ~/.claude/CLAUDE.md
```

**Once per repo** — routing plus slash commands:

```bash
agentfiles-link <scope>    # AGENTS.md/CLAUDE.md -> the scope router  (dotfiles/bin)
agentfiles-sync <scope>    # skills -> .claude/skills, .cursor/, .agents/  (this repo's bin/)
```

`agentfiles-sync` symlinks each `<name>/SKILL.md` directory into every path
Claude Code, Cursor, and pi discover skills from, so `/plan-new` and
`/save-status` work in all three from one canonical source. Generated links are
added to `.git/info/exclude`, so they never appear in `git status`.

Per-repo is deliberate: Claude Code resolves personal skills *above* project
skills, so a machine-wide skill would shadow a scope's own. Use
`agentfiles-sync --global` only for genuinely universal skills.

See [harness/claude-code.md](./harness/claude-code.md),
[harness/cursor.md](./harness/cursor.md), or [harness/pi.md](./harness/pi.md)
for the full detail and rationale.
