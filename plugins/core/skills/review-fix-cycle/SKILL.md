---
name: review-fix-cycle
description: Run review-and-fix cycles on a slice PR, or a design and feasibility review on a slice doc before any code. Two independent reviewers (correctness and security, design conformance), one skeptic per High, Medium or Design finding, one commit per fixed finding with a test first for behaviour (a new row in an existing table test where one fits), stopping after the first cycle with no High or Medium (at most 4 cycles, at most 5 agents at once), with one "Review cycle n" comment per cycle. Resolves the active profile's overlay (rules of the road, commit conventions, quality gates, tracker) and launches the /core:review-fix-cycle-run workflow with it. Use after every push to a slice PR without being asked, on a slice doc before implementation, or when Robin asks for a review cycle.
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
- **Design holds** (`stoppedBy: design`): the cycle has already fixed what did not depend on the hold. Give
  Robin, or decide as coordinator when the question refines an existing ruling, what the design says, what the
  code needs, the options and a recommendation, from the returned `design` list. Do not fix around it. Re-run
  with the next `firstCycle` once it is decided.
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
| Low | misleading comments, dead code, small test gaps, naming, docs; also a design question whose answer only touches one of these | fixed only when narrow, on the reading the design sources support best, else deferred. Never holds the run |
| Design | the design sources are wrong, contradict each other, or are silent on something the change had to decide, and the answer changes High or Medium behaviour | never fixed in place. The cycle still fixes the High and Medium findings whose fix does not depend on it, holds the rest, then stops |

Every finding needs `path:line` and the failing input or sequence. A finding that predates the PR
or belongs to another slice is deferred, not fixed.

A cycle with no High or Medium is the last: its Lows are fixed or deferred and nothing re-reviews
them. A behaviour fix adds a row to an existing table test, or changes an existing assertion, before
it adds a new test. No test for a comment, doc, naming or dead-code fix, and never a test that copies
a table or constant from the code or exercises a test double (Robin, 2026-11-14).

## Handoffs

Hand off to a fresh session between commits whenever that helps context or accuracy, never in the
middle of a cycle. At every handoff, print a copy-paste kick-off prompt and record it under the
plan's `handoff.md` **Resume prompt**.

## Model routing

Both workflows route each agent along `/core:orchestrator-mode`'s tiers, so the expensive model is spent
only where judgement matters:

| Step | Model |
|---|---|
| precheck, posting the comment, wif tracking | haiku |
| design-conformance and feasibility review, verifying a Medium, fixing a Medium or Low, building a slice from its spec | sonnet |
| correctness and security review, verifying a High or Design finding, a fix batch that contains a High | the session model |

Override with `models` (review) or `models` / `reviewModels` (waves); `'main'` means the session model. A
plan slice whose code carries authority or payment risk sets `model: 'main'` for its build lane. A profile
overlay may set different defaults.

## Running a whole plan in waves

[`plan-wave-run`](../../workflows/plan-wave-run.js) (`/core:plan-wave-run`) runs one wave of a plan
directory and stops at the next human gate: merges, release tags and privileged steps.

- **`wave: doc-review`**: this cycle in doc mode on every slice doc. It reports only.
- **`wave: build`**: each slice whose dependencies are merged gets one implementer, then this cycle on each
  of its PRs.

Build its `args` from the same overlay: `review.args` takes `rules`, `escalators`, `commitRules`,
`gates`, `tdd`, `clones` and `postComment`. The coordinator keeps the gate state (`merged`, `blocked`)
between runs, and keeps it in the plan's `handoff.md` beside the slice graph.

At most 5 agents are in flight at once, review runs included. An implementer holds one permit; a review
run holds `reviewAgents` and is told to use no more.

**wif keeps the perspective.** The plan's container is the parent stream.
- Each build lane runs `herdr-task <slice task> <repos…> -p <parent stream> -g "<slice goal>"`. Every slice
  gets its own container, branch and child stream.
- A lane records `wif mark -p/-n` as it goes, and a design hold becomes a `wif note`.
- `wif scan --prs` then follows each slice's PR review state.
- `/core:wif` shows the whole plan at a glance: which slices are building, under review, awaiting merge
  or held.
- After each run the coordinator writes the wave summary and the next gates to the parent stream: a
  `wif note` per gate, and `wif remind` for gates with a date.
