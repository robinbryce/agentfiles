# workflow/rules

Cross-scope rules. Default: **requestable** (load when relevant). Project
repo overlays may set harness-specific `alwaysApply`.

| Rule | Scope |
|------|-------|
| [clickable-references.md](./clickable-references.md) | Every file / line / PR / issue / commit reference must be a clickable link — gitweb permalink for git content, absolute `path:line` for local-only. Cross-scope, intended always-on. |
| [planning.md](./planning.md) | Plan / ADR / ARC organisation & numbering — date-cohort plans, absolute ADR/ARC. Scopes override the params. |
| [linear-direct-api.md](./linear-direct-api.md) | Linear via the direct GraphQL API keyed by the active scope's `LINEAR_API_KEY` (not MCP / interactive login). forestrie + justgames. |

Scope-specific rules live in `scopes/<scope>/workflow/rules/` instead — this
directory is only for genuinely cross-scope conventions (e.g. general commit
hygiene, not any org's specific Linear/Jira workflow).
