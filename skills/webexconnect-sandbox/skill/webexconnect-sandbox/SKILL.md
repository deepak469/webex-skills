---
name: webexconnect-sandbox
description: >
  Configure and use the Webex Connect Sandbox for supported SMS, Voice, or WhatsApp API tests, verified recipients, and sandbox-specific limits.
---

## Overview

Use sandbox for quick proofs of concept and payload validation. Do not use
sandbox success as proof that production sender assets, templates, throughput,
or carrier reach are ready.

## Supported Areas

The API overview lists sandbox sections for SMS APIs and SDKs, Voice APIs and
SDKs, WhatsApp APIs and SDKs, SMS/Voice support, and sandbox rate limits.

## Sandbox Checklist

1. Confirm the sandbox endpoint and service key from the current tenant.
2. Use sandbox-specific SMS, Voice, or WhatsApp docs for the first request.
3. Configure callback URLs before testing delivery or call progress.
4. Keep test recipient numbers and WhatsApp participants separate from production data.
5. Validate payload shape in sandbox, then re-check production prerequisites before launch.

## Setup Preflight

Before a Sandbox API call, require a Sandbox `.env` with the explicitly selected environment and the channel credential/endpoint documented for that Sandbox operation. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`. Never use Production credentials or MCP authentication for Sandbox.

## CANNOT

- Cannot assume every production channel feature exists in sandbox.
- Cannot use sandbox TPS or rate limits to size production traffic.
- Cannot prove WhatsApp template approval, RCS carrier approval, or MMS tenant enablement through sandbox alone.
- Cannot commit sandbox keys or test customer identifiers.
- Cannot skip production webhook and Contact Policy testing after sandbox validation.

## Source Links

- https://developers.webexconnect.io/reference/sandbox-apis-overview
- https://developers.webexconnect.io/reference/sms-and-voice-support-in-sandbox
- https://developers.webexconnect.io/reference/sandbox-rate-limits-and-throughput
- https://developers.webexconnect.io/reference/apioverview

## Next Skills

- SMS: `webexconnect-sms-sendmessage`
- WhatsApp: `webexconnect-whatsapp-sendmessage`
- Voice: `webexconnect-voice-sendmessage`
- Setup and API connection: `webex-connect-setup`
