---
paths: ["**/.worktrees-herdr/**"]
---
# herdr session handoff offers

**When this fires:** the working directory is under a
`*/.worktrees-herdr/<task>/` workspace AND the session reaches a **clean
handoff point** — a stream/phase/issue-set is delivered, all PRs are merged
or explicitly parked, and no work is in flight. Do not fire mid-stream or
after every merge; fire when the natural next step is "start fresh".

**What to do:** without being asked, close the status update with a
**"Ready to clear and hand off"** block containing:

1. **Memory first** — before offering, update the workspace's task-state
   memory (and index) so a fresh session inherits delivery state; say that
   this was done.
2. **A paste-ready kickoff prompt** for the next session — one short
   paragraph naming the next issue/stream, pointing at memory for state,
   and naming any skill/workflow to use (e.g. grill-with-docs).
3. **Absolute path references** for everything the next session needs:
   - the workspace memory index
     (`$CLAUDE_CONFIG_DIR/projects/<sanitized-cwd>/memory/MEMORY.md`)
   - any handoff/plan docs (worktree-absolute paths)
   - tracker links (Linear issue URLs)
   - 2–4 key code anchors (absolute paths) for the next task
4. **Stay-vs-new-workspace advice**: recommend `/clear` in place when the
   next task fits the current repo set (memory auto-loads only in the SAME
   workspace directory); recommend a new `herdr-task` only when the repo
   set or stream genuinely changes — and in that case include the one-line
   memory bridge for the new session:
   "Read `<old memory dir>/MEMORY.md` and the memories it indexes, then
   re-save what's still relevant to this workspace's own memory."

Keep the block compact — a table or short list, not an essay. The goal is
that Robin can `/clear` (or spawn a new workspace) and lose nothing.
