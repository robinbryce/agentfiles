---
name: planning
description: How plan, ADR, and ARC documents are named, numbered, and laid out: date-cohort plan ids, absolute ADR/ARC ids, frontmatter, and the forward-only migration policy. Scopes override the parameters.
when_to_use: Creating, renaming, or reorganising a plan / ADR / ARC document, or picking an id for one. The /plan-new skill applies this for you.
paths: ["**/plans/**", "**/docs/plans/**", "**/adr/**", "**/docs/adr/**", "**/arc/**", "**/docs/arc/**"]
user-invocable: false
---

# Planning & decision docs — organisation and numbering

Cross-scope **default** for how plan, ADR, and ARC documents are named,
numbered, and laid out. A scope may override the parameters (see
[Scope parameters](#scope-parameters)); the scheme itself is common.

> **When this applies:** load this rule whenever a task creates, renames, or
> reorganises a plan / ADR / ARC. The `/plan-new` command applies it for you —
> prefer that over hand-naming files.

---

## Two document classes, two id schemes

The classes have different lifecycles, so they get different ids:

| Class | Nature | Cited by stable id? | Id scheme |
|-------|--------|---------------------|-----------|
| **ADR / ARC** | Durable, curated, low-churn decisions & architecture | **Yes** (from plans, code, other ADRs) | **Absolute** `NNNN` |
| **Plan** | Churny, often agent-generated, spans a task/feature | Rarely | **Date-cohort** `YYMM-NN` |

Rationale: an absolute number's value *is* its stability, so ADR/ARC keep it.
Plans mostly race on allocation — two agents/branches both grabbing "the next
number" is why `plan-0030`, `plan-0033`, `adr-0023`, `adr-0042` already collide
in the wild. A month-scoped ordinal shrinks the allocation scan (and the
collision window) from all-history to the current month.

---

## Plans — date-cohort numbering

### Default: one file

```
plans/plan-2607-01-checkpoint-publisher.md
       │    │    │  └ slug (kebab-case, terse)
       │    │    └ ordinal within the month, zero-padded 2 digits (lexical sort)
       │    └ YYMM cohort — 2607 = July 2026
       └ type prefix (keeps plans / reviews / handoffs greppable & co-located)
```

**Allocation** (what `/plan-new` does): find every `plan-<YYMM>-NN` already
taken (the working tree including any `archive/`, origin's default branch
after a fetch, and open GitHub PRs), next ordinal = highest + 1, else `01`.
Only the current month's cohort counts, but it is checked against the
remote, so a stale clone cannot reuse an id. A scope whose docs repo is
governed by a dox schema repo (a `.dox.toml`, with `DOX_SCHEMA_REPO` set)
allocates through `dox new` instead; `/plan-new` dispatches to it, and the
schema, not this skill, then decides names, frontmatter and placement.

### Larger plans: a named directory

Promote to a directory when the plan needs phases, an agent handoff, several
sub-docs, or spans more than one session:

```
plans/plan-2607-03-release-promotion/
  ├── README.md            # the plan + slice index; the only file with frontmatter
  ├── 01-lane-b-gate.md    # phase / slice docs — local 2-digit, NOT date-based
  ├── 02-mandate-exemplar.md
  ├── handoff.md           # replaces ad-hoc *-agent-handoff.md siblings
  └── decisions.md         # optional
```

The directory occupies **one** month-ordinal slot. Promote a single file with:

```bash
git mv plans/plan-2607-03-x.md plans/plan-2607-03-x/README.md
```

---

## ADR / ARC — absolute numbering (unchanged, tightened)

- `adr-NNNN-<slug>.md` / `arc-NNNN-<slug>.md`, **strictly 4 digits** (retire
  stragglers like `arc-021`).
- **Reserve the id before writing** — one id, one document. The `adr-0023` /
  `adr-0042` dupes are latent reference bugs.
- For exploration/retrospective clusters use a **directory**
  (`arc-0014-long-lived-deployments/` with sub-docs) rather than
  `arc-0014-patterns.md` + `arc-0014-exploration.md` + …

---

## Frontmatter (all plan docs)

Status lives in **frontmatter, never in the id** — renaming a file to change
status breaks every reference to it. The `id` is the filename stem (the
directory name for a directory plan). No bold `**Status:**` header in the
body.

```yaml
---
id: plan-2607-03-release-promotion
title: Release promotion
status: active        # draft | active | blocked | complete | abandoned
created: 2026-07-04
updated: 2026-07-09
repos: [canopy, arbor]            # repos the work changes
issues: [FOR-314]                 # tracker issues it serves
refs: [ADR-0043, ARC-0024]        # decisions / docs it serves
outcome: [ADR-0050]               # on complete: durable docs produced,
                                  # or "none: <reason>"
---
```

Status snapshots (`status-YYMM-NN-<slug>`) use the same fields, the same
status values, and `plans:` for the plans they track.

This matches the forestrie `plan` and `status` schemas
(forestrie-agents `schemas/`), so a doc scaffolded here validates there.
Plans also carry a `## Rules check` section in scopes that keep rules files.

---

## Migration policy — forward-only (default)

A scope may replace this with a one-time normalisation (forestrie does,
under its ADR-0071).

Existing `plan-NNNN` files are **frozen legacy**; do not renumber them
(renumbering breaks cross-refs). New plans use the date cohort. Each `plans/`
`README.md` should carry a one-line banner:

> ids ≤ 2026-07 are legacy absolute (`plan-0001…`); ids ≥ `2607` are date
> cohorts (`plan-2607-01…`).

ADR/ARC are untouched except the 4-digit / one-id-per-doc tightening going
forward.

---

## Scope parameters

The scheme above is the default. A scope's `AGENTS.md` sets only what differs:

| Param | Meaning | Default |
|-------|---------|---------|
| `plans_root` | where plan docs live | repo `docs/plans/` |
| `status_root` | where status snapshots live | repo `docs/status/` |
| `decisions_home` | where ADR/ARC live | repo `docs/{adr,arc}/` |
| `id_scheme.plans` | plan id scheme | date-cohort |
| `id_scheme.decisions` | ADR/ARC id scheme | absolute |
| `issue_refs` | issue tracker prefix for `refs:` | none |

See [templates/](../plan-new/templates/) for the file and directory-README scaffolds,
and [`/plan-new`](../../skills/plan-new/SKILL.md) for automated allocation.
