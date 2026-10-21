# Dashboard spec (`wif show`)

Target ≤ 40 lines at 120 columns. Order is fixed so the eye learns it.

```
wif · <account> @ <scope> · scanned 3m ago [· PRs cached/none]
▶ <current stream>  <status>  [flags]
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
untracked containers (N; wif adopt <task> [-s parked]):
  task   age   shape   dirty   herdr:<agent_status>   flags   (8 by recency; --all for everything)
unbound memory (N): task(files), …
```

- `--brief`: header block plus due reminders only.
- `--changes`: header + due + only containers whose (stream status, dirty,
  ahead, flags, PR states) changed since the previous `--changes` call, plus
  removed containers; last line `no changes` otherwise. The first call records
  a baseline and says so. This is the `/loop` tick output.
- Line budget: 40 lines total. The streams table takes whatever the other
  sections leave (minimum 4 rows) and ends with `… N more` when cut; `--all`
  lifts every cap.
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
