# wif — design record

Status: building (2026-10-21). Glossary: [CONTEXT.md](./CONTEXT.md).
Decisions below were settled in a grill-with-docs session; routine defaults are
listed so they can be changed deliberately rather than rediscovered.

## Decisions (settled)

| # | Decision | Chosen | Rejected |
|---|----------|--------|----------|
| 1 | Ledger home | `${CLAUDE_CONFIG_DIR}/wif/<scope>/` — account separation *is* the config-dir split ([ADR-0001](./docs/adr/0001-ledger-lives-in-account-config-dir.md)) | `<scope-root>/.wif/` (no root for personal scope); inside agentfiles (public repo, ephemeral state) |
| 2 | Stream identity | herdr task name, 1:1 with container; optional `parent` groups siblings; plain-repo work is `<repo>--<branch>`; memory-only dirs are *unbound memory*, never auto-streams | issue/plan as stream; task-only |
| 3 | Stream status | `active \| parked \| blocked \| landed \| closed`; scan may *propose* `landed?`, nothing proposes closed, only Robin sets parked | plan vocabulary; open/closed |
| 4 | Session state | one JSON file per session id; stream file holds only durable state; handoff folds session into stream | inline in stream file; no intent ring |
| 5 | Intent capture | inferred by default: hooks record prompt/outcome first lines mechanically, the model records an `intent` when a prompt starts new work; `wif mark` is the override | explicit-only; prompt-type classifier hook (deferred) |
| 6 | Hook install | permanent in every profile's `settings.json` via `wif install` (diff first); hooks no-op fast when no Backing resolves | skill-frontmatter hooks (session-only); per-task settings |
| 7 | Account/scope mismatch | warn and record nothing; a Ledger write never crosses accounts | hard refuse; record anyway |
| 8 | Dashboard surface | terminal (`wif show` as the skill's instructed first step) + statusline; artifact deferred to phase 4 | artifact first; dynamic `!` injection (aborts the skill when denied) |

## Routine defaults (changeable)

- Auto-bind: a session binds to a Stream automatically only when cwd is under a
  herdr container; plain-repo Streams bind only once created by `wif adopt .`.
  Keeps the Ledger free of noise from `$HOME` or throwaway sessions. Only the
  first *prompt* creates the stream file; SessionStart/Stop/SessionEnd in a
  container with no stream record nothing.
- Scan never creates Stream files. Containers without one are shown as
  *untracked* with age/dirty/PR facts; `wif adopt` (or the first prompt in the
  container) creates the file. Scan may propose `landed?`; nothing proposes
  `closed`.
- Closed streams (archived) are not recorded by hooks: a session that keeps
  running in a closed container writes nothing until `wif adopt` re-opens it.
  (Ruling 2026-10-21, after review found the hook resurrecting closed streams.)
- Intent ring length 10. Stream file cap 120 lines (over-cap is a dashboard flag).
- Stale: no commit, session or stream update for 14 days and nothing dirty →
  flag `stale` (not a status).
- Landed proposal: every PR for the task MERGED, nothing dirty or unpushed, and
  a verifiable remote ref (upstream or `origin/<branch>`) for every repo. A
  branch that was never pushed (`unpublished`) can never be proposed landed.
- Session files: ended sessions older than 30 days and orphaned ctx sidecars
  are pruned by scan. Tunables (`WIF_RING`, `WIF_STREAM_CAP`, `WIF_STALE_DAYS`,
  `WIF_ROTATE_PCT`, `WIF_PR_TTL`, `WIF_SESSION_KEEP_DAYS`, `WIF_BUDGET_LINES`)
  are environment variables read by `wif/config.py` at call time.
- Rotation: at `context_window.used_percentage >= 60` `wif ctx` prints ROTATE
  and the statusline shows `· ROTATE`; the number comes from the statusline
  dump, not a guess. The tick (SKILL §5) acts on `wif ctx`.
- Dates: every calendar date (`created`, `updated`, note stamps, reminder due,
  due comparison) is the *local* date; timestamps inside session JSON are UTC.
- Concurrency: writes to a stream file happen under an advisory `flock` on
  `<stream>.md.lock` (hooks and commands); readers never lock. All file writes
  go through a private temp file + rename.
- Memory-dir keys use Claude Code's sanitizer: every non-alphanumeric
  character becomes `-` (observed in the installed binary, not documented).
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
- Only 20 of 114 real worktree repos have an upstream or `origin/<branch>`;
  herdr task branches are usually never pushed, so `unpushed` is mostly
  unknowable and `unpublished` is the common state.
- Adversarial review 2026-10-21 (two blind reviewers) fixed: SessionStart
  silent failure on foreign session files, compact overwriting the session
  goal, install truncating settings.json, awk `-v` escape mangling, spaces in
  task names, submodule ids, gh failures cached as empty, memory-dir binding
  by longest task prefix, `--changes` semantics, line budget, off-by-one caps.

## Implementation and tests (2026-10-21, v0.2)

The first cut was bash + jq + two Python scripts; the adversarial review
found most of its defects in shell-specific corners (error traps, `awk -v`
escapes, `ls` parsing, jq truthiness). It was replaced by a stdlib-only Python
package, `wif/`, behind the same `scripts/wif` entry point, so the installed
settings.json commands did not change. No jq, no third-party modules.

- `wif/proc.py` is the single subprocess seam; tests patch `wif.proc.run` to
  fake `gh` and `herdr` while real `git` runs in temp repos.
- `tests/` is plain `unittest`: `tests/base.py` gives every case an isolated
  `HOME` and `CLAUDE_CONFIG_DIR` inside a `TemporaryDirectory`, a fully
  replaced environment (`mock.patch.dict(os.environ, ..., clear=True)`, with
  `GIT_CONFIG_GLOBAL=/dev/null` so the developer's git config cannot leak),
  `contextlib.chdir` for cwd, and helpers that build git repos, bare remotes,
  herdr containers and auto-memory dirs. Paths are compared after
  `Path.resolve()` because macOS temp dirs live under a symlink.
- The review reproductions are pinned as tests (foreign session file at
  SessionStart, compact vs clear goal carry, closed-stream resurrection,
  escape round-trips, spaces in task names, gh failure caching, memory
  prefix binding, `--changes` semantics, settings merge/remove).

- `tests/test_meta.py` guards the harness itself: no test class may shadow a
  `TestCase` method (a helper named `run` once silently disabled a whole class).

Run: `cd ~/agentfiles/workflow/skills/wif && python3 -m unittest discover -s tests -t .`
The package runs on Python 3.9+; the tests need 3.11+ (`contextlib.chdir`).

Second review (2026-10-21, two blind reviewers on the package): fixed the
shared temp-file name in atomic writes, the hook/command lost-update race
(now locked), resumed sessions keeping `ended`, `note --done` matching the
template comment, the memory-dir sanitizer, vanished containers mid-scan,
lone surrogates in prompts, `WIF_RING=0`, install backup-name collisions and
malformed `hooks` values, `adopt <name>` preferring a local directory, the
`fork` SessionStart source, NFC task names, BOM / `key:` / unterminated
frontmatter, multi-line HTML comments leaking into injected context.

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
