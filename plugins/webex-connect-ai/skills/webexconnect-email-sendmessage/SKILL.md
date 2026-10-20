---
name: webexconnect-email-sendmessage
description: >
  Build, validate, or send Webex Connect Email through Send Message API v2 or the configured Email MCP, including sender discovery, recipients, content, callbacks, and receipts.
---

## Overview

Email is supported through Send Message API v2 with `channel: "email"`. Build
for asynchronous acceptance and downstream receipts; available receipt types can
vary by configured email provider.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, sender domain/app, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V2_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Email channel/app configured in Webex Connect.
- Verified sender address/domain as required by the tenant setup.
- Service Key or service-specific JWT.
- Callback endpoint if delivery, bounce, complaint, read, click, or failure status is required.

## MCP Send Path

When the user explicitly asks to send one email and the Webex Connect CPaaS MCP
tools are available:

1. Call `mcp__mcp_servers_webexcpaas__webex_sender_ids` with
   `channel: "email"` and the use case `marketing`, `utility`, or `service`.
2. Use a returned `senderid` whose `usecases` includes that use case. If none
   is available, stop and ask for a compatible sender; never invent one.
3. Call `mcp__mcp_servers_webexcpaas__webex_email_message` with
   `channel: "email"`, the selected sender as `from`, a valid recipient as
   `to`, a subject of 50 characters or fewer, `body`, and `contentType` set to
   `text` or `html`.
4. Pass `callbackUrl` only when the user provides or requests one, then report
   the returned `messageId` and `status` as acceptance state.

The MCP tool accepts one `to` address and does not expose the full API v2
fields. For cc, bcc, multiple recipients, substitutions, scheduling, or rich
receipt controls, use the API payload path instead of silently dropping fields.
Before using the MCP send path, verify that the selected host has completed its
documented OAuth flow for `spark:mcp`. Do not ask for the token in chat or print
it. The local `.env` may hold a token only when the MCP host has a documented
secure way to consume it; `.env` presence alone does not authenticate the host.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/v2/messages
```

## Payload Pattern

```json
{
  "channel": "email",
  "from": "billing@example.com",
  "to": [
    {
      "email": ["customer@example.com"],
      "correlationId": "invoice-123"
    }
  ],
  "cc": [],
  "bcc": [],
  "multipleToRecipients": true,
  "options": {
    "fromName": "Example Billing"
  },
  "content": {
    "type": "html",
    "subject": "Your invoice",
    "replyTo": "support@example.com",
    "html": "<p>Your invoice is ready.</p>"
  },
  "requestedReceipts": ["submitted", "delivered", "bounce", "complaint", "failed"],
  "callbackData": "invoice-123",
  "notifyUrl": "https://example.com/webexconnect/email"
}
```

## Key Patterns

- Use `content.type: "text"` with `text` or `content.type: "html"` with `html`.
- Use `multipleToRecipients` intentionally; omitting it may send separate messages for each destination.
- Include `fromName` for recognizable inbox display names.
- Verify requested receipt values against the configured email backend; SMTP may support fewer receipts than SES.
- Use link shortening options only with a configured short-link domain.
- Apply Contact Policy for consent and frequency caps when appropriate.

## Setup Preflight

Before any direct Email API request, require `WEBEX_CONNECT_MESSAGING_V2_URL` and either `WEBEX_CONNECT_SERVICE_KEY` or `WEBEX_CONNECT_SERVICE_JWT` from the project `.env`. Before an MCP send, also require the configured MCP OAuth access token with `spark:mcp` and a connected, authenticated MCP client. If setup is incomplete, stop and ask the user to run `webex-connect-setup`. Never echo secrets; `.env` alone does not authenticate every MCP host.

## CANNOT

- Cannot assume unverified sender domains will be accepted or delivered.
- Cannot assume all receipt values are available for every email provider.
- Cannot put secrets, tokens, or PII in callback URLs.
- Cannot treat API acceptance as inbox delivery.
- Cannot rely on click/read receipts as universally available or privacy-proof.
- Cannot call the MCP send tool for a draft or payload-generation request.
- Cannot send with a sender ID that was not returned by sender discovery or
  explicitly supplied and validated by the user.

## Source Links

- https://developers.webexconnect.io/reference/email-api
- https://developers.webexconnect.io/reference/email-outbound-webhooks

## Next Skills

- Connection and authentication: `webex-connect-setup`
- Unified send guide: `webexconnect-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
- Contact Policy: `webexconnect-contact-policy`
