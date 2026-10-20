---
name: send-webex-connect-message
description: Select the correct Webex Connect channel skill and build a production-ready send-message request.
---

Start with `$webexconnect-sendmessage` as the single front door. It must select
the API family, load exactly one channel adapter, and add shared skills only
when the request needs them.

Route to the relevant Webex Connect channel adapter:

- `webexconnect-sms-sendmessage`
- `webexconnect-mms-sendmessage`
- `webexconnect-rcs-sendmessage`
- `webexconnect-email-sendmessage`
- `webexconnect-push-sendmessage`
- `webexconnect-livechat-inapp-sendmessage`
- `webexconnect-apple-messages-for-business-sendmessage`
- `webexconnect-facebook-messenger-sendmessage`
- `webexconnect-whatsapp-sendmessage`
- `webexconnect-voice-sendmessage`

For every send, confirm required identifiers, sender assets, recipient
identifiers, regional host, authentication, callback URLs, consent/contact
policy requirements, and sandbox limitations before producing code. Use
`webex-connect-setup` for tenant setup, host, and authentication details, add
`webexconnect-contact-policy` for consent or frequency caps, and add
`webexconnect-webhooks-events` for delivery or inbound event handling. Return a
runnable request example and list any setup steps that remain.
