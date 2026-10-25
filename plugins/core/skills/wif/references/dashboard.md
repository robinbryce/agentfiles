# Dashboard spec (`wif show`)

Target ≤ 40 lines at 120 columns. Order is fixed so the eye learns it.

```
wif · <account> @ <scope> · scanned 3m ago [· PRs cached/none]
▶ <current stream>  <status>  [flags]  · issue <ENG-N>     (plain only; under --refs md the issue is a Reference line)
  goal: <stream goal>
  next: <next>   position: <position>
    [#1669](https://github.com/<slug>/pull/1669) OPEN · <PR title>      (--refs md: one Reference line per resolved
    [ENG-N](https://linear.app/<ws>/issue/ENG-N) this stream             reference in goal/next/position/issue)
  goal: <stream goal>
  next: <next>   position: <position>
  session: <session goal|goal unset>   ~ <last intent|last prompt>  ctx NN%
due:                                   (only when a reminder is due)
  ! <stream>: <text>
streams (N):
  id   status   age   next   flags      (active, blocked, landed, parked; closed hidden)
  … N more (wif show --all)            (when the budget cuts the table)
  (backing missing: a, b)              (streams whose container/checkout is gone)
candidates (N):                         (tangents awaiting promotion)
  ← <stream>: <text>
  last → task: <task> [(derived; pin with wif tangent --as <task> --for "<substring>")]
    herdr-task <task> <collection|repos> && wif adopt <task> -g '<text>'   (parent stream's repo set)
    (container exists:  wif adopt <task>   (container exists, untracked)
                    or  wif adopt <task>   (already a stream (<status>); re-adopting clears this note))
untracked containers (N; wif adopt <task> [-s parked]):
  task   age   shape   dirty   herdr:<agent_status>   flags   (8 by recency; --all for everything)
unbound memory (N): task(files), …
```

- `--refs md|plain` (default plain; env `WIF_REFS`, the flag wins): under `md`
  item text is rendered exactly as written — **never inline links** — and each
  item (header block, streams-table row, due reminder, candidate) is followed
  by **Reference lines**: four-space-indented, one per distinct resolved
  **Reference** (`#N`, `owner/repo#N`, issue ids of the scope's Linear teams)
  in the item's *untrimmed* text, so a reference the column trim hides is
  still listed. A line is `[ref](url)` then a note: a PR's cached
  `STATE · title` (trimmed so the line fits 120 columns), `this stream` for
  the stream's own `issue:`, else nothing. An unresolvable reference has no
  line and stays as written. PR URLs come from the container's PR cache —
  this branch's PRs plus every bare `#N` the stream cites, resolved by number
  across the container's GitHub origins at `scan --prs` time (ambiguous →
  omitted) — else its single GitHub origin, else unresolvable (no guessing).
  Issue URLs need the scope's Linear workspace (`wif/config.py` `LINEAR`,
  override `WIF_LINEAR_<SCOPE>=workspace:TEAM,TEAM`). Reference lines count
  toward the line budget (the table shows fewer rows before `… N more`;
  `--all` lifts it). The skill runs `--refs md`; a human's `wif show` (pane
  or `!`) stays plain — indistinguishable from inside the process, so no TTY
  heuristic. `--json` is always plain ids. The hook injections keep inline
  links (single lines read by the model).
- `--brief`: header block plus due reminders only.
- `--changes`: header + due + only containers whose (stream status, dirty,
  ahead, flags, PR states) changed since the previous `--changes` call, plus
  removed containers; last line `no changes` otherwise. The first call records
  a baseline and says so. This is the `/loop` tick output.
- Line budget: 40 lines total. The streams table takes whatever the other
  sections leave (minimum 4 rows) and ends with `… N more` when cut; `--all`
  lifts every cap.
- `last →` is the newest tangent by date (ties: the current stream, then file
  order). Its task name is the `as=` pin on the note, else derived from the
  text (`<issue>-` prefix + first content words, ≤ 40 chars). The `herdr-task`
  repos are the parent container's; a `HERDR_REPOS_<X>` collection whose set
  matches exactly is named instead (`oracle`). The command is complete on its
  own: `wif adopt <task>` clears the tangent note on the parent stream and
  inherits parent and goal from it (see stream-format.md). The `-g` text is
  the tangent cut at a word boundary under 72 chars (no ellipsis), and the
  command line is the one dashboard line never trimmed to 110 columns: a cut
  command is not pasteable, a wrapped one is.
- Flags: `stale` (no commit, session or stream update for 14 days and nothing
  dirty), `dirty`, `unpushed` (ahead of the remote ref), `unpublished` (origin
  exists, branch never pushed), `no-remote` (a repo without origin), `landed?`
  (every PR MERGED, nothing dirty/unpushed, remote ref verifiable), `over-cap`
  (stream file over 120 lines), `bad-status` (status outside the vocabulary).
- `age` is time since the newest of: the latest commit across the container's
  repos, the newest session on the stream, and the stream file's `updated` date.
- Statusline (3 lines, event-driven + 30s refresh):
  `[account/scope] <stream> · <status> · <position> · NN% ctx · <model> [· ROTATE]`
  `goal: <session or stream goal>   next: <next>`
  `~ <last intent>`
