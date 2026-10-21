# Stream file format

Path: `${CLAUDE_CONFIG_DIR}/wif/<scope>/streams/<id>.md`. Markdown with a
flat YAML frontmatter (every value a double-quoted scalar; the parser
handles nothing fancier). Cap: 120 lines total — `over-cap` is a dashboard flag.

```
---
id: "eng-2486-declare-undeclarables"     # herdr task name, or <repo>--<branch>
scope: "justgames"
status: "active"                          # active|parked|blocked|landed|closed
goal: "one line: what done looks like for the whole stream"
next: "one line: the very next action"
position: "slice 2/3 — review fixes"      # plan slice when a plan dir exists, else free text
parent: "ENG-2486"                        # optional grouping key (issue / plan id / topic)
backing: "herdr:/abs/path/.worktrees-herdr/<task>"   # or repo:/abs/path
issue: "https://linear.app/..."           # optional
prs: "#1581"                              # optional, free text; scan keeps the real list in index.json
handoff_doc: "/abs/path/docs/plans/plan-2610-03-x/handoff.md"   # where durable handoff text lives
last_session: "<session id>"              # hook-maintained; the handoff carry-forward source
created: "2026-10-21"
updated: "2026-10-21"
---
## Now
goal: …          (ACE four fields; ≤ 20 lines; rewritten, not appended, at handoff)
approach: …
done: …
failing: …
## Notes
- [followup] 2026-10-21 check hockey CMS rows after merge
- [tangent] 2026-10-21 generic drift-report linter could be its own stream
- [reminder due=2026-10-23] 2026-10-21 ping reviewer
- [reminder due=landed] 2026-10-21 close ENG-2486 in Linear
## Handoff
(paste-ready kickoff prompt, ≤ 25 lines; the SessionStart hook injects this)
## Dead ends
- 2026-10-21 tried X; fails because Y
```

Rules
- `Now` is rewritten at each handoff and should shrink or hold. Growth is drift.
- `Notes` lines are removed with `wif note --done "<substring>"` when acted on
  (a followup that became an intent, a tangent that became a stream via
  `wif adopt`/`start`, a reminder that fired).
- The SessionStart hook injects `Handoff` (30 lines max) and `Now` (20 lines max).
- Closing: `wif mark -s closed` moves the file to `../archive/`; hooks then
  ignore the container until `wif adopt` re-opens it.
- Values are double-quoted with `\` and `"` escaped; newlines are flattened
  to spaces. Keep every value on one line.

## Session file

`${CLAUDE_CONFIG_DIR}/wif/<scope>/sessions/<session_id>.json`, hook-written:

```json
{"session_id":"…","scope":"justgames","stream":"<id>","started":"…","ended":null,
 "goal":"session goal or null",
 "ring":[{"t":"…","prompt":"first line of prompt","intent":"model-inferred or pinned","pinned":false,"outcome":"first line of reply"}]}
```

`ring` keeps the last 10. `ended` and `end_reason` are set by SessionEnd and
cleared again when the session resumes. A sidecar `<session_id>.ctx.json` is
written by the statusline whenever the cwd is bindable:
`{"used_pct":63,"model":"Fable","cost_usd":1.5,"t":"…","stream":"<id>"}`.
A `<id>.md.lock` file next to each stream is the advisory write lock.

## Index

`index.json` is derived by `wif scan` and never hand-edited. Per container:
task, path, shape (`normal|direct|docs|norepos|empty|repo`), repos (branch,
dirty, ahead/behind, remote ref, last commit, origin), memory dirs, herdr
workspace status, cached PRs, stream status, and flags (`stale`, `dirty`,
`unpushed`, `unpublished`, `no-remote`, `landed?`, `over-cap`, `bad-status`).
Plus `orphan_streams` (stream file whose backing is gone), `unbound_memory`,
`pr_failures` and `pruned_sessions`.
