# CATALOG.md

Index of all skills, plugins and tools.

## Skills

| File | Description | Invocation |
|------|-------------|------------|
| `packages/ui-code-inspector/skills/ui-code-inspector/SKILL.md` | Adds a dev-only click-the-UI-to-open-the-source inspector to Vite React projects | `/ui-code-inspector` (install the ui-code-inspector plugin first) |
| `packages/e2e-test/skills/e2e-test/SKILL.md` | Sets up Playwright E2E tests with istanbul branch coverage and generates, runs and fixes a test for each code branch | `/e2e-test` (install the e2e-test plugin first) |
| `packages/coderabbit-review/skills/cr/SKILL.md` | Runs a local CodeRabbit CLI review of the current branch and reports the findings | `/coderabbit-review:cr` (install the coderabbit-review plugin first) |
| `packages/coderabbit-review/skills/cr-fix/SKILL.md` | Runs a CodeRabbit review, then validates and fixes the findings and runs lint/typecheck/tests | `/coderabbit-review:cr-fix` (install the coderabbit-review plugin first) |

## Packages / Plugins

| Directory | Description |
|-----------|-------------|
| `packages/cc-dialogs` | Replaces Claude Code's terminal prompts with native macOS / Windows dialogs |
| `packages/ui-code-inspector` | Plugin wrapper that ships the `/ui-code-inspector` skill |
| `packages/e2e-test` | Plugin wrapper that ships the `/e2e-test` skill |
| `packages/coderabbit-review` | Plugin wrapper that ships the `/coderabbit-review:cr` and `/coderabbit-review:cr-fix` skills |

## Scripts

| File | Description |
|------|-------------|
| _(none yet)_ | |

---

> Update this file whenever something is added.
