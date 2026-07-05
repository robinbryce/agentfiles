# /save-status — checkpoint work in flight

Condense the current session into a `status-*.md` document that is the ideal
starting point for a **fresh agent session**: combined with the prevailing
context hooks, reading the status doc should be sufficient context to continue
the work it describes. Naming follows
[workflow/rules/planning.md](../rules/planning.md) (date-cohort scheme).

## Usage

```
/save-status [context hints...]
```

- `context hints` — optional; any of:
  - a Linear issue id (e.g. `FOR-314`)
  - a plan title
  - a plan / ADR / ARC document reference
- With no hints, establish context from the **entire current session**:
  condense the chat, and pick up references to Linear issues, active worktrees
  and branches, and relevant plan / ADR / ARC documents. Cross-check against
  recently changed or added plan docs in the shared and repo-specific plans
  roots (`docs/plans/`, `plans/`, `devdocs/plans/`).

## What the agent does

1. **Establish the workstream** from the hints (or the session, as above).
2. **Prefer update-in-place.** Scan the status root for an existing doc
   covering the same workstream (match on Linear issue id, plan ref, or slug)
   and update it rather than creating a sibling. A duplicate created by
   accident is not a disaster as long as lexical ordering stays sound, but
   each status doc is expected to track one currently active workstream
   across repeated `/save-status` calls.
3. **Otherwise create** a new doc in the status root appropriate to the
   context:
   - shared: `devdocs/status/`
   - repo-specific: `docs/status/`

   Run the shared allocation helper — it names the file with the plan
   date-cohort scheme (`status-<YYMM>-<NN>-<short-desc>.md`), scanning only
   the current `YYMM` cohort for the ordinal (same rule as `/plan-new` —
   never hand-pick against all history):

   ```bash
   bash ~/agentfiles/workflow/commands/new-plan.sh <short-desc> --prefix status [--root <status-dir>]
   ```

   Infer `<short-desc>` from the context; if the workstream is a specific
   Linear issue, put the issue id at the start, e.g.
   `status-2607-03-for-314-checkpoint-publisher.md`.

## Document content

A brief overview of the work in hand, with gitweb links (local relative links
if the docs are in the same repo) to the plans, ADRs, and ARC docs of
significance. Then:

- **Status** — what is completed
- **Notables** — design choices or implementation details discovered during
  implementation
- **Next steps** — the logical next steps
- **Blockers** — anything blocking, such as dependencies on other tasks

Use plan-style frontmatter (`id`, `status`, `created`, `refs` — see
[rules/planning.md](../rules/planning.md#frontmatter-all-plan-docs)), with
`refs:` carrying the Linear issues and plan/ADR/ARC ids the workstream serves.
On update, refresh the sections in place and keep `refs:` current rather than
appending a log.
