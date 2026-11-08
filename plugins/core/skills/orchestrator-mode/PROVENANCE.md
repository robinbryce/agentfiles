# Provenance

- **Origin:** copied 2026-11-08 from
  [SentientDogs/just-agents](https://github.com/SentientDogs/just-agents)
  `skills/orchestrator-mode` at `1eab7e8` (2026-10-06), Robin's own work.
  Changed here: the handover routing no longer hard-codes just-agents'
  `agent-archive/status/` and `workflow/` links; per-profile roots moved to
  `references/profile-*.md`; `reference.md` names the profile config dir
  instead of `~/.claude`; invocations are `/core:…`. The routing policy,
  brief contract, economics and handover triggers are unchanged. Upstream
  edits are not synced automatically: re-diff against just-agents when it
  changes.
- **License:** no package-local `LICENSE` is pinned, because no third-party
  payload is redistributed. The skill carries the repository's own terms.
- **Compatibility:** Agent Skills-compatible harnesses that discover package
  directories containing `SKILL.md`. The behavioural policy is harness-agnostic;
  the mechanics it names (per-invocation model override, `.claude/agents/`
  definitions, built-in `Explore` / `Plan` agents, `fork`, concurrency and
  nesting limits) are **Claude Code specific** and version-dependent — see the
  caveats in [reference.md](./reference.md).

## Payload inventory

| Path | Role |
| --- | --- |
| `SKILL.md` | Session posture and routing policy |
| `reference.md` | Durable `.claude/agents/` definitions for the cheap tiers |
| `references/profile-*.md` | Per-profile handoff destinations (status skill, status root, plans root) |

## Sources consulted

Research behind the policy, as of 2026-10-02:

- Anthropic, *How we built our multi-agent research system* —
  <https://www.anthropic.com/engineering/multi-agent-research-system>
  (15x token multiplier; token spend explaining ~80% of eval variance; the
  objective / format / tools / boundaries brief contract; the 1 / 2-4 / 10+
  scaling table; the vague-brief duplication failure mode).
- Claude Code docs, *Subagents* — <https://code.claude.com/docs/en/sub-agents>
  (frontmatter fields, model aliases and `inherit`, model resolution order,
  built-in agents, `Explore` inheriting the main conversation's model).
- Claude Code docs, *Environment variables* — <https://code.claude.com/docs/en/env-vars>
  (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` default 20;
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` default 3, was 1 in v2.1.217-218).
- Claude Code docs, *Skills* — <https://code.claude.com/docs/en/skills>
  (`SKILL.md` frontmatter fields, `when_to_use`, description length budget).
- claudefa.st, *Multi-agent orchestration: the cost math* —
  <https://claudefa.st/blog/guide/development/multi-agent-orchestration-cost>
  (fixed per-handoff cost and break-even; cache writes at 1.25x vs reads at 0.1x
  favouring worker reuse over respawn).
- channel.tel, *Claude Code subagents and the orchestrator pattern* —
  <https://www.channel.tel/blog/claude-code-subagents-orchestrator-pattern>
  (context packets; bridging a dependency's output into the next brief;
  repeating binding rules inside the task description).

Handover-point section, added 2026-10-03:

- Claude Code docs, *Best practices* — <https://code.claude.com/docs/en/best-practices>
  ("Once the spec is complete, start a fresh session to execute it"; "a clean
  session with a better prompt almost always outperforms a long session with
  accumulated corrections"; `/clear` between unrelated tasks; `/compact
  <instructions>`; "Run `/context` to see what's using space" is addressed to
  the user, not the model).
- Claude Code docs, *How Claude Code works* — <https://code.claude.com/docs/en/how-claude-code-works>
  (automatic compaction clears older tool output first, then summarises;
  "Sessions are independent. Each new session starts with a fresh context
  window"; resume reopens the same session, fork copies it).
- Claude Code docs, *Skills* — <https://code.claude.com/docs/en/skills>
  ("Claude Code does not re-read the skill file on later turns, so write
  guidance that should apply throughout a task as standing instructions";
  combined `description` + `when_to_use` truncated at 1,536 characters; a rule
  that must hold every time belongs in a hook, not a skill).
- Anthropic, *Effective context engineering for AI agents* —
  <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
  (compaction and structured note-taking as the two long-horizon techniques;
  a note persisted outside the window survives a context reset).
- Conventions the section routes into rather than replacing: in agentfiles,
  `core:save-status` and the plan-directory `handoff.md` scaffold of
  `core:plan-new` / `core:planning`; per profile, the status skill and roots
  in `references/profile-*.md` (upstream, just-agents'
  `workflow/commands/save-status.md` and `workflow/rules/planning.md`).

**Not adopted:** a trigger on context fullness. The model cannot observe
`/context`, the harness compacts on its own, and its guidance is not to wrap
up early on account of length — so the section triggers on work state only.
Also not adopted: writing the handoff automatically by default; it is offered,
and written unasked only when the user invokes the posture with auto-handoff.

**Not adopted:** `CLAUDE_CODE_SUBAGENT_MODEL` / `..._FORCE`, which several
community guides present as the way to force every subagent onto one model. They
do not appear in the documented environment-variable reference, so the skill
routes per call and per definition instead.
