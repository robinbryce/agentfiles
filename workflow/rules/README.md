# workflow/rules

Cross-scope rules. Default: **requestable** (load when relevant). Project
repo overlays may set harness-specific `alwaysApply`.

| Rule | Scope |
|------|-------|
| [clickable-references.md](./clickable-references.md) | Every file / line / PR / issue / commit reference must be a clickable link — gitweb permalink for git content, absolute `path:line` for local-only. Cross-scope, intended always-on. |
| [planning.md](./planning.md) | Plan / ADR / ARC organisation & numbering — date-cohort plans, absolute ADR/ARC. Scopes override the params. |
| [linear-direct-api.md](./linear-direct-api.md) | Linear via the direct GraphQL API keyed by the active scope's `LINEAR_API_KEY` (not MCP / interactive login). forestrie + justgames. |
| [multi-repo-fanout.md](./multi-repo-fanout.md) | Fan out to execute, never to decide — one context spanning repos makes the cross-repo decisions, per-repo agents implement an already-written plan. The plan is the interface. Cross-scope. |
| [pr-descriptions.md](./pr-descriptions.md) | PR descriptions are self-contained: introduce and link every term, id or decision before using shorthand for it; lead with the change in plain words; no bullets of bare identifiers. Cross-scope, always-on when creating or editing a PR. |
| [herdr-session-handoff.md](./herdr-session-handoff.md) | In herdr task worktrees, proactively offer a "ready to clear and hand off" block at clean completion points — kickoff prompt, absolute memory/handoff paths, stay-vs-new-workspace advice. Cross-scope, always-on in `*/.worktrees-herdr/*`. |

Scope-specific rules live in `scopes/<scope>/workflow/rules/` instead — this
directory is only for genuinely cross-scope conventions (e.g. general commit
hygiene, not any org's specific Linear/Jira workflow).
