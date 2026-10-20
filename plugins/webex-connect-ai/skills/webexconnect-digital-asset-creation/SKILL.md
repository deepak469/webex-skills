---
name: webexconnect-digital-asset-creation
description: >
  Create, retrieve, and update Webex Connect Chat, Email, Facebook Messenger, or WhatsApp digital assets using the documented operation schema, tenant-region routing, and confirmation before mutations.
---

## Overview

This skill is the interactive entry point for Webex Connect digital-asset
lifecycle operations. It supports create, get, and update operations across
four Digital Asset API branches:

- **Chat asset** for Web, Mobile, or both, including Live Chat/In-App Messaging
  configuration.
- **Email asset** for SMTP/OAuth-based email configuration.
- **Facebook Messenger asset** for the Messenger channel (`channel=fb`,
  `channelId=5`).
- **WhatsApp asset** for the WhatsApp Business channel (`channel=wa`,
  `channelId=8`).

Keep all four branches separate. Their fields, validation, provider
credentials, and API schemas are not interchangeable. The channel-specific
messaging skills send through an existing asset; this skill manages the asset
configuration itself.

## Interactive Entry Point

When the user invokes this skill without naming an operation, ask this exact
choice before collecting configuration:

> What do you want to do: Create, Get, or Update a digital asset?

Do not select a default. If the user names an asset type but not the operation,
ask for the operation before collecting fields. If the user names the
operation but not the asset type, ask this exact choice:

> Which asset type: Chat, Email, Facebook Messenger, or WhatsApp?

Present the choices as `Create`, `Get`, and `Update`, and as `Chat asset`,
`Email asset`, `Facebook Messenger asset`, and `WhatsApp asset`. Do not select
a default. If the user clearly names both, continue without asking again.

Then ask for the Webex Connect tenant URL if it is not already available. The
tenant URL is required for region and environment resolution. If the URL does
not unambiguously identify Sandbox or Production, ask the user to choose the
environment; never silently use Sandbox.

## Tenant URL and Regional Routing

1. Normalize the supplied URL and extract its hostname. Preserve the full
   tenant URL in the request context, but never put credentials or secrets in
   it.
2. Resolve the region using the current Webex Connect **Know Your API
   Endpoints** reference. Examples include `tenant.ca.webexconnect.io` to
   `api.ca.webexconnect.io` and `tenant.eu.webexconnect.io` to
   `api.eu.webexconnect.io`.
3. Use the exact Digital Asset API host and path published by the selected live
   operation reference. The Messaging API hosts (`/v2/messages` and
   `/resources/v1/messaging`) are not Digital Asset API endpoints.
4. If the hostname is legacy, malformed, or not in the endpoint reference,
   stop and ask for the correct tenant URL or region. Do not guess.

## Shared Asset Fields and Channel Routing

All four Digital Asset API references use the regional Digital Channel
Onboarding API base URL and expose create, retrieve, and update-style asset
operations. Before constructing a request:

- collect the common asset fields required by the selected operation, such as
  asset name, description, assignment, flow/service mapping, and channel;
- route the channel value exactly as documented: `app` for Chat, `email` for
  Email, `fb` for Facebook Messenger, or `wa` for WhatsApp;
- retain `channelId=5` for Facebook Messenger and `channelId=8` for WhatsApp
  when the operation requires the channel identifier;
- select the exact operation reference for the requested channel and action
  (`create`, `get`, or `update`) before collecting or constructing anything;
- read that operation page for the exact method, path, query parameters,
  headers, required body fields, enums, and response schema; and
- never copy provider fields from one branch into another.

The public Messenger and WhatsApp reference pages identify the shared asset
create/update/get operations and channel identifiers. The exact operation links
are listed in [Operation References](#operation-references).

## Strict Operation-Schema Boundary

The selected operation page is the sole allowlist for the request. The agent
must:

- use only the documented HTTP method, path, query parameters, headers,
  request-body properties, nested properties, enum values, formats, and
  conditional requirements for that exact channel and operation;
- use only identifiers documented by that operation for `get` or `update`,
  and never invent an asset ID, channel ID, query parameter, or body field;
- validate the final request keys against the selected operation schema before
  confirmation, including nested objects and arrays;
- omit optional fields that the user did not provide unless the operation
  explicitly requires them; and
- stop with a blocked/draft result if the operation schema is unavailable, a
  requested value cannot be mapped exactly, or any generated key is not
  explicitly supported.

The agent must not borrow fields from another channel, another operation,
Send Message APIs, SDK examples, Control Hub forms, remembered payloads, or
provider conventions. A conversational prompt such as “assignment,” “flow,”
“protocol,” or “credentials” is not permission to add a field: include it only
when the selected operation documents that exact field at that exact location.
The same rule applies to response handling: report only fields documented by
the selected operation's response schema.

## Credentials and Operation Gate

- Use the documented Digital Asset API for the selected operation. Require
  `WEBEX_CONNECT_DIGITAL_ASSET_API_BASE`,
  `WEBEX_CONNECT_DIGITAL_ASSET_ACCESS_TOKEN`, and
  `WEBEX_CONNECT_ORGANIZATION_ID` from the project `.env` prepared by
  `webex-connect-setup`.
- For Email provider configuration, reuse only the relevant local
  `WEBEX_CONNECT_EMAIL_*` values when the selected API schema requires them.
  Never place access tokens, OAuth client secrets, refresh tokens, private
  keys, or tenant-specific identifiers in the skill package, generated
  examples, repository, or normal chat output.
- Do not ask for API credentials in chat. If a required value is missing, stop
  and route to `webex-connect-setup` for local configuration.
- Create and update are external mutations. Before calling either operation,
  show a redacted summary containing asset type, operation,
  tenant/environment, resolved region, identifier when applicable, and
  channel-specific settings, then ask for explicit confirmation. Get is
  read-only and does not require mutation confirmation. A draft or payload
  request must not create or update an asset.
- Treat only a documented successful response as proof of the selected
  operation. Report documented identifiers and generated App ID or Client Key
  when returned, but never report secret values.

## Chat Asset Branch

Read the exact Chat create/get/update operation reference before constructing
the request. The following are conversation topics only; they are not a fixed
payload schema. Ask for a topic only when the selected operation documents the
corresponding field and requires it or the user wants to set it:

- asset name and optional description;
- assignment, normally Webex Connect when that is the user's stated target;
- platform: Web, Mobile, or Both;
- for Mobile: Android, iOS, or Both, only when represented by fields in the
  selected schema;
- experience: Live Chat, In-App Messaging, or another supported option, only
  when represented by fields in the selected schema;
- transport configuration exactly as documented (for example, a documented
  fallback protocol string); do not split it into invented primary/secondary
  fields;
- secured-port and payload-encryption fields only when the selected schema
  documents them;
- push configuration for the selected mobile platforms, if enabled;
- JWT settings when enabled, using only the documented public-key fields and
  constraints; never request private keys;
- multi-user registration, single-device behavior, server-side inbox/data
  stream, and service/flow mapping when applicable.

Validate the platform-dependent fields before previewing the selected request.
For example, do not collect Android push credentials for a Web-only asset, and
do not claim that a mobile asset is ready until its required platform push and
JWT configuration is complete.

After create or update, tell the user to complete any documented Webex Connect
service/flow configuration and retain generated App ID and Client Key values
for SDK or messaging integrations. For get, report the documented current
configuration. The channel is immutable after creation.

## Email Asset Branch

Read the exact Email create/get/update operation reference before constructing
the request. The following are conversation topics only; they are not a fixed
payload schema. Collect a value only when the selected operation documents the
corresponding field and requires it or the user wants to set it:

- asset name using the documented alphanumeric/no-spaces/no-special-characters
  rule and optional description;
- assignment to the intended Webex Connect service/workload;
- mailbox email address;
- SMTP server, username, and port;
- OAuth client ID and client secret through local `.env` or the host's secret
  manager, using `WEBEX_CONNECT_EMAIL_OAUTH_CLIENT_ID` and
  `WEBEX_CONNECT_EMAIL_OAUTH_CLIENT_SECRET` when those names match the
  configured profile;
- authorization URL, scope, access-token URL, refresh-token URL, and callback
  URL.

For Gmail or Microsoft 365, offer the provider's documented defaults as
editable values, and ask the user to verify tenant-specific client IDs,
consent, scopes, and callback settings. Do not assume another provider is
supported unless the current API reference says so.

Validate the mailbox, URLs, port, callback URL, and required OAuth fields. Do
not echo client secrets or access/refresh tokens in the preview. After a
successful create or update, explain any documented inbound email setup,
forwarding address, or domain/provider consent requirement.

## Facebook Messenger Asset Branch

Read the official [Messenger Digital Asset API reference][messenger-asset-api]
before constructing the request. This branch uses the Facebook Messenger
channel (`channel=fb`, `channelId=5`) and the shared asset create, update, and
get operations documented there.

Collect the common asset fields and only the provider-specific fields marked
required by the selected operation. Route provider credentials, page
identifiers, app identifiers, callback settings, and other secrets through the
secure setup mechanism. Do not assume that a Facebook Page ID, Page access
token, webhook, or app field is required unless the current operation schema
requires it. Never echo access tokens or client secrets in the preview.

Validate the exact channel enums, identifiers, URLs, and provider fields from
the live reference. After create or update, explain the required Facebook
page, permission, webhook, flow, or sender configuration returned by the
operation. For get, report the documented configuration only.

## WhatsApp Asset Branch

Read the official [WhatsApp Digital Asset API reference][whatsapp-asset-api]
before constructing the request. This branch uses the WhatsApp Business
channel (`channel=wa`, `channelId=8`) and the shared asset create, update, and
get operations documented there.

Collect the common asset fields and only the provider-specific fields marked
required by the selected operation. Route provider credentials, business
account identifiers, phone-number identifiers, callback settings, and other
secrets through the secure setup mechanism. Do not assume that a WABA ID,
phone-number ID, access token, webhook, or template field is required unless
the current operation schema requires it. Never echo access tokens or client
secrets in the preview.

Validate the exact channel enums, identifiers, URLs, and provider fields from
the live reference. After create or update, explain the required WhatsApp
Business account, phone-number, sender, webhook, flow, or consent
configuration returned by the operation. For get, report the documented
configuration only.

## Request Construction and Failure Handling

- Use the exact operation reference selected below as the authority for HTTP
  method, path, headers, schema, enum values, and response fields. The
  top-level channel page and Control Hub help pages are navigation or
  configuration guidance, not substitutes for the operation schema.
- Do not copy a Send Message API payload into a Digital Asset API request.
- Before confirmation, produce an internal allowlist check containing the
  selected operation URL and every query, header, and body key that will be
  sent. Reject any key that cannot be found in that operation's documentation.
- If the live reference does not expose the exact selected endpoint or schema
  in the current environment, stop before the API call and provide a clearly
  labeled draft of the collected configuration. Ask for the missing official
  API schema; never invent a path or claim success.
- On validation errors, identify the field and correction without exposing
  secrets. On authorization or region errors, re-check tenant URL, environment,
  credential scope, and resolved host before retrying. Do not retry a create
  blindly because it may create duplicates.

## Output Contract

Return:

- `assetType`: `chat`, `email`, `messenger`, or `whatsapp`;
- channel value and channel ID when the selected operation defines them;
- tenant URL, environment, and resolved region/host;
- a redacted configuration summary;
- the documented endpoint and operation used, when verified;
- operation status and returned asset identifier;
- generated App ID or Client Key only if the API returns them and they are not
  secret values;
- required post-create mapping, provider-consent, SDK, or channel setup steps;
- a clear blocked/draft result when endpoint, schema, credentials, or required
  configuration is unavailable.

## Setup Preflight

For any Digital Asset API operation, require `WEBEX_CONNECT_DIGITAL_ASSET_API_BASE`, `WEBEX_CONNECT_DIGITAL_ASSET_ACCESS_TOKEN`, and `WEBEX_CONNECT_ORGANIZATION_ID` from the project `.env`. If the file or any required value is missing, stop and ask the user to run `webex-connect-setup`. Never echo credential values.

## CANNOT

- Cannot operate on an asset without first determining the operation and
  Chat, Email, Facebook Messenger, or WhatsApp type.
- Cannot silently choose Sandbox, Production, region, assignment, provider, or
  channel-specific defaults that materially change the asset.
- Cannot use a Send Message API endpoint to create a digital asset.
- Cannot guess a Digital Asset API path, payload key, query parameter, header,
  identifier, nested property, or unsupported enum.
- Cannot create or update without a complete preview and explicit user
  confirmation.
- Cannot store, print, commit, or transmit bearer tokens, service keys, JWT
  private keys, client secrets, or refresh tokens in skill content or examples.
- Cannot treat an accepted, partial, or asynchronous response as proof that the
  asset was created and registered successfully.
- This skill does not delete assets. For get/update requests, use only the
  exact documented get/update operation and its schema; do not substitute the
  create operation.

## Source Links

### Operation References

- Chat create: https://developer.webex.com/webex-connect/docs/api/v1/chat-digital-asset-apis-mobile-web-app-channel/create-an-chat-asset
- Chat get: https://developer.webex.com/webex-connect/docs/api/v1/chat-digital-asset-apis-mobile-web-app-channel/get-an-chat-asset
- Chat update: https://developer.webex.com/webex-connect/docs/api/v1/chat-digital-asset-apis-mobile-web-app-channel/update-an-chat-asset
- Email create: https://developer.webex.com/webex-connect/docs/api/v1/email-digital-asset-apis-email-channel/create-an-email-asset
- Email get: https://developer.webex.com/webex-connect/docs/api/v1/email-digital-asset-apis-email-channel/get-an-email-asset
- Email update: https://developer.webex.com/webex-connect/docs/api/v1/email-digital-asset-apis-email-channel/update-an-email-asset
- Facebook Messenger create: https://developer.webex.com/webex-connect/docs/api/v1/messenger-digital-asset-apis-facebook-messenger-channel/create-a-messenger-asset
- Facebook Messenger get: https://developer.webex.com/webex-connect/docs/api/v1/messenger-digital-asset-apis-facebook-messenger-channel/get-a-messenger-asset
- Facebook Messenger update: https://developer.webex.com/webex-connect/docs/api/v1/messenger-digital-asset-apis-facebook-messenger-channel/update-a-messenger-asset
- WhatsApp create: https://developer.webex.com/webex-connect/docs/api/v1/whatsapp-digital-asset-apis-whatsapp-business-channel/create-a-whatsapp-asset
- WhatsApp get: https://developer.webex.com/webex-connect/docs/api/v1/whatsapp-digital-asset-apis-whatsapp-business-channel/get-a-whatsapp-asset
- WhatsApp update: https://developer.webex.com/webex-connect/docs/api/v1/whatsapp-digital-asset-apis-whatsapp-business-channel/update-a-whatsapp-asset

- Chat Digital Asset APIs: https://developer.webex.com/webex-connect/docs/api/v1/chat-digital-asset-apis-mobile-web-app-channel
- Email Digital Asset APIs: https://developer.webex.com/webex-connect/docs/api/v1/email-digital-asset-apis-email-channel
- Messenger Digital Asset APIs: https://developer.webex.com/webex-connect/docs/api/v1/messenger-digital-asset-apis-facebook-messenger-channel
- WhatsApp Digital Asset APIs: https://developer.webex.com/webex-connect/docs/api/v1/whatsapp-digital-asset-apis-whatsapp-business-channel
- Chat asset configuration: https://help.webex.com/article/11dtv5
- Email asset configuration: https://help.webex.com/article/nrelvg3
- Regional endpoints: https://developers.webexconnect.io/reference/know-your-api-endpoints
- API authentication: https://developers.webexconnect.io/reference/api-authentication

## Next Skills

- Tenant and credential setup: `webex-connect-setup`
- Send through a created asset: `webexconnect-sendmessage`
- Chat widget implementation: `webexconnect-livechat-widget`
- Chat/In-App message requests: `webexconnect-livechat-inapp-sendmessage`
- Email message requests: `webexconnect-email-sendmessage`

[messenger-asset-api]: https://developer.webex.com/webex-connect/docs/api/v1/messenger-digital-asset-apis-facebook-messenger-channel
[whatsapp-asset-api]: https://developer.webex.com/webex-connect/docs/api/v1/whatsapp-digital-asset-apis-whatsapp-business-channel
