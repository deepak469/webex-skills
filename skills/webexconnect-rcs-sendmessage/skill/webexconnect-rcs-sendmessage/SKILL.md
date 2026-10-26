---
name: webexconnect-rcs-sendmessage
description: >
  Build and validate Webex Connect RCS Send Message API v2 requests for capability checks, rich content, templates, and SMS fallback.
---

## Overview

RCS is supported through Send Message API v2 with `channel: "rcs"`. Use an RCS
app asset in `from` and design SMS fallback for recipients or carriers that
cannot receive RCS.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, sender asset, or callback details are missing. Reuse its
  `WEBEX_CONNECT_MESSAGING_V2_URL`, `WEBEX_CONNECT_SERVICE_KEY`, and
  `WEBEX_CONNECT_SERVICE_JWT` values instead of inventing host or auth details.
- Service Key or service-specific JWT.
- RCS app asset and approved sender configuration.
- Recipient mobile number in E.164 format.
- Optional RCS capability lookup when routing decisions should happen before send.
- SMS sender and fallback text if using `options.smsFallback`.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/v2/messages
```

## Payload Pattern

```json
{
  "channel": "rcs",
  "from": "RCS_APP_ID",
  "to": [
    {
      "msisdn": ["+15551234567"],
      "correlationId": "shipment-123"
    }
  ],
  "options": {
    "smsFallback": true,
    "smsSenderId": "SMS_SENDER",
    "text": "Your shipment update is available."
  },
  "requestedReceipts": ["Sent", "Delivered", "Read", "Failed"],
  "content": {
    "type": "text",
    "text": "Your shipment is out for delivery. Reply Yes or No."
  },
  "callbackData": "shipment-123",
  "notifyUrl": "https://example.com/webexconnect/rcs"
}
```

## Message Types

The RCS API reference includes text, text with suggestions, scheduled text,
templates, file messages, rich cards, carousels, typing events, and read events.
For rich cards and carousels, include accurate media metadata; `fileSize` should
not be zero for images or videos in URLs.

## Key Patterns

- Use `options.smsFallback` only when an SMS sender and fallback text are ready.
- Use `carrierId` only when you trust the carrier mapping and want to skip lookup.
- Keep substitutions to fields where the docs support them; the docs call out text substitutions specifically.
- Test across every carrier or MaaP your program terminates to; receipt sequencing may vary.
- Preserve receipt value casing from the RCS docs, such as `Sent`, `Clicked`, `Delivered`, `Read`, and `Failed`.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot send RCS without a configured RCS app asset.
- Cannot guarantee RCS capability for every phone number without lookup or fallback.
- Cannot assume all MaaPs handle rich content metadata the same way.
- Cannot use SMS receipt names blindly; RCS receipt value casing differs in examples.
- Cannot skip fallback planning for critical notifications.

## Source Links

- https://developers.webexconnect.io/reference/rcs-api
- https://developers.webexconnect.io/reference/capability-api
- https://developers.webexconnect.io/reference/rcs-outbound-webhooks

## Next Skills

- Connection and authentication: `webex-connect-setup`
- SMS fallback: `webexconnect-sms-sendmessage`
- Unified send guide: `webexconnect-sendmessage`
- Webhooks: `webexconnect-webhooks-events`
