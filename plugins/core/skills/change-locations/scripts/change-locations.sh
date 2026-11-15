#!/usr/bin/env bash
# Prints one table row per git worktree under the given paths that holds changes not yet merged:
# uncommitted changes, or commits ahead of the default branch whose PR has not merged. The
# definition is the worktree-row clause of agentfiles rules/expand-abbreviated-references.md.
# Read-only: git status, rev-list and `gh pr list`.
set -uo pipefail

usage() {
  echo "usage: change-locations.sh [--header] PATH..." >&2
  echo "  PATH is a worktree, or a directory searched two levels down (a herdr container or root)." >&2
  exit 2
}

header=0
paths=()
for a in "$@"; do
  case "$a" in
    --header) header=1 ;;
    -h | --help) usage ;;
    *) paths+=("$a") ;;
  esac
done
[ "${#paths[@]}" -gt 0 ] || usage

worktrees() {
  local p=$1 d
  if git -C "$p" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$p" rev-parse --show-toplevel
    return 0
  fi
  for d in "$p"/*/ "$p"/*/*/; do
    if [ -e "${d}.git" ]; then git -C "$d" rev-parse --show-toplevel; fi
  done
  return 0
}

# Prints "<reference>\t<branch>\t<path>" for an active worktree, nothing otherwise.
row() {
  local wt=$1 url slug repo clone branch dirty base b ahead=0 state ref
  url=$(git -C "$wt" remote get-url origin 2>/dev/null || true)
  slug=$(printf '%s' "$url" | sed -E 's#^(git@[^:]+:|[a-z+]+://[^/]+/)##; s#\.git$##')
  repo=${slug##*/}
  clone=$(basename "$wt")
  [ -n "$repo" ] || repo=$clone
  branch=$(git -C "$wt" branch --show-current)
  dirty=$(git -C "$wt" status --porcelain | wc -l | tr -d ' ')
  base=$(git -C "$wt" symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || true)
  if [ -z "$base" ]; then
    for b in origin/main origin/master; do
      if git -C "$wt" rev-parse -q --verify "$b" >/dev/null; then base=$b; break; fi
    done
  fi
  if [ -n "$base" ]; then ahead=$(git -C "$wt" rev-list --count "$base..HEAD"); fi
  if [ "$dirty" -eq 0 ]; then
    [ "$ahead" -gt 0 ] || return 0
    # A squash merge leaves the branch's commits ahead of the default branch, so the PR decides.
    if [ -n "$branch" ] && [ -n "$slug" ] && command -v gh >/dev/null; then
      state=$(gh pr list -R "$slug" --head "$branch" --state all --json state --jq '.[0].state // ""' 2>/dev/null || true)
      [ "$state" != MERGED ] || return 0
    fi
  fi
  ref=$repo
  [ "$clone" = "$repo" ] || ref="$repo (clone: $clone)"
  printf '%s\t%s\t%s\n' "$ref" "${branch:-detached}" "$wt"
}

rows=$(for p in "${paths[@]}"; do worktrees "$p"; done | sort -u | while IFS= read -r wt; do row "$wt"; done)
if [ -z "$rows" ]; then
  echo "No worktree with unmerged changes."
  exit 0
fi
dups=$(printf '%s\n' "$rows" | cut -f1 | sort | uniq -d)
[ "$header" -eq 0 ] || printf '| Reference | What it is |\n|---|---|\n'
printf '%s\n' "$rows" | while IFS=$'\t' read -r ref branch wt; do
  if [ -n "$dups" ] && printf '%s\n' "$dups" | grep -qxF -- "$ref"; then ref="$ref ($branch)"; fi
  printf '| `%s` | `%s` |\n' "$ref" "$wt"
done
