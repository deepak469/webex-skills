---
name: webexconnect-sendmessage
description: >
  Route an outbound Webex Connect message to the correct channel skill and API family, using shared setup, Contact Policy, and webhook guidance when required.
---

## Role

Treat this as the public front door for outbound messaging. It is a router and
shared workflow, not a universal payload schema. Select exactly one channel
adapter for the requested send, then load only the cross-cutting skills that
the request needs.

The standalone skill tree is the source of truth. Plugin packages add manifests,
commands, and rules on top of the same skills; they must not contain a second,
independently maintained send implementation.

## MCP Send Path

Use the Webex Connect CPaaS MCP tools when they are available and the user
explicitly asks to send an SMS or email. Do not use them for a draft, payload
review, or API-code request.

1. Identify the channel and classify the use case as exactly one of `marketing`,
   `utility`, or `service`.
2. Call `mcp__mcp_servers_webexcpaas__webex_sender_ids` with `channel` set to
   `sms` or `email` and the selected `usecase`.
3. Select a returned `senderid` whose `usecases` includes the selected use case.
   If there is no match, or multiple senders require a user choice, stop and
   ask rather than inventing or silently choosing an incompatible sender.
4. Route to the matching channel skill and call its MCP send tool with the
   selected sender.
5. Report the returned `messageId` and `status`. A `queued`, `accepted`, or
   similar status is not proof of delivery.

MCP authentication is handled by the selected host's documented secure OAuth
flow. Verify that the MCP connection is available and authenticated before
using it. Never ask the user to paste an access token into chat. If the host is
not configured, route the user to `webex-connect-setup` and use the direct API
path only when its `.env` prerequisites are present.
For multiple recipients or channel features unsupported by the MCP tools, use
the documented API path instead of silently looping or dropping fields.

## Channel Decision

Use the following decision rules when the user has not named a channel:

| Need | Channel | Adapter |
| --- | --- | --- |
| Universal phone reach | SMS | `webexconnect-sms-sendmessage` |
| Rich media to phone numbers | MMS | `webexconnect-mms-sendmessage` |
| Branded rich native messaging | RCS | `webexconnect-rcs-sendmessage` |
| Business-initiated WhatsApp | WhatsApp templates | `webexconnect-whatsapp-sendmessage` |
| Transactional or marketing communications | Email | `webexconnect-email-sendmessage` |
| Mobile app notifications | Push | `webexconnect-push-sendmessage` |
| In-app support or messaging | Live Chat/In-App | `webexconnect-livechat-inapp-sendmessage` |
| iOS Messages app business chat | Apple Messages for Business | `webexconnect-apple-messages-for-business-sendmessage` |
| Facebook Page messaging | Facebook Messenger | `webexconnect-facebook-messenger-sendmessage` |
| Phone call notifications or IVR | Voice | `webexconnect-voice-sendmessage` |

Confirm sender assets, recipient identifiers, regional availability, templates,
and fallback requirements before selecting an adapter. Do not assume that a
channel's content types, receipts, or fallback behavior are shared by another
channel.

## Routing Workflow

1. Identify the channel, use case, destination type, and whether the message is
   outbound, inbound, or an SDK/client implementation.
2. If the channel is unknown, use the Channel Decision table in this skill to
   choose the channel and determine fallback and onboarding requirements.
3. Use `webex-connect-setup` to resolve the environment, regional host,
   authentication, asynchronous response model, and rate limits when those
   details are missing.
4. Load exactly one channel adapter from the table below. Do not merge payload
   fields across adapters.
5. Add `webexconnect-contact-policy` when consent, opt-out, or frequency caps
   must be enforced.
6. Add `webexconnect-webhooks-events` when delivery, read, click, failure,
   inbound, or call events must be reconciled.
7. Add `webex-connect-setup` or `webexconnect-sandbox` when tenant, sender,
   app, credential, or test-environment prerequisites are missing.
8. Return the smallest valid request first, then optional rich content or
   channel features. Clearly separate API acceptance from final delivery.

## Channel Adapters

| Channel | Adapter skill | API family | Destination identifier |
| --- | --- | --- | --- |
| SMS | `webexconnect-sms-sendmessage` | Messaging API v2 | `msisdn` |
| MMS | `webexconnect-mms-sendmessage` | Messaging API v2 | `msisdn` |
| RCS | `webexconnect-rcs-sendmessage` | Messaging API v2 | `msisdn` |
| Email | `webexconnect-email-sendmessage` | Messaging API v2 | `email` |
| Push | `webexconnect-push-sendmessage` | Messaging API v1 | `userid` or `pushid` |
| Live Chat/In-App | `webexconnect-livechat-inapp-sendmessage` | Messaging API v1 | `userid` or `customerid` |
| Apple Messages for Business | `webexconnect-apple-messages-for-business-sendmessage` | Messaging API v1 | Apple opaque ID |
| Facebook Messenger | `webexconnect-facebook-messenger-sendmessage` | Messaging API v1 | `psid` |
| WhatsApp | `webexconnect-whatsapp-sendmessage` | Messaging API v1 | `waid` |
| Voice | `webexconnect-voice-sendmessage` | Voice API v1 or documented v2 flow | `dialedNumber` |

For SDK/client work, route to `webexconnect-livechat-widget` for browser
widgets or `webexconnect-android-push-inapp-messaging-builder` for native
Android Push/In-App applications. These are runtime integrations, not HTTP
send adapters.

## API Families

| API family | Endpoint pattern | Typical channels |
| --- | --- | --- |
| Send Message API v2 | `POST https://api.{region}.webexconnect.io/v2/messages` | SMS, MMS, RCS, Email, documented v2 Voice flows |
| Messaging API v1 | `POST https://api.{region}.webexconnect.io/resources/v1/messaging` | Push, Live Chat/In-App, Apple Messages for Business, Messenger, WhatsApp |
| Voice API v1 | `POST https://api.{region}.webexconnect.io/v1/voice/messages` | TTS, media playback, programmable voice callbacks |

Keep v2 camel-case fields such as `notifyUrl` and `correlationId` separate from
v1 lower-case fields such as `notifyurl` and `correlationid`.

## Shared Send Contract

Every adapter should confirm, when supported:

- regional API host and Service Key or service-specific JWT;
- configured sender, app asset, domain, caller ID, or approved business asset;
- channel-specific destination identifier and formatting;
- stable correlation value and callback metadata;
- notify URL, callback URL, or outbound webhook for final state;
- supported receipt values and channel-specific retry behavior;
- Contact Policy checks when consent or frequency caps apply;
- batching and tenant/channel TPS limits.

Immediate HTTP success means accepted, queued, or submitted. Store returned
message or call IDs and reconcile final state from callbacks, webhooks, or
status APIs.

## v2 Payload Pattern

Use only for adapters documented on Send Message API v2:

```json
{
  "channel": "sms",
  "from": "SENDER",
  "to": [
    {
      "msisdn": ["+15551234567"],
      "correlationId": "order-123"
    }
  ],
  "content": {
    "type": "text",
    "text": "Your order has shipped."
  },
  "requestedReceipts": ["SUBMITTED", "DELIVERED", "FAILED"],
  "callbackData": "order-123",
  "notifyUrl": "https://example.com/webexconnect/status"
}
```

## v1 Payload Pattern

Use only for adapters documented on Messaging API v1:

```json
{
  "deliverychannel": "whatsapp",
  "appid": "APP_ID",
  "destination": [
    {
      "waid": ["15551234567"]
    }
  ],
  "channels": {},
  "correlationid": "order-123",
  "callbackData": "order-123",
  "notifyurl": "https://example.com/webexconnect/status"
}
```

## Setup Preflight

Before routing a send, require the project `.env` and the selected adapter’s endpoint and credential values. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask them to repeat values already stored there or echo secrets.

## CANNOT

- Cannot pretend that every channel has one payload shape, content model, or
  receipt vocabulary.
- Cannot use one destination identifier across channels.
- Cannot mix v1 and v2 fields or assume `notifyUrl` and `notifyurl` are
  interchangeable.
- Cannot select a channel adapter without checking its sender/app asset,
  onboarding, template, consent, and recipient requirements.
- Cannot treat HTTP acceptance or publish success as delivered, read, clicked,
  answered, or played.
- Cannot bypass Contact Policy, channel policy, template approval, or regional
  compliance requirements.

## Source Links

- https://developers.webexconnect.io/reference/apioverview
- https://developers.webexconnect.io/reference/send-sms-message-api-v2
- https://developers.webexconnect.io/reference/mms-api
- https://developers.webexconnect.io/reference/rcs-api
- https://developers.webexconnect.io/reference/email-api
- https://developers.webexconnect.io/reference/whatsapp-apis
- https://developers.webexconnect.io/reference/voice-only-api-v1-make-outbound-calls

## Next Skills

- Connection and authentication: `webex-connect-setup`
- Channel adapters: use the table in this skill
- Delivery and inbound events: `webexconnect-webhooks-events`
- Consent and frequency caps: `webexconnect-contact-policy`
