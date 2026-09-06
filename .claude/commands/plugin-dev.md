---
description: Toggle any wl-cc-toolkit plugin to local dev mode (link) or back to remote
allowed-tools: Bash, Read
---

# Plugin Dev Toggle

Point a plugin's cache entry at this working tree so edits take effect without publishing,
or put it back on the remote cache.

## Usage

`/plugin-dev <plugin-name> [local|remote|status]`

- `plugin-name`: the `name` field in the local `.claude-plugin/marketplace.json`
- Action defaults to `local`

## Implementation

Constants:

- PROJECT = git root of this repository (`git rev-parse --show-toplevel`)
- MARKETPLACE = `$PROJECT/.claude-plugin/marketplace.json` — **the local one, on the branch
  currently checked out**
- CACHE = `~/.claude/plugins/cache/wl-cc-toolkit`
- REGISTRY = `~/.claude/plugins/installed_plugins.json`

> **Read the local marketplace, not the installed clone.** The clone under
> `~/.claude/plugins/marketplaces/` tracks `main`, but plugins are developed on a feature
> branch and verified before they are merged. Resolving a name against `main` while
> computing a path into this working tree means a plugin that only exists on the branch is
> reported missing even though its source is right there.

### Step 1: Resolve source path

Read MARKETPLACE, find the plugin whose `name` matches, and take its `source`. The absolute
local path is `$PROJECT/{source without leading ./}`.

If the name is not found, list the names the local marketplace does contain and stop —
adding that the plugin may be on a different branch, or its marketplace entry may not be
committed yet.

If the resolved path does not exist on disk, stop and say so rather than linking a hole.

### Step 2: Execute action

#### `status` (also the default when no action is given)

```bash
node -e "
const fs = require('fs'), path = require('path'), dir = process.argv[1];
if (!fs.existsSync(dir)) { console.log('not in cache'); process.exit(0); }
for (const entry of fs.readdirSync(dir)) {
  const at = path.join(dir, entry);
  console.log(fs.lstatSync(at).isSymbolicLink()
    ? entry + ' -> local dev, linked to ' + fs.realpathSync(at)
    : entry + ' -> remote cache (real directory)');
}" "$CACHE/{plugin-name}"
```

Node reports a Windows junction as `isSymbolicLink()`, so one check covers junctions and
POSIX symlinks alike. Do not judge this from `ls -la`: a junction prints no `->` arrow
there and would be misreported as remote.

#### `local`

1. Resolve the local path (step 1).
2. Read `{local-path}/.claude-plugin/plugin.json` for `version`.
3. Replace the cache entry with a link to the local source:

```bash
mkdir -p "$CACHE/{plugin-name}"
rm -rf "$CACHE/{plugin-name}/{version}"
```

On **Windows**, create a directory junction — not a symlink:

```bash
powershell -NoProfile -Command "New-Item -ItemType Junction -Path '<cache>/{plugin-name}/{version}' -Target '<local-path>'"
```

On **macOS / Linux**:

```bash
ln -s "{local-path}" "$CACHE/{plugin-name}/{version}"
```

> **Why a junction on Windows.** Git Bash's `ln -s` defaults to copying: it exits 0, the
> directory reads correctly, and `test -L` returns false — a snapshot that silently stops
> tracking the source, so later edits appear to have no effect. Real symlinks need
> `MSYS=winsymlinks:nativestrict` plus Developer Mode or an elevated shell, which cannot be
> assumed. Junctions need neither, work across drives, and `rm -rf` on one removes the
> junction without touching the target.

4. Update REGISTRY at key `{plugin-name}@wl-cc-toolkit`. **Create the entry if it is
   absent** — a plugin being linked for the first time has never been installed, so there is
   nothing to find, and Claude Code will not load a plugin with no registry entry. The value
   is an array with a single object:

```json
{
  "scope": "user",
  "installPath": "<local-path, native separators>",
  "version": "<version>",
  "installedAt": "<existing value, or now as ISO-8601>",
  "lastUpdated": "<now as ISO-8601>",
  "gitCommitSha": "<git rev-parse HEAD in PROJECT>"
}
```

5. **Verify the link actually conducts.** Append a byte to a file in the local source, read
   that file back through the cache path, and confirm the byte is there — then remove it:

```bash
echo "" >> "{local-path}/.claude-plugin/plugin.json"
tail -c 40 "$CACHE/{plugin-name}/{version}/.claude-plugin/plugin.json"
cd "$PROJECT" && git checkout .claude-plugin/plugin.json 2>/dev/null || true
```

If the change is not visible through the cache path, the link is a copy: report failure and
do not claim success. Checking that `ls` "looks right" is exactly the test a copy passes.

6. Print: `Linked {plugin-name} -> {local-path}. Restart the session to load it.`

> **Why both the cache link and the registry?** Claude Code loads plugin content from the
> cache path at session start and ignores `installPath`, so the link is what makes local
> code take effect. The registry entry is what makes the plugin load at all.

#### `remote`

1. Remove the link (`rm -rf`, not `rm -f` — the entry is a directory or a junction, and
   `rm -f` fails on both):

```bash
rm -rf "$CACHE/{plugin-name}/{version}"
```

2. In REGISTRY, set `installPath` back to `$CACHE/{plugin-name}/{version}`.
3. Run `/reload-plugins` to re-fetch the remote copy into the cache.
4. Verify with `status` that the entry is a real directory again.
5. Print: `Restored {plugin-name} to the remote cache.`

> A plugin that has never been published has no remote copy to restore. Say so rather than
> leaving an empty cache directory behind.
