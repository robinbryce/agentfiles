---
name: review-feedback
description: Babysit one pull request's review feedback in a self-paced loop. Each tick refreshes the PR's review state through wif and acts only when it changed - fetch the unresolved review threads and post-push comments, give every finding a verdict (fix / refute / defer / rejected fix), fix what fits the PR's plan and design with one commit per finding, reply with the commit, resolve the thread, defer out-of-scope findings to a Linear issue via the tangent machinery, draft human refutations for Robin, and request re-review from the reviewers whose threads were addressed once nothing is pending. Scope overlays (justgames / forestrie / personal) supply the standards and tracker. Use when Robin asks to watch a PR for review feedback, babysit a PR, address review comments, handle Bugbot / CodeRabbit / Copilot findings, or runs it under /loop.
argument-hint: "[<pr number|url>] [--dry-run] [--once]"
allowed-tools: Bash(wif *) Bash(gh *) Bash(git *) Bash(curl *) Bash(direnv *) Read Grep Glob Edit Write
---

# review-feedback — act on a PR's review feedback, driven by wif

```
/loop /core:review-feedback [<pr>]        self-paced loop; wake stretches when quiet, cap 20 min
/core:review-feedback <pr> --once         one tick, then stop
/core:review-feedback <pr> --dry-run      fetch and triage, print every verdict and draft, post nothing
```

Glossary: [CONTEXT.md](./CONTEXT.md). Plan: `docs/plans/plan-2610-05-review-feedback-skill.md`.
Overlays: [references/scope-justgames.md](./references/scope-justgames.md),
[references/scope-forestrie.md](./references/scope-forestrie.md),
[references/scope-personal.md](./references/scope-personal.md) (home → personal).
Triage rules: [references/triage.md](./references/triage.md).
GitHub calls: [references/github-api.md](./references/github-api.md).

## 0. Posture

- **The Ledger is GitHub.** Which Findings are handled is read from the
  Threads' resolved state and from the skill's own replies (each carries
  `<!-- review-feedback: <sha> -->`). Keep no private list.
- **Only a change makes work.** A tick that finds no change costs two wif
  commands and ends as `noop`.
- **Posting policy.** Fixes, deferrals and bot refutations post autonomously.
  A refutation of a human reviewer, or a rejected fix, is **drafted** for
  Robin and blocks the re-review request until posted or overridden. Never
  argue with a human in public on Robin's behalf.
- **Never force-push, never rebase the PR branch, never touch another PR.**
  One commit per Finding, on the PR's branch, after the touched area's tests
  or lint pass.
- `--dry-run` posts nothing, resolves nothing, pushes nothing, creates no
  issue; it prints what every step would do.

## 1. Scope and overlay (every tick)

1. `wif where --json` → `scope`, `kind`, `id`. Load
   `references/scope-<scope>.md` (`home` loads `scope-personal.md`). If the
   overlay says this scope's checkouts live elsewhere (forestrie → morgan)
   and the PR's repo is not under the scope root here, stop with one line.
2. Resolve the PR: the argument (number or URL), else the single OPEN
   own-branch PR in `wif show --json` for this container; two or more →
   stop and list them. Record `owner/repo`, `number`, `headRefOid`, author.
3. If the PR's author is not Robin's login (`gh api user --jq .login`), stop:
   this skill answers feedback on Robin's PRs; reviewing others' is
   `review-pr-justgames`.

## 2. Tick gate

1. `wif scan --fresh --quiet` (inside the container; fetches only this
   container's PRs — never a scope-wide refetch on a tick).
2. `wif show --changes`. A change counts when this PR's `reviewDecision`,
   `unresolved` or `lastReviewAt` moved, or a draft from a previous tick is
   still pending in your context. Otherwise: print one line
   (`no review changes on #N; next check in <m> min`) and, under `/loop`,
   schedule the next wake — 5 min after a change, doubling while quiet, cap
   20 min — with `noop`. First tick after start always proceeds.

## 3. Fetch Feedback

Per [github-api.md](./references/github-api.md): unresolved Threads (id,
path, line, outdated, first comment's author/body/databaseId, later comments),
`latestReviews` (state, author, body, submittedAt), issue comments newer than
the skill's newest marker reply (its timestamp, not its SHA — a deferral's
marker carries an issue id; none → since the PR's creation). Drop anything
authored by Robin's login. Bots count
(Bugbot, CodeRabbit, Copilot, GitHub Advanced Security) when they appear as
Threads or comments. Failing checks are not Feedback.

## 4. Triage — one Verdict per Finding

Read the diff for the Thread's path and the PR body's plan link (or the
`docs/plans` reference it names). Apply [triage.md](./references/triage.md):

| Verdict | When | Action |
|---|---|---|
| **Fix** | correct about the code as it stands; a remedy exists inside the PR's Plan and Design and is not a Workaround or a rules-of-the-road violation | one commit, test/lint, push, reply with the short SHA + marker, **resolve** |
| **Refute** | wrong about the code, or asks for what a recorded decision rules out | bot: reply with evidence (file:line, decision), leave open. human: **draft** |
| **Defer** | correct, belongs outside this PR | Linear issue per the overlay's tracker rule; `wif tangent --as <eng-N-words> --issue <ID> "<finding>"`; reply with the issue URL; **resolve** |
| **Rejected fix** | correct, but every in-scope remedy is a Workaround or breaks a rule of the road | nothing changed; **draft** the explanation |

**Already fixed at head.** Many Threads are `isOutdated` because a later
commit changed the lines. Before any other Verdict, check whether the current
head already satisfies the Finding (read the code at `headRefOid`; `git log
-S`/`git blame` on the Thread's path finds the commit). If it does, the
Verdict is Fix with nothing to change: reply naming that commit (`fixed in
<short sha>` + what it did + the marker) and **resolve**. The dry run on
just-agents#35 (2026-10-25) found all seven open Threads in this state.

Bots and humans are triaged identically; only the posting policy differs.
When in doubt between Fix and Rejected fix, it is Rejected fix: the cost of a
Workaround is paid later by someone else.

## 5. Act

- **Fix**: the container's worktree is already on the PR branch. Edit,
  run the overlay's test/lint command for the touched area, `git commit` with
  a subject that names the Thread (`fix(review): <path> — <finding in 6 words>`),
  `git push` (no `--force`). Reply on the Thread (what changed, why it is the
  right fix, `<short sha>`, the marker). Resolve the Thread.
- **Defer**: create the issue (title ≤ 70 chars; body = the Finding verbatim,
  **Context** with the PR link and Thread URL, **Discovered from** the stream,
  **Acceptance criteria**), then the `wif tangent` line, then reply + resolve.
- **Refute (bot)**: reply with the evidence; leave the Thread open.
- **Refute (human) / Rejected fix**: compose the reply as a draft. Print it
  under `drafts for Robin` with the one-line `gh api … -F body=@-` that
  posts it. Do not resolve. Re-review is blocked while any draft is pending.
- After all actions in a tick: if more than one Thread was handled, one PR
  comment summarising them (one line each: verdict, what, link). Then
  `wif mark -n "<next>" -p "<position>"`: e.g. `awaiting re-review from <logins> since <sha>`
  or `2 drafts awaiting Robin on #N`.

## 6. Re-review request

When every Thread is resolved or carries a posted answer and no draft is
pending: `gh pr edit <n> --add-reviewer <login>…` for the authors of the
Threads fixed or refuted this round **plus** everyone in `requestedChangesBy`.
Never approvers without Findings; never bots. Reply nothing else. Record it
with `wif mark -n "awaiting re-review from … since <sha>"`.

## 7. Report (every tick that did work)

Humanized, one block:

```
#1672 · 3 threads this tick
  fixed    src/x.ts:42 — null guard on cursor → a1b2c3d (resolved)
  deferred docs/plan.md — second provider fallback → ENG-2701 (resolved)
  draft    tests/y.spec.ts — "flaky" claim; evidence says deterministic → awaiting Robin
re-review: blocked by 1 draft
next check: 5 min
```

Then the drafts, verbatim, each followed by its post command. Under `/loop`,
end with the wake schedule.
