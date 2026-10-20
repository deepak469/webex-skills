---
name: webexconnect-voice-sendmessage
description: >
  Build and validate Webex Connect Voice API v1 and documented Send Message API v2 voice requests for outbound calls, text-to-speech, media, callbacks, and call status.
---

## Overview

Voice API v1 is asynchronous. The API response confirms acceptance; subsequent
call progress and outcomes arrive on the callback URL. Use Voice API v1 for
simple outbound voice notifications and programmable voice patterns.

## Prerequisites

- Run `webex-connect-setup` first when tenant region, API base URL,
  authentication, caller ID/voice asset, or callback details are missing. Reuse
  its `WEBEX_CONNECT_API_BASE`, `WEBEX_CONNECT_VOICE_API_BASE`,
  `WEBEX_CONNECT_SERVICE_KEY`, and `WEBEX_CONNECT_SERVICE_JWT` values instead
  of inventing host or auth details.
- Voice-enabled Webex Connect asset/number for `callerId`.
- Destination `dialedNumber`.
- Service Key or service-specific JWT.
- Callback endpoint for call state.

## Endpoint

```text
POST https://api.{region}.webexconnect.io/v1/voice/messages
```

## TTS Payload Pattern

```json
{
  "callerId": "+15551230000",
  "dialedNumber": "+15551234567",
  "audio": {
    "type": "TTS",
    "style": "NEURAL",
    "language": "en-US",
    "voice": "AriaNeural",
    "gender": "FEMALE",
    "engine": "AZURE",
    "textFormat": "TEXT",
    "text": "Hello, this is a notification from Webex Connect."
  },
  "correlationId": "case-123",
  "callbackUrl": "https://example.com/webexconnect/voice",
  "callbackUrlAuthId": "AUTH_ID"
}
```

## Key Patterns

- Use `audio.type: "TTS"` for text-to-speech and validate voice/language support.
- Use `textFormat: "SSML"` only with valid SSML.
- Use prerecorded media or media URL patterns when the docs for that voice use case require them.
- Persist call IDs and `correlationId` for status and recording reconciliation.
- Keep callback responses fast and idempotent for programmable voice flows.

## Setup Preflight

Before any live API request, require the project `.env` and the endpoint and credential variables documented for this API family in `webex-connect-setup`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`; never ask the user to repeat configured values or echo secrets.

## CANNOT

- Cannot place calls from a non-voice-enabled `callerId`.
- Cannot assume acceptance means the call was answered.
- Cannot retrieve recordings unless recording was requested or configured.
- Cannot control interactive call flow without a reachable callback URL.
- Cannot use Messaging API v1 channel payloads for Voice API v1.

## Source Links

- https://developers.webexconnect.io/reference/voice-only-api-v1-make-outbound-calls
- https://developers.webexconnect.io/reference/voice-only-api-v1-programmable-voice-api
- https://developers.webexconnect.io/reference/send-message-api-v2-make-voice-call

## Next Skills

- Webhooks/callbacks: `webexconnect-webhooks-events`
- Connection and authentication: `webex-connect-setup`
- Sandbox: `webexconnect-sandbox`
