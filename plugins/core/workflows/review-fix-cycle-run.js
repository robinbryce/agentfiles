export const meta = {
  name: 'review-fix-cycle-run',
  description: 'Review a PR against its design, fix verified findings one commit each, and repeat until no High or Medium remain',
  whenToUse: 'Launched by /core:review-fix-cycle, which resolves the active profile overlay into args. After each push to a slice PR (kind pr), or on a slice doc before any code (kind doc).',
  phases: [
    { title: 'Check', detail: 'the worktree is clean and at the PR head' },
    { title: 'Review', detail: 'correctness and design reviewers, in parallel' },
    { title: 'Verify', detail: 'one skeptic per High, Medium or Design finding' },
    { title: 'Fix', detail: 'one commit per finding, in the PR worktree' },
    { title: 'Report', detail: 'the review-cycle comment, posted when publishing' },
  ],
}

// The review-and-fix cycle first run by hand on forestrie plan-2611-09 (FOR-603). The script is
// profile-neutral: everything a profile decides (rules of the road, commit conventions, quality
// gates, the TDD skill, where clones live) arrives in args from the skill's profile overlay.
//
// args:
//   profile     active profile name, for the log and the report (optional)
//   kind        'pr' (default) or 'doc'
//   repo        'owner/repo'                            (kind pr)
//   pr          PR number                               (kind pr)
//   worktree    absolute path of the PR branch checkout (required unless mode is 'report')
//   doc         absolute path of the slice doc          (kind doc)
//   design      design sources to hold the change to: ARC, ADRs, protocol spec, the plan README.
//   slice       absolute path of the plan slice this PR implements (optional)
//   mode        'report' (find and verify only), 'fix' (default: commit locally),
//               'publish' (fix, push, and post the cycle comment)
//   postComment false: in publish mode, push but return the comment instead of posting it, so the
//               caller can file follow-up issues first and substitute their ids
//   maxCycles   default 4
//   firstCycle  number of the first cycle this run makes (default 1)
//   followup    one issue named for every deferred finding, e.g. 'FOR-669' (optional)
//   maxAgents   concurrent agents, default 5
//   rules       how the design reviewer checks the rules of the road (a skill name or doc paths)
//   escalators  extra severity rules from the profile, e.g. rule families that make a finding Medium
//   commitRules commit conventions for fix commits (title and body limits, trailer policy)
//   gates       how to run the quality gates (a skill name or commands)
//   tdd         the test-first skill to use for behaviour fixes (optional)
//   clones      where the primary clones live, for the doc feasibility check
//   models      per-step model overrides (see MODELS below); 'main' or null means the session model
//   selftest    true: validate args and return the run plan without spawning agents
//
// Design findings are never fixed here. A cycle that confirms one still fixes the findings whose fix does not
// depend on it, then stops the run and returns the Design findings for the coordinator to decide.

const A = args || {}
const KIND = A.kind || 'pr'
const MODE = A.mode || 'fix'
const MAX_CYCLES = A.maxCycles || 4
const FIRST = A.firstCycle || 1
const MAX_AGENTS = Math.min(A.maxAgents || 5, 5)
const DESIGN = Array.isArray(A.design) ? A.design : (A.design ? [A.design] : [])
const RULES = A.rules || "the repo's AGENTS.md, its ADRs, and any rules-of-the-road documents they name"
const COMMIT_RULES = A.commitRules || "the repo's commit conventions (read its AGENTS.md and recent git log)"
const GATES = A.gates || "the repo's documented test and lint commands for the touched packages"
const ESCALATORS = Array.isArray(A.escalators) ? A.escalators : (A.escalators ? [A.escalators] : [])

// Model routing, after /core:orchestrator-mode's tiers. Mechanical steps go to haiku. Steps that need
// judgement but follow a decided design or a confirmed finding go to sonnet. Correctness and security
// review, verifying a High or Design finding, and fixing a High stay on the session model ('main').
const MODELS = {
  check: 'haiku',
  correctness: 'main',
  design: 'sonnet',
  feasibility: 'sonnet',
  verify: 'sonnet',
  verifyHigh: 'main',
  fix: 'sonnet',
  fixHigh: 'main',
  post: 'haiku',
  ...(A.models || {}),
}
const model = step => (MODELS[step] && MODELS[step] !== 'main' ? { model: MODELS[step] } : {})

const problems = []
if (!['pr', 'doc'].includes(KIND)) problems.push(`kind must be pr or doc, not ${KIND}`)
if (!['report', 'fix', 'publish'].includes(MODE)) problems.push(`mode must be report, fix or publish, not ${MODE}`)
if (KIND === 'pr' && !(A.repo && A.pr)) problems.push('kind pr needs repo and pr')
if (KIND === 'pr' && MODE !== 'report' && !A.worktree) problems.push(`mode ${MODE} needs worktree`)
if (KIND === 'doc' && !A.doc) problems.push('kind doc needs doc')
if (!DESIGN.length) problems.push('design must name at least one design source (ARC, ADR, plan README)')
if (problems.length) throw new Error('review-fix-cycle-run: ' + problems.join('; '))

// Concurrency cap: at most MAX_AGENTS agents at once across every stage.
function limiter(n) {
  let active = 0
  const queue = []
  const next = () => {
    if (active >= n || !queue.length) return
    active++
    const job = queue.shift()
    job.fn().then(
      v => { active--; job.resolve(v); next() },
      e => { active--; job.reject(e); next() })
  }
  return fn => new Promise((resolve, reject) => { queue.push({ fn, resolve, reject }); next() })
}
const slot = limiter(MAX_AGENTS)
const run = (prompt, opts) => slot(() => agent(prompt, opts))

const SEVERITIES = ['High', 'Medium', 'Low', 'Design']
const RANK = { Design: 0, High: 1, Medium: 2, Low: 3 }
const SCOPES = ['pr', 'preexisting', 'out-of-slice']

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string', description: 'The defect in one sentence' },
          severity: { type: 'string', enum: SEVERITIES },
          file: { type: 'string', description: 'Repo-relative path' },
          line: { type: 'integer' },
          scope: { type: 'string', enum: SCOPES },
          detail: { type: 'string', description: 'One or two sentences: what goes wrong and when' },
          evidence: { type: 'string', description: 'path:line references and the input or sequence that fails' },
          fix: { type: 'string', description: 'The smallest change that fixes it' },
          designRef: { type: 'string', description: 'Design source and section the finding relies on, if any' },
          designSays: { type: 'string', description: 'Design findings: what the design sources say, or that they are silent' },
          codeNeeds: { type: 'string', description: 'Design findings: what the code has to decide' },
          options: { type: 'array', items: { type: 'string' } },
          recommendation: { type: 'string' },
        },
        required: ['title', 'severity', 'file', 'scope', 'detail', 'evidence'],
      },
    },
    covered: { type: 'string', description: 'What you read and checked, in one or two sentences' },
  },
  required: ['findings', 'covered'],
}

const VERDICT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'adjusted', 'refuted'] },
    severity: { type: 'string', enum: SEVERITIES },
    scope: { type: 'string', enum: SCOPES },
    reason: { type: 'string' },
  },
  required: ['verdict', 'reason'],
}

const PRECHECK = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    head: { type: 'string' },
    base: { type: 'string', description: 'origin/<baseRefName>' },
    title: { type: 'string' },
    reason: { type: 'string' },
  },
  required: ['ok'],
}

const FIXES = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          outcome: { type: 'string', enum: ['fixed', 'not-fixed', 'design'] },
          commit: { type: 'string', description: 'Short SHA' },
          test: { type: 'string', description: 'The test that fails without the fix, if any' },
          note: { type: 'string' },
        },
        required: ['id', 'outcome'],
      },
    },
    checks: { type: 'string', description: 'Quality gates run and their result' },
    head: { type: 'string' },
    pushed: { type: 'boolean' },
  },
  required: ['results', 'checks'],
}

const DEPENDS = {
  type: 'object',
  properties: {
    dependent: { type: 'array', items: { type: 'string' }, description: 'ids of findings whose fix depends on how a Design finding is decided' },
    reason: { type: 'string' },
  },
  required: ['dependent'],
}

const POSTED = {
  type: 'object',
  properties: { url: { type: 'string' }, error: { type: 'string' } },
}

const designList = DESIGN.map(d => `- ${d}`).join('\n')
const target = KIND === 'pr' ? `${A.repo}#${A.pr}` : A.doc

const SEVERITY_RULES = `Severity:
- High: ships wrong behaviour. An authority, payment, signature or proof check that can be bypassed or wrongly fails; funds or data at risk; a contract, wire-format or API break.
- Medium: a real bug with limited reach, or behaviour that contradicts what an ADR, ARC, protocol spec, the rules of the road or the plan's locked decisions state. A Low that a design source states is Medium. A missing test for changed behaviour on an authority or payment path.
- Low: misleading comments, dead code, small test gaps, naming, docs.
- Design: the design sources are wrong, contradict each other, or are silent on something this change had to decide. A code change alone cannot settle it. Fill designSays, codeNeeds, options and recommendation.
${ESCALATORS.length ? `This profile also rates:\n${ESCALATORS.map(e => `- ${e}`).join('\n')}\n` : ''}Scope: pr (introduced or touched by this change), preexisting (predates it), out-of-slice (belongs to other planned work).
Each finding needs concrete evidence: path:line and the input or sequence that fails. No style nits. A few real findings beat many weak ones. An empty list is a valid answer.`

const REVIEWERS = KIND === 'pr' ? [
  {
    key: 'correctness',
    lens: `Correctness and security. Trace the changed code paths end to end: error handling, concurrency and locking, retries and idempotency, boundary values, what a hostile caller can send. For each changed behaviour ask whether a test would fail if it were wrong; a test that stays green with the bug present (for example with two branches swapped) is a finding.`,
  },
  {
    key: 'design',
    lens: `Design conformance. Hold the change to the design sources and to the rules of the road: ${RULES}. Cite rule ids and doc sections. Look for behaviour that contradicts a decision, comments or docs that misstate a decision, and anything the change decides that the design sources do not say: that last is a Design finding.`,
  },
] : [
  {
    key: 'design',
    lens: `Design conformance of the plan slice. Does the slice implement what the design sources decide, in their terms? Does it cite the decisions it implements? Does it decide anything they leave open (a Design finding), or contradict them? Check it against the rules of the road: ${RULES}.`,
  },
  {
    key: 'feasibility',
    lens: `Feasibility against the code as it is on each repo's origin/main. Do the files, functions, interfaces, config keys, workflow inputs and endpoints the slice names exist and behave as it assumes? Is its merge and deploy order sound? What will the implementer hit that the slice does not mention? Read the code in ${A.clones ? `the primary clones under ${A.clones}` : 'the repo checkouts the slice names'} without changing anything.`,
  },
]

function changeSource(base) {
  if (KIND === 'doc') return `Read the slice doc ${A.doc} and the plan README beside it.`
  if (A.worktree && base) {
    return `The change is ${A.repo}#${A.pr}, checked out at ${A.worktree}. Read it with \`git -C ${A.worktree} log --oneline ${base}..HEAD\` and \`git -C ${A.worktree} diff ${base}...HEAD\`, and read surrounding code in that worktree by absolute path. \`gh pr view ${A.pr} --repo ${A.repo}\` gives the description.`
  }
  return `The change is ${A.repo}#${A.pr}. Read it with \`gh pr view ${A.pr} --repo ${A.repo}\` and \`gh pr diff ${A.pr} --repo ${A.repo}\`.`
}

function reviewPrompt(r, cycle, base, prevFixes, handled) {
  const again = prevFixes.length
    ? `\nThis is review cycle ${cycle}. Start with an adversarial pass over the previous cycle's fix commits, then make a full pass:\n${prevFixes.map(f => `- ${f.commit}: ${f.title}`).join('\n')}\n`
    : `\nThis is review cycle ${cycle}.\n`
  const seen = handled.length
    ? `\nAlready handled in earlier cycles; do not report these again without new evidence:\n${handled.map(h => `- [${h.outcome}] ${h.file}${h.line ? ':' + h.line : ''} ${h.title}`).join('\n')}\n`
    : ''
  return `You are an independent reviewer. Your lens: ${r.lens}

${changeSource(base)}
${A.slice ? `It implements the plan slice ${A.slice}.` : ''}
Design sources to hold it to (read the parts the change touches):
${designList}
${again}${seen}
${SEVERITY_RULES}

Report only. Do not edit files, commit, push, comment on GitHub or write to an issue tracker.`
}

function verifyPrompt(f, base) {
  return `Try to refute this review finding on ${target}. Re-read the code yourself; do not trust the finding's account.

${changeSource(base)}
Design sources:
${designList}

Finding (${f.severity}, scope ${f.scope}): ${f.title}
${f.file}${f.line ? ':' + f.line : ''}
Detail: ${f.detail}
Evidence: ${f.evidence}
${f.designRef ? 'Design reference: ' + f.designRef : ''}
${f.severity === 'Design' ? `Design says: ${f.designSays || '-'}\nCode needs: ${f.codeNeeds || '-'}` : ''}

Answer:
- refuted: it is not real, or (for a Design finding) the design sources do settle it; cite where.
- adjusted: it is real but the severity or scope is wrong; give the right ones.
- confirmed: it is real as stated.
Refute only when you can show it is wrong. If you cannot decide, confirm and say what is uncertain.
${SEVERITY_RULES}

Report only. Do not edit files, commit, push or comment.`
}

function fixPrompt(items, head) {
  return `Fix review findings on ${A.repo}#${A.pr} in the worktree ${A.worktree}. Use absolute paths, or cd there first. HEAD should be ${head}; if it is not, or the tree is dirty, stop and return every finding as not-fixed with that reason.

Fix them in this order, one commit per finding:
${items.map(f => `- id ${f.id} (${f.severity}): ${f.title}\n  ${f.file}${f.line ? ':' + f.line : ''}. ${f.detail}\n  Suggested: ${f.fix || '-'}`).join('\n')}

For each finding:
- When it is about behaviour, first add or change a test that fails without the fix${A.tdd ? ` (${A.tdd})` : ''}, then fix it.
- Keep the change to that finding. No refactoring around it.
- Commit following ${COMMIT_RULES}. Never amend, rebase or force-push.
- If the fix needs a design decision (the design sources are silent, or the fix would contradict them), make no change for it: outcome design, and say why in note.
- If you cannot fix it, outcome not-fixed with the reason.

Design sources, for checking a fix stays inside the design:
${designList}

After the last commit, run the quality gates (${GATES}) and put the result in checks. If a gate fails because of a fix, correct it in a new commit and name it in that finding's note.
${MODE === 'publish' ? 'Then push the branch with a plain git push (never force) and set pushed.' : 'Do not push.'}
Return head as the output of git rev-parse --short HEAD.`
}

function dependsPrompt(designF, items, base) {
  return `Some review findings on ${target} wait on Design findings that a person must decide. Say which of the other findings cannot be fixed correctly until those are decided.

${changeSource(base)}

Design findings, held for a decision:
${designF.map(f => `- ${f.title}\n  Design says: ${f.designSays || '-'}\n  Code needs: ${f.codeNeeds || '-'}`).join('\n')}

Findings to classify:
${items.map(f => `- id ${f.id} (${f.severity}): ${f.title}. ${f.file}${f.line ? ':' + f.line : ''}. ${f.detail}`).join('\n')}

A finding is dependent when any reasonable decision on a Design finding would change its fix, or would make it moot. A finding is independent when its fix is the same however the Design findings are decided. When unsure, call it dependent. Return the dependent ids. Report only.`
}

function sameSpot(a, b) {
  return a.file === b.file && (a.line == null || b.line == null || Math.abs(a.line - b.line) <= 3)
}

function dedupe(list) {
  const kept = []
  for (const f of [...list].sort((a, b) => RANK[a.severity] - RANK[b.severity])) {
    const twin = kept.find(k => sameSpot(k, f) && k.severity !== 'Design' && f.severity !== 'Design')
    if (twin) { twin.reviewers.push(...f.reviewers); continue }
    kept.push(f)
  }
  return kept
}

const cell = s => String(s == null ? '' : s).replace(/\|/g, '\\|').replace(/\s*\n\s*/g, ' ').trim()

// "follow-up pending [<id>]" is a placeholder the caller swaps for an issue id when it files one
// per deferred finding before posting (postComment: false).
function outcomeText(f) {
  if (f.outcome === 'fixed') return `Fixed in \`${f.commit}\`${f.test ? ` (${f.test})` : ''}`
  if (f.outcome === 'deferred') return A.followup ? `Deferred to ${A.followup} (${f.scope})` : `Deferred (${f.scope}); follow-up pending [${f.id}]`
  if (f.outcome === 'design') return 'Held for a design decision'
  if (f.outcome === 'held') return 'Held: its fix depends on a Design finding in this cycle'
  if (f.outcome === 'reported') return 'Reported (report mode)'
  return `Not fixed: ${f.note || 'no reason given'}`
}

function cycleMarkdown(c) {
  const rows = c.findings.map(f => `| ${f.id} | ${f.severity} | ${cell(f.title)}. ${cell(f.detail)} | ${cell(outcomeText(f))} |`)
  const counts = SEVERITIES.map(s => [s, c.findings.filter(f => f.severity === s).length]).filter(([, n]) => n).map(([s, n]) => `${n} ${s}`).join(', ')
  const lines = [`## Review cycle ${c.cycle}`, '']
  lines.push(c.findings.length
    ? `Independent correctness and design reviews found ${counts}${c.refuted ? `; ${c.refuted} more ${c.refuted === 1 ? 'was' : 'were'} refuted on verification` : ''}${c.unverifiedLows ? `. Lows are not separately verified (${c.unverifiedLows} this cycle)` : ''}.`
    : `Independent correctness and design reviews found nothing${c.refuted ? ` that survived verification (${c.refuted} refuted)` : ''}.`)
  if (rows.length) lines.push('', '| # | Severity | Finding | Outcome |', '|---|---|---|---|', ...rows)
  if (c.checks) lines.push('', `Checks: ${cell(c.checks)}`)
  return lines.join('\n')
}

if (A.selftest) {
  return {
    ok: true,
    profile: A.profile || 'default',
    target,
    kind: KIND,
    mode: MODE,
    reviewers: REVIEWERS.map(r => r.key),
    maxCycles: KIND === 'doc' ? 1 : MAX_CYCLES,
    firstCycle: FIRST,
    maxAgents: MAX_AGENTS,
    design: DESIGN,
    rules: RULES,
    commitRules: COMMIT_RULES,
    gates: GATES,
    escalators: ESCALATORS,
    models: MODELS,
    sample: cycleMarkdown({ cycle: FIRST, refuted: 1, unverifiedLows: 1, checks: 'quality gates passed', findings: [
      { id: `${FIRST}.1`, severity: 'High', title: 'Example finding', detail: 'What goes wrong | and when', outcome: 'fixed', commit: 'abc1234', test: 'TestExample' },
      { id: `${FIRST}.2`, severity: 'Low', title: 'Example deferral', detail: 'Predates the PR', outcome: 'deferred', scope: 'preexisting' },
    ] }),
  }
}

log(`review-fix-cycle-run (${A.profile || 'default'}): ${target}, kind ${KIND}, mode ${MODE}, up to ${KIND === 'doc' ? 1 : MAX_CYCLES} cycles, at most ${MAX_AGENTS} agents at once`)

let head = null
let base = null
if (KIND === 'pr' && A.worktree) {
  phase('Check')
  const pre = await run(`Check a PR worktree before review. Change nothing except fetching.
1. git -C ${A.worktree} status --porcelain  (must be empty)
2. gh pr view ${A.pr} --repo ${A.repo} --json headRefOid,baseRefName,state,title
3. git -C ${A.worktree} fetch origin <baseRefName>
4. git -C ${A.worktree} rev-parse HEAD  (must equal headRefOid${MODE === 'fix' ? ', or descend from it when only local review fixes sit on top' : ''})
ok is true only when the tree is clean, the PR is OPEN and HEAD matches. head is the short HEAD SHA; base is origin/<baseRefName>.`,
    { label: 'check worktree', phase: 'Check', schema: PRECHECK, effort: 'low', ...model('check') })
  if (!pre || !pre.ok) {
    return { target, stoppedBy: 'precheck', reason: pre ? pre.reason : 'precheck agent failed', cycles: [] }
  }
  head = pre.head
  base = pre.base
}

const cycles = []
const design = []
const deferred = []
const handled = []
let prevFixes = []
let stoppedBy = 'maxCycles'
let lastChecks = null
const cycleLimit = KIND === 'doc' ? 1 : MAX_CYCLES

for (let i = 0; i < cycleLimit; i++) {
  const cycle = FIRST + i

  phase('Review')
  const reviews = await parallel(REVIEWERS.map(r => () =>
    run(reviewPrompt(r, cycle, base, prevFixes, handled), { label: `cycle ${cycle} ${r.key}`, phase: 'Review', schema: FINDINGS, ...model(r.key) })))
  const raw = reviews.flatMap((res, ri) => res ? res.findings.map(f => ({ ...f, reviewers: [REVIEWERS[ri].key] })) : [])
  const missing = reviews.map((res, ri) => res ? null : REVIEWERS[ri].key).filter(Boolean)
  if (missing.length) log(`cycle ${cycle}: reviewer(s) returned nothing: ${missing.join(', ')}`)
  const found = dedupe(raw)

  phase('Verify')
  const needsVerify = f => f.severity !== 'Low'
  const judged = await parallel(found.map((f, k) => () => needsVerify(f)
    ? run(verifyPrompt(f, base), { label: `cycle ${cycle} verify ${k + 1}`, phase: 'Verify', schema: VERDICT, ...model(f.severity === 'High' || f.severity === 'Design' ? 'verifyHigh' : 'verify') })
        .then(v => v ? { ...f, verdict: v.verdict, severity: v.verdict === 'adjusted' && v.severity ? v.severity : f.severity, scope: v.verdict === 'adjusted' && v.scope ? v.scope : f.scope, why: v.reason } : { ...f, verdict: 'unverified' })
    : Promise.resolve({ ...f, verdict: 'unverified' })))
  const all = judged.filter(Boolean)
  const refuted = all.filter(f => f.verdict === 'refuted')
  const live = all.filter(f => f.verdict !== 'refuted').sort((a, b) => RANK[a.severity] - RANK[b.severity])
  live.forEach((f, k) => { f.id = `${cycle}.${k + 1}` })
  refuted.forEach(f => handled.push({ ...f, outcome: 'refuted' }))

  const designF = live.filter(f => f.severity === 'Design')
  const defer = live.filter(f => f.severity !== 'Design' && f.scope !== 'pr')
  const toFix = live.filter(f => f.severity !== 'Design' && f.scope === 'pr')
  designF.forEach(f => { f.outcome = 'design'; design.push(f) })
  defer.forEach(f => { f.outcome = 'deferred'; deferred.push(f); handled.push(f) })

  const entry = { cycle, findings: live, refuted: refuted.length, unverifiedLows: live.filter(f => f.verdict === 'unverified').length }
  cycles.push(entry)
  const count = s => toFix.filter(f => f.severity === s).length
  log(`cycle ${cycle}: ${live.length} live (${count('High')} High, ${count('Medium')} Medium, ${count('Low')} Low to fix; ${designF.length} Design; ${defer.length} deferred), ${refuted.length} refuted`)

  // A Design finding stops the run, but first the cycle fixes the findings whose fix does not depend on it
  // (Robin, 2026-11-12). The rest are held. If the classifier fails, everything is held.
  let fixNow = toFix
  if (designF.length) {
    stoppedBy = 'design'
    if (!toFix.length || KIND === 'doc' || MODE === 'report') {
      toFix.forEach(f => { f.outcome = KIND === 'doc' || MODE === 'report' ? 'reported' : 'held' })
      break
    }
    const dep = await run(dependsPrompt(designF, toFix, base), { label: `cycle ${cycle} design dependence`, phase: 'Verify', schema: DEPENDS, ...model('verify') })
    const dependent = new Set(dep ? dep.dependent : toFix.map(f => f.id))
    toFix.filter(f => dependent.has(f.id)).forEach(f => { f.outcome = 'held' })
    fixNow = toFix.filter(f => !dependent.has(f.id))
    log(`cycle ${cycle}: ${fixNow.length} finding(s) fixed despite the Design hold, ${toFix.length - fixNow.length} held`)
    if (!fixNow.length) break
  }
  if (!toFix.length) { stoppedBy = 'clean'; break }
  if (KIND === 'doc' || MODE === 'report') {
    toFix.forEach(f => { f.outcome = 'reported' })
    stoppedBy = 'report'
    break
  }

  phase('Fix')
  const fixed = await run(fixPrompt(fixNow, head), { label: `cycle ${cycle} fix ${fixNow.length}`, phase: 'Fix', schema: FIXES, ...model(fixNow.some(f => f.severity === 'High') ? 'fixHigh' : 'fix') })
  if (!fixed) {
    fixNow.forEach(f => { f.outcome = 'not-fixed'; f.note = 'fixer agent failed' })
    stoppedBy = 'fix-failed'
    break
  }
  const byId = new Map(fixed.results.map(r => [r.id, r]))
  for (const f of fixNow) {
    const r = byId.get(f.id)
    f.outcome = r ? r.outcome : 'not-fixed'
    f.commit = r && r.commit
    f.test = r && r.test
    f.note = r ? r.note : 'the fixer did not report it'
    if (f.outcome === 'design') design.push(f)
    handled.push(f)
  }
  entry.checks = fixed.checks
  lastChecks = fixed.checks
  if (fixed.head) head = fixed.head
  prevFixes = fixNow.filter(f => f.outcome === 'fixed')

  if (designF.length || fixNow.some(f => f.outcome === 'design')) { stoppedBy = 'design'; break }
  if (fixNow.some(f => f.outcome === 'not-fixed' && f.severity !== 'Low')) { stoppedBy = 'not-fixed'; break }
  if (!toFix.some(f => f.severity === 'High' || f.severity === 'Medium')) { stoppedBy = 'clean'; break }
}

if (stoppedBy === 'maxCycles') log(`stopped after ${cycleLimit} cycles with High or Medium findings still being fixed; run again with firstCycle ${FIRST + cycleLimit}`)

const markdown = [
  ...cycles.map(cycleMarkdown),
  design.length ? `## Held for a design decision\n\n${design.map(f => `- **${cell(f.title)}** (${f.file}${f.line ? ':' + f.line : ''}). Design says: ${cell(f.designSays || '-')} Code needs: ${cell(f.codeNeeds || f.note || '-')}`).join('\n')}` : '',
  stoppedBy === 'clean' ? `The last cycle found no High or Medium.` : '',
  '🤖 Generated with [Claude Code](https://claude.com/claude-code)',
].filter(Boolean).join('\n\n')

let commentUrl = null
if (KIND === 'pr' && MODE === 'publish' && A.postComment !== false && cycles.length) {
  phase('Report')
  const posted = await run(`Post this markdown as a comment on ${A.repo}#${A.pr}, unchanged. Write it to a new file under $TMPDIR, then run gh pr comment ${A.pr} --repo ${A.repo} --body-file <that file>. Return the comment URL gh prints, or the error.

<<<COMMENT
${markdown}
COMMENT>>>`, { label: 'post comment', phase: 'Report', schema: POSTED, effort: 'low', ...model('post') })
  commentUrl = posted && posted.url
  if (!commentUrl) log(`comment not posted: ${posted ? posted.error : 'agent failed'}`)
}

return {
  profile: A.profile || 'default',
  target,
  kind: KIND,
  mode: MODE,
  stoppedBy,
  clean: stoppedBy === 'clean',
  head,
  cyclesRun: cycles.map(c => c.cycle),
  design: design.map(f => ({ title: f.title, file: f.file, line: f.line, designSays: f.designSays, codeNeeds: f.codeNeeds || f.note, options: f.options, recommendation: f.recommendation, designRef: f.designRef })),
  deferred: deferred.map(f => ({ id: f.id, severity: f.severity, scope: f.scope, title: f.title, file: f.file, line: f.line, detail: f.detail, evidence: f.evidence })),
  notFixed: cycles.flatMap(c => c.findings.filter(f => f.outcome === 'not-fixed').map(f => ({ id: f.id, severity: f.severity, title: f.title, note: f.note }))),
  checks: lastChecks,
  commentMarkdown: markdown,
  commentUrl,
}
