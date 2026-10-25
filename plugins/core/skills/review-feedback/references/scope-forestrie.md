# Overlay — forestrie

- **Scope root**: `~/Dev/personal/forestrie`. **Checkouts live on morgan**,
  not on banks-7: if the scope root is absent here, stop with one line
  ("forestrie checkouts are on morgan; run this skill there").
- **Standards**: the forestrie-agents rules (`forestrie-agents/workflow/skills`
  via `SKILLS_PATH`), the repo's `AGENTS.md` / ADRs. No separate
  rules-of-the-road corpus; the ADRs are the recorded decisions a Fix must
  not contradict.
- **Bots to expect**: GitHub Copilot review, CodeRabbit where enabled.
- **Tracker**: Linear workspace **TBD** (set `WIF_LINEAR_FORESTRIE=<ws>:FOR`
  and update here), team `FOR`, key via `direnv exec ~/Dev/personal/forestrie
  printenv LINEAR_API_KEY`; never the justgames key.
- **Test / lint for a Fix**: the repo's own task runner; run the touched
  package's tests only.
