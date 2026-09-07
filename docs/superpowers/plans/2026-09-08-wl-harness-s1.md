# wl-harness S1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move stack knowledge out of the commands into profile data, let `init-project` accept a document, make `workflow-state.md` resumable, and close the loop with `/ship` and its capture.

**Architecture:** S0's commands accumulated stack knowledge as prose until they read as project templates rather than process definitions. S1 extracts that into `references/profiles/fullstack-nextjs.{json,md}` so the commands describe only the process, then builds the three things whose shape is already settled by the spec: document intake for stage 3, resumption from the state file, and stage 8. The profile extraction runs first because everything else edits the same command files.

**Tech Stack:** Node 22 ESM (`.mjs`, zero external dependencies), `node:test`, Claude Code plugin commands and hooks.

**Spec:** `docs/superpowers/specs/2026-09-05-wl-harness-architecture-design.md`

## Global Constraints

- **Language:** every file committed to this repo is written in English — code, comments, docs, commit messages (spec §14, repo `CLAUDE.md`).
- **Zero external npm dependencies in `packages/wl-harness`.** Node's built-ins cover everything, including the test runner.
- **Script language is chosen by shape** (spec §8): orchestration in `.sh`, computation in `.mjs`. Everything here is computation, so `.mjs`.
- **Read files with line endings normalised.** `core.autocrlf` is `true` in this repo, so any checkout on Windows materialises files with CRLF while git reports them unchanged. Patterns anchored on `\n` silently stop matching — this already broke the step-alignment gate once.
- **Windows paths are passed as `argv` values, never interpolated into a `node -e` JS string.** Backslashes are consumed as escape sequences with no error, silently corrupting the path.
- **The stage spine does not change.** Eight stages, `intake` … `ship`; commands differ in the depth of each stage, never in which stages they have (spec §4).
- **After S1, no command file may name a framework, library, package manager or directory convention.** Those live in the profile. This is the criterion the whole slice is judged by.
- **Existing behaviour is preserved.** The profile extraction is a move, not a redesign: a run after Task 2 must produce the same project as a run before it.

---

## File Structure

**Created in `packages/wl-harness/`:**

| File | Responsibility |
|---|---|
| `references/profiles/fullstack-nextjs.json` | Machine-readable stack data: scaffold command, deps, layout, checks, verify, forbidden |
| `references/profiles/fullstack-nextjs.md` | The judgement half: why Less, why wrap antd, antd v5 theming, when to split a service |
| `scripts/profile.mjs` | Loads and validates a profile; resolves the overlay in `.claude/harness.json` |
| `scripts/profile.test.mjs` | Tests for the above |
| `scripts/capture.mjs` | Reads and writes the capture section of `workstate/shipped/{slug}.md` |
| `scripts/capture.test.mjs` | Tests for the above |
| `commands/ship.md` | Stage 8: conformance check, capture, archive |

**Modified:**

| File | Change |
|---|---|
| `commands/init-project.md` | Stack prose replaced by profile lookups; document intake added to stage 3; resumption added |
| `commands/feature-dev.md` | Same, minus document intake |
| `scripts/workflow-state.mjs` | `resumePoint()` added |
| `scripts/workflow-state.test.mjs` | Tests for `resumePoint()` |
| `docs/superpowers/specs/2026-09-05-wl-harness-architecture-design.md` | Slice table rewritten; §16 D-2 note on what S1 answered |

---

### Task 1: Profile loader

**Files:**
- Create: `packages/wl-harness/scripts/profile.mjs`
- Create: `packages/wl-harness/scripts/profile.test.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `loadProfile(pluginRoot: string, id: string): object` — reads `references/profiles/<id>.json`, throws if absent or malformed
  - `applyOverlay(profile: object, overlay: object): object` — merges a project's `.claude/harness.json`; **sealed fields are rejected, array fields merge as a union**
  - `SEALED_FIELDS: string[]` — `['layout', 'forbidden', 'migration_policy']`

The overlay rule is [ADR-0001](../../adr/0001-overlay-tightens-only.md): a profile is the source of defaults and an overlay may tighten it, never relax it. The agent can edit the committed `harness.json`, so a symmetric override would let it switch off its own red lines.

- [ ] **Step 1: Write the failing tests**

Create `packages/wl-harness/scripts/profile.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { SEALED_FIELDS, applyOverlay, loadProfile } from './profile.mjs';

function withPluginRoot(profile, fn) {
  const root = mkdtempSync(path.join(tmpdir(), 'wl-profile-'));
  try {
    mkdirSync(path.join(root, 'references', 'profiles'), { recursive: true });
    writeFileSync(
      path.join(root, 'references', 'profiles', 'demo.json'),
      JSON.stringify(profile),
      'utf8',
    );
    fn(root);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

const base = {
  id: 'demo',
  kind: 'fullstack',
  enabled: true,
  layout: ['app', 'components'],
  forbidden: [{ from: '!ui/**', to: 'antd', why: 'wrap it' }],
  verify: ['pnpm test'],
  overridable: ['deps'],
  deps: { runtime: ['antd'], dev: ['vitest'] },
};

test('loadProfile reads a profile by id', () => {
  withPluginRoot(base, (root) => {
    assert.equal(loadProfile(root, 'demo').id, 'demo');
  });
});

test('loadProfile names the id it could not find', () => {
  withPluginRoot(base, (root) => {
    assert.throws(() => loadProfile(root, 'missing'), /missing/);
  });
});

test('loadProfile rejects a profile with no id', () => {
  withPluginRoot({ kind: 'fullstack' }, (root) => {
    assert.throws(() => loadProfile(root, 'demo'), /id/);
  });
});

test('an overlay may set an overridable field', () => {
  const merged = applyOverlay(base, { deps: { runtime: ['vue'] } });
  assert.deepEqual(merged.deps.runtime, ['vue']);
});

test('an overlay may not touch a sealed field', () => {
  assert.throws(() => applyOverlay(base, { layout: ['whatever'] }), /layout/);
  assert.throws(() => applyOverlay(base, { forbidden: [] }), /forbidden/);
});

test('an overlay may not set a field absent from overridable', () => {
  assert.throws(() => applyOverlay(base, { verify: [] }), /verify/);
});

test('array fields merge as a union, so an overlay can add but not remove', () => {
  const merged = applyOverlay(
    { ...base, overridable: ['tags'], tags: ['a', 'b'] },
    { tags: ['b', 'c'] },
  );
  assert.deepEqual(merged.tags, ['a', 'b', 'c']);
});

test('the overlay leaves the original profile untouched', () => {
  const before = JSON.stringify(base);
  applyOverlay(base, { deps: { runtime: ['vue'] } });
  assert.equal(JSON.stringify(base), before);
});

test('SEALED_FIELDS names the three fields ADR-0001 seals', () => {
  assert.deepEqual([...SEALED_FIELDS].sort(), ['forbidden', 'layout', 'migration_policy']);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — `Cannot find module ... profile.mjs`.

- [ ] **Step 3: Write the implementation**

Create `packages/wl-harness/scripts/profile.mjs`:

```js
// A profile is the source of defaults; an overlay may tighten it, never relax
// it (ADR-0001). The agent can edit a project's committed harness.json, so a
// symmetric override would let it switch off the red lines that bind it.

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

export const SEALED_FIELDS = ['layout', 'forbidden', 'migration_policy'];

export function profilePath(pluginRoot, id) {
  return path.join(pluginRoot, 'references', 'profiles', `${id}.json`);
}

export function loadProfile(pluginRoot, id) {
  const filePath = profilePath(pluginRoot, id);
  if (!existsSync(filePath)) {
    throw new Error(`no profile named "${id}" at ${filePath}`);
  }
  const profile = JSON.parse(readFileSync(filePath, 'utf8'));
  if (!profile.id) throw new Error(`profile at ${filePath} has no id`);
  return profile;
}

export function applyOverlay(profile, overlay = {}) {
  const overridable = profile.overridable ?? [];
  const merged = structuredClone(profile);

  for (const [field, value] of Object.entries(overlay)) {
    if (SEALED_FIELDS.includes(field)) {
      throw new Error(`"${field}" is sealed and cannot be set by an overlay`);
    }
    if (!overridable.includes(field)) {
      throw new Error(`"${field}" is not listed in the profile's overridable fields`);
    }
    // Arrays merge as a union: an overlay adds, it does not remove.
    merged[field] = Array.isArray(profile[field]) && Array.isArray(value)
      ? [...new Set([...profile[field], ...value])]
      : value;
  }

  return merged;
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — 39 tests (31 existing + 8 here).

- [ ] **Step 5: Commit**

```bash
git add packages/wl-harness/scripts/profile.mjs packages/wl-harness/scripts/profile.test.mjs
git commit -m "feat(wl-harness): add the profile loader and overlay rule"
```

---

### Task 2: Extract the stack into a profile

**Files:**
- Create: `packages/wl-harness/references/profiles/fullstack-nextjs.json`
- Create: `packages/wl-harness/references/profiles/fullstack-nextjs.md`
- Modify: `packages/wl-harness/commands/init-project.md`
- Modify: `packages/wl-harness/commands/feature-dev.md`
- Create: `packages/wl-harness/scripts/skeleton-purity.test.mjs`

**Interfaces:**
- Consumes: `loadProfile` from Task 1.
- Produces: `references/profiles/fullstack-nextjs.json` as the single source of stack facts.

**This task is a move, not a redesign.** Every stack fact currently in the two command files goes into the profile unchanged. A run after this task must produce the same project as a run before it.

- [ ] **Step 1: Write the profile data**

Create `packages/wl-harness/references/profiles/fullstack-nextjs.json`:

```json
{
  "id": "fullstack-nextjs",
  "kind": "fullstack",
  "enabled": true,
  "scaffold": "pnpm create next-app@latest . --ts --eslint --app --src-dir --import-alias \"@/*\" --no-tailwind",
  "package_manager": "pnpm",
  "deps": {
    "runtime": ["antd", "less"],
    "dev": ["vitest", "@testing-library/react", "@testing-library/jest-dom", "jsdom"]
  },
  "layout": ["app", "components", "components/ui", "hooks", "services", "types", "styles", "utils"],
  "source_root": "src",
  "test_dir": "__tests__",
  "style_convention": "*.module.less; globals hold variables, reset and theme only",
  "checks": { "**/*.{ts,tsx}": ["pnpm exec tsc --noEmit", "pnpm eslint"] },
  "verify": ["pnpm test", "pnpm exec tsc --noEmit"],
  "forbidden": [
    {
      "from": "!src/components/ui/**",
      "to": "antd",
      "why": "business code imports UI primitives only from src/components/ui/, so swapping the library touches one directory"
    }
  ],
  "scaffold_safe_entries": [
    ".claude", ".cursor", ".DS_Store", ".git", ".gitattributes", ".gitignore",
    ".gitlab-ci.yml", ".hg", ".hgcheck", ".hgignore", ".idea", ".npmignore",
    ".travis.yml", ".vscode", ".zed", "LICENSE", "Thumbs.db", "docs",
    "mkdocs.yml", "npm-debug.log", "yarn-debug.log", "yarn-error.log",
    "yarnrc.yml", ".yarn"
  ],
  "deploy": "vercel",
  "overridable": ["deps", "complexity", "deploy"]
}
```

- [ ] **Step 2: Write the profile's judgement half**

Create `packages/wl-harness/references/profiles/fullstack-nextjs.md`. It carries what JSON cannot: the reasoning an agent needs in order to apply the data well. Write these sections, each two to four sentences:

- **Why UI primitives are wrapped** — business code imports from `src/components/ui/` so that swapping the underlying library touches one directory, and so style discussion stays out of pages.
- **Theming on Ant Design v5** — v5 themes through `ConfigProvider` token objects, not the Less variables v4 used. A Less-only theme leaves every antd component on its defaults while custom components follow the new values, which looks worse than either alone. Use the library's default tokens unless the author supplies a design; do not invent a palette.
- **Why Less over Sass or CSS Modules alone** — one preprocessor across the codebase, component styles always `*.module.less`, globals limited to variables, reset and theme.
- **Layout components before hand-written CSS** — reach for the library's `Flex`, `Space`, `Row`/`Col` before writing flexbox by hand; less hand-written CSS means less that drifts between runs.
- **When to split a service** — one file per module in `services/`; split when a module's requests stop sharing a subject, not when the file reaches a line count.
- **`scaffold_safe_entries`** — read from `create-next-app`'s published bundle. It refuses a non-empty directory unless every entry is on that list; `.claude` and `docs` are both on it, so scaffolding straight into the target works and a temporary directory is unnecessary.

- [ ] **Step 3: Write the purity test**

Create `packages/wl-harness/scripts/skeleton-purity.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.join(here, '..');

// Stack knowledge belongs in profile data, not in the skeleton (spec §7).
// references/ is deliberately excluded: it is where stack names are supposed
// to appear, because that is what an agent reads in order to judge.
const SKELETON_DIRS = ['commands', 'scripts', 'contracts'];

// Names that must not appear in the skeleton.
//
// Matched on word boundaries, not as substrings: "less" is a substring of
// "unless" and "regardless", "react" of "reaction", and the command prose
// legitimately uses all three. Verified — with \b, "regardless of how" and
// "unless the author" pass while "Less. Component styles", "*.module.less"
// and "React components" are still caught.
const BANNED = [
  'next\\.js', 'nextjs', 'create-next-app', 'antd', 'ant design',
  'less', 'sass', 'tailwind', 'pnpm', 'yarn',
  'vitest', 'jest', 'react',
];

function bannedIn(text) {
  return BANNED.filter((name) => new RegExp(`\\b${name}\\b`, 'i').test(text));
}

function filesUnder(dir) {
  const out = [];
  for (const entry of readdirSync(path.join(pluginRoot, dir), { withFileTypes: true })) {
    const full = path.join(pluginRoot, dir, entry.name);
    if (entry.isDirectory()) continue;
    out.push(full);
  }
  return out;
}

for (const dir of SKELETON_DIRS) {
  for (const file of filesUnder(dir)) {
    // The purity test names the very things it bans, so it exempts itself.
    if (file.endsWith('skeleton-purity.test.mjs')) continue;

    test(`${dir}/${path.basename(file)} names no stack`, () => {
      const text = readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
      const found = bannedIn(text);
      assert.deepEqual(
        found,
        [],
        `stack knowledge belongs in references/profiles/, not in ${dir}/: found ${found.join(', ')}`,
      );
    });
  }
}
```

- [ ] **Step 4: Run it and watch it fail loudly**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — both command files name several banned terms. That list is your worklist for step 5.

- [ ] **Step 5: Rewrite the commands against the profile**

In both `commands/init-project.md` and `commands/feature-dev.md`, replace every stack fact with a profile lookup. The mapping:

| Was | Becomes |
|---|---|
| The whole "Fixed stack" block | "The stack is declared by the profiles named in `.claude/harness.json`. Read them in stage 2 and state them back; do not carry stack assumptions into a run." |
| The "Directory layout" block | "Create `profile.source_root`, then one directory per entry in `profile.layout`." |
| `pnpm create next-app@latest . --ts …` | "Run `profile.scaffold` from the target directory." |
| `pnpm add antd less` and the dev-dependency line | "Install `profile.deps.runtime` and `profile.deps.dev` with `profile.package_manager`." |
| The whitelist paragraph | "The generator refuses a non-empty directory unless every entry is on `profile.scaffold_safe_entries`; check the target against that list before scaffolding." |
| "no `antd` outside `src/components/ui/`" | "the bans in `profile.forbidden`, each of which carries its own `why`" |
| "`pnpm exec tsc --noEmit`" in stage 6 | "each command in `profile.verify`" |
| "tests live in `__tests__/`" | "tests live in a directory named `profile.test_dir`, beside the code they cover" |
| "Less. Component styles are `*.module.less` …" | "`profile.style_convention`" |

Keep every **process** rule exactly as it is — test-first ordering, the Testing Trophy guidance, the stage-3 approval checkpoint, the grill, spec authority, the `HARNESS` resolution preamble, the argv rule. Those survive a change of stack and are the harness's own.

Add to stage 2 of both commands, after the existing template read:

> Read `.claude/harness.json` for the project's declared profiles, load each with
> `scripts/profile.mjs`, and apply the overlay. If the file is absent, this project
> predates profile declaration: say which profile you are assuming and why, and
> record that in the spec.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS. The purity test is now green, and the step-alignment tests still pass because the step count did not change.

- [ ] **Step 7: Commit**

```bash
git add packages/wl-harness/references/profiles/ packages/wl-harness/commands/ packages/wl-harness/scripts/skeleton-purity.test.mjs
git commit -m "refactor(wl-harness): move stack knowledge into a profile"
```

---

### Task 3: Document intake

**Files:**
- Modify: `packages/wl-harness/commands/init-project.md`

**Interfaces:**
- Consumes: the design template read in stage 2.
- Produces: nothing other tasks depend on.

Spec §16 already settles the behaviour: *when the author supplies a document, it is read as raw material rather than accepted as the spec.* A hand-written brief almost never states acceptance criteria — people do not naturally write down what "done" means — and that is the one thing stage 6 needs.

This task has no red-green cycle: the deliverable is command prose, and the alignment tests already guard its structure.

- [ ] **Step 1: Widen the usage line**

Replace the Usage section of `commands/init-project.md` with:

````markdown
## Usage

`/init-project <project name>` — name only; stage 3 asks for the rest.

`/init-project <project name> <path to a document>` — a product brief, a
requirements note, a design outline. Anything the author has already written.

The document is raw material, not the spec. It answers what it answers; stage 3
covers the remainder and turns the whole into `docs/spec.md`.
````

- [ ] **Step 2: Teach stage 2 to read it**

In stage 2 of `commands/init-project.md`, after the profile load, add:

> If the author named a document, read it in full. Extract, without inventing:
> the project's purpose, anything resembling a route or view list, any stated
> constraint, and any acceptance criterion. Say which of the template's
> dimensions it answered and which it left open. A document that answers nothing
> is not an error — it just means stage 3 asks about everything.

- [ ] **Step 3: Teach stage 3 to merge rather than replace**

In stage 3 of `commands/init-project.md`, before the drafting instruction, add:

> Where a document was supplied, its answers stand. Do not re-ask what it already
> settled, and do not quietly overrule it: if something in it looks wrong or
> self-contradictory, raise that in the batch as its own item, with what it says
> and what you would do instead.
>
> Carry its wording into `docs/spec.md` where it is precise enough to serve.
> Rewriting a clear requirement in your own words loses the author's intent for
> no gain.

- [ ] **Step 4: Verify the structure still holds**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — the step count and stage names are unchanged, so the alignment tests stay green.

Then confirm by eye that the frontmatter `steps` list still has 7 entries and the body still has 7 numbered lines.

- [ ] **Step 5: Commit**

```bash
git add packages/wl-harness/commands/init-project.md
git commit -m "feat(wl-harness): let init-project take a document as raw material"
```

---

### Task 4: Resumption

**Files:**
- Modify: `packages/wl-harness/scripts/workflow-state.mjs`
- Modify: `packages/wl-harness/scripts/workflow-state.test.mjs`
- Modify: `packages/wl-harness/commands/init-project.md`
- Modify: `packages/wl-harness/commands/feature-dev.md`

**Interfaces:**
- Consumes: `readWorkflowState`, `STAGES` from `workflow-state.mjs`.
- Produces: `resumePoint(projectDir: string): { slug: string, stage: string, nextStage: string | null } | null` — `null` when there is no state file; `nextStage` is `null` when the run reached the last stage.

The state file is written at every stage and read by nothing, which makes it a log rather than a state machine. Spec §11 wants the opposite: *read `workflow-state.md` frontmatter first — if a run is in progress, continue from the current stage; otherwise start fresh.*

- [ ] **Step 1: Write the failing tests**

Add to `packages/wl-harness/scripts/workflow-state.test.mjs`, importing `resumePoint` alongside the existing imports:

```js
test('resumePoint returns null when no run has started', () => {
  withTempProject((dir) => {
    assert.equal(resumePoint(dir), null);
  });
});

test('resumePoint reports the stage reached and the one after it', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'demo', stage: 'plan' });
    assert.deepEqual(resumePoint(dir), {
      slug: 'demo',
      stage: 'plan',
      nextStage: 'implement',
    });
  });
});

test('resumePoint has no next stage once the last stage is reached', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'demo', stage: 'ship' });
    assert.equal(resumePoint(dir).nextStage, null);
  });
});

test('resumePoint reports an unrecognised stage without inventing a next one', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'demo', stage: 'not-a-stage' });
    assert.deepEqual(resumePoint(dir), {
      slug: 'demo',
      stage: 'not-a-stage',
      nextStage: null,
    });
  });
});

test('resumePoint returns null when the state file cannot be parsed', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'demo', stage: 'plan' });
    writeFileSync(workflowStatePath(dir), 'not frontmatter at all', 'utf8');
    assert.equal(resumePoint(dir), null);
  });
});
```

The last test needs `writeFileSync` added to the `node:fs` import at the top of the file.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — `resumePoint is not a function`.

- [ ] **Step 3: Write the implementation**

Add to `packages/wl-harness/scripts/workflow-state.mjs`:

```js
// Spec §11: in-process state is downgraded to file state, so a run survives
// compaction and a restarted session. A corrupt or unreadable file reads as
// "no run in progress" rather than throwing: the caller's next move is to
// start fresh, and wedging the resume path is worse than losing a position.
export function resumePoint(projectDir) {
  let state;
  try {
    state = readWorkflowState(projectDir);
  } catch {
    return null;
  }
  if (!state) return null;

  const index = STAGES.indexOf(state.stage);
  const nextStage = index >= 0 && index < STAGES.length - 1 ? STAGES[index + 1] : null;
  return { slug: state.slug, stage: state.stage, nextStage };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS.

- [ ] **Step 5: Teach both commands to resume**

Add to the Implementation preamble of `commands/init-project.md` and `commands/feature-dev.md`, immediately after the `TARGET` resolution and before step 1:

````markdown
**Check for a run already in progress before starting one:**

```bash
node -e "import('<resolved HARNESS url>').then(m => console.log(JSON.stringify(m.resumePoint(process.argv[1]))))" "<resolved TARGET path>"
```

`null` means no run is in progress: start at step 1. Otherwise the result names
the stage last reached and the one after it. Report both to the author, then
continue from the next stage rather than repeating completed work — with one
exception: **an interrupted run may have left the stage it was in half-finished**,
since the stage is recorded at its start. Check that stage's declared output
exists and is complete before moving past it, and redo it if not.

Never silently restart a run that is in progress. Redoing stage 3 discards an
approval the author already gave.
````

- [ ] **Step 6: Verify the whole suite**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS, and the purity test still green — nothing added here names a stack.

- [ ] **Step 7: Commit**

```bash
git add packages/wl-harness/scripts/workflow-state.mjs packages/wl-harness/scripts/workflow-state.test.mjs packages/wl-harness/commands/
git commit -m "feat(wl-harness): resume a run from the state file"
```

---

### Task 5: Capture

**Files:**
- Create: `packages/wl-harness/scripts/capture.mjs`
- Create: `packages/wl-harness/scripts/capture.test.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `renderCapture(entry: { slug, date, answeredOutsideTemplate: string[], decisions: string[], deviations: string[] }): string` — the Markdown section
  - `readCaptures(shippedDir: string): object[]` — every capture under `workstate/shipped/`, for a later distillation step

A capture records one shipped work item without reducing it; distilling many captures into a proposed convention is a separate act, and deliberately not built here. One capture is a sample, not a pattern — see `CONTEXT.md`.

The most valuable field is `answeredOutsideTemplate`: what the author had to decide that no template asked. That list is the evidence for what the template should grow, and it carries its own justification — a real project needed it.

- [ ] **Step 1: Write the failing tests**

Create `packages/wl-harness/scripts/capture.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { readCaptures, renderCapture } from './capture.mjs';

const entry = {
  slug: 'single-page-nav',
  date: '2026-09-08',
  answeredOutsideTemplate: ['whether tag lists may contain duplicates'],
  decisions: ['navigation: single page with anchors'],
  deviations: [],
};

test('renderCapture writes a heading naming the slug and date', () => {
  const out = renderCapture(entry);
  assert.match(out, /## Capture/);
  assert.match(out, /single-page-nav/);
  assert.match(out, /2026-09-08/);
});

test('renderCapture lists what the template failed to ask', () => {
  assert.match(renderCapture(entry), /whether tag lists may contain duplicates/);
});

test('renderCapture marks an empty section rather than omitting it', () => {
  const out = renderCapture(entry);
  assert.match(out, /Deviations from profile[\s\S]*none/i);
});

test('readCaptures returns an empty array when nothing has shipped', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'wl-capture-'));
  try {
    assert.deepEqual(readCaptures(dir), []);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('readCaptures finds one entry per shipped document', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'wl-capture-'));
  try {
    mkdirSync(dir, { recursive: true });
    writeFileSync(path.join(dir, 'a.md'), renderCapture(entry), 'utf8');
    writeFileSync(
      path.join(dir, 'b.md'),
      renderCapture({ ...entry, slug: 'other', answeredOutsideTemplate: ['dark mode'] }),
      'utf8',
    );
    const found = readCaptures(dir);
    assert.equal(found.length, 2);
    assert.deepEqual(
      found.flatMap((c) => c.answeredOutsideTemplate).sort(),
      ['dark mode', 'whether tag lists may contain duplicates'],
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('readCaptures ignores a shipped document with no capture section', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'wl-capture-'));
  try {
    writeFileSync(path.join(dir, 'plain.md'), '# just notes\n', 'utf8');
    assert.deepEqual(readCaptures(dir), []);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — `Cannot find module ... capture.mjs`.

- [ ] **Step 3: Write the implementation**

Create `packages/wl-harness/scripts/capture.mjs`:

```js
// A capture records one shipped work item without reducing it. Distilling many
// captures into a proposed convention is a separate act and is not built here:
// one capture is a sample, not a pattern.

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';

const SECTIONS = [
  ['answeredOutsideTemplate', 'Answered outside the template'],
  ['decisions', 'Decisions that held'],
  ['deviations', 'Deviations from profile'],
];

function renderList(items) {
  return items.length ? items.map((line) => `- ${line}`).join('\n') : '- none';
}

export function renderCapture({ slug, date, ...rest }) {
  const body = SECTIONS.map(
    ([key, heading]) => `### ${heading}\n\n${renderList(rest[key] ?? [])}`,
  ).join('\n\n');
  return `## Capture — ${slug} (${date})\n\n${body}\n`;
}

// Parses back what renderCapture wrote. The format is ours on both sides, so a
// line-based reader is enough; it never has to survive arbitrary Markdown.
export function parseCapture(raw) {
  const text = raw.replace(/\r\n/g, '\n');
  const header = text.match(/^## Capture — (.+?) \((.+?)\)$/m);
  if (!header) return null;

  const entry = { slug: header[1], date: header[2] };
  for (const [key, heading] of SECTIONS) {
    const block = text.match(new RegExp(`^### ${heading}\\n\\n([\\s\\S]*?)(?=\\n### |\\n## |$)`, 'm'));
    const lines = block
      ? block[1].split('\n').filter((l) => l.startsWith('- ')).map((l) => l.slice(2).trim())
      : [];
    entry[key] = lines.filter((l) => l !== 'none');
  }
  return entry;
}

export function readCaptures(shippedDir) {
  if (!existsSync(shippedDir)) return [];
  return readdirSync(shippedDir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => parseCapture(readFileSync(path.join(shippedDir, f), 'utf8')))
    .filter(Boolean);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/wl-harness/scripts/capture.mjs packages/wl-harness/scripts/capture.test.mjs
git commit -m "feat(wl-harness): add capture rendering and reading"
```

---

### Task 6: The ship command

**Files:**
- Create: `packages/wl-harness/commands/ship.md`

**Interfaces:**
- Consumes: `resumePoint`, `writeWorkflowState` (Task 4), `renderCapture` (Task 5).
- Produces: the `/ship` command.

Spec §5: `/ship` is conformance and archival, not synchronisation. It verifies the delivered code conforms to its spec and archives the work item. It does **not** rewrite the spec to match what was built — a document edited to agree with the code has stopped constraining anything.

Spec §11: each state transition is the last side effect of its command, which is why an aborted ship finds nothing committed to undo.

- [ ] **Step 1: Write the command**

Create `packages/wl-harness/commands/ship.md`:

````markdown
---
id: ship-s1
type: ship
description: Check delivered work against its spec, capture what it taught, and archive it
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
steps:
  - conformance
  - capture
  - archive
---

# ship

Archive a work item the author has accepted.

**Run this after reviewing the work, not instead of reviewing it.** Stage 7
(Handoff) left the item in `testing/` precisely so a human could look at it.

## Usage

`/ship` — archives the item named in `.claude/workflow-state.md`

`/ship abort` — restores documents from their snapshot and stops
`/ship skip <reason>` — the same, recording why

## Implementation

Resolve `HARNESS` and `TARGET` exactly as `init-project` does — the same
preamble, the same `pathToFileURL` requirement, the same rule that `TARGET` is
passed as an argv value and never interpolated into a `node -e` JS string.

Read the current state before anything else:

```bash
node -e "import('<resolved HARNESS url>').then(m => console.log(JSON.stringify(m.resumePoint(process.argv[1]))))" "<resolved TARGET path>"
```

If it reports no run, or a stage before `handoff`, stop: there is nothing
accepted to archive. Say which stage the item is actually at.

1. **Conformance** — Record stage `ship`. Check the delivered code against
   `docs/spec.md`, criterion by criterion, and report each as met or not.

   Run every command in `profile.verify` and report the result.

   **The spec is the authority and the code is its product.** Where they
   disagree, that is a defect in the code, not an error in the spec. Do not
   edit `docs/spec.md` to match what was built.

   Report anything the code does that the spec never asked for. Work beyond the
   spec is as much a conformance gap as work missing from it — both mean the
   document no longer describes the software.

   If a clause genuinely needs to change, that is an amendment: stop, put it to
   the author with what the spec says and what you propose, and record the
   decision in the capture below. Never amend silently.

2. **Capture** — Write what this item taught, into `workstate/shipped/<slug>.md`.
   Ask yourself three questions and answer them honestly:

   - **What did the author have to decide that no template asked?** This is the
     most valuable line in the whole file. Every entry is a candidate dimension
     for the design template, and it arrives with its own evidence: a real
     project needed it.
   - **Which decisions held?** The ones that survived implementation unchanged.
   - **Where did the work depart from the profile, and why?**

   Record without reducing. Do not decide here that something is a convention —
   one item is a sample, not a pattern, and turning samples into rules is how a
   profile fills with accidents. A later distillation step, not yet built, reads
   many captures and proposes what recurred.

   Use `renderCapture` from `scripts/capture.mjs` so the format stays readable
   by that step:

   ```bash
   node -e "import('<resolved HARNESS url capture>').then(m => console.log(m.renderCapture(JSON.parse(process.argv[1]))))" '<the entry as JSON>'
   ```

3. **Archive** — Only after conformance passes and the capture is written: move
   the item from `workstate/testing/<slug>.md` to `workstate/shipped/<slug>.md`,
   appending the capture, and record stage `ship`.

   **This transition is the last thing this command does.** Nothing after it can
   fail and leave a half-archived item, which is why `/ship abort` has no state
   to roll back.

### `abort` and `skip`

Restore `docs/spec.md` and any plan from their snapshot, delete the snapshot,
and stop. `skip` does the same and records the reason in the capture.

Neither reverts code: code is git's to roll back, and conflating the two is how
a bad incident starts. Neither touches the workstate either — the transition
above has not happened yet.
````

- [ ] **Step 2: Verify the alignment tests accept it**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — the frontmatter lists three steps and the body has three numbered lines, whose bolded names match in order.

If the alignment test fails, the frontmatter and body disagree: fix the command, not the test.

- [ ] **Step 3: Confirm the purity test still passes**

The command must name no stack. It refers to `profile.verify` rather than any concrete command.

Run: `npm test --prefix packages/wl-harness`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/wl-harness/commands/ship.md
git commit -m "feat(wl-harness): add the ship command with conformance and capture"
```

---

### Task 7: Update the spec

**Files:**
- Modify: `docs/superpowers/specs/2026-09-05-wl-harness-architecture-design.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a spec that matches what was built.

- [ ] **Step 1: Rewrite the slice table**

In §15, replace the S1–S4 rows with:

| Slice | Adds |
|---|---|
| **S1** | The profile extraction, document intake, resumption, and `/ship` with capture |
| **S2** | A second profile. The abstraction gets its first real test — S1 extracted it under pressure from accumulation rather than from a second case, so §7's assumption is still unverified |
| **S3** | The full gate set: hooks, `harness-check.mjs`, dependency-cruiser |
| **S4** | `bug-fix`, complexity M/L, distillation across captures, CodeGraph decomposition, timing |

Add beneath it:

> S1's ordering departed from the original plan, which put `/ship` first. Two
> runs of `init-project` showed the commands accumulating stack knowledge as
> prose until they read as project templates rather than process definitions —
> so the extraction came first, since everything else edits the same files.
> ADR-0002 anticipated the abstraction being forced out by a second stack; it
> was forced out by depth on one instead.

- [ ] **Step 2: Record what S1 answered and what it did not**

In §16, add a row:

| **D-9** | What distillation proposes, and on what evidence a capture becomes a convention | Several captures. One is a sample, not a pattern |

And amend D-2's unblock column, which S1 partly answered:

> S0 and S1 running. The state file now has a reader, so `stage` earned its
> place; `steps` proved its worth through the alignment gate. The enumerations
> and the shape of a `steps` entry are still open.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-05-wl-harness-architecture-design.md
git commit -m "docs(wl-harness): record what S1 built and reordered"
```

---

## Self-Review

**Spec coverage.** §7's profile mechanism and ADR-0001's overlay rule → Tasks 1–2. §16 D-8's document intake → Task 3. §11's "read the frontmatter first, continue from the current stage" → Task 4. §5's ship-as-conformance and §11's "the transition is the last side effect" → Task 6. `CONTEXT.md`'s capture/distill split → Task 5, with distillation deliberately absent. §15's slice table → Task 7.

**Deliberately out of scope:** distillation across captures (needs several captures to exist), `harness-check.mjs` and the contract schema (S3, and D-2 may yet find the schema unnecessary), dependency-cruiser, a second profile, `bug-fix`, complexity M/L, CodeGraph, timing. The `ship-snapshot` mechanism is referenced by `/ship abort` but not built here — abort restores from a snapshot that stage 3 must write, which is S3's gate work.

**Type consistency.** `loadProfile(pluginRoot, id)`, `applyOverlay(profile, overlay)`, `SEALED_FIELDS`, `resumePoint(projectDir)`, `renderCapture(entry)`, `parseCapture(raw)` and `readCaptures(shippedDir)` are defined in Tasks 1, 4 and 5 and used under those exact names in Tasks 2, 4 and 6. The profile field names in Task 2's JSON — `scaffold`, `deps`, `layout`, `source_root`, `test_dir`, `checks`, `verify`, `forbidden`, `scaffold_safe_entries`, `package_manager`, `style_convention` — are the same ones Task 2 step 5's mapping table and Task 6's command refer to.

**One risk worth naming.** Task 2's purity test is the boundary between the harness and a profile made executable, so a false positive there is tempting to fix by deleting the test. Do not. The substring form was already caught and fixed during planning — `less` is inside "unless" and "regardless", `react` inside "reaction", and the command prose uses all three — which is why it matches on word boundaries. If a new false positive appears, narrow that entry.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-08-wl-harness-s1.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
