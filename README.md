# Webex Skills and Plugins

Agent skills and plugins for building with Webex, for Codex, GitHub Copilot, Claude Code, and Cursor.

## Packages

| Package | Description | Details |
| --- | --- | --- |
| [webex-api-knowledge](skills/webex-api-knowledge/) | Grounded Webex Public API knowledge for building integrations | [releases](skills/webex-api-knowledge/release/) |
| [webex-connect-ai](plugins/webex-connect-ai/) | Codex, Claude Code, and Cursor plugin with 19 Webex Connect skills | [plugin files](plugins/webex-connect-ai/) |

See each skill's README for installation and usage.

## Repository layout

```
skills/<name>/
  README.md                 skill documentation
  package.json              package name, version, installer bin, shipped files
  skill/<name>/SKILL.md     the skill as installed into the agent (plus references/, scripts/, agents/)
  scripts/                  skill-specific scripts (e.g. installer)
  tests/                    skill tests (`npm test`)
  release/                  CHANGELOG.md and released packages, one .tgz per version
scripts/                    shared repo tooling (validate, detect changes, changelog, package)
.agents/skills/             project-level agent skills for working on this repo
.agents/plugins/            local Codex plugin marketplace
.claude-plugin/             local Claude Code plugin marketplace
.cursor-plugin/             local Cursor plugin marketplace
plugins/webex-connect-ai/   installable Webex Connect AI plugin
.github/workflows/          CI verification and release packaging
```

Each skill is an npm workspace, so its `package.json` owns its version and packaging.

The `webex-connect-ai` plugin is a separate installable package. Its 19 skills,
commands, rules, manifests, and branding live under `plugins/webex-connect-ai/`.
Codex discovers the local plugin through `.agents/plugins/marketplace.json`.

## Development

Requires Node.js 20 or newer.

```sh
npm run validate                                  # validate skills and the plugin package
npm test                                          # test all skills
npm test --workspace skills/<name>                # test one skill
node scripts/package-skill.mjs <name> --dry-run   # preview a package
```

Plugin changes are checked by the same `npm run validate` command. From this
repository, install the local Codex plugin with:

```sh
codex plugin marketplace add .
codex plugin add webex-connect-ai@webex-connect-ai
```

## CI

**Verify skills** runs on every push and pull request. It detects changed skills and validates, tests, and dry-run packs only those. Plugin changes also run the plugin package validator. Changes to shared skill tooling verify all skills. Use the `verified` check for branch protection.

## Releasing a skill

Versions are `X.Y.Z` (stable) or `X.Y.Z-beta.N` (pre-release). Stable releases require a changelog entry; pre-releases do not.

**Stable release**

1. Locally, ask your agent to use the project skill **skill-changelog** (e.g. "use skill-changelog to prepare the webex-api-knowledge 1.0.0 changelog"). It collects commits since the last stable tag, drafts the entry for your review, bumps `version` if needed, pushes a `changelog/<name>-<version>` branch, and opens a PR.
2. Review, edit if needed, and merge the PR.
3. Run **Actions > Package skill release** and pick the skill. The workflow fails if the stable version has no entry in `skills/<name>/release/CHANGELOG.md`.

**Pre-release**: bump `version` to `X.Y.Z-beta.N`, merge, and run **Package skill release**.

The workflow validates, tests, packs `skills/<name>/release/<name>-<version>.tgz` and `<name>-latest.tgz`, and commits them to the default branch. Stable releases are also tagged `<name>@<version>`; these tags mark where the next changelog starts. Existing versions are never overwritten. The changelog is not shipped inside the package.

## Adding a skill

1. Create `skills/<name>/` following the layout above, including `release/CHANGELOG.md`; the folder name must equal the `name` in `SKILL.md`.
2. Add `<name>` to the `skill` options in [.github/workflows/publish.yml](.github/workflows/publish.yml).
3. Add a row to the table above and run `npm run validate`.
