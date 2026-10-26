---
name: webexconnect-livechat-inapp-sendmessage
description: >
  Build and validate Webex Connect Messaging API v1 requests for Live Chat, In-App Messaging, notifications, threads, and callbacks.
---

## Overview

Live Chat/In-App uses Messaging API v1 with `deliverychannel: "appmessaging"`.
It can send an in-app message, a notification, or both, and normally requires a
thread and an app user/customer identity.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, app asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V1_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- App asset and SDK integration configured.
- App user identified by `userid` or `customerid`.
- `thread_id` when sending into a conversation thread.
- Service Key or service-specific JWT.
- Callback or outbound webhook path for delivery and inbound replies.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/resources/v1/messaging
```

## Payload Pattern

```json
{
  "deliverychannel": "appmessaging",
  "appid": "APP_ID",
  "destination": [
    {
      "userid": ["user-123"]
    }
  ],
  "channels": {
    "appmessaging": {
      "thread_id": "thread-123",
      "message": {
        "text": "Can we help with your order?",
        "quickreplies": {
          "reference": "support-options",
          "options": [
            {
              "type": "quickReplyPostback",
              "identifier": "help",
              "title": "Yes",
              "payload": {
                "intent": "help"
              }
            }
          ]
        }
      },
      "notification": {
        "title": "Support",
        "text": "New message from support"
      }
    }
  },
  "correlationid": "support-123",
  "callbackData": "support-123",
  "notifyurl": "https://example.com/webexconnect/inapp"
}
```

## Key Patterns

- Use Thread APIs or prior inbound events to obtain valid thread IDs.
- Keep quick reply identifiers stable and map payloads to application intents.
- Validate attachment shape against the exact message type before sending media.
- Use platform-specific notification extras only when the mobile app supports them.
- Capture inbound replies through outbound webhooks or data streams.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot send in-app messages to users who are not registered/profiled for the app.
- Cannot omit `thread_id` for message types that require a thread.
- Cannot use Push API payloads directly; app messaging has its own `channels.appmessaging` shape.
- Cannot assume notification interactivity categories are supported by every client app version.
- Cannot treat v1 `notifyurl` as v2 `notifyUrl`.

## Source Links

- https://developers.webexconnect.io/reference/live-chat-in-app-messaging-api
- https://developers.webexconnect.io/reference/live-chat-in-app-messages-outbound-webhooks
- https://developers.webexconnect.io/reference/overview-of-thread-apis
- https://developers.webexconnect.io/reference/apioverview

## Next Skills

- Push: `webexconnect-push-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
- Connection and authentication: `webex-connect-setup`
