# Handoff protocol ("land the plane")

Trigger: a clean completion point (per
[herdr-session-handoff](../../../rules/herdr-session-handoff.md)), or `wif ctx`
reporting ≥ 60% context, or Robin saying they are stopping. Never mid-step.

Order matters; each step is cheap on its own.

1. **Reconcile before trusting.** `wif scan --quiet` then `wif show --brief`.
   If the stream file's `next`/`position` disagree with what you just did,
   the file is stale — fix it, do not merge into it blindly.
2. **Rewrite `## Now`** (≤ 20 lines) with the ACE four fields: goal, approach,
   done (verified only — tests, merged PRs, deployed where), failing (the
   current blocker or open question, with the exact error text if short).
   Shrink or hold; drop anything a fresh session can re-derive from git.
3. **Set the pointers.** `wif mark -n "<next action>" -p "<slice n/m — what>"`
   and, if it changed, `-s blocked|landed|active`.
4. **Fold the session.** Promote any ring intent that is still open into a
   `[followup]` note; delete notes that were acted on. Tangents stay until
   promoted or rejected.
5. **Durable text goes to the convention, not the Ledger.** In order of
   preference: the plan dir's `handoff.md` → `/save-status` → auto memory
   (`MEMORY.md` index + topic file). Set `handoff_doc` to the absolute path.
   The stream file keeps only the pointers and the kickoff.
6. **Write `## Handoff`** — the paste-ready kickoff, ≤ 25 lines: objective;
   bootstrap order (handoff doc first, then 2–4 docs, then files, absolute
   paths); state (branch, worktree, SHA, open PR, deployed where); locked
   decisions; what not to touch and the verification command; which skill to
   re-invoke. The SessionStart hook injects this verbatim after `/clear`.
7. **Print** the kickoff and the stay-vs-new-workspace advice: `/clear` in
   place when the next work fits this container (the hook carries the goal
   forward); a new `herdr-task` only when the repo set changes, with the
   memory-bridge line from the herdr rule.
8. `wif mark -s landed` only when every PR is merged or explicitly parked and
   nothing is dirty or unpushed (the `landed?` flag is the evidence).
