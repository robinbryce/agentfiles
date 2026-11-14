# Provenance

- **Origin.** Built by hand on 2026-11-14 at the close of a forestrie grill on a multi-repo design
  (44 decisions over three rounds). Robin asked for the decisions as a thematic log and a graph canvas
  of their impact on the design, then asked for it as a skill usable in any planning, design or
  implementation session, in any profile. Both are Robin's own work.
- **Generalised here.**
  - The page is a template filled from one JSON data file (`scripts/build.py`), so the log and the
    canvas cannot drift.
  - Theme colours are eight slots, not named per subject; a `proposed` status covers decisions not
    yet ruled.
  - The canvas embeds its data, so `build.py extract` recovers it and a later session can update the
    canvas in place.
  - Where the log lives, the ids, commits and publishing come from `references/profile-*.md`, chosen
    from `CLAUDE_CONFIG_DIR` (wif account as fallback), as in `orchestrator-mode` and
    `review-fix-cycle`.
