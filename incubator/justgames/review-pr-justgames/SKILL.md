---
name: review-pr-justgames
description: Chat-only pull-request review for JustGames / SentientDogs repos (flip-*, just-*, infra-flip, release-eng) from Robin's perspective (GitHub login robinbryce), for Robin's own PRs and other people's. Runs pre-checks, detects re-review against robinbryce's prior review and focuses on the delta, applies the just-agents review-pull-request / review-changes rules plus the repo's rules-of-the-road, ADRs and flip-oracle ME-* market-extras rules, triages every PR comment and bot finding, runs the check-drift ownership and binding-docs check, and runs a gated multi-agent adversarial pass (two blind reviewer subagents plus consensus) when the PR is Medium-or-higher complexity, or on re-review only when the remediation delta is itself high-risk or a big delta from the original. Never posts to GitHub. Use when asked to review a PR, re-review a PR, look at a pull request, check what reviewers or bots said on a PR, or give a verdict on a PR in any justgames repo.
allowed-tools: Bash(gh *) Bash(git *) Read Grep Glob Agent
---

# review-pr-justgames

Do a **chat-only** review. Do NOT post, comment, approve or request changes on
GitHub, and do NOT write Linear comments/issues or local remediation-plan
files, unless Robin explicitly says so **after** seeing the review.

Robin's GitHub login is `robinbryce`. "My review" below always means a review
or review-comment authored by `robinbryce`. Treat Robin's own PRs exactly like
anyone else's: same rigour, same verdict scale.

Argument: a PR number or URL. Repo defaults to the git remote of the cwd.

## 0. Working posture

- Orchestrate; do not absorb raw output. Mechanical gathering (listing files,
  pulling comments, counting lines) goes to a `haiku` subagent that returns a
  bounded summary. Judgement stays with you.
- Subagent reports are evidence, not truth. Verify every Medium+ finding
  yourself with one targeted read before it goes in the table.
- Clickable references everywhere: `path:line` for local files, permalinks
  (`https://github.com/<org>/<repo>/blob/<fullsha>/<path>#L<n>`) for PR
  content, links for every ticket / ADR / rule id cited.

## 1. Pre-checks

Gather with `gh` (delegate the pulls, keep the reading):

```bash
gh pr view <N> --json number,title,author,state,isDraft,mergedAt,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus,body,url,reviews,comments,files,additions,deletions
gh api repos/<o>/<r>/pulls/<N>/reviews           # formal reviews (incl. bots)
gh api repos/<o>/<r>/pulls/<N>/comments          # inline review threads
gh api repos/<o>/<r>/issues/<N>/comments         # conversation comments
gh api repos/<o>/<r>/pulls/<N>/commits           # commit list with dates
```

1. **My review state.** Filter reviews and comments for `user.login ==
   "robinbryce"`. If any exist, this is a **re-review**: record the timestamp
   and commit SHA of my latest review, and compute the delta = commits and
   diff since that SHA, plus every comment / review / bot finding posted after
   that timestamp. The re-review focuses on the delta; the original diff is
   context only.
2. **PR facts.** Draft, closed, merged, stale (base moved far ahead; see
   `mergeStateStatus`), stacked (base is not `main`), conflicting with main,
   and whether main already contains the same work (`git log main --grep`,
   `git cherry`). Note any open PR it replaces or builds on, by number.
3. **Where things live.** The repo under review must have `just-agents` as a
   sibling checkout (`~/Dev/justgames/code/just-agents`). In a herdr worktree
   set `JUST_CODE=~/Dev/justgames/code` so check-drift finds siblings.

## 2. Complexity rating and review-mode gate

Rate complexity **before** reading the diff in depth, then record the decision
in Part A as `Review mode:` with the reason. Rate from the file list, sizes
and touched paths:

| Signal (any one) | Rating |
|---|---|
| Touches money, payout, resolution, settlement, refund, queue state machines, contracts, deploy / release workflows, secrets, auth, or a cross-repo contract (ABI, API schema, event binding) | High-risk class |
| Adds or changes an ADR, rules-of-the-road, spec, or identity-registry seed | High-risk class |
| New provider, provider vocabulary pin, or market type | High-risk class |
| More than ~300 changed lines (excluding generated / lockfiles / fixtures) or more than ~10 non-trivial files | Large |
| Concurrency, cursors, retries, idempotency, migrations | High-risk class |

- **Low**: none of the above. **Medium**: one signal. **High**: two or more
  signals, or anything in contracts / prod deploy paths.

Gate:

| Situation | Mode |
|---|---|
| First review, Low | Single reviewer (you) |
| First review, Medium or High | **Adversarial** (§4) |
| Re-review, delta is a tidy remediation of my prior findings and is neither high-risk class nor large | Single reviewer, delta-focused |
| Re-review, delta touches a high-risk class, OR is large relative to the original (roughly >40% of the original diff, or new files / new behaviour beyond what was asked) | **Adversarial** on the delta |

If Robin passes `--single` or `--adversarial`, that overrides the gate; say so.

## 3. What the review covers (both modes)

- **Code review:** correctness, reliability, security, tests, docs and naming.
- **Repo rules:** follow `workflow/commands/review-pull-request.md` and
  `workflow/commands/review-changes.md` from `SentientDogs/just-agents`
  (sibling checkout; if the local clone is behind, read them with
  `git -C just-agents show origin/main:<path>` after `git fetch`). **Skip**
  review-pull-request.md §1 "Claim lock", §2 "Choose two reviewer families"
  and §5 "Submit the GitHub review, then release the lease"; skip
  review-changes.md §5 "Output: remediation plan" and §6 "Linear
  integration". Use review-changes.md §1 (context) and §3 (dimensions:
  Security, Liveness, Testability, Test coverage, Best practice, Modern
  standards).
- **Repo overlays:** the repo's own `AGENTS.md` / rules-of-the-road and ADRs.
  ADRs are binding: flag drift between code and docs, and between documents
  inside the PR. For curator / market-queue changes also apply the
  `rotd-review-curator-changes` / `rotd-review-market-queue-changes` skills'
  rule sets, chat-only (do not let them post).
- **flip-oracle market extras:** apply the ME-* rules in
  `docs/market-extras-rules-of-the-road.md` whenever the PR touches market
  extras, namespacing, `isOnChainExtra`, `provider#` keys, participant slot
  keys or related docs. ME-6 and ME-11 are BLOCK rules. Main uses participant
  slot keys `slot0` / `slot1`.
- **Comments:** read ALL conversation comments, inline review threads and bot
  findings (Cursor Bugbot, CodeRabbit, GitHub Advanced Security, CI bots). For
  each: valid / addressed / false positive, with the evidence. On re-review,
  mark which are new since my last review and whether my own prior findings
  were addressed.
- **Drift check:** run `just-agents/workflow/skills/check-drift/scripts/check-drift.sh`
  from the repo under review (it reports `sibling_root`, `found`, `missing`,
  `ok=`). Then apply the skill's two checks: (a) repo ownership — is this
  change in the right repo, does it break a contract owned by another repo
  (`references/repo-map.md`); (b) binding docs — are the ADRs, rules and
  specs the change touches updated in the same PR. If the script cannot run
  (missing locally, no siblings), do both checks by reading the repos and
  say so in "Not verified".

## 4. Adversarial mode

Launch **two reviewer subagents in one message** so they run in parallel and
cannot see each other. Use the session's default model for both (never
`haiku` for a reviewer). Each brief carries: PR URL, repo path, base and head
SHA, the exact diff range (`<base>...<head>`, or on re-review
`<my-last-reviewed-sha>...<head>` with the original range as context), spec /
plan / Linear links from the PR body, the rules in §3 inlined (not pointed
at), and the return contract below.

- **Reviewer A — break it.** Adversary. Dimensions: Security, Liveness,
  Test coverage, Testability. Hunt for: wrong-path failures, unchecked
  states, partial writes, retries that double-apply, cursor / ordering
  inversions, money or resolution paths that can diverge, tests that pass for
  the wrong reason. Must try to construct a concrete failing input or state
  for every finding.
- **Reviewer B — rules and drift.** Dimensions: Best practice, Modern
  standards, plus ADR / rules-of-the-road / ME-* conformance, docs-vs-code
  drift, naming, repo ownership and binding-docs (the check-drift checks).
  Must cite the rule id or doc section for every finding.

Return contract for each (inline it in the brief):

> Return under 500 words: a findings table (ID, Severity High/Medium/Low,
> Dimension, Location as path:line, Finding, Rule/invariant cited), then
> "Checked and clear", then "Could not determine". Quote at most 10 lines of
> code. Do not paste diffs, files or logs. Do not post anything to GitHub.

**Consensus** (from review-pull-request.md §4): High by either → Blocking.
Medium by both → Blocking. Medium by one with a citation that the other did
not refute → Blocking. Medium by one without citation → Non-blocking. Low →
Non-blocking. A refutation needs a conflicting invariant / spec citation, not
an opinion. Before accepting any Blocking item, verify it yourself with a
targeted read; drop or downgrade with a one-line reason if it does not hold.
Merge the two tables into one, de-duplicated, and map Blocking → Critical/High
and Non-blocking → Medium/Low in Part A.

## 5. Single-reviewer mode

You do the review. Delegate only mechanical gathering (haiku): comment pulls,
file lists, line counts, grep sweeps for callers of changed symbols. On a
re-review, read the delta diff fully; skim the original only to confirm the
remediation matches what was asked.

## 6. Output, in this order

### Part A: the full review

- **PR facts:** full head SHA, author, state, base or stacking, my review
  state (first review / re-review since `<sha>` at `<time>`), and
  **Review mode:** single or adversarial, with the gate reason (complexity
  rating and the signals that drove it).
- **Intent:** what the PR does and why, short paragraph or a few bullets.
- **Comments checked:** what was read, what is new since my last review, and
  whether each item was addressed.
- **Findings:** table with ID, Severity (Critical / High / Medium / Low),
  Dimension, Location (permalink), Finding, Rule. In adversarial mode add a
  column `Source` (A / B / both / orchestrator).
- **Drift check:** ownership result, binding-docs result, drift found.
- **Checked and clear:** what was verified and found fine.
- **Verdict:** approve, approve after fixes, or request changes, one-line
  reason. Do not post it.
- **Not verified:** anything skipped or unconfirmed (including "check-drift
  script did not run" and any subagent claim you could not confirm).

### Part B: Medium+ findings, humanised

Plain numbered list, one paragraph per point: what is wrong, why it matters,
what to change. If none: "No Medium+ findings".

Then stop. Posting, approving, requesting changes, Linear writes and
remediation plans happen only on Robin's explicit instruction afterwards.
