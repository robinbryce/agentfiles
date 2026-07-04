# workflow/rules

Cross-scope rules. Default: **requestable** (load when relevant). Project
repo overlays may set harness-specific `alwaysApply`.

| Rule | Scope |
|------|-------|
| [planning.md](./planning.md) | Plan / ADR / ARC organisation & numbering — date-cohort plans, absolute ADR/ARC. Scopes override the params. |

Scope-specific rules live in `scopes/<scope>/workflow/rules/` instead — this
directory is only for genuinely cross-scope conventions (e.g. general commit
hygiene, not any org's specific Linear/Jira workflow).
