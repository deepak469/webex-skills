---
name: webexconnect-apple-messages-for-business-sendmessage
description: >
  Build and validate Webex Connect Apple Messages for Business API v1 requests for text, rich messages, attachments, callbacks, and delivery handling.
---

## Overview

Apple Messages for Business uses Messaging API v1 with
`deliverychannel: "AppleBusinessChat"`. The API reference exposes separate
endpoint pages for text and each rich message type; select the exact page before
building a rich payload.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, app asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V1_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Apple Messages for Business app asset configured in Webex Connect.
- App ID from the Connect platform.
- Customer's Apple opaque ID from an inbound AMB interaction.
- Service Key or service-specific JWT.
- Valid callback URL if delivery reports are required.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/resources/v1/messaging/
```

## Payload Skeleton

```json
{
  "deliverychannel": "AppleBusinessChat",
  "appid": "AMB_APP_ID",
  "destination": [
    {
      "opaqueId": ["APPLE_OPAQUE_ID"]
    }
  ],
  "channels": {
    "AppleBusinessChat": {}
  },
  "correlationid": "case-123",
  "callbackData": "case-123",
  "notifyurl": "https://example.com/webexconnect/amb",
  "notifyurlAuthId": "AUTH_ID"
}
```

Confirm the destination field name and `channels` body in the selected AMB
endpoint schema or Try It panel; the API docs describe the destination as the
user's opaque ID and split message-type fields by endpoint page.

## Message Types

- Text
- Typing indicator
- Text with attachments
- Rich link
- List picker
- Time picker
- Apple Pay and authentication
- Quick reply
- Form messages
- iMessage app

## Key Patterns

- Use the exact AMB endpoint page for the rich message type being sent.
- Preserve v1 lower-case field names such as `correlationid` and `notifyurl`.
- Use valid authorization IDs for notify URLs when configured; invalid notify URLs may not produce useful debug logs.
- Store Apple opaque IDs as channel-specific identifiers, not phone numbers.
- Validate Apple Pay, authentication, form, and picker payloads with the platform team before production.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot send AMB messages without an Apple Messages for Business app asset.
- Cannot invent a customer opaque ID; obtain it from inbound AMB context.
- Cannot assume text, list picker, Apple Pay, and form payloads share the same `channels` body.
- Cannot use SMS `msisdn`, WhatsApp `waid`, or Messenger `psid` as AMB destination identifiers.
- Cannot rely on invalid or whitespace-padded `notifyurl` values.

## Source Links

- https://developers.webexconnect.io/reference/apple-message-for-business-_text
- https://developers.webexconnect.io/reference/apple-message-for-business_-list-picker
- https://developers.webexconnect.io/reference/apple-message-for-business_-quick-reply
- https://developers.webexconnect.io/reference/amb-outbound-webhooks
- https://developers.webexconnect.io/reference/apioverview

## Next Skills

- In-app messaging: `webexconnect-livechat-inapp-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
- Connection and authentication: `webex-connect-setup`
