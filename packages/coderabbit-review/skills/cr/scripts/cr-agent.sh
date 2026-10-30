#!/usr/bin/env bash
# Run a fresh CodeRabbit agent review and keep exactly one current review:
#   .coderabbit/review.ndjson   current valid review
#   .coderabbit/stale/          superseded reviews (history only)
# The current review is replaced only after a new review succeeds.
# By default only what is not on the remote yet is reviewed: commits since the branch's
# upstream (or origin/<branch>) plus local edits. Pushed commits are left to the PR review.
# Extra arguments go to `coderabbit review`, e.g. `--base main` or `--include-untracked`;
# passing --base or --base-commit overrides the default base.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# The official installer puts the binary in ~/.local/bin, which non-login shells may miss.
if ! command -v coderabbit >/dev/null 2>&1 && [ -x "$HOME/.local/bin/coderabbit" ]; then
  PATH="$HOME/.local/bin:$PATH"
fi
command -v coderabbit >/dev/null 2>&1 || { echo "coderabbit CLI not found." >&2; exit 127; }

BASE_DIR=".coderabbit"
STALE_DIR="$BASE_DIR/stale"
ACTIVE_FILE="$BASE_DIR/review.ndjson"

mkdir -p "$STALE_DIR"
# Leftovers from runs that were killed outright (SIGKILL, e.g. a tool timeout) skip the trap.
rm -f "$BASE_DIR"/review.tmp.*
TMP_FILE=$(mktemp "$BASE_DIR/review.tmp.XXXXXX")
trap 'rm -f "$TMP_FILE"' EXIT

# Read a flat string/number field from one NDJSON line.
field() {
  sed -nE "s/.*\"$2\" *: *\"?([^\",}]*)\"?.*/\1/p" <<<"$1"
}

args=("$@")
explicit_base=no
for a in "$@"; do
  case "$a" in --base|--base=*|--base-commit|--base-commit=*) explicit_base=yes ;; esac
done

if [ "$explicit_base" = no ]; then
  # --base-commit rather than --base: --base is saved as a repo-wide git preference.
  REMOTE=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)
  CUR=$(git branch --show-current 2>/dev/null || true)
  if [ -z "$REMOTE" ] && [ -n "$CUR" ] && git rev-parse -q --verify "refs/remotes/origin/$CUR" >/dev/null; then
    REMOTE="origin/$CUR"
  fi
  if [ -n "$REMOTE" ]; then
    FORK=$(git merge-base HEAD "$REMOTE")
    args+=(--base-commit "$FORK")
    echo "Reviewing changes not yet on $REMOTE (since $(git rev-parse --short "$FORK"))."
  else
    echo "No remote branch yet; CodeRabbit compares against its default base branch."
  fi
fi

echo "Running fresh CodeRabbit review (can take up to ~15 minutes)..."

rc=0
coderabbit review --agent --fresh ${args[@]+"${args[@]}"} | tee "$TMP_FILE" || rc=$?

if [ "$rc" -ne 0 ]; then
  echo "CodeRabbit review failed (exit $rc). Current review left unchanged." >&2
  exit "$rc"
fi

if [ ! -s "$TMP_FILE" ]; then
  echo "CodeRabbit returned empty output. Current review left unchanged." >&2
  exit 1
fi

COMPLETE=$(grep -E '"type" *: *"complete"' "$TMP_FILE" | tail -n 1 || true)
if [ -z "$COMPLETE" ]; then
  echo "No 'complete' event in CodeRabbit output. Current review left unchanged." >&2
  exit 1
fi

if [ -f "$ACTIVE_FILE" ]; then
  BRANCH=$(git branch --show-current 2>/dev/null || true)
  BRANCH=$(printf '%s' "${BRANCH:-detached}" | tr -c 'A-Za-z0-9._-' '-')
  SHA=$(git rev-parse --short HEAD 2>/dev/null || echo nohead)
  TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
  ARCHIVE_FILE="$STALE_DIR/cr-${BRANCH}-${SHA}-${TIMESTAMP}.ndjson"
  n=1
  while [ -e "$ARCHIVE_FILE" ]; do
    ARCHIVE_FILE="$STALE_DIR/cr-${BRANCH}-${SHA}-${TIMESTAMP}-$((n++)).ndjson"
  done
  mv "$ACTIVE_FILE" "$ARCHIVE_FILE"
  echo "Archived previous review: $ARCHIVE_FILE"
fi

mv "$TMP_FILE" "$ACTIVE_FILE"

CONTEXT=$(grep -E '"type" *: *"review_context"' "$ACTIVE_FILE" | head -n 1 || true)

echo
echo "Current CodeRabbit review: $ACTIVE_FILE"
echo "  branch:   $(field "$CONTEXT" currentBranch)"
echo "  base:     $(field "$CONTEXT" baseBranch)"
echo "  status:   $(field "$COMPLETE" status) / $(field "$COMPLETE" outcome)"
echo "  findings: $(field "$COMPLETE" findings)"
echo "  fresh:    yes (--fresh)"
