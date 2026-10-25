# review-feedback — glossary

The language of the `review-feedback` skill: the loop that watches a pull
request Robin owns, acts on what reviewers and bots say, and asks for another
look when everything has an answer.

## Language

**Feedback**:
What a pull request has received since the last commit the skill pushed:
every unresolved review Thread, plus review bodies and plain comments by
anyone but the author. Failing checks are not Feedback.
_Avoid_: comments (too narrow), review (one kind of Feedback)

**Thread**:
One inline review conversation on the pull request, with a resolved state
that GitHub keeps. A Thread is the unit of Feedback that is fixed, refuted or
deferred, and its resolved state is the Ledger.
_Avoid_: comment chain, discussion

**Finding**:
The claim one piece of Feedback makes about the change. A Finding gets
exactly one Verdict.
_Avoid_: issue (a tracker item), nit, suggestion (a kind of Finding)

**Verdict**:
The skill's decision about a Finding: *Fix*, *Refute*, *Defer*, or *Rejected
fix*. Fix and Defer are acted on and their Threads resolved; Refute and
Rejected fix leave the Thread open and, for a human reviewer, are drafted
for Robin rather than posted.
_Avoid_: triage (the act of reaching a Verdict), status

**Fix**:
The Verdict for a Finding that is correct about the code as it stands and
whose remedy lies within the pull request's Plan and Design. The remedy is
one commit, named in the reply.

**Refute**:
The Verdict for a Finding that is wrong about the code, or asks for what a
recorded decision rules out. Posted autonomously for a bot; drafted for a
human.

**Defer**:
The Verdict for a Finding that is correct but belongs outside this pull
request. It becomes a Tangent with a tracker Issue, and the reply names it.

**Rejected fix**:
The Verdict for a Finding that is correct but whose every in-scope remedy is
a Workaround or breaks a rule of the road. Nothing is changed; the
explanation is drafted for Robin.

**Workaround**:
A change that satisfies a Finding without changing the behaviour the Finding
is about: a suppressed warning, a widened type, a special-cased test, a
caught-and-ignored error. Never a Fix.
_Avoid_: hack, patch

**Plan and Design**:
The documents the pull request answers to — its plan, the decisions recorded
there and in the repository's ADRs and rules of the road. The boundary a Fix
must stay inside.

**Overlay**:
The per-Scope part of the skill: which standards to apply, which tracker and
team, which bots to expect, where the Scope's checkouts live. One file per
Scope inside the skill; the Scope is the working directory's, as wif resolves
it.
_Avoid_: profile (an Account's config dir), config

**Ledger**:
Where "already handled" lives: the Threads' resolved states on GitHub, with
each reply naming the commit or Issue that handled it. The skill keeps no
private record of Findings.
_Avoid_: state file, cache

**Blocked re-review**:
The condition in which a drafted Verdict (a human Refute or a Rejected fix)
awaits Robin: the skill does not request re-review until every draft is
posted or overridden.

**Re-review request**:
Asking the reviewers whose Threads were fixed or refuted, and anyone whose
review decision is "changes requested", to look again. Reviewers who
approved without Findings are not asked; bots re-run on push and are never
asked.

**Tick**:
One pass of the loop: refresh this container's pull-request state through
wif, and act only if it changed. Shares wif's meaning of the word.
