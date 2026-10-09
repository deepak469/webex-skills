# Installation

The canonical skill directory is `webex-api-knowledge`. It requires Node.js 20 or newer and has no third-party package dependencies.

## Package installation

Install directly from the latest release package in the public `webex-skills`
repository. To pin a version, replace `latest` with a version from
`skills/webex-api-knowledge/release/`, for example `0.2.0-beta.0`.

User-level installation, available across projects:

```bash
npx --yes \
  --package https://raw.githubusercontent.com/webex/webex-skills/main/skills/webex-api-knowledge/release/webex-api-knowledge-latest.tgz \
  webex-api-knowledge install \
  --client all \
  --scope user
```

Project-level installation, run from the target project:

```bash
cd /path/to/project

npx --yes \
  --package https://raw.githubusercontent.com/webex/webex-skills/main/skills/webex-api-knowledge/release/webex-api-knowledge-latest.tgz \
  webex-api-knowledge install \
  --client all \
  --scope project
```

Use `--force` to replace an existing installation after reviewing the new
package version.

## Repository installation

- Codex and GitHub Copilot in VS Code discover the installed directory at `.agents/skills/webex-api-knowledge`.
- Claude Code expects the same directory at `.claude/skills/webex-api-knowledge`.

For Claude Code, copy the canonical directory rather than maintaining a rewritten skill. On Windows, copying is preferred over symlinking because symlink creation may require Developer Mode or elevated privileges.

## Personal installation

Copy the canonical directory to:

- Codex: `~/.agents/skills/webex-api-knowledge`
- GitHub Copilot: `~/.copilot/skills/webex-api-knowledge`
- Claude Code: `~/.claude/skills/webex-api-knowledge`

The bundled installer performs these copies without platform-specific shell commands:

```sh
node <repository-directory>/scripts/install-skill.mjs --client all --scope user
```

For a project checkout, use `--scope project`. Codex and Copilot share the `.agents/skills` destination, so the installer writes that copy only once. Existing destinations are preserved unless the user explicitly supplies `--force`.

The `agents/openai.yaml` file provides optional Codex presentation metadata. Other clients can ignore it; the portable behavior lives in `SKILL.md`, `scripts/`, and `references/`.

## Invocation

- Codex: `$webex-api-knowledge`
- Claude Code: `/webex-api-knowledge`
- GitHub Copilot VS Code Agent Mode: ask Copilot to use the `webex-api-knowledge` skill, or let it select the skill from its description.

## Codex network permission

The helper attempts the request normally so Codex can apply its native network
policy. If that request is blocked, it returns
`code: "network_permission_required"`. The skill then reruns the exact helper
command through Codex's tool-level sandbox/network escalation, which produces
the permission prompt. After approval, Codex retries once and continues
automatically. The installer does not weaken the sandbox, silently edit
`~/.codex/config.toml`, or attempt to bypass the sandbox by changing
`CODEX_SANDBOX_NETWORK_DISABLED`.

Developers who prefer to enable networking for every sandboxed command in a
trusted project can explicitly add this project-local configuration:

```toml
# <project>/.codex/config.toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = true
```

This optional setting is broader than the skill-specific approval flow.

## Service origin

The released helper uses one fixed service origin in `scripts/webex-knowledge.mjs`. For local service testing, edit that constant in a development checkout and do not distribute the edited package. Credentials are stored separately for each service origin.
