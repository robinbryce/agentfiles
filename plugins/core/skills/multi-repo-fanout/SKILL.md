---
name: multi-repo-fanout
description: Fan out to execute, never to decide. One context spanning repos
  makes the cross-repo decisions; per-repo agents implement an already-written
  plan. Cross-scope.
user-invocable: false
---
# Multi-repo fan-out — decide in one context, execute in many

When work spans several repositories, there are two modes and they are not
interchangeable. Choosing wrongly is the main way multi-agent work goes bad.

## The rule

**Fan out to execute. Do not fan out to decide.**

| Phase | Shape | Why |
|-------|-------|-----|
| Read, connect, decide | **One** context spanning all the repos | Cross-repo findings are *connections*; nothing scoped to one repo can see them |
| Implement a settled plan | **One agent per repo** | Well-specified, independent, parallel, failure-contained |

## Why discovery cannot be fanned out

An agent scoped to one repo is structurally unable to notice that two repos
disagree. The findings that matter most in multi-repo work all have the same
shape — a relationship between things in different trees:

- a term that names one mechanism in repo A and a different one in repo B, so a
  comment or ticket in A is quietly describing B's thing;
- a dependency recorded in a ticket that was never real, visible only by holding
  both sides at once;
- a design document contradicted by its own companion document, or by the code;
- an interface whose two ends were specified from opposite directions.

Each of these is invisible from inside either repo alone. Every one is cheap to
find with the whole picture loaded and effectively unfindable without it.

**The failure mode is specific.** Fan out before the cross-repo understanding
exists and you get N locally-sensible, globally-wrong implementations — each
defensible inside its own repo, collectively wrong, and expensive to unwind
because each arrives as a plausible finished PR.

## The sequence

1. **One agent, many repos.** Read across the trees, state the connections,
   settle the design. Expect to be corrected; expect to withdraw things.
2. **Write the decision down** — ADR / ARC per
   [planning.md](./planning.md) — so it outlives the context that produced it.
   A decision that exists only in a conversation will be re-derived, differently.
3. **Write the plan**: a master section (goal, locked decisions with citations,
   sequencing, definition of done, out-of-scope) and **one subsection per repo**.
4. **Fan out**, giving each agent its own subsection.

## The plan is the interface, and it has a test

A per-repo section is ready to dispatch when it is **self-contained enough to
paste into a fresh agent that has read none of the discussion**.

If you find yourself writing context into the dispatch prompt that the plan
should have carried — a rejected alternative, a constraint, a false dependency
someone should not re-derive — the plan is not finished. **Fix the plan, not the
prompt.** The prompt is thrown away; the plan is what the next person reads.

Corollaries worth stating in the plan itself, because a per-repo agent cannot
work them out:

- **False dependencies, explicitly denied.** If repo B's work looks blocked on
  repo A but is not, say so in B's section, with the reason. Otherwise B's agent
  will wait, or invent the coupling.
- **Hard invariants, named.** Constraints that a locally-sensible change would
  violate ("payment gates issuance only; no verification path consults payment
  state") must appear where the implementing agent will read them.
- **Rejected alternatives.** Otherwise each agent re-litigates them, and some
  will choose differently.

## Dispatch hygiene

- **Results come back as PRs and tracker updates**, never scraped terminal
  output. Terminal text is for diagnosing a stuck agent.
- **Decide the permission posture before dispatching**, not after agents block.
  Unattended execution is a deliberate choice; do not make it implicitly, and do
  not answer another agent's permission prompts to keep things moving.
- **Verify a dispatch was actually accepted.** Submission APIs can report
  success while the agent never received the text.
- **Do not fan out onto a human decision.** If the remaining work is "someone
  must choose", an agent only produces churn.

## Tooling

Scope- and tool-specific. For the herdr multi-repo setup — `herdr-task` to build
workspace/worktrees/tabs, `herdr-dispatch` to start and drive named agents —
see `dotfiles/docs/README-herdr.md`. The rule above is independent of it and
applies equally to in-session subagents.
