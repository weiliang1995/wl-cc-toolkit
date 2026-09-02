# CLAUDE.md

Guidance for Claude Code in this repository.

## What this repo is

weiliang's personal development toolbox, containing:

- **packages/** — reusable plugins and small tool packages; Claude Code skills ship inside them
- **scripts/** — automation scripts
- **workflows/** — workflow definitions

## Conventions

- Skills are Markdown, at `packages/<plugin>/skills/<skill-name>/SKILL.md`; the directory name is the invocation name
- Every plugin needs `.claude-plugin/plugin.json` and an entry in `.claude-plugin/marketplace.json`
- Prefer PowerShell for scripts (Windows environment); use bash for cross-platform ones
- Documentation goes in `docs/`; update `CATALOG.md` to keep the index in sync

## Development principles

- Keep each skill/plugin to a single responsibility
- Anything new must be added to CATALOG.md
