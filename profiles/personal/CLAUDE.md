# Profile: personal

This session runs in Robin's **personal** profile (`~/.claude-personal`):
robinbryce GitHub repos, open-source work, IETF drafts, dotfiles and other
personal projects. Conventions arrive as `core` and `research` plugin skills
and as the rules in this profile. Nothing from the forestrie, home or
justgames profiles is installed here; do not go looking for it.

## Planning params (override `core:planning` defaults)

| Param | Value |
|-------|-------|
| `plans_root` | in-repo `docs/plans/` (or `plans/` for small projects) |
| `decisions_home` | in-repo `docs/adr/`; ARC optional; many projects need neither |
| `id_scheme.plans` | date-cohort `plan-YYMM-NN-<slug>` |
| `id_scheme.decisions` | absolute `adr-NNNN` |
| `issue_refs` | none |

Everything is repo-local; there is no central docs hub for personal work.
