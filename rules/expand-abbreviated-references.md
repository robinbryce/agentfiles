# Expand abbreviated references

> **User preference — Robin (durable, all sessions/scopes/harnesses): every
> response expands each abbreviated reference it uses, at least once, in a
> table with one or two sentences of context per reference.**

Long sessions accrete codes — plan slices (`S3`), rulings (`R-32`), plan
commits (`c4`), open items (`P-18`), grill questions (`Q7`), PR numbers
(`#1616`), ADR sections (`ADR-0077 §7.3`), invariant codes (`IC-35`, `ME-11`,
`RR-3`), workflow or metric names used as shorthand. A reader cannot hold
them; Robin: "the context is impossible to follow otherwise."

## Rule

- Before sending, scan the draft for every token of those shapes.
- Add a **References** table — one row per distinct reference: the short
  form, then one or two sentences saying what it is and why it matters in
  this response. Fold it into a table the response already carries if one
  fits (a slice table, a status table); otherwise add it, at the top of a
  short response or the bottom of a long one.
- Prose may use the short form once the table is present.
- The table also carries **one row per active worktree with changes**, so
  Robin can point external diff tooling at the work while it is in progress
  (Robin, 2026-11-15). These rows are supplementary: every expansion row
  stays, and the worktree rows come last, after all of them.
  `/core:change-locations` prints just these rows. Active means a worktree this session, or a lane or
  agent it started, is working in or has worked in, whose changes are not yet
  merged: uncommitted changes, or a branch with commits not on its default
  branch. Leave out clean worktrees and branches already merged.
  - **Reference:** the repo name, plus the local clone's directory name when
    it differs (`flip-oracle`, `agentfiles (clone: af-main)`). When two rows
    would read the same, add the branch: `flip-oracle (eng-2922-curator-split)`.
  - **What it is:** the absolute path of the working directory, as plain
    code text (`/Users/robin/Dev/…/flip-oracle`), not a link, so it copies
    straight into a diff tool.
  - Check before sending, for each candidate path:
    `git -C <path> status --porcelain` and
    `git -C <path> rev-list --count origin/HEAD..HEAD`. A squash merge leaves
    a branch's commits ahead of the default branch, so for a branch with
    commits ahead, its PR's state decides whether it is merged.
- Never rely on an expansion given in an earlier response; each response
  stands alone.
- Repo docs, PR bodies and commit messages keep their own conventions
  (`core:pr-descriptions` already requires self-contained PR bodies); this
  rule is for chat-facing replies to Robin.
