# scopes

A **scope** keeps a workstream's context, rules, and glossary completely
separate from the others. Robin works across different employers/orgs and
personal projects with different confidentiality boundaries — scopes let all
of that live in one repo without leaking into each other.

## Current scopes

| Scope | Role |
|-------|------|
| [forestrie](./forestrie/) | Personal overlay on the shared [forestrie-agents](https://github.com/forestrie/forestrie-agents) repo |
| [justgames](./justgames/) | JustGames/SentientDogs work |
| [personal](./personal/) | Personal projects and life admin automation |

## Isolation rule

An agent must determine the current scope **before** loading anything
scope-specific, and must **never** load a second scope's `arc-context/` or
`workflow/` content in the same task unless the user explicitly asks to
cross-reference. This is the entire reason scopes exist as separate
directories rather than one shared `arc-context/`.

## Scope detection

| Working on... | Scope |
|---|---|
| `~/Dev/personal/forestrie/**` (canopy, arbor, univocity, mandate, forest-1, devdocs, product, forestrie-agents) | forestrie |
| `~/Dev/justgames/**` (Flip contracts, protocol deploy, JustGames/SentientDogs code) | justgames |
| Anything else — other personal projects, dotfiles, home automation | personal |

If the working directory doesn't clearly match a row above, ask which scope
applies rather than guessing.

## Adding a new scope

1. Create `scopes/<name>/` with at minimum a `README.md` and `AGENTS.md`
2. Add `arc-context/` and `workflow/{commands,rules,skills}/` if the scope
   needs its own glossary or standards (skip if it's a thin pointer to an
   external canonical repo, like `forestrie/`)
3. Add a row to this file's tables and to the root [AGENTS.md](../AGENTS.md)
   scope-detection table
