# Repository guidance

This repository contains independently versioned agent skills and plugin
bundles. Read `README.md` and `CONTRIBUTING.md` before changing shared
structure or marketplace metadata.

## Plugin structure

- Keep each installable plugin self-contained under `plugins/<plugin-name>/`.
- Put skills under `plugins/<plugin-name>/skills/<skill-name>/SKILL.md` with
  frontmatter `name` matching the directory and a useful `description`.
- Add a manifest only for each supported agent surface. Add the corresponding
  plugin entry to that surface's repository marketplace catalog.
- Keep plugin versions synchronized across every surface manifest and
  marketplace entry. Repository marketplace identities use `webex-skills`.
- After changing plugin metadata or skill descriptions, run
  `npm run catalog:generate`, then `npm run validate`.

## Validation and safety

- Run `npm test` for skill package tests and `npm run validate` for skill and
  plugin metadata checks. Run `node --test tests/plugins.test.mjs` for the
  generic plugin discovery and version-sync checks.
- Keep credentials and local `.env` files out of plugin packages. A blank
  `.env.example` is allowed where a skill needs one.
- Do not change the `webex-api-knowledge` workspace, release files, or workflow
  unless the task explicitly includes that skill.
