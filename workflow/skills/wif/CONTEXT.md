# wif — work in flight

The language of the `wif` skill: a tracker for the many concurrent workstreams
Robin runs across two Claude accounts and several herdr worktrees. It exists so
a session can always answer "which stream am I in, what is this session for,
what was the last prompt for, and where does that sit in the stream".

## Language

**Account**:
One Claude Code identity (justgames or personal). An Account owns exactly one
Ledger root.
_Avoid_: profile, login, config

**Scope**:
The agentfiles routing unit derived from the working directory (`justgames`,
`forestrie`, `personal`). An Account serves one or more Scopes; a Scope is
never served by two Accounts.
_Avoid_: project, workspace, environment

**Ledger**:
The on-disk record of every Stream an Account knows about, kept per Scope under
the Account's config dir. The Ledger is the only state `wif` owns.
_Avoid_: database, registry, state file

**Stream**:
One workstream in flight: a unit of work with a goal, a Position and a next
action, backed by one Container or checkout. A Stream has exactly one file in
the Ledger and exactly one Status.
_Avoid_: ticket, branch, workspace (each of those is a Backing of a Stream, not the Stream)

**Status**:
Where a Stream is in its life: *active* (being worked), *parked* (deliberately
paused by Robin), *blocked* (waiting on something external), *landed*
(delivered; awaiting closeout), *closed* (its Backing is gone or retired).
Only Robin parks; tooling may propose landed, never set it.
_Avoid_: state, phase, done, complete

**Container**:
A herdr task directory under `.worktrees-herdr/`: the default Backing, and the
source of a Stream's id. herdr calls it a *task*; `wif` accepts that word on
the command line and nowhere else.
_Avoid_: task (in prose), workspace, worktree (a Container *holds* worktrees)

**Untracked**:
A Container with no Stream file yet. Shown so it can be adopted or parked;
never silently promoted.

**Backing**:
The concrete thing a Stream is attached to: a Container, or a plain repo
checkout on a branch. A Stream has exactly one Backing.
_Avoid_: source, origin

**Parent**:
An optional grouping key on a Stream — a Linear issue, plan id or topic — that
relates sibling Streams (e.g. three herdr tasks for one issue). A Parent is a
label, not a Stream.
_Avoid_: epic, umbrella

**Session**:
One Claude Code conversation, bound to exactly one Stream by its working
directory. A Session has a Session goal and an Intent ring; it is folded into
its Stream at Handoff. Many Sessions may be live on one Stream.
_Avoid_: conversation, chat, window

**Session goal**:
What this Session is for, in one line. Inferred from the first substantive
prompt unless set explicitly.

**Intent**:
What one prompt is for, in one line, with the Position it belongs to. Inferred
by the model for prompts that start a unit of work; follow-ups inherit the
current Intent. Robin's explicit statement overrides the inference.
_Avoid_: task, step (Position), request

**Intent ring**:
The bounded, most-recent-first list of Intents in a Session, with the first
line of each prompt and of each outcome recorded mechanically.
_Avoid_: log, history

**Position**:
Where a Stream currently is: the active slice of its plan when a plan exists,
else free text.
_Avoid_: progress, phase, stage, step

**Slice**:
One phase of a Stream's plan, numbered within the plan ("slice 2 of 3"). The
unit Position points at.
_Avoid_: step, stage, milestone

**Handoff**:
The act of folding live Session state into the Stream and the existing
handoff conventions, ending with a paste-ready Kickoff. "Landing the plane".
_Avoid_: checkpoint, wrap-up, save

**Kickoff**:
The short prompt a fresh Session starts from after a Handoff: objective,
bootstrap order, state, locked decisions, what not to touch.
_Avoid_: handoff doc, summary

**Rotation**:
Handing off and clearing a Session because its context is nearly full, rather
than because the work reached a boundary.
_Avoid_: compaction (that is what Claude Code does on its own), reset

**Tick**:
One pass of the looped overview: rescan, report what changed, check for
Rotation.
_Avoid_: poll, heartbeat, iteration

**Flag**:
A fact about a Stream or Container that tooling can observe (stale, dirty,
unpushed, unpublished, no-remote, landed?, over-cap, bad-status). A Flag is
evidence for a Status change, never a Status.
_Avoid_: warning, badge, state

**Note**:
A one-line thought captured against a Stream mid-flight without acting on it.
A Note has exactly one kind: Followup, Tangent or Reminder. Notes live in the
Stream and survive Handoff.
_Avoid_: todo, comment, memo

**Followup**:
A Note about work that belongs to *this* Stream but not to the current
Intent. The default kind.

**Tangent**:
A Note about work that does *not* belong to this Stream: a candidate for a new
Stream, recorded with the Stream it was discovered from.
_Avoid_: side quest, spin-off, idea

**Reminder**:
A Note with a trigger — a date, or the event "this Stream lands" — that the
dashboard surfaces when the trigger is met.
_Avoid_: alarm, alert, nudge

**Unbound memory**:
An auto-memory directory of the Account that matches no Container. Reported as
a candidate; it never becomes a Stream on its own.
