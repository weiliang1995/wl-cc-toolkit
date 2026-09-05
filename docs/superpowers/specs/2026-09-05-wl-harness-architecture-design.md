# wl-harness — Architecture Design

**Date:** 2026-09-05
**Status:** Umbrella design approved; per-layer designs pending
**Scope:** Top-level architecture only. Each layer gets its own brainstorm, spec and plan
that references this document.

Terms used here — stage, step, gate, acceptance, profile, overlay, workstate, ship — are
defined in [`CONTEXT.md`](../../../packages/wl-harness/CONTEXT.md) and used in exactly that sense.

---

## 1. Problem

The author built an i18n-cms almost entirely through agents, but the process required
constant back-and-forth: re-explaining stack choices, correcting file placement, redoing
UI details, and re-litigating decisions that had already been made earlier in the session.

The cost is not "the agent cannot write code." The cost is that **the agent does not know
the author's rules**, and any rule expressed only as a prompt decays once the context is
compacted — exactly when a long task needs it most.

## 2. Goal

`wl-harness` is an opinionated, contract-driven harness built on top of Claude Code. It
turns the author's stack preferences and delivery workflow into **hard gates**, so agents
build it right the first time.

Precisely: it is an *application-level* harness. Claude Code provides the runtime
primitives (tool execution, context management, hook dispatch); `wl-harness` provides the
domain layer — contracts, workflow, state and guardrails.

### Non-goals

- Rebuilding anything Claude Code already provides (tool execution, subagents, context
  compaction, permissions).
- Supporting every technology. Extensibility is guaranteed by mechanism (§7), not by
  shipping every profile.

The relationship to superpowers is **not yet decided**; see §16 (D-1).

## 3. Six-layer architecture

**This is a map of responsibility, not a build order.** See §15 for how it is actually
built, and [ADR-0002](../../adr/0002-walking-skeleton-over-layer-order.md) for why.

| Layer | Responsibility | Artifacts |
|---|---|---|
| **L1 Information boundary** | Role and goal definition, information isolation, contract schema, context injection | `contracts/schema.json` (frontmatter contract: `id` / `type` / `status` / `role`); the three skill roles; subagent and worktree isolation boundaries; generated project `CLAUDE.md` / `AGENTS.md`; injection of profile data and `tsconfig` strictness into the agent's context before generation |
| **L2 Tool system** | Filesystem abstraction, execution environment, MCP mounting | `scripts/*.mjs` (cross-platform, replaces bash); CodeGraph MCP (symbol graph, impact analysis); dependency-cruiser (dependency graph and bans); hook runtime |
| **L3 Execution orchestration** | Stage sequencing, state machine orchestration | `commands/`: `init-project`, `feature-dev`, `bug-fix`, `ship`; step-ised commands; quick/deep split inside `feature-dev`; concurrency decomposition fed by CodeGraph impact |
| **L4 Memory and state** | Task state, cross-session memory, context compaction | `workflow-state.md` (frontmatter for machines, body for humans); `timing-state.json`; `workstate/{processing,testing,shipped}/{slug}.md` state machine; `references/` preference library; skill dedup |
| **L5 Evaluation and observability** | Independent verification, sandboxed testing, observability | Structured `acceptance` field on every step; `verify` skill; `integrated-test` skill; git worktree as sandbox; `harness-check.mjs`; timing logs summarised into the shipped document |
| **L6 Constraints, validation, recovery** | Red lines, hard gates, rollback | `contracts/project-rules.json`; PostToolUse / PreToolUse hook gates; idempotent scripts with a re-entry guard; `ship-snapshot` document rollback; git for code rollback; forward-only migration policy |

### Mapping from the reference five-layer design

The author's company uses a five-layer structure organised by *implementation*. This design
is organised by *concern*, so the mapping is one-to-many. Every company layer has a home;
nothing was dropped.

| Company layer | Lands in |
|---|---|
| L1 Contract | **L1** (frontmatter type system) + **L6** (validator enforcement) |
| L2 Workflow | **L3** (step-ised commands) |
| L3 Behaviour constraint | **L1** (role taxonomy) + **L5** (automatic precondition checks) + **L6** (hard gates) |
| L4 External integration | **L2** (MCP and tools) + **L3** (delegation points) |
| L5 Session lifecycle | **L4** (state and memory) + **L6** (interruption recovery) |

## 4. Stage spine

Every work item travels the same spine. Commands differ in the **depth** of each stage,
never in which stages they have. One vocabulary means one resumption mechanism, one place
to answer "what does this stage need", and one coordinate system for the per-layer designs.

| # | Stage | What happens | Done when |
|---|---|---|---|
| 1 | **Intake** | Choose the path (init / feature-quick / feature-deep / bug), mint the slug, open the workstate | `processing/{slug}.md` exists |
| 2 | **Context load** | Inject profile data, `tsconfig` strictness, `references/`, CodeGraph state, prior shipped documents | The context manifest is declared |
| 3 | **Design** | Requirement → approach (deep and init paths only) | A spec exists |
| 4 | **Plan** | Decompose into steps; declare `acceptance` and `artifacts`; decompose for concurrency | `steps` ↔ `^N.` aligned |
| 5 | **Implement** | Write code | The declared `artifacts` exist |
| 6 | **Verify** | Run `acceptance`; report pass/fail | All assertions pass |
| 7 | **Handoff** | Hard gate, then `processing → testing` | `testing/{slug}.md` committed |
| 8 | **Ship** | Confirm conformance to spec, archive → `shipped` | `shipped/{slug}.md` committed |

**Stages 5 and 6 form a loop.** Implement → Verify → on failure back to Implement, until
the assertions pass. The loop is machine-judged and the agent repairs its own work inside
it; no human is involved. The loop's exit is stage 7.

Every path runs every stage — **spec → plan → code is a discipline applied to one work
item, not a project-wide waterfall.** The item is small (one slug), the spec states intent
and acceptance rather than implementation, and stage 3 scales down to a few lines rather
than disappearing. What differs between commands is depth, not presence:

| Command | Stage 3 (Design) produces | Stage 4 (Plan) depth |
|---|---|---|
| `init-project` | Selection is fixed by complexity tier; page/route structure is the real design work | Scaffold steps |
| `feature-dev` deep | Full design exploration | Multi-step, concurrency-decomposed |
| `feature-dev` quick | A few lines: intent + acceptance, plus a required `spec:` pointer to the existing spec this change refines (§5) | 1–3 steps |
| `bug-fix` | A diagnosis, classified as **breach** (spec said X, code doesn't) or **gap** (spec never said) — see §5 | 1–2 steps; step 1 is always "write a test that reproduces the failure" |

Stage 7 is the last thing every command does before stage 8. **Stage 8 is a separate,
author-initiated act** — see §5 and §12.

## 5. Workflow paths

Tiers were deliberately dropped. The path itself carries the process weight.

| Command | When | Weight |
|---|---|---|
| `init-project` | 0 → 1, empty repository | Always deep: selection, scaffold, design tokens, base components |
| `feature-dev` | Iterating on an existing project | Split **quick / deep**: quick when the flow being changed already exists in the repo; deep when a new subsystem or interface change is required |
| `bug-fix` | Defect repair | Light |
| `ship` | Conformance check and archival | First-class citizen; `abort` and `skip <reason>` subcommands |

Commands are step-ised: the `steps` array in frontmatter must match the `^N.` lines in the
body one-for-one. This is what makes a run resumable at a breakpoint.

### `ship` is conformance, not synchronisation

The spec is authoritative; code is its product. `/ship` verifies that the delivered code
conforms to its spec and archives the work item. It does **not** rewrite the spec to match
what was built — a document that is edited to agree with the code has stopped constraining
anything, which is the failure mode §1 describes. Where a spec genuinely needs to change,
that is an explicit act recorded in `shipped/{slug}.md`: which clause changed, and why.

(Large, long-lived systems do maintain an as-built architecture description alongside a
spec. Those are two documents, each written in one direction. That is not bidirectional
synchronisation, and it does not change the rule above.)

### The authoritative document, per path

Every path is authoritative against *some* document; which one differs:

| Path | Authoritative document |
|---|---|
| `init-project`, `feature-dev` deep | The spec written in stage 3 |
| `feature-dev` quick | The **parent spec** it points at via a required `spec:` field, set in stage 1. Quick exists because the flow being changed already exists in the repo (§4) — so a spec covering it should already exist. If none can be found, that gap is itself informative: fall back to the step's `acceptance`/`artifacts` as the authoritative document instead of inventing a spec after the fact |
| `bug-fix` | The existing spec the bug is diagnosed against, classified in stage 3 as: **breach** (the spec says X, the code doesn't) — fixed without touching the spec; or **gap** (the spec never said) — fixing it makes a decision for the first time, and that decision needs an amendment (below) |

### Amendments must be cheap, and must not be the agent's call

A spec will sometimes turn out to be wrong once coding starts, or a bug turns out to be a
gap rather than a breach. Both require changing the authoritative document mid-flight. Two
rules, in tension on purpose:

- **Cheap.** An amendment is one line in `shipped/{slug}.md` — which clause changed, and
  why — not a re-entry into stage 3. If amending is as expensive as the original design
  pass, it will be avoided, and an avoided amendment is exactly how a spec quietly stops
  matching the code (the failure this whole section exists to prevent).
- **Gated.** Per §10, changing the document that constrains the agent is an irreversible,
  in-repo action: the agent may *propose* an amendment, but the author confirms it before
  the plan proceeds. A pure refinement — `feature-dev` quick adding detail within its
  parent spec's scope, or a `bug-fix` breach that needs no spec change — does not touch the
  authoritative document and does not stop for confirmation. Only the moment the document
  itself would change does.

A spec is written to state intent and acceptance, not implementation — "sorted by
publish date, paginated, unpublished posts excluded" rather than "use `getStaticProps`, 10
per page, a `<Pagination>` component". The closer a spec sits to implementation, the more
often coding will contradict it. If a given slug needs more than two amendments, treat that
as a signal the spec was written at the wrong altitude rather than as a process failure to
route around.

## 6. Stack preference dictionary

This is *content*, orthogonal to the six layers. It is split by a single test:
**anything expressible as an assertion belongs to L1/L6; anything requiring judgement
belongs to the reference documents an agent reads before generating.**

### 6.1 Selection dimensions

| Dimension | Values | Decision basis |
|---|---|---|
| Form | frontend-only / fullstack / backend-only | Does it own persistence? |
| Rendering | CSR → **Vite + React**; SSR/SSG/ISR → **Next.js (App Router)** | Login-gated tools are CSR; SEO, first paint or static sites are Next |
| Complexity | S / M / L | S = single user, no auth, ≤5 pages; M = multi-module CRUD with login; L = multi-role permissions, multi-tenant, complex flows |

### 6.2 Complexity to stack

The table below is the author's current preference. **It is not a lookup table in the
skeleton**: it lives inside each profile as a `complexity` object, so that adding a stack
means writing its own S/M/L slice rather than editing a shared matrix (§7).

| | S | M | L |
|---|---|---|---|
| State | Context + useState | zustand (client) + TanStack Query (server) | as M, store split per module |
| Backend | Next Route Handlers, or none | Next Route Handlers (Vercel-first) | Next Route Handlers; split out a service only when genuinely required |
| DB / ORM | SQLite + Prisma | Postgres (Neon) + Prisma | Postgres (Neon) + Prisma |
| Auth | none / simple token | cookie session or JWT + route guards | RBAC with permission points |
| Testing | key utils unit-tested | vitest + core flows | vitest + Playwright |

Fixed regardless of complexity: TypeScript strict, react-hook-form + zod (one schema for
form validation and types), dayjs, a single axios instance with interceptors,
ESLint + Prettier, pnpm.

### 6.3 Preferred routes, in order

1. **Next.js fullstack** — one profile, native to Vercel
2. **PERN / MERN** — `frontend-react-vite` + `backend-node-express`; PERN and MERN differ
   only in the `db` parameter (postgres + Prisma / mongo + Mongoose), not in the profile
3. **React + Python** — `frontend-react-vite` + `backend-python-fastapi`

Go and Java are not enabled. That fact is a `enabled: false` field on their profiles, not
a special case in the selection logic — selecting a disabled profile prompts the author for
explicit confirmation, and the skeleton never learns the words "Go" or "Java".

### 6.4 Directory conventions

Frontend:

```
src/
  app/ | pages/     routing
  components/       presentational, no business logic, reusable
  containers/       data-bound / business composition
  hooks/
  services/         request layer, one file per module
  store/            zustand
  types/            aligned with backend schemas
  styles/           variables, mixins, globals
  utils/
public/  .env.*
```

Backend (layered MVC variant — there is no view layer):

```
src/
  routes/        URL to controller mapping only
  controllers/   parse input, call service, shape response; no business logic
  services/      business logic; the only place rules may live
  repositories/  data access; the only place that touches the ORM
  schemas/       zod DTOs, the request/response contract
  middlewares/   auth, error handling, logging
  config/  utils/
prisma/schema.prisma
```

**Iron rules:** controllers never touch the ORM; services never touch `req`/`res`.

### 6.5 Styling and components

- CSS priority: **Less > Sass > CSS Module**. Component styles are always `*.module.less`.
  Globals hold only variables, reset and theme.
- All business code imports UI primitives **only** from `components/ui/`.
  - Complexity S: Ant Design, still wrapped behind `components/ui/`.
  - Complexity M/L: Radix headless primitives + hand-built Less tokens — Modal, Input,
    Button, Link, Radio, Select, Tooltip, Table, Form.
- Consequence: swapping the underlying library touches one directory. Style discussion is
  confined to `components/ui/` and the token file, and never leaks into pages. This is the
  designed cure for the "UI needs another round of tweaks" loop.

### 6.6 Deployment

Guiding principle: **do not introduce a second platform unless forced to.**

| Tier | When | Frontend | Backend | DB |
|---|---|---|---|---|
| Default | Most cases | Next.js | Route Handlers in the same project | Neon |
| Second | Vite React is wanted (pure CSR, no SEO) | Static build on Vercel | **Vercel Functions** (Node or Python) in the same repo | Neon |
| Fallback | A long-running process is required: WebSocket, cron, long jobs, model inference | Vercel | Render / Fly.io | Neon / Supabase |

Only the fallback tier introduces a second platform, and the free tier sleeps
(tens of seconds of cold start). The selection step must state that cost before choosing it,
and choosing it requires the author's confirmation (§11).

Free-tier terms change often, so the dictionary records **platform names and the reason to
pick them**, never quota numbers. Current terms are checked at deployment time.

Monorepo (`apps/` + `packages/`, with `packages/shared` holding zod schemas used by both
sides) is used only when a genuinely separate service exists. Small and frontend-only
projects stay single-package.

## 7. Profile mechanism and the overlay rule

Stacks are **data, not code**. The skeleton — `commands/`, `skills/`, `scripts/`,
`contracts/` — does not know the word "Next.js". Selection dimensions, complexity slices
and the enabled flag all live inside profiles, so that adding a technology is a data change.

```
references/profiles/
  <id>.json    machine-readable: enabled, complexity slices, checkers, layout, bans, verify
  <id>.md      human/agent-readable: rationale, idioms, known pitfalls
```

`references/` is deliberately full of stack names — it is what an agent reads in order to
judge. The no-stack-names rule applies to the skeleton only.

```json
{
  "id": "backend-node-express",
  "kind": "backend",
  "enabled": true,
  "match": ["apps/api/**"],
  "complexity": {
    "S":  { "db": "sqlite",   "testing": ["vitest"] },
    "M":  { "db": "postgres", "testing": ["vitest"] },
    "L":  { "db": "postgres", "testing": ["vitest", "playwright"] }
  },
  "checks": { "**/*.ts": ["pnpm tsc --noEmit", "pnpm eslint --max-warnings=0"] },
  "layout": ["routes", "controllers", "services", "repositories", "schemas", "middlewares"],
  "forbidden": [
    { "from": "controllers/**", "to": "@prisma/client",
      "why": "controllers must not touch the ORM" }
  ],
  "verify": ["pnpm test:integration"],
  "deploy": "vercel-functions",
  "migration_policy": "forward-only",
  "overridable": ["db", "complexity", "deploy"]
}
```

### The overlay rule

A project declares its profiles in one file:

```json
// <project>/.claude/harness.json
{ "profiles": ["frontend-react-vite", "backend-node-express"],
  "complexity": "M",
  "db": "postgres" }
```

**A profile is the source of defaults; the overlay may tighten it, never relax it.**
Two mechanically checked rules:

1. **Sealed fields.** Only fields listed in the profile's `overridable` array may appear in
   the overlay. `forbidden`, `layout` and `migration_policy` are always sealed.
2. **Tighten-only merge.** Array fields merge as a union, never a replacement. An overlay
   can add a ban; it cannot remove one.

Without this, an agent — which is able to edit the committed `harness.json` — could
disable the red lines that constrain it by writing `"forbidden": []`. Rationale in
[ADR-0001](../../adr/0001-overlay-tightens-only.md).

An overlay that departs from the profile default must be *announced*: `init-project`
states "you have overridden the S-tier default of SQLite" rather than silently applying it.

### Consumption

| Layer | How it consumes a profile |
|---|---|
| L1 context injection | Inject `layout`, `complexity[level]` and `tsconfig` strictness before generation |
| L2 hooks | Route check commands by the `checks` globs |
| L3 commands | "Create directories per `profile.layout`" — never a hard-coded directory name |
| L5 acceptance | Run `profile.verify` — never a hard-coded `pnpm test` |
| L6 red lines | Feed `forbidden` to dependency-cruiser |

Preconditions route checkers by file extension: `.ts`/`.tsx` → `tsc --noEmit` + eslint;
`.py` → ruff + mypy.

### The assumption this rests on

**The development process is identical across stacks; only the tools and languages differ.**
Every profile-shaped design decision above depends on this being true. It is currently
*assumed*, not verified — the initial scope (§15) is React, Next.js, Node + Express and
Python FastAPI, possibly JavaScript only at first, which is a narrow enough range that the
assumption is very likely to hold.

It is the kind of assumption that fails silently. If a stack turns out to need a stage the
spine does not have, or a step ordering the others do not, **the profile mechanism itself
needs redesigning, not patching**. The check that would detect this — scaffolding from a
synthetic profile with fictional directory names and asserting the output matches it
exactly — is deferred to the slice that introduces the second profile (§16, D-3).

**Caveat:** the architecture guarantees any stack *can* be plugged in. The quality of a
plugged-in stack depends entirely on how well its profile is written.

## 8. Directory layout

### Plugin

```
packages/wl-harness/
├── .claude-plugin/plugin.json
├── contracts/                          L1 + L6
│   ├── schema.json                     single source of truth
│   ├── schema.md                       GENERATED — do not hand-edit
│   └── project-rules.json              red lines
├── commands/                           L3
│   └── init-project.md  feature-dev.md  bug-fix.md  ship.md
├── skills/                             L1 roles / L3 delegation / L5 verification
│   ├── typescript-eslint-check/  ship-guard/          [precondition]
│   ├── init-project/  feature-dev/  bug-fix/          [delegating]
│   └── prd-to-trd/  parallel-implementation/
│       verify/  integrated-test/                      [capability]
├── references/                         L4 preference library
│   ├── tech-stack.md  conventions.md  ui-system.md
│   └── profiles/<id>.{json,md}
├── hooks/                              L6 hard gates
│   ├── hooks.json
│   ├── post_tool_use_check.mjs         per-file lint after a write
│   ├── pre_tool_use_gate.mjs           intercept `gh pr create`; deny if not shipped
│   └── session_start_resume.mjs        read workflow-state, inject "you are on stage N"
└── scripts/                            L2 tools
    └── harness-check.mjs  workflow-state.mjs
        ship-snapshot.mjs  timing.mjs
```

All scripts are `.mjs`, never `.sh`. The author develops on Windows; bash-only scripts
break pre-commit hooks there, and Node is already a dependency of every supported stack.

### Runtime files in a target project

```
<project>/.claude/
├── harness.json                   COMMIT      profile declaration and overlay
├── workflow-state.md              gitignore   progress (frontmatter machine-readable)
├── timing-state.json              gitignore   timing
├── logs/{slug}.jsonl              gitignore   per-step detail
├── ship-snapshot/                 gitignore   {sha7}-{slug}-{trd,spec,plan}.md
└── workstate/
    ├── processing/{slug}.md       gitignore   in progress
    ├── testing/{slug}.md          COMMIT      machine-verified, awaiting the author
    └── shipped/{slug}.md          COMMIT      accepted and archived, includes timing summary
```

Consequence of not committing `processing/`: work in progress cannot be resumed on a
different machine. Acceptable for single-machine development.

## 9. Gates and acceptance

Rules are only real if something rejects a violation. But **not every check is a
rejection**, and conflating the two is what makes an enforcement model incoherent.

- A **gate** answers *"is this allowed?"*. Failing it means something is wrong. A gate
  blocks.
- An **acceptance** answers *"is this done?"*. Failing it means work remains. An
  acceptance reports, and the Implement ⇄ Verify loop repairs.

Type errors are the clearest case. A half-finished refactor fails `tsc` because it is
half-finished, not because a rule was broken — so `tsc` is an acceptance criterion, and
treating it as a gate would have the agent "fixing" code it is about to rewrite.

### Gates (a violation is rejected)

| Constraint | Mechanism | Why a gate |
|---|---|---|
| Contract compliance: frontmatter fields, `steps` ↔ `^N.`, id uniqueness, referenced ids exist, every step declares `acceptance` | `harness-check.mjs` | Mechanically decidable; a malformed contract is always wrong |
| Overlay does not touch sealed fields, and only tightens (§7) | `harness-check.mjs` | The agent must not be able to relax its own constraints |
| Layering bans (`forbidden`) | dependency-cruiser via `harness-check.mjs` | Reachability on a graph; a violation is never "in progress" |
| Per-file lint and formatting | PostToolUse hook | Single-file decidable, milliseconds, never a false positive on partial work |
| Entering `testing` requires acceptance to be green | Stage 7 precondition | This is the real gate: what is guarded is the *state transition*, not the type checker |
| PR creation requires a shipped item | PreToolUse hook intercepting `gh pr create` | Rare, high-consequence, trivially decidable |

### Acceptance (a failure means unfinished)

| Criterion | When | Behaviour on failure |
|---|---|---|
| `tsc --noEmit` passes | Stage 6, and again as the stage-7 precondition | Reported in the pass/fail summary; the loop repairs it. Never blocks a file write |
| `profile.verify` commands pass | Stage 6 | As above |
| Declared `artifacts` exist | Stage 6 | As above |

`tsconfig` strictness is additionally read at **stage 2** and injected into the agent's
context, so that generated code is born conformant. That injection is an L1 *input*, not a
check — it rejects nothing.

### Defence in depth

Three lines, increasing in cost: **PostToolUse hook** (immediate, per-file) → **pre-commit**
(`simple-git-hooks`) → **CI** (GitHub Actions, in case local hooks are bypassed).

`schema.md` is generated from `schema.json` rather than hand-written, because a
hand-written specification alongside a separate validator is itself a source of drift.

Not machine-decidable, and therefore expressed as prompt in precondition skill bodies:
stack selection, UI judgement, layering intent. Skill dedup within a session is prompt plus
a session state file, with one reload permitted after compaction; a hook would cost more
than it saves.

## 10. Human-in-the-loop boundary

The agent proceeds on its own except where an action is hard to undo. The rule is derived,
not enumerated, so that a newly encountered action can be placed without updating a list:
**can git undo it, and does it cross the repository boundary?**

| | Reversible | Irreversible |
|---|---|---|
| **Inside the repo** | Write or edit files, run tests, run lint → **proceed** | Delete files, edit `harness.json`, edit red lines, write a migration → **ask** |
| **Outside the repo** | Install a dependency, run a local dev server → **proceed** | `git push`, open a PR, deploy, introduce a second platform, touch a production database → **ask** |

The load-bearing case is the top-right cell: **the agent must not silently modify what
constrains the agent.** The overlay rule (§7) makes this structural rather than a matter of
asking politely.

The bottom-left cell is deliberately permissive. A harness that confirms every action
becomes the interruption-heavy experience §1 exists to eliminate.

## 11. Recovery model

Three independent mechanisms with explicit boundaries. Conflating them is the most likely
source of a bad incident.

| What is being recovered | Mechanism |
|---|---|
| **Workflow position** | Idempotent scripts + re-entry guard. In-process state is downgraded to file state: read `workflow-state.md` frontmatter first — if a run is in progress, continue from the current stage and step; otherwise start fresh. Nothing depends on shell variables, so compaction and session re-entry are survivable. |
| **Documents** (TRD / spec / plan) | Before modifying any of them, copy to `.claude/ship-snapshot/{sha7}-{slug}-{trd,spec,plan}.md`. `/ship abort` restores from the snapshot and deletes it; `/ship skip <reason>` does the same but records the reason. On success the snapshot is removed. A stale snapshot found at the start of a `/ship` run prompts: abort or resume? |
| **Code** | git branches. `/ship abort` does **not** revert code. |
| **Database migrations** | **Forward-only.** Never delete or roll back a migration; generate a compensating one. The development database may be reset and rebuilt at will. Without this rule an agent will delete migration files and desynchronise schema from code — the hardest class of failure to diagnose. |

**The workstate needs no rollback mechanism.** Each state transition is the *last* side
effect of the command that performs it: stage 7 moves `processing → testing` after its gate
passes, and stage 8 moves `testing → shipped` after the author accepts. An aborted `/ship`
therefore finds the state machine untouched — there is no committed intermediate state to
undo, which is why `testing/` can be committed safely.

The snapshot filename includes the slug because a second ship under the same commit would
otherwise overwrite the first.

## 12. Observability

- Every step declares `acceptance` as a list of executable assertions, and `artifacts`
  as the paths it is expected to produce. This makes acceptance criteria a checkable
  contract rather than prose, and lets `harness-check.mjs` assert that no step is missing
  its criteria.
- Backend steps must express acceptance as executable assertions (integration tests
  passing), and must produce `docs/api.md`. The author is not a backend specialist; review
  happens against an interface list and a test result, not against source code. **This is
  what the `testing` state is for**: the machine loop has finished, and the author has not
  yet looked.
- Backend verification runs against an in-memory SQLite database, not Docker, to stay
  inside a hobby-tier setup.
- Timing is appended to `.claude/logs/{slug}.jsonl` (gitignored) and summarised into the
  committed `shipped/{slug}.md` on completion, so "how long does this class of work
  usually take" is answerable months later.

## 13. External integration

| Dependency | Used for | Status |
|---|---|---|
| superpowers | Process skills: brainstorming, planning, execution, TDD, code review, worktrees | **Positioning undecided** — see §16 (D-1). The technical constraint is known: skills that carry their own orchestration compete with `workflow-state.md`, while interactive skills that return without advancing state do not |
| CodeGraph MCP | Structural memory: symbol lookup, call paths, `impact` for concurrency decomposition | Installed (`@colbymchenry/codegraph` v1.6.0), wired into Claude Code globally |
| dependency-cruiser | Dependency graph and forbidden-rule enforcement | Planned |
| A semantic "codebase-memory" store | — | **Rejected for now.** Structural memory is covered by CodeGraph; semantic memory is already covered by `workstate/shipped/*.md` plus specs and plans, which are committed, reviewable and state-machine managed. A second store would compete for the role of "source of decision truth" and would silently go stale. Re-evaluate only if the workstate documents prove insufficient in practice. |

## 14. Language rule

All written artifacts are in English: skills, specs, plans, READMEs, API docs, code
comments, commit messages. Conversation with the author is in Chinese. Generated project
`CLAUDE.md` files must restate this rule so downstream agents inherit it.

## 15. Implementation strategy

**Breadth-first, as a walking skeleton.** Cut the thinnest possible hole through all six
layers, run one real work item end to end, then deepen each layer against what that run
taught. §3 is a map, not a schedule. Rationale in
[ADR-0002](../../adr/0002-walking-skeleton-over-layer-order.md).

The first slice, S0, touches every layer at minimum depth. The target command is
`init-project`, at complexity S only (M/L wait for S4) — it doubles as bootstrapping the
author's own site, which S0 needs as a real object to act on. All eight stages run (§4:
every path runs every stage); what's thin is each stage's content, not its presence:

| Layer | S0 |
|---|---|
| L1 | Frontmatter carries three fields — `id`, `type`, `steps`. No enumerations, no validator |
| L2 | One `.mjs` that reads and writes `workflow-state.md`. No MCP |
| L3 | One command, `init-project`, complexity S only. All 8 stages run; stage 3 (Design) is thin because S-tier selection is fixed — only page/route structure is a real decision |
| L4 | `workflow-state.md` records the current position and nothing else |
| L5 | One acceptance criterion: `tsc` passes |
| L6 | One red line, in one hook |

Subsequent slices, each end-to-end runnable:

| Slice | Adds |
|---|---|
| **S1** | Stage 8 — `/ship`, the workstate state machine, `ship-snapshot` rollback |
| **S2** | A second profile. **The profile abstraction is extracted here**, forced out by a real second case rather than designed in advance. §7's assumption gets its first test |
| **S3** | The full gate set: hooks, `harness-check.mjs`, dependency-cruiser |
| **S4** | `init-project`, `bug-fix`, CodeGraph concurrency decomposition, timing |

Initial stack scope is deliberately narrow: React, Next.js, Node + Express, Python FastAPI —
and JavaScript only in the earliest slices.

## 16. Deferred decisions

Decisions consciously postponed, with what unblocks them. **A question listed here is not
an oversight**; reopening one early costs more than it saves.

| # | Deferred | Unblocked by |
|---|---|---|
| **D-1** | The relationship to superpowers: full delegation, selective delegation, or none — and which skill, tool or MCP each stage uses | S0 running. The stage spine has to exist before its stages can be equipped. The technical line, when the question is reopened, is whether a skill carries its own orchestration |
| **D-2** | L1 contract detail: `type` and `status` enumerations, the shape of a `steps` entry, whether `role` is its own field, how a generated `AGENTS.md` differs from `CLAUDE.md` | S0 running. These are exactly the questions a real run answers and abstract design guesses at — the reason for ADR-0002 |
| **D-3** | Automated verification that the skeleton is free of stack knowledge: a synthetic-profile golden test, plus a narrow assertion that no profile `id` appears under `commands/`, `skills/`, `scripts/` or `contracts/` | S2, the second profile |
| **D-4** | L2: which MCP servers each project kind mounts, and whether that list is itself a profile field; dependency-cruiser as library or CLI | S3 |
| **D-5** | L5: the acceptance assertion vocabulary; how a failed assertion is reported and retried; what the timing summary contains | S0 running, refined in S3 |
| **D-6** | L6: the full red-line list per profile; hook failure ergonomics (retries before handing back to the author); stale snapshot detection detail | S3 |
| **D-7** | L4: the skill dedup state file format; what qualifies as long-term memory versus per-task state; behaviour immediately after context compaction | S1, once the state machine is real |

### Test-first development

Spec-driven development and TDD are likely future working styles. One decision about them
is made now, because it concerns the shape of the spine and the spine is the root:

**Test-first is an execution strategy *within* the Implement stage, not a stage of its
own.** When it is introduced, it is expressed as a step-level strategy field; the stage
spine does not change. No such field is being added today — per ADR-0002, contract fields
are grown from real runs, not anticipated.

This note exists so that a future reader does not look at `Plan → Implement ⇄ Verify`,
conclude that tests have no home, and modify the spine.

The spec-authority half of the question is *not* deferred: it is settled in §5.

---

## Appendix: decisions and their reasons

| Decision | Reason |
|---|---|
| Named `wl-harness` | It satisfies all six criteria of a harness: behaviour boundaries, tooling, orchestration, state, verification, recovery. It is an application-level harness on top of Claude Code, not a replacement for it. |
| One stage spine, commands differ in depth | One vocabulary for resumption, one place to answer "what does this stage need", one coordinate system for the per-layer designs. Every path runs spec → plan → code; skipping stages for a "lighter" path was rejected because it produces code with no authoritative document to ship against. |
| Spec → plan → code is per-item, not per-project | The item is small (one slug) and the spec states intent, not implementation — that is what keeps the discipline from becoming a waterfall. |
| Amendments are cheap but gated | Cheap so an outdated spec is actually corrected rather than quietly ignored; gated because the agent must not be the one deciding its own constraining document changed (§10). |
| Tiers dropped, three paths kept | The path carries the weight. Only `feature-dev` has real internal variance, handled by a single quick/deep split. |
| `init-project` added | `feature-dev` and `bug-fix` both assume the project exists. The original pain — building a new project fast — had no entry point. |
| Gates separated from acceptance | "Not finished" is not "not allowed". Merging them makes `tsc` block half-finished refactors, which teaches the agent to ignore the check. |
| The gate guards the *state transition*, not the type checker | What must not happen is entering `testing` with unfinished work. `tsc` is one of that gate's criteria, not a gate in itself. |
| `testing` is a real state with a human in it | §12: the author reviews backend work against an interface list and a test result. That review needs a moment to happen in. |
| `/ship` is conformance, not synchronisation | A spec edited to agree with the code has stopped constraining anything — the failure §1 describes. |
| State transitions are the last side effect of their command | Makes workstate rollback unnecessary: an aborted ship finds nothing committed to undo. |
| Profile is the default, overlay only tightens | The agent can edit the committed overlay. A symmetric override would let it switch off its own red lines. See ADR-0001. |
| Human-in-the-loop derived from a rule, not a list | A rule places newly encountered actions without maintenance; a list goes stale and grows into a confirmation dialog for everything. |
| Selection dimensions live inside profiles | A shared S/M/L matrix in the skeleton would have to be edited for every new stack, which is exactly the leak §7 forbids. |
| Breadth-first walking skeleton | The contract's open questions can only be answered by a real run, and the contract is the root — guessing it wrong invalidates everything declared against it. See ADR-0002. |
| Stack knowledge may be hardcoded until S2 | An abstraction extracted from one case is a guess. The second profile forces the real shape out. |
| All scripts `.mjs` | Windows. `cp`, `rm -f` and `${HEAD:0:7}` are bash-only and break pre-commit there. |
| `schema.json` is the source, `schema.md` is generated | A hand-written spec plus a separate validator drift apart. |
| `workflow-state.md` uses frontmatter rather than a separate JSON | One file, two readers: scripts parse the YAML frontmatter reliably, humans and agents read the body. |
| Timing stays in a separate `timing-state.json` / jsonl | High-frequency appends do not belong in frontmatter. |
| Vercel-first | The author deploys hobby projects on free tiers. This pushes fullstack work toward a single Next.js app and makes monorepos the exception rather than the default. |
| `db` is a profile parameter, not a profile | 2 frontends × 3 backends × 3 databases would be 18 files to maintain; parameterised, it is 5 profiles. |
| Semantic memory store rejected | Duplicates the role of committed workstate documents and goes stale invisibly. |
