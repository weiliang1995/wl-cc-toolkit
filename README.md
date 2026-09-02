# cc-toolkit

Personal toolbox holding Claude Code skills, workflows and small plugins.

## Layout

```
cc-toolkit/
├── .claude/            # Claude Code config (settings.json, hooks, commands)
├── .claude-plugin/     # Plugin marketplace definition (marketplace.json)
├── .githooks/          # Git hook scripts
├── docs/               # Documentation
├── packages/           # Reusable packages / plugins
└── scripts/            # Utility scripts
```

Skills ship inside their plugin, at `packages/<plugin>/skills/<skill-name>/SKILL.md`.

## Commands

| Command | Purpose |
|---------|---------|
| `/plugin-dev <name> [local\|remote\|status]` | Local dev mode: symlink a plugin into the cache and debug it without installing |
| `/publish <name> <patch\|minor\|major>` | Ship a release: bump the version, generate the changelog, tag and push |
| `/update-catalog [--prune]` | Scan the directories and incrementally update CATALOG.md |

## Getting started

See [CATALOG.md](CATALOG.md) for every available skill and tool.

For how to contribute, see [CONTRIBUTING.md](CONTRIBUTING.md).
