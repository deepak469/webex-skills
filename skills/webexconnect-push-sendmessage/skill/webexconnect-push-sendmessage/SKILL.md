---
name: webexconnect-push-sendmessage
description: >
  Build and validate Webex Connect Push Messaging API v1 requests for registered users and devices, platform payloads, notifications, and callbacks.
---

## Overview

Push uses Messaging API v1, not Send Message API v2. The payload uses
`deliverychannel: "push"`, `appid`, `destination`, and nested platform payloads
under `channels.push`.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, app asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V1_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Mobile or web app asset configured in Webex Connect.
- SDK/device registration producing `userid` or `pushid`.
- Valid platform credentials in the app asset.
- Service Key or service-specific JWT.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/resources/v1/messaging
```

## Payload Pattern

```json
{
  "deliverychannel": "push",
  "appid": "APP_ID",
  "destination": [
    {
      "userid": ["user-123"]
    }
  ],
  "channels": {
    "push": {
      "android": {
        "title": "Order update",
        "text": "Your order has shipped.",
        "extras": {
          "time_to_live": "3600",
          "customtags": {
            "orderId": "123"
          },
          "notificationaction": {
            "action": "OPEN_URL",
            "value": "https://example.com/orders/123"
          }
        }
      },
      "ios": {
        "title": "Order update",
        "text": "Your order has shipped.",
        "extras": {
          "badge": "1",
          "sound": "default"
        }
      }
    }
  },
  "correlationid": "order-123",
  "callbackData": "order-123",
  "notifyurl": "https://example.com/webexconnect/push"
}
```

## Key Patterns

- Choose `userid` when targeting a known app user and `pushid` for a specific device token/profile where appropriate.
- Keep Android and iOS payloads explicit because platform options differ.
- Use Android `time_to_live` for expiry behavior and `collapse_key` when only the latest pending notification matters.
- Use `customtags.imageurl` for rich notification images when supported by the app.
- Use notification actions intentionally; validate deep links and URLs before sending.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot send push until the device/app user is registered through the Webex Connect SDK.
- Cannot use v2 fields such as `channel` and `notifyUrl` for the v1 push endpoint.
- Cannot rely on badges, sounds, images, or actions behaving identically across Android and iOS.
- Cannot use stale app credentials or expired device registrations.
- Cannot treat accepted push as viewed by the user.

## Source Links

- https://developers.webexconnect.io/reference/push-api
- https://developers.webexconnect.io/reference/push-outbound-webhooks
- https://developers.webexconnect.io/reference/apioverview

## Next Skills

- Live Chat/In-App: `webexconnect-livechat-inapp-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
- Connection and authentication: `webex-connect-setup`
