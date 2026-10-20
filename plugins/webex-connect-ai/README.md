# Webex Connect AI Plugin

This directory is the installable Webex Connect AI plugin package. It contains
19 complete skills, shared commands and rules, platform manifests, and branding
assets. The package is available to Codex through the repository marketplace
file at `.agents/plugins/marketplace.json`.

For outbound messaging, the plugin command and `$webexconnect-sendmessage`
skill provide one front door and route to exactly one channel adapter plus any
needed shared safeguards.

Before API-backed workflows, run `$webex-connect-setup` to create or update a
private project `.env`. The package contains only a blank environment template
and safe setup utility; it never contains the user's `.env` or credentials.
SMS/Email MCP authentication still needs the selected host's supported secure
configuration; project `.env` loading is not automatic in every host.

## Components

- Codex manifest: `.codex-plugin/plugin.json`
- Claude Code manifest: `.claude-plugin/plugin.json`
- Cursor manifest: `.cursor-plugin/plugin.json`
- Plugin logo assets: `assets/webex.svg`, `assets/webex-icon-400.png`
- Skills: `skills/*/SKILL.md`
- Cursor/Claude commands: `commands/*.md`
- Cursor rule: `rules/webex-connect-development.mdc`

## Local Testing

Codex repository marketplace:

```bash
codex plugin marketplace add /path/to/Webex-Connect-AI
codex plugin add webex-connect-ai@webex-connect-ai
```

To install a reproducible release, use the repository's `v0.2.39` tag. Previous
tags remain available for legacy installs.

Claude Code local plugin:

```bash
claude --plugin-dir ./plugins/webex-connect-ai
```

Cursor plugin submission checks should verify:

- `.cursor-plugin/plugin.json` exists and parses.
- `assets/webex-icon-400.png` is packaged and referenced by the Cursor manifest.
- `skills/*/SKILL.md` is discoverable.
- `rules/*.mdc` is discoverable.
- `commands/*.md` is discoverable.
- `build-ios-push-inapp-demo.md` uses the iOS builder with Swift Package
  Manager, APNs, and Webex Connect In-App Messaging SDK checks.

## Validation and maintenance

Edit the skills and plugin components in this directory, then run
`npm run validate` from the repository root. Keep root plugin assets under
`plugins/webex-connect-ai/assets/`. The Codex
manifest uses these files for the plugin card logo and composer icon, so they
must remain inside the installable plugin package.
