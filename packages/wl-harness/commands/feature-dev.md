---
id: feature-dev-quick-s1
type: feature-dev
description: Change a flow that already exists in this project, test-first, against its governing spec
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
steps:
  - intake
  - context-load
  - design
  - plan
  - implement
  - verify
  - handoff
---

# feature-dev

Change something in a project that already exists.

**S1 scope: the quick path only** — the flow being changed is already in the
repository. A change that needs a new subsystem, or that alters an interface
other code depends on, is the deep path and is not built yet; say so and stop
rather than improvising one.

## Usage

`/feature-dev <what you want changed>`

Example: `/feature-dev the four routes should become one page with anchor navigation`

## Fixed rules (S0-HARDCODE)

Same stack and layout as `init-project` — see that command's fixed stack block.
Two rules bind every step here:

- Business code imports UI primitives only from `src/components/ui/`, never from
  `antd` directly. A PostToolUse hook catches this, **but only for writes made
  with the Write and Edit tools** — a file written through Bash never triggers
  it. The rule binds you regardless of how you write the file.
- **Test-first.** Every module with behaviour gets its tests written before its
  implementation. Details in step 5.

## Implementation

Resolve `HARNESS`, the absolute path to `workflow-state.mjs`, before anything
else. `CLAUDE_PLUGIN_ROOT` is set reliably when Claude Code dispatches a hook,
but is not guaranteed in the shell environment of a Bash call made from inside a
slash command — treat it as a hint, not a given:

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

A native Windows path concatenated after `file://` is not a valid URL and
`import()` rejects it with `ERR_INVALID_URL`; `pathToFileURL` formats it
correctly on every platform, including the `/c/...` MSYS paths `find` produces
on Windows. The fallback search matches by filename and filters on `wl-harness`
anywhere in the path, because the plugin layout nests a marketplace and version
segment (`.../cache/<marketplace>/wl-harness/<version>/scripts/...`). `-L`
follows a symlinked plugin directory, which is how local dev mode is wired.

Let `TARGET` be the absolute path of the project being changed — the current
working directory.

**Both resolutions happen once, here.** Shell state does not persist between
separate Bash tool calls; only the working directory does. Carry the two
resolved values forward as literal text substituted into every later command.
The examples below write `<resolved HARNESS url>` and `<resolved TARGET path>`
to mark where.

Record the stage at the start of each numbered step:

```bash
node -e "import('<resolved HARNESS url>').then(m => m.writeWorkflowState(process.argv[1], { slug: '<slug>', stage: '<stage>' }))" "<resolved TARGET path>"
```

**`TARGET` MUST be passed as an argv value**, never interpolated into the `-e`
JS string: a Windows path's backslashes are consumed as escape sequences with no
error, silently corrupting it.

1. **Intake** — Derive a slug for *this change*, not for the project: a short
   kebab-case name for what is being changed (`single-page-nav`, not
   `wl-portfolio`). `slugify` is exported by `workflow-state.mjs`; call it and
   echo the result rather than composing one by hand:

   ```bash
   node -e "import('<resolved HARNESS url>').then(m => console.log(m.slugify(process.argv[1])))" "<change name>"
   ```

   Confirm the project already exists — `package.json` and `src/` are present.
   If the directory is empty, this is `init-project`, not `feature-dev`; say so
   and stop. Write the state file with stage `intake`.

2. **Context load** — Record stage `context-load`. Read, and state back in one
   short block:

   - `docs/spec.md` — the governing spec. **If there is none, stop.** A quick
     change refines an existing spec; with nothing to refine there is no
     authority to check the result against, and the change would be
     unaccountable. Offer to write one first.
   - `${CLAUDE_PLUGIN_ROOT}/references/design-template.md` — resolve it from the
     same plugin root as the harness script.
   - The files the change will touch. Use Grep and Glob to find them; name them
     explicitly rather than guessing from the description.

3. **Design** — Record stage `design`. Decide, and state, which of two cases
   this is:

   - **Refinement** — the change stays inside what `docs/spec.md` already
     allows. Write a short change spec: intent, acceptance criteria, and a
     `spec:` line pointing at the clause of `docs/spec.md` it refines. Continue
     without stopping.
   - **Amendment** — the change contradicts or extends `docs/spec.md`. Draft the
     amended clauses, then **stop and put them to the author as a batch**: what
     the spec says now, what you propose it say, and the alternatives you passed
     over. Rewrite `docs/spec.md` from the answers, recording what changed and
     why. Only then continue.

   Amendments stop and refinements do not, because an amendment changes the
   constraints the work is judged against, and §10 does not let the agent settle
   those alone. Where the change touches a dimension in the design template that
   `docs/spec.md` never covered, treat it as an amendment — an unstated
   dimension is not an allowance.

   Save the change spec as `docs/changes/<slug>.md`.

4. **Plan** — Record stage `plan`. Write `docs/changes/<slug>-plan.md`: the steps
   in order, each naming the files it produces or modifies and the tests that
   cover it. Keep it to 1-3 steps; more than that is the deep path, which is not
   built.

5. **Implement** — Record stage `implement`. **Test-first, per module:**

   1. Write the failing test.
   2. Run it. Confirm it fails, and fails for the reason you expect.
   3. Write the smallest implementation that passes it.
   4. Run it again. Confirm it passes.

   Tests live in a `__tests__/` directory beside the code they cover —
   `src/services/__tests__/projects.test.ts` for `src/services/projects.ts`.

   **The guiding principle** (Testing Library's, and the Testing Trophy's):
   *the more your tests resemble the way the software is used, the more
   confidence they give you.* Its corollary is the one rule that matters here:
   **never assert on implementation details** — state variables, handler
   internals, class names, markup structure.

   That rules out three patterns worth naming, because they get written by
   reflex and cannot fail when the code is wrong:

   - `renders without crashing` — any behavioural test that renders the
     component already fails when it throws, so this adds nothing.
   - snapshot assertions — they pin markup structure, and legitimate changes
     break them, which trains everyone to re-record rather than read them.
   - asserting a third-party component rendered — that is the library's class
     name and the library's responsibility.

   Test instead what a user would notice: conditional rendering, props-to-output
   transformation, what happens on interaction, degraded behaviour on missing or
   malformed data, and every branch of a service or utility function. Where you
   want protection against a crash on bad input, assert **what should be shown
   instead** rather than that nothing threw.

   Per the Testing Trophy: static analysis is covered by `tsc --noEmit` and
   ESLint; unit tests cover pure functions; integration tests — components with
   their real children — carry the bulk of the value. End-to-end coverage
   belongs to Playwright at the L tier per §6.2 and is deliberately absent here;
   do not substitute a build command for it, since `pnpm build` renders every
   page only when output is fully static and says nothing under CSR, SSR or ISR.

   A component with no logic — pure passthrough to a UI primitive — has no
   behaviour to resemble. Say so rather than inventing a test for it.

   If the project has no test runner, stop and set one up first: `vitest` plus
   `@testing-library/react` for components, and a `test` script in
   `package.json`. Report that you did.

6. **Verify** — Record stage `verify`. Run, from `<resolved TARGET path>`:

   ```bash
   pnpm test
   pnpm exec tsc --noEmit
   ```

   Then check the acceptance criteria in `docs/changes/<slug>.md` one by one and
   report pass/fail for each. On failure, fix and re-run — this loop is
   machine-judged and does not involve the author. Do not proceed until every
   criterion passes.

7. **Handoff** — Record stage `handoff` only after step 6 is green. Report: what
   changed, which files, which tests cover it, and whether `docs/spec.md` was
   amended. A failing check means the work is unfinished, not that a rule was
   broken.
