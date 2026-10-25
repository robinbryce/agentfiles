---
id: plan-2610-05
status: active
created: 2026-10-25
refs:
  - plugins/core/skills/review-feedback/CONTEXT.md
  - plugins/core/skills/wif/DESIGN.md
  - plugins/core/skills/wif/references/dashboard.md
  - plugins/justgames/skills/review-pr-justgames/SKILL.md
  - profiles/justgames/rules/linear-auth.md
  - rules/herdr-session-handoff.md
---

# Plan plan-2610-05 — `review-feedback`: babysit a PR's review feedback, driven by wif

**Status:** ACTIVE · **Created:** 2026-10-25

## Context

Robin runs this prompt regularly:

> /loop 20 minutes check for review feedback. assess if you agree with the
> finding. if you agree assess if a reasonably fix is possible in the scope of
> the PR's plan and design. Reject work arounds. Reject rules of the road
> violations. fix everything that passes those filters and post a succinct
> clear humanized explanation of what you did. if all findings are addressed
> or refuted request re-review

Three of its steps are mechanics identical in every scope; the standards and
the tracker differ per scope; posting a refutation is a judgment that needs a
policy. A fixed 20-minute poll re-reads the PR whether or not anything
changed. Glossary: [review-feedback/CONTEXT.md](../../plugins/core/skills/review-feedback/CONTEXT.md).

Grilled 2026-10-25; decisions in dependency order:

| # | Decision | Chosen | Rejected |
|---|----------|--------|----------|
| 1 | Shape | **One core skill, `/core:review-feedback <pr>`, with Overlays** per scope (justgames, forestrie, personal; home inherits personal) selected by the cwd's scope as wif resolves it. GitHub identity is `robinbryce` in every scope; only the tracker differs. | a skill per scope (triplicated mechanics) |
| 2 | Overlay location | **Inside the skill**: `references/scope-<name>.md`, loaded only when the skill runs. justgames points at `review-pr-justgames`, the rotd-review skills and ME-* rules, team `ENG`; forestrie: forestrie-agents rules, team `FOR`, checkout lives on **morgan** (stop with one line when the scope's repos are absent here); personal: repo rules only, no tracker. | profile rules (load on every prompt) |
| 3 | Feedback | Unresolved review Threads + review bodies and plain comments by non-authors since the last commit the skill pushed. **Failing CI is out of scope** (a different loop). Bot findings count when delivered as Threads/comments (Bugbot, CodeRabbit, Copilot). | including check failures |
| 4 | Verdicts | **Fix / Refute / Defer / Rejected fix.** Fix: correct and within Plan and Design → one commit. Refute: wrong, or ruled out by a recorded decision → bots autonomously with evidence, humans **drafted for Robin**. Defer: correct but out of scope → Linear issue via the tangent machinery, reply names it. Rejected fix: correct but every in-scope remedy is a Workaround or a rules-of-the-road violation → nothing changed, explanation drafted. Drafts **block re-review**. Workaround = satisfies the comment without changing the behaviour it is about (suppressed warning, widened type, special-cased test, caught-and-ignored error). | agree/disagree only; autonomous human refutation |
| 5 | Ledger | **GitHub thread state.** The skill resolves every Thread it fixed or deferred right after replying with the commit SHA / issue; Refute and Rejected fix stay open. No private ledger. One commit per Finding; the touched area's tests/lint run before any push; push only to the PR branch, never force; a summary comment only when a tick handled > 1 Thread. | reviewer resolves (needs a private ledger) |
| 6 | Re-review request | Reviewers whose Threads were fixed or refuted + anyone with `CHANGES_REQUESTED`. Not approvers without Findings; never bots. | every reviewer |
| 7 | wif changes | (a) scope-wide `scan --prs` adds `reviewDecision`, `isDraft` (free from `gh pr list`); dashboard flag **`feedback`** when an own-branch PR is `CHANGES_REQUESTED`; Reference-line note `OPEN · CHANGES_REQUESTED · <title>`. (b) **`scan --prs --fresh`**: ignore the TTL for the *current container only* and fetch, per own-branch PR, the unresolved-thread count and last review activity (one GraphQL call each); both join the `--changes` signature. (c) **Loop**: `/loop /core:review-feedback <pr>` self-paced; tick = refresh + `wif show --changes`; no change → `noop`, wake stretches; **20 min cap**. The per-PR GraphQL call never runs in the scope-wide scan. | fixed 20-min poll; thread counts in the global scan (70 extra calls) |
| 8 | Glossary | `review-feedback/CONTEXT.md` created; wif's **Flag** lists `feedback`. No ADR. | — |

## Goal

```
/loop /core:review-feedback 1672          # in the PR's container, self-paced, cap 20m
… tick: wif scan --prs --fresh → wif show --changes → "no changes" → noop
… tick: eng-2654-odds-writer: #1672 CHANGES_REQUESTED · 3 open threads (was 0)
   → 3 Findings: Fix (commit a1b2c3d, reply, resolve) · Defer (ENG-2701 via wif tangent, reply, resolve)
     · Refute (human) → draft shown to Robin; re-review blocked until posted/overridden
… Robin posts the draft → next tick: all Threads answered → re-review requested from <reviewer>
```

## Approach

### W1 — wif: review state (agentfiles `plugins/core/skills/wif`)

- `scan.prs_for`: add `reviewDecision,isDraft,updatedAt` to both `gh pr list`
  and `gh pr view` field lists. `--fresh`: when the cwd's container is being
  scanned, bypass the TTL and, for each own-branch PR (not cited ones), run
  one GraphQL query (`pullRequest(number){ reviewThreads(first:100){ nodes{
  isResolved isOutdated comments(first:1){ nodes{ author{login} createdAt } } } }
  latestReviews(first:20){ nodes{ author{login} state submittedAt } } }`) →
  `unresolved`, `lastReviewAt`, `requestedChangesBy: [login]`. Cached in the
  same file; absent for containers scanned without `--fresh`.
- Flags: `feedback` when any own-branch PR has `reviewDecision ==
  CHANGES_REQUESTED` or `unresolved > 0`. `--changes` signature includes
  `(state, reviewDecision, unresolved, lastReviewAt)` per PR.
- Reference-line note: `STATE[ · CHANGES_REQUESTED][ · N open threads] · title`.
- `wif show --json` already exposes the cache; the skill reads it from there.
- Docs: dashboard.md (flag, `--fresh`), DESIGN.md routine default, CONTEXT
  Flag (done). Tests: list/view fields, `--fresh` scope, GraphQL parse +
  failure tolerance, flag, signature, note.

*W1 as built (2026-10-25):* as specified. `--fresh` implies `--prs`, applies
only to the cwd's container (exits 1 outside one), and fetches review facts
only for OPEN own-branch PRs (not cited, not merged). Suite 151 → 153.

### W2 — the skill (`plugins/core/skills/review-feedback/`)

`SKILL.md` (argument: PR number or URL; defaults to the container's
own-branch PR when exactly one is open):

0. **Scope + overlay.** `wif where --json` → scope; load
   `references/scope-<scope>.md`; stop with one line if the scope's repo for
   the PR is not on this machine.
1. **Tick gate.** `wif scan --prs --fresh --quiet`; `wif show --changes`. If
   the PR's `(reviewDecision, unresolved, lastReviewAt)` did not change and no
   draft is pending → `noop`, schedule next wake (self-paced, cap 20 min).
2. **Fetch Feedback** (decision 3): unresolved Threads via GraphQL (body,
   path, line, author, outdated); reviews and comments since the last SHA the
   skill pushed (found from its own replies: `<!-- review-feedback: <sha> -->`
   marker in each reply — the only private mark, and it lives on GitHub).
3. **Triage** each Finding to a Verdict (decision 4). Inputs: the diff, the
   PR body's plan link / `docs/plans` reference, the overlay's standards
   (justgames: invoke `review-pr-justgames` posture and, when the PR touches
   curator or market-queue, the rotd-review skills' rule ids). Bots'
   Findings and humans' Findings are triaged the same; only the posting
   policy differs.
4. **Act.** Fix: one commit per Finding, repo tests/lint for the touched area,
   push (never force) → reply (what changed, short SHA, marker) → resolve
   Thread. Defer: create the Linear issue per the scope's Linear rule
   (`core:linear-direct-api`; justgames `linear-auth`), `wif tangent --as
   eng-N-… --issue ENG-N "<finding>"`, reply with the issue URL → resolve.
   Refute (bot): reply with the evidence, leave open. Refute (human) /
   Rejected fix: write the draft into the reply text shown to Robin with a
   one-line `gh api` command that posts it; Thread stays open; re-review
   blocked.
5. **Summary + re-review** (decisions 5, 6): if > 1 Thread handled this tick,
   one PR comment listing them; when every Thread is resolved or has a posted
   answer and no draft is pending, `gh pr edit --add-reviewer` for the
   addressed reviewers + `CHANGES_REQUESTED` authors; `wif mark -n "awaiting
   re-review from <logins> since <sha>" -p …`.
6. **Report** (humanized): per Thread one line — verdict, what was done, link
   (Reference lines style) — then drafts awaiting Robin, then the next wake.

`references/`: `scope-justgames.md`, `scope-forestrie.md`,
`scope-personal.md` (home → personal), `triage.md` (the Workaround test, the
"within Plan and Design" test with examples), `github-api.md` (the GraphQL
queries, resolveReviewThread mutation, the reply marker).

*W2 as built (2026-10-25):* `plugins/core/skills/review-feedback/` — SKILL.md
(§0 posture, §1 scope/overlay + PR resolution + author check, §2 tick gate,
§3 fetch, §4 verdict table, §5 act, §6 re-review, §7 report), `references/
triage.md` (the two tests, Workaround shapes), `references/github-api.md`
(the one GraphQL query — verified live on flip-oracle#1672 — reply, resolve,
comment, re-request, the marker), overlays for justgames / forestrie /
personal. `--dry-run` and `--once` flags. Plugin manifest description lists
the skill; `claude plugin validate` passes.

### W3 — wiring and docs

- agentfiles `core` plugin picks the new skill up automatically (skills dir);
  `claude-<profile> plugin update core@agentfiles` after merge.
- wif `SKILL.md` §5 tick: note that `--fresh` exists for a single container.
- `rules/herdr-session-handoff.md`: unchanged; the skill's `wif mark -n` keeps
  the stream honest for handoff.

### W4 — verification

- wif: suite green with the new tests; live `wif scan --prs --fresh` from a
  container with an open PR shows `unresolved`/`lastReviewAt` in its cache
  file and the `feedback` flag when applicable; a second `--fresh` within the
  TTL refetches only that container.
- skill: dry run on a real PR of Robin's with at least one bot Thread and one
  human Thread: verdicts and drafts printed, nothing posted (`--dry-run`);
  then a live tick on a PR Robin picks, confirming reply + resolve + marker,
  and that a `noop` tick costs only the two wif commands.

## Order

W1 first (it improves the dashboard on its own), then W2 with a `--dry-run`
flag before any posting path is exercised, then W3/W4.

## Out of scope

- Fixing failing CI (decision 3).
- Autonomous refutation of human reviewers (decision 4).
- A private findings ledger (decision 5).
