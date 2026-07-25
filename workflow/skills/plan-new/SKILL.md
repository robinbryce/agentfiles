---
name: plan-new
description: Allocate the next date-cohort plan id for the current month and scaffold the plan document with frontmatter pre-filled. Use when starting a new plan or a multi-slice effort that needs a tracked plan-YYMM-NN-<slug> document.
when_to_use: The user says "new plan", "start a plan", "scaffold a plan doc", or is about to hand-name a file under a plans/ directory.
argument-hint: "<slug> [--dir]"
allowed-tools: Read, Edit, Glob, Grep, Bash
---

# /plan-new — create a date-cohort plan doc

Allocate the next plan id for the current month and scaffold the file (or
directory) with frontmatter pre-filled. Applies
[workflow/rules/planning](../../rules/planning/SKILL.md).

Arguments: `$ARGUMENTS`

- `$0` — the slug, kebab-case, e.g. `checkpoint-publisher`
- `--dir` — scaffold a **directory plan** (`README.md` + `handoff.md`) for a
  larger, multi-slice effort instead of a single file

If no slug was given, infer one from the work in hand and confirm it with the
user before allocating.

## Steps

1. Determine the plans root from the active scope's `plans_root` param (falls
   back to `docs/plans/`, then `plans/`, then `devdocs/plans/`).
2. Run the helper — it scans only the **current YYMM cohort** and picks the
   next 2-digit ordinal:

   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/new-plan.sh" <slug> [--dir] [--root <plans-dir>]
   ```

3. Open the created path, fill `refs:` with the ADRs/ARCs/issues it serves, and
   flip `status: draft → active` when work starts.

The helper prints the created path on stdout. Never hand-pick the ordinal —
let the scan allocate it so parallel branches don't collide.

## Notes

- `${CLAUDE_SKILL_DIR}` resolves to this skill's own directory whether it is
  installed at personal, project, or plugin level, so the helper is reachable
  regardless of the current working directory. On a harness that does not
  substitute it, run the script by its path under
  `workflow/skills/plan-new/scripts/`.
- The helper resolves its own symlinks to find `workflow/rules/templates/`;
  override with `NEW_PLAN_TEMPLATES` if you relocate them.
- The plan-doc `PreToolUse` guardrail
  ([harness/hooks/validate-plan.sh](../../../harness/hooks/validate-plan.sh))
  is the backstop for direct writes that skip this skill.
