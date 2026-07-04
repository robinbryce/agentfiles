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

**Allocation** (what `/plan-new` does): list `plans/plan-<YYMM>-*`, next
ordinal = highest in that month + 1, else `01`. Only the current month is
scanned — never the whole series.

### Larger plans: a named directory

Promote to a directory when the plan needs phases, an agent handoff, several
sub-docs, or spans more than one session:

```
plans/plan-2607-03-release-promotion/
  ├── README.md            # overview + index + status ("plan of plans")
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
status breaks every reference to it.

```yaml
---
id: 2607-03
status: active        # draft | active | blocked | superseded | complete
created: 2026-07-04
refs: [ADR-0043, ARC-0024, FOR-314]   # decisions / issues this plan serves
supersedes: 2606-07   # optional
---
```

Keep an annotated `README.md` index in each `plans/`, `adr/`, `arc/` dir.

---

## Migration policy — forward-only

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
| `decisions_home` | where ADR/ARC live | repo `docs/{adr,arc}/` |
| `id_scheme.plans` | plan id scheme | date-cohort |
| `id_scheme.decisions` | ADR/ARC id scheme | absolute |
| `issue_refs` | issue tracker prefix for `refs:` | none |

See [templates/](./templates/) for the file and directory-README scaffolds,
and [`/plan-new`](../commands/plan-new.md) for automated allocation.
