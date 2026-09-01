# UI Code Inspector Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Claude Code skill that guides agents through integrating a dev-only UI-to-source inspector for Vite React and Next.js projects.

**Architecture:** The repository stores skills as Markdown files under `skills/` with frontmatter. The new skill encodes a structured detect-then-adapt workflow, separating compile-time metadata injection from a framework-neutral DOM runtime and editor launch path.

**Tech Stack:** Claude Code skill Markdown, repository catalog Markdown, Vite React, Next.js, Babel/SWC concepts, DOM event handling, editor launch endpoints.

**Spec:** `docs/superpowers/specs/2026-09-01-ui-code-inspector-skill-design.md`

## Global Constraints

- Skill name is `ui-code-inspector`.
- Phase one executable targets are Vite React and Next.js.
- Vue, Angular, Nuxt, and unknown frameworks are detection-only or advisory in phase one.
- The target integration must be dev-only.
- Production output must not contain inspector attributes or runtime code.
- Runtime inspector behavior must be framework-neutral DOM code.
- Do not update `CATALOG.md` until formal publication.

---

### Task 1: Add Skill File

**Files:**
- Create: `skills/ui-code-inspector.md`

**Interfaces:**
- Consumes: The design in `docs/superpowers/specs/2026-09-01-ui-code-inspector-skill-design.md`.
- Produces: A callable Claude Code skill named `ui-code-inspector`.

- [x] **Step 1: Create the skill frontmatter**

```markdown
---
name: ui-code-inspector
description: Use when adding or reviewing a local development UI-to-source inspector for Vite React or Next.js projects, where clicking a rendered UI element should open the source file line in the editor.
---
```

- [x] **Step 2: Add the required workflow**

Add sections for scope, repo inspection, structured framework detection, architecture, Vite React, Next.js, runtime inspector, editor launch, verification, and stop conditions.

- [x] **Step 3: Encode stop conditions**

Include stop conditions for unsupported frameworks, ambiguous detection, unsafe compile-chain replacement, unapproved SWC/Babel tradeoffs, and non-dev-only editor launch.

### Task 2: Keep Catalog Draft-Free

**Files:**
- Read: `CATALOG.md`

**Interfaces:**
- Consumes: `skills/ui-code-inspector.md`.
- Produces: Confirmation that draft skill development does not publish the catalog entry early.

- [x] **Step 1: Leave the Skills table unchanged during draft development**

Do not add `/ui-code-inspector` to `CATALOG.md` until formal publication.

- [x] **Step 2: Preserve existing catalog content**

Do not remove existing entries or sections.

### Task 3: Verify Repository State

**Files:**
- Read: `skills/ui-code-inspector.md`
- Read: `CATALOG.md`

**Interfaces:**
- Consumes: The edited files.
- Produces: Verification evidence.

- [ ] **Step 1: Confirm files exist**

Run:

```powershell
Test-Path skills/ui-code-inspector.md
Test-Path CATALOG.md
```

Expected: both commands return `True`.

- [ ] **Step 2: Confirm skill frontmatter is present**

Run:

```powershell
Get-Content -First 5 skills/ui-code-inspector.md
```

Expected: output includes `name: ui-code-inspector`.

- [ ] **Step 3: Confirm catalog does not publish the draft skill**

Run:

```powershell
Select-String -Path CATALOG.md -Pattern "ui-code-inspector"
```

Expected: no matches until formal publication.
