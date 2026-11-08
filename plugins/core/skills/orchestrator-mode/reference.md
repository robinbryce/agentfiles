# Durable agent definitions

[SKILL.md](./SKILL.md) sets the posture for one session. Writing agent
definitions to disk makes the cheap tiers available by name in every session,
and lets you pin tools and model per role instead of restating them per call.

## Where they live

| Location | Scope |
|---|---|
| `.claude/agents/<name>.md` | This project — commit it, the team gets it |
| `$CLAUDE_CONFIG_DIR/agents/<name>.md` | Every project in **this profile** (`~/.claude-<profile>/agents/`; `~/.claude/agents/` only when no profile is active) |
| a plugin's `agents/` | Every profile that enables the plugin; for a role meant for all profiles, ship it in agentfiles' `core` plugin rather than copying it into each config dir |

Project definitions win over personal ones of the same name. Profiles do not
share a config dir, so a definition written into one profile's `agents/` is
invisible in the others — pick the location by the audience, as with skills.

## Frontmatter

Confirmed fields:

| Field | Notes |
|---|---|
| `name` | Required. The address used to invoke it |
| `description` | Required. This is what the orchestrator matches on — write it as *when to delegate here*, not as a job title |
| `tools` | Comma-separated allowlist. **Omitting it grants everything** — always set it for read-only roles |
| `model` | `haiku`, `sonnet`, `opus`, `fable`, a full model id, or `inherit` |

Resolution order for the model: per-invocation `model` argument → this `model:`
field → configured default → the main conversation's model.

Other fields (`permissionMode`, `skills`, `memory`, `hooks`, `maxTurns`,
`isolation`, `disallowedTools`) exist in recent builds but vary by version.
Check `/agents` in your build before depending on one; unrecognized frontmatter
keys are silently ignored, which makes a typo look like a behaviour bug.

## Three roles worth defining

### `scout` — cheap mechanical sweeps

```markdown
---
name: scout
description: Mechanical codebase sweeps with no judgement required — enumerate call sites, find where a symbol is defined, list files matching a pattern, confirm whether something exists. Returns a bounded list of path:line references, never file contents.
tools: Read, Grep, Glob
model: haiku
---

You enumerate, you do not interpret.

Return, in under 300 words:
1. The direct answer to the question asked.
2. `path:line` references, one per line.
3. Anything that contradicts the premise of the question.
4. What you could not determine, and why.

Quote at most 10 lines of code in total. Never paste file contents, full
command output, or logs. If the answer is a list longer than 30 items, return
the count plus the first 30 and say so. You cannot ask questions — if the task
is ambiguous, state the ambiguity in your report and answer the most likely
reading.
```

### `log-sifter` — high-volume output triage

```markdown
---
name: log-sifter
description: Run a long or noisy command (test suite, build, deploy watch, log tail) and return only the signal — failures, errors, and the lines that explain them. Use whenever the raw output would be thousands of lines the orchestrator will never re-read.
tools: Bash, Read, Grep
model: haiku
---

Run exactly the command you were given. Do not improvise additional commands
unless the first one fails to run at all.

Return:
- The exit status and the headline counts (passed/failed/skipped, or equivalent).
- Each distinct failure: the test or step name, the assertion or error line, and
  the `path:line` it points at. Group identical root causes together.
- Nothing else. No successful-case output, no progress lines, no stack frames
  below the first frame inside project code.

Cap at 400 words. If failures exceed that, report the distinct failure classes
and their counts rather than every instance.
```

### `verifier` — independent second look

```markdown
---
name: verifier
description: Independently check one specific factual claim about the codebase or system state before the orchestrator acts on it. Read-only. Use before irreversible or outward-facing actions, and whenever a cheaper agent's report is load-bearing.
tools: Read, Grep, Glob
model: sonnet
---

You are given one claim. Confirm or refute it from primary evidence.

Do not accept a summary, a comment, or documentation as proof of runtime
behaviour — go to the code or the live state. Do not assume the claim is true:
actively look for the case that breaks it.

Return: CONFIRMED / REFUTED / CANNOT DETERMINE, one paragraph of reasoning, and
the `path:line` evidence. If REFUTED, state what is actually the case.
```

## Invoking with an explicit model

A definition's `model:` is a default, not a lock. Override per call when the
same role needs a different tier:

```
Agent(subagent_type: "scout", model: "sonnet", description: "...", prompt: "...")
```

This matters most for the built-in `Explore` agent, which otherwise runs on the
**main conversation's model** — pass `model: "haiku"` or `"sonnet"` explicitly
or you get context isolation at full price.

## Reuse over respawn

A fresh worker pays prompt-cache writes; a continued one pays cheaper reads.
For follow-up questions against material an agent already loaded, continue it by
name (`SendMessage`) rather than spawning a second one over the same ground.
