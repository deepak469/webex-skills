# Contributing

This repository hosts independently packaged agent skills and installable
plugin bundles assembled from those skills.

## Add a skill

1. Create `skills/<skill-name>/` as an independent npm workspace. Follow the
   existing package pattern: `README.md`, `package.json`, `skill/<skill-name>/SKILL.md`,
   installer and tests, and `release/CHANGELOG.md`.
2. Keep scripts, references, templates, and assets needed by the skill under
   `skill/<skill-name>/`. The package folder name and skill frontmatter name
   must match.
3. Add the skill to `.github/workflows/publish.yml` so it can be independently
   released. Run `npm run validate`, `npm test`, and
   `npm run pack:check --workspace skills/<skill-name>`.

## Add or update a plugin

1. Create `plugins/<plugin-name>/` with a `plugin.json` source recipe. Its
   `skills` array links to package names from `/skills`; do not add skill source
   folders here.
2. Add manifests only for supported agent surfaces. Repository marketplace
   catalogs are `.agents/plugins/marketplace.json` (Codex),
   `.claude-plugin/marketplace.json` (Claude Code),
   `.cursor-plugin/marketplace.json` (Cursor), and
   `.windsurf-plugin/marketplace.json` (Windsurf). Their entries point at the
   generated `./dist/plugins/<plugin-name>` package.
3. Keep versions synchronized in the plugin recipe, surface manifests, and
   marketplace entries. Marketplace catalogs share the repository identity
   `webex-skills`.
4. Build output is generated and ignored by Git. `npm run plugin:build`
   resolves the recipe's skill names and assembles a self-contained plugin in
   `dist/plugins/` for installation or release.
5. Regenerate indexes and run all checks:

   ```sh
   npm run catalog:generate
   npm run validate
   npm run plugin:build
   node --test tests/plugins.test.mjs
   npm test
   ```

Do not edit `PLUGINS.md` or `catalog.json` by hand. The generator reads plugin
recipes and the linked skill package metadata.

## Change an existing plugin

Keep implementation resources with the skill package that owns them. Update a
plugin's skill links when its composition changes. When published behavior
changes, update the plugin version consistently across its recipe, supported
surface manifests, and marketplace entries. Update plugin-specific docs or
commands, regenerate the catalog, and run the checks above.

## Existing standalone skills

Each `skills/<name>/` directory is independently versioned and releaseable.
Plugin-only changes should stay under `plugins/` and shared plugin tooling;
avoid changing a standalone skill's source or release files unless it is part
of the requested work.
