# Decisions — plan 2610-01

Answers to the [README's open questions](./README.md#open-questions--verify-before-phase-2)
and the choices Robin made on 2026-10-11. Design decisions D1–D8 were all
accepted as written.

## Robin's choices (2026-10-11)

| Topic | Decision |
|-------|----------|
| Home profile root | `~/Dev/personal/home`. Its `.envrc` exports `CLAUDE_CONFIG_DIR=~/.claude-home` and overrides the `~/Dev/personal/.envrc` (personal profile) above it. |
| Home marketplace | New **private** repo `robinbryce/agentfiles-home`, cloned to `~/agentfiles-home`. |
| justgames | Left as is on the old wrappers and scope content. Not migrated in Phases 1–3. **Superseded 2026-10-21:** Robin's justgames skills ship as the public `justgames@agentfiles` plugin (`plugins/justgames/`), enabled only in the justgames profile, and the profile is bootstrapped like the others. |
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

### Q1 — skills-dir plugin in a cloud session. **No.**

Robin checked `/skills` in the claude.ai web session on 2026-10-11:
`plugin-probe` (a skill inside a plugin directory under `.claude/skills/`) was
not listed. A repo cannot ship a whole plugin, hooks included, to cloud
sessions. The committed layer stays plain skills in `.agents/skills/` (with
`.claude/skills/` symlinks) plus `.claude/rules/`; plugin hooks run only in
terminal sessions. Probe branch and worktree deleted.

Original probe notes:

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
skills + rules, which works whatever the answer. Clean-up done.

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

## Phase 2 notes, PRs 2–3 and the canopy pilot (2026-10-11)

- **Layout deviates from 01-target-layout.** `forestrie-core` stays rooted at
  the repo (`source: "./"`, skills from `workflow/skills/`, `workflow/rules/`,
  `arc-context/`) rather than moving under `plugins/forestrie-core/`. Glossaries
  are `arc-context/arc-<name>/SKILL.md`; `rules-of-the-road/` stays where it is
  and serves as the rules source. `workflow/rules/` was not split into
  `rules/{common,lang}/`: the manifests copy `workflow/rules/<name>/SKILL.md`
  to `.claude/rules/<name>.md` directly, and Claude Code reads `paths:` from
  the skill frontmatter (verified in canopy).
- **Public repos get the synced subset (Robin, 2026-10-11).** forestrie-agents
  is private; canopy, arbor, univocity, univocity-tools and mandate are public.
  Robin chose to publish the synced subset as-is (process guidance and
  invariants, no secrets; links into private repos 404 for outsiders) rather
  than trim it or make forestrie-agents public. forestrie-agents' AGENTS.md now
  says to write nothing there that cannot be public.
- **Manifest format grew** `marketplace` and `plugin` directives (merged into
  `.claude/settings.json`), and a relative `source` resolves against the
  manifest's directory (`source ..`).
- **Frontmatter YAML.** Ten forestrie-agents SKILL.md files had unquoted `: `
  in `description`/`when_to_use`. Claude Code tolerated it; `npx skills` skipped
  them. Fixed in forestrie-agents#9; AGENTS.md tells contributors to check
  with `npx skills add . --list`.
- **Drift is content, not SHA.** `doctor --repo` diffs the committed files
  against a local checkout of the source; the source SHA moves with unrelated
  commits. `.synced-from` holds no machine paths or timestamps, and sync deletes
  the `skills-lock.json` that `npx skills` writes.
- **Marketplace name overlap is harmless.** The profile knows
  `forestrie-agents` as a directory source, canopy's project settings as a
  GitHub source; the session used the profile's without prompting.
- **Measured cost in canopy:** AGENTS.md 1.6k tokens; always-on rules 5.9k
  (rules-of-the-road-canopy 3k, platform 1.5k, branch-naming 0.9k); six project
  skills ~0.5k of metadata. TypeScript rules attach only on a `.ts` read.
- **Merge practice (2026-10-11).** forestrie-agents squash-merges, canopy uses
  merge commits. Stacked PRs in forestrie-agents: after the base squashes,
  merge `main` into the next branch (keeping the branch side) rather than
  rebasing and force-pushing. Re-sync target repos from forestrie-agents main
  after its PRs merge, so `.synced-from` names a commit that stays on main.

## Phase 2 step 6 and workspace loading (2026-10-11)

- **The workspace AGENTS.md loads without a CLAUDE.md beside it.** Claude
  Code (2.1.x) picks up `~/Dev/personal/forestrie/AGENTS.md` from the parent
  directory of a repo session, so the workspace needs no `CLAUDE.md` shim.
- **Directory-source plugin versions are cosmetic.** After the rerun,
  `claude plugin list` still shows forestrie-core at `72fa8903d9fa` (the #8
  commit) and the cache directory keeps that name, but `plugin details` and a
  live session both see the current checkout (28 skills, `arc-*` included).
  Do not read the version string as staleness for a directory marketplace.
- `forestrie-agent-context.md` deleted; `workspace/AGENTS.md` replaces it.

## Phase 2 step 5 rollout (2026-10-11)

- **Same PR shape as canopy#268**, one worktree and draft PR per repo, all on
  `robin/agent-layer-sync`, synced from forestrie-agents main 797688a.
- **AGENTS.md edits stay minimal**: `../devdocs/` links become GitHub links
  (marked private in public repos), the glossary points at
  `forestrie/protocol`, a "Team rules and skills" line names the manifest, and
  `.cursor/rules` lists keep only the rules with no synced twin (Terraform,
  YAML-manifest, citty CLI, markdown, doppler-run-tasks). univocity's
  `../../devdocs/` links were broken and are fixed. mandate had no CLAUDE.md.
- **Repos can hide the layer.** devdocs ignored `.claude/` (added 2026-08-01
  for `.claude/worktrees/`); now only `.claude/worktrees/` and
  `.claude/settings.local.json`. `sync` warns and `doctor --repo` reports
  drift when a layer path is gitignored (agentfiles e2c263f), since a local
  doctor run otherwise passes while every clone lacks the files.
- **Repo formatters must skip the copies.** mandate's `prettier --check .`
  failed on them; `.prettierignore` now lists `.agents/` and `.claude/`.
  Reformatting in place would be drift. canopy and univocity-tools scope
  prettier to package dirs and need nothing.
- **Org commit rule wins over tool attribution.** The synced
  `commit-conventions` rule forbids `Co-Authored-By` in org repos, so the
  rollout commits carry none (canopy#268's do).

## CI job proposal (2026-10-11)

Awaiting Robin's choice; nothing added yet.

**What it checks.** The committed layer is exactly what `agentfiles sync`
wrote at the forestrie-agents SHA recorded in `.agents/skills/.synced-from`:
no hand edits, nothing missing, nothing gitignored. It does **not** fail
because forestrie-agents main moved on; staleness is a separate, advisory
concern.

**Where it lives.** A composite action
`forestrie/.github/actions/agent-layer-doctor` in the public org `.github`
repo, next to `secret-egress-lint`, which repos already call as
`forestrie/.github/actions/secret-egress-lint@main`. Each repo calls it from
a job in `workflow-lint.yml` (arbor, univocity and mandate already have the
workflow; the others get it). Trigger: `pull_request` with paths `AGENTS.md`,
`CLAUDE.md`, `.claude/**`, `.agents/**`, `.gitignore`, plus `push` to main.
The action fetches `bin/agentfiles` from public `robinbryce/agentfiles` at a
pinned SHA.

**How it gets forestrie-agents (private): two options.**

- **A. GitHub App token.** `actions/create-github-app-token` with the org app
  (`GITAPP_ID` / `GITAPP_PRIVATE_KEY`, scoped to `repositories:
  forestrie-agents`, contents read), check out forestrie-agents at the
  `.synced-from` SHA, run `doctor --repo . --source <dir> --ci`. Needs the
  app installed on forestrie-agents and the key as an org secret visible to
  eight repos. Fork PRs cannot mint, so the job skips there. Known hazard:
  canopy's `dev` environment shadows `GITAPP_PRIVATE_KEY` with an invalid key
  (canopy `tests-system.yml`), so the job must not use an environment.
- **B. No secret: record file hashes at sync time (recommended).** `sync`
  writes a sha256 per synced file into `.synced-from`; `doctor --repo --ci`
  checks the committed files against those hashes when no source checkout is
  present. That catches the same failures (hand edits, missing or ignored
  files) without reading forestrie-agents, works on fork PRs, and puts no
  secret in eight repos. Staleness against forestrie-agents main then belongs
  in forestrie-agents itself (a later scheduled job that re-syncs and opens
  PRs). Cost: an agentfiles change and one re-sync of every repo, which is
  cheap now while seven of the eight PRs are drafts; canopy needs a small
  follow-up PR.

## Rethinking D4: pointer, not copies (2026-10-11)

Robin questioned replicating the agent layer into every repo: copies drift,
and the drift check above only papers over that. Decisions:

- **Drop the CI drift job** (the proposal above is withdrawn).
- **Keep the source split** (agentfiles, forestrie-agents, agentfiles-home;
  one marketplace per trust boundary, D3).
- **Public repos first.** Make forestrie-agents public after a sensitivity
  review, so a committed `.claude/settings.json` marketplace pointer works
  with no auth. Private repos (forest-1, arbor-flux, devdocs) wait.
- Open standards (AGENTS.md, SKILL.md) have no cross-repo include by design
  (no remote instructions, reproducible per commit, no auth), so routing is
  a harness feature: Claude plugins via the pointer, or MCP. Cursor and Codex
  get AGENTS.md links only.
- Gate: Robin's cloud check in canopy must show cloud sessions installing
  forestrie-core from the project-settings pointer. The seven draft PRs are
  on hold until then; if it works they shrink to the pointer plus AGENTS.md.

### forestrie-agents sensitivity review (2026-10-11)

Scope: all 41 commits on every ref, 79 files on main, 10 PRs and their
comments, no issues.

- gitleaks over full history and PR text: no leaks.
- No IPs, cloud project ids, cluster names, contract addresses or machine
  paths. Only author email is Robin's.
- Hostnames (`mandate-dev.forestrie.dev`, `mandate.forestrie.dev`,
  `api-b.forest-2.forestrie.dev`), Doppler project names and env-var names
  appear in `workflow/skills/fork-mandate` and `setup-clone`. All already
  appear in public mandate or canopy `main`.
- "customer"/"partner" hits are generic examples in the vendored
  grill-with-docs skill.
- PR bodies link five claude.ai session ids; they open only for Robin.
- **To fix before publishing:** the vendored mattpocock/skills copy is MIT
  but ships without upstream's LICENSE; add it under `vendored/matt-skills/`.
  forestrie-agents itself has no license (canopy, arbor, univocity none;
  univocity-tools, mandate, protocol MIT).

### Cloud check in canopy (2026-10-11), README verification item 4

Run by Robin on canopy main (f61729a) while forestrie-agents was still
**private**.

- The six synced skills are listed as project skills (from `.claude/skills/`
  symlinks); the five always-on rules load and the five `paths:`-scoped ones
  do not until a matching file is touched. The committed layer works in
  cloud.
- **forestrie-core is not present.** `installed_plugins.json` is empty and
  the marketplace was never fetched, although `.claude/settings.json`
  declares it. No hooks ran.
- Ambiguous cause: cloud may ignore project-declared marketplaces (terminal
  sessions ask before trusting one; cloud has no one to ask), or it could not
  read the private repo. Next probe: make forestrie-agents public, then a
  throwaway canopy branch with a SessionStart hook that adds the marketplace
  and installs forestrie-core; run two cloud sessions on it.
- The session saw the `commit-conventions` rule override the tool's
  Co-Authored-By reminder, as intended.

### Cloud plugin-install probe (2026-10-11)

forestrie-agents made public by Robin. Probe branch
[canopy `probe/cloud-plugin-install`](https://github.com/forestrie/canopy/commit/4a65172)
keeps the settings pointer and adds a SessionStart hook that runs
`claude plugin marketplace add forestrie/forestrie-agents` and
`claude plugin install` for both plugins (skipped when `CLAUDE_CONFIG_DIR`
is set, so local profiles are untouched).

Result, first cloud session: **forestrie-core (28 skills, `arc-*` included)
and mattpocock-skills (3) were available in the same session** the hook ran
in. The plugin's `require-worktree` PreToolUse hook is registered from its
`hooks.json` (not exercised). A second session is not needed.

Consequence: public repos need no copies. Pointer + SessionStart install
hook in `.claude/settings.json`, `CLAUDE.md` as `@AGENTS.md`. Costs: rules
arrive as plugin skills rather than always-on `.claude/rules/`, so
always-on guidance becomes on-demand in cloud; Cursor and Codex get AGENTS.md
links only.

Hook log: `installed_plugins.json` did not exist before the hook ran, so
**the settings pointer alone installs nothing in cloud**, even with the repo
public; the hook did all of it (anonymous clone, both plugins installed at
forestrie-agents main 5cc4ef4, Claude Code 2.1.296). Cloud sets
`CLAUDE_CODE_REMOTE=true`: use that as the hook's guard. Cloud sessions get
forestrie-agents **main** at session start, not a pinned SHA: no drift and
no re-sync, at the price of per-commit reproducibility.
