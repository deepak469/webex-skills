---
name: webexconnect-webhooks-events
description: >
  Build and troubleshoot Webex Connect webhook receivers, callback verification, inbound events, Event API requests, retries, and data streams.
---

## Overview

Use this whenever Webex Connect calls an application or an application raises an
event into Webex Connect. Delivery, call, read, click, inbound, and failure
events are asynchronous and must be handled independently from send requests.

## Outbound Webhook Handler Rules

- Use HTTPS endpoints.
- Make the URL pass any required HEAD validation.
- Return HTTP 200 only after durable acceptance by your system.
- Keep handlers fast and idempotent.
- Persist message IDs, call IDs, `correlationId`, `correlationid`, `callbackData`, `x-wx-gtrid`, and channel status fields.
- Avoid logging raw customer message bodies, secrets, JWTs, or service keys.

## Signature Verification

If Hub Secret is enabled, verify `x-hub-signature` using HMAC with the same
secret configured in Webex Connect. Reject mismatches and avoid leaking payloads
in logs.

## Event API v1

Use Event API v1 when an external system needs to raise custom events into
Webex Connect. Confirm the service, event, rule, and actions exist before
coding. Treat common error responses as contract failures: invalid JSON,
authentication failure, missing mandatory parameters, invalid values, or missing
custom event parameters.

## Inbound Webhooks And Data Streams

Use inbound webhooks for external systems that invoke or resume Webex Connect
flows. Use data streams for higher-volume analytics/event-pipeline processing
of channel events or audit logs.

## Setup Preflight

Before calling Event or Inbound Webhook APIs, require the corresponding endpoint and Service Key or service JWT from the project `.env`. For receiver code, require `WEBEX_CONNECT_HUB_SECRET` only when signature verification is enabled. If a required value is missing, stop and ask the user to run `webex-connect-setup`. Never echo secrets.

## CANNOT

- Cannot rely on receiving a callback exactly once.
- Cannot treat every non-200 response as retriable.
- Cannot verify `x-hub-signature` without the configured Hub Secret.
- Cannot trigger Event API flows without the required service, event, rule, and action setup.
- Cannot debug final delivery using only the original send response.

## Source Links

- https://developers.webexconnect.io/reference/outbound-webhooks
- https://developers.webexconnect.io/reference/inbound-webhooks
- https://developers.webexconnect.io/reference/event-api-overview
- https://developers.webexconnect.io/reference/data-streams

## Next Skills

- Connection and authentication: `webex-connect-setup`
- SMS callbacks: `webexconnect-sms-sendmessage`
- WhatsApp callbacks: `webexconnect-whatsapp-sendmessage`
- Voice callbacks: `webexconnect-voice-sendmessage`
