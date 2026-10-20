# Contributing

This repository hosts multiple Webex agent skills and installable plugin
bundles. Each plugin owns its skills, assets, scripts, and any platform-specific
manifests under `plugins/<plugin-name>/`.

## Add a plugin

1. Create `plugins/<plugin-name>/` and put each skill under
   `skills/<skill-name>/SKILL.md`. Match the skill's frontmatter `name` to its
   directory and provide a concise, trigger-focused `description`.
2. Add manifests for the agent surfaces the plugin supports. The matching
   repository marketplace catalogs are `.agents/plugins/marketplace.json`
   (Codex), `.claude-plugin/marketplace.json` (Claude Code),
   `.cursor-plugin/marketplace.json` (Cursor), and
   `.windsurf-plugin/marketplace.json` (Windsurf).
3. Keep the plugin version equal in each surface manifest and marketplace
   entry. Marketplace catalogs share the repository identity `webex-skills`.
4. Regenerate the human and machine-readable indexes and run checks:

   ```sh
   npm run catalog:generate
   npm run validate
   node --test tests/plugins.test.mjs
   npm test
   ```

The catalog generator discovers plugins and skills from their manifests and
`SKILL.md` frontmatter. Do not edit `PLUGINS.md` or `catalog.json` by hand.

## Change an existing plugin

Keep implementation resources with their owning skill. When a change affects a
plugin's published behavior, update its version consistently across all
manifests and marketplace entries. Update any plugin-specific README or
commands that describe the changed behavior, regenerate the catalog, and run
the checks above.

## Existing standalone skills

The `skills/<name>/` npm workspaces are independently packaged skills with
their own tests and release workflows. Plugin-only changes should stay under
`plugins/` and the shared plugin tooling; avoid changing a standalone skill's
source or release files unless that skill is part of the requested work.
