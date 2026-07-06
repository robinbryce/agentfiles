---
description: Every file / line / PR / issue / commit reference in agent output
  must be a clickable link. Gitweb permalink for content in git; absolute path
  (ideally an editor URL) for local-only content. Cross-scope, always-on.
---
# Clickable references

Whenever output names a **file, line range, PR, issue, commit, or code
symbol**, render it as a **clickable link** — never as bare prose the reader
has to retype. This applies to chat replies, status/plan/ADR/ARC docs, PR
descriptions, and commit bodies alike.

The right link form depends on **where the referent lives**. There is no single
form that is simultaneously clickable, line-accurate, and runnable in another
terminal (see [Trade-offs](#trade-offs-no-form-wins-on-every-axis)); pick by
this decision order.

---

## Decision order

### 1. Committed **and** pushed to a forge → gitweb permalink (preferred)

Best all-round: clickable anywhere, carries a line range, portable to any
machine or teammate, and stable because it is **pinned to a commit SHA**.

```
https://github.com/<owner>/<repo>/blob/<SHA>/<path>#L<start>-L<end>
```

Derive it mechanically — do not hand-assemble:

```bash
slug=$(git remote get-url origin \
       | sed -E 's#^(git@[^:]+:|https?://[^/]+/)##; s#\.git$##')   # owner/repo
sha=$(git rev-parse HEAD)                                          # pin, not a branch
echo "https://github.com/$slug/blob/$sha/path/to/file.go#L42-L60"
```

Rules:
- **Pin to the SHA**, never `blob/main/…`. Branch links rot — lines shift, the
  target disappears on rebase. The whole value of a permalink is that it stays
  valid.
- The referenced lines **must exist at that SHA**. If the file is
  working-tree-modified (or untracked), HEAD line numbers are wrong → it is not
  yet "in git"; fall to step 2 (or commit first).
- GitLab / Gitea differ only in the path: GitLab uses `/-/blob/<SHA>/…`,
  self-hosted Gitweb CGI uses `?p=<repo>;a=blob;f=<path>;hb=<SHA>`. Read
  `origin` and match the host rather than assuming GitHub.
- **PRs / issues / commits:** link the object directly —
  `…/pull/<n>`, `…/issues/<n>`, `…/commit/<SHA>`. Prefer forge-native id syntax
  (`owner/repo#123`) in PR/commit bodies where the forge auto-links it.

### 2. Same-repo doc referencing same-repo content → relative markdown link

Inside a repo doc (status/plan/ADR), a **relative** link survives the repo
being moved, cloned, or browsed on the forge:

```markdown
see [planning rule](../rules/planning.md#frontmatter-all-plan-docs)
```

Use this over an absolute gitweb link when author and target sit in the same
repo — it stays correct on disk *and* renders as a link in the forge UI.

### 3. Local-only (uncommitted, untracked, outside any repo) → absolute path

No forge URL can exist yet. Give an **absolute** path (never relative to an
unstated cwd) with the line appended:

```
/Users/robin/Dev/personal/forestrie/canopy/foo.go:42
```

Why this shape:
- Claude Code's own TUI and iTerm2 (semantic history) make `path:line`
  **clickable → opens the editor at the line**.
- It is **copy-paste runnable** as an editor argument in another terminal:
  `code -g <path>:<line>`, `cursor -g …`, `nvim +<line> <path>`,
  `hx <path>:<line>`.
- Absolute means it resolves regardless of the reader's cwd.

Optionally *also* emit an editor-scheme URL when you know the reader's editor —
it is clickable *and* line-accurate:

```
vscode://file/Users/robin/Dev/personal/forestrie/canopy/foo.go:42:1
cursor://file/Users/robin/…:42:1
```

Do **not** reach for `file:///…` — most terminals open it in the default app,
it carries **no line number**, and it cannot be pasted as a shell command.

---

## Trade-offs (no form wins on every axis)

The user asked references to be (a) clickable in-terminal, (b) line-accurate,
and (c) copyable/runnable in another terminal. **No single form is all three** —
this is why the decision order above routes by referent, not by preference:

| Form | Clickable | Line # | Portable off this machine | Runnable as a shell cmd |
|------|:--------:|:-----:|:-------------------------:|:-----------------------:|
| Gitweb permalink `…/blob/<SHA>/…#L42` | ✅ everywhere | ✅ | ✅ | ➖ (opens browser, not editor) |
| Relative repo link `../x.md#h` | ✅ in forge/renderers | ➖ | ✅ (travels with repo) | ❌ |
| Absolute `path:line` | ✅ CC TUI / iTerm2 only | ✅ | ❌ machine-local | ✅ `code -g` / `nvim +N` |
| Editor URL `vscode://file/…:42` | ✅ if handler registered | ✅ | ❌ + editor-specific | ❌ |
| `file:///abs/path` | ✅ | ❌ | ❌ | ❌ |

Consequences to accept honestly:
- **Permalinks require commit + push.** Fresh work has no stable URL — step 3 is
  a genuine fallback, not a failure. Say "not yet pushed" rather than fabricate a
  `blob/main` link that may not resolve.
- **Plain `path:line` clickability is terminal-dependent** (Claude Code TUI and
  iTerm2 yes; plain Terminal.app / tmux often no). That is exactly why it stays
  copy-runnable — the reader always has the manual path.
- **Editor URLs assume an editor and a registered handler** and can't be run as
  a command — so they are an *addition* to the absolute path, never a
  replacement.
- **Line ranges drift** unless SHA-pinned; a range is only trustworthy in forms
  that pin (permalink) or resolve live (local path).

Rule of thumb: **in git and pushed → permalink; same-repo doc → relative link;
otherwise → absolute `path:line`, plus an editor URL when the editor is known.**
When you cannot produce any link, name the limitation explicitly.
