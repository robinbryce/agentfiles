# Linear auth — JustGames scope

Extends the cross-profile `core:linear-direct-api` skill, which owns the
*mechanism* decision (direct GraphQL over MCP). This file
only covers how the key is resolved **in this scope**.

## Resolve the key (never print it)

The scope root is `~/Dev/justgames`, as the justgames profile's `CLAUDE.md`
records. Resolve through
direnv from that root, so the key follows wherever the scope's `.envrc`
actually lives:

```bash
direnv exec ~/Dev/justgames printenv LINEAR_API_KEY
```

**Do not hardcode a path to a specific `.envrc`** in commands; resolve through direnv
from the scope root, then from `~/Dev/justgames/code`, then rely on the inherited
environment inside a herdr container (next section). If the layout moves, direnv
follows it.

## Where the key comes from (verified 2026-10-24)

`~/Dev/justgames/code/.envrc` exists and exports `LINEAR_API_KEY`; herdr containers
under `~/Dev/justgames/code/.worktrees-herdr/<task>/` inherit it through their own
`.envrc` (`source_up_if_exists`), so inside a container the key is already in the
environment and `direnv exec ~/Dev/justgames printenv LINEAR_API_KEY` may print nothing
even though the key is available. Check in this order:

1. `[ -n "$LINEAR_API_KEY" ]` in the current environment.
2. `direnv exec ~/Dev/justgames printenv LINEAR_API_KEY`.
3. `direnv exec ~/Dev/justgames/code printenv LINEAR_API_KEY`.

An earlier version of this rule said the scope defined no key and that the `code/.envrc`
no longer existed; both were stale and produced false "no key" stops.

## When no key resolves

Only when all three checks fail:

1. Say so plainly: this scope has no Linear key configured.
2. **Stop.** Do not fall back to another scope's key. The key *is* the identity, and
   reusing the forestrie key for JustGames work is precisely the cross-scope leak the
   scope model exists to prevent.
3. Do not prompt for a key until the environment and both direnv lookups have failed.

To configure one, add `export LINEAR_API_KEY=…` to an `.envrc` at or under
`~/Dev/justgames`, then `direnv allow` it. Rotating means editing that file and
re-running any agent shells.

## Calling the API

```bash
curl -sS https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { id name email } }"}'
```

Personal API keys go in `Authorization` directly, with **no** `Bearer` prefix.
Confirm identity with that `viewer` query once before the first write in a
session.

## Not for Linear MCP

The MCP server authenticates through Cursor OAuth and does not read
`LINEAR_API_KEY`. Per `core:linear-direct-api`,
MCP is the fallback only.

## Never

- Print, echo, log, or commit the key.
- Copy it into a plan, status doc, PR body, or commit message.
