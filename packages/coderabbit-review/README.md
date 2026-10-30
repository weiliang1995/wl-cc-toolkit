# coderabbit-review

Plugin wrapper that ships two skills for Claude Code and Codex, both built on a local
CodeRabbit CLI review (`coderabbit review --agent --fresh`) of the current Git repository:

- **`/coderabbit-review:cr`** — ensure the CLI and repo integration exist → run the review →
  summarise `.coderabbit/review.ndjson` → stop. Source code is not touched.
- **`/coderabbit-review:cr-fix`** — the same review, then validate each finding against the
  code, fix only the valid ones, and run the repo's real lint/typecheck/test commands. At
  most one final review may follow. `/coderabbit-review:cr-fix --reuse` fixes the current
  `.coderabbit/review.ndjson` (e.g. after `npm run cr`) instead of running a new review; it
  falls back to reviewing if there is no complete report for the current branch.

Neither skill commits, pushes, or opens PRs.

By default a review covers only what is not on the remote yet: commits since the branch's
upstream (or `origin/<branch>`) plus staged and unstaged edits, not untracked files.
Pushed commits are left to the CodeRabbit review on the GitHub PR. A branch that has never
been pushed is compared against CodeRabbit's default base branch (usually `main`).

Options after the command, or after `npm run cr --`, go straight to `coderabbit review`:

```bash
npm run cr -- --base main                # review the whole branch against main
npm run cr -- --include-untracked        # also review files not added to Git
/coderabbit-review:cr --base main
/coderabbit-review:cr-fix --reuse
```

The default base is passed as `--base-commit`, which saves nothing. An explicit `--base` is
remembered as the repo's `coderabbit.baseBranch` git preference by CodeRabbit.

`scripts/cr-agent.sh` is never overwritten, so a repo bootstrapped before option
pass-through was added keeps its old copy; delete it and rerun the skill to get the new one.

## Files it may create in a repository

| Path | Purpose |
|---|---|
| `scripts/cr-agent.sh` | Review runner, copied from `skills/cr/scripts/cr-agent.sh` only if missing; an existing copy is never overwritten |
| `.gitignore` | Entries for the artifacts below are appended only if not already ignored |
| `package.json` | A `"cr": "bash scripts/cr-agent.sh"` script, so `npm run cr` runs a review by hand; added only if the repo root has a `package.json` and `cr` is not already defined |
| `.coderabbit/review.ndjson` | The current review; replaced only after a new review succeeds |
| `.coderabbit/stale/cr-<branch>-<sha>-<timestamp>.ndjson` | Previous reviews, kept as history |
| `.coderabbit/review.tmp.*` | In-progress output, removed when the script exits |

Per-repo `scripts/cr-agent.sh` and `.coderabbit/` stay after the plugin is removed; delete
them by hand if no longer wanted.
