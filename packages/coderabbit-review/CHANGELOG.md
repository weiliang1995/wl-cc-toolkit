# Changelog

## 1.0.0 - 2026-10-30

### Added
- `/coderabbit-review:cr` skill: runs a local CodeRabbit CLI review (`coderabbit review --agent --fresh`) of the current branch and reports the findings by severity, without changing code
- `/coderabbit-review:cr-fix` skill: runs the same review, validates each finding against the code, fixes only the valid ones, runs the repo's real lint/typecheck/test commands, and allows at most one final review
- `cr-fix --reuse`: fixes the current `.coderabbit/review.ndjson` (e.g. after `npm run cr`) instead of running a new review, falling back to a review when there is no complete report for the current branch
- `bootstrap.sh` adds a `"cr": "bash scripts/cr-agent.sh"` script to the repo root `package.json` (if present and `cr` is not taken), preserving its indentation and line endings
- `cr-agent.sh` passes extra arguments through to `coderabbit review`, e.g. `npm run cr -- --base main` or `--include-untracked`

### Changed
- Reviews cover only what is not on the remote yet by default: commits since the branch's upstream (or `origin/<branch>`) plus local edits, passed as `--base-commit` so no git preference is saved. Pushed commits are left to the CodeRabbit review on the GitHub PR; an explicit `--base` or `--base-commit` overrides this

### Fixed
- `cr-agent.sh` removes leftover `.coderabbit/review.tmp.*` files from runs that were killed before they could clean up
