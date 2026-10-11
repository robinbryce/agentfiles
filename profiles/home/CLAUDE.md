# Profile: home

This session runs in Robin's **home** profile (`~/.claude-home`): tax,
finance, household administration and personal research. Procedures arrive as
`admin`, `finance` and `research-personal` plugin skills from the private
`agentfiles-home` marketplace, plus `core` and `research`. The privacy rule in
this profile is always on. Nothing from the coding profiles is installed here.

## Working conventions

- Records live under `~/Dev/personal/home/` in the layout the `admin` skills
  describe; never scatter copies elsewhere.
- Prefer `claude-local` (local model) for anything that processes raw
  statements or identifiers; use the hosted model for drafting and research.
- Plans and checklists use `core:planning` defaults with `plans_root` =
  `~/Dev/personal/home/docs/plans/`; no ADR/ARC.
