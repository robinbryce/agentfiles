# wif — work in flight

The language of the `wif` skill: a tracker for the many concurrent workstreams
Robin runs across two Claude accounts and several herdr worktrees. It exists so
a session can always answer "which stream am I in, what is this session for,
what was the last prompt for, and where does that sit in the stream".

## Language

**Account**:
One Claude Code identity, selected by `CLAUDE_CONFIG_DIR` (`~/.claude-justgames`
or `~/.claude-personal`). An Account owns exactly one Ledger root.
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
One workstream in flight: a unit of work with a goal, a current position and a
next action, usually backed by one herdr task. A Stream has exactly one file in
the Ledger.
_Avoid_: task, ticket, branch, workspace (each of those is a *backing* of a Stream, not the Stream)

**Backing**:
The concrete thing a Stream is attached to: a herdr task container (the
default, and the source of the Stream's id), or a plain repo checkout on a
branch (id `<repo>--<branch>`). A Stream has exactly one Backing.
_Avoid_: source, origin

**Parent**:
An optional grouping key on a Stream — a Linear issue, plan id or topic — that
relates sibling Streams (e.g. three herdr tasks for one issue). A Parent is a
label, not a Stream.
_Avoid_: epic, umbrella

**Session**:
One Claude Code conversation, bound to exactly one Stream (inferred from the
working directory, overridable). A Session has a Session goal and an Intent
ring; it is folded into its Stream at Handoff. Many Sessions may be live on one
Stream.
_Avoid_: conversation, chat, window

**Session goal**:
What this Session is for, in one line. Inferred from the first substantive
prompt unless set explicitly.

**Intent**:
What one prompt is for, in one line, with the Position it belongs to. Inferred
by the model for prompts that start a unit of work; follow-ups inherit the
current Intent. An explicit `mark` overrides the inference.
_Avoid_: task, step (Position), request

**Intent ring**:
The bounded list (last ten) of Intents in a Session, with the first line of
each prompt and of each outcome recorded mechanically by hooks.
_Avoid_: log, history

**Position**:
Where a Stream currently is: the active slice of its plan when a plan dir
exists, else free text. Rendered as "step n of m" only when the plan gives m.
_Avoid_: progress, phase, stage

**Handoff**:
The act of folding live Session state into the Stream file and the existing
handoff conventions (plan `handoff.md`, `/save-status`, auto memory), ending
with a paste-ready kickoff prompt. "Landing the plane".
_Avoid_: checkpoint, wrap-up, save

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
Stream, recorded with the Stream it was discovered from. Promoted with `start`.
_Avoid_: side quest, spin-off, idea

**Reminder**:
A Note with a trigger — a date, or the event "this Stream lands" — that the
dashboard surfaces when the trigger is met.
_Avoid_: alarm, alert, nudge

**Unbound memory**:
An auto-memory directory in the Account's config dir whose sanitized cwd matches
no Stream Backing. Scan reports these as candidates; they never become Streams
on their own.
