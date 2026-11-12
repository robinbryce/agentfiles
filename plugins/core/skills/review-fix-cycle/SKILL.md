---
name: review-fix-cycle
description: Run review-and-fix cycles on a slice PR, or a design and feasibility review on a slice doc before any code. Two independent reviewers (correctness and security, design conformance), one skeptic per High, Medium or Design finding, one commit per fixed finding with a test first, repeated until no High or Medium remain (at most 4 cycles, at most 5 agents at once), with one "Review cycle n" comment per cycle. Resolves the active profile's overlay (rules of the road, commit conventions, quality gates, tracker) and launches the /core:review-fix-cycle-run workflow with it. Use after every push to a slice PR without being asked, on a slice doc before implementation, or when Robin asks for a review cycle.
argument-hint: "[<pr number|url> | --doc <slice.md>] [--mode report|fix|publish] [--first-cycle N] [--dry-run]"
allowed-tools: Bash(wif *) Bash(gh *) Bash(git *) Bash(jq *) Bash(curl *) Bash(direnv *) Read Grep Glob Workflow
---

# review-fix-cycle

```
/core:review-fix-cycle                      the current container's own open PR, profile default mode
/core:review-fix-cycle 123 --mode report    find and verify only; change and post nothing
/core:review-fix-cycle --doc <slice.md>     design review + feasibility against origin/main; fixes nothing
```

The cycle itself is the workflow [`review-fix-cycle-run`](../../workflows/review-fix-cycle-run.js)
(invoked as `/core:review-fix-cycle-run`). It is profile-neutral: this skill supplies every
profile-specific value through its `args`. Origin and changes: [PROVENANCE.md](./PROVENANCE.md).

## When it runs

- After every push to a slice PR, without being asked.
- On a slice doc before any code is written (`--doc`). Nothing is fixed in this mode.
- Merging, deploying, approving and anything that runs on a lane still need a human go-ahead for
  each PR or run. This skill never does them.

## 1. Profile overlay

```bash
p=$(basename "${CLAUDE_CONFIG_DIR:-}" | sed -n 's/^\.claude-//p')
[ -n "$p" ] || p=$(wif where --json 2>/dev/null | jq -r '.account // empty')
```

Load `references/profile-<p>.md` (`justgames`, `forestrie`, `personal`, `home`); with no match use
[references/profile-default.md](./references/profile-default.md). Never apply another profile's
overlay: its skills, clones and tracker key are not available here. If the overlay says this
profile's checkouts live elsewhere and the target is not under its clones root, stop with one line.

## 2. Target

- **PR**: the argument, else the single open own-branch PR of this container (`wif show --json`);
  two or more, stop and list them. Record `owner/repo`, number, author and the worktree path that
  has the PR branch checked out (`git worktree list`). The overlay says what to do when the author
  is not Robin (`gh api user --jq .login`).
- **Doc**: the slice doc path; the plan README sits beside it.
- **Design sources**: the plan README and the slice doc (from the PR body, the branch's plan
  directory, or `wif show`), plus the overlay's standing sources for the touched repos. At least
  one is required.

## 3. Run

1. Build `args`: `profile`, `kind`, `repo`, `pr`, `worktree` or `doc`, `design`, `slice`, `mode`
   (argument, else the overlay's default), `firstCycle` (argument, else 1 plus the highest
   "Review cycle n" already on the PR), `maxCycles: 4`, `maxAgents: 5`, and from the overlay:
   `rules`, `escalators`, `commitRules`, `gates`, `tdd`, `clones`, `postComment`.
   `--dry-run` forces `mode: report`.
2. Run the workflow once with `selftest: true` and show Robin the one-line plan it returns
   (target, mode, cycles, reviewers). Then run it for real:
   `Workflow({name: "core:review-fix-cycle-run", args})`.

## 4. After the run

- **Deferred findings** (scope preexisting or out-of-slice, or a Low too wide to fix): file them per
  the overlay's tracker rule, one issue each, related to the PR's issue. With `postComment: false`,
  replace each `follow-up pending [<id>]` in `commentMarkdown` with `deferred to <ISSUE>` and post
  the comment yourself (`gh pr comment <n> --body-file <file>`). A profile without a tracker records
  each with `wif tangent` and says so in the comment.
- **Design holds** (`stoppedBy: design`): stop. Give Robin what the design says, what the code needs,
  the options and a recommendation, from the returned `design` list. Do not fix around it.
- **`not-fixed` or `fix-failed`**: report each with its note; do not retry blindly.
- **`maxCycles`**: High or Medium remain after 4 cycles. Say so and offer a new run with the
  `firstCycle` the log names.
- If a figure in a posted comment turns out wrong, correct the comment.

## Severities, and fix, defer or hold

The workflow carries the definitions. In short:

| Severity | Meaning | Outcome |
|---|---|---|
| High | ships wrong behaviour: a bypassable or wrongly failing authority, payment, signature or proof check; funds or data at risk; a contract, wire-format or API break | fixed when the fix stays inside the agreed design |
| Medium | a real bug with limited reach, or a contradiction of an ADR, ARC, spec, rule of the road or locked decision; a missing test on an authority or payment path | fixed as High |
| Low | misleading comments, dead code, small test gaps, naming, docs | fixed only when narrow, else deferred |
| Design | the design sources are wrong, contradict each other, or are silent on something the change had to decide | never fixed in place; the run stops |

Every finding needs `path:line` and the failing input or sequence. A finding that predates the PR
or belongs to another slice is deferred, not fixed.

## Handoffs

Hand off to a fresh session between commits whenever that helps context or accuracy, never in the
middle of a cycle. At every handoff, print a copy-paste kick-off prompt and record it under the
plan's `handoff.md` **Resume prompt**.
