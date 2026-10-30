# coderabbit-review

Plugin wrapper that ships the `/coderabbit-review` skill for Claude Code and Codex.

The skill runs a local CodeRabbit CLI review (`coderabbit review --agent --fresh`) of the
current Git repository and reports the findings.

- **Review mode (default):** ensure the CLI and repo integration exist → run the review →
  summarise `.coderabbit/review.ndjson` → stop. Source code is not touched.
- **Fix mode (only on explicit request):** after the review, validate each finding against
  the code, fix only the valid ones, and run the repo's real lint/typecheck/test commands.
  At most one final review may follow.

The skill never commits, pushes, or opens PRs.

## Files it may create in a repository

| Path | Purpose |
|---|---|
| `scripts/cr-agent.sh` | Review runner, copied from `skills/coderabbit-review/scripts/cr-agent.sh` only if missing; an existing copy is never overwritten |
| `.gitignore` | Entries for the artifacts below are appended only if not already ignored |
| `.coderabbit/review.ndjson` | The current review; replaced only after a new review succeeds |
| `.coderabbit/stale/cr-<branch>-<sha>-<timestamp>.ndjson` | Previous reviews, kept as history |
| `.coderabbit/review.tmp.*` | In-progress output, removed when the script exits |

Per-repo `scripts/cr-agent.sh` and `.coderabbit/` stay after the plugin is removed; delete
them by hand if no longer wanted.
