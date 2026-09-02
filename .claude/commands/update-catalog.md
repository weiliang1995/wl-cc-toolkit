---
name: update-catalog
description: Scan skills/, packages/ and scripts/ and incrementally update CATALOG.md
user-invocable: true
model-auto-invocable: false
---

# Update Catalog

Scan the repository and incrementally update `CATALOG.md`. Existing rows are never rewritten — only new entries are appended and stale ones are flagged.

## Usage
```
/update-catalog [--prune]
```

- `--prune`: also remove rows whose underlying file or directory no longer exists

## Steps

Constants:
- PROJECT = the git root of this repository (detect via `git rev-parse --show-toplevel`)
- CATALOG = `$PROJECT/CATALOG.md`

### 1. Read the current catalog

Read CATALOG and index the existing rows per table, keyed by the file or directory name in the first column. This key set is what makes the update incremental — anything already keyed is left untouched, including hand-edited descriptions.

### 2. Scan `skills/`

For each `.md` file under `$PROJECT/skills/` (skip `.gitkeep`):
- Read the frontmatter and extract `name` and `description`
- If `name` is missing, fall back to the filename without its extension
- If the file is not already in the Skills table, append a row: file, description, `/<name>`

### 3. Scan `packages/`

For each subdirectory of `$PROJECT/packages/`:
- Read `.claude-plugin/plugin.json` and extract `description` and `version`
- If that file is missing, use the first paragraph of the directory's `README.md`
- If neither exists, skip the directory — it is not a publishable package yet
- If the directory is not already in the Packages table, append a row

### 4. Scan `scripts/`

For each `.ps1`, `.sh`, `.js`, or `.ts` file under `$PROJECT/scripts/` (skip `.gitkeep`):
- Read the leading comment block (up to the first 5 lines) for a description
- If there is no header comment, use the filename and mark the description as `TODO`
- If the file is not already in the Scripts table, append a row

### 5. Write the catalog back

- Append new rows to the end of their table, preserving the order of existing rows
- Drop any `_(pending)_` placeholder row from a table that now has real entries
- Leave all prose outside the tables exactly as it is

With `--prune`, also drop rows whose target no longer exists on disk. Without it, list those rows as stale in the summary but leave them in place.

### 6. Report

Print what changed, grouped by table:

```
Skills:   +2 added, 1 stale
Packages: no changes
Scripts:  +1 added
```

If nothing changed anywhere, print `Catalog is up to date.` and make no edit to the file.
