# Repository guidance

This repository contains independently versioned agent skills and plugin
recipes. Read `README.md` and `CONTRIBUTING.md` before changing shared
structure or marketplace metadata.

## Skill and plugin structure

- Keep reusable skills under `skills/<skill-name>/` as independent packages.
  Match `skill/<skill-name>/SKILL.md` frontmatter `name` to the package folder.
- Keep skill-specific scripts, references, assets, tests, documentation, and
  release files with that skill package.
- Keep plugin selection and host manifests under `plugins/<plugin-name>/`.
  Link skills by package name in `plugin.json`; do not copy skill source into
  the plugin recipe.
- Use `npm run plugin:build` to assemble a self-contained installable plugin
  under ignored `dist/plugins/<plugin-name>/`.
- Keep plugin versions synchronized across `plugin.json`, supported surface
  manifests, and marketplace entries. Marketplace identities use
  `webex-skills`.
- After changing plugin metadata or skill descriptions, run
  `npm run catalog:generate`, then `npm run validate`.

## Validation and safety

- Run `npm test` and `npm run validate` for skill packages and metadata.
- Run `npm run plugin:build` and
  `node --test tests/plugins.test.mjs` to verify plugin assembly and links.
- Keep credentials and local `.env` files out of packages. A blank
  `.env.example` is allowed where a skill needs one.
- Do not change the `webex-api-knowledge` workspace, release files, or workflow
  unless the task explicitly includes that skill.
