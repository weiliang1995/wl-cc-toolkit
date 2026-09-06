---
id: init-project-s0
type: init-project
description: Scaffold a new complexity-S, frontend-only Next.js project through all eight harness stages
allowed-tools: Bash, Read, Write, Edit, Glob
steps:
  - intake
  - context-load
  - design
  - plan
  - implement
  - verify
  - handoff
---

# init-project

Scaffold a new project from nothing, walking every stage of the harness spine.

**S0 scope:** complexity S, frontend-only, one stack. Complexity M/L, other stacks
and the profile mechanism are later slices — do not generalise this file.

## Usage

`/init-project <short project description>`

Example: `/init-project my personal website`

## Fixed stack (S0-HARDCODE)

These are not decisions to re-litigate during a run. In S2 they move into a
profile; until then they live here:

- **Framework:** Next.js, App Router, TypeScript strict
- **Package manager:** pnpm
- **Styling:** Less. Component styles are `*.module.less`; globals hold only
  variables, reset and theme
- **UI:** Ant Design, always wrapped behind `src/components/ui/`. Business code
  imports from `src/components/ui/`, never from `antd` directly — a PostToolUse
  hook rejects violations
- **Not installed unless a page needs one:** react-hook-form, zod, dayjs, axios
- **No database, no auth:** complexity S, frontend-only

## Directory layout (S0-HARDCODE)

```
src/
  app/              routing
  components/       presentational, no business logic
  components/ui/    the only place antd may be imported
  hooks/
  services/         request layer, one file per module
  types/
  styles/           variables, mixins, globals
  utils/
public/
```

## Implementation

Resolve `HARNESS`, the absolute path to `workflow-state.mjs`, before doing
anything else. `CLAUDE_PLUGIN_ROOT` is set reliably when Claude Code dispatches
a hook, but it is not guaranteed to reach the shell environment of a Bash call
made from inside a slash command's own instructions — treat it as a hint, not
a given:

```bash
HARNESS=""
if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -f "$CLAUDE_PLUGIN_ROOT/scripts/workflow-state.mjs" ]; then
  HARNESS="$CLAUDE_PLUGIN_ROOT/scripts/workflow-state.mjs"
else
  HARNESS=$(find ~/.claude/plugins -path "*/wl-harness/scripts/workflow-state.mjs" -print -quit 2>/dev/null)
fi
if [ -z "$HARNESS" ] || [ ! -f "$HARNESS" ]; then
  echo "ERROR: could not locate wl-harness/scripts/workflow-state.mjs (checked \$CLAUDE_PLUGIN_ROOT and ~/.claude/plugins)"
  exit 1
fi
HARNESS=$(node -e "console.log(require('fs').realpathSync(process.argv[1]))" "$HARNESS")
echo "Resolved HARNESS: $HARNESS"
```

`~/.claude/plugins` may hold a symlink into a local checkout during
development — `find` follows it, and the `realpathSync` call above resolves
the final path to an absolute, non-symlinked location before it is used.
Stop with the printed error if no file is found; do not guess a path and
continue.

Let `TARGET` be the absolute path of the directory being initialised (the
current working directory unless the author names another).

Record the stage at the *start* of each numbered step, using:

```bash
node -e "import('file://$HARNESS').then(m => m.writeWorkflowState('$TARGET', { slug: '<slug>', stage: '<stage>' }))"
```

1. **Intake** — Derive the slug from the description with `slugify` (for example
   `my personal website` becomes `my-personal-site`). Confirm `TARGET` is empty
   or contains only `.git`; if it holds other files, stop and tell the author
   this command is for empty repositories. Write the state file with stage
   `intake`.

2. **Context load** — Record stage `context-load`. State back to the author, in
   one short block: the fixed stack above, the directory layout above, and the
   one red line (no `antd` outside `src/components/ui/`). This is the injection
   step — the agent that writes code in step 5 must have seen it.

3. **Design** — Record stage `design`. Selection is already fixed by the stack
   block, so the only real decision here is structure. Ask the author for the
   page list if the description does not imply one, then write
   `docs/spec.md` in `TARGET` containing: the project's purpose in one
   sentence, the list of routes with one line each, and the acceptance criteria
   ("`pnpm exec tsc --noEmit` passes", "every route renders", plus anything the
   author named). Keep it to intent and acceptance — no implementation detail.

4. **Plan** — Record stage `plan`. Write `docs/plan.md` in `TARGET` listing the
   scaffold steps in order, each with the files it produces. For a typical
   personal site that is: create the Next.js app, add Less and Ant Design,
   create the `src/components/ui/` wrappers the routes need, then one step per
   route.

5. **Implement** — Record stage `implement`. Work through `docs/plan.md` in
   order:

   ```bash
   cd "$TARGET"
   pnpm create next-app@latest . --ts --eslint --app --src-dir --import-alias "@/*" --no-tailwind
   pnpm add antd less
   ```

   Then set `"strict": true` in `tsconfig.json` if the generator did not, create
   the directory layout above, and build each route from `docs/plan.md`. Every
   Ant Design component gets a wrapper in `src/components/ui/` first; routes
   import the wrapper.

6. **Verify** — Record stage `verify`. Run the acceptance criteria from
   `docs/spec.md`:

   ```bash
   cd "$TARGET" && pnpm exec tsc --noEmit
   ```

   Report a pass/fail summary. On failure, fix and re-run — this loop is
   machine-judged and does not involve the author. Do not proceed until it
   passes.

7. **Handoff** — Record stage `handoff` only after step 6 is green; a failing
   check means the work is unfinished, not that a rule was broken. Tell the
   author what was built, which routes exist, and that `/ship` (a later slice)
   is what archives the work once they have accepted it.
