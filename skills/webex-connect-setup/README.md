# webex connect setup

Standalone Webex Connect agent skill: webex connect setup.

## Install

Install from this skill's latest GitHub release package; it is not published to npm. To pin a version, replace `latest` with the desired version.

```sh
npx --yes \
  --package https://raw.githubusercontent.com/webex/webex-skills/main/skills/webex-connect-setup/release/webex-connect-setup-latest.tgz \
  webex-connect-setup install --client codex --scope user
```

Use `--scope project` to install into the current project, or `--client all` to install for Codex, GitHub Copilot, and Claude Code. Add `--force` only when replacing an existing installation.

## Source

The skill instructions and supporting resources are in `skill/webex-connect-setup/`.
