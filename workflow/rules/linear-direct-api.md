---
description: Prefer the direct Linear GraphQL API with the active scope's
  LINEAR_API_KEY over MCP OAuth / interactive login. Cross-scope.
---
# Linear via direct API key (not MCP)

For any Linear work (create/update/query issues, projects, initiatives,
documents), the default mechanism is the **GraphQL API keyed by the active
scope's `LINEAR_API_KEY`** — NOT the Linear MCP server, and NOT interactive
login. Reach for MCP only if the direct API is unavailable *and* the user asks.

This exists because MCP OAuth / "current login" resolves to a single global
identity that breaks across scopes. A per-scope `.envrc` key does not.

## Resolve the key (do not print it)

Resolve from the ACTIVE scope's `.envrc`, tolerating an unset shell (direnv may
not be loaded in a non-interactive Bash tool):

    direnv exec <scope-root> printenv LINEAR_API_KEY

Scope roots:

- **forestrie** → `~/Dev/personal/forestrie` (workspace **Forestrie**, team key
  **FOR**, `robinbryce@gmail.com`)
- **justgames** → `~/Dev/justgames` *if* it defines `LINEAR_API_KEY`. If none
  exists, tell the user and stop — do **not** fall back to the forestrie key.

## Call it

    curl -s https://api.linear.app/graphql \
      -H "Authorization: $LINEAR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"query":"..."}'

Personal API keys go in the `Authorization` header directly, with **no**
`Bearer` prefix.

## Guardrails (the key IS the identity)

- Use ONLY the current scope's key. NEVER use forestrie's key for justgames work
  or vice versa — that cross-scope leak is the exact failure this rule prevents.
- Before the first *write* in a session, confirm identity once:
  `query { viewer { email } }` → expect `robinbryce@gmail.com` (forestrie).
- On `401`/`403`: report that the scope's `LINEAR_API_KEY` is missing or
  invalid and ask the user to check that scope's `.envrc`. Do **not** silently
  fall back to MCP.

## Relationship to the team rule

Forestrie's team repo carries `workflow/rules/linear-mcp-forestrie.md` with MCP
identity pre-flight checks. On this machine, **this rule takes precedence** for
mechanism choice; those MCP checks apply only in the fallback case.
