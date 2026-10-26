---
name: webexconnect-sms-sendmessage
description: >
  Build, validate, or send Webex Connect SMS through Send Message API v2 or the configured SMS MCP, including sender discovery, recipients, scheduling, receipts, and callbacks.
---

## Overview

Use Send Message API v2 for new SMS sends unless maintaining a v1 integration.
The API is asynchronous: the immediate response confirms acceptance or rejection,
and delivery status arrives through `notifyUrl` or outbound webhooks.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, sender asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V2_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Tenant region and Messaging API v2 host.
- Service Key or service-specific JWT.
- SMS-capable sender ID, long code, short code, or configured sender asset.
- Recipient `msisdn` values in E.164 format.
- Callback endpoint if delivery, failure, or click status is required.

## MCP Send Path

When the user explicitly asks to send one SMS and the Webex Connect CPaaS MCP
tools are available:

1. Call `mcp__mcp_servers_webexcpaas__webex_sender_ids` with
   `channel: "sms"` and the use case `marketing`, `utility`, or `service`.
2. Use a returned `senderid` whose `usecases` includes that use case. If none
   is available, stop and ask for a compatible sender; never invent one.
3. Call `mcp__mcp_servers_webexcpaas__webex_sms_message` with `from` set to the
   selected sender, `to` as an E.164 phone number, `content`, and
   `contentType` set to `text` or `unicode` based on the message encoding.
4. Pass `callbackUrl` only when the user provides or requests one, then report
   the returned `messageId` and `status` as acceptance state.

The MCP tool sends one recipient and does not expose the full API v2 payload.
For multiple recipients, substitutions, scheduling, receipts, or other rich
fields, use the API payload path instead. Before an MCP send, verify that the
selected host has completed its documented OAuth flow for `spark:mcp`. Do not
ask for the token in chat or print it. The local `.env` may hold a token only
when the MCP host has a documented secure way to consume it; `.env` presence
alone does not authenticate the host.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/v2/messages
```

## Payload Pattern

```json
{
  "channel": "sms",
  "from": "SENDER_ID_OR_NUMBER",
  "to": [
    {
      "msisdn": ["+15551234567"],
      "substitutions": {
        "{{name}}": "Alex"
      },
      "correlationId": "otp-123"
    }
  ],
  "content": {
    "type": "text",
    "text": "Your verification code is {{code}}."
  },
  "requestedReceipts": ["SUBMITTED", "DELIVERED", "FAILED"],
  "callbackData": "otp-123",
  "notifyUrl": "https://example.com/webexconnect/sms"
}
```

## Key Patterns

- Use `content.type` as `text` for standard GSM text and `unicode` for emojis or multi-byte characters; unicode may increase segment usage.
- Use `SUBMITTED`, `DELIVERED`, `FAILED`, and `CLICKED` only when link tracking is configured.
- For link shortening, include `options.shortenLinks`, `options.trackClicks`, and the configured short-link `domain`.
- Use `sendAt` for UTC scheduling and set only one of `expireAt` or `validity`.
- Use destination-level substitutions for per-recipient values and global substitutions for shared values.
- Add `contactPolicy.contactPolicyGroup` plus at least one enabled check when consent or frequency caps are required.

## Setup Preflight

Before any direct SMS API request, require `WEBEX_CONNECT_MESSAGING_V2_URL` and either `WEBEX_CONNECT_SERVICE_KEY` or `WEBEX_CONNECT_SERVICE_JWT` from the project `.env`. Before an MCP send, also require the configured MCP OAuth access token with `spark:mcp` and a connected, authenticated MCP client. If setup is incomplete, stop and ask the user to run `webex-connect-setup`. Never echo secrets; `.env` alone does not authenticate every MCP host.

## CANNOT

- Cannot treat accepted or queued responses as delivered.
- Cannot send both `expireAt` and `validity`.
- Cannot assume `from` uses the same `+E.164` requirement as destination `msisdn`.
- Cannot receive click receipts without link shortening and tracking.
- Cannot exceed tenant Messaging API TPS or channel TPS by batching blindly.
- Cannot call the MCP send tool for a draft or payload-generation request.
- Cannot send with a sender ID that was not returned by sender discovery or
  explicitly supplied and validated by the user.

## Source Links

- https://developers.webexconnect.io/reference/send-sms-message-api-v2
- https://developers.webexconnect.io/reference/sms-length-and-encoding
- https://developers.webexconnect.io/reference/sms-outbound-webhooks

## Next Skills

- Connection and authentication: `webex-connect-setup`
- Unified send guide: `webexconnect-sendmessage`
- MMS: `webexconnect-mms-sendmessage`
- RCS fallback: `webexconnect-rcs-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
