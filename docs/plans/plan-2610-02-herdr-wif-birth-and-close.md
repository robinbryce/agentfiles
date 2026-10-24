---
id: plan-2610-02
status: active
created: 2026-10-24
refs:
  - plugins/core/skills/wif/DESIGN.md
  - plugins/core/skills/wif/docs/adr/0001-ledger-lives-in-account-config-dir.md
  - rules/herdr-session-handoff.md
  - ~/dotfiles/docs/README-herdr.md
---

# Plan plan-2610-02 — herdr-task and wif: one command to birth a stream, one to close it

**Status:** ACTIVE · **Created:** 2026-10-24

## Context

A new workstream today takes six manual steps: `herdr-task`, `wif adopt`,
`wif note --done` on the parent, switch tab, `just-claude`, paste the memory
bridge. Each seam is skippable, and the ledger shows it: on 2026-10-24 the
justgames dashboard had 13 streams, 59 untracked containers and 2 streams
whose backing was gone (`pr-1643-rotd-rr`, `cms-v45-market-listings`).

The pieces live in two repos:

- **dotfiles** (`master`): [bin/herdr-task.sh](https://github.com/robinbryce/dotfiles/blob/master/bin/herdr-task.sh),
  [bin/herdr-task-done.sh](https://github.com/robinbryce/dotfiles/blob/master/bin/herdr-task-done.sh),
  [bin/herdr-task-force-clean.sh](https://github.com/robinbryce/dotfiles/blob/master/bin/herdr-task-force-clean.sh),
  [bin/herdr-dispatch.sh](https://github.com/robinbryce/dotfiles/blob/master/bin/herdr-dispatch.sh),
  [docs/README-herdr.md](https://github.com/robinbryce/dotfiles/blob/master/docs/README-herdr.md).
  herdr-task deliberately starts no agent and knows nothing about wif.
- **agentfiles** (`main`): the `wif` skill under
  [plugins/core/skills/wif/](../../plugins/core/skills/wif/) — settled
  decisions in [DESIGN.md](../../plugins/core/skills/wif/DESIGN.md); the
  tangent → task recommendation in
  [wif/tangents.py](../../plugins/core/skills/wif/wif/tangents.py) (`recommend`);
  `adopt` in [wif/commands.py](../../plugins/core/skills/wif/wif/commands.py);
  the SessionStart hook in [wif/hooks.py](../../plugins/core/skills/wif/wif/hooks.py)
  already injects a stream's `## Handoff` section into a fresh session.
- **justgames scope env** (not a repo): `~/Dev/justgames/code/.envrc` defines
  the `HERDR_REPOS_*` collections; `HERDR_REPOS_BACKEND` is defined twice.

Settled wif decisions this plan must respect (DESIGN.md): the Ledger lives in
the account config dir; stream id == herdr task name; scan never creates
streams; only Robin sets `parked`; the tangent's `as=<task>` tag is the link
between a note and the container it becomes.

## Goal

Creating a stream is **one command** and closing it is **one command**, with
no container left untracked and no stream left orphaned:

```bash
herdr-task eng-2700-thing oracle -p eng-2654-mq-burst-fix -g "<what done looks like>"
#   -> worktrees for every repo, .envrc (as today); workspace with ONLY two
#      tabs: root and the first repo on the command line
#   -> wif stream created with goal + parent
#   -> the parent's [tangent as=eng-2700-thing] note cleared
#   -> ## Handoff seeded (tangent text, parent pointers, memory bridge) so the
#      first session's SessionStart hook injects it
#   -> footer: cd path, tab key, `just-claude`
herdr-task-done eng-2700-thing
#   -> worktrees, branch, task dir, workspace (as today) and the stream archived
```

## Approach

Slices are ordered so each is useful alone. C1 goes first because A's footer
and the dashboard text both describe what adopt now does.

### Slice C1 — `wif adopt` finishes the tangent (agentfiles) — MERGED 2026-10-24 (robinbryce/agentfiles#7, 938a716)

Files: `wif/commands.py` (`adopt`, `_tangent_tail`), `wif/tangents.py`,
`wif/ledger.py` (`Stream.section`), `tests/test_commands.py`.

1. **Clear the originating tangent.** On `adopt <task>`, search every
   non-archived stream in scope for a `[tangent as=<task>]` note. If found,
   remove it (same code path as `note --done`), print
   `cleared tangent on <parent>: <text>`, and default `parent` to that stream
   id when `-p` was not given. Exact `as=` match only; derived names are not
   searched (DESIGN.md: the CLI's derivation is a fallback, not an authority).
2. **Seed `## Handoff` on a new stream** when (a) a tangent was cleared or
   (b) `-p` names an existing stream. Content, ≤ 12 lines:
   - `objective:` the tangent text (or the goal);
   - `discovered from:` parent stream id, its `handoff_doc` if set, its
     container path;
   - the memory-bridge line from
     [rules/herdr-session-handoff.md](../../rules/herdr-session-handoff.md)
     pointing at the parent container's
     `$CLAUDE_CONFIG_DIR/projects/<sanitized>/memory/MEMORY.md` (wif's scan
     already computes memory-dir keys with the same sanitizer);
   - `re-invoke: /core:wif` .
   Never overwrite an existing non-empty `## Handoff` (re-adopt, re-open).
3. **Collapse the recommendation** in `tangents.recommend` to the one-command
   form, and only the `wif adopt <task>` line when the container already
   exists. The `wif note --done` line goes away because adopt now does it.
   *As built:* the form is `herdr-task <task> <collection|repos> && wif adopt
   <task> -g '<text>'` (single-quoted goal) rather than herdr-task flags, so the printed command is
   valid before Slice A lands; `-p` is omitted because adopt infers the parent
   from the cleared note. Slice A may switch the text to the flag form.
4. Tests: adopt clears the as= note and prints it; adopt without `-p` inherits
   the parent; Handoff seeded once and never clobbered; recommend emits one
   line; existing-container and already-a-stream branches unchanged.
5. Docs: SKILL.md §3 (`last → task:` block), DESIGN.md "Tangent → task name"
   ruling, `references/dashboard.md`, `references/stream-format.md` (adopt
   removes the note; Handoff may be seeded).

### Slice A — `herdr-task` births the stream and says what to do next (dotfiles) — IMPLEMENTED 2026-10-24 (draft PR robinbryce/dotfiles#1, branch `plan-2610-02-a`)

*As built:* verified offline against a stub `herdr` and a temp wif ledger
(all seven items below); the live herdr-session smoke in item 7 is still
to do by hand. Two extras landed with it: `git worktree add` is created
`--no-track` so a task branch never tracks `origin/main`, and a
pre-existing `herdr-dispatch` bug (`die()` inside `$(…)` only exited the
subshell, so a missing tab fell through to an empty submit) is fixed. The
wif recommendation keeps the `&&` form (not herdr-task flags); both
forms work once this slice lands.

File: `bin/herdr-task.sh`; docs: `docs/README-herdr.md` (herdr-task section
and the conventions table).

1. **Flags:** `-g|--goal <text>`, `-p|--parent <id>`, `--no-wif`,
   `--all-tabs`. Parsed in the existing option loop; usage text comes from
   the header comment, so extend the header.
2. **Tabs only for root and the first repo.** Robin never uses the other repo
   tabs. Worktrees and `SKILLS_PATH` still cover every repo; only the tab
   loop changes: iterate `"${ok_repos[0]}"` instead of `"${ok_repos[@]}"`
   (first repo in command-line order that got a worktree, so collection
   order matters and is documented). `--all-tabs` restores one tab per repo.
   On a re-run, tabs that already exist for later repos are reused and
   renumbered as today, never closed; `managed` still lists every repo so
   their labels keep the `<n>:` prefix. The header comment's "Produces" block
   and the README conventions table gain a row:
   "Tabs: root + first repo; `--all-tabs` for the rest".
3. **herdr-dispatch creates a missing tab on demand.** `ensure_agent` in
   `bin/herdr-dispatch.sh` dies with "no tab labelled <repo>" when
   `pane_for_repo` fails. With the tab change that is the normal case for
   every repo but the first, so instead: `herdr tab create --workspace $ws
   --cwd <TASK_DIR>/<repo> --label <repo> --no-focus`, renumber the label
   from `herdr tab list` the way herdr-task does (factor the numbering into a
   shared helper only if it stays under ~20 lines; otherwise duplicate and
   note it), then resolve the pane. The worktree must exist; a missing
   worktree still dies with the `herdr-task <task> <repo>` hint.
4. **Adopt after the tabs are built.** When `wif` is on PATH and `--no-wif`
   is absent: `wif adopt "$TASK" ${GOAL:+-g "$GOAL"} ${PARENT:+-p "$PARENT"}`,
   run with cwd = `$TASK_DIR` so the account/scope resolve from the container.
   Failure is a `note`, never fatal: the container is already correct and the
   first prompt still creates a bare stream. Skip adopt when the ledger scope
   is not served by this account (wif prints that itself; just relay).
5. **Next-steps footer** on stderr after the `done ->` line:
   ```
   next: prefix+<n> (tab <n>:<first repo>)   or: cd <TASK_DIR>/<first repo>
         just-claude                          # SKILLS_PATH -> --plugin-dir
         stream: <ledger path>                # when adopt ran
   ```
6. **Fresh base.** When `--base` is absent: `git -C "$main" fetch origin
   --quiet` (tolerate failure), then default BASE to `origin/<default>` where
   default comes from `refs/remotes/origin/HEAD` (fallback: current HEAD with
   a `note "branching from local HEAD, which is N behind origin"`). Record
   this as a conventions-table row; the old behaviour stays reachable via
   `--base HEAD`.
7. Verify: `shellcheck`, then a throwaway task on a small repo (`just-robin`
   has a short worktree list) inside the justgames herdr session, with and
   without `-g/-p`, and a re-run to confirm adopt is idempotent.

### Slice B — closeout completes from inside the session (dotfiles + agentfiles) — IMPLEMENTED 2026-10-24 (draft PRs robinbryce/dotfiles#2 + robinbryce/agentfiles#8)

*As built:* all of B1–B6 as specified; verified offline with the stub
`herdr` serving agents from a file (all six item-7 scenarios pass); the
live run from a real pane is still to do. One finding on the way: a plain
`( nohup … & )` leaves the forked subshell holding the caller's
stdout/stderr, so an agent's piped invocation blocked for the reaper's
whole wait — the reaper is now daemonised with perl's double fork + setsid
(fallback `exec nohup … &`) and the in-session run returns in 0s. The
process also `cd`s to the scope root before anything else, so it never sits
in a directory it may delete.

Files: `bin/herdr-task-done.sh`, `bin/herdr-task-force-clean.sh`,
`docs/README-herdr.md` (dotfiles); `plugins/core/skills/worktrees-closeout/SKILL.md`
(agentfiles).

**Problem (2026-10-24, `just-agents-1`).** A session cannot close itself out:
`git worktree remove` happily deletes the directory the session stands in
(exit 0, shell left with no cwd) and `herdr workspace close` kills the pane
running the command. An outside run cannot finish either: it sees "3 commits
ahead, no MERGED PR" and refuses, because the evidence that made it safe
(the commits were byte-identical to the head of open PR just-agents#35) lived
only in the session. The confidence is inside; the destruction must happen
outside. **Design: approve inside, reap outside.**

1. **B1 remote-reachability rule.** A worktree whose HEAD is reachable from
   any pushed remote branch (`git branch -r --contains <head>` after the
   fetch) is removable even with no MERGED PR: the content is on origin. An
   OPEN PR on the branch still blocks. This alone would have removed
   `just-agents-1`. Applies to detached HEADs too.
2. **B2 live-agent guard.** A worktree whose path is the cwd of a live herdr
   agent (`herdr agent list`) is kept with reason "live agent <name>", and
   the workspace is not closed while any live agent remains in the container.
   Removing a worktree under a running session breaks it; this is a new
   safety check, not overridable by `--approve`. `--force` (used by
   force-clean) still closes, with a warning naming the agents.
3. **B3 approval marker.** `herdr-task-done <task> --approve "<evidence>"`
   runs the discovery and, for every worktree kept *only* for the
   unmerged-commits class of reason, records `{repo: HEAD sha}` plus the
   evidence, session id and timestamp in `<task-dir>/.closeout.json`. It
   changes nothing else. A plain run then removes such a worktree when the
   marker's sha equals the current HEAD (a later commit re-blocks). Dirty
   trees, open PRs and live agents are never overridden. The marker is
   removed with the task dir (treated as generated).
4. **B4 detached final step.** When the run's own cwd is under the task dir
   (the in-session case), everything else is done now; the worktree hosting
   the session, the task dir, the stream close and the workspace close are
   handed to a detached reaper (`nohup` + `setsid` via perl, cwd = scope
   root) that polls `herdr agent list` until no agent remains in the
   container (timeout 2h), then re-runs `herdr-task-done <task> --reap`.
   Log: `~/.local/state/herdr-task/<task>.reap.log`. The in-session message
   ends with "exit this session; the rest is swept when it is gone".
5. **B5 stream close** (the original Slice B): `wif mark --stream <task>
   -s closed` from the scope root once the task dir is gone, or on
   `--workspace-only` from force-clean; "no stream" / "already closed" are
   notes; `--no-wif` skips; dry run says `would close stream`.
6. **B6 skill.** `worktrees-closeout` §0 gains the remote-reachability
   condition; §3 says: when the only blockers are unmerged commits with
   concrete evidence, run `herdr-task-done <task> --approve "<evidence>"` then
   `herdr-task-done <task>`; when inside the container expect the deferred
   message and tell Robin to exit the session. Live agents are reported, not
   fought.
7. Verify with the stub `herdr` (agents with a cwd under the container):
   remote-reachable branch removed with no marker; live agent keeps worktree
   and workspace from outside; `--approve` then plain run removes an
   unmerged-but-approved worktree and refuses after a new commit; in-session
   run defers and the reaper completes once the stub agent disappears;
   stream archived. Then the live smoke from a real pane.

*Follow-up, not in this slice:* `wif tick` sweeps containers that carry a
marker and have no live agent, so a forgotten approval still lands.

### Slice D — scope env and agent kickoff

1. `~/Dev/justgames/code/.envrc`: delete the first `HERDR_REPOS_BACKEND`
   (it duplicates `ORACLE`); keep the six-repo definition. Not a repo file,
   so this is a hand edit plus `direnv allow`.
2. **Stretch:** `wif kickoff [<task>]` prints the stream's `## Handoff`
   section (fallback: goal/next/position as a three-line prompt), and
   `herdr-task --dispatch <repo>` runs
   `herdr-dispatch "$TASK" <repo> --prompt "$(wif kickoff "$TASK")"` after
   the footer. Keeps herdr-task's "no agent by default" rule: dispatch is
   opt-in per run. Only if A and B land cleanly; otherwise drop.

### Slice E — one-off ledger hygiene (operational)

Not code. After A–C land: run `/core:worktrees-closeout` over the `stale`
untracked containers on the justgames dashboard, then `herdr-task-done` the
disposable ones (which now archives nothing, since they never had streams) and
`wif adopt <task> -s parked` the keepers. Target: untracked count under 10 and
`wif show` back within its 40-line budget.

## Verification

- agentfiles: `python3 -m unittest discover -s tests -t .` from the wif skill
  dir stays green with the new cases (89 today).
- dotfiles: `shellcheck bin/herdr-task*.sh`; the throwaway-task round trip
  (create with `-g/-p` and three repos → exactly two tabs, root and the
  first repo; stream exists with goal/parent, tangent cleared on the parent,
  Handoff seeded → `herdr-dispatch <task> <third-repo> --prompt x` creates
  that tab and starts the agent → `herdr-task-done` → stream archived,
  container gone, dashboard clean).
- Dashboard: a recorded tangent's `last → task:` block is one copy-pasteable
  command; after running it the candidate disappears without a third step.
- README-herdr and SKILL.md describe the same flow as the scripts print.

## Out of scope

- Auto-starting agents by default (herdr-task's settled rule).
- Scan creating or closing streams (DESIGN.md).
- Any change to where the Ledger lives or how sessions bind.
