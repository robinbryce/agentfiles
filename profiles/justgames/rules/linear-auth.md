---
name: linear-auth
description: How to resolve LINEAR_API_KEY for JustGames Linear work — discovered from the scope root via direnv, never a hardcoded path, and a hard stop rather than falling back to another scope's key.
when_to_use: Any direct Linear API call (GraphQL, REST, curl, or a script) in JustGames work, or when a Linear call fails with missing or invalid auth.
user-invocable: false
---

# Linear auth — JustGames scope

Extends the cross-scope
[linear-direct-api](../../../../../workflow/rules/linear-direct-api/SKILL.md)
rule, which owns the *mechanism* decision (direct GraphQL over MCP). This file
only covers how the key is resolved **in this scope**.

## Resolve the key (never print it)

The scope root is the one recorded in the scope-detection table in
[AGENTS.md](../../../../../AGENTS.md) — `~/Dev/justgames`. Resolve through
direnv from that root, so the key follows wherever the scope's `.envrc`
actually lives:

```bash
direnv exec ~/Dev/justgames printenv LINEAR_API_KEY
```

**Do not hardcode a path to a specific `.envrc`.** An earlier version of this
guidance pinned `~/Dev/justgames/code/.envrc`; that directory no longer exists,
and the stale pin silently produced "key missing" instead of a useful error.
Resolving from the scope root has no such failure mode — if the layout moves,
direnv follows it.

## When this scope defines no key

As of 2026-07-25 **`~/Dev/justgames` defines no `LINEAR_API_KEY`** — there is
no `.envrc` under it at all.

When resolution fails:

1. Say so plainly: this scope has no Linear key configured.
2. **Stop.** Do not fall back to another scope's key. The key *is* the
   identity, and reusing the forestrie key for JustGames work is precisely the
   cross-scope leak the scope model exists to prevent.
3. Do not prompt for a key until both the environment and the direnv lookup
   have failed.

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
`LINEAR_API_KEY`. Per
[linear-direct-api](../../../../../workflow/rules/linear-direct-api/SKILL.md),
MCP is the fallback only.

## Never

- Print, echo, log, or commit the key.
- Copy it into a plan, status doc, PR body, or commit message.
