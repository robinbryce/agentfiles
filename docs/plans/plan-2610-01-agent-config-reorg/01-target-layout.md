# 01 — Target layout

Part of [plan 2610-01](./README.md). Trees below show the **end state**; the
file-by-file mapping from today's layout is in
[03-migration.md](./03-migration.md#file-mapping).

## Repositories

| Repo | Visibility | Marketplace name | Plugins | Owns |
|------|-----------|------------------|---------|------|
| [robinbryce/agentfiles](https://github.com/robinbryce/agentfiles) | public | `agentfiles` | `core`, `research` | cross-profile skills, always-on rules, **profiles**, bootstrap/doctor/sync tooling, harness notes |
| [forestrie/forestrie-agents](https://github.com/forestrie/forestrie-agents) | org | `forestrie-agents` | `forestrie-core`, `forestrie-linear`, `engineering` | team skills, glossaries, rules-of-the-road, per-repo sync manifests, workspace `AGENTS.md` |
| robinbryce/agentfiles-home (new) | **private** | `agentfiles-home` | `admin`, `finance`, `research-personal` | tax / finance / household skills with reference material, privacy rule |
| [SentientDogs/just-agents](https://github.com/SentientDogs/just-agents) | org | `just-agents` | unchanged | out of scope; the `justgames` profile points at it |

Rule of thumb: **a skill lives in the repo of the narrowest audience that
needs it.** Cross-profile → `agentfiles/core`; team → `forestrie-agents`;
private → `agentfiles-home`.

---

## agentfiles

```text
agentfiles/
├── .claude-plugin/
│   └── marketplace.json            # name "agentfiles"; entries core, research (relative paths)
├── AGENTS.md                       # ONLY for an agent editing this repo: layout, how to add a
│                                   # skill/rule/profile, run `agentfiles doctor` + plugin validate
├── README.md                       # for humans: what, why, bootstrap
├── plugins/
│   ├── core/
│   │   ├── .claude-plugin/plugin.json          # name "core"; hooks → ./hooks/hooks.json
│   │   ├── skills/
│   │   │   ├── plan-new/            SKILL.md, scripts/new-plan.sh, templates/
│   │   │   ├── save-status/         SKILL.md            (user-invoked; generic flavour)
│   │   │   ├── planning/            SKILL.md            (user-invocable: false; paths: plans|adr|arc)
│   │   │   ├── pr-descriptions/     SKILL.md            (user-invocable: false; description: creating/editing a PR)
│   │   │   ├── multi-repo-fanout/   SKILL.md            (user-invocable: false)
│   │   │   └── linear-direct-api/   SKILL.md            (mechanism only; key resolution per profile)
│   │   ├── agents/                  (none yet; e.g. plan-reviewer.md later)
│   │   └── hooks/hooks.json         # PreToolUse Write|Edit → validate-plan.sh (ships with the plugin)
│   │       └── scripts/validate-plan.sh
│   └── research/
│       └── skills/
│           ├── research-brief/      SKILL.md, templates/brief.md
│           ├── source-triage/       SKILL.md
│           └── literature-map/      SKILL.md
├── rules/                          # always-on rule FILES (plugins cannot ship rules)
│   ├── clickable-references.md     # no paths: → every session
│   └── herdr-session-handoff.md    # paths: ["**/.worktrees-herdr/**"]
├── profiles/
│   ├── personal/
│   │   ├── CLAUDE.md               # ≤ 40 lines: who you are, planning params, where content comes from
│   │   ├── AGENTS.md               # pi's equivalent (no @import; points at CLAUDE.md content, kept in sync)
│   │   ├── settings.json           # template: extraKnownMarketplaces + enabledPlugins + hooks + permissions
│   │   └── rules/                  # extra per-profile rules (optional)
│   ├── forestrie/   CLAUDE.md, AGENTS.md, settings.json
│   ├── home/        CLAUDE.md, AGENTS.md, settings.json, rules/privacy.md
│   └── justgames/   CLAUDE.md, AGENTS.md, settings.json
├── bin/
│   └── agentfiles                  # bootstrap | doctor | sync | link   (bash; shells out to claude/npx)
├── harness/
│   ├── claude-code.md              # profiles, marketplaces, cloud parity (short)
│   ├── pi.md
│   ├── cursor.md
│   └── local-models.md             # claude-local / pi-local wrappers, Ollama settings
├── docs/plans/                     # this plan
└── incubator/
    └── forestrie/                  # drafts destined for forestrie-agents (was scopes/forestrie/incubator)
```

### marketplace.json

```json
{
  "name": "agentfiles",
  "description": "Robin's cross-profile agent skills and hooks.",
  "owner": { "name": "Robin Bryce", "url": "https://github.com/robinbryce" },
  "metadata": { "pluginRoot": "./plugins" },
  "plugins": [
    { "name": "core",     "source": "core",     "description": "/core:plan-new, /core:save-status, planning + PR-description + fan-out rules, plan-naming hook", "category": "workflow" },
    { "name": "research", "source": "research", "description": "Research briefs, source triage, literature maps", "category": "research" }
  ]
}
```

Entry name = manifest name (`core`), so skills are `/core:plan-new` and the
enable key is `core@agentfiles`. No `version` field in either manifest: a
hosted install then tracks commits; a local-directory marketplace loads in
place regardless.

### plugins/core/.claude-plugin/plugin.json

```json
{
  "name": "core",
  "description": "Cross-profile skills and the plan-doc naming guardrail.",
  "author": { "name": "Robin Bryce" },
  "repository": "https://github.com/robinbryce/agentfiles",
  "license": "MIT",
  "hooks": "./hooks/hooks.json"
}
```

`skills/` and `agents/` are discovered by convention; only `hooks` needs a
path. The hook command uses `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate-plan.sh`,
so it works in-place and from the cache.

### profiles/forestrie/settings.json (template)

```json
{
  "$comment": "rendered by `agentfiles bootstrap`; ${HOME} and ${FORESTRIE_AGENTS} substituted",
  "extraKnownMarketplaces": {
    "agentfiles":       { "source": { "source": "directory", "path": "${HOME}/agentfiles" } },
    "forestrie-agents": { "source": { "source": "directory", "path": "${FORESTRIE_AGENTS}" } }
  },
  "enabledPlugins": {
    "core@agentfiles": true,
    "forestrie-core@forestrie-agents": true,
    "forestrie-linear@forestrie-agents": true,
    "engineering@forestrie-agents": true
  },
  "pluginConfigs": {
    "cc-plugin-agents-md@builtin": { "options": { "instructionFiles": "claude-md-and-agents-md" } }
  },
  "permissions": {
    "allow": [ "Bash(curl -s https://api.linear.app/graphql*)" ]
  },
  "alwaysThinkingEnabled": true
}
```

- `directory` sources load plugins **in place** from the checkout: edit a
  skill, `/reload-plugins`, done. On a machine without the checkout,
  bootstrap writes a `github` source instead (`{"source":"github","repo":"forestrie/forestrie-agents"}`).
- `instructionFiles: claude-md-and-agents-md` makes Claude read a repo's
  `AGENTS.md` even when a `CLAUDE.md` exists above it (e.g. a stray one in
  `~`), so workspace and repo routing never silently switch off.
- The `personal` profile has only `agentfiles`; `home` has `agentfiles` +
  `agentfiles-home`. **A marketplace absent from a profile is unreachable
  from it.**

### profiles/forestrie/CLAUDE.md

```markdown
# Profile: forestrie

This session runs in Robin's **forestrie** profile. Team conventions arrive as
`forestrie-core` / `forestrie-linear` / `engineering` plugin skills and as the
repo's committed `AGENTS.md` and `.claude/rules/`. Personal conventions arrive
as `core` plugin skills and the rules in this profile. Nothing from other
profiles is installed here; do not go looking for it.

## Planning params (override `core:planning` defaults)
| plans_root | repo `docs/plans/`; cross-repo plans in `devdocs/plans/` |
| decisions_home | central `devdocs/adr/`, `devdocs/arc/` |
| issue_refs | Linear `FOR-*` |

Workspace map: `~/Dev/personal/forestrie/AGENTS.md` (loads automatically).
```

That is the whole file. Everything that used to be a router table is now
either installed (plugins), discovered (AGENTS.md walk-up, rules `paths:`) or
triggered (skill descriptions).

### bin/agentfiles

| Subcommand | Does |
|------------|------|
| `bootstrap [profile…]` | create `~/.claude-<p>`; symlink `CLAUDE.md`, `rules/`; render `settings.json` (merge-preserving unmanaged keys); `CLAUDE_CONFIG_DIR=… claude plugin marketplace add` / `install` for each declared plugin; mirror to `~/.pi-<p>` (`AGENTS.md` link, `skills/` links); write `~/.config/agentfiles/wrappers.sh` (sourced by dotfiles) defining `claude-<p>`, `pi-<p>`, `claude-local` |
| `doctor [--profile p] [--repo]` | print, per profile: marketplaces (`claude plugin marketplace list`), plugins (`claude plugin list --json`), rule files, instruction files, pending `/reload-plugins`; with `--repo`: compare `.agents/skills/*/.synced-from` and `.claude/rules/*` against the marketplace source SHA and report drift |
| `sync <repo-dir> [--manifest <name>]` | apply a sync manifest (below): `npx skills add <marketplace-repo> -a claude-code -a codex -a cursor …` into `.agents/skills` with `.claude/skills` symlinks, copy listed rule files into `.claude/rules/`, write `.synced-from`, print `git status` |
| `link <profile>` | legacy per-repo `AGENTS.md`/`CLAUDE.md` link for harnesses with no walk-up; kept for cursor-agent |

All of these are thin: the real work is `claude plugin …` and `npx skills`.

---

## forestrie-agents

```text
forestrie-agents/
├── .claude-plugin/marketplace.json      # name "forestrie-agents"; pluginRoot ./plugins
├── AGENTS.md                            # org map + how to contribute to this repo (replaces the router)
├── README.md
├── plugins/
│   ├── forestrie-core/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/
│   │   │   ├── review-changes/  triage/  pre-commit-checks/  setup-clone/  fork-mandate/
│   │   │   ├── plan-with-linear/  persist-plan/  save-status/ (forestrie flavour)
│   │   │   ├── rules-of-the-road-review/            # cites rule ids; loads the repo's rules file
│   │   │   └── arc-canopy/ arc-arbor/ arc-univocity/ arc-infra/ arc-mandate/ arc-tools/ arc-company/
│   │   │                                            # glossaries as model-invoked skills, description =
│   │   │                                            # the old "task touches …" column
│   │   ├── agents/
│   │   │   └── reviewer.md                          # subagent: skills: [rules-of-the-road-review], tools read-only
│   │   └── hooks/hooks.json                         # require-worktree (ships with the plugin)
│   ├── forestrie-linear/
│   │   └── skills/linear-forestrie/SKILL.md         # key resolution + identity pre-flight for FOR
│   └── engineering/                                 # EITHER a marketplace entry pinned to matt-skills by sha (Q4)
│       └── (VENDOR.md + skills/{tdd,diagnose,grill-with-docs})   # OR this single vendored copy
├── rules/                                 # SOURCES for the committed layer (not loaded from here)
│   ├── common/      commit-conventions.md  branch-naming.md  breaking-changes.md  adr-format.md  plan-docs.md
│   ├── lang/        go-comments.md (paths: **/*.go)  typescript-comments.md  solidity-comments.md
│   │                go-task-over-shell.md  source-order-call-graph.md  types-single-responsibility.md
│   └── rules-of-the-road/   platform.md  arbor.md  canopy.md  univocity.md  mandate.md  univocity-tools.md  forest-1.md  arbor-flux.md
├── sync/                                  # per-repo manifests consumed by `agentfiles sync`
│   ├── canopy.manifest                    # rules: common/*, lang/typescript-comments, rules-of-the-road/{platform,canopy}
│   │                                      # skills: forestrie-core:{review-changes,save-status,persist-plan,rules-of-the-road-review,arc-canopy}
│   ├── arbor.manifest
│   └── …
├── workspace/AGENTS.md                    # installed at ~/Dev/personal/forestrie/AGENTS.md by bootstrap
├── incubator/<github-login>/
└── harness/                               # two short pages: claude-code (profiles+cloud), other-tools
```

### A forestrie repo after `agentfiles sync` (committed layer)

```text
canopy/
├── AGENTS.md                      # repo-specific: build/test, layout, devdocs links. Not a copy of org content.
├── .claude/
│   ├── settings.json              # for terminal collaborators:
│   │                              #   extraKnownMarketplaces: forestrie-agents (github source)
│   │                              #   enabledPlugins: forestrie-core@forestrie-agents, forestrie-linear@…, engineering@…
│   │                              #   hooks: none (require-worktree comes with the plugin; cloud does not need it)
│   ├── rules/                     # SYNCED from forestrie-agents/rules per sync/canopy.manifest
│   │   ├── rules-of-the-road-platform.md
│   │   ├── rules-of-the-road-canopy.md
│   │   ├── commit-conventions.md
│   │   └── typescript-comments.md           (paths: ["**/*.ts", "**/*.tsx"])
│   └── skills/
│       └── review-changes -> ../../.agents/skills/review-changes      # relative symlinks survive clone
├── .agents/skills/                # SYNCED vendored copies (open-standard path; Codex/Cursor/Copilot/OpenCode read it)
│   ├── review-changes/   save-status/   persist-plan/   rules-of-the-road-review/   arc-canopy/
│   └── .synced-from               # forestrie-agents@<sha>  manifest=canopy
└── .mcp.json                      # project MCP servers, if any
```

Why both the plugin **and** a committed copy:

- Terminal collaborators get everything, live, from the plugin; the committed
  copy is for **cloud sessions** (which never load plugins) and for
  **non-Claude harnesses** (which read `.agents/skills`).
- The committed set is deliberately a **subset** (the manifest), so repos do
  not carry seven glossaries. Drift is detected by `agentfiles doctor --repo`
  and can be enforced by a CI job that re-runs the sync and fails on diff.
- In a terminal session both `/review-changes` and
  `/forestrie-core:review-changes` appear. Harmless; if the noise bothers,
  `skillOverrides` in the profile settings can collapse the bare names.

### Workspace AGENTS.md (`~/Dev/personal/forestrie/AGENTS.md`)

Claude Code and pi load it in every session started anywhere beneath it, so
it replaces both `forestrie-agent-context.md` and the cwd table:

```markdown
# Forestrie workspace

Clones of forestrie org repos live here as siblings. Treat several clones of
one repo as one repo; the clone whose directory name equals the repo name is
primary. `dotgithub/` is `forestrie/.github`.

| Directory | Repo | Notes |
| canopy | forestrie/canopy | SCRAPI Workers API |
| arbor, arbor-ssh-test | forestrie/arbor | arbor is primary |
| … | … | … |

Org conventions come from the forestrie-agents plugins installed in this
profile and from each repo's `AGENTS.md` + `.claude/rules/`.
Platform "why": devdocs. Platform glossary: devdocs/glossary.md.
```

---

## agentfiles-home (private)

```text
agentfiles-home/
├── .claude-plugin/marketplace.json       # name "agentfiles-home"
├── plugins/
│   ├── admin/
│   │   └── skills/
│   │       ├── uk-self-assessment/       SKILL.md, references/{deadlines.md,allowances.md,evidence-checklist.md}, scripts/normalise-statements.py
│   │       ├── household-records/        SKILL.md, references/
│   │       └── correspondence/           SKILL.md, assets/letter-templates/
│   ├── finance/
│   │   └── skills/  statement-reconcile/  budget-review/
│   └── research-personal/
│       └── skills/  (home-flavoured briefs; cross-profile research stays in agentfiles/research)
└── rules/
    └── privacy.md                        # no identifiers to third-party tools, redact before web search, where records live
```

- The `home` profile dir symlinks `rules/privacy.md` so it is always on.
- The admin skills are also **uploaded to the claude.ai account** (Q5) so
  claude.ai chat, Cowork and cloud sessions, where most admin work with Gmail /
  Drive / Calendar connectors happens, have them. Account skills are
  account-wide, so only content that is harmless in a forestrie session goes
  there; anything sensitive stays plugin-only.

---

## Selection: direnv + wrappers

```bash
# ~/Dev/personal/forestrie/.envrc   (already sources .env.secret for LINEAR_API_KEY)
export CLAUDE_CONFIG_DIR="$HOME/.claude-forestrie"
export PI_CODING_AGENT_DIR="$HOME/.pi-forestrie"

# ~/Dev/personal/.envrc, ~/Dev/justgames/.envrc, ~/Home/.envrc — likewise
```

```bash
# ~/.config/agentfiles/wrappers.sh  (generated by bootstrap, sourced by dotfiles profiles/common/agents.sh)
claude() {                       # honour direnv first, DOTFILES_ROLE second
  if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then command claude "$@"; return; fi
  case "${DOTFILES_ROLE:-personal-dev}" in work-dev) claude-justgames "$@" ;; *) claude-personal "$@" ;; esac
}
claude-personal()  { CLAUDE_CONFIG_DIR="$HOME/.claude-personal"  command claude "$@"; }
claude-forestrie() { CLAUDE_CONFIG_DIR="$HOME/.claude-forestrie" command claude "$@"; }
claude-home()      { CLAUDE_CONFIG_DIR="$HOME/.claude-home"      command claude "$@"; }
claude-local() {                 # same profile, local model: see harness/local-models.md
  ANTHROPIC_BASE_URL="${OLLAMA_HOST:-http://localhost:11434}" ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY="" \
  ANTHROPIC_DEFAULT_SONNET_MODEL="${LOCAL_MODEL:-qwen3-coder}" ANTHROPIC_DEFAULT_OPUS_MODEL="${LOCAL_MODEL:-qwen3-coder}" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="${LOCAL_SMALL_MODEL:-qwen3-coder}" claude "$@"
}
```

The deterministic chain is: **directory → direnv → config dir → profile
content.** The model is never asked which scope it is in.
