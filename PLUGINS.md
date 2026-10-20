# webex-skills

Available plugin bundles and their skills. Generated from plugin manifests and `SKILL.md` frontmatter; edit the source files and run `npm run catalog:generate`.

## Webex Connect AI (0.2.39)

Webex Connect AI skills for digital-asset lifecycle operations, digital-channel messaging, live chat widgets, Android and iOS push plus in-app messaging demos, setup workflows, and production-ready API integrations.

Surfaces: Claude Code, Codex, Cursor

| Skill | Description |
| --- | --- |
| [`webex-connect-setup`](<plugins/webex-connect-ai/skills/webex-connect-setup/SKILL.md>) | Configure Webex Connect Sandbox or Production tenant access, regional API endpoints, credentials, Digital Asset API prerequisites, and the region-matched Production SMS/Email MCP in a local .env or secure MCP host. Use before API-backed workflows when setup is missing or incomplete; SDK app and widget builders do not require this setup. |
| [`webexconnect-android-push-inapp-messaging-builder`](<plugins/webex-connect-ai/skills/webexconnect-android-push-inapp-messaging-builder/SKILL.md>) | Build or repair native Android apps that use the Webex Connect SDK for Push Notifications or In-App Messaging, including registration, chat, notifications, and QA. |
| [`webexconnect-apple-messages-for-business-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-apple-messages-for-business-sendmessage/SKILL.md>) | Build and validate Webex Connect Apple Messages for Business API v1 requests for text, rich messages, attachments, callbacks, and delivery handling. |
| [`webexconnect-contact-policy`](<plugins/webex-connect-ai/skills/webexconnect-contact-policy/SKILL.md>) | Use Webex Connect Contact Policy APIs to manage consent, opt-in and opt-out, channel checks, frequency caps, and message policy enforcement. |
| [`webexconnect-digital-asset-creation`](<plugins/webex-connect-ai/skills/webexconnect-digital-asset-creation/SKILL.md>) | Create, retrieve, and update Webex Connect Chat, Email, Facebook Messenger, or WhatsApp digital assets using the documented operation schema, tenant-region routing, and confirmation before mutations. |
| [`webexconnect-email-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-email-sendmessage/SKILL.md>) | Build, validate, or send Webex Connect Email through Send Message API v2 or the configured Email MCP, including sender discovery, recipients, content, callbacks, and receipts. |
| [`webexconnect-facebook-messenger-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-facebook-messenger-sendmessage/SKILL.md>) | Build and validate Webex Connect Facebook Messenger API v1 messages for Page-scoped recipients, text, attachments, interactive replies, and callbacks. |
| [`webexconnect-ios-push-inapp-messaging-builder`](<plugins/webex-connect-ai/skills/webexconnect-ios-push-inapp-messaging-builder/SKILL.md>) | Build or repair native iOS apps that use the Webex Connect SDK for Push Notifications or In-App Messaging, including registration, chat, notifications, and QA. |
| [`webexconnect-livechat-inapp-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-livechat-inapp-sendmessage/SKILL.md>) | Build and validate Webex Connect Messaging API v1 requests for Live Chat, In-App Messaging, notifications, threads, and callbacks. |
| [`webexconnect-livechat-widget`](<plugins/webex-connect-ai/skills/webexconnect-livechat-widget/SKILL.md>) | Build or troubleshoot a browser Live Chat widget using the Webex Connect JavaScript SDK, including setup, registration, threads, messaging, and events. |
| [`webexconnect-mms-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-mms-sendmessage/SKILL.md>) | Build and validate Webex Connect MMS Send Message API v2 requests for recipients, attachments, fallback text, receipts, and callbacks. |
| [`webexconnect-push-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-push-sendmessage/SKILL.md>) | Build and validate Webex Connect Push Messaging API v1 requests for registered users and devices, platform payloads, notifications, and callbacks. |
| [`webexconnect-rcs-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-rcs-sendmessage/SKILL.md>) | Build and validate Webex Connect RCS Send Message API v2 requests for capability checks, rich content, templates, and SMS fallback. |
| [`webexconnect-sandbox`](<plugins/webex-connect-ai/skills/webexconnect-sandbox/SKILL.md>) | Configure and use the Webex Connect Sandbox for supported SMS, Voice, or WhatsApp API tests, verified recipients, and sandbox-specific limits. |
| [`webexconnect-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-sendmessage/SKILL.md>) | Route an outbound Webex Connect message to the correct channel skill and API family, using shared setup, Contact Policy, and webhook guidance when required. |
| [`webexconnect-sms-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-sms-sendmessage/SKILL.md>) | Build, validate, or send Webex Connect SMS through Send Message API v2 or the configured SMS MCP, including sender discovery, recipients, scheduling, receipts, and callbacks. |
| [`webexconnect-voice-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-voice-sendmessage/SKILL.md>) | Build and validate Webex Connect Voice API v1 and documented Send Message API v2 voice requests for outbound calls, text-to-speech, media, callbacks, and call status. |
| [`webexconnect-webhooks-events`](<plugins/webex-connect-ai/skills/webexconnect-webhooks-events/SKILL.md>) | Build and troubleshoot Webex Connect webhook receivers, callback verification, inbound events, Event API requests, retries, and data streams. |
| [`webexconnect-whatsapp-sendmessage`](<plugins/webex-connect-ai/skills/webexconnect-whatsapp-sendmessage/SKILL.md>) | Build and validate Webex Connect WhatsApp API v1 messages for session replies, approved templates, media, interactive content, and callbacks. |
