# Triage rules

The two tests a Finding must pass to become a **Fix**, and the shapes that
fail them. Read the code before deciding; never triage from the comment text
alone.

## Test 1 — is the Finding correct about the code as it stands?

Reproduce the claim: open the file at the Thread's path and line (or the
current line if the Thread is outdated), trace the behaviour it describes.
Correct → go on. Wrong → **Refute**, with the evidence as `file:line` plus
the one sentence that shows it. A reviewer describing a *preference* ("I
would name this X") is correct by definition; whether to act is Test 2.

## Test 2 — is a remedy inside the PR's Plan and Design?

Inputs: the PR body's plan link or `docs/plans/<plan>` it names; the plan's
decision table; the repository's ADRs and rules of the road the overlay
points at. The remedy is inside when it changes code the PR already touches
or must touch to satisfy its own goal, and contradicts no recorded decision.

- Contradicts a recorded decision → **Refute** (cite the decision).
- Correct but outside the PR's goal or file set → **Defer** (issue + tangent).
- Inside, but every remedy is a Workaround or breaks a rule of the road →
  **Rejected fix** (draft; say which rule or what behaviour the Workaround
  would hide).
- Otherwise → **Fix**.

## Workaround — the shapes to refuse

A change that satisfies the comment without changing the behaviour the
comment is about:

- a suppressed or downgraded warning / lint rule / type error
- a widened type, an `any`, a cast, an `unwrap`, a `!` to silence a check
- a special-cased test, a skipped or retried test, a loosened assertion
- a caught-and-ignored error, a default that hides a missing value
- a comment or docstring that explains the problem instead of fixing it
- copying the reviewer's suggested text when the suggestion itself does one
  of the above

## Rules of the road

Scope overlays name them. A Fix that would need an exception to one is a
Rejected fix even when the reviewer asked for it; the draft says which rule
and offers the in-rule alternative if one exists.

## Preferences and nits

Correct, in scope, cheap, and consistent with the codebase's conventions →
Fix (one commit, same as any other). Inconsistent with the codebase's
conventions → Refute with the convention cited. Never silently ignore a nit:
every Thread gets a Verdict.
