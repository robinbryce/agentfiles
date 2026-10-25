---
id: plan-2610-03
status: draft
created: 2026-10-25
refs:
  - plugins/core/skills/wif/CONTEXT.md
  - plugins/core/skills/wif/DESIGN.md
  - plugins/core/skills/wif/references/dashboard.md
  - plugins/core/skills/wif/SKILL.md
  - docs/plans/plan-2610-02-herdr-wif-birth-and-close.md
---

# Plan plan-2610-03 — wif: clickable References in the dashboard and hook text

**Status:** DRAFT · **Created:** 2026-10-25

## Context

Recovering a session with `/core:wif` works (2026-10-25: the hook loaded the
stream, the agent printed the dashboard). The goal / next / position lines
cite PRs (`#1669`, `#1672`) and Linear issues (`ENG-2654`) as plain text, so
nothing in the printed block is clickable. Robin asked for markdown links,
with a way to turn them off.

Grilled 2026-10-25 (`/grill-with-docs`); decisions, in dependency order:

| # | Decision | Chosen | Rejected |
|---|----------|--------|----------|
| 1 | Surfaces | `wif show` (header block, due, candidates, streams `next` column) **and** both hook injections (`[wif]` prompt line, SessionStart body). Not the statusline. | header block only; statusline |
| 2 | Default + switch | **Plain by default.** `--refs md\|plain` flag, `WIF_REFS` env (flag wins). The skill runs `wif show --refs md`; hooks always emit markdown. **No TTY detection**: `! wif show` inside Claude Code prints raw and is indistinguishable from the agent's Bash tool (both captured stdout, same env) — measured 2026-10-25. | markdown by default + `--summary-plain-refs`; TTY heuristic |
| 3 | What is a Reference | PR numbers (`#N`, `owner/repo#N`) and Issue ids matching the **scope's team keys** (justgames `ENG`, forestrie `FOR`). `ADR-0071`, `plan-2610-02`, `ARC-014`, SHAs stay plain. | all `[A-Z]+-\d+` (ARC-014 false positive); SHAs → commit pages |
| 4 | PR → repo | (1) the container's cached PR list entry with that number → its URL; (2) else the container's single origin repo → `https://github.com/<slug>/pull/N`; (3) else plain. No cross-container lookup. | scope-wide cache search (wrong repo on number collisions) |
| 5 | Linear workspace | per-scope table in `wif/config.py` (`justgames` → workspace `justgames`, teams `ENG`; forestrie → **TBD by Robin**, team `FOR`), env override `WIF_LINEAR_<SCOPE>=workspace:TEAM,TEAM`; no entry → plain. | read from the scope `.envrc` (direnv not loaded where hooks run) |
| 6 | Trim vs link | trim to column width first, then link the trimmed text; a cut reference stays plain; the Ledger is never rewritten. | link then trim (breaks links / budget) |
| 7 | Glossary | **Reference** added to CONTEXT.md. No ADR (cheap to reverse, not surprising). | — |

## Goal

```
$ wif show --refs md            # what the skill runs; the agent prints it verbatim
▶ eng-2654-odds-writer-optimisations  active · issue [ENG-2654](https://linear.app/justgames/issue/ENG-2654)
  goal: significantly reduced writes of live odds to market queue
  next: Robin: merge [#1669](https://github.com/SentientDogs/flip-oracle/pull/1669) and [#1672](…/pull/1672); promote S1 to stage-2 …
$ wif show                      # Robin, in a pane or via `!`: unchanged, plain
```

## Approach

One module, one call site per surface. Files under `plugins/core/skills/wif/`.

### S1 — `wif/refs.py` (pure)

- `linkify(text, resolver, mode) -> str` where `mode ∈ {"plain","md"}`; plain
  returns `text` unchanged. Patterns: `(?<![\w/])#(\d+)\b`,
  `\b([\w.-]+/[\w.-]+)#(\d+)\b`, and `\b(<TEAM>|<TEAM>)-\d+\b` built from the
  scope's team keys. Already-linked text (`](http`) is left alone so a
  second pass is a no-op.
- `Resolver` built from the index for one container: `pr_url(number,
  slug=None)` per decision 4 (cache → single origin → None), `issue_url(id)`
  per decision 5. Origin → slug: strip `git@host:` / `https://host/` and
  `.git`, GitHub hosts only (others → None).
- `mode_from(args, env)`: `--refs X` beats `WIF_REFS`, default `plain`;
  anything but `md`/`plain` is an error.
- `config.py`: `LINEAR = {"justgames": ("justgames", ("ENG",)), "forestrie":
  (<TBD>, ("FOR",))}` + `linear_for(scope)` honouring `WIF_LINEAR_<SCOPE>`.

### S2 — `show.py`

- `render(...)` takes the mode; after each `trim(...)` on goal / next /
  position / session / due text / candidate text / the streams-table `next`
  column, apply `linkify` with the resolver of the row's container (the
  current container for the header; the stream's own container for table
  rows and due notes). The header's `· issue ENG-N` (from `issue:`) is linked
  too. `--json` unchanged (plain ids; URLs are derivable).
- `--brief` and `--changes` inherit the mode.

### S3 — `hooks.py`

- `_ctx_line` and the SessionStart body (`goal:`, `next:`, `position:`,
  `issue:`, the `## Handoff` and `## Now` lines) go through `linkify(…, "md")`
  with the stream's container resolver. The index may be stale or absent in a
  hook; when there is no index entry, decision 4 step 2 (single origin,
  read from the container on disk via `tangents.container_repos` + `git
  remote get-url`) still applies, else plain.

### S4 — skill + docs

- `SKILL.md` §0: "Run `wif show --refs md` …" (and §5 tick: `wif show
  --changes --refs md`). Note that the agent prints the block verbatim so the
  links survive into the reply.
- `references/dashboard.md`: the `--refs` flag, the plain default, which
  fields are linked. `DESIGN.md` routine default: the seven decisions above
  in one bullet, including the measured `!` finding. `CONTEXT.md`: done
  (Reference).
- `wif help`: `show [--refs md|plain]`.

### S5 — tests

- `refs.py`: each pattern, `owner/repo#N`, team-key limit (`ARC-014` plain),
  cache-hit URL, single-origin URL, multi-origin → plain, non-GitHub origin →
  plain, idempotent on linked text, trim-cut reference stays plain, mode
  precedence (flag > env > default), bad mode errors.
- `show`: header/next/due/candidates/table linked under `--refs md`, byte-
  identical to today under default; `--json` unchanged.
- `hooks`: `[wif]` line and SessionStart body linked; stale/absent index →
  single-origin fallback → plain.

## Verification

- Suite green (140 today). A read-only `wif show --refs md` from
  `eng-2654-odds-writer-optimisations` shows `#1669`, `#1672` and `ENG-2654`
  as links; plain `wif show` is byte-identical to the pre-change output.
- In a live session: `/core:wif` prints a dashboard whose references are
  clickable in Claude Code; `! wif show` in the same session prints plain.

## Open for Robin

- forestrie Linear workspace key (decision 5). Until set, FOR-ids render plain.

## Out of scope

- Linking ADR / plan / ARC ids or SHAs (decision 3).
- Rewriting anything in the Ledger (decision 6).
- Statusline links (decision 1).
