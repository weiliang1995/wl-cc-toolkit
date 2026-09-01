---
name: ui-code-inspector
description: Use when adding or reviewing a local development UI-to-source inspector for Vite React or Next.js projects, where clicking a rendered UI element should open the source file line in the editor.
---

# UI Code Inspector

Use this skill to add or review a dev-only UI inspector that lets a developer click a rendered UI element and open the corresponding source file location in their editor.

Phase one executable support is limited to Vite React and Next.js. For Vue, Nuxt, Angular, Svelte, Astro, Remix, generic webpack, or unknown frameworks, detect the framework and explain the likely adapter shape, but stop before modifying the compile chain unless the human explicitly approves a new design.

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

Stop and ask the human if detection is unknown, mixed, or ambiguous. For Next.js App Router, tell the human during detection that Server Components have no client runtime and the inspector can only attach runtime interaction to Client Components and DOM that reaches the browser.

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

## Next.js Path

When the target is Next.js:

1. Identify App Router, Pages Router, or both.
2. Inspect existing `next.config.*`, including custom webpack config, Turbopack settings, `swcPlugins`, and TypeScript path aliases.
3. Tell the human whether the project uses App Router, Pages Router, or both. In App Router, explicitly state that Server Components do not host client-side runtime behavior; only Client Components and browser-rendered DOM can be inspected.
4. Remember that modern Next.js, especially Next.js 13+, defaults to SWC. `babel-plugin-react-dev-inspector` will not run unless the project opts into Babel.
5. If the project already uses Babel, extend its React JSX transform path carefully and prefer `babel-plugin-react-dev-inspector` for injection.
6. If the project is SWC-only, do not silently add `.babelrc`. Present the choices:
   - add `.babelrc` and accept that Next.js will switch from SWC to Babel with a performance cost,
   - use or write a SWC plugin if the project already supports that path,
   - add a dev-only custom webpack loader for AST injection,
   - stop with a recommendation if the tradeoff is not acceptable.
7. Add the runtime inspector through:
   - a client component imported by the root `app/layout.*` for App Router, or
   - a client-only wrapper in `pages/_app.*` for Pages Router.
8. For App Router, use a `"use client"` component plus dynamic import with `ssr: false` when appropriate, and install listeners inside `useEffect`.
9. Add an API route or dev-only helper endpoint for editor launch only when required.
10. Preserve SSR and hydration behavior. The runtime must render nothing server-side or be dynamically loaded on the client.

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

## Stop Conditions

Stop before editing and ask the human when:

- The project is not Vite React or Next.js.
- Framework detection is ambiguous.
- The app root cannot be identified.
- The project uses a compile chain that would require replacing existing Babel, SWC, Vite, or Next behavior.
- The project uses Vite React SWC or Next.js SWC-only and no approved injection strategy exists.
- Editor launch cannot be made dev-only.
- The only plausible implementation would affect or remain inside production output.
- The request requires Vue, Nuxt, Angular, Svelte, Astro, Remix, or generic webpack support in phase one.
