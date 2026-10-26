---
name: webex-connect-setup
description: >
  Configure Webex Connect Sandbox or Production tenant access, regional API endpoints, credentials, Digital Asset API prerequisites, and the region-matched Production SMS/Email MCP in a local .env or secure MCP host. Use before API-backed workflows when setup is missing or incomplete; SDK app and widget builders do not require this setup.
---

# Webex Connect Setup

## What Webex Connect Is

Webex Connect is Cisco's tenant-based communications platform for connecting
business applications to digital customer channels. It supports channels such
as SMS, MMS, RCS, WhatsApp, Email, Push, Live Chat/In-App, Apple Messages for
Business, Facebook Messenger, and Voice through APIs, SDKs, and webhooks.

The main building blocks are:

- **Tenant:** the organization's Webex Connect environment and regional home.
- **Service:** a logical workspace that provides API credentials, channel
  configuration, sender or app assets, flows, and outbound webhook settings.
- **Channel asset:** the sender, phone number, app, domain, business account,
  or caller ID required by a specific channel.
- **API or SDK integration:** server APIs send messages and calls; browser or
  mobile SDKs support interactive Live Chat, In-App Messaging, and Push flows.
- **Callbacks and webhooks:** asynchronous delivery, failure, read, click,
  inbound, and call events used to reconcile the final state.

Sandbox is useful for early payload testing with supported channels and verified
recipients. Production setup is required for approved senders, templates,
compliance, contracted throughput, and real customer traffic.

## Overview

Use this for one-time Webex Connect setup and reusable API connection guidance
before invoking channel-specific APIs. The goal is to identify the right
environment, region, endpoint, credentials, service, sender assets, and
callback path, then apply the correct authentication, throughput, and async
response rules.

For exact source links and current UI pages, read `references/live-docs.md`.

## Shared Configuration Contract

The setup skill owns the reusable local `.env` for this project. Before any
API-backed Webex Connect skill runs, it must locate and check that file without
printing its contents. If it is missing, stop and ask the user to run
`webex-connect-setup`. If a required value is missing, return to this skill
instead of asking the user to repeat setup details in every channel workflow.
Android, iOS, and browser widget builders use SDK configuration and are exempt
from this `.env` preflight.

Use the bundled `scripts/ensure_env.py` to create or extend `.env`. When the
user confirms an environment and region, pass both values to the utility so it
resolves all supported non-secret regional endpoints. It preserves existing
and unrelated entries, adds missing keys from the bundled environment
template, restricts file permissions to the current user, and never prints
values. Do not populate credentials with guessed, sample, or placeholder
values in `.env`.

Direct API credentials belong in the local `.env` or an approved secret
manager. Do not ask users to paste credentials into normal chat. Tell users to
enter any missing secrets directly into their local `.env` or host secret
store, then validate only whether each required value is present; never echo,
log, or include secret values in generated files or setup summaries.

### SMS and Email MCP Authentication

Webex MCP Messaging for AI Agents supports non-templated SMS and Email using an
OAuth 2.0 access token generated from Integration App credentials with the
`spark:mcp` scope. This is separate from Service Key/JWT direct API
authentication. The local `.env.example` includes dedicated MCP credential
slots, but a project `.env` is not automatically loaded by every Codex, Claude,
or Cursor MCP host. Use the host's documented secure credential configuration
or documented environment-variable wiring. Never put credentials in plugin
manifests, skill files, archives, or chat. Do not claim that writing `.env`
alone authenticated the MCP server. Sandbox workflows use Sandbox APIs and do
  not use the Production MCP server.

### Regional Production MCP server

Select the environment and tenant region before configuring MCP. Configure MCP
only when the user selects **Production** and explicitly requests SMS, Email,
or sender discovery through MCP. Use the exact server URL from this table; do
not derive it from the Webex Connect API host or select a default region.

| Webex Connect region | Production MCP server URL |
| --- | --- |
| `ca` (AWS Canada) | `https://agentic-server-platform.prodca1.ciscoccservice.com/mcp/cpaas` |
| `eu` (AWS Ireland) | `https://agentic-server-platform.prodeu2.ciscoccservice.com/mcp/cpaas` |
| `uk` (AWS London) | `https://agentic-server-platform.prodeu1.ciscoccservice.com/mcp/cpaas` |
| `us` (US) | `https://agentic-server-platform.produs1.ciscoccservice.com/mcp/cpaas` |
| `in` (AWS Mumbai) | `https://agentic-server-platform.prodin1.ciscoccservice.com/mcp/cpaas` |
| `au` (AWS Sydney) | `https://agentic-server-platform.prodanz1.ciscoccservice.com/mcp/cpaas` |
| `sg` (AWS Singapore) | `https://agentic-server-platform.prodsg1.ciscoccservice.com/mcp/cpaas` |

The current MCP documentation does not publish a Sandbox endpoint. For
Sandbox, leave MCP unconfigured and use the supported Sandbox APIs. If a
Production tenant region is not in the table, stop and ask the user to verify
the region and consult the current MCP documentation; never guess an endpoint.

The MCP server must be enabled by the organization's administrator in Webex
Control Hub, enabled in Webex Connect Tenant Settings, and assigned approved
SMS or Email use cases and sender assets before sender discovery or sending.
The documented MCP tools are `webex-sender-ids`, `webex-sms-message`, and
`webex-email-message`.

After the user selects a supported Production region, save the non-secret
endpoint as `WEBEX_CONNECT_MCP_SERVER_URL` and automatically configure the
selected AI host with that URL as part of the one-time setup. Do not wait for a
later SMS or Email request to register MCP. Ask only for the bearer token after
registration, and collect it through the host's secure authentication flow.
Never write a real token into the skill, plugin, release archive, or committed
`.env`. A user may leave MCP unauthenticated if they will use direct APIs, but
the region-matched MCP endpoint is still registered during Production setup.

Use the bundled installer to register the endpoint for the active host. It
writes only the regional URL and preserves any existing authentication fields:

```bash
python3 /path/to/webex-connect-setup/scripts/install_mcp.py \
  --environment production --region in --client codex
```

Use `--client claude` for Claude Code or `--client cursor` for Cursor. Run the
installer automatically after the user confirms Production and the region.
The installer refuses Sandbox and refuses regions not published in the table.
After registration, ask the user to add only the bearer token through the
host's secure MCP authentication flow and verify the server connection. Never
add a token as a command-line argument or echo it in setup output.

## Quickstart

1. Ask the user to choose exactly one environment before giving or executing setup instructions. Do not assume or silently default to Sandbox or Production. If the user has not explicitly selected an environment, ask: `Should I set up Sandbox or Production?`
2. Follow only the selected branch:
   - **Sandbox:** sign up at `https://sandbox.imiconnect.io/self-sign-up` with a business email address, verify email, and verify or register a phone number. Use only supported sandbox channels and verified recipients.
   - **Production:** obtain the tenant URL and owner/admin access from the Cisco/Webex provisioning path or account team. Configure direct API credentials in `.env`; configure the MCP bearer token through the selected host's secure mechanism after the endpoint is registered. Confirm sender assets, channel onboarding, compliance, and throughput prerequisites before sending traffic.
3. Ask for the tenant URL and region. If the URL is `https://tenantname.in.webexconnect.io`, show `in` as the inferred region and ask the user to confirm it; never silently choose a region. For Production, resolve and register the matching MCP server URL from the regional table during this setup. Do not configure MCP for Sandbox.
4. Create a Service from the Webex Connect home page.
5. In the Service API tab, copy either the Service Key or configure service-specific JWT credentials.
6. If using Profile or Contact Policy APIs, copy the Profile Key from Tenant Settings.
7. Configure at least one sender asset or channel app before sending messages. For Production, do not proceed until the required channel and compliance prerequisites are complete.
8. Create or update the user's project `.env` with the bundled `scripts/ensure_env.py`. Set the explicitly selected environment, normalized tenant domain, organization ID when supplied, region, all endpoint values verified from current official references, and the matching `WEBEX_CONNECT_MCP_SERVER_URL` for Production. Preserve existing values unless the user explicitly changes them. Leave unconfigured credentials blank; direct the user to enter missing direct-API secrets locally. `.env` is ignored by Git and is not included in plugin archives.

   For example:

   ```bash
   python3 /path/to/webex-connect-setup/scripts/ensure_env.py \
     --env-file .env --environment production --region us \
     --set WEBEX_CONNECT_TENANT_DOMAIN=tenantname.us.webexconnect.io \
     --set WEBEX_CONNECT_ORGANIZATION_ID=YOUR_ORGANIZATION_ID
   ```

9. Complete the one-time credential pass locally. The setup skill must show
which credential fields are required for the user's intended workflows and
must not request endpoint URLs again. The user enters direct API secrets into
the local owner-only `.env`; the user enters only the MCP bearer token through
the active MCP host's secure authentication flow. Do not ask for a Service
Key, JWT, Profile Key, or Digital Asset token again during a send when the
setup preflight confirms that it is present.

The bundled `assets/env.example` is the complete variable list. It contains no
credentials and is copied by the setup utility. Resolve host values from the
current endpoint reference rather than copying sample URLs into a different
tenant or environment. Keep unused credential fields blank.

9. Send a minimal test request only after the sender asset and destination rules are ready and the user explicitly confirms the test. Do not run this test during setup automatically:

```bash
curl -X POST "$WEBEX_CONNECT_API_BASE/v2/messages" \
  -H "Content-Type: application/json" \
  -H "key: $WEBEX_CONNECT_SERVICE_KEY" \
  -d '{
    "channel": "sms",
    "from": "SENDER_ID_OR_NUMBER",
    "to": [
      {
        "msisdn": ["+15551234567"],
        "correlationId": "setup-test-001"
      }
    ],
    "content": {
      "type": "text",
      "text": "Webex Connect setup test"
    },
    "requestedReceipts": ["SUBMITTED", "DELIVERED", "FAILED"],
    "callbackData": "setup-test-001"
  }'
```

Treat a successful response as API acceptance, not final delivery. Use callbacks, outbound webhooks, or message status APIs for the final state.

## Environment Choice

| Need | Use |
| --- | --- |
| Try SMS, Voice, WhatsApp, Custom Event API, or inbound webhooks without a production tenant | Sandbox |
| Configure real sender IDs, phone numbers, compliance, throughput, and customer traffic | Production tenant |
| Validate channel onboarding, sender approvals, Contact Policy, Profile, or full production limits | Production tenant |

Sandbox recipients are limited to verified phone numbers. Up to 5 numbers can be registered, all from the same country as the first registered number.

## Tenant and Region Setup

Start from the tenant URL. For `tenantname.in.webexconnect.io`, the region is `in`, and the Messaging, Voice, RCS, Event, and Profile API base is:

```text
https://api.in.webexconnect.io
```

Known current region codes include `ca`, `eu`, `uk`, `us`, `in`, `au`, and `sg`. If a tenant uses a legacy domain or an unlisted region, use the current endpoint reference instead of guessing.

## Regional API Hosts

Resolve the tenant region before building URLs. Prefer the `webexconnect.io`
hosts shown by the current API reference for the tenant.

After the user confirms the region, run the bundled resolver instead of asking
the user to provide each endpoint separately:

```bash
python3 /path/to/webex-connect-setup/scripts/ensure_env.py \
  --env-file .env --environment production --region in
```

This populates the Messaging API v1 and v2, Voice, Contact Policy, Profile,
Audit Logs, Digital Channel Onboarding, and region-matched Production MCP
values. Webhook receivers remain customer-owned HTTPS URLs; Event and inbound
webhook API calls use the resolved core API base. Sandbox setup records the
selected environment and region, clears the Production MCP URL, and does not
copy Production API endpoints into the file.

| API family | Host pattern |
| --- | --- |
| Messaging API v2, RCS, Voice, Event, Profile | `https://api.{region}.webexconnect.io` |
| Messaging API v1 channel resources | `https://api.{region}.webexconnect.io/resources/v1/messaging` |
| Contact Policy | `https://contactpolicy.{region}.webexconnect.io` |
| User Audit Logs | `https://{region}.webexconnect.io` |
| Digital Channel Onboarding APIs | Use the full regional base shown in the Digital Asset API endpoint reference; it has a separate host family. |

## Setup Output Contract

When this skill is used before a send-message, SDK, webhook, Contact Policy, or
thread workflow, produce a setup record that downstream Webex Connect skills can
reuse instead of rediscovering or inventing connection details.

Minimum setup fields:

| Field | Environment variable | Used by |
| --- | --- | --- |
| Selected environment (`sandbox` or `production`) | `WEBEX_CONNECT_ENVIRONMENT` | All setup and downstream workflows |
| Tenant domain | `WEBEX_CONNECT_TENANT_DOMAIN` | UI access, region discovery, setup notes |
| Region code | `WEBEX_CONNECT_REGION` | All regional hosts |
| Core API base | `WEBEX_CONNECT_API_BASE` | Messaging, Voice, Event, Profile |
| Messaging API v2 URL | `WEBEX_CONNECT_MESSAGING_V2_URL` | SMS, MMS, RCS, Email |
| Messaging API v1 URL | `WEBEX_CONNECT_MESSAGING_V1_URL` | Push, Live Chat/In-App, WhatsApp, Messenger, Apple Messages for Business |
| Voice API base | `WEBEX_CONNECT_VOICE_API_BASE` | Voice calls and status |
| Contact Policy base | `WEBEX_CONNECT_CONTACT_POLICY_BASE` | Consent and frequency-cap APIs |
| Profile API base | `WEBEX_CONNECT_PROFILE_API_BASE` | Profile API v2 |
| Audit Logs base | `WEBEX_CONNECT_AUDIT_LOGS_BASE` | User Audit Logs API |
| Digital Asset API base | `WEBEX_CONNECT_DIGITAL_ASSET_API_BASE` | Chat, Email, Messenger, and WhatsApp asset onboarding |
| Organization ID | `WEBEX_CONNECT_ORGANIZATION_ID` | Digital Asset API `x-organization-id` header |
| Service Key | `WEBEX_CONNECT_SERVICE_KEY` | Messaging, Event, Voice, Inbound Webhooks, RCS lookup |
| Service JWT | `WEBEX_CONNECT_SERVICE_JWT` | Messaging, Event, Voice, Inbound Webhooks, RCS lookup |
| Profile Key | `WEBEX_CONNECT_PROFILE_KEY` | Profile API v2 and Contact Policy |
| Digital Asset personal access token | `WEBEX_CONNECT_DIGITAL_ASSET_ACCESS_TOKEN` | Digital Asset API operations |
| Production MCP server URL | `WEBEX_CONNECT_MCP_SERVER_URL` | Region-matched SMS/Email MCP host; blank for Sandbox |
| Email asset provider config | `WEBEX_CONNECT_EMAIL_*` | Mailbox, SMTP, and OAuth values only when the selected Email schema requires them |
| MCP OAuth access token | `WEBEX_CONNECT_MCP_ACCESS_TOKEN` | SMS/Email MCP tools with `spark:mcp`; host wiring is separate |
| MCP Integration App ID/secret | `WEBEX_CONNECT_MCP_CLIENT_ID`, `WEBEX_CONNECT_MCP_CLIENT_SECRET` | Optional only when a specific MCP host requires client-based OAuth; not required for bearer-token setup |
| Webhook Hub Secret | `WEBEX_CONNECT_HUB_SECRET` | Verify signed outbound webhook callbacks |
| Callback URL Auth ID | `WEBEX_CONNECT_CALLBACK_URL_AUTH_ID` | Voice callback authentication when required |
| Audit Logs access token | `WEBEX_CONNECT_AUDIT_LOGS_ACCESS_TOKEN` | Cisco Webex Common Identity authentication when the API flow requires it |

The setup record may include the `.env` path, service name, service ID,
credential type, sender asset, callback URL, and throughput assumptions, but
must never include credential values. Treat blank fields as setup gaps; direct
API skills must stop and route back to setup when a required value is missing.
For MCP work, verify both that the configured MCP host is available and that
the user has completed its documented authentication flow; `.env` presence
alone does not prove MCP authentication.

Downstream skills must use these values when present. After setup is complete,
they must not ask the user to repeat the endpoint, Service Key, JWT, Profile
Key, Digital Asset token, or MCP server URL. They should collect only the
business inputs for the requested operation, such as channel, sender, target,
content, and confirmation. If a required field is genuinely missing, pause
and route back to this skill rather than guessing or silently asking for a
different endpoint. Do not hardcode a region, tenant host, Service Key, JWT,
Profile Key, sender, app ID, or callback URL in generated code.

## Credentials

| Credential | Where to find it | Use for |
| --- | --- | --- |
| Service Key | Service > API tab | Messaging API, Custom Event API, Inbound Webhooks, RCS Capability Lookup |
| Service-specific JWT | Service > API tab | Messaging API, Custom Event API, Inbound Webhooks, RCS Capability Lookup |
| Profile Key | Tenant Settings | Profile API v2 and Contact Policy APIs |
| Digital Asset personal access token | Webex Developer Portal user account | Digital Asset API; also requires organization ID and asset permissions |
| MCP OAuth access token | Integration App/MCP client, `spark:mcp` scope | SMS and Email MCP tools; separate from direct API credentials |
| Hub Secret | Webex Connect outbound webhook configuration | HMAC verification of outbound webhook notifications |
| Cisco Webex identity token | Cisco Webex Common Identity flow | User Audit Logs API |

If both JWT and Service Key are present in one API request, JWT takes priority. Store direct API secrets in the ignored local `.env` or a secret manager. Use the MCP host's secure OAuth configuration for MCP authentication unless that host documents a safe environment-variable integration.

| API family | Credential |
| --- | --- |
| Messaging API v1/v2 | Service Key or service-specific JWT |
| Voice API v1 | Service Key or service-specific JWT |
| Event API v1 / Inbound Webhooks | Service Key or service-specific JWT |
| RCS Capability Lookup | Service Key or service-specific JWT |
| Contact Policy APIs / Profile API v2 | Profile Key |
| Digital Asset API | Webex personal access token + `x-organization-id` |
| SMS/Email MCP tools | Region-matched MCP URL plus OAuth 2.0 access token with `spark:mcp` configured in the MCP client |
| User Audit Logs API | Cisco Webex Common Identity |

## API Request Checklist

1. Resolve the regional host from the tenant.
2. Choose the API family and matching credential type.
3. Store secrets in environment variables or a secret manager.
4. Include `correlationId`, `correlationid`, and `callbackData` where supported.
5. Configure `notifyUrl`, `notifyurl`, or `callbackUrl` before relying on final status.
6. Queue requests within tenant and channel TPS limits.
7. Persist accepted message or call IDs and reconcile final state from callbacks.

## Async Response Model

Most Webex Connect communication APIs are asynchronous. The HTTP response
usually means accepted, queued, or rejected. Delivery, read, click, call, and
failure outcomes arrive later through notify URLs, outbound webhooks, callbacks,
or data streams.

## Service Setup

Create one Service per logical workspace or customer journey. A Service is where Webex Connect exposes the API credentials, outbound webhook configuration, flow builder, rules, and channel assets for that workspace.

Before sending traffic:

1. Name the Service after the use case, team, or tenant boundary.
2. Configure sender assets or app assets for the target channel.
3. Add outbound webhook or `notifyUrl` handling for delivery results.
4. Confirm the user can view masked credentials. Tenant owners, full access users, and limited access users can view Service Key and JWT credentials.
5. Keep a setup record with tenant domain, region, service name, service ID if used, credential type, sender asset, callback URL, and throughput assumptions.

## Product Enablement

| Capability | Setup checkpoint |
| --- | --- |
| SMS or Voice | Get a phone number, sender ID, short code, or approved regional sender asset as required. |
| Email | Configure an Email app and verify the sending domain before sending. |
| RCS | Complete chatbot/operator onboarding before attempting live sends. |
| WhatsApp | Complete WhatsApp onboarding and template setup before proactive sends. |
| Push, In-App, Live Chat | Configure the channel app asset and use the relevant SDK setup. |
| Contact Policy | Confirm the Contact Policy app is enabled and use Profile Key authentication. |
| Webex AI Agent Studio | Confirm the tenant has the app and complete its product setup before designing agent flows. |
| Outbound webhooks | Configure webhook endpoint, optional auth, and idempotent event handling. |

## Postman Setup

Use the official Postman collection for first validation when possible. Change the regional base URL to the tenant region and set one authentication method:

```text
key: <Service Key>
```

or:

```text
Authorization: Bearer <JWT>
```

Do not send both unless intentionally testing JWT priority.

## CANNOT

- Cannot assume a production tenant is self-service or API-created. Production access is provisioned through the Webex/Cisco account path.
- Cannot use sandbox as proof that production sender assets, compliance, channel approvals, or throughput are ready.
- Cannot send sandbox messages or calls to arbitrary unverified recipients.
- Cannot use one credential for every API family. Messaging uses Service Key or service-specific JWT; Profile and Contact Policy use Profile Key.
- Cannot use one host for every API family. Contact Policy and Audit Logs use separate host patterns.
- Cannot configure the Production MCP server before the environment and tenant region are selected.
- Cannot configure the Production MCP server for Sandbox or guess an MCP URL for an unlisted region.
- Cannot treat HTTP acceptance as delivery success.
- Cannot assume sandbox throughput or channel coverage matches production.
- Cannot send production messages until channel assets and regional compliance prerequisites are complete.
- Cannot hardcode Service Keys, JWT secrets, Profile Keys, sender assets, or tenant URLs in source code.

## Source Links

- https://help.webexconnect.io/docs/accessing-the-product
- https://help.webexconnect.io/docs/create-a-service
- https://help.webexconnect.io/docs/service-key-and-jwt-authentication-tokens
- https://help.webexconnect.io/docs/tenant-settings
- https://developers.webexconnect.io/reference/apioverview
- https://developers.webexconnect.io/reference/know-your-api-endpoints
- https://developers.webexconnect.io/reference/api-authentication
- https://developers.webexconnect.io/reference/postman-collection
- https://developer.webex.com/mcp/docs/connect-mcp-server

## Next Skills

- Outbound messaging: `webexconnect-sendmessage`
- Digital Asset lifecycle: `webexconnect-digital-asset-creation`
- Sandbox testing: `webexconnect-sandbox`
- Channel adapters: use the adapter selected by `webexconnect-sendmessage`
- WhatsApp setup and templates: `webexconnect-whatsapp-sendmessage`
- Voice calls: `webexconnect-voice-sendmessage`
- Webhooks and callbacks: `webexconnect-webhooks-events`
- Consent and frequency caps: `webexconnect-contact-policy`
