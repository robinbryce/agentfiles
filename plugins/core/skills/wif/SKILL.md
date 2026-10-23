---
name: wif
description: Work-in-flight tracker for Robin's many concurrent workstreams across herdr worktrees and Claude profiles (justgames, personal, forestrie, home). Answers "which stream am I in, what is this session for, what was the last prompt for, where does it sit in the stream, and what else is open" from an on-disk Ledger kept per account and scope. Use when Robin asks where things stand, what is in flight, what the current goal or next step is, to set a session goal, to note a followup / tangent / reminder mid-stream, to hand off or clear a session, to adopt or park a worktree, or runs it under /loop as a tick. Also use when a session starts in a herdr container and the goal is unclear.
argument-hint: "[status|start|mark|note|tangent|remind|scan|tick|handoff|adopt|install|where]"
allowed-tools: Bash(wif *) Bash(*/skills/wif/scripts/wif *) Bash(git *) Bash(gh pr *) Bash(ls *) Bash(cat *) Read Grep Glob
---

# wif — work in flight

```
/core:wif [status]                 dashboard (default)
/core:wif start "<session goal>"   bind this session to the stream here; set its goal
/core:wif mark ...                 override an inferred goal/intent; set position/next/status
/core:wif note|tangent|remind ...  capture a side thought without acting on it
/core:wif scan [--prs]             rebuild the index from disk (gh lookups opt-in, cached 6h)
/core:wif tick                     loop body: scan, print only what changed, check rotation
/core:wif handoff                  land the plane: fold session → stream, write kickoff, advise /clear
/core:wif adopt <task> [-s parked] create a stream for an untracked container
/core:wif where                    what account/scope/stream this directory resolves to
/core:wif install [--apply]        merge hooks + statusline into every profile's settings.json
```

Glossary: [CONTEXT.md](./CONTEXT.md). Decisions: [DESIGN.md](./DESIGN.md).
Formats: [references/stream-format.md](./references/stream-format.md).
Dashboard spec: [references/dashboard.md](./references/dashboard.md).
Handoff protocol: [references/handoff-protocol.md](./references/handoff-protocol.md).

CLI: `wif` (linked into `~/.local/bin` by install; entry point
`${CLAUDE_SKILL_DIR}/scripts/wif`, code in `wif/`,
Python 3.9+ stdlib only). `wif help` lists every subcommand and its flags.

## 0. First action, every invocation

Run `wif show` (fallback: the absolute script path above) and print its output
verbatim as the first thing in your reply. Not a dynamic `!` injection on
purpose: a denied shell command would abort the whole skill instead of just
the dashboard.

## 1. Posture

- **The Ledger is the memory; your context is the cache.** Never answer "where
  are we" from recollection. Read the dashboard above (or run `wif show`).
- **Infer first, ask never.** Session goal and prompt intent are inferred;
  Robin corrects with `mark`. Do not ask Robin to state a goal.
- **One Account, one Scope.** If the dashboard says the scope is not served
  by this account, say so in one line and record nothing. Never touch another
  config dir's Ledger.
- **Reuse conventions, don't invent.** Durable handoff text goes where it
  already goes: a plan dir's `handoff.md`, `/save-status`, auto memory. The
  stream file *points* at those; it does not duplicate them.
- **Scan and show never mutate streams.** Scan rebuilds `index.json`, prunes
  old session files and proposes flags (`stale`, `dirty`, `unpushed`,
  `unpublished`, `no-remote`, `landed?`, `over-cap`, `bad-status`). Streams
  are written only by `mark`, `adopt`, `note` and the hook on the first
  prompt in a container (no other hook event creates one). A closed
  (archived) stream is never recreated by hooks; `wif adopt` re-opens it.
- **Keep it short.** Dashboard ≤ 40 lines, stream file ≤ 120 lines, kickoff ≤ 25.

## 2. Inference duties (every session in a stream, with or without /core:wif)

The hooks inject one `[wif]` line per prompt. On seeing it:

- **Session goal unset** and this prompt states what the session is for →
  `wif mark -g "<one line>" --session ${CLAUDE_SESSION_ID}`. Do it silently
  as part of the turn; do not announce it.
- **This prompt starts a new unit of work** (new question, new slice, new
  file set) → `wif mark -i "<one line>" --session ${CLAUDE_SESSION_ID}`.
  Follow-ups ("yes", "fix that", "and the tests") inherit; do nothing.
- **A slice boundary is reached** (tests green, PR opened, decision locked) →
  `wif mark -p "<slice n/m — what>" -n "<next action>"`.
- Robin says "remind me", "followup", "tangent", "note that", "park that
  thought" → the matching `wif note|tangent|remind` command, verbatim text.
- A note has been acted on (followup became the intent, reminder fired,
  tangent promoted or rejected) → `wif note --done "<substring>"`.

## 3. `/core:wif` and `/core:wif status`

Print nothing beyond the dashboard unless something needs Robin's decision:
due reminders, `landed?` proposals, `over-cap` streams, or a stream without a
goal. For each, one line with the command that resolves it.

## 4. `/core:wif start "<goal>"`

`wif mark -g "<goal>" --session ${CLAUDE_SESSION_ID}` (creates the stream if
the cwd is a herdr container). In a plain repo checkout, first `wif adopt .`.
If the goal names a tangent recorded on another stream, say which one and
suggest `-p <parent>` so the two stay linked.

## 5. `/core:wif tick` (for `/loop /core:wif tick`, self-paced)

1. `wif scan --quiet` (add `--prs` at most once per 6h; the cache enforces it).
2. `wif show --changes` — print exactly that output, nothing more.
3. `wif ctx` — if it says ROTATE, run the handoff protocol (§6) now, then
   tell Robin to `/clear`; do not keep ticking in a session past 60%.
4. Schedule the next wake: 20–30 min idle; sooner only if a due reminder or a
   CI/PR state you are explicitly waiting on changes faster. Mark `noop` when
   the last line was `no changes` (a due reminder in the header does not make
   a tick non-noop; it repeats until acted on). The first tick only records a
   baseline.

## 6. `/core:wif handoff`

Follow [references/handoff-protocol.md](./references/handoff-protocol.md).
Summary: update `## Now` (goal / approach / done / failing, ≤ 20 lines) and
`next`/`position`; write the kickoff into `## Handoff` (≤ 25 lines); write
durable facts to the existing convention and set `handoff_doc`; update auto
memory; print the kickoff and the stay-vs-new-workspace advice from
[herdr-session-handoff](../../../../rules/herdr-session-handoff.md). Then
`wif mark -s landed` only when the `landed?` flag shows (every PR merged,
nothing dirty or unpushed, remote ref verifiable) or every PR is explicitly
parked.

## 7. `/core:wif adopt`, `/core:wif install`, `/core:wif where`

Pass-throughs to the CLI. `install` without `--apply` is a dry run that
prints the settings diff; run it that way first and show Robin the diff.
Run `install` from the agentfiles checkout
(`~/agentfiles/plugins/core/skills/wif/scripts/wif install`), never from the
plugin cache: the cache path changes on every plugin update.
Removing a worktree is `/core:worktrees-closeout`'s job. Close its stream
with `wif mark -s closed` inside the container, or from anywhere with
`wif mark --stream <id> [--scope S] -s closed` (also the fix for a
`backing missing` stream). Either moves the stream file to `archive/`, and
hooks stop recording there until `wif adopt`.
