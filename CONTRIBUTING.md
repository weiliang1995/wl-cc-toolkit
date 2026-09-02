# CONTRIBUTING.md

## Adding a skill

Skills ship inside a plugin, so a new skill either joins an existing plugin or gets a
new one (see below).

1. Create `packages/<plugin-name>/skills/<skill-name>/SKILL.md`
2. Put frontmatter at the top of the file:

```yaml
---
name: skill-name
description: One line covering what it does and when it triggers
---
```

3. Write the skill's steps or instructions in the body
4. Add a row to the Skills table in [CATALOG.md](CATALOG.md)

## Adding a package / plugin

1. Create the plugin directory at `packages/<package-name>/`
2. Add `.claude-plugin/plugin.json` with `name`, `version` and `description`
3. Include a `README.md` covering what it is and how to use it
4. Register it in the `plugins` array of [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json)
5. Add a row to the Packages table in [CATALOG.md](CATALOG.md)

## Adding a script

1. Put the script in `scripts/`
2. Use a header comment covering its purpose, arguments and an example
3. Add a row to the Scripts table in [CATALOG.md](CATALOG.md)

## Commit conventions

```
feat: add the xxx skill
fix: fix the xxx problem
docs: update CATALOG.md
```
