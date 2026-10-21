---
name: research-brief
description: Produce a research brief on a question that needs several sources compared and synthesised, with every claim traceable to a source. Use for technology choices, standards and specification questions, market or ecosystem surveys, and personal research that should outlive the chat.
when_to_use: The user asks to "research", "compare options", "survey the ecosystem", "what is current best practice", or wants a written brief rather than a chat answer.
argument-hint: "<question> [--out <path>]"
allowed-tools: Read, Write, Glob, Grep, WebSearch, WebFetch
---

# /research-brief — a brief that cites its sources

Deliver a **brief**, not a transcript of searching. The reader knows the
domain but has not done the reading; every non-obvious claim carries a link.

## Steps

1. **Frame** the question in one sentence and list the 3–6 sub-questions a
   decision needs answered. Confirm with the user only if the framing changes
   what you would search for.
2. **Gather** with web search first in `standard` mode; switch to `extended`
   only when a result is thin, off-target or possibly stale. Prefer primary
   sources (specs, official docs, source code, first-party announcements) over
   secondary summaries. Record for each source: URL, date, and what it
   establishes.
3. **Triage**: drop sources that only restate another; flag disagreements
   between sources explicitly rather than averaging them.
4. **Write** using [templates/brief.md](templates/brief.md). Keep the
   executive answer to five sentences. Put the comparison in a table. End with
   "what would change this conclusion".
5. **Save** to the path the user gave, else `docs/research/<yymmdd>-<slug>.md`
   in the current repo if there is one, else print it.

## Rules

- No claim without a source; no source without a date.
- Quote numbers and version strings exactly; do not round.
- Separate "verified by running it" from "reported by a source".
- When the question is about an LLM or agent product, check the vendor's
  own docs before any blog post, and say which page you used.
