---
name: decision-map
description: Turn the decisions of a planning, design or implementation session into a thematic decision log and an interactive graph canvas. Each decision is grouped by design area and traced to the parts of the system it shapes, with superseded and amended links, a contradiction check and the open questions that check raises. The log lands where the active profile (forestrie, justgames, personal, home) keeps plan documents; the canvas is published as a private Artifact, or written as a local HTML file where there is no Artifact tool. Use when Robin asks for a decision log, decision map, decision tree or decision canvas, asks to turn the session's decisions into something visual, or when a grill or design session closes and its decisions should be recorded.
argument-hint: "[<plan dir>] [--update <canvas url or html>]"
---

# decision-map

```
/core:decision-map                     map this session's decisions; log into the current plan
/core:decision-map <plan dir>          log into that plan directory
/core:decision-map --update <url>      re-read an existing canvas, change it, republish to the same URL
```

One JSON data file produces both outputs, so they cannot drift:

| Output | What it is | Where |
|---|---|---|
| `decisions.md` | The durable log: one table per design area, then open questions and the contradiction check | The profile overlay's log home, normally the plan directory |
| Canvas | One HTML page: the graph (decisions by area, linked to the parts they shape; dashed arcs from a superseded decision to its replacement), a detail rail, the log, and the wrap-up | A private Artifact; else a local file |

The builder is `${CLAUDE_SKILL_DIR}/scripts/build.py` (Python 3.9+, stdlib only). The data format is
[references/data-format.md](./references/data-format.md). Origin: [PROVENANCE.md](./PROVENANCE.md).

## 1. Profile overlay

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/build.py profile
```

It reads `CLAUDE_CONFIG_DIR` (`~/.claude-<profile>`), falls back to the wif account, and prints the
overlay to load: `references/profile-<p>.md` for `forestrie`, `justgames`, `personal` or `home`, else
[profile-default.md](./references/profile-default.md). Load that file now and follow it for the log
home, ids, linting, commits and publishing. Never apply another profile's overlay.

## 2. Collect the decisions

Gather from, in order: the conversation (rulings, `Re <n>` answers), the session's grill or decision
record, the plan README's locked decisions, and the ADRs, ARCs or slice docs the session changed.

- Record only what was decided. A recommendation Robin has not ruled on is `proposed`.
- Keep every superseded decision, with what replaced it, so it is not reopened.
- Keep the session's own ids (`Q7`, `R-3`). Give a decision settled outside the numbered series a
  short letter id (`V1`) and say where it came from in its text.
- `text` states the decision as it stands now, in one to three plain sentences. For a superseded
  decision, say what it was and what replaced it.
- `lands` names where the decision is, or will be, recorded: a doc section, an ADR, a plan slice.

## 3. Organise by design area

- **Themes**: 4 to 8 design areas named by design concern ("Payment binding and replay"), never by
  repo, owner or chronology. Every decision belongs to exactly one. Order them from foundations to
  consumers. Each has a one-line blurb.
- **Components**: 8 to 20 parts of the system, named as a reader recognises them, grouped into 3 to 6
  layers (on chain, services, tooling, third parties…).
- **Impacts**: the parts a decision changes or constrains, not every part it mentions. A superseded
  decision has none; its arc shows the replacement.
- **Pivot** (optional): the one decision that reshaped the most others, with one sentence on why.

## 4. Check for contradictions

Walk every pair of decisions that shape the same component, and each decision against the documents
it lands in:

- settled because one replaced the other → a `resolved` line;
- a live conflict, or a gap the decisions leave open → an `open` question extending the session's
  numbering, with context and a recommendation;
- text in a doc that predates a decision → a `fold` line.

Check the decisions against any standard or spec they adopt, too. The wrap-up is the part reviewers
read first, so don't skip it.

## 5. Build

Keep the data file in the session scratchpad, not in the repo: the canvas embeds it, and
`build.py extract` recovers it.

```bash
B=${CLAUDE_SKILL_DIR}/scripts/build.py
python3 $B init > <scratch>/decisions.json            # skeleton; replace every example value
python3 $B check <scratch>/decisions.json             # fix every error it lists
python3 $B build <scratch>/decisions.json --html <scratch>/<slug>-decisions.html --md <scratch>/decisions.md
```

`meta.title` is the page's name: a specific noun phrase such as "Delegated Spend Decisions", not
"Decision map".

## 6. Publish the canvas

- **Artifact tool present** (and the overlay allows it): the template already meets the page contract
  (title, theme tokens, both themes, phone width). For a new canvas follow the Artifact tool's rules
  for a new page first (its quickstart), then publish the HTML file with `icon: "graph"` and a
  one-sentence `description`. Republish from the same file path to keep the URL.
- **No Artifact tool**: give the HTML file's absolute path; it opens in any browser.

## 7. Write the log

Rebuild with `--canvas-url <url>` so the log links the canvas, then copy `decisions.md` to the
overlay's log home. Link it from the plan README where the plan lists its decisions. Lint and commit as
the overlay says; push or open a PR only when the overlay or Robin allows it.

## 8. Report

In chat:
- the counts by status;
- the pivot;
- the contradiction check;
- the new open questions as a table of question and recommendation;
- links to the canvas and the log.

Robin's standing reference rules apply: a References table for every short reference, and
clickable paths.

## Updating an existing map

1. Read the canvas: the Artifact tool's `read` action on its URL, or the local file.
2. `python3 $B extract <html> > <scratch>/decisions.json`.
3. Change statuses, add decisions or close open questions. Never delete a superseded decision.
4. Rebuild, republish to the same URL (`url` from another session), and rewrite the log.
