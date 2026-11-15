---
name: change-locations
description: Print just the repo rows of the References table, one per worktree with unmerged changes for the current work, the repo (and the clone's directory name when it differs) beside the absolute working directory, so Robin can point external diff tooling at work in progress. Use when Robin runs /core:change-locations or asks where the changes are or which worktrees to diff.
argument-hint: "[worktree, herdr container or herdr root ...]"
allowed-tools: Bash
---

# /change-locations

Prints only the worktree rows that close every response's References table, under the rule
`expand-abbreviated-references` (agentfiles `rules/`), which defines them: a worktree this
session, or a lane or agent it started, works or has worked in, with changes not yet merged.

## Steps

1. **Candidates.** The paths in `$ARGUMENTS`. With none, every worktree this session or its lanes
   and agents have worked in, as the conversation shows: the working directory, herdr task
   containers, and worktrees named in tool calls. A herdr container
   (`.worktrees-herdr/<task>`) or herdr root (`.worktrees-herdr`) may be passed as it is: the
   script searches two levels down.
2. **Run** `${CLAUDE_SKILL_DIR}/scripts/change-locations.sh --header <paths...>`. It is read-only:
   `git status`, `git rev-list` against the default branch, and `gh pr list` for a clean branch
   with commits ahead, because a squash merge leaves those commits ahead.
3. **Reply** with its output and nothing else: no expansion rows, no prose. When it prints
   `No worktree with unmerged changes.`, reply with that line.
