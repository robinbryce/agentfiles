# Overlay — home profile

- **Status skill**: `/core:save-status`.
- **Status root**: `~/Dev/personal/home/docs/status/`.
- **Plans root**: `~/Dev/personal/home/docs/plans/`; no ADR/ARC.
- **Delegation caveat**: work that reads raw statements or identifiers goes
  to the local model per the profile's conventions, never to a hosted
  subagent. Keep that work in the main thread or a local-model session
  rather than routing it to a `haiku` / `sonnet` tier.
