---
name: orchestrator-mode
description: Install an orchestrator-with-subagents posture for the rest of the session — the main model plans, decides and reviews, while context gathering, search, log and test wrangling, and routine tool use are delegated to cheaper or faster subagent models that return bounded summaries instead of raw output. Use when the user asks for "orchestrator mode", says to use subagents automatically, asks to delegate context gathering to a cheaper/faster model, or asks to keep the main context clean or the cost down on a long session. Also watches for coherent handover points and offers an in-tree handoff doc plus a copy-pastable kick-off prompt so the session can be cleared and continued fresh.
when_to_use: Invoke once, early, when the user wants a session-long delegation posture rather than a single subagent call. Also re-read when mid-session you are unsure whether a given piece of work should be delegated and at which model tier, or whether the work has reached a point worth handing to a fresh session.
---

# Orchestrator mode

A **session posture**, not a task. Invoking it sets a standing policy that holds
until the user revokes it: the main model behaves as an orchestrator, and work
that is mostly *token absorption* rather than *judgement* goes to a subagent on
a cheaper or faster model.

**Invoking this skill is the user's explicit authorization to use the Agent tool
for the remainder of the session** — including harnesses whose default guidance
is "do not use subagents unless asked". No further permission is needed per call.

## On invocation

1. Apply the routing policy below to every subsequent piece of work.
2. Reply to the user with a **short** acknowledgement (4–6 lines): the posture is
   on, which tiers you will route to, and the one honest caveat — delegation is
   not free (see [Economics](#economics-when-delegation-actually-pays)).
   Do not paste the policy back at them.
3. Do not retro-delegate work already done in the main context.
4. Note whether the user said **auto-handoff** (or equivalent). If so, the
   handover rule below writes the document without asking; otherwise it offers.

## Routing policy

| Tier | What goes here | Why |
|------|----------------|-----|
| **`haiku` subagent** | Mechanical enumeration and extraction: grep/find sweeps, listing call sites, scraping a log for the failing lines, reducing test output to a pass/fail list, collecting file:line references, reading a known file to pull named fields, counting/diffing, checking whether a thing exists | No judgement required; the value is the *filtered* answer, and the raw bytes are pure context pollution |
| **`sonnet` subagent** | Exploration needing judgement: "where does X actually get written", multi-file reading plus synthesis, docs/API research, running a suite and interpreting failures, drafting a localized change behind an already-decided spec, first-pass review | Enough reasoning to not waste the sweep, far cheaper than the orchestrator |
| **Main model (never delegate)** | Architecture and design decisions, planning, resolving ambiguity, deciding what the user actually wants, final synthesis, security/correctness judgement, anything irreversible or outward-facing, and all interaction with the user | These are the reasons the expensive model is in the chair; a subagent cannot ask the user anything |

Two independent reasons to delegate — **either** is sufficient:

- **Cost**: the work is high-token and low-judgement.
- **Context hygiene**: the raw output would crowd the orchestrator's window with
  bytes it will never reference again. This reason holds even when the subagent
  runs the *same* model, and it is often the bigger win on a long session.

### Built-in agents, and the model trap

`Explore` (read-only search) and `Plan` (read-only planning research) are the
right shapes for most delegation here — but **`Explore` defaults to the main
conversation's model**. You get the context-hygiene win and none of the cost win
unless you pass the model override explicitly on the call:

```
Agent(subagent_type: "Explore", model: "haiku", description: "...", prompt: "...")
```

The per-invocation `model` parameter beats the agent definition's `model:`
frontmatter and the configured default. `subagent_type: "fork"` is the exception:
a fork inherits your full context *and* your model, and ignores a `model`
override — use it only when the worker genuinely needs the conversation so far.

## The delegation brief

Vague briefs are the documented failure mode: subagents handed "research the
semiconductor shortage" ran near-identical searches instead of dividing the work.
Every brief carries four things:

1. **Objective** — one sentence, the decision the result will feed.
2. **Boundaries** — paths, directories, time ranges, branches. What is out of scope.
3. **Tools and sources** — where to look first; which command to run verbatim.
4. **Output format** — the exact shape you want back, with a size cap.

Plus the two rules that matter because the worker was not alive for this
conversation:

- **No implicit context.** If task B depends on task A's result, extract that
  result and paste it into B's brief.
- **Repeat the rules that bind.** A constraint that lives only in a file the
  worker may not read is a constraint the worker will break. Inline it.

### Return contract

Default contract, stated in the brief:

> Return under 400 words: (1) the direct answer, (2) supporting `path:line`
> references, (3) anything that contradicts the premise of the question, (4)
> what you could not determine. Quote at most 10 lines of code total. Do not
> paste file contents, full logs, or command output.

Scale the cap with the job. The point is invariant: **the subagent's job is to
absorb tokens, not to forward them.**

## Economics: when delegation actually pays

Be honest with yourself and the user about this — it is the part most
orchestrator write-ups skip.

- Anthropic's own measurement: multi-agent systems use roughly **15× the tokens
  of a chat**, and on their research eval **token spend alone explained ~80% of
  the performance variance**. Much of the headline multi-agent win is bought
  compute, not clever coordination.
- Handoff cost is roughly **fixed per delegation** (brief in, report out).
  Delegation pays only when the tokens the worker absorbs outweigh it. A short
  task below that break-even is cheaper and better done in the main thread.
- **Cache behaviour punishes churn.** A fresh worker pays cache *writes*; a
  continued one pays *reads*. For repeat work against the same material, continue
  an existing agent (`SendMessage` with its id/name) rather than spawning a new one.

### Do not delegate when

- You already know the file and the symbol — just read it.
- The task needs the conversation's shared context more than it needs isolation
  (and a `fork` would be too expensive to be worth it).
- Steps are tightly chained, each depending on the last — that is a pipeline, and
  a single agent runs it cheaper and more reliably than a relay of briefs.
- The orchestrator will need the raw bytes anyway, e.g. it must make the edit itself.
- It is most ordinary coding work. Multi-agent wins on *parallel, independent*
  threads; coding is usually neither.

## Parallelism

Anthropic's own scaling guidance, which transfers directly:

| Task shape | Agents | Tool calls each |
|---|---|---|
| Simple fact-finding | 1 | 3–10 |
| Direct comparison | 2–4 | 10–15 |
| Broad, genuinely independent threads | 10+ | divide responsibilities explicitly |

Launch independent agents **in a single message** so they run concurrently.
Partition by a real seam — file, module, provider, environment — so two workers
cannot duplicate each other. Default ceilings: 20 concurrent subagents, and
subagents may nest up to 3 layers below the main conversation (both adjustable
via `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` / `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`;
older builds capped nesting at 1 — do not assume nesting without checking).

## Orchestrator discipline

- **Never run a search you have already delegated.** Wait for the report.
- **Never predict a pending agent's result.** If the user asks before it lands,
  say it is still running.
- **Reports are evidence, not truth.** A subagent on a cheaper model can be
  confidently wrong. Before anything irreversible, verify the specific claim
  yourself — one targeted read beats trusting a summary.
- **Relay, don't dump.** The agent's report is not shown to the user; state the
  conclusion in your own words.
- **You own the user.** Subagents cannot ask questions. Any ambiguity a worker
  surfaces comes back to you to resolve or to put to the user.
- **Drop the posture when it stops paying.** On a small, focused task, say so and
  work directly rather than performing orchestration.

## Handover points: when to hand the work to a fresh session

Delegation keeps the orchestrator's window clean *within* a session. The same
logic applies *across* sessions: a conversation that has finished one coherent
unit of work is carrying context the next unit will never reference. Anthropic's
guidance is to clear between tasks and to start a fresh session once a spec is
written, because "a clean session with a better prompt almost always
outperforms a long session with accumulated corrections". This posture
therefore includes a standing watch for **handover points**, and treats a fresh
session exactly as it treats a subagent: a worker that was not alive for this
conversation and needs a complete brief.

### What a handover point is — and is not

Trigger on the **state of the work**, never on a feeling that the context is
getting full. You cannot see context usage (`/context` is a user command, its
output is not in your window), the harness compacts automatically when it must,
and its own guidance is not to wrap up early or hand off mid-task on account of
length. Mid-task context pressure is the user's call via `/compact <focus>`,
not yours.

A handover point is one of these, and nothing else:

| Signal | Example |
|---|---|
| A deliverable left your hands | PR opened or updated; plan or ADR written and accepted; status doc saved |
| A slice boundary in a plan directory | slice `01` merged, slice `02` is a separate implementation with its own kick-off prompt |
| A hard dependency on something outside the session | waiting on a review, a deploy run, a merge, a product ruling, a teammate |
| A change of kind | research is done and implementation starts; implementation is done and a deploy/operator phase starts |
| The user said they are stopping | "that's it for today", "let's pick this up tomorrow" |

Not a handover point: you are in the middle of an edit, a test run, or a
delegated search; the next step depends on something you hold only in
conversation; the task was small enough that the posture itself should have
been dropped.

### What to do at one

1. **Say so in one line**, then **offer**. Default behaviour is to offer, not to
   write: "This is a coherent handover point (PR #N open, slice 01 done). Say
   `handoff` and I'll write the handoff doc and give you a kick-off prompt."
   Writing a document into the tree on every PR open is noise if the user
   intends to continue; the offer costs one line. If the user invoked this
   posture with **auto-handoff**, skip the offer and write.
2. **Write the handoff into the existing convention — never a new one.**
   Where that convention points depends on the profile: load the overlay
   first (see [Profile overlay](#profile-overlay)). Then, in order:
   - The work has a plan directory → update its `handoff.md`. Fill the four
     headings the `/core:plan-new` scaffold writes and add none of your own:
     **Bootstrap order**, **Locked decisions**, **Next slice**, **Resume
     prompt**. The state-as-of SHA, branch and worktree go under *Bootstrap
     order*; the kick-off prompt of step 3 goes under *Resume prompt*.
   - Otherwise → the overlay's **status skill** into the overlay's **status
     root**, updating in place where a status doc for the workstream exists.
   - Only if neither applies and the user asks for a note → promote the work
     to a plan directory (`/core:plan-new --dir`, into the overlay's **plans
     root**) so the handoff lands at the conventional `handoff.md` inside it,
     per `core:planning`. There is no `handoff-`-prefixed file at the plans
     root: the in-directory `handoff.md` is what replaced those ad-hoc
     siblings.
   - If the session is on a wif stream (`core:wif`), also record the
     handoff as the stream's next step so the dashboard shows it.
   The document is a **snapshot** (state as of a SHA, what is done, what is
   next, what is blocked, decisions locked and why), not a chat transcript.
   Update in place on repeat handoffs; keep the previous state line "for the
   record" below the current one. Leave it uncommitted unless the user's
   workflow commits handoffs; say which you did.
3. **Print a kick-off prompt** in a fenced block the user can copy, after
   `/clear` or into a new terminal — the same text that goes under the handoff
   doc's *Resume prompt* heading. It is a
   [delegation brief](#the-delegation-brief) addressed to your successor, and
   the same four parts apply — objective,
   boundaries, tools and sources, output — plus the two rules that matter
   because the successor was not here: paste in any result it depends on, and
   inline every binding constraint rather than pointing at a file it may not
   read. Concretely:
   - Objective: the next slice in one sentence.
   - Bootstrap order: the handoff doc first (absolute path), then 2–4 further
     documents in reading order, then the files to open. No more.
   - State: branch, worktree, SHA, open PR, what is deployed where.
   - Locked decisions the successor must not relitigate, one line each.
   - What not to touch, and the verification command that proves the slice.
   - "Re-invoke `/core:orchestrator-mode`" if the posture should carry over.
   Cap it at roughly 25 lines. If it needs more, the handoff doc is missing
   something; put it there and shorten the prompt.
4. **Stop.** Do not start the next slice in this session after offering the
   handover. If the user replies with new work instead of `handoff`, the offer
   lapses; do not repeat it until the next handover point.

### Why a document and not `--resume`

`claude --resume` reopens the same context, corrections and all; `/rewind` with
"summarize" compacts it in place. Both keep the session. A handoff doc plus
kick-off prompt is the only form that gives the successor a *clean* window,
survives a machine change, and can be read by a teammate or a different agent.
Use resume when the accumulated context is the asset; hand off when it is the
liability.

## Profile overlay

Everything above is profile-neutral except *where* handoffs land. That comes
from one overlay per profile, loaded only when a handover is written:

```bash
p=$(basename "${CLAUDE_CONFIG_DIR:-}" | sed -n 's/^\.claude-//p')
[ -n "$p" ] || p=$(wif where --json 2>/dev/null | jq -r '.account // empty')
```

Load `references/profile-<p>.md` (`forestrie`, `justgames`, `personal`,
`home`); with no match, use
[references/profile-default.md](./references/profile-default.md). The overlay
names the status skill, status root and plans root. The active profile's
`CLAUDE.md` planning params win over the overlay if they disagree. Never
apply another profile's overlay: its roots and skills are not installed here.

## Making it durable

For a posture that survives across sessions, write the agent definitions to disk
rather than re-deriving them: see [reference.md](./reference.md).
