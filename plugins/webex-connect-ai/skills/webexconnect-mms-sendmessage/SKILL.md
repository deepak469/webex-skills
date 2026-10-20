---
name: webexconnect-mms-sendmessage
description: >
  Build and validate Webex Connect MMS Send Message API v2 requests for recipients, attachments, fallback text, receipts, and callbacks.
---

## Overview

MMS uses Send Message API v2 with `channel: "mms"`. Confirm tenant and sender
enablement before coding; the API reference states MMS access is currently for
US and Canadian regions unless enabled through the account team.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, sender asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V2_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Service Key or service-specific JWT.
- MMS enabled for the tenant and region.
- MMS-capable sender and recipient reachability.
- Publicly reachable media URLs.
- Callback endpoint for delivery status.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/v2/messages
```

## Payload Pattern

```json
{
  "channel": "mms",
  "from": "+15551230000",
  "to": [
    {
      "msisdn": ["+15551234567"],
      "correlationId": "invoice-123"
    }
  ],
  "requestedReceipts": ["SUBMITTED", "DELIVERED", "FAILED"],
  "content": {
    "subject": "Invoice",
    "fallbacktext": "Your invoice is available online.",
    "name": "Invoice message",
    "attachments": [
      {
        "type": "pdf",
        "messageText": "Invoice PDF",
        "mediaUrl": "https://example.com/invoice.pdf",
        "duration": 5
      }
    ]
  },
  "callbackData": "invoice-123",
  "notifyUrl": "https://example.com/webexconnect/mms"
}
```

## Attachment Types

The API examples include image, iCal, PDF, video, audio, and vCard attachment
types. Validate current size, media type, and carrier limitations before using
large files or carrier-specific content.

## Key Patterns

- Use `fallbacktext` so the recipient gets useful content if rich delivery is not possible.
- Host media on HTTPS URLs that Webex Connect and carriers can fetch.
- Keep attachments purposeful; large files can fail or degrade carrier delivery.
- Use `correlationId`, `callbackData`, and `notifyUrl` for reconciliation.
- Apply Contact Policy when consent/frequency caps are required for MMS.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot assume MMS is enabled in every tenant or region.
- Cannot use private, expired, or auth-protected media URLs.
- Cannot assume all Canadian carriers support every TFN MMS path.
- Cannot treat `SUBMITTED` as delivered.
- Cannot reuse SMS text-only payloads without adding MMS `content.attachments`.

## Source Links

- https://developers.webexconnect.io/reference/mms-api
- https://developers.webexconnect.io/reference/mms-outbound-webhooks

## Next Skills

- Connection and authentication: `webex-connect-setup`
- SMS fallback: `webexconnect-sms-sendmessage`
- Unified send guide: `webexconnect-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
