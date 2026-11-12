export const meta = {
  name: 'plan-wave-run',
  description: 'Run one wave of a multi-slice plan: doc reviews, or build-and-review lanes, at most 5 agents at once',
  whenToUse: 'Executing a plan directory whose slices have docs, dependencies and human gates. One run covers one wave and stops at the next gate; the coordinator updates the gate state and runs the next wave.',
  phases: [
    { title: 'Doc review', detail: 'review-fix-cycle-run in doc mode on each slice doc' },
    { title: 'Build', detail: 'one implementer per ready slice, in its own container and wif stream' },
    { title: 'Review', detail: 'review-fix-cycle-run on each slice PR until no High or Medium remain' },
    { title: 'Track', detail: 'the slice stream records its position and next step in wif' },
  ],
}

// A plan is executed as waves because merges, release tags and privileged steps are human gates a
// run cannot cross. Each run does what is ready, records where every slice stands in wif, and stops.
//
// args:
//   wave         'doc-review' | 'build'
//   profile      active profile name (for logs and the review workflow)
//   plan         { id, readme, handoff, issue, parentStream }
//   slices       [{ id, title, doc, repos: ['repo', ...], task, goal, deps: ['id', ...] }]
//                task is the container and branch name (lowercase kebab-case); goal is the wif stream goal
//   merged       slice ids whose PRs are merged (gate state, supplied by the coordinator)
//   blocked      { <slice id>: 'reason' } for slices held at a human gate the coordinator knows about
//   only         slice ids to limit this run to (optional)
//   maxAgents    total concurrent agents across this run and its review runs, at most 5 (default 5)
//   reviewAgents agents one review run may use (default 2; must be below maxAgents for build waves)
//   review       { workflow: 'core:review-fix-cycle-run' or { scriptPath }, mode: 'report'|'fix'|'publish',
//                  args: profile values for review-fix-cycle-run (rules, escalators, commitRules, gates,
//                  tdd, clones, postComment, design: [standing design sources]) }
//   container    { root, command: 'herdr-task'|'git-worktree', wif: true }
//   prRules      how to write PR descriptions (a rule or skill name), optional
//   selftest     true: validate and return the run plan without spawning agents
//
// The coordinator owns everything outward-facing that the profile reserves for it: filing deferred
// findings, posting cycle comments when postComment is false, merges, tags and privileged steps.

const A = args || {}
const WAVE = A.wave
const MAX = Math.max(1, Math.min(A.maxAgents || 5, 5))
const REVIEW_AGENTS = Math.max(1, Math.min(A.reviewAgents || 2, MAX))
const SLICES = Array.isArray(A.slices) ? A.slices : []
const MERGED = new Set(A.merged || [])
const BLOCKED = A.blocked || {}
const ONLY = A.only && A.only.length ? new Set(A.only) : null
const REVIEW = A.review || {}
const REVIEW_WF = REVIEW.workflow || 'core:review-fix-cycle-run'
const CONTAINER = A.container || {}
const PLAN = A.plan || {}

const problems = []
if (!['doc-review', 'build'].includes(WAVE)) problems.push(`wave must be doc-review or build, not ${WAVE}`)
if (!SLICES.length) problems.push('slices is empty')
if (!PLAN.readme) problems.push('plan.readme is required')
SLICES.forEach(s => {
  if (!s.id || !s.doc) problems.push(`slice ${s.id || '?'} needs id and doc`)
  if (WAVE === 'build' && !(s.repos && s.repos.length && s.task)) problems.push(`slice ${s.id} needs repos and task for a build wave`)
  ;(s.deps || []).forEach(d => { if (!SLICES.some(x => x.id === d)) problems.push(`slice ${s.id} depends on unknown slice ${d}`) })
})
if (WAVE === 'build' && REVIEW_AGENTS >= MAX) problems.push('reviewAgents must be below maxAgents in a build wave, or an implementer can never start')
if (WAVE === 'build' && !CONTAINER.root) problems.push('container.root is required for a build wave')
if (problems.length) throw new Error('plan-wave-run: ' + problems.join('; '))

// Weighted permits: an implementer holds 1, a review run holds REVIEW_AGENTS and is told to use no
// more, so the run never has more than MAX agents in flight, children included.
function permits(total) {
  let free = total
  const queue = []
  const pump = () => {
    while (queue.length && queue[0].n <= free) {
      const job = queue.shift()
      free -= job.n
      job.resolve()
    }
  }
  return {
    acquire: n => new Promise(resolve => { queue.push({ n: Math.min(n, total), resolve }); pump() }),
    release: n => { free += Math.min(n, total); pump() },
  }
}
const pool = permits(MAX)
async function holding(n, fn) {
  await pool.acquire(n)
  try { return await fn() } finally { pool.release(n) }
}
const call = (prompt, opts) => holding(1, () => agent(prompt, opts))

const inScope = s => !ONLY || ONLY.has(s.id)
const ready = s => !MERGED.has(s.id) && !BLOCKED[s.id] && (s.deps || []).every(d => MERGED.has(d))
const designFor = s => [...(REVIEW.args && REVIEW.args.design ? REVIEW.args.design : []), PLAN.readme, s.doc]
  .filter((d, i, all) => d && all.indexOf(d) === i)

function plannedSlices() {
  return SLICES.filter(inScope).map(s => ({
    id: s.id,
    title: s.title,
    action: WAVE === 'doc-review' ? 'doc review'
      : MERGED.has(s.id) ? 'skip: merged'
      : BLOCKED[s.id] ? `skip: ${BLOCKED[s.id]}`
      : ready(s) ? `build in ${s.task} (${s.repos.join(', ')})`
      : `wait: needs ${(s.deps || []).filter(d => !MERGED.has(d)).join(', ')} merged`,
  }))
}

if (A.selftest) {
  return { ok: true, wave: WAVE, profile: A.profile || 'default', maxAgents: MAX, reviewAgents: REVIEW_AGENTS, reviewWorkflow: REVIEW_WF, slices: plannedSlices() }
}

log(`plan-wave-run ${PLAN.id || ''}: wave ${WAVE}, ${SLICES.filter(inScope).length} slice(s), at most ${MAX} agents (review runs ${REVIEW_AGENTS})`)

async function review(reviewArgs, label) {
  return holding(REVIEW_AGENTS, async () => {
    try {
      return await workflow(REVIEW_WF, { ...(REVIEW.args || {}), profile: A.profile, maxAgents: REVIEW_AGENTS, ...reviewArgs })
    } catch (e) {
      log(`${label}: review run failed: ${e && e.message ? e.message : e}`)
      return { stoppedBy: 'review-error', error: String(e && e.message ? e.message : e) }
    }
  })
}

// Doc review: a design and feasibility review of each slice doc. Report only; nothing is fixed.
if (WAVE === 'doc-review') {
  phase('Doc review')
  const results = await Promise.all(SLICES.filter(inScope).map(s =>
    review({ kind: 'doc', doc: s.doc, slice: s.doc, design: designFor(s), mode: 'report' }, `slice ${s.id}`)
      .then(r => ({ slice: s.id, title: s.title, result: r }))))
  return {
    wave: WAVE,
    plan: PLAN.id,
    slices: results.map(x => ({
      slice: x.slice,
      title: x.title,
      stoppedBy: x.result && x.result.stoppedBy,
      design: (x.result && x.result.design) || [],
      deferred: (x.result && x.result.deferred) || [],
      report: x.result && x.result.commentMarkdown,
    })),
  }
}

// Build: each ready slice runs implement, then review, then track, with no barrier between slices.
const TRACK = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, note: { type: 'string' } },
  required: ['ok'],
}
const BUILT = {
  type: 'object',
  properties: {
    container: { type: 'string', description: 'absolute path of the task container' },
    prs: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          repo: { type: 'string', description: 'owner/name' },
          pr: { type: 'integer' },
          url: { type: 'string' },
          worktree: { type: 'string', description: 'absolute path of the PR branch checkout' },
          head: { type: 'string' },
        },
        required: ['repo', 'pr', 'worktree'],
      },
    },
    checks: { type: 'string', description: 'quality gates run and their result' },
    blocked: { type: 'string', description: 'set when the slice could not be built, with the reason' },
  },
  required: ['prs'],
}

function buildPrompt(s) {
  const make = CONTAINER.command === 'git-worktree'
    ? `create a git worktree per repo on branch ${s.task} from origin/<default branch> under ${CONTAINER.root}/.worktrees-herdr/${s.task}/<repo>`
    : `run \`herdr-task ${s.task} ${s.repos.join(' ')} --root ${CONTAINER.root}${PLAN.parentStream ? ` -p ${PLAN.parentStream}` : ''} -g ${JSON.stringify(s.goal || s.title)}\` from ${CONTAINER.root}. It creates ${CONTAINER.root}/.worktrees-herdr/${s.task}/<repo> on branch ${s.task}${CONTAINER.wif === false ? '' : ' and adopts the wif stream'}; a herdr workspace error is not fatal. Re-running it is safe`
  return `Implement slice ${s.id} (${s.title}) of plan ${PLAN.id || PLAN.readme}.

Read first: the plan README ${PLAN.readme}, the slice doc ${s.doc}${PLAN.handoff ? `, and ${PLAN.handoff}` : ''}. The slice doc's Tests and "Done when" sections are the acceptance bar.

1. Container: ${make}. Work only inside that container.${CONTAINER.wif === false ? '' : ` From inside it, record progress with \`wif mark -p "<where the slice stands>" -n "<next step>"\` after each milestone.`}
2. Implement the slice. For behaviour, write a test that fails first${REVIEW.args && REVIEW.args.tdd ? ` (${REVIEW.args.tdd})` : ''}. Commit following ${REVIEW.args && REVIEW.args.commitRules ? REVIEW.args.commitRules : "the repo's commit conventions"}. Never amend, rebase, force-push or push to the default branch.
3. Run the quality gates: ${REVIEW.args && REVIEW.args.gates ? REVIEW.args.gates : "the repo's documented test and lint commands"}.
4. Push the task branch and open one PR per repo you changed. ${A.prRules ? `Write each PR description following ${A.prRules}.` : 'Make each PR description self-contained.'} Link ${PLAN.issue || 'the plan issue'} and the slice doc.
5. If the slice cannot be built as written (a missing interface, a contradiction in the design, a gate it depends on), stop, change nothing more, and set blocked with the reason and the evidence.

Never merge, approve, tag a release, run a deploy, or do anything the profile reserves for a person.`
}

function trackPrompt(s, built, reviews) {
  const lines = reviews.map(r => `${r.repo}#${r.pr}: ${r.result ? r.result.stoppedBy : 'no review result'}${r.result && r.result.design && r.result.design.length ? ` (${r.result.design.length} design hold)` : ''}`)
  const held = reviews.some(r => r.result && r.result.stoppedBy === 'design')
  const clean = reviews.length && reviews.every(r => r.result && r.result.clean)
  return `In ${built.container}, record where slice ${s.id} stands in wif. Change nothing else.
Run from inside the container:
  wif mark -p ${JSON.stringify(`PRs open: ${lines.join('; ')}`)} -n ${JSON.stringify(held ? 'design decision needed before more work' : clean ? 'review clean; awaiting merge' : 'review incomplete; see the cycle comments')}
${held ? `  wif note ${JSON.stringify(`design hold on slice ${s.id}: see the Held for a design decision section of the cycle report`)}\n` : ''}Return ok=true when the commands succeeded.`
}

const work = SLICES.filter(inScope)
const results = await Promise.all(work.map(async s => {
  if (MERGED.has(s.id)) return { slice: s.id, status: 'merged' }
  if (BLOCKED[s.id]) return { slice: s.id, status: 'gated', reason: BLOCKED[s.id] }
  if (!ready(s)) return { slice: s.id, status: 'waiting', needs: (s.deps || []).filter(d => !MERGED.has(d)) }

  const built = await call(buildPrompt(s), { label: `build ${s.id}`, phase: 'Build', schema: BUILT })
  if (!built) return { slice: s.id, status: 'build-failed', reason: 'implementer returned nothing' }
  if (built.blocked) return { slice: s.id, status: 'blocked', reason: built.blocked, container: built.container }

  const reviews = await Promise.all((built.prs || []).map(p =>
    review({ kind: 'pr', repo: p.repo, pr: p.pr, worktree: p.worktree, slice: s.doc, design: designFor(s), mode: REVIEW.mode || 'publish' }, `${p.repo}#${p.pr}`)
      .then(result => ({ ...p, result }))))

  if (CONTAINER.wif !== false && built.container) {
    await call(trackPrompt(s, built, reviews), { label: `track ${s.id}`, phase: 'Track', schema: TRACK, model: 'haiku', effort: 'low' })
  }

  const held = reviews.some(r => r.result && r.result.stoppedBy === 'design')
  const clean = reviews.length > 0 && reviews.every(r => r.result && r.result.clean)
  return {
    slice: s.id,
    status: held ? 'design-hold' : clean ? 'awaiting-merge' : 'review-open',
    container: built.container,
    checks: built.checks,
    prs: reviews.map(r => ({
      repo: r.repo,
      pr: r.pr,
      url: r.url,
      stoppedBy: r.result && r.result.stoppedBy,
      head: r.result && r.result.head,
      design: (r.result && r.result.design) || [],
      deferred: (r.result && r.result.deferred) || [],
      commentMarkdown: r.result && r.result.commentMarkdown,
      commentUrl: r.result && r.result.commentUrl,
    })),
  }
}))

const nextGates = results.filter(r => ['awaiting-merge', 'gated', 'waiting'].includes(r.status))
  .map(r => r.status === 'awaiting-merge' ? `merge slice ${r.slice}` : r.status === 'gated' ? `slice ${r.slice}: ${r.reason}` : `slice ${r.slice} waits on ${r.needs.join(', ')}`)
return { wave: WAVE, plan: PLAN.id, slices: results, nextGates }
