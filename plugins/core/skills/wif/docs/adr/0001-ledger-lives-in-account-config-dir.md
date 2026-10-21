---
status: accepted
---
# The wif Ledger lives in the account's config dir, not beside the worktrees

Robin runs two Claude accounts (`CLAUDE_CONFIG_DIR=~/.claude-justgames` /
`~/.claude-personal`) that must never see each other's work. The obvious home
for a work-in-flight ledger is next to `.worktrees-herdr/` in the scope root,
but the personal scope has no single root and the forestrie root is absent on
some machines. We decided the Ledger is `${CLAUDE_CONFIG_DIR}/wif/<scope>/`:
the account split that already governs memory and sessions then governs the
Ledger for free, and a mismatched account simply records nothing. Consequence:
the Ledger is machine-local and unversioned; durable facts still belong in the
in-repo conventions (plan `handoff.md`, `/save-status`, auto memory) that the
Stream file points at.

Update 2026-10-21: agentfiles now splits the personal account into profiles
(`~/.claude-personal`, `~/.claude-forestrie`, `~/.claude-home`). Each profile
is an Account for `wif`'s purposes and serves the Scope of its own name, so the
forestrie Ledger lives under `~/.claude-forestrie`. Personal keeps serving
forestrie and home only on a machine where those profiles do not exist, so
one Scope still never has two Ledgers.
