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
[core:planning](../planning/SKILL.md).

Arguments: `$ARGUMENTS`

- `$0` — the slug, kebab-case, e.g. `checkpoint-publisher`
- `--dir` — scaffold a **directory plan** (`README.md` + `handoff.md`) for a
  larger, multi-slice effort instead of a single file

If no slug was given, infer one from the work in hand and confirm it with the
user before allocating.

## Steps

1. Determine the plans root from the active scope's `plans_root` param (falls
   back to `docs/plans/`, then `plans/`, then `devdocs/plans/`). When that
   root is another repo (forestrie: `forestrie/work`), use a worktree of it
   on a branch, never the primary clone's default branch, and always pass
   `--root <worktree>/plans`: without it the helper falls back to (and
   creates) `./docs/plans` in the current repo.
2. Run the helper — it scans only the **current YYMM cohort** and picks the
   next 2-digit ordinal. It counts the cohort across the whole working tree
   (so `archive/` holds its ids), and in a git repo with an `origin` remote
   it also fetches (best effort, never prompting) and counts origin's default
   branch and the files of open GitHub PRs, so an id merged or proposed
   elsewhere is not re-allocated:

   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/new-plan.sh" <slug> [--dir] [--root <plans-dir>]
   ```

3. Open the created path, fill `repos:`, `issues:` and `refs:`, write the
   plan, and flip `status: draft → active` (bump `updated:`) when work
   starts.

**dox repos.** When [dox](https://github.com/robinbryce/dox) is on `PATH`,
`DOX_SCHEMA_REPO` is set, and the git repo holding `--root` (else the
current directory) has a `.dox.toml` whose `types` include `plan`, the
helper hands allocation to `dox new plan <slug> [--dir] [--date D]
[--offline]`, run in that repo, and prints the path dox prints. dox places
the document where its schema says, so `--root` only picks the repo, and the
scaffold comes from the schema's templates rather than this skill's. A dox
config or remote error (exit 2 or 3) warns and falls back to the built-in
scan; `NEW_PLAN_NO_DOX=1` forces the built-in path.

The helper prints the created path on stdout. Never hand-pick the ordinal —
let the scan allocate it so parallel branches don't collide. Offline it
warns and falls back to the last-fetched origin state; `--offline` (or
`NEW_PLAN_OFFLINE=1`) skips the remote entirely, for tests.

## Notes

- `${CLAUDE_SKILL_DIR}` resolves to this skill's own directory whether it is
  installed at personal, project, or plugin level, so the helper is reachable
  regardless of the current working directory. On a harness that does not
  substitute it, run the script by its path under
  `plugins/core/skills/plan-new/scripts/`.
- The helper resolves its own symlinks to find its `templates/` directory;
  override with `NEW_PLAN_TEMPLATES` if you relocate them.
- The plan-doc guardrail
  ([hooks/scripts/validate-plan.sh](../../hooks/scripts/validate-plan.sh))
  is the backstop for direct writes that skip this skill. Without dox it
  blocks a misnamed new file under `plans/` before the write. In a dox repo
  it lets the write through and, after it, runs `dox lint --json` in the
  repo and hands back the findings for that file that are not baselined;
  if dox fails with a config or remote error it says so and falls back to
  the name check.
- Tests: `python3 -m unittest discover -s plugins/core/skills/plan-new/tests`
  and `-s plugins/core/hooks/tests`.
