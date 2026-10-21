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
  (no container: a, b, c)
candidates (N):                         (tangents awaiting promotion)
  ← <stream>: <text>
untracked containers (N; wif adopt <task> [-s parked]):
  task   age   shape   dirty   herdr:<agent_status>   flags   (8 by recency; --all for everything)
unbound memory (N): task(files), …
```

- `--brief`: header block only (first 5 lines). Used by the statusline-adjacent
  "where am I" injection in SKILL.md.
- `--changes`: header + due + only containers whose (stream status, dirty,
  ahead, flags, PR states) changed since the previous `--changes` call; prints
  `no changes` otherwise. This is the `/loop` tick output.
- `age` is time since the newest commit across the container's repos, or the
  newest session on the stream, whichever is later.
- Statusline (3 lines, event-driven + 30s refresh):
  `[account/scope] <stream> · <status> · <position> · NN% ctx · <model> [· ROTATE]`
  `goal: <session or stream goal>   next: <next>`
  `~ <last intent>`
