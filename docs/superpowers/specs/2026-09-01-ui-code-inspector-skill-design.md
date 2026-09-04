# UI Code Inspector Skill Design

## Goal

Create a Claude Code skill named `ui-code-inspector` that guides Claude through adding a local-development UI-to-source inspector to frontend projects.

Vite React is the only executable path. Next.js is a deliberate non-goal — see "Next.js Is Out of Scope". Other JSX-like frameworks can be detected, but the skill must not automatically modify them until a later version defines a verified adapter.

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

## Next.js Is Out of Scope

Next.js is detected but never implemented against. Detection exists only so the skill can stop cleanly and explain why.

Reasons:

- **Turbopack is the default.** Next.js 16 runs `next dev` and `next build` on Turbopack, which does not execute a webpack loader chain. Loader-based injection would require forcing the whole repository onto `next dev --webpack` and `next build --webpack`, slowing every developer for one dev tool and betting on a bundler path Next.js is moving away from.
- **Injection depends on Next.js internals.** There is no public API for adding a transform alongside the built-in SWC step; it requires walking `config.module.rules` to find and extend the `next-swc-loader` rule. That is not a stability contract, and breakage surfaces as an unrelated-looking build error.
- **Production exclusion takes three separate cuts.** The client runtime chain, the compile-time injection chain, and the editor-launch API route each leak independently, and guaranteeing a clean build requires re-verifying after any change to the layout, the API tree, or the webpack config.
- **App Router limits the payoff.** Server Components do not run browser runtime code, so a meaningful part of a typical App Router tree is not inspectable regardless.

Recommend the existing Next.js dev overlay, React DevTools, and source maps instead. Anything beyond that is a separate design conversation with its own approval, not an application of this skill.

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
- Do not overwrite existing Babel or Vite config style; extend the local pattern.
- Do not dynamically mutate `data-inspector-*` attributes at runtime because it can interfere with React prop diff and hydration expectations.
- Do not claim support for Next.js, Angular, Vue, Nuxt, or unknown frameworks.
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
