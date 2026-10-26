---
name: webexconnect-android-push-inapp-messaging-builder
description: >
  Build or repair native Android apps that use the Webex Connect SDK for Push Notifications or In-App Messaging, including registration, chat, notifications, and QA.
---

# Webex Connect Android Push and InApp Messaging Builder

## Overview

Use this skill to build a working Android sample named `Webex Connect Demo`.
Do not stop at documentation. Generate or modify Android files, resolve the
latest SDK version, create a login screen that asks for User ID, register the
device, and expose bidirectional chat inside a realistic customer app backed by
the modular Android SDK.

Read `references/android-sdk-methods.md` before implementing message renderers,
push customization, media, templates, or QA automation.

As of the Webex Connect developer docs checked on September 2, 2026, Live
Chat/In-App messages include text, attachments, quick replies, extras, thread
alerts, typing indicators, and optional accompanying push notifications.
Attachments include file, image, video, audio, location, and template payloads;
the Android SDK template package includes generic and form template
attachments. Keep generated renderers, UI, and QA checks aligned to those
components.

## Design Reference

When a target app needs UI refinement, use the product Figma files supplied for
this builder as design references:

- Push and In-App Demo:
  `https://www.figma.com/design/HIygbHLAu7iBgHtsodlQuI/Push-and-InApp-Demo---Webex-Connect-Android-and-iOS?node-id=5-2`
- In-App Messaging Live Chat:
  `https://www.figma.com/design/XHaSDEkISFmQcu4CrU9t4H/In-App-Messaging---Live-chat`

The generated app must not depend on expiring Figma asset URLs. Reuse durable
local Webex logo assets and encode stable design tokens, spacing, safe-area
behavior, list rows, profile/settings structure, modal creation flow, and chat
composer behavior directly in the generated Compose UI.

## Build-Time Input Gate

Before generating or building the app, collect these build-time inputs in the
Codex/plugin conversation UI when they are not already present in the user's
request. Do not run the generator first and then show a config-required state
when the missing value is a required build choice.

- Messaging capability: Push, In-App, or Both.
- Push provider: FCM or HMS, only when the selected capability includes Push.
- Webex Connect asset config: either `WebexConnectConfig.properties`, legacy
  `IMIconnectConfig.properties`, or `appId`, `clientKey`, and `environment`.
- Provider service file: `google-services.json` for FCM or
  `agconnect-services.json` for HMS, only when the selected capability includes
  Push.
- Android package/application ID.
- APK build type: debug or release.
- Whether to build the APK immediately after generation.

Provider choice must happen at build time when Push is selected because each
build variant can use only one provider module. Do not silently default to FCM
or HMS for APK generation. User ID is not a build-time input; keep User ID
entry inside the running app login screen.

When the user says only "create Android app" or selects the Android builder
from the plugin without details, ask one grouped question covering:
Capability: Push, In-App, or Both; Push provider when Push is selected;
package/build type; Connect config; provider file; and whether to build now.
After the user answers, pass explicit script flags. Use `--interactive` only
from a real terminal where `stdin` is a TTY; most Codex/plugin invocations
should collect choices in chat and call the script non-interactively.

## Optional Experience Selections

Use defaults unless the user needs a different demo shape. Optional choices can
cover scenario, full rich-message coverage, thread policy, media handling,
notification UX, SDK source, and QA depth. Apply them by editing the generated
Compose UI, demo data, QA checklist, and build notes when no CLI flag exists.

## Default Build Workflow

1. Inspect the target Android app structure: Gradle Kotlin/Groovy DSL,
   application ID, app module name, Compose/XML UI style, Firebase/HMS setup,
   existing `google-services.json`, and package naming.
2. Collect build-time inputs in the Codex/plugin UI first. Use the interactive
   generator only when you are running from a real terminal:

   ```bash
   python3 path/to/webexconnect-android-push-inapp-messaging-builder/scripts/create_android_demo.py . --interactive
   ```

   For automation, pass the choices explicitly. In-App-only builds omit provider
   inputs.

   ```bash
   python3 path/to/webexconnect-android-push-inapp-messaging-builder/scripts/create_android_demo.py . \
     --capability both \
     --provider fcm \
     --package com.example.webexconnectdemo \
     --app-id APP_ID \
     --client-key CLIENT_KEY \
     --environment UK \
     --provider-config /path/to/google-services.json \
     --build-type debug \
     --build-apk
   ```

3. Resolve SDK version from Maven Central.

   The script fetches Maven metadata for `com.webex.connect` modules and falls
   back to the latest known modular SDK version when offline. Always include
   `webexconnect-core`; include `webexconnect-push` only for Push builds;
   include exactly one provider module (`webexconnect-fcm` or
   `webexconnect-hms`) when Push is selected; and include
   `webexconnect-inappmessaging` only when In-App is selected.
   If the user provides a Webex Connect Android SDK GitHub source checkout
   instead of Maven, inspect its tags/releases and pin the matching module
   version explicitly with `--version`.
4. If the selected capability includes Push, add exactly one push provider per
   build variant:
   - FCM: `webexconnect-fcm`; enable the Google services plugin only when
     `google-services.json` is present.
   - HMS: `webexconnect-hms`; add the Huawei repository, and enable the
     AGConnect plugin only when `agconnect-services.json` is present.
   - Do not include FCM and HMS in the same build variant.
5. If the selected capability includes In-App, add
   `webexconnect-inappmessaging`. Do not generate Kotlin imports for modules
   that are not included in the selected capability.
6. Apply the Kotlin Compose plugin, generate root `gradle.properties` with
   `android.useAndroidX=true`, and pin Java/Kotlin targets to 17 so generated
   builds do not inherit an incompatible host JDK target.
7. Add `WebexConnectConfig.properties` from the Webex Connect Mobile/Web app
   asset into `app/src/main/assets/`, or generate it from `appId`,
   `clientKey`, and `environment` supplied by the user. Accept legacy
   `IMIconnectConfig.properties` when updating an existing project. If the user
   is not building an APK yet and does not provide config, create
   `WebexConnectConfig.properties.example` and make the app show a clear
   configuration-required state.
8. Create or update app code:
   - Use the Figma Android messaging/product/profile references when available
     for screen structure, spacing, surface treatment, and color tokens. The
     default generated palette is dark: `#1A1A1A` canvas, `#262626` base
     surface, `#303030` elevated surface, `#3492EB` active blue, `#17C7A8`
     success teal, `#F55868` alert red, and translucent white borders/fields.
   - Use the bundled Webex logo assets for the launcher icon, round launcher
     icon, login screen brand mark, app top bar, and agent/chat brand avatar.
   - For Push builds, use a monochrome Webex notification small icon through
     `NotificationBuilderCallback`; do not use unrelated Android system icons
     for Webex Connect notifications.
   - Application startup and notification channel.
   - Rich login screen with User ID input.
   - On app launch, check `WebexConnect.instance.isRegistered`; when true,
     restore the saved demo User ID, skip the login screen, and start the
     selected messaging capability.
   - Real app shell with home, orders, support, and bottom navigation.
   - Product/order cards that can route into messaging.
   - Notification bell icon in the top bar.
   - Do not show User ID, capability, provider, or route text in the customer top bar; keep those diagnostics in Profile.
   - Notification center panel opened from the bell icon.
   - Support workspace focused on conversation/thread list and the selected
     agent chat. Keep SDK settings, profile controls, and QA/debug tools out of
     the inbox/chat surface.
   - Profile/settings screen or drawer for current User ID, Customer ID APIs,
     App ID, provider, SDK version, started/registered/connected state,
     copyable push token, editable local store/sync limits, QA diagnostics,
     global logger/security-token notes, and unregister/profile switching.
     Keep selected thread ID, thread state, unread count, and media transfer
     controls in the thread/chat context instead of the global Profile status.
   - Device registration using `DeviceProfile.defaultDeviceId` and User ID.
   - Push permission prompt for Android 13+.
   - Push token and push message listeners.
   - In-app connection status listener.
   - In-app message listener.
   - Thread inbox on one consistent surface with search, filters, modal create,
     pagination, row-open navigation, and no inline create form. After
     `createThread` succeeds, immediately merge the returned thread into local
     state before refreshing from the SDK so the thread remains visible even if
     the backend list is eventually consistent.
   - Dedicated chat header follows the opened/closed thread reference: back
     button, Webex logo, selected SDK thread title, dot status line, compact
     copyable thread ID, and three-dot menu. Do not show metadata pills, a
     redundant notification bell, extra top whitespace, or a separate
     selected-thread status card above the message list.
   - Keep View details, Search in conversation, and Close/Reopen thread in the
     chat header overflow menu. Do not show persistent close controls in the
     conversation body.
   - Chat composer with `publishMessage`, compact bubbles, focus cleanup,
     picker-backed attachments, and no duplicate bottom inset gap. Use one
     anchored bottom rail with a circular plus attachment action, subtle
     divider, inline text entry, send arrow, `imePadding`, and navigation-bar
     padding, using the same dark Webex Connect tokens as the rest of the app.
     Do not show static demo shortcut chips in an opened thread; quick replies,
     card buttons, and form actions must render only from SDK message payloads.
   - Outgoing message reconciliation so `publishMessage` success updates the
     existing optimistic bubble instead of appending a second bubble. Preserve
     recent visible rows for a short grace window while server history catches
     up, then reconcile by SDK transaction ID/fingerprint so realtime inbound
     messages do not disappear during delayed fetch recovery.
   - Normalize realtime and fetched message batches through one ordered merge
     path. Display oldest-to-newest by SDK `submittedAt`/`createdAt`, preserve
     insertion order when timestamps are equal or missing, and keep the list
     scrolled to the newest message without using `reverseLayout`.
   - Listener/history de-duplication by transaction ID and a short-lived
     outgoing fingerprint for SDK echo events. Do not use top-level recipient
     fields like `userId` or `customerId` alone to decide that a message is
     outgoing; backend, agent, platform, alert, thread-update, typing, deleted,
     and receipt messages must render as non-user messages.
   - Message history with `fetchMessages`. Never show seeded welcome/card demo
     messages inside a real SDK thread while history is loading; show a loading
     state, then an empty state only if the fetched thread has no messages.
   - Read/delivered/clicked status updates.
   - Typing indicator throttled to SDK behavior.
   - Render text, extras, location, quick replies, form/generic templates,
     postbacks, thread alerts, thread updates, typing indicators,
     read/delivered/clicked/deleted receipts, push alert rows, and
     media/file/image/audio/video attachments; show real card/attachment image
     URLs inline.
   - Never render SDK object dumps, push tokens, transaction IDs, callback data,
     concatenated debug diagnostics, or raw JSON wrappers as customer-visible
     bubble text. Show customer-readable message text in the conversation and
     keep diagnostic values in the Profile/QA surface.
   - Render generic-template elements as a single carousel message with a
     horizontal card rail and image cards, not as multiple separate messages.
   - Disable carousel/card buttons, quick replies, and form submission controls
     only after the postback/form submit `publishMessage` callback succeeds.
   - Render form templates as editable user-input controls with required-field
     validation, option chips, and a submit postback; do not show forms as
     read-only labels. Serialize submitted form values as structured JSON, not
     as raw concatenated text.
   - Keep listener objects for Push token/message callbacks and In-App
     connection/message callbacks so `unregisterPushTokenListener`,
     `unregisterMessagingListener`, and
     `unregisterConnectionStatusListener` can cleanly remove them on release,
     sign-out, or profile switching.
   - For inbound In-App messages, send `DELIVERED` as soon as the SDK listener
     receives the message and send `READ` only when the message belongs to the
     currently visible thread. Other-thread inbound messages update the inbox
     preview/unread count without being marked read, then fetch that thread's
     metadata so title, closed/open status, unread count, and preview stay
     accurate before the user opens it.
   - On In-App connection restore, resync the thread inbox and selected thread
     history through `fetchThreads`/`fetchMessages` instead of relying only on
     realtime listener delivery. This recovers messages that arrived while the
     app was disconnected, assuming Server-Side Inbox is enabled for the app
     asset.
   - Use indexed/stable Compose lazy-list keys for messages, cards, and
     actions; never key only by SDK transaction ID or action title.
   - Android back must close the notification center first, then return from
     Orders or Support to Home. Do not strand users on a screen.
   - Do not generate calling UI. Webex Connect Demo must not include telephone
     glyphs, callback-request actions, or call-support flows.
9. Add QA hooks:
   - A debug/status panel showing SDK version, provider, started/registered/
     connected state, local store/sync policy, logger/security-token notes, and
     last error. Keep current thread ID, thread state, unread count, and media
     transfer status out of the global SDK status card.
   - Android test tags or resource IDs for login, home, orders, support entry,
     notification icon, notification center, workflow cards, agent chat, send,
     message list, notification permission, and QA panel.
   - A smoke test or documented emulator test sequence.
10. Run the verifier before handing off:

   ```bash
   python3 path/to/webexconnect-android-push-inapp-messaging-builder/scripts/verify_android_demo.py . \
     --capability both \
     --provider fcm \
     --package com.example.webexconnectdemo \
     --build-type debug
   ```

   Add `--strict-config` only when tenant/provider files are expected to be
   present, and `--run-gradle` when an Android SDK and Gradle runtime are
   available.

## Generated Demo Requirements

The generated app must use only Webex Connect naming. The app label must be
`Webex Connect Demo`. Do not mention other vendors or sample-app names in code,
comments, package names, UI strings, test names, filenames, or documentation.

The minimum usable demo must include:

- `LoginScreen`: asks for User ID and stores only non-sensitive local demo
  state.
- `WebexConnectAppShell`: a real customer-facing app with home, orders,
  support, bottom navigation, Android back handling, and top notification bell.
- Webex logo assets: generated app manifest must set launcher and round icons
  to the bundled Webex mark, and Compose screens must reuse `webex_logo` for
  visible app branding.
- `HomeScreen`: hero area, product cards, and support entry that demonstrates
  messaging from a normal customer journey.
- `OrdersScreen`: order status cards with routes into support.
- `NotificationCenterSheet`: opens from the notification icon and lists push
  or demo notifications with a support handoff action.
- `SupportWorkspace`: conversation/thread inbox plus dedicated selected-thread
  agent chat. It must not render SDK settings/debug panels inside the
  conversation list.
- `ProfileScreen`: owns settings and diagnostics so the support experience
  stays clean. It should follow the profile/menu reference: branded avatar,
  User ID, Customer ID, App ID, provider, SDK version, started/registered/
  connected state, copyable push token, editable local store/sync limits,
  QA status, logger/security-token integration notes, and switch-user/
  unregister action.
- `AccountToolsPanel`: shows the current User ID, lets the user update or
  remove a demo Customer ID through profile APIs, and supports switching users
  by unregistering and returning to login from the Profile screen.
- `PushTokenCard`: shows the current push token separately from SDK status and
  provides a copy action when the token is available.
- `AdvancedSdkToolsPanel`: exposes editable local store/sync limits for maximum
  threads and messages per thread, defaulting to `50`/`50`. Keep media
  upload/download/regenerate actions in thread attachment flows, not as global
  Profile buttons.
- `ThreadListPanel`: fetches and displays in-app threads as a polished chat
  inbox with search/filter, avatar/presence dots, preview text, time, unread,
  badges, refresh, pagination, row-open navigation, modal create UI, and one
  consistent Webex blue/teal color system across cards, chips, and dialogs.
  Creating a thread must insert the returned thread into `threads` immediately
  and the next refresh must merge with local state instead of replacing the new
  row with an empty/stale server list.
- `ChatScreen`: dedicated selected-thread screen with status-safe header that
  uses the actual selected thread title and copyable thread ID, dot status
  line, overflow details/search/close/reopen actions, back button, paginated
  messages, SDK-driven quick replies/actions, reference-style bottom composer,
  picker-backed media, delete controls, receive rendering, and closed-thread
  recovery. It must not show metadata pills or a separate selected-thread
  status card between the app bar and message list.
- `WebexConnectSdkController`: single owner for SDK calls, callbacks, and state
  mapping.
- `NotificationSupport`: for Push builds, creates
  `NotificationFactory.DEFAULT_CHANNEL_ID`, requests notification permission,
  sets `NotificationBuilderCallback`, applies the Webex notification small
  icon, handles push actions, registers foreground in-app notification
  callbacks, sends delivered/read push statuses, and routes push opens into
  support messaging.
- `MessageRenderer`: handles text, push alert, read/delivered/clicked receipts,
  deleted messages, thread update/reopen/close, typing start/stop, quick
  replies, generic templates, form templates, media/file/image/audio/video, and
  location attachments. It must sanitize raw SDK diagnostic strings so device
  tokens, transaction IDs, and callback payloads do not appear in chat bubbles.
- `CardCarousel` and `RichMessageCard`: render a generic template as one
  message bubble containing a horizontally scrollable list of cards, with inline image previews and postback action chips wired through `createPostbackMessage`.
- `FormMessagePreview`: render form-template fields as editable inputs, option
  chips where available, and a submit button that publishes a structured JSON
  form postback payload.
- Interaction state: keep `disabledInteractionIds` in app state and disable
  quick replies, card buttons, and form controls after the postback/form submit
  callback succeeds. Do not disable on tap before SDK success.
- `QaChecklist`: emulator/device verification steps and failure triage.
- `verify_android_demo.py`: repeatable static QA for SDK dependencies, app
  label, Webex-only hygiene, notification setup, SDK API coverage, and test
  tags.
- `BUILD_APK.md`: generated build command, selected capability, selected
  provider when Push is included, package name, build type, and release-signing
  reminder.

Do not generate a plain full-screen chat test app. The first authenticated
screen must feel like an actual mobile app where support messaging and
notifications are embedded into product/order workflows.

## SDK Integration Pattern

Use the modular SDK APIs, not deprecated legacy `IC*` Android APIs.
Register with `DeviceProfile.defaultDeviceId` and User ID, restore registered
sessions through `WebexConnect.instance.isRegistered`, then connect in-app
messaging only after registration is ready. Register connection and messaging
listeners, render SDK messages through one `MessageRenderer`, and suppress
outgoing echoes by transaction ID plus a short-lived text fingerprint.

For threads, use `fetchThreads`, `fetchThread`, `createThread`, and
`updateThread` from the SDK. Fetch all thread types for the inbox unless the
user asks for a narrower filter.

Conversation threads are writable when active. Announcement threads are
read-only. Closed threads must show history but disable composer, attachment
send, quick replies, card actions, and form submit until the user reopens the
thread with `updateThread`.

For local store, pagination, media, and profile switching, implement the SDK
methods listed in `references/android-sdk-methods.md`: `DefaultMessageStore`,
`MessageSynchronizationPolicy`, `fetchThreads`, `fetchMessages`,
`deleteMessage`, `mediaFileManager.uploadFile`, `downloadFile`,
`regenerateMediaURL`, `updateProfileParam`, `removeProfileParam`, and
`unregister`.

Configure `DefaultMessageStore` and editable `MessageSynchronizationPolicy`
thread/message limits before calling `InAppMessaging.instance.connect()`.
Realtime messages should update
the active chat immediately; fetch APIs are the recovery and navigation path:
fetch the inbox after connect/reconnect, fetch thread metadata after
other-thread realtime messages or thread updates, and fetch messages whenever a
thread is opened or older history is requested. After a visible-thread
realtime message or successful send, schedule one short debounced
`fetchMessages` reconciliation for that thread so local store/server-side inbox
lag cannot leave the transcript stale or reorder messages later.

For sending, publish against the active SDK thread. Never append the optimistic
outgoing bubble again inside the publish callback. Keep one UI row per user
send, update its ID/status on callback success, and suppress the matching SDK
listener echo by transaction ID or a short-lived text fingerprint. Use User
ID/sender/direction metadata for right/left alignment; delivery/read/clicked
receipts update the same outgoing bubble instead of rendering as messages.

For Push, register token/message listeners, request notification permission
from a user action, create the notification channel, configure the Webex small
icon, and adapt callback signatures to the exact SDK version resolved by
Gradle while keeping the lifecycle and ownership model intact. The current
Maven `3.1.0` AAR exposes `registerPushTokenListener` and
`unregisterPushTokenListener`; use those paired methods for generated code.

For current new builds, align with the modular SDK docs checked on September 2,
2026: SDK `3.1.0`, Android 6.0/API 23+, compile SDK 37, Kotlin `2.2.20`, and
Android Gradle Plugin `8.13.0` unless Maven/Gradle metadata or the target app's
existing validated build constraints require a newer compatible value.
## QA Verification

Run the generated verifier and the QA matrix in `references/android-sdk-methods.md`
before finishing. At minimum verify Gradle build readiness, selected capability
and provider, Webex-only branding, thread list/navigation, realtime receive,
reconnect recovery, message-store/sync setup, send de-duplication, receipts,
closed/read-only threads, media, templates/forms, push permission/channel/action
handling, profile switching, and no non-Webex vendor/sample-app references.

## CANNOT

- Cannot leave SDK dependency resolution as a manual follow-up when the user
  asked to build the demo; resolve Maven Central or explain the network blocker
  and pin the latest verified version.
- Cannot include both `webexconnect-fcm` and `webexconnect-hms` in the same
  build variant.
- Cannot build a Push APK until provider, package name, build type, Connect app
  config, and provider service file have been supplied or confirmed present.
- Cannot use deprecated legacy Android `IC*` SDK APIs for a new modular demo.
- Cannot hardcode app IDs, client keys, FCM server keys, JWTs, access tokens,
  tenant names, or real user/customer identifiers.
- Cannot commit production `WebexConnectConfig.properties`, legacy
  `IMIconnectConfig.properties`, `google-services.json`, or
  `agconnect-services.json` unless the user explicitly provides sanitized demo
  files.
- Cannot call in-app chat methods before device registration is confirmed.
- Cannot append a second outgoing chat bubble when `publishMessage` succeeds or
  when the SDK listener echoes the app user's own message.
- Cannot treat `publishMessage` success as delivered or read; send and process
  message statuses separately.
- Cannot render quick replies, generic templates, form templates, media,
  locations, or push interactive actions as plain text.
- Cannot flatten carousel/generic-template elements into multiple independent
  messages or key cards/actions by non-unique button text.
- Cannot disable carousel, quick reply, card, or form actions before the SDK
  postback callback succeeds.
- Cannot render form templates as read-only previews when user input is
  expected.
- Cannot omit notification channel creation on Android 8+ or permission handling
  on Android 13+.
- Cannot use any non-Webex sample app or vendor name anywhere in generated
  files.
- Cannot include a callback-request action, telephone glyph, or any calling flow;
  this skill does not support calling.
- Cannot leave launcher, notification, login, top-bar, or chat avatar branding
  on generic placeholder/system icons when bundled Webex logo assets are
  available.
- Cannot ship a bare SDK test screen as the default generated UI; embed
  messaging inside a polished customer app shell.

## Source Links

- Android SDK setup: https://developers.webexconnect.io/docs/android-modularization-sdk-quick-start-guide, https://developers.webexconnect.io/docs/android-core-modularization-sdk, https://developers.webexconnect.io/docs/android-push-modularization-sdk, https://developers.webexconnect.io/docs/android-inapp-modularization-sdk
- Runtime APIs: https://developers.webexconnect.io/docs/webexconnect, https://developers.webexconnect.io/docs/sdk-pushmessaging, https://developers.webexconnect.io/docs/inappmessaging
- In-App/Live Chat messages: https://developers.webexconnect.io/reference/live-chat-in-app-messaging-api, https://developers.webexconnect.io/docs/webexconnectinappmessageattachmentstemplates
- Maven/release checks: https://developers.webexconnect.io/docs/android-sdk-release-notes, https://repo1.maven.org/maven2/com/webex/connect/webexconnect-inappmessaging/maven-metadata.xml

Next skills: `webex-connect-setup`, `webexconnect-push-sendmessage`, `webexconnect-livechat-inapp-sendmessage`.
