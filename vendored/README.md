# vendored

Third-party agent content, pinned by git SHA. **Do not edit files in place.**

| Source | Path | Record |
|--------|------|--------|
| (none yet) | — | — |

To extend a vendored skill, add an overlay under
[workflow/skills/](../workflow/skills/) (cross-scope) or
`scopes/<scope>/workflow/skills/` (scope-specific) — never edit here.

When vendoring a new source, add a `<name>/` directory with a `VENDOR.md`
recording upstream URL, pinned SHA, and what was pulled in — following the
pattern used by [forestrie-agents/vendored](https://github.com/forestrie/forestrie-agents/tree/main/vendored).
