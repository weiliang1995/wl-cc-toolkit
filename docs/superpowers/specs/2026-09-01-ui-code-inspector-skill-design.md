# UI Code Inspector Skill Design

## Goal

Create a Claude Code skill named `ui-code-inspector` that guides Claude through adding a local-development UI-to-source inspector to frontend projects.

The first phase supports Vite React and Next.js as executable paths. Other JSX-like frameworks can be detected, but the skill must not automatically modify them until a later version defines a verified adapter.

## User Experience

The target project should gain a dev-only inspect mode:

- Hold `Alt` or `Option` to enable hover inspection.
- Hovered elements with source metadata show an outline and source label.
- Clicking a marked element opens the editor at `file:line:column`.
- Normal app clicks must keep working when the modifier key is not held.
- Production builds must not contain `data-inspector-*` attributes or inspector runtime code.

## Architecture

The skill describes a two-layer architecture:

1. Compile-time source metadata injection.
   JSX elements receive `data-inspector-line`, `data-inspector-column`, and `data-inspector-relative-path`.

2. Runtime DOM inspector.
   A framework-neutral client script listens for hover and click events, walks from `event.target` through `parentElement`, finds the nearest `data-inspector-*` node, and opens the source location through an editor launcher.

The runtime layer must not depend on React. React, Next.js, Vite, Babel, SWC, or webpack are only adapter concerns.

## Supported Targets

### Vite React

Claude should detect Vite React through:

- `package.json` dependencies or devDependencies containing `vite`, `react`, and usually `@vitejs/plugin-react`.
- `vite.config.*`.

Recommended strategy:

- Detect whether the project uses `@vitejs/plugin-react` or `@vitejs/plugin-react-swc`.
- With `@vitejs/plugin-react`, prefer `babel-plugin-react-dev-inspector` for AST injection.
- With `@vitejs/plugin-react-swc`, use a SWC-compatible injector, explicitly ask before switching to Babel, or stop with a recommendation.
- Add a dev-only client runtime through the Vite entry path or plugin HTML transform.
- Add or reuse an editor-launch endpoint when browser URI opening is not enough.

### Next.js

Claude should detect Next.js through:

- `package.json` containing `next`.
- `next.config.*`.
- App Router files under `app/` or `src/app/`, or Pages Router files under `pages/` or `src/pages/`.

Recommended strategy:

- Prefer a dev-only integration using existing React inspector libraries when compatible.
- Check whether the project uses App Router, Pages Router, custom `swcPlugins`, Babel config, SWC-only compilation, Turbopack, or custom Next config before choosing an injection path.
- For Next.js 13+, assume SWC unless evidence shows Babel is active. Adding `.babelrc` makes Next switch to Babel and has a performance cost that needs approval.
- In App Router projects, disclose that Server Components do not host client-side inspector runtime behavior; the runtime can only operate on Client Components and browser-rendered DOM.
- Add the runtime through a client-only wrapper in the root app layout or custom app file.
- Add an API route or dev helper endpoint for editor launch only when needed.

## Detection Rules

The skill must require Claude to inspect project files before editing and output a structured detection result:

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

Inspection inputs:

- Read `package.json`.
- Inspect lock files to infer package manager.
- Search for `vite.config.*`, `next.config.*`, `webpack.config.*`, `babel.config.*`, `.babelrc*`, `tsconfig.json`, `jsconfig.json`, `src/app`, `app`, `pages`, and `src/pages`.
- Identify monorepo layout when app code is under `apps/*` or packages are under `packages/*`.

If the stack is unknown or ambiguous, Claude must ask the user before changing files.

## Editor Launch

Preferred launch order:

1. Existing project editor-launch endpoint, if present.
2. `launch-editor` package.
3. `react-dev-utils/launchEditorEndpoint` when already available or appropriate.
4. Browser URI fallback such as `vscode://file/{absolutePath}:{line}:{column}`.

The skill should ask Claude to support VS Code-compatible editors where practical: VS Code, Cursor, and Windsurf. The exact command or URI must be verified on the local machine or documented as a configurable option.

## Safety Rules

- Only enable in development.
- Ensure production output does not include inspector attributes or runtime code; rely on dev-only entry points and dead-code elimination, not only runtime no-ops.
- Do not inject inspector attributes into `node_modules`.
- Do not overwrite existing Babel, Vite, or Next config style; extend the local pattern.
- Do not dynamically mutate `data-inspector-*` attributes at runtime because it can interfere with React prop diff and hydration expectations.
- Do not claim support for Angular, Vue, Nuxt, or unknown frameworks in phase one.
- Do not continue after a failed framework detection.

## Verification

Claude must verify the integration before completion:

- Run the relevant typecheck, lint, or build commands available in the target project.
- Start or inspect the dev server when feasible.
- Confirm inspector attributes are present in rendered DOM.
- Confirm hover/click behavior can identify a source location.
- Confirm editor launch route or URI is wired.
- Confirm HMR or React Refresh does not break inspector listeners.
- Confirm production build output does not contain `data-inspector-` or inspector runtime code.

If runtime browser verification is not feasible, Claude must state exactly what was verified and what remains manual.

## Deliverables

This repository should add:

- `skills/ui-code-inspector.md`
- `CATALOG.md` entry only during formal publication, not during draft skill development
- design and implementation documentation under `docs/superpowers/`
