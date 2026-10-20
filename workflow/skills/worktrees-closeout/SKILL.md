---
name: worktrees-closeout
description: Close out a workstream whose worktrees for one or more sibling repos are staged under a common container directory (e.g. <scope-root>/.worktrees-herdr/<task>/<repo>). Confirms per repo what has merged to the default branch (squash-merge aware, via GitHub PR state), assesses any residual local changes — dirty files, unpushed commits, stashes, non-repo files in the container — and says whether they are worth preserving, then removes every worktree, branch and container that is provably safe to remove and lists exactly what was kept and why. Use when the user says a workstream / task / branch set is complete and wants it confirmed and cleaned up, asks to close out, tear down, retire or tidy a set of worktrees, or asks what is still unmerged across a task's sibling repos.
allowed-tools: Bash(git *) Bash(gh *) Bash(herdr-task-done *) Bash(ls *) Bash(cat *) Bash(diff *) Read Grep Glob
---

# worktrees-closeout

```
/worktrees-closeout [<container-path> | <task-name>] [--keep-branches] [--dry-run]
```

- `container-path` — a directory whose immediate subdirectories are git
  worktrees of sibling repos. Default: derive from cwd — if cwd is inside
  `…/.worktrees-herdr/<task>/…` the container is `…/.worktrees-herdr/<task>`.
- `task-name` — shorthand for `<scope-root>/.worktrees-herdr/<task-name>`.
- `--keep-branches` — remove worktrees but never delete branches.
- `--dry-run` — do steps 1–3 only; report, change nothing.

The job has three parts, in order, and the first two are **read-only**:
**confirm** what merged, **assess** what is left, **clean up** what is safe.
Never skip to part 3.

## 0. Posture

- Destruction is gated on evidence, not on the user's belief that the work is
  done. "I think this is complete" is the hypothesis; parts 1–2 test it.
- Squash merges mean `git branch -d` / `--merged` are useless here (git cannot
  see a squashed branch as merged, and `-D` protects nothing). The merge
  oracle is GitHub: a MERGED PR whose `headRefOid` is the worktree's HEAD, or a
  patch-identity check against the default branch for anything beyond that.
- Work is removable only when **all** hold: clean tree, no OPEN PR has the
  branch as head, and HEAD is level with `origin/<default>` **or** is the
  `headRefOid` of a MERGED PR **or** every extra commit is patch-identical to
  something already on `origin/<default>`. Anything else is kept and reported.
- One context, all repos ([multi-repo-fanout](../../rules/multi-repo-fanout.md)):
  cross-repo facts (a PR in repo A that supersedes a branch in repo B) are only
  visible with every sibling loaded. Do not fan out the assessment.
- Every path, PR, commit and ticket in the report is a clickable link with an
  absolute path ([clickable-references](../../rules/clickable-references.md)).

## 1. Inventory (read-only)

Resolve the container, then for every entry in it:

```bash
ls -la "$C"                                              # non-repo files too (.envrc, notes, csvs)
for wt in "$C"/*/; do
  git -C "$wt" rev-parse --path-format=absolute --git-common-dir   # owning main checkout, or not-a-repo
  git -C "$wt" branch --show-current ; git -C "$wt" rev-parse HEAD
  git -C "$wt" status --porcelain --branch                         # dirty files + upstream ahead/behind
  git -C "$wt" stash list                                          # stashes are per-repo; note any
done
```

Then, per repo, from the **main checkout** (`dirname` of the common dir):

```bash
git -C "$main" fetch origin --quiet
base=$(gh -R "$(git -C "$main" remote get-url origin)" repo view --json defaultBranchRef --jq .defaultBranchRef.name)
git -C "$wt" rev-list --left-right --count "origin/$base...HEAD"   # behind<TAB>ahead
git -C "$wt" log --oneline "origin/$base..HEAD"                    # the candidate unmerged commits
git -C "$wt" log --oneline '@{u}..HEAD' 2>/dev/null               # unpushed
gh pr list -R <owner/repo> --head "$branch" --state all --json number,state,title,url,headRefOid,mergedAt,mergeCommit
git ls-remote --heads origin "$branch"                            # does the remote branch still exist
```

Record for each worktree: repo, branch, HEAD, dirty files, stashes, unpushed
commits, ahead/behind, PRs (number, state, headRefOid), remote branch present.
Also list every non-directory / non-repo entry in the container.

## 2. Confirm and assess (read-only)

**Merged verdict**, one of:

- **merged** — HEAD == `headRefOid` of a MERGED PR, or ahead == 0.
- **merged + trailing commits** — a MERGED PR exists but HEAD moved past it.
  For each extra commit run `git cherry -v origin/$base HEAD`; a `-` line is
  already on main by patch identity, a `+` line is genuinely unmerged. Diff
  the `+` ones (`git show --stat`) and judge.
- **open** — an OPEN PR has this branch as head. Not closeable; say so and
  stop for that repo (optionally report the PR's review / CI state).
- **never raised** — ahead > 0 with no PR at all. Treat the commits as
  residual local changes (below).
- **detached / foreign** — detached HEAD or branch not named for the task.
  Report; do not infer intent.

**Residual local changes**, for every dirty file, stash, unpushed or unmerged
commit, and non-repo container file, classify and recommend:

| Class | Typical examples | Recommendation |
|-------|------------------|----------------|
| Generated / reproducible | gitignored codegen, build output, lockfile churn from a tool bump | discard |
| Scratch | one-off scripts, exploratory diffs, `.envrc` written by the task tool | discard; quote anything that reads like a finding |
| Docs / notes with unique content | plan or handoff edits, ADR drafts, session notes not in any git ref | **preserve** — commit to a salvage branch and push, or copy into the scope's notes repo; name the destination |
| Code not in any PR | a fix started after the PR merged, a follow-up never raised | **preserve** — push to a named branch and say whether it deserves a PR or a ticket |
| Superseded | patch-identical to something merged, or a design the merged PR replaced | discard, citing the superseding PR |

"Worth preserving" means: content that exists in **no git ref anywhere**
(check `git log --all -S` / `git branch -a --contains` before claiming that)
*and* that a future reader would want. Err toward preserving docs; err toward
discarding generated output. State the salvage action precisely enough to run.

Also note, without acting on them: whether the workstream's ticket(s) are
closed (follow the active scope's tracker rule), and whether the main checkout
of each repo is on `origin/<default>` and clean (a fast-forward is a cheap
courtesy, but only when it is on the default branch with a clean tree).

Present parts 1–2 as one table, one row per worktree plus one for container
files, before touching anything. If `--dry-run`, stop here.

## 3. Clean up (as far as is provably safe)

Order of preference:

1. **herdr task** (container is `…/.worktrees-herdr/<task>`): run
   `herdr-task-done <task> --dry-run`, compare its kept/removed list with your
   own verdicts — they must agree; if they do not, say which is wrong and why
   before proceeding — then `herdr-task-done <task>` (add `--keep-branches`
   if asked). It removes worktrees, deletes task branches under the same safety
   rule as §0, drops the empty task dir, and closes the herdr workspace.
2. **Plain container**: for each worktree that passed §0, from its main checkout
   `git worktree remove "$wt"`, `git branch -D "$branch"` (skip with
   `--keep-branches`), `git worktree prune`; then `rmdir` the container when it
   is empty.

Never pass `--force` to any of the above on the user's behalf. A worktree that
fails the rule is left in place and listed under **kept**; removing it is the
user's call after they have read the assessment.

Remote branches: GitHub normally deletes the head branch on merge. If
`git ls-remote` still shows one for a repo whose verdict is **merged**, delete it
with `git push origin --delete "$branch"` — its content is on the default
branch and in the PR. Leave every other remote branch alone.

Salvage actions recommended in §2 are **not** executed automatically: list them
as the next steps unless the user has already said to preserve / discard.

## 4. Report

Lead with the verdict: closed out, or closed out except N kept. Then:

- one table: repo | branch | PR(s) with state | merged verdict | residual |
  action taken | kept because
- salvage steps still to run, each as a runnable command
- anything the user must decide (an open PR, a never-raised branch, a kept
  worktree)
- the absolute path of every worktree touched and of the container

Keep the merged-evidence concrete: PR number + `headRefOid`, or the
`git cherry` output, never "looks merged".
