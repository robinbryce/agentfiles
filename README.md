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
| [scopes/](./scopes/) | Isolated workstreams: forestrie, justgames, personal |
| [workflow/](./workflow/) | Cross-scope commands, rules, skills |
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

Recommended as a sibling of other personal checkouts:

```text
~/Dev/personal/
├── agentfiles/              # this repo
└── forestrie/
    └── forestrie-agents/    # canonical shared Forestrie team repo
```

## Install

See [harness/claude-code.md](./harness/claude-code.md) or
[harness/cursor.md](./harness/cursor.md) for wiring this repo (and a scope)
into a specific agent harness.
