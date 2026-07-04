# /plan-new — create a date-cohort plan doc

Allocate the next plan id for the current month and scaffold the file (or
directory) with frontmatter pre-filled. Applies
[workflow/rules/planning.md](../rules/planning.md).

## Usage

```
/plan-new <slug> [--dir]
```

- `<slug>` — kebab-case, e.g. `checkpoint-publisher`
- `--dir` — scaffold a **directory plan** (`README.md` + `handoff.md`) for a
  larger, multi-slice effort instead of a single file

## What the agent does

1. Determine the plans root from the active scope's `plans_root` param (falls
   back to `docs/plans/`, then `plans/`, then `devdocs/plans/`).
2. Run the helper — it scans only the **current YYMM cohort** and picks the
   next 2-digit ordinal:

   ```bash
   bash ~/agentfiles/workflow/commands/new-plan.sh <slug> [--dir] [--root <plans-dir>]
   ```

3. Open the created path, fill `refs:` with the ADRs/ARCs/issues it serves, and
   flip `status: draft → active` when work starts.

The helper prints the created path on stdout. Never hand-pick the ordinal —
let the scan allocate it so parallel branches don't collide.
