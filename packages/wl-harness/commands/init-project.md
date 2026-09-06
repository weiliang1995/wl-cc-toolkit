---
id: init-project-s0
type: init-project
description: Scaffold a new complexity-S, frontend-only Next.js project through all stages up to Handoff
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
  imports from `src/components/ui/`, never from `antd` directly. A PostToolUse
  hook catches this, **but only for writes made with the Write and Edit tools** —
  a file written through Bash (`cat`, a heredoc, `sed -i`, `tee`) never triggers
  it, because the hook matches on tool name and a Bash payload carries a command
  string rather than a file path. Treat the rule as binding on you regardless of
  how you write the file; the hook is a safety net with a hole in it, not the
  authority.
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
  HARNESS=$(find -L ~/.claude/plugins -name workflow-state.mjs -path "*wl-harness*" -print -quit 2>/dev/null)
fi
if [ -z "$HARNESS" ] || [ ! -f "$HARNESS" ]; then
  echo "ERROR: could not locate wl-harness/scripts/workflow-state.mjs (checked \$CLAUDE_PLUGIN_ROOT and ~/.claude/plugins)"
  exit 1
fi
HARNESS_URL=$(node -e "console.log(require('url').pathToFileURL(require('fs').realpathSync(process.argv[1])).href)" "$HARNESS")
echo "resolved HARNESS url: $HARNESS_URL"
```

`HARNESS` must be resolved to a `file://` URL, not left as a native path. A
native Windows path (`D:\...`) concatenated after `file://` is not a valid URL
and `import()` rejects it with `ERR_INVALID_URL`; `pathToFileURL` is what
correctly escapes and formats it on every platform, including the `/c/...`
MSYS-style paths `find` can produce on Windows.

The real Claude Code plugin layout nests a marketplace and version segment
between `plugins` and the plugin's own files (for example
`~/.claude/plugins/cache/<marketplace>/wl-harness/<version>/scripts/workflow-state.mjs`),
so the fallback search matches by filename and filters on `wl-harness`
appearing anywhere in the path, rather than assuming `scripts/` is a direct
child of a directory literally named `wl-harness`. `-L` makes `find` follow a
symlinked plugin directory, which is how local-checkout dev mode is wired in.
If more than one match exists, take the first and trust the echoed path —
that echo is the record of which one was used. Stop with the printed error if
no file is found; do not guess a path and continue.

Let `TARGET` be the absolute path of the directory being initialised (the
current working directory unless the author names another).

**Both resolutions above happen exactly once, in this preamble, before step 1
runs.** Each numbered step below is a separately-invoked Bash call, and shell
state — including `$HARNESS_URL` and `$TARGET` — does not persist between
separate Bash tool calls; only the working directory does. So `$HARNESS_URL`
and `$TARGET` used in this preamble are placeholders for exposition only: once
resolved and echoed here, carry the two absolute values forward as literal
text substituted into every later command in this run, not as live shell
variables. The remaining examples in this file write `<resolved HARNESS
url>` and `<resolved TARGET path>` to mark exactly where that substitution
happens.

Record the stage at the *start* of each numbered step, using:

```bash
node -e "import('<resolved HARNESS url>').then(m => m.writeWorkflowState(process.argv[1], { slug: '<slug>', stage: '<stage>' }))" "<resolved TARGET path>"
```

**`TARGET` MUST be passed as a Node `argv` value (read back via
`process.argv[1]`), never interpolated directly into the `-e` JS string.** A
Windows `TARGET` contains backslashes (`C:\Users\...`); inside a JS string
those are consumed as escape sequences with no error, silently corrupting the
path (e.g. `\U` and `\t` vanish or turn into a tab) so the state file lands
somewhere unintended and the run looks like it succeeded. Passing it as
`argv` sidesteps JS string-escape processing entirely. Do not "simplify" this
back to string interpolation in a future edit — it is the fix for a
reproduced silent-corruption bug, not a style preference.

1. **Intake** — Derive the slug, then confirm the target is empty.

   The argument to this command may carry more than the project's name — a
   description, testing instructions, whatever the author typed. **Only the
   project's short name feeds the slug.** Do not slugify the whole argument:
   the result would be a long, wrong, but non-empty string, which every guard
   below would happily accept. If the name is not obvious from the argument,
   ask which part it is rather than guessing.

   `slugify` is exported by `workflow-state.mjs` — the same module as
   `writeWorkflowState`. Do not install a package of that name or write your
   own; behaviour differences here produce a slug that disagrees with the one
   in the state file. Call it the same way:

   ```bash
   node -e "import('<resolved HARNESS url>').then(m => console.log(m.slugify(process.argv[1])))" "<project name>"
   ```

   Echo the derived slug before using it, so a wrong one is visible rather
   than buried in a filename. It strips everything outside `[a-z0-9]` with no
   transliteration, so a non-ASCII name (Chinese, for example) collapses to an
   empty string. If the slug is empty, stop and ask the author for an explicit
   ASCII slug — never call `writeWorkflowState` with an empty slug.

   Then confirm `<resolved TARGET path>` is empty or contains only `.git`; if
   it holds other files, stop and tell the author this command is for empty
   repositories. Write the state file with stage `intake`.

2. **Context load** — Record stage `context-load`. State back to the author, in
   one short block: the fixed stack above, the directory layout above, and the
   one red line (no `antd` outside `src/components/ui/`). This is the injection
   step — the agent that writes code in step 5 must have seen it.

3. **Design** — Record stage `design`. Selection is already fixed by the stack
   block, so the only real decision here is structure. Ask the author for the
   page list if the description does not imply one, then write
   `docs/spec.md` in `<resolved TARGET path>` containing: the project's purpose in one
   sentence, the list of routes with one line each, and the acceptance criteria
   ("`pnpm exec tsc --noEmit` passes", "every route renders", plus anything the
   author named). Keep it to intent and acceptance — no implementation detail.

4. **Plan** — Record stage `plan`. Write `docs/plan.md` in `<resolved TARGET path>` listing the
   scaffold steps in order, each with the files it produces. For a typical
   personal site that is: create the Next.js app, add Less and Ant Design,
   create the `src/components/ui/` wrappers the routes need, then one step per
   route.

5. **Implement** — Record stage `implement`. Work through `docs/plan.md` in
   order.

   Scaffold directly into the target directory:

   ```bash
   cd "<resolved TARGET path>"
   pnpm create next-app@latest . --ts --eslint --app --src-dir --import-alias "@/*" --no-tailwind
   pnpm add antd less
   ```

   `create-next-app` refuses a non-empty directory unless every entry is on
   its whitelist, but everything present by this step is on it. The list, read
   from the published package, is: `.claude`, `.cursor`, `.DS_Store`, `.git`,
   `.gitattributes`, `.gitignore`, `.gitlab-ci.yml`, `.hg`, `.hgcheck`,
   `.hgignore`, `.idea`, `.npmignore`, `.travis.yml`, `.vscode`, `.zed`,
   `LICENSE`, `Thumbs.db`, `docs`, `mkdocs.yml`, `npm-debug.log`,
   `yarn-debug.log`, `yarn-error.log`, `yarnrc.yml`, `.yarn`. So `.claude/`
   from step 1, `docs/` from steps 3-4, and an existing `.git` all pass. Scaffolding
   into a temporary directory and moving the contents up is unnecessary — and
   costly, because the temp directory's basename becomes the package `name`
   and a dot-prefixed one is rejected outright by `validate-npm-package-name`.

   Then set `"strict": true` in `tsconfig.json` if the generator did not, create
   the directory layout above, and build each route from `docs/plan.md`. Every
   Ant Design component gets a wrapper in `src/components/ui/` first; routes
   import the wrapper.

6. **Verify** — Record stage `verify`. Run the acceptance criteria from
   `docs/spec.md`:

   ```bash
   cd "<resolved TARGET path>" && pnpm exec tsc --noEmit
   ```

   Report a pass/fail summary. On failure, fix and re-run — this loop is
   machine-judged and does not involve the author. Do not proceed until it
   passes.

7. **Handoff** — Record stage `handoff` only after step 6 is green; a failing
   check means the work is unfinished, not that a rule was broken. Tell the
   author what was built, which routes exist, and that `/ship` (a later slice)
   is what archives the work once they have accepted it.
