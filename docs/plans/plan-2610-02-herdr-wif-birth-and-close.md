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

### Slice C1 — `wif adopt` finishes the tangent (agentfiles)

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
   form: `herdr-task <task> <collection|repos> -p <parent> -g "<text>"`, and
   only the `wif adopt <task>` line when the container already exists. The
   `wif note --done` line goes away because adopt now does it.
4. Tests: adopt clears the as= note and prints it; adopt without `-p` inherits
   the parent; Handoff seeded once and never clobbered; recommend emits one
   line; existing-container and already-a-stream branches unchanged.
5. Docs: SKILL.md §3 (`last → task:` block), DESIGN.md "Tangent → task name"
   ruling, `references/dashboard.md`, `references/stream-format.md` (adopt
   removes the note; Handoff may be seeded).

### Slice A — `herdr-task` births the stream and says what to do next (dotfiles)

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

### Slice B — closeout closes the stream (dotfiles)

Files: `bin/herdr-task-done.sh`, `bin/herdr-task-force-clean.sh`.

1. In herdr-task-done, after the workspace step and only when the task dir was
   actually removed (nothing kept) or `--workspace-only` was passed by
   force-clean: `wif mark --stream "$TASK" -s closed` with cwd = `$ROOT`.
   "no stream" and "already closed" are notes, not failures; `--dry-run`
   prints `would close stream`. Honour `--no-wif`.
2. force-clean needs no change beyond passing `--no-wif` through; it already
   execs task-done `--workspace-only`.
3. Verify with the Slice A throwaway task: stream file moves to `archive/`,
   `wif show` loses the `backing missing` line for it.

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
