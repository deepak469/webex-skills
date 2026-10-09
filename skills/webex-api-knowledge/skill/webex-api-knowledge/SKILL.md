---
name: webex-api-knowledge
description: Retrieve grounded Webex Public API and integration knowledge, then implement or explain working Webex code in the user's local project. Use for Webex REST APIs, OAuth integrations, webhooks, meetings, messaging, calling, contact center, and related developer-portal questions. Do not use for administering a live Webex organization unless the user separately requests that action.
---

# Webex API Knowledge

Use the local helper to ground Webex API work before relying on recalled API details. The helper owns browser login, token refresh, secure local token storage, and calls to the structured knowledge endpoint; never ask the user to paste a token into chat.

## Retrieve knowledge

1. Inspect the user's request and relevant local code first.
2. Break the information need into 1–8 distinct, self-contained search queries. Keep each query under 500 characters. Include the Webex product, resource, operation, language or SDK, and the specific auth or error concern when relevant.
3. Do not send source code, secrets, personal data, or full logs as search queries. Search only for the Webex knowledge needed to complete the task.
4. Write a temporary JSON request matching [references/knowledge-api-contract.md](references/knowledge-api-contract.md), then run:

   ```sh
   node <skill-directory>/scripts/webex-knowledge.mjs search --request <request-json-path>
   ```

   Resolve `<skill-directory>` to this skill's installed directory. The helper connects to its fixed Webex knowledge-service origin.
5. In Codex, run the helper normally once so Codex can apply its native network policy. If it exits with `code: "network_permission_required"`, immediately rerun that exact command through the shell execution tool with escalated sandbox/network permission and explain that it connects to the configured Webex knowledge-service and Webex login hosts. This must be a real tool-level approval request, not a plain chat message saying access was requested. After approval, retry once and continue automatically; do not ask the user to repeat their request, change Codex configuration, or unset `CODEX_SANDBOX_NETWORK_DISABLED`. If permission is denied or the approved retry fails, report that grounded retrieval was unavailable and continue only when the task can be completed safely without it.
6. If the helper says browser authorization is required, tell the user that a Webex login window is opening and let the foreground helper continue waiting. The helper briefly listens on `localhost:17177` to receive the login callback. Browser login is the only expected user interaction; after login the helper must resume automatically. Never ask the user for a macOS password, Windows password, Webex token, polling credential, or secure-store contents. If a terminal unexpectedly prompts for password data, cancel the helper and report the secure-storage failure rather than asking the user to type anything.
7. Treat `partial: true` and per-query warnings as incomplete retrieval, not full success. If results are empty, refine the queries once. Do not repeatedly broaden queries or invent missing API behavior.

## Complete the development task

- Use retrieved records as grounding, but adapt the implementation to the repository's language, libraries, conventions, and existing authentication model.
- Prefer the API operation, fields, scopes, and constraints supported by the returned records. Reconcile conflicting records explicitly; prefer the more specific record and source URL.
- Generate complete code only when requested. Otherwise answer the developer's question directly.
- Validate changes with the repository's normal tests or the smallest proportionate check.
- Cite useful `source_url` values in explanations when available. Do not dump all retrieved content unless the user asks for raw results.
- State when retrieval was unavailable or insufficient. Never present an ungrounded guess as retrieved Webex documentation.

## Helper operations

Use these only when needed:

```sh
node <skill-directory>/scripts/webex-knowledge.mjs status
node <skill-directory>/scripts/webex-knowledge.mjs auth
node <skill-directory>/scripts/webex-knowledge.mjs logout
```

`logout` removes the locally stored Webex token pair. Run it only when the user asks to sign out, remove credentials, or recover from an explicitly confirmed account mismatch.

For request fields, response interpretation, and error behavior, read [references/knowledge-api-contract.md](references/knowledge-api-contract.md). For installing the same skill in Codex, GitHub Copilot, or Claude Code, read [references/installation.md](references/installation.md).
