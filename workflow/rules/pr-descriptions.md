---
description: PR descriptions must be self-contained — introduce and link every
  term, id or decision before using shorthand for it. Cross-scope, always-on
  when creating or editing a pull request.
---
# PR descriptions are self-contained

## Standing principle

Write the description for a reader who is **generally familiar with the
project or repo's domain but not involved in the detail of the current
plans**: a reviewer from an adjacent repo, a future reader of `git log`, or
Robin a week later. That reader knows what a checkpoint or a grant is; they
do not know what "D2" or "slice 04" refers to, and should not have to open
a plan to find out. Everything below serves this principle.

## Rule

1. **Introduce before you abbreviate.** The first time the description
   names a decision, section, issue, error, flag or file, spell out what it
   is and link it (per [clickable-references.md](./clickable-references.md)).
   Only after that may shorthand appear. "D2 withdrawn" is fine once the
   reader has been told that D2 is the chain-semantics decision in ADR-0066
   and where to find it; on its own it is a puzzle.
2. **Say what changed in words, then where.** Lead with the behaviour or
   rule that is different after the merge, in one or two plain sentences.
   Then list the edits. A reader should be able to stop after the first
   paragraph and know what the PR does.
3. **No lists of bare identifiers.** A run like "D1, D3, D4, D5, D8 revised;
   D2 withdrawn; label −65932 withdrawn" is an index, not a description.
   Either expand each item to a clause that says what it now means, or
   group them under one sentence that states the common change and link
   the document that enumerates them.
4. **Every reference reachable in one click.** Plan slices, ADR sections,
   review folders and handoff files are not reachable from GitHub unless
   linked; local-only paths get a note saying so. If the authoritative text
   lives in another PR, link that PR and say what to read there.
5. **Companion PRs are named and linked**, with one clause each on what
   they carry, so the set can be reviewed in order.

## Why

Robin, 2026-09-20: "The standing principle is that the PR description
should be easily consumable by a reader generally familiar with the project
and/or repo domain but not specifically involved in the detail of the
current plans."

Robin, 2026-09-20, on a PR body that opened with "D1 revised, D2 withdrawn,
D3 one label": "creating PR descriptions with abbreviations and hard to
reach references … results in descriptions that are unnecessarily hard to
follow. It is fine to use shorthand like this *after* the terms are
introduced and linked; ideally the PR description would be self contained."

## Checklist before `gh pr create` / `gh pr edit`

- [ ] First paragraph states the change in plain words, no ids.
- [ ] Every id (Dn, Pn, Un, FOR-nnn, ADR-nnnn, slice nn) is expanded and
      linked on first use.
- [ ] No bullet is only identifiers.
- [ ] Every path or document a reviewer needs is a link, or flagged as local.
- [ ] Companion PRs linked with a clause each.

The same applies to commit bodies that will become squash-merge messages.
