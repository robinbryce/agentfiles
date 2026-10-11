# Decisions — plan 2610-01

Answers to the [README's open questions](./README.md#open-questions--verify-before-phase-2)
and the choices Robin made on 2026-10-11. Design decisions D1–D8 were all
accepted as written.

## Robin's choices (2026-10-11)

| Topic | Decision |
|-------|----------|
| Home profile root | `~/Dev/personal/home`. Its `.envrc` exports `CLAUDE_CONFIG_DIR=~/.claude-home` and overrides the `~/Dev/personal/.envrc` (personal profile) above it. |
| Home marketplace | New **private** repo `robinbryce/agentfiles-home`, cloned to `~/agentfiles-home`. |
| justgames | Left as is on the old wrappers and scope content. Not migrated in Phases 1–3. |
| claude.ai account skills | Cross-profile core set (`planning`, `pr-descriptions`, `clickable-references`, `save-status`) **plus** the non-sensitive home admin procedures. Sensitive home content stays plugin-only. |
| Q1 probe location | A throwaway branch of `robinbryce/draft-bryce-cose-receipts-mmr-profile`. |

## Verified answers

### Q2 — does `~/.claude/CLAUDE.md` load alongside the profile's own? **Yes.**

Tested with a copy of `~/.claude-personal` as `CLAUDE_CONFIG_DIR`, a marker
`CLAUDE.md` inside it, and a headless `claude -p` run (Claude Code 2.1.296).
The session reported both files loaded: the profile's `CLAUDE.md` as "the
user's private global instructions" **and** `/Users/robin/.claude/CLAUDE.md`
labelled "project instructions". The `@~/agentfiles/AGENTS.md` import inside
the latter was shown as a literal line, not expanded, in the headless run.

Consequence: Phase 1 must reduce `~/.claude/CLAUDE.md` to a two-line stub (or
delete it). Anything left there leaks into every profile.

### Q3 — pi skills paths and the skills CLI. **Both supported.**

- `npx skills@1.7.2` has a `pi` agent target that writes to `.pi/skills`
  (project) under `.pi/agent` conventions, so `npx skills add <repo> -a pi` works.
- pi 0.80.10's own bundle references `.agents/skills` (8 occurrences), so the
  open-standard project path is read too.

Consequence: the committed `.agents/skills/` layer serves pi without extra
links; bootstrap only needs to link the **plugin** skills into
`~/.pi-<profile>/skills/` for terminal parity with Claude Code.

### Q4 — pin an upstream skills repo as a plugin by sha. **Works, with caveats.**

A marketplace entry
`{ "source": "github", "repo": "mattpocock/skills", "sha": "b8be62ff…" }`
validated, added, and installed into a scratch config dir. The version recorded
is the 12-char sha; the cache path is `cache/<marketplace>/<entry>/<sha>/`.

Caveats:

- The upstream ships its own `.claude-plugin/plugin.json` with
  `name: mattpocock-skills`, so skills are namespaced `/mattpocock-skills:tdd`
  and `claude plugin details` needs that name. Name the marketplace entry
  `mattpocock-skills` too, as the docs recommend, to avoid the mismatch.
- You get **every** skill the upstream manifest lists (14 at the pinned sha,
  21 at current `main`, with renames such as `diagnose` → `diagnosing-bugs`).
  An entry cannot subtract from a manifest. Projected always-on cost at the
  pinned sha: about 1.4k tokens of skill metadata.
- Therefore: pin by sha in `forestrie-agents/marketplace.json` and delete both
  vendored copies, **or** keep one vendored `plugins/engineering/` with only
  the three skills if the extra metadata cost matters. Recommendation: pin,
  and revisit if the always-on cost is noticed.

### Q5 — account skills. Decided above (core + non-sensitive admin).

### Q1 — skills-dir plugin in a cloud session. **Unresolved; plan assumes no.**

Probe branch `probe/skills-dir-plugin` on the draft repo carries
`.claude/skills/probe-plugin/` (plugin dir with a skill and a SessionStart hook)
and `.claude/skills/plain-probe/` (control). Cloud session
`session_016pszdKMVD3AAEttVgbXa1y` was asked to write `/context` and skill
invocation results to `PROBE-RESULT.md` and push `probe/result`.

Local observation while the probe worktree was the session cwd: Claude Code
surfaced `plain-probe` as a nested skill but **not** `plugin-probe`, consistent
with the docs' note that skills-dir plugins are read only from the primary
working directory and never from nested or parent directories.

Status 2026-10-11: the cloud session started
([session_016pszdKMVD3AAEttVgbXa1y](https://claude.ai/code/session_016pszdKMVD3AAEttVgbXa1y))
but never pushed `probe/result` in about 25 minutes, including after a
follow-up message. Cloud sessions may only be able to push to `claude/…`
branches, or the session may be waiting on a prompt. Open the session to read
its `/context` output directly. Until then the committed layer stays plain
skills + rules, which works whatever the answer. Clean-up when done: delete the
remote `probe/skills-dir-plugin` branch and the local worktree
`draft-bryce-cose-receipts-mmr-profile/.claude/worktrees/probe-skills-dir-plugin`.

## Phase 2 notes (2026-10-11)

- forestrie-agents already had an unmerged `robin/skills-as-slash-commands`
  branch (skills form, duplicate vendored copy removed, tracked `tdd` patch).
  PR 1 builds on it: [forestrie/forestrie-agents#8](https://github.com/forestrie/forestrie-agents/pull/8),
  branch `robin/marketplace`.
- Because `tdd` carries a local patch, the engineering skills stay **vendored**
  as plugin `mattpocock-skills` (source `./vendored/matt-skills`) rather than
  sha-pinned upstream (Q4's alternative).
- `forestrie-linear` is not split out yet; `linear-mcp-forestrie` ships inside
  `forestrie-core`. The profile template no longer enables `forestrie-linear`.
