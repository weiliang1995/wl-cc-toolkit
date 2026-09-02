---
description: Toggle any wl-cc-toolkit plugin to local dev mode (symlink) or back to remote
allowed-tools: Bash, Read
---

# Plugin Dev Toggle
Given a plugin name, automatically resolve its local source path from `marketplace.json` and switfch between local dev mode and remote cache mode.

## Usage
`/plugin-dev <plugin-name> [local|remote|status]`

- `plugin-name`: The `name` field in marketplace.json
- Action defaults to `local`

## Implementation

Constants:
- CACHE = `~/.claude/plugins/cache/wl-cc-toolkit`
- MARKETPLACE = `~/.claude/plugins/marketplaces/wl-cc-toolkit/marketplace.json`
- PROJECT = the git root of this repository (detect via `git rev-parse --show-toplevel`)

### Step 1: Resolve source path
Read MARKETPLACE and find the plugin with `name == plugin-name`, extract its `source` field. The absolute local path is `$PROJECT/{source without leading ./}`.

If not found, list available plugin names and abort.

### Step 2: Execute action
#### `status` (or no action specified after name):
```bash
ls -la $CACHE/{plugin-name}/
```
Report: symlink entries = local dev mode, regular dirs = remote cached.

#### `local`:
1. Resolve local path from step 1
2. Read `{local-path}/.claude-plugin/plugin.json` to get `version`
3. Replace cache directory with symlink to local source:
```bash
rm -rf $CACHE/{plugin-name}
ln -s {local-path} $CACHE/{plugin-name}/{version}
```
4. Update `~/.claude/plugins/installed_plugins.json`:
  - Find entry where key is `${plugin-name}@wl-cc-toolkit`
  - set `installPath` to `{local-path}`
  - set `version` to `{version}`
5. Verify: `ls -la $CACHE/{plugin-name}/` shows symlink, and content matches local source
6. Print: "Done. Cache symlinked + installpath updated. New sessions will load local source."

> **Why both?** Claude code loads skills from the cache path at session start, ignoring installPath. The symlink ensures the cahce reads local files. installPath is updated as a secondary signal.

#### `remote`:
1. Remove symlink and restore cache from remote:
```bash
rm -f $CACHE/{plugin-name}/{version}
```
2. Update `~/.claude/plugins/installed_plugins.json`:
  - Set `installPath` back to `$CACHE/{plugin-name}/{version}`
3. Run `/reload-plugins` to re-fetch from remote into cache
4. Verify: `ls -la $CACHE/{plugin-name}/` shows regular directory (not symlink), and content matches remote source
5. Print: "Restored to remote. Plugin will use cached version."

