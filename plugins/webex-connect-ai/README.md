# Webex Connect AI plugin source

This directory defines a plugin assembled from independently maintained skills
in the repository's `/skills` directory. `plugin.json` lists the skill package
names included in this bundle. Keep skill instructions, scripts, references,
tests, and releases with their owning skill package.

The checked-in plugin source contains manifests, plugin-specific commands,
rules, and branding. It intentionally contains no skill implementations. The
build step resolves the skill names in `plugin.json`, copies their distributable
skill directories into `plugin-packages/webex-connect-ai/skills/`, and produces
a self-contained plugin folder for supported hosts. The generated package is
committed so repository marketplace installs work from GitHub clones. Its
`plugin-lock.json` records the exact versions of the linked skill packages.

## Build and install locally

From the repository root:

```sh
npm run plugin:build
codex plugin marketplace add .
codex plugin add webex-connect-ai@webex-skills
```

The marketplace points to the generated plugin under `plugin-packages/`. After
changing a linked skill or plugin component, bump the plugin version and rebuild
the package before committing. CI checks that the committed bundle matches the
source.

## Included skills

The bundle currently links 19 standalone skill packages. To change bundle
membership, edit the `skills` list in `plugin.json`, then run
`npm run catalog:generate`, `npm run plugin:build`, and `npm run validate`.

## Platform components

- Codex manifest: `.codex-plugin/plugin.json`
- Claude Code manifest: `.claude-plugin/plugin.json`
- Cursor manifest: `.cursor-plugin/plugin.json`
- Shared plugin assets: `assets/`
- Claude Code and Cursor commands: `commands/`
- Cursor rule: `rules/`

The generated plugin folder includes the linked skill implementations required
by those host manifests. The source skill packages remain separately
installable and versioned.
