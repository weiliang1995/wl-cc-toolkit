---
name: publish
description: Publish a plugin - bump version, auto-generate commit message from changelog, commit and push
user-invocable: true
model-auto-invocable: false
---

# Publish Plugin

Bump version, generate changelog-based commit message, commit and push.

## Usage
```
/publish <package> <patch|minor|major>
```

If called without arguments or with incomplete arguments, show this help:

```
Usage: /publish <package> <bump>

Packages:
  example -> packages/example
  <other> -> packages/<name>

Bump types:
  patch x.y.z -> x.y.z+1 bugfixes, tweaks, skill wording
  minor x.y.z -> x.(y+1).0 new skills, new features
  major x.y.z -> (x+1).0.0 breaking changes

Examples:
  /publish example patch
  /publish example minor
```

Then stop and wait for user input.

## Steps

Constants:
- PROJECT = the git root of this repository (detect via `git rev-parse --show-toplevel`)
- MARKETPLACE = `$PROJECT/.claude-plugin/marketplace.json`

### 1. Resolve package

Map the package alias to its directory:
- `<name>` -> `$PROJECT/packages/<name>`

Verify `$PKG/.claude-plugin/plugin.json` exists. If not, list the directories under `packages/` and abort.

Read `plugin.json` and extract the current `version` and `name`.

### 2. Preflight checks

Abort with a clear message if any of these fail:

1. Working tree is clean for paths outside the package:
   ```bash
   git status --porcelain
   ```
   Uncommitted changes *inside* `packages/<name>/` are fine — they are part of this release. Changes elsewhere must be committed or stashed first.
2. Current branch is `main`:
   ```bash
   git rev-parse --abbrev-ref HEAD
   ```
   If not, ask the user to confirm before continuing.
3. Local branch is up to date with the remote:
   ```bash
   git fetch origin && git status -sb
   ```
   If behind, abort and tell the user to pull.

### 3. Compute the new version

Parse the current version as `x.y.z` and apply the bump:
- `patch` -> `x.y.(z+1)`
- `minor` -> `x.(y+1).0`
- `major` -> `(x+1).0.0`

Print `<name>: <old-version> -> <new-version>` so the user can see it.

### 4. Collect changes for the changelog

Find the previous release tag for this package:
```bash
git tag --list '<name>@*' --sort=-v:refname | head -1
```

List the commits touching this package since that tag (or since the first commit if there is no tag):
```bash
git log <last-tag>..HEAD --oneline -- packages/<name>/
```

Also include any uncommitted changes in the package:
```bash
git diff --stat -- packages/<name>/
git diff --cached --stat -- packages/<name>/
```

Read the actual diffs where the summary is not descriptive enough. Group what you find into these buckets, dropping any that are empty:
- **Added** — new skills, commands, features
- **Changed** — behavior or wording changes to existing entries
- **Fixed** — bug fixes

If there is nothing to publish, say so and stop — do not bump a version for an empty release.

### 5. Write the version bump

1. Update `version` in `$PKG/.claude-plugin/plugin.json`.
2. Update the matching plugin entry's `version` in MARKETPLACE, if that file tracks versions.
3. Prepend a new section to `$PKG/CHANGELOG.md` (create the file with a `# Changelog` header if it does not exist):

```markdown
## <new-version> - <YYYY-MM-DD>

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

Use today's date. Write entries in plain, specific language — name the skill or command that changed, not "various improvements".

### 6. Sync the catalog

Run the `/update-catalog` command so `CATALOG.md` picks up any new skills, packages, or scripts this release introduced.

### 7. Show the plan and confirm

Print a summary before touching git:

```
Package:  <name>
Version:  <old> -> <new>
Tag:      <name>@<new>
Files:    packages/<name>/.claude-plugin/plugin.json
          packages/<name>/CHANGELOG.md
          .claude-plugin/marketplace.json
          CATALOG.md

Commit message:
  <the message from step 8>
```

Ask the user to confirm. Stop and wait — do not commit, tag, or push without an explicit yes.

### 8. Commit, tag, push

Build the commit message from the changelog section:

```
release(<name>): v<new-version>

<the bullet lines from the changelog section, without the ### headers>
```

Then:
```bash
git add packages/<name>/ .claude-plugin/marketplace.json CATALOG.md
git commit -m "<message>"
git tag <name>@<new-version>
git push origin main --follow-tags
```

Report the pushed tag and commit SHA.

### 9. Post-publish note

Remind the user: if this package is currently symlinked into local dev mode, run `/plugin-dev <name> remote` to switch back to the published version before verifying the release.