# wl-harness S0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the thinnest possible hole through all six wl-harness layers and run `init-project` end to end, producing the author's personal website skeleton.

**Architecture:** wl-harness ships as a Claude Code plugin under `packages/wl-harness/`. S0 builds one command (`init-project`, complexity S only), one state script, one contract file and one enforcement hook. Stack knowledge is deliberately hardcoded in the command file — the profile mechanism is S2 work, extracted when a second stack forces it out (ADR-0002). All eight stages of the spine run; only their content is thin.

**Tech Stack:** Node 22 ESM (`.mjs`, zero external dependencies), `node:test` built-in test runner, Claude Code plugin manifest + hooks. Generated target project: Next.js App Router, TypeScript strict, Less modules, Ant Design behind `components/ui/`, pnpm.

**Spec:** `docs/superpowers/specs/2026-09-05-wl-harness-architecture-design.md`

## Global Constraints

- **Language:** every file committed to this repo is written in English — code, comments, docs, commit messages (spec §14, repo `CLAUDE.md`).
- **S0's scripts are `.mjs`.** Neither language is banned — the rule is to pick by shape (spec §8): orchestration in `.sh`, computation in `.mjs`. Both S0 scripts parse structured data and are unit-tested, so both are `.mjs`. Do not rewrite them in bash: Git Bash ships no `jq`, and `core.autocrlf` is `true` in this repo.
- **Zero external npm dependencies in `packages/wl-harness`.** Node's built-ins cover everything S0 needs, including the test runner.
- **No validator and no enumerations ship in S0.** `contracts/schema.json` documents the frontmatter shape as data; nothing reads it at runtime yet (spec §15, §16 D-2).
- **No profile mechanism in S0.** Stack choices live directly in `commands/init-project.md`. Do not create `references/profiles/` — that abstraction is S2 (ADR-0002).
- **Mark every hardcoded stack choice with `S0-HARDCODE`** in a comment or inline note, so S2 can find them all at once.
- **Target project stack, fixed for S0** (spec §6.1–6.5, complexity S, form = frontend-only): Next.js App Router · TypeScript strict · Less modules (`*.module.less`) · Ant Design wrapped behind `src/components/ui/` · pnpm.
- **Do not scaffold unused fixed defaults.** react-hook-form, zod, dayjs and axios are available per spec §6.2 but are only installed when a page actually needs them.
- **Human-in-the-loop (spec §10):** nothing in S0's scope lands in an "ask" quadrant — all actions are repo-local and git-reversible, or outside-repo and reversible (`pnpm install`). Do not add confirmation prompts to the command.
- **Stage vocabulary** (spec §4, kebab-cased for the state file): `intake`, `context-load`, `design`, `plan`, `implement`, `verify`, `handoff`, `ship`.

---

## File Structure

**Created in `packages/wl-harness/`:**

| File | Responsibility |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest — name, version, description |
| `package.json` | ESM marker + `npm test` entry point; no dependencies |
| `contracts/schema.json` | L1 — documents the three frontmatter fields (`id`, `type`, `steps`). Data only, nothing reads it |
| `scripts/workflow-state.mjs` | L2 + L4 — reads and writes `<project>/.claude/workflow-state.md`, plus `slugify` |
| `scripts/workflow-state.test.mjs` | Tests for the above |
| `scripts/check-command-steps.test.mjs` | Regression guard: every command's frontmatter `steps` aligns 1:1 with its body's `^N.` lines (spec §5) |
| `commands/init-project.md` | L3 — the step-ised command walking all eight stages at complexity S |
| `hooks/hooks.json` | L6 — registers the PostToolUse hook |
| `hooks/check-ui-imports.mjs` | L6 — the one red line: no direct `antd` import outside `src/components/ui/` |
| `hooks/check-ui-imports.test.mjs` | Tests for the above |

**Modified at repo root:**

| File | Change |
|---|---|
| `.claude-plugin/marketplace.json` | Add the `wl-harness` entry |
| `CATALOG.md` | Add `packages/wl-harness` to Packages / Plugins |

`packages/wl-harness/CONTEXT.md` already exists and is not modified by this plan.

---

### Task 1: Plugin skeleton and test harness

**Files:**
- Create: `packages/wl-harness/.claude-plugin/plugin.json`
- Create: `packages/wl-harness/package.json`
- Create: `packages/wl-harness/scripts/manifest.test.mjs`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CATALOG.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a loadable plugin at `packages/wl-harness`, and `npm test --prefix packages/wl-harness` as the command every later task runs.

- [ ] **Step 1: Write the failing test**

Create `packages/wl-harness/scripts/manifest.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.join(here, '..');
const repoRoot = path.join(pluginRoot, '..', '..');

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'));
}

test('plugin.json declares name, version and description', () => {
  const manifest = readJson(path.join(pluginRoot, '.claude-plugin', 'plugin.json'));
  assert.equal(manifest.name, 'wl-harness');
  assert.match(manifest.version, /^\d+\.\d+\.\d+$/);
  assert.ok(manifest.description.length > 0);
});

test('package.json is ESM and has no dependencies', () => {
  const pkg = readJson(path.join(pluginRoot, 'package.json'));
  assert.equal(pkg.type, 'module');
  assert.equal(pkg.dependencies, undefined);
  assert.equal(pkg.devDependencies, undefined);
});

test('the marketplace lists wl-harness, pointing at this package', () => {
  const marketplace = readJson(path.join(repoRoot, '.claude-plugin', 'marketplace.json'));
  const entry = marketplace.plugins.find((p) => p.name === 'wl-harness');
  assert.ok(entry, 'wl-harness is missing from marketplace.json');
  assert.equal(entry.source, './packages/wl-harness');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — npm cannot find `packages/wl-harness/package.json`.

- [ ] **Step 3: Create the plugin manifest**

Create `packages/wl-harness/.claude-plugin/plugin.json`:

```json
{
  "name": "wl-harness",
  "version": "0.1.0",
  "description": "Opinionated, contract-driven harness on top of Claude Code: turns stack preferences and delivery workflow into enforced gates"
}
```

- [ ] **Step 4: Create the package manifest**

Create `packages/wl-harness/package.json`:

```json
{
  "name": "wl-harness",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "description": "Opinionated, contract-driven harness on top of Claude Code",
  "scripts": {
    "test": "node --test"
  }
}
```

- [ ] **Step 5: Register the plugin in the marketplace**

Modify `.claude-plugin/marketplace.json` — append to the `plugins` array, after the `ui-code-inspector` entry:

```json
    {
      "name": "wl-harness",
      "source": "./packages/wl-harness",
      "description": "Opinionated, contract-driven harness on top of Claude Code: turns stack preferences and delivery workflow into enforced gates"
    }
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — 3 tests passing.

- [ ] **Step 7: Update CATALOG.md**

Modify `CATALOG.md` — add a row to the Packages / Plugins table:

```markdown
| `packages/wl-harness` | Opinionated, contract-driven harness on top of Claude Code (S0 slice: `init-project` at complexity S) |
```

- [ ] **Step 8: Commit**

```bash
git add packages/wl-harness/.claude-plugin/plugin.json packages/wl-harness/package.json packages/wl-harness/scripts/manifest.test.mjs .claude-plugin/marketplace.json CATALOG.md
git commit -m "feat(wl-harness): add plugin skeleton and test harness"
```

---

### Task 2: Workflow state script (L2 + L4)

**Files:**
- Create: `packages/wl-harness/scripts/workflow-state.mjs`
- Create: `packages/wl-harness/scripts/workflow-state.test.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `workflowStatePath(projectDir: string): string` — absolute path to `<projectDir>/.claude/workflow-state.md`
  - `slugify(text: string): string`
  - `readWorkflowState(projectDir: string): { slug: string, stage: string, body: string } | null`
  - `writeWorkflowState(projectDir: string, state: { slug: string, stage: string, body?: string }): void`
  - `STAGES: string[]` — the eight stage names in spine order, inert documentation, not enforced

The frontmatter parser handles only flat `key: value` string pairs — no nesting, no lists. That is sufficient for S0's two fields and avoids pulling in a YAML dependency. If the frontmatter grows lists, swap in a real parser then.

- [ ] **Step 1: Write the failing tests**

Create `packages/wl-harness/scripts/workflow-state.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  STAGES,
  readWorkflowState,
  slugify,
  workflowStatePath,
  writeWorkflowState,
} from './workflow-state.mjs';

function makeTempProject() {
  return mkdtempSync(path.join(tmpdir(), 'wl-harness-'));
}

function withTempProject(fn) {
  const dir = makeTempProject();
  try {
    fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('readWorkflowState returns null when the file does not exist', () => {
  withTempProject((dir) => {
    assert.equal(readWorkflowState(dir), null);
  });
});

test('write then read round-trips slug, stage and body', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, {
      slug: 'personal-site',
      stage: 'intake',
      body: '# personal-site\n',
    });
    const state = readWorkflowState(dir);
    assert.equal(state.slug, 'personal-site');
    assert.equal(state.stage, 'intake');
    assert.equal(state.body, '# personal-site\n');
  });
});

test('writeWorkflowState creates the .claude directory when it is missing', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'intake' });
    assert.ok(existsSync(workflowStatePath(dir)));
  });
});

test('a second write advances the stage in place', () => {
  withTempProject((dir) => {
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'intake' });
    writeWorkflowState(dir, { slug: 'personal-site', stage: 'plan' });
    assert.equal(readWorkflowState(dir).stage, 'plan');
  });
});

test('writeWorkflowState refuses a missing slug', () => {
  withTempProject((dir) => {
    assert.throws(() => writeWorkflowState(dir, { stage: 'intake' }), /slug/);
  });
});

test('writeWorkflowState refuses a missing stage', () => {
  withTempProject((dir) => {
    assert.throws(() => writeWorkflowState(dir, { slug: 'personal-site' }), /stage/);
  });
});

test('slugify lowercases, trims and hyphenates', () => {
  assert.equal(slugify('  My Personal Site!! '), 'my-personal-site');
});

test('STAGES lists the eight spine stages in order', () => {
  assert.deepEqual(STAGES, [
    'intake',
    'context-load',
    'design',
    'plan',
    'implement',
    'verify',
    'handoff',
    'ship',
  ]);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — `Cannot find module ... workflow-state.mjs`.

- [ ] **Step 3: Write the implementation**

Create `packages/wl-harness/scripts/workflow-state.mjs`:

```js
// L2 + L4: the single file-state mechanism for S0.
// Nothing here depends on shell variables or in-process state, so a session
// can be compacted or restarted and still resume from the file.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const DELIM = '---';

// Inert documentation of the spine's order. Deliberately not enforced:
// S0 ships no validator (spec 15, 16 D-2).
export const STAGES = [
  'intake',
  'context-load',
  'design',
  'plan',
  'implement',
  'verify',
  'handoff',
  'ship',
];

export function workflowStatePath(projectDir) {
  return path.join(projectDir, '.claude', 'workflow-state.md');
}

export function slugify(text) {
  return String(text)
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Handles only flat `key: value` string pairs. Sufficient for S0's two
// fields; swap in a real YAML parser if the frontmatter ever grows lists.
export function parseFrontmatter(raw) {
  const lines = raw.split(/\r?\n/);
  if (lines[0] !== DELIM) {
    throw new Error('workflow-state.md is missing its opening frontmatter delimiter');
  }
  const fields = {};
  let i = 1;
  for (; i < lines.length; i++) {
    if (lines[i] === DELIM) break;
    const sep = lines[i].indexOf(':');
    if (sep === -1) continue;
    fields[lines[i].slice(0, sep).trim()] = lines[i].slice(sep + 1).trim();
  }
  const body = lines.slice(i + 1).join('\n').replace(/^\n+/, '');
  return { slug: fields.slug, stage: fields.stage, body };
}

export function stringifyFrontmatter({ slug, stage }, body) {
  return `${DELIM}\nslug: ${slug}\nstage: ${stage}\n${DELIM}\n\n${body}`.replace(/\n+$/, '\n');
}

export function readWorkflowState(projectDir) {
  const filePath = workflowStatePath(projectDir);
  if (!existsSync(filePath)) return null;
  return parseFrontmatter(readFileSync(filePath, 'utf8'));
}

export function writeWorkflowState(projectDir, { slug, stage, body }) {
  if (!slug) throw new Error('writeWorkflowState requires a slug');
  if (!stage) throw new Error('writeWorkflowState requires a stage');
  // The only caller (init-project's per-step stage recorder) never passes a
  // body — it just wants to advance the stage. Blanking the body on every
  // one of the seven stage transitions would destroy anything a step wrote
  // there, so when body is omitted, carry the existing body forward instead
  // of defaulting to empty. A brand-new file still starts with an empty body.
  let resolvedBody = body;
  if (resolvedBody === undefined) {
    // A crashed or partial previous run can leave a zero-byte or otherwise
    // unparseable state file. Recovering from that (the entire point of this
    // module) matters more than preserving a body that cannot be read, so a
    // parse failure here falls back to an empty body instead of propagating.
    try {
      const existing = readWorkflowState(projectDir);
      resolvedBody = existing ? existing.body : '';
    } catch {
      resolvedBody = '';
    }
  }
  mkdirSync(path.join(projectDir, '.claude'), { recursive: true });
  writeFileSync(
    workflowStatePath(projectDir),
    stringifyFrontmatter({ slug, stage }, resolvedBody),
    'utf8',
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — 11 tests passing (3 from Task 1, 8 here).

- [ ] **Step 5: Commit**

```bash
git add packages/wl-harness/scripts/workflow-state.mjs packages/wl-harness/scripts/workflow-state.test.mjs
git commit -m "feat(wl-harness): add workflow-state read/write script"
```

---

### Task 3: The one red line (L6)

**Files:**
- Create: `packages/wl-harness/hooks/check-ui-imports.mjs`
- Create: `packages/wl-harness/hooks/check-ui-imports.test.mjs`
- Create: `packages/wl-harness/hooks/hooks.json`

**Interfaces:**
- Consumes: nothing.
- Produces: `shouldBlockUiImport(filePath: string, content: string): boolean`, plus a PostToolUse hook that emits `{ decision: 'block', reason: string }` on stdout.

The rule enforced is spec §6.5: business code imports UI primitives only from `src/components/ui/`. Files inside that directory are exempt — wrapping Ant Design is exactly their job.

The hook follows the fail-safe convention already used by `packages/cc-dialogs/hooks/ccdialogs/hookio.py`: any failure exits 0 with empty stdout, so a crashing hook can never wedge a session.

- [ ] **Step 1: Write the failing tests**

Create `packages/wl-harness/hooks/check-ui-imports.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { shouldBlockUiImport } from './check-ui-imports.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(here, 'check-ui-imports.mjs');

function runHook(filePath) {
  return execFileSync(process.execPath, [SCRIPT], {
    input: JSON.stringify({ tool_name: 'Write', tool_input: { file_path: filePath } }),
    encoding: 'utf8',
  });
}

function withTempFile(name, contents, fn) {
  const dir = mkdtempSync(path.join(tmpdir(), 'wl-harness-hook-'));
  try {
    const filePath = path.join(dir, name);
    writeFileSync(filePath, contents, 'utf8');
    fn(filePath);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('blocks a direct antd import outside components/ui', () => {
  assert.equal(
    shouldBlockUiImport('src/app/page.tsx', 'import { Button } from "antd";'),
    true,
  );
});

test('allows a direct antd import inside src/components/ui', () => {
  assert.equal(
    shouldBlockUiImport('src/components/ui/Button.tsx', 'import { Button } from "antd";'),
    false,
  );
});

test('allows the same path written with backslashes (Windows)', () => {
  assert.equal(
    shouldBlockUiImport('src\\components\\ui\\Button.tsx', "import { Button } from 'antd';"),
    false,
  );
});

test('ignores code with no antd import', () => {
  assert.equal(
    shouldBlockUiImport('src/app/page.tsx', 'import { Fragment } from "react";'),
    false,
  );
});

test('blocks a tree-shaken antd subpath import outside components/ui', () => {
  assert.equal(
    shouldBlockUiImport('src/app/page.tsx', 'import Button from "antd/es/button";'),
    true,
  );
});

test('allows a tree-shaken antd subpath import inside src/components/ui', () => {
  assert.equal(
    shouldBlockUiImport('src/components/ui/Button.tsx', 'import Button from "antd/es/button";'),
    false,
  );
});

test('ignores non-code files', () => {
  assert.equal(
    shouldBlockUiImport('src/styles/globals.less', '.antd-override { color: red; }'),
    false,
  );
});

test('as a hook: emits a block decision for an offending file', () => {
  withTempFile('page.tsx', 'import { Button } from "antd";\n', (filePath) => {
    const result = JSON.parse(runHook(filePath));
    assert.equal(result.decision, 'block');
    assert.match(result.reason, /components\/ui/);
  });
});

test('as a hook: emits nothing for a clean file', () => {
  withTempFile('page.tsx', 'import { Fragment } from "react";\n', (filePath) => {
    assert.equal(runHook(filePath), '');
  });
});

test('as a hook: emits nothing when the file no longer exists', () => {
  assert.equal(runHook(path.join(tmpdir(), 'wl-harness-does-not-exist.tsx')), '');
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test --prefix packages/wl-harness`
Expected: FAIL — `Cannot find module ... check-ui-imports.mjs`.

- [ ] **Step 3: Write the implementation**

Create `packages/wl-harness/hooks/check-ui-imports.mjs`:

```js
// L6: S0's single red line.
// Spec 6.5 — business code imports UI primitives only from src/components/ui/.
// S0-HARDCODE: the library name and the directory are fixed here. In S2 they
// come from the profile's `forbidden` rules instead.

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const CODE_FILE = /\.(ts|tsx|js|jsx)$/;
const UI_DIR = /(^|\/)src\/components\/ui\//;
const ANTD_IMPORT = /from\s+['"]antd(\/[^'"]*)?['"]/;

export function shouldBlockUiImport(filePath, content) {
  const normalised = String(filePath).replace(/\\/g, '/');
  if (!CODE_FILE.test(normalised)) return false;
  if (UI_DIR.test(normalised)) return false;
  return ANTD_IMPORT.test(content);
}

function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', () => resolve(''));
  });
}

// Any failure ends in exit 0 with empty stdout: Claude Code reads "no output"
// as "the hook made no decision", so a crash can never wedge the session.
async function main() {
  try {
    const raw = (await readStdin()).replace(/^﻿/, '').trim();
    if (!raw) return;

    const filePath = JSON.parse(raw)?.tool_input?.file_path;
    if (!filePath) return;

    const content = readFileSync(filePath, 'utf8');
    if (!shouldBlockUiImport(filePath, content)) return;

    process.stdout.write(JSON.stringify({
      decision: 'block',
      reason:
        `${filePath} imports "antd" directly. Business code may only import UI ` +
        'primitives from src/components/ui/ — wrap the component there and import ' +
        'the wrapper instead.',
    }));
  } catch {
    // Deliberately silent.
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  // Do not force process.exit(0) here: on Windows, pipe writes to stdout are
  // asynchronous at the libuv level, and process.exit() does not wait for the
  // stream to drain — it can truncate the block decision before Claude Code
  // reads it. Setting exitCode instead lets Node flush stdout and exit
  // naturally once the event loop is empty.
  main().then(() => { process.exitCode = 0; }, () => { process.exitCode = 0; });
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — 21 tests passing.

- [ ] **Step 5: Register the hook**

Create `packages/wl-harness/hooks/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/check-ui-imports.mjs\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add packages/wl-harness/hooks/
git commit -m "feat(wl-harness): add the components/ui red line as a PostToolUse hook"
```

---

### Task 4: Contract shape and the init-project command (L1 + L3)

**Files:**
- Create: `packages/wl-harness/contracts/schema.json`
- Create: `packages/wl-harness/commands/init-project.md`
- Create: `packages/wl-harness/scripts/check-command-steps.test.mjs`

**Interfaces:**
- Consumes: `scripts/workflow-state.mjs` (Task 2) — the command calls it at every stage transition. The hook from Task 3 fires on its own during the Implement stage; the command does not invoke it.
- Produces: the `/init-project` slash command.

This task's deliverable is documentation-shaped, so it does not follow a red-green cycle: the alignment test needs real content to check. Write the command first, then the test that guards its structure.

- [ ] **Step 1: Write the contract shape**

Create `packages/wl-harness/contracts/schema.json`:

```json
{
  "$comment": "S0 shape only. No enumerated values and no validator ship with this slice — see docs/superpowers/specs/2026-09-05-wl-harness-architecture-design.md section 15 and section 16 D-2. Nothing reads this file at runtime yet; it documents the frontmatter every wl-harness command carries.",
  "fields": {
    "id": {
      "type": "string",
      "description": "Stable identifier for this command definition, unique within the plugin."
    },
    "type": {
      "type": "string",
      "description": "Which command this is. S0 has exactly one value in use: init-project. Deliberately not enumerated — see D-2."
    },
    "steps": {
      "type": "array",
      "items": { "type": "string" },
      "description": "One entry per numbered step in the command body, in order. Must align 1:1 with the body's ^N. lines. Checked by scripts/check-command-steps.test.mjs; harness-check.mjs is a later slice."
    }
  }
}
```

- [ ] **Step 2: Write the command**

Create `packages/wl-harness/commands/init-project.md`:

````markdown
---
id: init-project-s0
type: init-project
description: Scaffold a new complexity-S, frontend-only Next.js project through all stages up to Handoff
allowed-tools: Bash, Read, Write, Edit, Glob
steps:
  - intake
  - context-load
  - design
  - plan
  - implement
  - verify
  - handoff
---

# init-project

Scaffold a new project from nothing, walking every stage of the harness spine.

**S0 scope:** complexity S, frontend-only, one stack. Complexity M/L, other stacks
and the profile mechanism are later slices — do not generalise this file.

## Usage

`/init-project <short project description>`

Example: `/init-project my personal website`

## Fixed stack (S0-HARDCODE)

These are not decisions to re-litigate during a run. In S2 they move into a
profile; until then they live here:

- **Framework:** Next.js, App Router, TypeScript strict
- **Package manager:** pnpm
- **Styling:** Less. Component styles are `*.module.less`; globals hold only
  variables, reset and theme
- **UI:** Ant Design, always wrapped behind `src/components/ui/`. Business code
  imports from `src/components/ui/`, never from `antd` directly — a PostToolUse
  hook rejects violations
- **Not installed unless a page needs one:** react-hook-form, zod, dayjs, axios
- **No database, no auth:** complexity S, frontend-only

## Directory layout (S0-HARDCODE)

```
src/
  app/              routing
  components/       presentational, no business logic
  components/ui/    the only place antd may be imported
  hooks/
  services/         request layer, one file per module
  types/
  styles/           variables, mixins, globals
  utils/
public/
```

## Implementation

Resolve `HARNESS`, the absolute path to `workflow-state.mjs`, before doing
anything else. `CLAUDE_PLUGIN_ROOT` is set reliably when Claude Code dispatches
a hook, but it is not guaranteed to reach the shell environment of a Bash call
made from inside a slash command's own instructions — treat it as a hint, not
a given:

```bash
HARNESS=""
if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -f "$CLAUDE_PLUGIN_ROOT/scripts/workflow-state.mjs" ]; then
  HARNESS="$CLAUDE_PLUGIN_ROOT/scripts/workflow-state.mjs"
else
  HARNESS=$(find -L ~/.claude/plugins -name workflow-state.mjs -path "*wl-harness*" -print -quit 2>/dev/null)
fi
if [ -z "$HARNESS" ] || [ ! -f "$HARNESS" ]; then
  echo "ERROR: could not locate wl-harness/scripts/workflow-state.mjs (checked \$CLAUDE_PLUGIN_ROOT and ~/.claude/plugins)"
  exit 1
fi
HARNESS_URL=$(node -e "console.log(require('url').pathToFileURL(require('fs').realpathSync(process.argv[1])).href)" "$HARNESS")
echo "resolved HARNESS url: $HARNESS_URL"
```

`HARNESS` must be resolved to a `file://` URL, not left as a native path. A
native Windows path (`D:\...`) concatenated after `file://` is not a valid URL
and `import()` rejects it with `ERR_INVALID_URL`; `pathToFileURL` is what
correctly escapes and formats it on every platform, including the `/c/...`
MSYS-style paths `find` can produce on Windows.

The real Claude Code plugin layout nests a marketplace and version segment
between `plugins` and the plugin's own files (for example
`~/.claude/plugins/cache/<marketplace>/wl-harness/<version>/scripts/workflow-state.mjs`),
so the fallback search matches by filename and filters on `wl-harness`
appearing anywhere in the path, rather than assuming `scripts/` is a direct
child of a directory literally named `wl-harness`. `-L` makes `find` follow a
symlinked plugin directory, which is how local-checkout dev mode is wired in.
If more than one match exists, take the first and trust the echoed path —
that echo is the record of which one was used. Stop with the printed error if
no file is found; do not guess a path and continue.

Let `TARGET` be the absolute path of the directory being initialised (the
current working directory unless the author names another).

**Both resolutions above happen exactly once, in this preamble, before step 1
runs.** Each numbered step below is a separately-invoked Bash call, and shell
state — including `$HARNESS_URL` and `$TARGET` — does not persist between
separate Bash tool calls; only the working directory does. So `$HARNESS_URL`
and `$TARGET` used in this preamble are placeholders for exposition only: once
resolved and echoed here, carry the two absolute values forward as literal
text substituted into every later command in this run, not as live shell
variables. The remaining examples in this file write `<resolved HARNESS
url>` and `<resolved TARGET path>` to mark exactly where that substitution
happens.

Record the stage at the *start* of each numbered step, using:

```bash
node -e "import('<resolved HARNESS url>').then(m => m.writeWorkflowState(process.argv[1], { slug: '<slug>', stage: '<stage>' }))" "<resolved TARGET path>"
```

**`TARGET` MUST be passed as a Node `argv` value (read back via
`process.argv[1]`), never interpolated directly into the `-e` JS string.** A
Windows `TARGET` contains backslashes (`C:\Users\...`); inside a JS string
those are consumed as escape sequences with no error, silently corrupting the
path (e.g. `\U` and `\t` vanish or turn into a tab) so the state file lands
somewhere unintended and the run looks like it succeeded. Passing it as
`argv` sidesteps JS string-escape processing entirely. Do not "simplify" this
back to string interpolation in a future edit — it is the fix for a
reproduced silent-corruption bug, not a style preference.

1. **Intake** — Derive the slug from the description with `slugify` (for example
   `my personal website` becomes `my-personal-website`). `slugify` strips
   everything outside `[a-z0-9]` with no transliteration step, so a
   non-ASCII description (for example one written in Chinese) can collapse to
   an empty string. If the derived slug is empty, stop and ask the author for
   an explicit ASCII slug instead of proceeding — do not call
   `writeWorkflowState` with an empty slug. Confirm `<resolved
   TARGET path>` is empty or contains only `.git`; if it holds other files,
   stop and tell the author this command is for empty repositories. Write the
   state file with stage `intake`.

2. **Context load** — Record stage `context-load`. State back to the author, in
   one short block: the fixed stack above, the directory layout above, and the
   one red line (no `antd` outside `src/components/ui/`). This is the injection
   step — the agent that writes code in step 5 must have seen it.

3. **Design** — Record stage `design`. Selection is already fixed by the stack
   block, so the only real decision here is structure. Ask the author for the
   page list if the description does not imply one, then write
   `docs/spec.md` in `<resolved TARGET path>` containing: the project's purpose in one
   sentence, the list of routes with one line each, and the acceptance criteria
   ("`pnpm exec tsc --noEmit` passes", "every route renders", plus anything the
   author named). Keep it to intent and acceptance — no implementation detail.

4. **Plan** — Record stage `plan`. Write `docs/plan.md` in `<resolved TARGET path>` listing the
   scaffold steps in order, each with the files it produces. For a typical
   personal site that is: create the Next.js app, add Less and Ant Design,
   create the `src/components/ui/` wrappers the routes need, then one step per
   route.

5. **Implement** — Record stage `implement`. Work through `docs/plan.md` in
   order.

   `create-next-app` refuses to scaffold into a non-empty directory unless
   every existing entry is on its own whitelist (things like `.git`,
   `.gitignore`, `docs`) — and `.claude/`, written in step 1, is not on that
   whitelist. By this step `<resolved TARGET path>` already holds `.claude/`
   (and `docs/spec.md`, `docs/plan.md` from steps 3-4), so scaffolding
   *directly* into `<resolved TARGET path>` aborts. Scaffold into a fresh,
   empty subdirectory instead, then move its contents up — including
   dotfiles, which a bare `mv tmp/* .` silently skips:

   ```bash
   cd "<resolved TARGET path>"
   SCAFFOLD_TMP="$(pwd)/wl-harness-scaffold"
   rm -rf "$SCAFFOLD_TMP" && mkdir -p "$SCAFFOLD_TMP"
   pnpm create next-app@latest "$SCAFFOLD_TMP" --ts --eslint --app --src-dir --import-alias "@/*" --no-tailwind
   pnpm --dir "$SCAFFOLD_TMP" add antd less
   shopt -s dotglob nullglob
   for f in "$SCAFFOLD_TMP"/*; do
     mv "$f" "./$(basename "$f")"
   done
   shopt -u dotglob nullglob
   rm -rf "$SCAFFOLD_TMP"
   node -e "const fs = require('fs'); const p = JSON.parse(fs.readFileSync(process.argv[1], 'utf8')); p.name = process.argv[2]; fs.writeFileSync(process.argv[1], JSON.stringify(p, null, 2) + '\n');" package.json "<slug>"
   ```

   `create-next-app` derives the project name from the scaffold path's
   basename and runs it through `validate-npm-package-name` before doing any
   work, which rejects a name starting with `.` — so `$SCAFFOLD_TMP` must not
   start with a dot; hence `wl-harness-scaffold`, not `.wl-harness-scaffold`.
   `$SCAFFOLD_TMP` is empty before the generator runs, so the whitelist check
   on `<resolved TARGET path>` never comes into play — `create-next-app` only
   ever sees the empty scaffold directory. `create-next-app` detects that
   `$SCAFFOLD_TMP` sits inside an existing git repository (the `.git` from
   Task 5's `git init`, or whatever the author already had) and skips its own
   `git init`, so there is no `.git`-vs-`.git` collision when the contents
   move up. Nothing in the generated output is named `.claude` or `docs`, so
   the move cannot clobber either.

   Because `create-next-app` scaffolded into `$SCAFFOLD_TMP` instead of `.`,
   the `name` field it wrote into `package.json` is `wl-harness-scaffold` —
   the temp directory's basename, not the project's slug — and
   `create-next-app` has no flag to override it. The `node -e` command above
   runs after the move, with `<resolved TARGET path>` already the working
   directory, and rewrites `package.json`'s `name` to `<slug>` in place. It
   passes `package.json` as a plain relative path rather than interpolating
   an absolute Windows path into the `-e` string, so there is nothing for
   JS-string escaping to corrupt — the same hazard flagged above for
   `TARGET`.

   Then set `"strict": true` in `tsconfig.json` if the generator did not, create
   the directory layout above, and build each route from `docs/plan.md`. Every
   Ant Design component gets a wrapper in `src/components/ui/` first; routes
   import the wrapper.

6. **Verify** — Record stage `verify`. Run the acceptance criteria from
   `docs/spec.md`:

   ```bash
   cd "<resolved TARGET path>" && pnpm exec tsc --noEmit
   ```

   Report a pass/fail summary. On failure, fix and re-run — this loop is
   machine-judged and does not involve the author. Do not proceed until it
   passes.

7. **Handoff** — Record stage `handoff` only after step 6 is green; a failing
   check means the work is unfinished, not that a rule was broken. Tell the
   author what was built, which routes exist, and that `/ship` (a later slice)
   is what archives the work once they have accepted it.
````

- [ ] **Step 3: Write the alignment test**

Create `packages/wl-harness/scripts/check-command-steps.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const commandsDir = path.join(here, '..', 'commands');

// Spec section 5: the frontmatter `steps` array must match the body's ^N.
// lines one-for-one. That alignment is what makes a run resumable.
function frontmatterSteps(raw) {
  const block = raw.match(/^steps:\n((?:\s*-\s+.+\n)+)/m);
  if (!block) return [];
  return block[1]
    .split('\n')
    .filter((line) => line.trim().startsWith('-'))
    .map((line) => line.trim().replace(/^-\s*/, ''));
}

function numberedBodyLines(raw) {
  const body = raw.split(/^---$/m).slice(2).join('---');
  return body.match(/^\d+\.\s/gm) ?? [];
}

const commandFiles = readdirSync(commandsDir).filter((f) => f.endsWith('.md'));

test('there is at least one command to check', () => {
  assert.ok(commandFiles.length > 0);
});

for (const file of commandFiles) {
  test(`${file}: frontmatter steps align 1:1 with the numbered body lines`, () => {
    const raw = readFileSync(path.join(commandsDir, file), 'utf8');
    const steps = frontmatterSteps(raw);
    const numbered = numberedBodyLines(raw);
    assert.ok(steps.length > 0, 'no steps found in frontmatter');
    assert.equal(
      steps.length,
      numbered.length,
      `frontmatter declares ${steps.length} steps but the body has ${numbered.length} numbered lines`,
    );
  });
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test --prefix packages/wl-harness`
Expected: PASS — 23 tests passing. If the alignment test fails, the command's
frontmatter and body disagree: fix the command, not the test.

- [ ] **Step 5: Commit**

```bash
git add packages/wl-harness/contracts/ packages/wl-harness/commands/ packages/wl-harness/scripts/check-command-steps.test.mjs
git commit -m "feat(wl-harness): add init-project command and contract shape"
```

---

### Task 5: S0 acceptance — the real run

**Files:**
- Create: the author's personal website, in a directory outside this repo
- Modify: `TODO.md` (untracked, local only)

**Interfaces:**
- Consumes: everything built in Tasks 1–4.
- Produces: the recorded friction that answers D-2 (contract field shapes). **This
  is the point of S0** — a run that works but is not written up has wasted the slice.

This task is interactive and cannot be automated: it needs a live Claude Code
session with the plugin loaded.

- [ ] **Step 1: Load the plugin locally**

Run `/plugin-dev wl-harness local`, then restart the session so the command and
hook are picked up. Confirm with `/plugin-dev wl-harness status` — the cache
entry should be a symlink.

- [ ] **Step 2: Create an empty target directory**

```bash
mkdir -p ~/projects/personal-site && cd ~/projects/personal-site && git init
```

- [ ] **Step 3: Run the command**

In a Claude Code session with that directory as the working directory:

```
/init-project my personal website
```

- [ ] **Step 4: Check the state file advanced through every stage**

While the run proceeds, and again at the end:

```bash
cat ~/projects/personal-site/.claude/workflow-state.md
```

Expected: frontmatter with `slug: my-personal-website` and a `stage` that ends at
`handoff`. Record any stage that was skipped or written out of order.

- [ ] **Step 5: Check the acceptance criterion actually ran**

```bash
cd ~/projects/personal-site && pnpm exec tsc --noEmit
```

Expected: exit 0. If it fails here but the command claimed Handoff, that is a
gate defect — record it.

- [ ] **Step 6: Provoke the red line**

Ask the session to add `import { Button } from "antd";` to `src/app/page.tsx`.

Expected: the PostToolUse hook emits a block decision and the agent corrects
itself by wrapping the component in `src/components/ui/` instead. If nothing
happens, the hook is not wired — check `/plugin-dev wl-harness status` and
`hooks/hooks.json`.

- [ ] **Step 7: Write up the friction**

Append to the `## 🚧 已知风险` section of `TODO.md` — one line per item:

- Which contract fields were missing (input for D-2: does a step need `acceptance`,
  `artifacts`, `preconditions`? did `type` want an enumeration after all?)
- Which stage transitions felt wrong or redundant
- Where stack knowledge leaked outside `commands/init-project.md` (input for S2)
- How long the run took end to end

- [ ] **Step 8: Commit the plan's completion**

```bash
git add docs/superpowers/plans/2026-09-05-wl-harness-s0.md
git commit -m "docs(wl-harness): record S0 acceptance run"
```

---

## Self-Review

**Spec coverage.** S0's six-layer table (§15) maps to tasks as follows: L1 →
Task 4 (`contracts/schema.json`, three fields, no validator); L2 → Task 2
(one `.mjs` reading and writing `workflow-state.md`, no MCP); L3 → Task 4
(`init-project`, complexity S, all eight stages); L4 → Task 2 (state file
records position only); L5 → Task 4 step 6 (`tsc --noEmit` as the single
acceptance criterion) and Task 5 step 5; L6 → Task 3 (one red line, one hook).
Task 1 carries the plugin plumbing the rest needs. Task 5 is the acceptance
run §15 requires.

**Deliberately out of scope**, per spec §15–§16: no `harness-check.mjs`, no
`ship-snapshot`, no `/ship` (stage 8 is S1), no `workstate/` state machine
(S1), no profile files (S2), no dependency-cruiser (S3), no CodeGraph or timing
(S4), no `feature-dev` or `bug-fix` (S4). Stage 8 appears in `STAGES` but no
command reaches it in S0 — that is intentional and matches the spine.

**Type consistency.** `workflowStatePath`, `slugify`, `readWorkflowState`,
`writeWorkflowState`, `parseFrontmatter`, `stringifyFrontmatter` and `STAGES`
are defined in Task 2 and used under those exact names in Task 4's command and
Task 5's checks. `shouldBlockUiImport` is defined and used only in Task 3. The
state field names `slug` and `stage` are identical across the script, its tests,
the command and the acceptance checks.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-05-wl-harness-s0.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
