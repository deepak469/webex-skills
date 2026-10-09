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
  release/                  CHANGELOG.md and released packages, one .tgz per version
scripts/                    shared repo tooling (validate, detect changes, changelog, package)
.agents/skills/             project-level agent skills for working on this repo (e.g. skill-changelog)
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

Versions are `X.Y.Z` (stable) or `X.Y.Z-beta.N` (pre-release). Stable releases require a changelog entry; pre-releases do not.

**Stable release**

1. Locally, ask your agent to use the project skill **skill-changelog** (e.g. "use skill-changelog to prepare the webex-api-knowledge 1.0.0 changelog"). It collects commits since the last stable tag, drafts the entry for your review, bumps `version` if needed, pushes a `changelog/<name>-<version>` branch, and opens a PR.
2. Review, edit if needed, and merge the PR.
3. Run **Actions > Package skill release** and pick the skill. The workflow fails if the stable version has no entry in `skills/<name>/release/CHANGELOG.md`.

**Pre-release**: bump `version` to `X.Y.Z-beta.N`, merge, and run **Package skill release**.

The workflow validates, tests, packs `skills/<name>/release/<package>-<version>.tgz` and `<package>-latest.tgz`, and commits them to the default branch. Stable releases are also tagged `<name>@<version>`; these tags mark where the next changelog starts. Existing versions are never overwritten. The changelog is not shipped inside the package.

## Adding a skill

1. Create `skills/<name>/` following the layout above, including `release/CHANGELOG.md`; the folder name must equal the `name` in `SKILL.md`.
2. Add `<name>` to the `skill` options in [.github/workflows/publish.yml](.github/workflows/publish.yml).
3. Add a row to the table above and run `npm run validate`.
