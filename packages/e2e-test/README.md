# e2e-test

Plugin wrapper that ships the `/e2e-test` skill for Claude Code and Codex.

The skill sets up Playwright E2E tests for a frontend project (with istanbul branch
coverage and the Playwright MCP), then analyses each branch in the code to generate, run
and fix test cases.

## Usage

```
/e2e-test [--all | --route <path> | --file <path> | --uncovered [path] | --setup-only]
```

| Argument | Behaviour |
|---|---|
| `--setup-only` | Only set up the environment; generate no tests |
| `--route <path>` | Test one route, e.g. `--route /sign-in` |
| `--file <path>` | Find every route that renders or calls the file and test that file's branches in them |
| `--all` | Scan every route and generate tests for each |
| `--uncovered [path]` | Run coverage first, then only add tests for uncovered branches; an optional path prefix filters them (e.g. `src/lib`) |
| _(none)_ | Set up, then list the routes found and the current coverage, and ask which scope to test |

See [skills/e2e-test/SKILL.md](skills/e2e-test/SKILL.md) for the full procedure.

## Layout

```
skills/e2e-test/
├── SKILL.md
├── scripts/uncovered-branches.mjs   # lists branches istanbul reports as uncovered
└── templates/                       # playwright.config.ts, fixtures, auth setup, .nycrc
```
