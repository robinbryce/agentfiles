# wif — design record

Status: building (2026-10-21). Glossary: [CONTEXT.md](./CONTEXT.md).
Decisions below were settled in a grill-with-docs session; routine defaults are
listed so they can be changed deliberately rather than rediscovered.

## Decisions (settled)

| # | Decision | Chosen | Rejected |
|---|----------|--------|----------|
| 1 | Ledger home | `${CLAUDE_CONFIG_DIR}/wif/<scope>/` — account separation *is* the config-dir split ([ADR-0001](./docs/adr/0001-ledger-lives-in-account-config-dir.md)) | `<scope-root>/.wif/` (no root for personal scope); inside agentfiles (public repo, ephemeral state) |
| 2 | Stream identity | herdr task name, 1:1 with container; optional `parent` groups siblings; plain-repo work is `<repo>--<branch>`; memory-only dirs are *unbound memory*, never auto-streams | issue/plan as stream; task-only |
| 3 | Stream status | `active \| parked \| blocked \| landed \| closed`; scan may *propose* landed/closed, only Robin sets parked | plan vocabulary; open/closed |
| 4 | Session state | one JSON file per session id; stream file holds only durable state; handoff folds session into stream | inline in stream file; no intent ring |
| 5 | Intent capture | inferred by default: hooks record prompt/outcome first lines mechanically, the model records an `intent` when a prompt starts new work; `wif mark` is the override | explicit-only; prompt-type classifier hook (deferred) |
| 6 | Hook install | permanent in both accounts' `settings.json` via `wif install` (diff first); hooks no-op fast when no Backing resolves | skill-frontmatter hooks (session-only); per-task settings |
| 7 | Account/scope mismatch | warn and record nothing; a Ledger write never crosses accounts | hard refuse; record anyway |
| 8 | Dashboard surface | terminal (`/wif` dynamic injection) + statusline; artifact deferred to phase 4 | artifact first |

## Routine defaults (changeable)

- Auto-bind: a session binds to a Stream automatically only when cwd is under a
  herdr container; plain-repo Streams bind only once created by `wif start`.
  Keeps the Ledger free of noise from `$HOME` or throwaway sessions.
- Scan never creates Stream files. Containers without one are shown as
  *untracked* with age/dirty/PR facts; `wif adopt` (or the first prompt in the
  container) creates the file.
- Intent ring length 10. Stream file cap 120 lines (over-cap is a dashboard flag).
- Stale: no git activity, no session, for 14 days → flag `stale` (not a status).
- Landed proposal: every PR for the task MERGED and no dirty/unpushed work.
- Rotation: at `context_window.used_percentage >= 60` the tick / dashboard says
  "hand off now"; the number comes from the statusline dump, not a guess.
- PR lookups (`gh`) are opt-in (`--prs`) and cached 6h; git facts always.
- Loop: `/loop /wif tick`, self-paced; a tick prints only changed rows.
- Account map: `.claude-justgames` → justgames; `.claude-personal`, `.claude`
  → personal + forestrie. Override with `WIF_ACCOUNT_SCOPES="a b"`.
- Scope roots: justgames `~/Dev/justgames/code`, forestrie
  `~/Dev/personal/forestrie`, personal `~/Dev/personal`. Override `WIF_ROOT_<SCOPE>`.

## Phases

1. Ledger formats, `wif` CLI (`scan`, `show`, `adopt`, `mark`, `ctx`), `/wif` skill. ✔ this build
2. Hooks + statusline + `wif install` into both accounts. ✔ this build
3. `tick` under `/loop`, rotation, `handoff` protocol. ✔ this build (protocol in references/)
4. Evals run with/without skill; optional artifact dashboard. ◻ later

## Observed vs documented (2026-10-21, Claude Code 2.1.267)

- `UserPromptSubmit` delivers the prompt as `prompt`, not the documented
  `prompt_text`; the hook reads both. Re-check on upgrades.
- A dynamic `` !`cmd` `` line in SKILL.md aborts the entire skill when the
  shell permission check fails (seen headless). The dashboard is therefore an
  instructed first step, not an injection.
- `allowed-tools` grants are per-turn and do not apply in `-p` default mode;
  interactive sessions under Robin's autoMode are the real target.

## Sources

Anthropic: [long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents),
[context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents),
[skills reference](https://code.claude.com/docs/en/skills), [hooks](https://code.claude.com/docs/en/hooks),
[statusline](https://code.claude.com/docs/en/statusline), [scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks).
Community: [beads](https://github.com/steveyegge/beads) (`ready`, discovered-from),
[get-shit-done](https://github.com/gsd-build/get-shit-done) (derived STATE + validate),
[HumanLayer ACE](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md) (four-field compaction),
[handoff](https://github.com/bugiiiii11/handoff) (120-line cap, rotate at 60%),
[ccstatusline](https://github.com/sirmalloc/ccstatusline).
