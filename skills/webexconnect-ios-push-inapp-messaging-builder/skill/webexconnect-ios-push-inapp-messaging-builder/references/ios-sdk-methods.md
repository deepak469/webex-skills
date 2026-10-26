# iOS Modular SDK Reference

Use this reference when building a `Webex Connect Demo` iOS app for Push
Messaging and In-App Messaging. Prefer the Webex Connect docs for exact
signatures and keep generated code SPM-first.

## Version And Products

Swift Package URL:

- `https://github.com/webex/wxconnect-ios-sdk`

Default version:

- `3.1.0`

Products:

- `WebexConnectCore`: SDK startup, device registration, config, profile,
  logging, and shared lifecycle.
- `WebexConnectPush`: APNs token registration, push receipt, notification
  display/action handling, and push token diagnostics.
- `WebexConnectInAppMessaging`: realtime in-app chat, threads, messages,
  local store, sync policy, media, templates, quick replies, and status
  receipts.

Do not generate Podfiles. The builder should create an Xcode app target using
SPM package products.

## Required Inputs

- Capability: `push`, `inapp`, or `both`.
- Bundle ID.
- Webex Connect config: `WebexConnectConfig.plist`, legacy
  `IMIConnectConfig.plist`, or explicit `appId`, `clientKey`, and environment.
- Apple signing team or a note to configure signing later.
- APNs environment when Push is selected: `development` or `production`.
- Optional SDK version override.
- Optional build/resolve flag.

Do not ask for FCM or HMS. iOS push uses APNs.

## Core Startup

Generated apps should:

- Detect whether `WebexConnectConfig.plist` or legacy `IMIConnectConfig.plist`
  is bundled before calling startup.
- Start the core module once on launch.
- Register a user through `DeviceProfile`.
- Store the selected User ID locally so app relaunch can restore registration.
- Expose unregister/profile switching in Profile.
- Keep App ID, SDK version, registration state, connection state, APNs token,
  sync limits, and last SDK status in Profile/settings.

Representative APIs:

- `WebexConnectProvider.instance`
- `WebexConnectProvider.instance.startup(completionHandler:)`
- `WebexConnectProvider.instance.shutdown(completionHandler:)`
- `WebexConnectProvider.instance.isRegistered`
- `DeviceProfile.defaultDeviceId()`
- `DeviceProfile(deviceId:userId:)`
- `WebexConnectProvider.instance.register(deviceProfile:completionHandler:)`
- `WebexConnectProvider.instance.unregister(completionHandler:)`

## Push Wiring

Generated Push builds should:

- Import `WebexConnectPush`.
- Use a `UIApplicationDelegate` bridge for SwiftUI apps.
- Set `pushMessagingDelegate`, `pushTokenDelegate`, and `actionsDelegate`.
- Request notification authorization.
- Call `UIApplication.shared.registerForRemoteNotifications()`.
- Forward APNs device tokens with `processPushToken(_:type:completionHandler:)`.
- Let SDK method swizzling and push delegates handle Webex Connect push
  message callbacks.
- Capture and expose the APNs token in a separate copyable Profile card.
- Keep notification actions out of the chat transcript unless the SDK payload
  is an actual user-visible push alert row.

Representative APIs:

- `PushMessagingProvider.instance`
- `PushMessagingProvider.instance.pushMessagingDelegate = ...`
- `PushMessagingProvider.instance.pushTokenDelegate = ...`
- `PushMessagingProvider.instance.actionsDelegate = ...`
- `PushMessagingProvider.instance.requestNotificationPermission()`
- `PushMessagingProvider.instance.processPushToken(_:type:completionHandler:)`
- `PushMessagingProvider.instance.foregroundNotificationPresentationOptions = ...`
- `PushMessagingProvider.instance.sendMessageStatus(forTransIds:status:completionHandler:)`
- `PushMessagingDelegate.didReceiveMessage(message:fromTap:)`
- `PushTokenDelegate.didUpdatePushToken(_:type:)`
- `PushActionsDelegate.handleAction(_:withIdentifier:forMessage:responseInfo:)`

For production signing, the generated app must remind developers to enable
Push Notifications and Background Modes with Remote notifications in Xcode and
upload APNs credentials to the Webex Connect app asset.

## In-App Messaging Wiring

Generated In-App builds should:

- Import `WebexConnectInAppMessaging`.
- Set `DefaultMessageStore` before connecting.
- Set `MessageSynchronizationPolicy(mode:maxThreads:maxMessagesPerThread:)`
  before connecting. Default to `limited`, `50`, and `50`.
- Assign `InAppMessagingProvider.instance.delegate`.
- Connect after device registration succeeds.
- Disconnect during sign-out/profile switching.

Representative APIs:

- `InAppMessagingProvider.instance`
- `InAppMessagingProvider.instance.messageStore = DefaultMessageStore(...)`
- `MessageSynchronizationPolicy(mode: .limited, maxThreads: 50, maxMessagesPerThread: 50)`
- `InAppMessagingProvider.instance.messageSynchronizationPolicy = policy`
- `InAppMessagingProvider.instance.delegate = ...`
- `try InAppMessagingProvider.instance.connect()`
- `try? InAppMessagingProvider.instance.disconnect()`
- `InAppMessagingDelegate.didReceiveInAppMessage(_:)`
- `InAppMessagingDelegate.didChangeConnectionStatus(_:)`

## Thread APIs

Generated apps should maintain one local observable thread list and merge SDK
updates into it.

Representative APIs:

- `InAppMessagingProvider.instance.fetchThreads(beforeDate:limit:category:completionHandler:)`
- `InAppMessagingProvider.instance.fetchThread(forThreadId:completionHandler:)`
- `InAppThread()`
- `InAppThread.title`
- `InAppMessagingProvider.instance.createThread(_:completionHandler:)`
- `InAppMessagingProvider.instance.updateThread(_:completionHandler:)`
- `InAppThread.type`
- `InAppThread.status`
- Conversation threads are writable. Announcement threads are read-only.
- Statuses include active, inactive, and closed.

Fetch threads:

- On startup after registration.
- When app becomes active.
- On pull-to-refresh.
- After create/close/reopen succeeds.
- After connection restore.
- After receiving a message for another thread.

## Message APIs

Generated apps should load cached history first when available, then fetch from
the SDK/server. Realtime listener messages and fetched messages must be merged
through the same de-duplication and ordering path.

Representative APIs:

- `InAppMessagingProvider.instance.fetchMessages(forThreadId:beforeDate:limit:completionHandler:)`
- `InAppMessage()`
- `message.thread = selectedThread`
- `message.message = text`
- `InAppMessagingProvider.instance.publishMessage(_:completionHandler:)`
- `InAppMessagingProvider.instance.sendMessageStatus(for:status:completionHandler:)`
- `InAppMessagingProvider.instance.publishTypingIndicator(on:typing:completionHandler:)`
- `InAppMessageStatus.sent`
- `InAppMessageStatus.delivered`
- `InAppMessageStatus.read`

Message merge rules:

- Use SDK message ID or transaction ID as the primary identity.
- Use a short-lived outgoing fingerprint of text, thread ID, created-at window,
  and user ID to reconcile publish echoes.
- Do not append duplicate local rows when the SDK returns the sent message.
- Render delivery/read/clicked/deleted receipts by updating the existing
  outgoing bubble footer only.
- Sort every merged transcript oldest-to-newest by SDK `submittedAt` first and
  `createdAt` second. Preserve insertion order for equal timestamps and keep
  the newest message at the bottom without reversing the visual list.

Direction rules:

- Current user messages render on the right.
- Agent/platform/backend messages render on the left.
- Use logged-in User ID plus SDK sender/source/direction metadata before
  falling back to `isOutgoing`.
- Receipt, typing, thread-update, deleted, and alert system events must not be
  treated as current-user messages just because a top-level user identifier is
  present.

Realtime rules:

- Open-thread inbound message: merge immediately, send Delivered, send Read
  only when that thread is visible, then schedule one short debounced
  `fetchMessages` reconciliation for that same thread.
- Other-thread inbound message: update inbox preview/unread, fetch that thread
  metadata, and leave it unread until opened.
- Successful send or attachment publish: keep the optimistic row visible,
  update it to Sent, then use the same short delayed reconciliation fetch so
  delayed SDK echoes or server-side inbox updates update rather than duplicate
  the row.
- Connection restored: fetch threads and fetch the visible thread's messages.
- Never seed static demo messages inside a real SDK thread while SDK history is
  loading.

## Rich Message Rendering

Render the Webex Connect message surface as customer UI:

- Text and extras.
- Quick replies.
- Generic cards and carousel.
- Form templates with editable fields, required validation, and submit
  postbacks.
- Thread alerts and thread updates.
- Typing indicators.
- Delivery/read/clicked/deleted receipts.
- Push alert rows when applicable.
- File, image, audio, video, and location attachments.

Do not show SDK object dumps, raw JSON wrappers, transaction IDs, callback
payloads, device tokens, APNs tokens, or debug diagnostics as chat text.

## Media APIs

Generated apps should support thread-context media handling:

- Select a file through PhotosPicker or UIDocumentPicker.
- Stage selected bytes in a temporary file when needed.
- Upload files through `mediaFileManager`.
- Publish the returned `mediaId` as an `InAppMediaAttachment`.
- Download media and refresh media URLs from a selected thread/message via
  `mediaFileManager`.

Representative APIs:

- `InAppMediaAttachment`
- `InAppMessagingProvider.instance.mediaFileManager.upload(fileURL:progressHandler:completionHandler:)`
- `InAppMessagingProvider.instance.mediaFileManager.downloadFile(at:progressHandler:completionHandler:)`
- `InAppMessagingProvider.instance.mediaFileManager.regenerateMediaURL(_:completionHandler:)`

## UI Expectations

- Use SwiftUI with `TabView`, `NavigationStack`, sheets, and a single app
  dependency graph.
- Use explicit Webex dark tokens:
  `#0B0F12`, `#121619`, `#1D2227`, `#2A3036`, `#3492EB`, `#17C7A8`, `#F55868`.
- Keep thread conversations compact and safe-area aware. No duplicated header
  panels or large blank status-bar gaps.
- The opened thread header shows title, compact thread ID with copy action,
  state dot, and overflow menu.
- The closed thread screen keeps history, shows a lock state and Reopen button,
  and hides the composer.
- Composer uses one bottom rail with plus, divider, text field, and send arrow.
- Profile keeps global settings only, including App ID, SDK state, APNs token,
  editable sync limits, and sign-out/register controls.

## QA Checklist Anchors

Generated files should include stable view names and labels so a reviewer can
find them quickly:

- `WebexConnectDemoApp`
- `WebexConnectRuntime`
- `ConversationInboxView`
- `ThreadConversationView`
- `ThreadHeaderView`
- `ThreadMenu`
- `MessageBubbleView`
- `CardCarouselView`
- `QuickReplyRow`
- `FormTemplateView`
- `ComposerView`
- `ProfileView`
