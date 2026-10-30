---
name: cr
description: Run a local CodeRabbit CLI review of the current Git branch or uncommitted changes and report the structured findings without changing code. Use when the user asks for a CodeRabbit review, a local or pre-PR code review of their current changes, or to generate CodeRabbit findings. To fix the findings, use cr-fix instead. Not for general code questions or reviews of GitHub PRs that do not mention CodeRabbit.
argument-hint: "[--base <branch>|--base-commit <sha>] [--include-untracked] [--committed|--uncommitted] [--dir <path>]"
---

# CodeRabbit review

Runs `coderabbit review --agent --fresh` through a small repo script and keeps one current review at `.coderabbit/review.ndjson`. Files under `.coderabbit/stale/` are history; never treat them as the current review.

`<skill-dir>` below means the directory containing this SKILL.md.

Run steps 1–4, then report and stop. Do not edit source code; fixing findings is the `cr-fix` skill's job.

Never commit, amend, push, merge, open a PR, or delete unrelated files unless the user asks for that separately.

## 1. CodeRabbit CLI

```bash
command -v coderabbit || ls ~/.local/bin/coderabbit
```

If either finds it, reuse it; do not reinstall. If it is missing, check the current official instructions at https://docs.coderabbit.ai/cli before installing (at the time of writing: `curl -fsSL https://cli.coderabbit.ai/install.sh | sh` or `brew install coderabbit`). Ask the user before installing. Afterwards verify with `coderabbit --help`.

If a review fails with an authentication error, ask the user to run `coderabbit auth login` (or `coderabbit auth login --agent` for agent-driven login). Do not handle credentials yourself.

## 2. Repository integration

From inside the Git repository:

```bash
bash <skill-dir>/scripts/bootstrap.sh
```

This creates `scripts/cr-agent.sh` only if it is missing; it never overwrites an existing one. It also appends `.gitignore` entries for generated artifacts (`review.ndjson`, `review.tmp.*`, `stale/`) only if they are not already ignored, and, if the repo root has a `package.json`, adds a `"cr": "bash scripts/cr-agent.sh"` script unless `cr` is already defined. It leaves CodeRabbit config files (`.coderabbit.yaml` etc. at the repo root) tracked.

## 3. Run the review

```bash
bash scripts/cr-agent.sh [coderabbit review options]
```

By default this reviews only what is not on the remote yet: commits since the point where the branch meets its upstream (or `origin/<branch>`), plus staged and unstaged edits to tracked files, but not untracked files. Pushed commits are left to the CodeRabbit review on the GitHub PR. A branch with no remote counterpart is compared against CodeRabbit's default base branch instead. The script prints which base it chose; include that in the report.

The remote-tracking ref is not fetched first, so commits pushed from elsewhere since the last fetch count as unpushed. That only widens the review.

Pass options through only when the user asks for a different scope, or their arguments include them:

- `--base <branch>` compares against that branch instead, e.g. `main` for the whole branch. CodeRabbit saves it as the repo's `coderabbit.baseBranch` git preference, which only matters for runs that bypass this script; say so when passing it. `--base-commit <sha>` sets an exact base without saving anything.
- `--include-untracked` also reviews files not yet added to Git.
- `--committed` / `--uncommitted` narrow the review to one side; `--dir <path>` to one directory.

Never pass `--agent` or `--fresh` (the script already does) or credential options such as `--api-key`.

- The review usually takes 2–6 minutes and can take up to 15. Use a long command timeout (≥ 15 min) or run it in the background and wait. Stopping it early discards the review.
- It needs network access. If a sandbox blocks it, ask for permission to run it outside the sandbox.
- Each run uses CodeRabbit review quota. Do not run it more often than this workflow allows.
- A non-zero exit means the previous `review.ndjson` was kept unchanged. Report the error and do not read the old file as if it were new.

## 4. Report

Read `.coderabbit/review.ndjson` (NDJSON: one JSON event per line):

- `review_context` holds `currentBranch`, `baseBranch`, and `reviewType`.
- `finding` holds `severity`, `fileName`, `startLine`, `endLine`, `title`, `comment`, and `codegenInstructions`.
- `complete` holds `status`, `outcome`, `findings` (count), `reviewedFiles`, and `message`.

Summarise the branch, base branch, review status/outcome, number of findings, and fresh/reused state. The script always passes `--fresh`, so the review is fresh unless the output says otherwise. Then list the findings by severity, giving file:line and title.

If there are zero findings, say whether this was a fresh review that completed with no findings, or whether the output shows that a checkpoint was reused or nothing was reviewed (e.g. empty `reviewedFiles`).

Stop here and let the user decide. If they want the findings fixed, that is `/coderabbit-review:cr-fix`.
