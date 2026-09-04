# wl-harness — Architecture Design

**Date:** 2026-09-05
**Status:** Umbrella design approved; per-layer designs pending
**Scope:** Top-level architecture only. Each layer gets its own brainstorm, spec and plan
that references this document.

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
- Replacing superpowers. Its process skills are delegated to, not reimplemented.
- Supporting every technology. Extensibility is guaranteed by mechanism (§6), not by
  shipping every profile.

## 3. Six-layer architecture

| Layer | Responsibility | Artifacts |
|---|---|---|
| **L1 Information boundary** | Role and goal definition, information isolation, contract schema | `contracts/schema.json` (frontmatter contract: `id` / `type` / `status` / `role`); the three skill roles; subagent and worktree isolation boundaries; generated project `CLAUDE.md` / `AGENTS.md` templates |
| **L2 Tool system** | Filesystem abstraction, execution environment, MCP mounting | `scripts/*.mjs` (cross-platform, replaces bash); CodeGraph MCP (symbol graph, impact analysis); dependency-cruiser (dependency graph and bans); hook runtime |
| **L3 Execution orchestration** | Multi-step sequencing, state machine orchestration | `commands/`: `init-project`, `feature-dev`, `bug-fix`, `ship`; step-ised commands; quick/deep split inside `feature-dev`; concurrency decomposition fed by CodeGraph impact; delegation points into superpowers |
| **L4 Memory and state** | Task state, cross-session memory, context compaction | `workflow-state.md` (frontmatter for machines, body for humans); `timing-state.json`; `workstate/{processing,testing,shipped}/{slug}.md` state machine; `references/` preference library; skill dedup |
| **L5 Evaluation and observability** | Independent verification, sandboxed testing, observability | Structured `acceptance` field on every step; `verify` skill; `integrated-test` skill; git worktree as sandbox; `harness-check.mjs`; timing logs summarised into the shipped document |
| **L6 Constraints, validation, recovery** | Red-line rules, hard gates, rollback | `contracts/project-rules.json`; PostToolUse / PreToolUse hook gates; idempotent scripts with a re-entry guard; `ship-snapshot` document rollback; git for code rollback; forward-only migration policy |

### Mapping from the reference five-layer design

The author's company uses a five-layer structure organised by *implementation*. This design
is organised by *concern*, so the mapping is one-to-many. Every company layer has a home;
nothing was dropped.

| Company layer | Lands in |
|---|---|
| L1 Contract | **L1** (frontmatter type system) + **L6** (validator enforcement) |
| L2 Workflow | **L3** (step-ised commands) |
| L3 Behaviour constraint | **L1** (role taxonomy) + **L5** (automatic precondition checks) + **L6** (hard gates) |
| L4 External integration | **L2** (MCP and tools) + **L3** (superpowers delegation points) |
| L5 Session lifecycle | **L4** (state and memory) + **L6** (interruption recovery) |

## 4. Workflow paths

Tiers were deliberately dropped. The path itself carries the process weight.

| Command | When | Weight |
|---|---|---|
| `init-project` | 0 → 1, empty repository | Always deep: selection, scaffold, design tokens, base components |
| `feature-dev` | Iterating on an existing project | Split **quick / deep**: quick when the flow being changed already exists in the repo; deep when a new subsystem or interface change is required. Deep delegates to `superpowers:brainstorming`. |
| `bug-fix` | Defect repair | Light; delegates to `superpowers:systematic-debugging` |
| `ship` | Document/code synchronisation | First-class citizen; `abort` and `skip <reason>` subcommands |

Commands are step-ised: the `steps` array in frontmatter must match the `^N.` lines in the
body one-for-one. This is what makes a run resumable at a breakpoint.

## 5. Stack preference dictionary

This is *content*, orthogonal to the six layers. It is split by a single test:
**anything expressible as an assertion belongs to L1/L6; anything requiring judgement
belongs to the reference documents an agent reads before generating.**

### 5.1 Selection dimensions

| Dimension | Values | Decision basis |
|---|---|---|
| Form | frontend-only / fullstack / backend-only | Does it own persistence? |
| Rendering | CSR → **Vite + React**; SSR/SSG/ISR → **Next.js (App Router)** | Login-gated tools are CSR; SEO, first paint or static sites are Next |
| Complexity | S / M / L | S = single user, no auth, ≤5 pages; M = multi-module CRUD with login; L = multi-role permissions, multi-tenant, complex flows |

### 5.2 Complexity to stack

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

### 5.3 Preferred routes, in order

1. **Next.js fullstack** — one profile, native to Vercel
2. **PERN / MERN** — `frontend-react-vite` + `backend-node-express`; PERN and MERN differ
   only in the `db` parameter (postgres + Prisma / mongo + Mongoose), not in the profile
3. **React + Python** — `frontend-react-vite` + `backend-python-fastapi`

Go and Java are placeholders. They are not enabled; selecting one must prompt the author
for explicit confirmation, because they have not learned them yet.

### 5.4 Directory conventions

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

### 5.5 Styling and components

- CSS priority: **Less > Sass > CSS Module**. Component styles are always `*.module.less`.
  Globals hold only variables, reset and theme.
- All business code imports UI primitives **only** from `components/ui/`.
  - Complexity S: Ant Design, still wrapped behind `components/ui/`.
  - Complexity M/L: Radix headless primitives + hand-built Less tokens — Modal, Input,
    Button, Link, Radio, Select, Tooltip, Table, Form.
- Consequence: swapping the underlying library touches one directory. Style discussion is
  confined to `components/ui/` and the token file, and never leaks into pages. This is the
  designed cure for the "UI needs another round of tweaks" loop.

### 5.6 Deployment

Guiding principle: **do not introduce a second platform unless forced to.**

| Tier | When | Frontend | Backend | DB |
|---|---|---|---|---|
| Default | Most cases | Next.js | Route Handlers in the same project | Neon |
| Second | Vite React is wanted (pure CSR, no SEO) | Static build on Vercel | **Vercel Functions** (Node or Python) in the same repo | Neon |
| Fallback | A long-running process is required: WebSocket, cron, long jobs, model inference | Vercel | Render / Fly.io | Neon / Supabase |

Only the fallback tier introduces a second platform, and the free tier sleeps
(tens of seconds of cold start). The selection step must state that cost before choosing it.

Free-tier terms change often, so the dictionary records **platform names and the reason to
pick them**, never quota numbers. Current terms are checked at deployment time.

Monorepo (`apps/` + `packages/`, with `packages/shared` holding zod schemas used by both
sides) is used only when a genuinely separate service exists. Small and frontend-only
projects stay single-package.

## 6. Profile mechanism and the extensibility criterion

**Criterion: adding a new technology stack means adding 2 files and modifying 0 files.**
If that fails, stack knowledge has leaked into the skeleton and the architecture is wrong.

Stacks are **data, not code**. Layers L1–L4 do not know the word "Next.js".

```
references/profiles/
  <id>.json    machine-readable: checkers, layout, bans, verification commands
  <id>.md      human/agent-readable: rationale, idioms, known pitfalls
```

```json
{
  "id": "backend-node-express",
  "kind": "backend",
  "match": ["apps/api/**"],
  "checks": { "**/*.ts": ["pnpm tsc --noEmit", "pnpm eslint --max-warnings=0"] },
  "layout": ["routes", "controllers", "services", "repositories", "schemas", "middlewares"],
  "forbidden": [
    { "from": "controllers/**", "to": "@prisma/client",
      "why": "controllers must not touch the ORM" }
  ],
  "verify": ["pnpm test:integration"],
  "deploy": "vercel-functions",
  "migration_policy": "forward-only"
}
```

A project declares its profiles in one file:

```json
// <project>/.claude/harness.json
{ "profiles": ["frontend-react-vite", "backend-node-express"], "db": "postgres" }
```

Consumption:

| Layer | How it consumes a profile |
|---|---|
| L2 hooks | Route check commands by the `checks` globs |
| L3 commands | "Create directories per `profile.layout`" — never a hard-coded directory name |
| L5 verify | Run `profile.verify` — never a hard-coded `pnpm test` |
| L6 red lines | Feed `forbidden` to dependency-cruiser |

Preconditions route checkers by file extension: `.ts`/`.tsx` → `tsc --noEmit` + eslint;
`.py` → ruff + mypy; `.go`/`.java` → placeholder, not enabled.

**Caveat:** the architecture guarantees any stack *can* be plugged in. The quality of a
plugged-in stack depends entirely on how well its profile is written. `fullstack-nextjs`
will be detailed; a future `backend-go` profile will start as a rough skeleton.

## 7. Directory layout

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
│   ├── post_tool_use_check.mjs         after writing .ts/.tsx, run checks, feed failures back
│   ├── pre_tool_use_gate.mjs           intercept `gh pr create`; deny if not shipped
│   └── session_start_resume.mjs        read workflow-state, inject "you are on step N"
└── scripts/                            L2 tools
    └── harness-check.mjs  workflow-state.mjs
        ship-snapshot.mjs  timing.mjs
```

All scripts are `.mjs`, never `.sh`. The author develops on Windows; bash-only scripts
break pre-commit hooks there, and Node is already a dependency of every supported stack.

### Runtime files in a target project

```
<project>/.claude/
├── harness.json                   COMMIT      profile declaration
├── workflow-state.md              gitignore   progress (frontmatter machine-readable)
├── timing-state.json              gitignore   timing
├── logs/{slug}.jsonl              gitignore   per-step detail
├── ship-snapshot/                 gitignore   {sha7}-{slug}-{trd,spec,plan}.md
└── workstate/
    ├── processing/{slug}.md       gitignore   in progress
    ├── testing/{slug}.md          COMMIT      awaiting acceptance
    └── shipped/{slug}.md          COMMIT      delivered, includes timing summary
```

Consequence of not committing `processing/`: work in progress cannot be resumed on a
different machine. Acceptable for single-machine development.

## 8. Enforcement model

Rules are only real if something rejects a violation.

| Constraint | Mechanism | Why |
|---|---|---|
| Contract compliance (frontmatter fields, `steps` ↔ `^N.`, id uniqueness, referenced ids exist, every step declares `acceptance`) | `harness-check.mjs` | Mechanically decidable |
| `.ts`/`.tsx` must pass typecheck and lint | PostToolUse hook: run checks, feed failures back to the agent | High frequency, decidable, corrects in place without human involvement |
| PR creation requires `/ship` | PreToolUse hook intercepting `gh pr create` | Rare but high-consequence, trivially decidable |
| Layering bans | dependency-cruiser via `harness-check.mjs` | Reachability question on a graph |
| Stack selection, UI judgement, layering intent | Prompt, in precondition skill bodies | Not machine-decidable |
| Skill dedup within a session | Prompt + session state file; one reload permitted after compaction | Hook cost outweighs benefit |

Three lines of defence, increasing in cost: **PostToolUse hook** (immediate, most valuable
— the agent is corrected before the author ever sees the mistake) → **pre-commit**
(`simple-git-hooks`) → **CI** (GitHub Actions, in case local hooks are bypassed).

`schema.md` is generated from `schema.json` rather than hand-written, because a
hand-written specification alongside a separate validator is itself a source of drift.

## 9. Recovery model

Three independent mechanisms with explicit boundaries. Conflating them is the most likely
source of a bad incident.

| What is being recovered | Mechanism |
|---|---|
| **Workflow position** | Idempotent scripts + re-entry guard. In-process state is downgraded to file state: read `workflow-state.md` frontmatter first — if a run is in progress, continue from `current_step`; otherwise start fresh. Nothing depends on shell variables, so compaction and session re-entry are survivable. |
| **Documents** (TRD / spec / plan) | Before modifying any of them, copy to `.claude/ship-snapshot/{sha7}-{slug}-{trd,spec,plan}.md`. `/ship abort` restores from the snapshot and deletes it; `/ship skip <reason>` does the same but records the reason. On success the snapshot is removed. A stale snapshot found at the start of a `/ship` run prompts: abort or resume? |
| **Code** | git branches. `/ship abort` does **not** revert code. |
| **Database migrations** | **Forward-only.** Never delete or roll back a migration; generate a compensating one. The development database may be reset and rebuilt at will. Without this rule an agent will delete migration files and desynchronise schema from code — the hardest class of failure to diagnose. |

The snapshot filename includes the slug because a second ship under the same commit would
otherwise overwrite the first.

## 10. Observability

- Every step declares `acceptance` as a list of executable assertions, and `artifacts`
  as the paths it is expected to produce. This makes acceptance criteria a checkable
  contract rather than prose, and lets `harness-check.mjs` assert that no step is missing
  its criteria.
- Backend steps must express acceptance as executable assertions (integration tests
  passing), and must produce `docs/api.md`. The author is not a backend specialist; review
  happens against an interface list and a test result, not against source code.
- Backend verification runs against an in-memory SQLite database, not Docker, to stay
  inside a hobby-tier setup.
- Timing is appended to `.claude/logs/{slug}.jsonl` (gitignored) and summarised into the
  committed `shipped/{slug}.md` on completion, so "how long does this class of work
  usually take" is answerable months later.

## 11. External integration

| Dependency | Used for | Status |
|---|---|---|
| superpowers | brainstorming, writing-plans, executing-plans, subagent-driven-development, dispatching-parallel-agents, test-driven-development, verification-before-completion, requesting-code-review, using-git-worktrees, finishing-a-development-branch | Delegated to at declared points in commands; never reimplemented |
| CodeGraph MCP | Structural memory: symbol lookup, call paths, `impact` for concurrency decomposition | Installed (`@colbymchenry/codegraph` v1.6.0), wired into Claude Code globally |
| dependency-cruiser | Dependency graph and forbidden-rule enforcement | Planned |
| A semantic "codebase-memory" store | — | **Rejected for now.** Structural memory is covered by CodeGraph; semantic memory is already covered by `workstate/shipped/*.md` plus specs and plans, which are committed, reviewable and state-machine managed. A second store would compete for the role of "source of decision truth" and would silently go stale. Re-evaluate only if the workstate documents prove insufficient in practice. |

## 12. Language rule

All written artifacts are in English: skills, specs, plans, READMEs, API docs, code
comments, commit messages. Conversation with the author is in Chinese. Generated project
`CLAUDE.md` files must restate this rule so downstream agents inherit it.

## 13. Decomposition

This document is the umbrella. Each layer is brainstormed, specced and planned separately
and references this file. Suggested order, by dependency:

1. **L1 Information boundary** — the contract schema is the root; everything else declares
   against it.
2. **L3 Execution orchestration** — the three command paths; delivers the first usable
   value.
3. **L6 Constraints and recovery** — gates and rollback; content depends on L1 and L3.
4. **L5 Evaluation and observability** — acceptance execution and timing.
5. **L4 Memory and state** — state files exist from L3 onward; the deeper questions
   (cross-session memory, compaction strategy, skill dedup) are settled here.
6. **L2 Tool system** — most independent; last.

## 14. Open questions per layer

**L1** — exact enumerations for `type` and `status`; the `steps` object shape
(`id`, `name`, `acceptance`, `artifacts`, `preconditions`); whether `role` is a separate
field or encoded in `type`; how the generated `AGENTS.md` differs from `CLAUDE.md`.

**L2** — which MCP servers each project kind should mount, and whether that list is itself
a profile field; whether dependency-cruiser is invoked as a library or a CLI.

**L3** — the concrete step list for each of the three commands; the exact quick/deep
decision rule; how concurrency decomposition consumes CodeGraph `impact` output; where
each superpowers delegation point sits.

**L4** — the skill dedup state file format; what qualifies for long-term memory versus
per-task state; behaviour immediately after context compaction.

**L5** — the acceptance assertion vocabulary; how a failed assertion is reported and
retried; what the timing summary contains.

**L6** — the full red-line list per profile; hook failure ergonomics (how many retries
before handing back to the author); stale snapshot detection details.

---

## Appendix: decisions and their reasons

| Decision | Reason |
|---|---|
| Named `wl-harness` | It satisfies all six criteria of a harness: behaviour boundaries, tooling, orchestration, state, verification, recovery. It is an application-level harness on top of Claude Code, not a replacement for it. |
| Tiers dropped, three paths kept | The path carries the weight. Only `feature-dev` has real internal variance, handled by a single quick/deep split aligned with superpowers' bounded/architectural distinction. |
| `init-project` added | `feature-dev` and `bug-fix` both assume the project exists. The original pain — building a new project fast — had no entry point. |
| All scripts `.mjs` | Windows. `cp`, `rm -f` and `${HEAD:0:7}` are bash-only and break pre-commit there. |
| `schema.json` is the source, `schema.md` is generated | A hand-written spec plus a separate validator drift apart. |
| `workflow-state.md` uses frontmatter rather than a separate JSON | One file, two readers: scripts parse the YAML frontmatter reliably, humans and agents read the body. Consistent with "frontmatter is the contract" throughout the harness. |
| Timing stays in a separate `timing-state.json` / jsonl | High-frequency appends do not belong in frontmatter. |
| Vercel-first | The author deploys hobby projects on free tiers. This pushes fullstack work toward a single Next.js app and makes monorepos the exception rather than the default. |
| `db` is a profile parameter, not a profile | 2 frontends × 3 backends × 3 databases would be 18 files to maintain; parameterised, it is 5 profiles. |
| Semantic memory store rejected | Duplicates the role of committed workstate documents and goes stale invisibly. |
