---
name: webexconnect-whatsapp-sendmessage
description: >
  Build and validate Webex Connect WhatsApp API v1 messages for session replies, approved templates, media, interactive content, and callbacks.
---

## Overview

WhatsApp uses Messaging API v1 with `deliverychannel: "whatsapp"`. Proactive
outbound WhatsApp messages require template registration and approval in Webex
Connect. Free-form text is for customer-service/session contexts where WhatsApp
policy allows it.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, app asset, template setup, or callback details are missing.
  Reuse its `WEBEX_CONNECT_MESSAGING_V1_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- WhatsApp app asset in Webex Connect.
- WhatsApp app ID (`appid`).
- Destination WhatsApp ID or phone number (`waid`).
- Approved template for business-initiated or out-of-window messages.
- Service Key or service-specific JWT.
- Callback endpoint for delivery status.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/resources/v1/messaging
```

## Text Payload Pattern

```json
{
  "deliverychannel": "whatsapp",
  "appid": "WHATSAPP_APP_ID",
  "destination": [
    {
      "waid": ["15551234567"]
    }
  ],
  "channels": {
    "OTT-Messaging": {
      "wa": {
        "type": "text",
        "text": {
          "body": "This is a WhatsApp message"
        }
      }
    }
  },
  "correlationid": "order-123",
  "callbackData": "order-123",
  "notifyurl": "https://example.com/webexconnect/whatsapp"
}
```

## Message Types

- Text
- Media
- Location
- Contacts
- List messages
- Reply buttons
- Template messages

## Key Patterns

- Use approved templates for proactive business-initiated messages and messages outside the customer-service window.
- Keep template parameter names and order aligned with the approved template in Webex Connect.
- Use `options.shortenLinks`, `trackClicks`, and `domain` only when short-link tracking is configured.
- Include `identity_key_hash` only when validating customer identity and you have the right value.
- Preserve v1 field casing: `notifyurl`, `notifyurlAuthId`, and `correlationid`.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot send proactive WhatsApp messages without an approved template.
- Cannot use SMS `msisdn` destination fields; WhatsApp uses `waid`.
- Cannot assume `waid` formatting is identical to E.164 with a leading plus.
- Cannot receive reliable final outcomes without callback or webhook setup.
- Cannot use deprecated HSM flows for new builds when template messages are available.

## Source Links

- https://developers.webexconnect.io/reference/whatsapp-apis
- https://developers.webexconnect.io/reference/whatsapp-template-messages
- https://developers.webexconnect.io/reference/whatsapp-outbound-webhooks

## Next Skills

- Unified send guide: `webexconnect-sendmessage`
- Sandbox: `webexconnect-sandbox`
- Webhooks: `webexconnect-webhooks-events`
