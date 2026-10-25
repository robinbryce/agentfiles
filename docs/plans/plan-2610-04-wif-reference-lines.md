---
id: plan-2610-04
status: active
created: 2026-10-25
refs:
  - docs/plans/plan-2610-03-wif-clickable-refs.md
  - plugins/core/skills/wif/CONTEXT.md
  - plugins/core/skills/wif/references/dashboard.md
  - plugins/core/skills/wif/DESIGN.md
---

# Plan plan-2610-04 — wif: Reference lines under each dashboard item

**Status:** ACTIVE · **Created:** 2026-10-25

## Context

plan-2610-03 (merged as agentfiles#12) made `wif show --refs md` link
References in place. The first real dashboard showed the cost: a `next`
column of 40 characters holding two 70-character links reads as URL soup, the
plain-English meaning is pushed out of the trimmed window, and a reference cut
by the trim (`ENG-2671` → `ENG-2…`) linked to the wrong issue (patched in
agentfiles#13 with an ellipsis guard). Robin's proposal, grilled 2026-10-25:
keep the item text as written and list each reference beneath the item as a
link with a short contextual note.

| # | Decision | Chosen | Rejected |
|---|----------|--------|----------|
| 1 | Where links live under `--refs md` | **Never inline on the dashboard.** Each item (header block, streams-table row, due reminder, candidate) is followed by one **Reference line** per distinct resolved Reference in its text, derived from the *untrimmed* text, so a reference the trim hides is still listed. | inline links (shipped in #12); links only in the table |
| 2 | Indent | **Four spaces** under every item, table and header alike. | column 37 (left of the status column) — groups visually but leaves ~30 fewer characters for the note |
| 3 | Sub-line content | `[ref](url)` then a note: a PR's cached **title and state**, trimmed so the line fits 120 columns; `this stream` when the id equals the stream's own `issue:`; otherwise the link alone. **Link-only**: a Reference with no resolvable URL gets no Reference line and stays as written in the text. | listing unresolvable refs as plain sub-lines (adds lines carrying nothing new); fetching Linear titles (the CLI never calls Linear) |
| 4 | Header block | same treatment: Reference lines after the `next … position …` line, four-space indent; the `· issue ENG-N` marker on the `▶` line is dropped in favour of a Reference line noted `this stream`. | keep the marker |
| 5 | Budget | Reference lines count toward the 40-line budget; the streams table fills rows **and their Reference lines** until the budget, then `… N more`; `--all` lifts the cap. Plain mode: byte-identical to today. | exempt md mode from the budget |
| 6 | Hooks | unchanged: the `[wif]` line and SessionStart body keep inline links (single lines read by the model, not a table); the #13 ellipsis guard stays for them. | sub-lines in hook text |
| 7 | Glossary | **Reference** refined; **Reference line** added. No ADR. | — |
| 8 | Owner prefix (added 2026-10-25 on review of the live output) | A leading `<owner>:` on `next` (`WIF_OWNER`, default `Robin`) is dropped on the header line and in the table, both modes; display only, Ledger as written; `owner:`, `Robin's`, mid-text `Robin:` untouched. | keep the prefix (wastes the 40-char cell on the reader's own name) |

## Goal

```
$ wif show --refs md
▶ eng-2654-odds-writer-optimisations  active  [unpublished]
  goal: significantly reduced writes of live odds to market queue
  next: Robin: merge #1669 and #1672; promote S1 to stage-2 and read §1.4 fro…   position: #1669 awaiting merge; ROTD PR…
    [#1669](https://github.com/SentientDogs/flip-oracle/pull/1669) OPEN · odds-writer: mirror the odds book …
    [#1672](https://github.com/SentientDogs/flip-oracle/pull/1672) OPEN · ROTD: PD-1…PD-6 …
streams (14):
  id                                 status    age next                                     flags
  ufc-aliases-1023                   landed    11m merge #1657 (ENG-2628) so the next stag… unpublished
    [#1657](https://github.com/SentientDogs/flip-oracle/pull/1657) MERGED · UFC fight-night aliases
    [ENG-2628](https://linear.app/justgames/issue/ENG-2628) this stream
$ wif show                       # plain: unchanged
```

## Approach

Files under `plugins/core/skills/wif/`.

### S1 — `refs.py`: collect, don't substitute

- `references(text, resolver) -> list[Ref]` with `Ref = (label, url, kind,
  number|id, note_source)`: every distinct PR / issue Reference in <text>
  that resolves to a URL, in first-appearance order, de-duplicated by URL.
  Reuses `PR_RE` / `issue_re()`; no ellipsis special-casing is needed since
  the input is untrimmed.
- `reference_lines(texts: list[str], resolver, own_issue: str, width=120)
  -> list[str]`: the four-space-indented lines. PR note from the resolver's
  cached entry (`title`, `state`): `OPEN · <title>`; `this stream` for the
  own issue; nothing otherwise. Title trimmed with `…` so the line ≤ width.
- `linkify(...)` stays for the hooks (decision 6).

### S2 — `show.py`

- Under `md`: every call site that linked inline (header goal/next/position/
  session, due text, candidate text, `last → task` issue, the table `next`
  cell) prints plain trimmed text, then `reference_lines([...untrimmed
  sources...])` for that item. Header sources: goal, next, position, issue;
  table row: next (+ issue); due: the note text; candidate: the note text.
  Drop the header `· issue` marker under md (plain keeps it).
- Budget: compute each row's lines (1 + len(ref lines)) and fill until
  `room` lines are used; `… N more` counts rows not shown. `--all` as today.
- `--changes`, `--brief`, `--json` unchanged in semantics (`--brief` includes
  the header's Reference lines).

### S3 — docs + skill

- `references/dashboard.md`: the Reference-line block, indent, note format,
  budget rule; `DESIGN.md` routine default (supersedes the inline-links
  sentence from plan-2610-03); `SKILL.md` §0 unchanged (`--refs md`).
- CONTEXT.md: done on this branch (Reference refined, Reference line added).

### S4 — tests

- `refs`: `references()` order/dedupe/resolution; `reference_lines()` note
  variants (title+state, own issue, link-only), width trimming, empty when
  nothing resolves.
- `show`: no `](http` inside any item text under md; Reference lines present
  under header, a table row, a due reminder and a candidate; a reference cut
  from the trimmed `next` still gets a line; budget counts Reference lines
  (`… N more` appears earlier under md than plain); plain byte-identical.
- hooks tests unchanged.

## As built (2026-10-25)

S1–S4 as specified, on this branch with the agentfiles#13 ellipsis guard
folded in (it remains for the hook text). `refs.references()` /
`refs.reference_lines()`; `show.py` renders item text plain under md and
appends Reference lines for the header (sources goal, next, position, issue),
each table row (next, issue), each due reminder and each candidate (note text
+ the tangent's issue); the streams table fills by lines, at least one row,
`… N more` counts rows. Suite 148 → 150.

## Verification

- Suite green (148 today + the above). Live, read-only: `wif show --refs md`
  from `eng-2654-odds-writer-optimisations` renders the Goal block above with
  the two PR titles from the cache; plain output byte-identical to the
  pre-change output.

## Out of scope

- Linear titles on issue Reference lines (would need the skill to write them
  into the stream; not now).
- Changing how Robin writes `next` (bare refs stay allowed; the text is
  rendered as written).
