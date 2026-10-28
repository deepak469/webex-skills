---
name: webexconnect-contact-policy
description: >
  Use Webex Connect Contact Policy APIs to manage consent, opt-in and opt-out, channel checks, frequency caps, and message policy enforcement.
---

## Overview

Contact Policy APIs manage communication preferences and frequency caps. Use
them before sends that must enforce opt-in, opt-out, or group-level frequency
rules.

## Authentication And Host

Use Profile Key authentication with the Contact Policy host:

```text
https://contactpolicy.{region}.webexconnect.io
```

## Send Payload Pattern

Many outbound channel payloads support a `contactPolicy` block:

```json
{
  "contactPolicy": {
    "contactPolicyGroup": "GROUP_ID",
    "channelCheckConsent": true,
    "channelApplyFrequencyCap": true
  }
}
```

Set at least one of `channelCheckConsent` or `channelApplyFrequencyCap` to true
when using the block. The group must exist and be enabled for the intended
channel.

## Contact Policy Workflow

1. Confirm Contact Policy is enabled for the tenant.
2. Create or identify a consent group for the communication type.
3. Add or update consumer consent.
4. Verify consent and increment counters before send when needed.
5. Include `contactPolicy` in supported send payloads for platform-side checks.
6. Store opt-out events and keep application state synchronized.

## Setup Preflight

Before a live Contact Policy API call, require `WEBEX_CONNECT_CONTACT_POLICY_BASE` and `WEBEX_CONNECT_PROFILE_KEY` from the project `.env`. If the file or a required value is missing, stop and ask the user to run `webex-connect-setup`. Never echo credential values.

## CANNOT

- Cannot use Service Key for Contact Policy APIs; use Profile Key.
- Cannot apply channel consent checks without a valid consent group.
- Cannot enforce frequency caps unless group caps are configured.
- Cannot treat Contact Policy as a substitute for channel-specific legal requirements.
- Cannot ignore opt-out events received through inbound messages or webhooks.

## Source Links

- https://developers.webexconnect.io/reference/contact-policy-create-a-new-consent-group
- https://developers.webexconnect.io/reference/contact-policy-add-or-update-consent
- https://developers.webexconnect.io/reference/contact-policy-error-codes
- https://developers.webexconnect.io/reference/send-sms-message-api-v2

## Next Skills

- Connection and authentication: `webex-connect-setup`
- Webhooks and opt-outs: `webexconnect-webhooks-events`
- Outbound sends: `webexconnect-sendmessage`
