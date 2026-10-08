# Webex Skills

Agent skills for building with Webex, for Codex, GitHub Copilot, and Claude Code.

## Skills

| Skill | Description | Releases |
| --- | --- | --- |
| [webex-api-knowledge](skills/webex-api-knowledge/) | Grounded Webex Public API knowledge for building integrations | [release/](skills/webex-api-knowledge/release/) |

See each skill's README for installation and usage.

## Repository layout

```
skills/<name>/
  README.md                 skill documentation
  package.json              package name, version, installer bin, shipped files
  skill/<name>/SKILL.md     the skill as installed into the agent (plus references/, scripts/, agents/)
  scripts/                  skill-specific scripts (e.g. installer)
  tests/                    skill tests (`npm test`)
  release/                  released packages, one .tgz per version
scripts/                    shared repo tooling (validate, detect changes, package)
.github/workflows/          CI verification and release packaging
```

Each skill is an npm workspace, so its `package.json` owns its version and packaging.

## Development

Requires Node.js 20 or newer.

```sh
npm run validate                                  # validate all skills
npm test                                          # test all skills
npm test --workspace skills/<name>                # test one skill
node scripts/package-skill.mjs <name> --dry-run   # preview a package
```

## CI

**Verify skills** runs on every push and pull request. It detects which skills changed and validates, tests, and dry-run packs only those. Changes to shared `scripts/`, `.github/`, or the root `package.json` verify every skill. Use the `verified` check for branch protection.

## Releasing a skill

1. Bump `version` in `skills/<name>/package.json` and merge to the default branch.
2. Run **Actions > Package skill release**, pick the skill, and optionally choose dry run.
3. The workflow validates, tests, packs `skills/<name>/release/<package>-<version>.tgz`, and commits it to the default branch. Existing versions are never overwritten.

## Adding a skill

1. Create `skills/<name>/` following the layout above; the folder name must equal the `name` in `SKILL.md`.
2. Add `<name>` to the `skill` options in [.github/workflows/publish.yml](.github/workflows/publish.yml).
3. Add a row to the table above and run `npm run validate`.
