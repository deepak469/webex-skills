---
name: webexconnect-facebook-messenger-sendmessage
description: >
  Build and validate Webex Connect Facebook Messenger API v1 messages for Page-scoped recipients, text, attachments, interactive replies, and callbacks.
---

## Overview

Facebook Messenger uses Messaging API v1 with `deliverychannel: "fb"`. The
recipient destination is a page-scoped ID (`psid`), not a phone number.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, app asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V1_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Facebook Messenger app/channel asset configured in Webex Connect.
- Recipient PSID from an inbound Messenger interaction or profile.
- Valid use of Meta's messaging window, message tags, and allowed use cases.
- Service Key or service-specific JWT.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/resources/v1/messaging
```

## Payload Pattern

```json
{
  "appid": "FB_APP_ID",
  "deliverychannel": "fb",
  "channels": {
    "OTT-Messaging": {
      "fb": {
        "text": "Welcome to Webex Connect",
        "notification_type": "REGULAR",
        "messaging_type": "RESPONSE",
        "quick_replies": [
          {
            "content_type": "text",
            "title": "Help",
            "payload": "HELP"
          }
        ],
        "type": "conversation"
      }
    }
  },
  "destination": [
    {
      "psid": ["PAGE_SCOPED_ID"]
    }
  ],
  "correlationid": "case-123",
  "callbackData": "case-123",
  "notifyurl": "https://example.com/webexconnect/messenger"
}
```

## Key Patterns

- Use `messaging_type: "RESPONSE"` for responses inside the standard messaging window.
- Use `messaging_type: "UPDATE"` only for allowed proactive updates inside the window.
- Use `messaging_type: "MESSAGE_TAG"` and a valid `tag` only for non-promotional messages outside the window.
- Use `sender_action` for states such as typing on/off or mark seen; do not send it together with unsupported content combinations.
- Keep `notification_type` explicit when silent or no-push behavior matters.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot use phone numbers for Messenger destinations; use `psid`.
- Cannot send promotional messages outside Meta's allowed messaging window using message tags.
- Cannot assume every quick reply or attachment type is allowed for every Messenger policy state.
- Cannot use v2 `channel` payloads for the v1 Messenger endpoint.
- Cannot rely on an invalid `notifyurl`; the docs warn malformed URLs may not be logged usefully.

## Source Links

- https://developers.webexconnect.io/reference/facebook-messenger-api
- https://developers.webexconnect.io/reference/messenger-outbound-webhooks

## Next Skills

- Connection and authentication: `webex-connect-setup`
- WhatsApp: `webexconnect-whatsapp-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
