# Webex API Knowledge Skill

Give Codex, GitHub Copilot in VS Code, or Claude Code grounded Webex Public API knowledge while building integrations. The skill runs a local Node.js helper that signs the developer in to Webex as a public OAuth client using PKCE (callback on `http://localhost:17177/callback`), stores the resulting token pair in macOS Keychain or Windows DPAPI-encrypted local storage, and queries the Webex Developer AI Assistant knowledge service. No client secret is used or shipped.

The current fixed service origin is the integration deployment. This package is for pilot testing until the production service is approved.

## Requirements

- Node.js 20 or newer
- macOS or Windows for secure token storage
- Network access to `u2c.wbx2.com`, the discovered Webex knowledge service (`*.wbx2.com`), and `idbroker*.webex.com`
- Local port 17177 free during login

## Install

Install directly from the latest release package in this repository; no download is needed. To pin a version, replace `latest` with a version from [release/](release/), for example `0.2.0-beta.0`.

**User-level installation**
Makes the skill available across projects:

```bash
npx --yes \
  --package https://raw.githubusercontent.com/webex/webex-skills/main/skills/webex-api-knowledge/release/webex-api-knowledge-latest.tgz \
  webex-api-knowledge install \
  --client all \
  --scope user
```

**Project-level installation**
Run from the target project:

```bash
cd /path/to/project

npx --yes \
  --package https://raw.githubusercontent.com/webex/webex-skills/main/skills/webex-api-knowledge/release/webex-api-knowledge-latest.tgz \
  webex-api-knowledge install \
  --client all \
  --scope project
```

_Use `--force` when updating an existing installation._

`--client` accepts `codex`, `copilot`, `claude`, or `all`.

After installation, restart the agent or start a new session. Invoke `$webex-api-knowledge` in Codex, `/webex-api-knowledge` in Claude Code, or ask Copilot to use the `webex-api-knowledge` skill. See [installation details](skill/webex-api-knowledge/references/installation.md).

## Build and verify

From this skill directory:

```sh
npm test
npm run pack:check
```

The package contains only the installer, skill instructions, references, and helper; no client secret or user credentials.

To release, bump `version` in [package.json](package.json) and run **Actions > Package skill release** with `webex-api-knowledge`. The workflow builds the package into [release/](release/) and commits it. Released versions are immutable; an existing version is never overwritten.

The service origin is defined once in [the helper](skill/webex-api-knowledge/scripts/webex-knowledge.mjs). For local service testing, edit that constant in a development checkout; do not distribute the edited package. Switch the constant to the approved production service before an App Hub public release.

## Migrating from the pilot skill

This package installs as `webex-api-knowledge`; it does not overwrite the older `webex-api-development` skill. Pilot users should inspect and remove any old `webex-api-development` directory in their Codex, Copilot, or Claude skill locations after verifying the new skill works. The installer does not delete the older installation or its saved Webex credentials.
