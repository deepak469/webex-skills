---
name: webexconnect-livechat-widget
description: >
  Build or troubleshoot a browser Live Chat widget using the Webex Connect JavaScript SDK, including setup, registration, threads, messaging, and events.
---

## Overview

Use this skill to create a Webex Connect Live Chat Widget around the JavaScript
SDK, not around the server-side Send Message API. The widget must handle SDK
asset loading, user/device registration, RTM connection state, thread creation
or recovery, message publishing, inbound message rendering, and receipts.

When the user asks to create a widget in a repo, build working files. Do not
stop at an explanation. Install the SDK assets, add the quickstart
dependencies, add widget UI/controller code, and leave a config path for the
tenant-specific `imi-environments.js` file from Webex Connect.

## Build-Time Input Gate

Before installing SDK assets, copying the starter, or generating widget code,
collect the build-time choices in the Codex/plugin conversation when they are
not already present in the user's request. Do not scaffold first and then ask
for a required deployment or configuration choice.

- Widget target: a new vanilla/static widget or an existing framework app
  (React, Vue, Angular, or another host), plus the target entry point.
- Webex Connect asset config: an existing `imi-environments.js` file, or
  `appId`, `clientKey`, and environment values from which to create an example
  config. Never ask the user to paste a security token or app secret into the
  conversation.
- Visitor identity: caller-supplied User ID/Customer ID, a host-page identity
  callback, or an anonymous/guest strategy. Keep actual User ID and Customer ID
  entry inside the running widget or host page; they are not build-time
  credentials.
- Browser push: enabled or disabled. When enabled, collect the Firebase web
  configuration and the intended service-worker/manifest path; otherwise do
  not add Firebase dependencies or push permission code.
- Deployment path: site base path and the service-worker root/asset path so
  `pathConfig.root` and `assetPath` are generated consistently.
- SDK source: download the latest GitHub distribution, or use a supplied local
  `dist.zip` when working offline.
- Whether to install/copy the widget now and whether to run the available
  static/build verification after generation.

When the user says only “create a widget” or selects this builder without
details, ask one grouped question covering target/framework, Connect config,
visitor identity, browser push, deployment paths, SDK source, and install/
verification preference. Use safe defaults only for non-material presentation
details. Do not silently choose a framework, enable browser push, invent tenant
configuration, or assume the site is deployed at `/`.

If the user is not ready to provide tenant config, create an example
`imi-environments.js` and make the widget show a clear configuration-required
state. Do not claim the widget is connected or ready for production until the
real asset config is supplied.

For full method and enum inventory, read
`references/javascript-sdk-methods.md` before implementing rich templates,
postbacks, topics, thread history, push permission handling, or production error
recovery.

## Default Implementation Workflow

1. Collect the build-time inputs in the Codex/plugin UI first. Use the answers
   to choose the starter/integration path and create explicit configuration
   placeholders; do not rely on an interactive terminal prompt for this gate.
2. Inspect the target app type and entry points (`index.html`, `src/`,
   framework routes, public/static asset folder, bundler config).
3. Install the latest SDK assets from GitHub. Prefer the bundled script:

   ```bash
   python3 path/to/webexconnect-livechat-widget/scripts/install_javascript_sdk.py . --copy-template
   ```

   This downloads the latest `dist.zip` from
   `https://github.com/webex/webexconnect-javascript-sdk/releases/latest/download/dist.zip`
   and installs `webex-connect-sdk.min.js`, `sw.min.js`, and `manifest.json`.
   `--copy-template` also adds the vanilla widget starter files for static or
   empty apps.
4. Add the quickstart dependencies to the browser entry page before the SDK:
   jQuery `1.12.4`, and Firebase compat scripts only when browser push is
   enabled.
5. Add `assets/js/imi-environments.js` from the Webex Connect UI. If the user
   has not provided it, create an example file or clear placeholder and make
   the widget show a configuration error until the real file is supplied.
6. Build the widget UI and controller. If the app is plain HTML or empty, copy
   `assets/vanilla-widget-template/*` into the project and then adapt config.
   If the app uses React/Vue/Angular/etc., port the same lifecycle and SDK calls
   into native components instead of dropping in unrelated framework code.
   Keep the first page static and login-only: collect User ID, optional Customer
   ID, and optional stable Device ID before revealing the widget. Do not start
   the SDK or display New conversation/composer controls before login succeeds.
7. Wire send and receive:
   - `startup()`
   - `isRegistered()` / `register()`
   - `setICMessagingReceiver()`
   - `connect()`
   - `fetchThreads()` or `createThread()`
   - `publishMessage()` from the composer
   - render `onMessageReceived`
8. Verify static integration before finishing:
   - SDK file exists under `assets/js/webex-connect-sdk.min.js`.
   - `sw.min.js` exists at the configured service worker root.
   - `assets/manifest/manifest.json` exists when push is enabled.
   - HTML loads jQuery before `imi-environments.js` and the SDK.
   - Widget has a launcher, panel, message list, input, send button, status
     indicator, and error state.
   - Code fails clearly when tenant config is missing instead of silently
     pretending to work.

## Build Sequence

1. Confirm there is a Web Application asset in Webex Connect with Live
   Chat/In-App Messaging enabled.
2. Download the latest JavaScript SDK distribution from GitHub and add the SDK
   files to the web app, normally under `assets/js/`.
3. Add `imi-environments.js` from the Webex Connect UI and verify its
   `asset.appId`, environment target, and `pathConfig` match the deployment
   path.
4. Place the service worker at the configured root path and the manifest under
   the configured assets path if browser push is required.
5. Include required browser dependencies before the SDK scripts.
6. Call `IMI.IMIconnect.startup()` once the SDK scripts are loaded.
7. Register a security token listener if the app asset uses JWT/security token
   enforcement, then call `IMI.IMIconnect.setSecurityToken(token)` before SDK
   calls that need it.
8. Check `IMI.IMIconnect.isRegistered()` on every launch. If false, create an
   `IMI.ICDeviceProfile` and call `IMI.IMIconnect.register(profile, callback)`.
9. Create the messaging singleton with `IMI.ICMessaging.getInstance()`.
10. Register an `IMI.ICMessagingReceiver` with `setICMessagingReceiver`.
11. Connect with `messaging.connect()` only after registration succeeds and the
    widget is ready to process callbacks.
12. Fetch existing threads or create a new `IMI.ICThread`; keep the selected
    thread in widget state.
13. Publish outbound user messages with `new IMI.ICMessage()`,
    `message.setMessage(text)`, `message.setThread(thread)`, and
    `messaging.publishMessage(message, callback)`.
14. Render inbound messages from `onMessageReceived`, then update read/clicked
    status with the SDK methods where applicable.

## HTML Asset Pattern

```html
<script src="https://code.jquery.com/jquery-1.12.4.js"></script>
<!-- Add Firebase compat scripts only when browser push is enabled. -->
<script src="https://www.gstatic.com/firebasejs/11.1.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/11.1.0/firebase-messaging-compat.js"></script>
<script src="/assets/js/imi-environments.js"></script>
<script src="/assets/js/webex-connect-sdk.min.js"></script>
```

Keep the script path and filename aligned with the file downloaded from Webex
Connect. If the site is hosted under a subpath, set both `assetPath` and `root`
in `imi-environments.js`; do not rely on root defaults.

For local/offline dependency policy, it is acceptable to download
`jquery-1.12.4.min.js` into `assets/js/` and load it locally, but do not omit
jQuery unless the SDK version's current docs no longer require it.

## Bundled Resources

- `scripts/install_javascript_sdk.py`: install or refresh latest SDK assets
  from GitHub into a target web project and optionally copy the vanilla widget
  with `--copy-template`. Use `--sdk-zip` for offline/local verification.
- `assets/vanilla-widget-template/`: complete plain HTML/CSS/JS widget
  skeleton with launcher, panel, message list, composer, SDK startup,
  registration, thread creation/recovery, send, receive, typing, receipts, and
  clear missing-config handling.

Use these resources when creating a new widget. For existing apps, use them as
the source implementation pattern and port them into the app's conventions.

## Widget Skeleton

```javascript
const callbacks = {
  onSuccess(value) {
    console.debug("webex connect sdk success", value);
  },
  onFailure(error) {
    console.error("webex connect sdk failure", error);
  }
};

async function startLiveChatWidget({ userId, customerId, deviceId, token }) {
  if (!window.IMI || !IMI.IMIconnect || !IMI.ICMessaging) {
    throw new Error("Webex Connect JavaScript SDK is not loaded");
  }

  IMI.IMIconnect.startup();

  if (token) {
    IMI.IMIconnect.registerSecurityTokenListener({
      onFailure: () => refreshTokenAndRetry()
    });
    IMI.IMIconnect.setSecurityToken(token);
  }

  const messaging = IMI.ICMessaging.getInstance();
  messaging.setICMessagingReceiver({
    onConnectionStatusChanged(status) {
      updateConnectionUi(status);
    },
    onMessageReceived(message) {
      renderInboundMessage(normalizeIcMessage(message));
      markReadableMessageAsRead(messaging, message);
    }
  });

  if (!IMI.IMIconnect.isRegistered()) {
    const profile = new IMI.ICDeviceProfile(
      deviceId || `${userId || customerId}-${Date.now()}`,
      userId,
      customerId
    );
    IMI.IMIconnect.register(profile, {
      onSuccess: () => connectIfNeeded(messaging),
      onFailure: showRegistrationError
    });
  } else {
    connectIfNeeded(messaging);
  }

  return messaging;
}

function connectIfNeeded(messaging) {
  if (!messaging.isConnected()) {
    messaging.connect();
  }
}

function sendTextMessage(messaging, thread, text) {
  const message = new IMI.ICMessage();
  message.setMessage(text);
  message.setThread(thread);
  messaging.publishMessage(message, callbacks);
}
```

Treat this as a starting pattern. Adapt the callback wiring to the host app's
state management, but keep the SDK call order intact.

## Thread Handling

- Prefer resuming an existing active thread when the app has one stored or when
  `fetchThreads(offset, limit, callback)` returns a usable conversation.
- When the visitor chooses New conversation, ask for a title before creating
  the `IMI.ICThread`; persist the entered title instead of a generic default.
- Keep the title prompt inside the widget panel so starting a conversation does
  not create a detached page-level dialog.
- Create a new `IMI.ICThread` only when there is no suitable active thread or
  the visitor explicitly requests a new conversation.
- Set title, status, type, and stream name only when those values are supported
  by the configured asset and expected by the service team.
- Use `fetchMessages(threadId, beforeDate, limit, callback)` to load history
  when opening a thread. Do not depend only on live RTM delivery.
- Use `fetchUnreadThreadCount(callback)` for badges and counters.
- Use `updateThread(thread, callback)` and `closeThread(thread, callback)` for
  explicit user actions, not as silent side effects of widget teardown.
- Expose close and reopen actions for the selected thread, keep closed threads
  readable, and disable message composition while a thread is closed.
- Provide a non-sensitive settings/diagnostics view for SDK version,
  application identity, registration, and connection state;
  never render security tokens or app secrets. Keep this view inside the
  widget and open it from the header settings icon.
- Use a single-column widget flow: Chat toggles the panel open/closed, the
  inbox shows the header, thread list, empty state, and bottom New conversation
  action; opening a thread replaces the inbox with the conversation and
  provides a back action.
- Keep the message composer at the bottom of the selected conversation view;
  do not show it on the inbox view until a thread is selected or created.
- Include an accessible header expand control that switches the widget to a
  full-screen layout.

## Message Rendering

Normalize every inbound `IMI.ICMessage` before rendering. At minimum inspect:
`getType()`, `getMessage()`, `getAttachments()`, `getMedia()`,
`getInteractiveData()`, `getQuickReplyData()`, `getTransactionId()`,
`getThread()`, `getSenderId()`, `getUserId()`, `getCustomTags()`, and
`getExtras()`.

Support these UI paths:

- Text message: render `getMessage()` as text with escaping.
- Media/file/image/audio/video/location: use attachment/media metadata, content
  type, URL, size, duration, latitude, and longitude where present.
- Form template: render each form field type and validate before postback.
- Generic template: render elements, buttons, image/media, and postback actions.
- Quick reply: render choices and call `createPostbackMessage(message, button)`
  before publishing the selected reply.
- Web URL or template postback: call `sendClickedEvent(transactionId, button,
  callback)` when the user activates a button.
- Receipts and statuses: reconcile `ReadReceipt`, `Delivered`,
  `ClickedReceipt`, and deleted events against the original transaction ID.
- Typing events: show temporary typing state for `TypingStart` and clear it on
  `TypingStop` or timeout.
- Thread lifecycle events: react to `UpdateThread`, `ReopenThread`, and
  `CloseThread` without rendering them as normal chat bubbles.

## SDK Methods to Prefer

| Need | SDK methods/classes |
| --- | --- |
| Initialize SDK | `IMI.IMIconnect.startup()`, `shutdown()` |
| Registration | `isRegistered()`, `register(profile, callback)`, `unregister()` |
| Secure assets | `setSecurityToken(token)`, `registerSecurityTokenListener(callback)` |
| Messaging singleton | `IMI.ICMessaging.getInstance()` |
| Connection | `connect()`, `disconnect()`, `isConnected()`, `getConnectionStatus()` |
| Receiver callbacks | `setICMessagingReceiver({ onConnectionStatusChanged, onMessageReceived })` |
| Threads | `createThread`, `fetchThreads`, `fetchThread`, `updateThread`, `closeThread` |
| History, streams, counts | `fetchMessages`, `fetchStreams`, `fetchUnreadThreadCount` |
| Sending | `IMI.ICMessage`, `setMessage`, `setThread`, `publishMessage` |
| Delete and outgoing flags | `deleteMessage`, `getOutgoing`, `setOutgoing` |
| Receipts | `setMessageAsRead`, `setMessagesAsRead`, `sendClickedEvent` |
| Interactions | `createPostbackMessage`, `setQuickReplyData`, template attachment classes |
| Typing | `publishTypingIndicator(thread, started, callback)` |
| Media upload | `IMI.ICMediaFileManager.uploadFile`, `onFileUploadComplete` |
| Push permission | `requestPushPermission(callback)` |
| Topics | `fetchTopics`, `subscribeTopic`, `unsubscribeTopic` |

## Production Guardrails

- Keep SDK code idempotent. Guard against repeated `startup()`, repeated
  receiver assignment, duplicate `connect()` calls, and multiple active widget
  instances.
- Store only stable thread IDs and non-sensitive widget state in browser
  storage, and scope those keys by User ID/Customer ID so browser sessions do
  not restore another visitor's selected thread.
- Treat the SDK registration as identity-bound. If the configured User ID or
  Customer ID changes, disconnect and unregister the old profile (or use the
  documented profile update fallback) before registering and fetching for the
  new visitor.
- Do not log real tokens, app secrets, user IDs, customer IDs, or message
  contents in production.
- Rate-limit typing indicator calls because the SDK throttles typing events.
- Add reconnect UI for `ICConnectionStatus.Error`, `Closed`, and `Refused`.
- Fetch threads/messages on startup because undelivered Live Chat/In-App
  messages have time-to-live limits and may require Server-Side Inbox recovery.
- Keep notification permission behind a clear user action when
  `shouldRequestNotificationPermission` is false.
- Use the dark Webex visual language for generated widget examples: dark
  surfaces, blue primary actions, teal connection state, and rounded cards,
  forms, carousels, and modals.
- Include accessibility basics: keyboard focus, ARIA labels for launcher,
  message list announcements, and readable contrast.
- Escape user and agent text before rendering. Treat URLs, file names, and
  custom tags as untrusted input.
- Deduplicate overlapping `getAttachments()`, `getMedia()`, and interactive
  payload getters before rendering so forms, cards, carousels, and attachments
  do not appear twice.

## CANNOT

- Cannot call messaging methods before `IMI.IMIconnect.startup()` and successful
  user registration.
- Cannot leave SDK installation as a manual follow-up when the user asked to
  create a widget; download/copy the latest GitHub SDK assets or explain the
  network blocker and use a provided `dist.zip`.
- Cannot assume registration persists forever; always call `isRegistered()` at
  launch and re-register when needed.
- Cannot commit tenant-specific `imi-environments.js`, app secrets, security
  tokens, user IDs, customer IDs, or service identifiers into reusable source.
- Cannot place `sw.min.js` in an arbitrary folder without matching
  `pathConfig.root`; browser push service worker scope depends on that path.
- Cannot request browser notification permission in a background flow when the
  browser requires a user gesture.
- Cannot use deprecated security token listener methods for new widgets; use
  `registerSecurityTokenListener` and `unRegisterSecurityTokenListener`.
- Cannot treat `publishMessage` success as delivered or read; process receipts
  and status callbacks separately.
- Cannot render forms, generic templates, quick replies, or postbacks as plain
  text.
- Cannot rely only on live callbacks for history; use fetch APIs for thread
  recovery and reloads.

## Source Links

- https://developers.webexconnect.io/docs/javascript-sdk-quickstart-guide
- https://developers.webexconnect.io/docs/javascript-sdk-api-reference
- https://developers.webexconnect.io/docs/javascript-sdk-messaging
- https://developers.webexconnect.io/docs/enumerations
- https://developers.webexconnect.io/docs/managing-assets

## Next Skills

- Setup: `webex-connect-setup`
- API connection: `webex-connect-setup`
- Live Chat/In-App server sends: `webexconnect-livechat-inapp-sendmessage`
- Webhooks and events: `webexconnect-webhooks-events`
