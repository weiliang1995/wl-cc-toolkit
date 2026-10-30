#!/usr/bin/env bash
# Idempotently add the CodeRabbit review integration to the current Git repository:
#   - scripts/cr-agent.sh (copied from this skill; an existing file is never overwritten)
#   - .gitignore entries for generated review artifacts (only those not already ignored)
#   - a "cr" script in package.json, if the repo root has one and "cr" is not already taken

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ -e scripts/cr-agent.sh ]; then
  echo "scripts/cr-agent.sh exists; reusing it."
else
  mkdir -p scripts
  cp "$SKILL_DIR/scripts/cr-agent.sh" scripts/cr-agent.sh
  chmod +x scripts/cr-agent.sh
  echo "Created scripts/cr-agent.sh"
fi

# Generated artifacts only. Repo config (.coderabbit.yaml etc.) lives at the root and stays tracked.
# Each line: <gitignore pattern> <sample path that pattern must ignore>
missing=()
while read -r pattern probe; do
  git check-ignore -q --no-index "$probe" || missing+=("$pattern")
done <<'EOF'
/.coderabbit/review.ndjson .coderabbit/review.ndjson
/.coderabbit/review.tmp.* .coderabbit/review.tmp.abc123
/.coderabbit/stale/ .coderabbit/stale/cr-main-abc1234-20260101-000000.ndjson
EOF

if [ "${#missing[@]}" -eq 0 ]; then
  echo ".gitignore already covers CodeRabbit review artifacts."
else
  if [ -s .gitignore ] && [ -n "$(tail -c 1 .gitignore)" ]; then
    echo >> .gitignore
  fi
  {
    echo
    echo "# CodeRabbit local review artifacts (scripts/cr-agent.sh)"
    printf '%s\n' "${missing[@]}"
  } >> .gitignore
  echo "Added to .gitignore: ${missing[*]}"
fi

# Lets people run the review by hand with `npm run cr`. Keeps the file's own indentation.
if [ -f package.json ]; then
  if ! command -v node >/dev/null 2>&1; then
    echo "node not found; add \"cr\": \"bash scripts/cr-agent.sh\" to package.json scripts by hand."
  else
    node - <<'EOF'
const fs = require('fs');
const text = fs.readFileSync('package.json', 'utf8');
const pkg = JSON.parse(text);
const want = 'bash scripts/cr-agent.sh';
const have = pkg.scripts && pkg.scripts.cr;
if (have === want) {
  console.log('package.json already has the "cr" script.');
} else if (have !== undefined) {
  console.log(`package.json "cr" script is already "${have}"; left unchanged.`);
} else {
  pkg.scripts = { ...pkg.scripts, cr: want };
  const indent = (text.match(/^[ \t]+(?=")/m) || ['  '])[0];
  const eol = text.includes('\r\n') ? '\r\n' : '\n';
  const out = JSON.stringify(pkg, null, indent).replace(/\n/g, eol);
  fs.writeFileSync('package.json', out + (/\r?\n$/.test(text) ? eol : ''));
  console.log('Added "cr" script to package.json');
}
EOF
  fi
fi
