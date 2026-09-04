---
name: ui-code-inspector
description: Use when adding or reviewing a local development UI-to-source inspector for Vite React projects, where clicking a rendered UI element should open the source file line in the editor. Next.js is explicitly out of scope.
---

# UI Code Inspector

Use this skill to add or review a dev-only UI inspector that lets a developer click a rendered UI element and open the corresponding source file location in their editor.

Executable support is limited to **Vite React**. Next.js is a deliberate non-goal —see "Next.js Is Out of Scope". For Vue, Nuxt, Angular, Svelte, Astro, Remix, generic webpack, or unknown frameworks, detect the framework and explain the likely adapter shape, but stop before modifying the compile chain unless the human explicitly approves a new design.

## Scope

The intended target behavior:

- In local development, holding `Alt` or `Option` enables inspect mode.
- Hovering a source-marked element shows an outline and a compact source label.
- Clicking a source-marked element opens `file:line:column` in the editor.
- Normal clicks work unchanged when inspect mode is not active.
- Production builds do not contain `data-inspector-*` attributes or inspector runtime code.

The implementation should be split into two layers:

- Compile-time metadata injection: JSX elements receive `data-inspector-line`, `data-inspector-column`, and `data-inspector-relative-path`.
- Runtime DOM inspector: framework-neutral browser code finds the nearest `data-inspector-*` element, displays hover UI, and opens the editor.

## Required Repo Inspection

Before proposing or editing anything in the target project:

1. Read `package.json`.
2. Identify the package manager from lock files.
3. Search for `vite.config.*`, `next.config.*`, `webpack.config.*`, `babel.config.*`, `.babelrc*`, `tsconfig.json`, and `jsconfig.json`.
4. Search for app roots: `src/main.*`, `src/App.*`, `app`, `src/app`, `pages`, `src/pages`, `apps/*`, and `packages/*`.
5. Check existing scripts for dev, build, lint, typecheck, and test commands.
6. Check whether similar inspector, devtools, overlay, launch-editor, or custom dev-server code already exists.

Use `rg` or `rg --files` first when available.

## Framework Detection

Classify the project before making changes. Output a structured detection result instead of a single label:

```json
{
  "framework": "react",
  "metaFramework": "vite | next | unknown",
  "bundler": "vite | next-webpack | turbopack | webpack | unknown",
  "transformer": "babel | swc | mixed | unknown",
  "router": "vite-spa | next-app-router | next-pages-router | next-mixed-router | unknown",
  "appRoot": "relative/path",
  "packageManager": "pnpm | npm | yarn | bun | unknown",
  "confidence": "high | medium | low",
  "notes": []
}
```

Detection rules:

- Vite React: `package.json` contains `vite` and `react`, usually with `@vitejs/plugin-react`, and the project has `vite.config.*`.
- Vite React with Babel: Vite config uses `@vitejs/plugin-react`.
- Vite React with SWC: Vite config uses `@vitejs/plugin-react-swc`.
- Next.js: `package.json` contains `next`, and the project has `next.config.*`, `app`, `src/app`, `pages`, or `src/pages`.
- Next.js App Router: `app/` or `src/app/` exists.
- Next.js Pages Router: `pages/` or `src/pages/` exists.
- Next.js mixed router: both App Router and Pages Router are present.
- Monorepo: app code is under `apps/*` or uses workspace packages under `packages/*`.
- Unknown or mixed: detection is ambiguous, multiple app frameworks are present, or the actual app root is unclear.

Next.js is still detected, but only so the skill can stop cleanly and explain why. Detecting `next` is a hard stop, not a branch into an implementation path.

Stop and ask the human if detection is unknown, mixed, or ambiguous.

## Architecture

Prefer mature packages over custom code when they fit the compile-time injection layer:

- `babel-plugin-react-dev-inspector`
- `launch-editor`
- `react-dev-utils/launchEditorEndpoint`
- `vite-plugin-inspect`
- `vite-plugin-vue-inspector` as a reference for Vite plugin shape
- `locator-js` as a reference for interaction design

Use `babel-plugin-react-dev-inspector` for AST injection when the target transformer is Babel. Do not use its bundled inspector component/runtime by default; write or adapt a small local DOM runtime so interaction behavior, hydration safety, event handling, and production tree-shaking are under project control.

Keep the implementation dev-only and production-absent. Prefer explicit guards such as `import.meta.env.DEV`, `process.env.NODE_ENV !== "production"`, dynamic imports, and framework-specific dev-only entry points that bundlers can dead-code eliminate.

## Vite React Path

When the target is Vite React:

1. Inspect the current Vite config style before editing.
2. Detect whether React compilation uses `@vitejs/plugin-react` or `@vitejs/plugin-react-swc`.
3. If it uses `@vitejs/plugin-react`, prefer `babel-plugin-react-dev-inspector` for AST metadata injection.
4. If it uses `@vitejs/plugin-react-swc`, do not apply a Babel plugin as if it will run. Either:
   - use or write a SWC-compatible injector,
   - explicitly ask approval to switch to the Babel React plugin with a performance tradeoff, or
   - stop with a recommendation if neither path is appropriate.
5. If adding a custom path, inject:
   - `data-inspector-line`
   - `data-inspector-column`
   - `data-inspector-relative-path`
6. Inject the runtime inspector from the app entry or through a Vite dev-only mechanism.
7. Add an editor launch endpoint through Vite dev server middleware when URI fallback is insufficient.
8. Preserve React Refresh and existing React plugin options.

Do not inject metadata into `node_modules`.

## Next.js Is Out of Scope

Do not implement a UI code inspector in a Next.js project with this skill. This is a deliberate decision, not a gap waiting to be filled. If the target project is Next.js, stop and report the reasoning below.

### Why

- **Turbopack is the default.** Next.js 16 runs `next dev` and `next build` on Turbopack, which does not execute a webpack loader chain. Any loader-based injection requires forcing the whole repository onto `next dev --webpack` and `next build --webpack`, which slows down every developer for the benefit of one dev tool, and stakes the integration on a bundler path Next.js is moving away from.
- **Injection requires depending on Next.js internals.** There is no public API for adding a transform alongside the built-in SWC step. It requires walking `config.module.rules`, locating the rule that contains `next-swc-loader`, and appending to its loader chain. That structure is not a stability contract, and when it changes the failure surfaces as an unrelated-looking build error such as `SyntaxError: Unexpected token 'export'`.
- **Keeping it out of production takes three separate cuts.** The client runtime chain, the compile-time injection chain, and the editor-launch API route each leak independently. A route file under `app/api/**` ships in production regardless of any handler-level `NODE_ENV` check, and a static import in a Server Component layout still emits a Client Reference even when a runtime guard is false. Guaranteeing a clean build means re-running a clean-build-and-scan after any change to the layout, the API tree, or the webpack config —a discipline that does not survive contact with a real project.
- **App Router limits the payoff anyway.** Server Components do not run browser runtime code, so only DOM rendered by Client Components can support hover and click inspection. A meaningful part of a typical App Router tree is not inspectable even after all of the above.

The cost is ongoing and falls on the whole team; the benefit is a development convenience. That trade does not clear.

### What to recommend instead

Before concluding that anything needs to be built, check what the project already has:

1. The Next.js dev overlay already resolves stack frames to source and can open them in an editor.
2. React DevTools can jump from a selected component to its source.
3. Source maps plus the browser devtools element inspector cover the common "which file is this" question without touching the build.

If the human explicitly wants inspector behavior in Next.js beyond what those provide, treat it as a separate design conversation with its own approval, not as an application of this skill. Do not improvise a webpack or SWC integration inside this skill's workflow.

## Runtime-Disabled vs Absent From the Bundle

These are different claims, and the distinction matters wherever dev-only code is added:

- **Runtime-disabled**: the code ships in the production bundle but a condition prevents it from executing. It still adds bytes, still appears in source maps and chunk output, and still exposes the editor-launch surface if the guard is wrong.
- **Absent from the production bundle**: the code and its identifiers do not exist in the build output at all.

The required verification for this skill is the second one. A passing runtime check is not evidence.

## Runtime Inspector Requirements

The runtime inspector should be plain DOM code:

- Listen for keyboard state and pointer events on `window` in the capture phase so app-level `stopPropagation()` does not disable inspection.
- Use `event.target` and walk up through `parentElement`.
- Find the nearest element with all required `data-inspector-*` attributes.
- Show an outline only while inspect mode is active. Implement the overlay with a portal or detached root using `pointer-events: none`.
- Prevent default and stop propagation only for the inspect click.
- Build a source location from project root, relative path, line, and column.
- Remove event listeners during cleanup if integrated through a component.
- Handle macOS `Option` and browser `Alt` behaviors defensively. Prefer also supporting a configurable fallback shortcut, such as `Meta+Shift` or a toggled inspect mode, if `Alt` conflicts with the app or browser.
- Keep listeners resilient across HMR and React Refresh. Reinstall or preserve listeners after module replacement so inspection still works after edits.

The runtime must not depend on React internals, React Fiber, Vue internals, or framework-specific devtools state.

Do not dynamically add or mutate `data-inspector-*` attributes at runtime. These attributes should come from compile-time injection so React's prop diff and hydration behavior stay predictable.

## Editor Launch

Preferred order:

1. Reuse an existing project editor-launch endpoint if present.
2. Use `launch-editor`.
3. Use `react-dev-utils/launchEditorEndpoint` when appropriate.
4. Fall back to a browser URI such as `vscode://file/{absolutePath}:{line}:{column}`.

Support VS Code-compatible editors where practical: VS Code, Cursor, and Windsurf. If the editor cannot be detected reliably, make it configurable and document the default.

## Verification

Before claiming completion in the target project:

1. Run the relevant available checks, usually lint, typecheck, test, and build.
2. Start or inspect the dev server when feasible.
3. Confirm rendered DOM contains `data-inspector-line`, `data-inspector-column`, and `data-inspector-relative-path`.
4. Confirm hover/click can resolve a source location.
5. Confirm editor launch endpoint or URI is wired.
6. Confirm HMR or React Refresh does not break inspector listeners after a source edit.
7. Confirm production build output does not contain `data-inspector-` or the inspector runtime code. This is stronger than checking that the runtime is disabled.

If browser verification or editor launch verification cannot be performed, state exactly what was verified and what remains manual.

### Production Verification Procedure

Stale build output is the most common source of false results in both directions. Always start from a clean build.

1. Remove or invalidate stale output before scanning. Delete the build output directory — `dist` by default, or whatever `build.outDir` is set to — and clear the Vite cache at `node_modules/.vite`.
2. Run a clean production build with the project's real production command.
3. Scan the entire build output for every one of these markers:
   - `data-inspector-`
   - `installUiCodeInspector`
   - `UiCodeInspector`
   - `ui-code-inspector`
4. Require zero matches. Any match means the dev-only code is still reachable from the production entry.

Windows-compatible scan:

```powershell
Remove-Item -Recurse -Force dist, node_modules\.vite -ErrorAction SilentlyContinue
npm run build
Get-ChildItem -Recurse -File dist |
  Select-String -Pattern 'data-inspector-','installUiCodeInspector','UiCodeInspector','ui-code-inspector'
```

Cross-platform equivalent:

```bash
rm -rf dist node_modules/.vite
npm run build
rg -n 'data-inspector-|installUiCodeInspector|UiCodeInspector|ui-code-inspector' dist
```

Report the exact command and its output. Do not claim a clean build from a scan that ran against pre-existing chunks.

### Verification Checklist

Work through every item and report each one as passed, failed, or manual:

- [ ] Development server starts.
- [ ] No transform or plugin error during dev compilation.
- [ ] Rendered DOM contains all three metadata attributes: `data-inspector-line`, `data-inspector-column`, `data-inspector-relative-path`.
- [ ] `Alt` / `Option` hover activates inspect mode and shows the overlay.
- [ ] Click resolves file, line, and column.
- [ ] Editor launch works and is dev-only.
- [ ] HMR does not duplicate listeners after a source edit.
- [ ] Production output contains none of the inspector markers.

## Failure Modes and Troubleshooting

**Stale build output causing false production scan results.** A scan that finds inspector markers may be reading chunks from an earlier build, and a scan that finds nothing may be reading a directory that was never rebuilt. Delete the output directory and `node_modules/.vite`, rebuild, then scan.

**Metadata attributes present but no hover or click behavior.** The injection layer works and the runtime layer does not. Confirm the runtime module is actually imported on the dev client entry path and that listeners install on `window` in the capture phase.

**Runtime works but attributes are missing on some elements.** Injection is not covering that file set. Check the plugin's include/exclude patterns, confirm the file is not in `node_modules`, and confirm the transform runs before the React plugin consumes the JSX.

**Inspector stops responding after an edit.** React Refresh replaced the module without reinstalling listeners. Make listener installation idempotent and re-register on module replacement rather than only on first load.

**Duplicate listeners after HMR.** The opposite failure: listeners are added on every module replacement without cleanup. Track the installed handlers and remove them before reinstalling.

**Alt or Option conflicts with the browser or the app.** On some platforms `Alt` opens browser menus or the app already binds it. Provide the configurable fallback shortcut described in the runtime requirements.

## Stop Conditions

Stop before editing and ask the human when:

- The project is not Vite React.
- The project is Next.js. Report the reasoning in "Next.js Is Out of Scope" instead of implementing anything.
- Framework detection is ambiguous.
- The app root cannot be identified.
- The project uses a compile chain that would require replacing existing Babel, SWC, or Vite behavior.
- The project uses Vite React SWC and no approved injection strategy exists.
- Editor launch cannot be made dev-only.
- The only plausible implementation would affect or remain inside production output.
- The request requires Next.js, Vue, Nuxt, Angular, Svelte, Astro, Remix, or generic webpack support.
