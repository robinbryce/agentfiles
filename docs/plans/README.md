# docs/plans

Plans for this repo itself (how agentfiles is organised), named per
[workflow/rules/planning.md](../../workflow/rules/planning.md).

> ids ≥ `2610` are date cohorts (`plan-2610-01…`); this repo has no legacy
> absolute-numbered plans.

| Plan | Status | Summary |
|------|--------|---------|
| [plan-2610-01-agent-config-reorg/](./plan-2610-01-agent-config-reorg/README.md) | active | Ground-up reorg: Claude profiles select scope; skills + AGENTS.md carry content; one plugin marketplace per trust boundary (agentfiles, forestrie-agents, private home); synced committed layer for cloud parity; pi / cursor / local-model coverage. |
| [plan-2610-02-herdr-wif-birth-and-close.md](./plan-2610-02-herdr-wif-birth-and-close.md) | active | herdr-task births the wif stream (-g/-p, adopt, tangent cleared, Handoff seeded, next-steps footer, fresh base, tabs only for root + first repo); closeout completes from inside the session (approve-inside / reap-outside marker, remote-reachability rule, live-agent guard, detached reaper, stream archived); one-command tangent promotion; envrc dedupe; ledger hygiene sweep. |
| [plan-2610-03-wif-clickable-refs.md](./plan-2610-03-wif-clickable-refs.md) | active | wif renders PR numbers and team-keyed Linear ids as markdown links in `wif show --refs md` and the hook injections; plain by default (no TTY heuristic: `!` output is raw); cache → single-origin → plain PR resolution; per-scope Linear workspace table. |
| [plan-2610-04-wif-reference-lines.md](./plan-2610-04-wif-reference-lines.md) | active | `wif show --refs md` lists each resolved Reference as a four-space-indented link + note line beneath its item (PR title/state from the cache; `this stream` for the own issue; link-only, unresolvable omitted) instead of inline links; plain unchanged; hooks keep inline. |
| [plan-2610-05-review-feedback-skill.md](./plan-2610-05-review-feedback-skill.md) | draft | `/core:review-feedback <pr>`: babysit a PR's review feedback — scope Overlays inside the skill, four Verdicts (Fix/Refute/Defer/Rejected fix; human refutations drafted), GitHub thread state as the Ledger, re-review for addressed reviewers; driven by wif PR review state (`scan --prs --fresh`, `feedback` flag) in a self-paced loop capped at 20 min. |
