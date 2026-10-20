# Android Modular SDK Reference

Use this reference when building a `Webex Connect Demo` Android app for Push
Messaging and In-App Messaging. Prefer Maven Central metadata for the current
SDK version and the Webex Connect docs for exact signatures.

## Version and Modules

Maven group: `com.webex.connect`

Common modules:

- `webexconnect-core`: SDK startup, config, registration, profile, logging,
  errors, shared module lifecycle.
- `webexconnect-push`: push notification APIs, token/message listeners,
  notification factory, action handling, in-app notification display.
- `webexconnect-fcm`: Firebase Cloud Messaging provider. Use for Google Play
  Services devices.
- `webexconnect-hms`: Huawei Mobile Services provider. Use for HMS devices.
- `webexconnect-inappmessaging`: bidirectional in-app chat, threads, messages,
  message store, synchronization, media.

Resolve these metadata URLs when building:

- `https://repo1.maven.org/maven2/com/webex/connect/webexconnect-core/maven-metadata.xml`
- `https://repo1.maven.org/maven2/com/webex/connect/webexconnect-push/maven-metadata.xml`
- `https://repo1.maven.org/maven2/com/webex/connect/webexconnect-fcm/maven-metadata.xml`
- `https://repo1.maven.org/maven2/com/webex/connect/webexconnect-hms/maven-metadata.xml`
- `https://repo1.maven.org/maven2/com/webex/connect/webexconnect-inappmessaging/maven-metadata.xml`

The generator must resolve Maven metadata at run time and use the current
module version returned for the selected provider. When the local runtime cannot
reach Maven Central, it falls back to the last verified modular SDK version
used by this repository so generation remains deterministic.

As of the Webex Connect developer docs checked on September 2, 2026, Live
Chat/In-App messages include text, attachments, quick replies, extras, thread
alerts, typing indicators, and optional accompanying push notifications.
Attachment content types include file, image, video, audio, location, and
template payloads. Generic template attachments can contain up to 8 elements, 5
images per element, and 3 buttons per element; quick replies can contain up to
4 options. The Android SDK template package exposes generic and form template
attachments, so generated apps must render both.

## Interactive Build Inputs

Collect these inputs in the Codex/plugin conversation UI before generating the
app when they are not already present:

- Messaging capability: `push`, `inapp`, or `both`.
- Push provider: `fcm` or `hms`, only when capability is `push` or `both`.
  This is a build-time choice because a build variant can include only one
  provider module.
- Webex Connect app asset config: either an existing
  `WebexConnectConfig.properties` file, legacy `IMIconnectConfig.properties`
  file, or `appId`, `clientKey`, and `environment` values.
- Provider service file: `google-services.json` for FCM or
  `agconnect-services.json` for HMS, only when capability includes Push.
- Android package/application ID.
- APK build type: `debug` or `release`.
- Whether to run the APK build after generation.

Do not ask for User ID during generation. User ID belongs in the running demo
app login screen and is used for device registration.

Do not default to FCM or HMS from a vague request. If the user asks to create an
Android app without build choices, ask for capability first; ask for provider
only when the chosen capability includes Push. Use the script's `--interactive`
flag only in a real terminal. In Codex/plugin tasks, pass explicit flags after
the user answers in chat.

Optional UI/experience selections can be asked in the same conversation turn
when the user wants control over the generated sample:

- Demo scenario: retail/service support default, travel, financial services,
  healthcare, or custom product/order labels.
- Feature coverage: standard chat, full rich messaging default, or QA-heavy all
  SDK coverage.
- Thread policy: active conversations only, or closed/reopen plus announcement
  read-only threads.
- Media handling: sample media only, or Android picker plus SDK upload,
  download, and media URL regeneration.
- Notification UX: notification center only, or foreground banners plus push
  actions when Push is selected.
- SDK source: latest Maven Central, pinned version, or local/GitHub SDK checkout.
- QA depth: static verifier, Gradle build, or emulator smoke run.

The generator CLI covers required build choices. Apply optional experience
selections by editing the generated Compose UI, demo data, QA checklist, and
build notes after generation when no explicit CLI flag exists.

Generated file locations:

- `app/src/main/assets/WebexConnectConfig.properties`
- `app/src/main/assets/IMIconnectConfig.properties` for legacy projects
- `app/google-services.json` or `app/agconnect-services.json`
- `BUILD_APK.md`
- `QA_CHECKLIST.md`

Generated `.gitignore` entries must protect `WebexConnectConfig.properties`,
legacy `IMIconnectConfig.properties`, provider service files, local
properties, build output, and signing keys.

## Rich Demo App UX

Build the generated app as a realistic customer application, not a standalone
SDK test screen. The authenticated experience must include:

- Home screen with branded commerce/service content, product cards, and a clear
  support entry point.
- Bundled Webex logo assets applied to the launcher icon, round launcher icon,
  login screen brand mark, app top bar, and agent/chat avatar.
- Orders screen with order status cards and a support handoff for order
  questions.
- Support workspace with automation workflow cards for order tracking, returns,
  and billing before or alongside agent chat.
- Thread inbox rendered as a vertical chat list with title, search field,
  filter action, circular avatar/initials, presence dot, preview text, updated
  time, unread count, closed/announcement badges, and clean row affordance.
- Tapping a thread row opens a dedicated chat screen for that thread; do not
  stack the chat composer below the inbox list.
- New conversations are created from a `+` icon near the Conversations header;
  show the title input and Create button in a modal only after the user taps it.
- Dedicated chat headers must respect status bar/cutout safe areas without
  double top padding, show the selected SDK thread title, and expose a compact
  copy action for the SDK thread ID.
- The dedicated chat header must follow the opened/closed thread reference:
  back button, Webex logo, selected thread title, dot status line
  (`Active`, `Thread closed`, `Announcement`, or `Connecting`), and three-dot
  menu. Do not add metadata pills, a redundant notification bell, or a separate
  status card between the header and message list.
- The three-dot menu contains View details, Search in conversation, and
  Close/Reopen thread. Closed threads show a centered lock recovery state,
  preserve history, and omit quick actions/composer until reopened.
- Use the Figma Android references for screen structure and apply one explicit
  Webex dark Material token set: `#1A1A1A` canvas, `#262626` surface,
  `#303030` elevated surface, `#3492EB` active blue, `#17C7A8` success teal,
  `#F55868` alert red, and translucent white borders/fields. Do not let
  default purple Material surfaces leak into the UI.
- Top-bar notification bell icon available from app screens.
- Customer-facing top bars should show the app brand only, not the current
  User ID, selected capability, provider, or route text. Keep App ID,
  provider, SDK version, started/registered/connected state, push token,
  sync limits, and other global diagnostics in Profile/settings.
- Profile/settings must not duplicate selected-thread ID, selected-thread
  state, unread count, or media transfer controls. Show push token in a
  separate copyable card and expose editable local sync limits for maximum
  threads and messages per thread, defaulting to `50`/`50`.
- Notification center opened from the bell icon, with notification rows and a
  path into support.
- Android back closes the notification center first, then returns from Orders
  or Support to Home.
- Agent chat card with header, online/connecting state, message bubbles,
  composer, attachment control, send control, SDK-driven quick replies/actions,
  notification permission action, typing support, and QA status panel.
- Keep chat bubbles compact with a max width instead of forcing short outgoing
  messages into large full-width blocks.
- Build the composer as one compact bottom rail using the existing Webex dark
  tokens: circular plus attachment action, subtle vertical divider, inline text
  entry, and send arrow. Do not fall back to a bulky outlined input box or a
  separate attachment button outside the rail.
- The attachment icon must open Android's document picker, copy the selected
  URI through `ContentResolver`, upload it through `mediaFileManager`, and
  publish the returned media reference as an attachment message.
- Card and carousel images, plus image attachments, must render inline from the
  URL. Do not replace real image URLs with placeholder text such as a generic
  media-preview label.
- Customer chat bubbles must show customer-readable text only. Do not show SDK
  object dumps, push tokens, transaction IDs, callback data, concatenated
  diagnostics, or raw JSON wrappers inside the conversation. Keep those values
  in Profile/QA diagnostics instead.
- Clear input focus after send, quick reply, and attachment actions so the
  keyboard or IME toolbar does not cover the chat header or leave a bottom gap.
- Stable test tags for `home-screen`, `orders-screen`, `support-entry`,
  `notification-icon`, `notification-center`, `automation-workflow`,
  `agent-chat-card`, `message-list`, `attachment-button`, `message-input`,
  and `send-button`.

Keep Webex Connect as the app and support brand. Do not reference unrelated
sample apps or vendor names in generated files. Do not add telephone glyphs,
callback-request actions, or call-support flows because this skill does not
support calling.

## Quickstart Requirements

- Android 6.0/API 23+ for SDK 3.1.0.
- Compile SDK and target SDK should follow the current modular quickstart;
  the docs checked on August 31, 2026 list compile SDK 37 for SDK 3.1.0.
- Generated projects can build with `./gradlew` after a trusted wrapper is
  added, or with `gradle` when Gradle is installed on PATH. Do not vendor an
  opaque Gradle wrapper binary into the skill package.
- Apply `org.jetbrains.kotlin.plugin.compose` for Compose projects and pin
  Java/Kotlin targets to 17 to avoid JVM target mismatch on newer local JDKs.
- Generate root `gradle.properties` with `android.useAndroidX=true` because
  Compose and the Webex Connect SDK dependency graph require AndroidX.
- Add Google services plugin for FCM or Huawei repository/plugin for HMS only
  when capability includes Push.
- Do not include FCM and HMS in one build variant.
- Add `webexconnect-core` for every generated app. Add `webexconnect-push`
  only when Push is selected, then add exactly one provider module:
  `webexconnect-fcm` or `webexconnect-hms`.
- Add `webexconnect-inappmessaging` only when capability includes In-App.
- Add `WebexConnectConfig.properties` under app assets from the Webex Connect
  Mobile/Web app asset configuration page. Accept legacy
  `IMIconnectConfig.properties` only when updating existing projects.
- If generating the properties file from inputs, include `appId`, `clientKey`,
  and `environment`; otherwise copy the downloaded file unchanged.
- Add network and boot permissions from the quickstart.
- Add ProGuard/R8 rules for Jetty, SQLCipher, WorkManager, MQTT, Firebase/HMS.
- Check `WebexConnect.instance.isRegistered` at app launch; when true, restore
  the saved demo User ID, skip the login screen, and start the selected
  messaging capability. The SDK can unregister inactive app users after
  extended inactivity.

## Core Flow

- `WebexConnect.instance.startup()`
- `WebexConnect.instance.shutdown()`
- `WebexConnect.instance.isRegistered`
- `WebexConnect.instance.register(DeviceProfile, callback)`
- `WebexConnect.instance.unregister(callback)`
- `DeviceProfile(DeviceProfile.defaultDeviceId, userId)`
- profile update/remove methods where needed
- security token/JWT setup when the app asset requires JWT authentication
- logging through SDK logger APIs when diagnosing QA failures

## PushMessaging Surface

Properties to account for:

- `PushMessaging.instance`
- `actionHandler`
- `inAppNotificationManager`
- `notificationFactory`
- `provider`
- `pushToken`
- `priority`

Functions to wire:

- `isConnectPushData(data)` in the current Maven `3.1.0` AAR. The online API
  page may describe this surface as `isConnectMessageData`.
- `processPushData(data)` in the current Maven `3.1.0` AAR. The online API
  page may describe this surface as `processMessageData`.
- `processPushToken(token)` in the current Maven `3.1.0` AAR. The online API
  page may describe this surface as `processToken`.
- `registerMessagingListener(listener)`
- `unregisterMessagingListener(listener)`
- `registerPushTokenListener(listener)` / `unregisterPushTokenListener(listener)`
  in the current Maven `3.1.0` AAR. If a later SDK switches to
  `registerTokenListener` / `unregisterTokenListener`, update the generated
  code and verifier together.
- `requestNotificationPermission(callback)`
- `sendMessageStatus(vararg ids, status, callback)`
- `sendMessageStatus(id, status, interactiveData, callback)`
- `startup()`
- `shutdown()`

Notification features:

- Create `NotificationFactory.DEFAULT_CHANNEL_ID` before displaying
  notifications on Android 8+.
- Use `NotificationBuilderCallback` to apply the generated monochrome Webex
  small icon and adjust title, body, priority, deep links, and actions.
- Replace `notificationFactory` only when the whole notification build process
  needs custom behavior.
- Implement `NotificationActionHandler` for notification action buttons.
- Use `InAppNotificationManager` and banner/modal styles for in-app display.
- On Android 13+, call `requestNotificationPermission` from a visible user
  action.

## InAppMessaging Surface
Properties to account for:

- `connectionStatus`
- `isConnected`
- `mediaFileManager`
- `messageStore`
- `messageSynchronizationPolicy`

Functions to wire:

- `connect()`
- `disconnect()`
- `registerConnectionStatusListener(listener)`
- `unregisterConnectionStatusListener(listener)`
- `registerMessagingListener(listener)`
- `unregisterMessagingListener(listener)`
- `publishMessage(message, callback)`
- `deleteMessage(messageTransactionId, callback)`
- `fetchMessages(threadId, beforeDate, limit, callback)`
- `publishTypingIndicator(thread, isTyping, callback)`
- `createPostbackMessage(message, button)`
- `createThread(thread, callback)`
- `updateThread(thread, callback)`
- `fetchThreads(beforeDate, limit, callback, category, type)`
- `fetchThread(threadId, callback)`
- `fetchUnreadThreadCount(callback)`
- `sendMessageStatus(vararg ids, status, callback)`
- `sendMessageStatus(id, status, button, callback)`
- `startup()`
- `shutdown()`

Important behavior:

- Conversation threads are bidirectional.
- Announcement threads are one-way platform-to-app.
- Thread inboxes should call `fetchThreads(beforeDate, limit, callback, null,
  null)` to show both conversation and announcement threads unless the user
  explicitly asks for a narrower category/type filter.
- Opening an item from the thread list should call `fetchThread(threadId,
  callback)` before loading messages so the UI has current title, status, type,
  unread count, and timestamps.
- Creating a user-started support conversation should instantiate
  `InAppThread`, set a clear title/category, set `InAppThreadStatus.ACTIVE`,
  call `createThread`, then select the returned SDK thread.
- Reopening or closing a thread should set `thread.status` to
  `InAppThreadStatus.ACTIVE` or `InAppThreadStatus.CLOSED`, set
  `reasonForStatusChange`, then call `updateThread`.
- Closed threads show history but must disable composer, attachments, quick
  replies, card actions, and form submits until reopened.
- Announcement threads show history but remain read-only because they are
  platform-to-app.
- Use `fetchUnreadThreadCount` for the global unread badge and per-thread
  `unreadMessageCount` from fetched thread records for the inbox.
- Keep registered listener objects in the controller and unregister those same
  objects on release/sign-out. Do not register anonymous listeners that cannot
  be removed later.
- For inbound messages, send `InAppMessageStatus.DELIVERED` after receive and
  send `InAppMessageStatus.READ` only after the message is visible in the
  active thread. Messages received for inactive threads should update inbox
  preview/unread state without being marked read, then call `fetchThread` for
  that thread ID or fall back to `fetchThreads` so the inbox metadata is not
  stale.
- When the connection listener reports that In-App Messaging is connected
  again after startup, foreground return, or network recovery, call
  `fetchThreads` and reload the selected thread's messages via the normal
  thread-selection path. Render realtime active-thread messages immediately,
  then schedule one short debounced `fetchMessages` reconciliation for the
  visible thread after receive or successful send. Do not synchronously block
  visible receive rendering on a full history fetch.
- Paginate thread lists with the `hasMore` value from `fetchThreads` and the
  oldest loaded thread timestamp.
- Paginate older messages with `fetchMessages(threadId, beforeDate, limit,
  callback)` using the oldest loaded message timestamp.
- Configure `DefaultMessageStore.create(context, storeName)` and
  `MessageSynchronizationPolicy(MessageSynchronizationMode.LIMITED, maxThreads,
  maxMessagesPerThread)` before connecting when generating the demo.
- Expose `deleteMessage(messageTransactionId, callback)` for real in-app
  messages and remove the row only after the callback succeeds.
- Use `mediaFileManager.uploadFile`, `downloadFile`, and `regenerateMediaURL`
  through SDK callbacks. Publish uploaded files as `InAppFileAttachment` where
  the SDK returns a media reference URL.
- Preserve the selected file's MIME type when publishing `InAppFileAttachment`
  so `MessageRenderer` can classify `image/*`, `video/*`, and `audio/*`
  attachments correctly.
- For Push builds, register `NotificationActionHandler` and
  `InAppNotificationCallback`; show foreground notifications in the demo UI and
  send delivered/read statuses when the SDK provides a transaction ID.
- Use `updateProfileParam(DeviceProfileParam.CUSTOMER_ID, ...)`,
  `removeProfileParam`, and `unregister` for profile update and user switching
  flows.
- A local optimistic outgoing bubble must be reconciled when `publishMessage`
  returns. Do not append the same text again on callback success. Preserve
  recent visible rows briefly while server history catches up so a realtime
  inbound message cannot disappear during delayed fetch recovery.
- Listener echoes and history reloads can surface messages already shown in the
  UI. Upsert by transaction ID and suppress only outgoing short-lived
  fingerprints so backend/agent replies are not consumed as user echoes.
- After every realtime, send callback, receipt, history, attachment, or
  pagination merge, normalize display order oldest-to-newest by SDK
  `submittedAt` first and `createdAt` second. Preserve insertion order when
  timestamps are equal or missing; do not use reverse-layout UI tricks to
  compensate for API batch ordering.
- When the SDK omits a transaction ID on fetched/history messages, derive a
  deterministic fallback ID from thread ID, type, timestamp, and sanitized text;
  never use a random ID in `MessageRenderer`, because the same message will
  duplicate after realtime/history reconciliation.
- Resolve user-vs-agent direction from explicit sender/author/from IDs plus
  `senderType`, `messageDirection`, `direction`, `source`, and `origin` before
  falling back to `message.isOutgoing`. Treat top-level `userId`, `appUserId`,
  and `customerId` as possible recipients unless paired with explicit sender
  metadata. Platform/agent/bot/business/alert messages align left.
- Generic-template attachments can contain multiple elements. Treat those
  elements as cards in one message-level carousel; do not split them into
  separate chat rows.
- Quick replies, card buttons, and form submit controls are stateful. Keep them
  enabled while the postback/form submit is publishing, then disable the source
  message's controls only after the callback succeeds. Leave controls enabled
  when the callback fails so the user can retry.
- Form-template attachments must render editable fields. Use text inputs for
  free-form values, option chips for choice lists, required-field validation,
  and a submit button that publishes a structured JSON postback payload.
- Compose `LazyColumn`/`LazyRow` keys must remain unique even when SDK messages
  reuse transaction IDs or multiple buttons share the same title. Include the
  list index plus stable message/card/action identity in keys.
- Real-time messages may be held for up to 24 hours while the app is
  disconnected.
- Server-Side Inbox must be enabled to recover messages beyond real-time
  delivery behavior.

Advanced implementation backlog:

- Add a production file picker and upload arbitrary user-selected media.
- Replace `DefaultMessageStore` with a custom store only when product retention,
  compliance, or observability requirements justify it.
- Add tenant-specific foreground notification view binders/styles for custom
  banner and modal layouts.
- Add JWT/security token refresh and server-backed identity/account linking for
  production account switching.
- Typing indicator publishes are throttled by the SDK to at most one start/stop
  event every five seconds.

## Message Rendering Coverage

Render and QA these types:

- Text messages.
- Push alert/notification messages.
- Read, delivered, clicked, deleted, and failed statuses.
- Typing start/stop.
- Thread create/update/reopen/close.
- Quick replies and button postbacks through `createPostbackMessage`.
- Generic templates with elements and buttons, rendered as one horizontal card
  carousel inside a single message bubble.
- Form templates with text, name, email, integer, decimal, date, dropdown, and
  multi-select dropdown fields, including user input and submit behavior.
- Media/file/image/audio/video attachments.
- Location attachments.
- Interactive push actions through `PushInteractiveData`.

## QA Matrix

- Fresh install with no config: app shows configuration-required state.
- Add config: app starts without crash.
- Login with User ID: device registration succeeds or shows actionable error.
- Force app restart: registration state is checked again.
- Connect: connection listener moves through expected states.
- Create thread: active conversation ID appears.
- Send text: one outgoing bubble appears, moves from sending to sent/failed,
  and is not duplicated by publish callbacks, listener echoes, or history fetch.
- Generic template: one inbound message with multiple elements appears as a
  horizontally scrollable carousel, and card buttons publish postbacks.
- Interactive disable: card buttons, quick replies, and form submit controls
  disable only after the postback callback succeeds; a failed callback keeps the
  controls available for retry.
- Form input: text/date/number/dropdown fields accept values, required fields
  gate submit, and submit publishes a structured JSON form postback payload.
- Duplicate labels: repeated actions such as "See Details" do not crash
  Compose lazy lists because keys include index and stable identity.
- Receive message: listener renders inbound bubble when it belongs to the
  active thread, and updates the inbox preview/unread state when it belongs to
  another thread.
- Reconnect recovery: after In-App Messaging reconnects, the app refreshes the
  thread inbox and selected thread history so messages missed while disconnected
  are recovered from local store/server-side inbox.
- Message direction: resolve from logged-in User ID plus SDK JSON
  sender/source/direction fields before falling back to `isOutgoing`, so user
  messages render right and agent/platform messages render left.
- Receipt reconciliation: delivery/read/clicked receipt events update the
  matching outgoing bubble through `relatedTransactionId` or transaction ID
  instead of appearing as separate chat rows.
- Fetch history: messages reload after process death without seeded demo
  welcome/card placeholders appearing in real SDK threads.
- Fetch order: open a thread, receive messages, leave and re-enter it, and
  confirm the transcript remains oldest-to-newest with the newest message at
  the bottom after realtime, delayed reconciliation, and pagination fetches.
- Load older threads: uses `fetchThreads` with the oldest loaded thread date.
- Thread inbox UI: search/filter works, rows look like a modern chat list, and
  each row shows avatar, presence, preview, time, unread, and status metadata.
- Thread navigation UI: tapping a row opens a dedicated selected-thread chat
  screen with its own back button, header, SDK-driven quick replies/actions,
  and composer. Do not add static demo shortcut chips to opened threads.
- New conversation UI: the title field is hidden until the header `+` action
  opens a modal, then Create calls `createThread`.
- Load older messages: uses `fetchMessages` with the oldest loaded message
  date and preserves existing optimistic message rows.
- Delete message: calls `deleteMessage`, then removes the row only on success.
- Local store/sync: configures `DefaultMessageStore` and
  `MessageSynchronizationPolicy` before connecting.
- Media upload/download: thread attachment flows upload selected media, publish
  attachments, download remote media, and regenerate media URLs through
  `mediaFileManager`.
- Profile switch: update/remove Customer ID and unregister to return to login
  for a new User ID.
- Profile details: show the current App ID from `WebexConnectConfig.properties`
  or legacy `IMIconnectConfig.properties`, SDK version, started/registered/
  connected state, logger/security-token integration notes, editable
  `MessageSynchronizationPolicy` thread/message limits, and copyable push
  token so support/QA can verify global SDK setup.
- Typing: start/stop calls are throttled in UI.
- Read/delivered/clicked: status APIs fire for relevant messages/actions.
- Push token: token listener records token.
- Notification permission: Android 13+ prompt is user initiated.
- Push data: `isConnectMessageData` gates SDK processing.
- Notification channel: default channel exists.
- Custom notification: builder callback changes visible notification content
  and uses the generated Webex small icon.
- Push actions and foreground display: action handler records action callbacks,
  foreground notification callback shows an in-app banner, and delivered/read
  status updates are sent when transaction IDs are available.
- Launcher branding: manifest icon and roundIcon resolve to the bundled Webex
  mark, and in-app UI surfaces reuse `webex_logo` instead of generic placeholder
  icons.
- UI automation: test IDs find login field, login button, composer, send
  button, message list, notification icon, notification center, support entry,
  workflow cards, agent chat, notification button, and QA drawer.

## Source Links

- https://developers.webexconnect.io/docs/android-modularization-sdk-quick-start-guide
- https://developers.webexconnect.io/docs/android-core-modularization-sdk
- https://developers.webexconnect.io/docs/android-push-modularization-sdk
- https://developers.webexconnect.io/docs/android-inapp-modularization-sdk
- https://developers.webexconnect.io/docs/push-messaging-guide
- https://developers.webexconnect.io/docs/in-app-messaging-guide-modularization
- https://developers.webexconnect.io/docs/inappmessaging
- https://developers.webexconnect.io/reference/live-chat-in-app-messaging-api
- https://developers.webexconnect.io/docs/webexconnectinappmessageattachmentstemplates
- https://developers.webexconnect.io/docs/sdk-pushmessaging
- https://developers.webexconnect.io/docs/android-sdk-release-notes
