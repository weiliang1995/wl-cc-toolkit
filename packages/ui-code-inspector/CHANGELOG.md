# Changelog

## 2.0.0 - 2026-09-05

### Changed

- **Breaking:** narrowed the `ui-code-inspector` skill to Vite React only. Next.js is no longer an executable target.
- Replaced the Next.js implementation guidance with a `Next.js Is Out of Scope` section explaining the four reasons the integration was rejected: Turbopack is the Next.js 16 default and does not run a webpack loader chain, injection would depend on the unstable internal `next-swc-loader` rule shape, keeping inspector code out of production requires three separately maintained cuts, and App Router Server Components cannot host the browser runtime.
- Next.js is still detected during framework classification, but detection is now a hard stop that reports the reasoning instead of branching into an implementation path.
- Retargeted the production verification procedure from `.next` to the Vite output directory, including clearing `node_modules/.vite` before a clean build, with both PowerShell and `rg` variants.
- Replaced the Next.js-specific troubleshooting entries with six Vite-relevant failure modes: stale build output, metadata present without a runtime, runtime present without metadata, React Refresh dropping listeners, HMR duplicating listeners, and `Alt`/`Option` key conflicts.
- Promoted the runtime-disabled versus absent-from-the-bundle distinction to its own section, since it applies to any dev-only code.
- Added an eight-item verification checklist covering dev server start, metadata attributes, hover, click resolution, dev-only editor launch, HMR listener behavior, and a clean production scan.
- Updated the skill description, both plugin manifests, the marketplace entry, and `CATALOG.md` to drop the Next.js claim, and removed the `nextjs` keyword from the Codex manifest.
- Updated the design spec and implementation plan under `docs/superpowers/` to match the Vite-only scope.
