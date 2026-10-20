---
name: webexconnect-ios-push-inapp-messaging-builder
description: >
  Build or repair native iOS apps that use the Webex Connect SDK for Push Notifications or In-App Messaging, including registration, chat, notifications, and QA.
---

# Webex Connect iOS Push and In-App Messaging Builder

## Overview

Use this skill to build or update a native iOS app named `Webex Connect Demo`
that demonstrates Webex Connect Push and In-App Messaging in a production-like
customer app. Generate files and QA checks; do not stop at documentation.

Read `references/ios-sdk-methods.md` before implementing SDK wiring,
realtime message handling, push callbacks, message renderers, media, templates,
or QA automation.

As of the Webex Connect developer docs checked on September 2, 2026, the iOS
modular SDK supports Swift Package Manager. Use the package repository
`https://github.com/webex/wxconnect-ios-sdk` and the current documented SDK
version `3.1.0` unless the user requests a pinned alternate version. Do not
generate a Podfile or CocoaPods workflow.

## Build-Time Input Gate

Before generating or building the app, collect these build-time inputs in the
Codex/plugin conversation UI when they are not already present in the user's
request:

- Capability: Push, In-App, or Both.
- Webex Connect app asset config: either `WebexConnectConfig.plist`, legacy
  `IMIConnectConfig.plist`, or `appId`, `clientKey`, and environment values.
- iOS bundle identifier.
- Apple signing team or instruction to configure signing later in Xcode.
- APNs environment: development or production, only when Push is selected.
- Whether to resolve SPM packages or run an Xcode build now.

Provider choice is not a build-time selector on iOS; Push uses APNs.
Do not ask for FCM or HMS for iOS. User ID is not a build-time input; keep User ID entry
inside the running app login/profile flow and use it for device registration.

When the user says only "create iOS app" or selects this builder from the
plugin without details, ask one grouped question covering capability, bundle
ID, Connect config, APNs environment, signing, and build/resolve preference.
After the user answers, pass explicit script flags. Use `--interactive` only
from a real terminal where `stdin` is a TTY.

## Default Build Workflow

1. Inspect the target iOS app structure: Xcode project/workspace, SwiftUI or
   UIKit, bundle ID, signing, app delegate lifecycle, capabilities, assets, and
   existing Swift Package dependencies.
2. Generate or update the app using Swift Package Manager only:

   ```bash
   python3 path/to/webexconnect-ios-push-inapp-messaging-builder/scripts/create_ios_demo.py . \
     --capability both \
     --bundle-id com.example.webexconnectdemo \
     --app-id APP_ID \
     --client-key CLIENT_KEY \
     --environment UK \
     --apns-environment development
   ```

3. Add SPM dependency products:
   - `WebexConnectCore` for every generated app.
   - `WebexConnectPush` only when Push is selected.
   - `WebexConnectInAppMessaging` only when In-App is selected.
4. Add `WebexConnectConfig.plist` from the Webex Connect Mobile/Web app asset,
   or generate it from explicit `appId`, `clientKey`, and environment inputs.
   If config is missing, generate `WebexConnectConfig.plist.example` and make
   the app show a configuration-required profile state instead of attempting
   SDK startup.
5. For Push builds, add APNs entitlements, request notification authorization,
   register for remote notifications, forward APNs tokens to the SDK, and
   forward incoming notifications/actions to the SDK.
6. For In-App builds, set up the message store and sync policy before connect,
   assign the SDK delegate, then handle connection status and realtime messages
   through delegate callbacks.
7. Verify the generated app with:

   ```bash
   python3 path/to/webexconnect-ios-push-inapp-messaging-builder/scripts/verify_ios_demo.py .
   ```

## Production UI Requirements

- Use the bundled Webex logo for app branding and chat avatar.
- Keep the customer-facing top bar branded and clean. Do not show App ID,
  user ID, capability, provider, or route text in the top bar.
- Keep App ID, SDK version, started/registered/connected state, APNs push
  token, message-store limits, and global diagnostics in Profile/settings.
- Profile must expose editable thread and message sync limits, defaulting to
  `50` threads and `50` messages per thread, and a separate copyable APNs token
  card.
- Thread inbox must show real SDK threads with search, filters, create modal,
  pagination, row-open navigation, unread count, title, preview, and closed or
  announcement state where applicable.
- After `createThread` succeeds, immediately merge the returned thread into
  local state before refreshing from the SDK so the row stays visible while the
  backend list catches up.
- Tapping a thread opens a dedicated chat screen for that exact SDK thread.
  The header must show back button, Webex logo, selected thread title,
  copyable compact thread ID, dot status line (`Active`, `Thread closed`,
  `Announcement`, or `Connecting`), and three-dot menu.
- Do not show metadata pills, a redundant notification bell, a selected-thread
  status card, or extra empty top space above the message list.
- Put View details, Search in conversation, and Close/Reopen thread in the
  overflow menu. Closed threads preserve history, show a centered lock recovery
  state, and hide quick actions/composer until reopened.
- Build one compact bottom composer rail: circular plus attachment action,
  subtle divider, inline text entry, and send arrow. Use safe-area and keyboard
  padding so no bottom gap remains.
- Render user messages on the right and agent/platform messages on the left.
  Decide direction from the logged-in User ID plus SDK sender/source/direction
  metadata before falling back to any SDK outgoing flag.
- Delivery/read/clicked/deleted receipts update the existing outgoing bubble
  footer (`Sent` -> `Delivered` -> `Read`) in one place and never render as
  standalone customer-visible message rows.
- Never show SDK object dumps, APNs tokens, transaction IDs, callback data,
  concatenated diagnostics, or raw JSON wrappers inside the chat transcript.
- Render dynamic SDK payloads: text, extras, alert/thread updates, typing
  indicators, quick replies, generic card templates, carousel, forms, location,
  file/image/audio/video attachments, push alert rows, and status receipts.
- Generic-template elements render as one carousel message with horizontal
  cards and inline images when URLs are present.
- Forms render as editable controls with required-field validation and submit
  postback. Disable controls only after the publish callback succeeds.
- Attachment action opens the iOS picker, uploads selected media through the
  SDK, publishes the returned media reference, and supports download/refresh
  media URL from the thread context.

## Realtime And Fetch Policy

- Configure the local message store before connecting so realtime and fetched
  history reconcile through one store.
- Fetch threads on app startup, foreground resume, pull-to-refresh, after
  create/close/reopen, and after In-App connection restore.
- Fetch messages when opening a thread, during pagination, after connection
  restore for the visible thread, and after an other-thread realtime message
  updates the inbox.
- When a realtime message belongs to the open thread, merge it into the visible
  transcript immediately, send Delivered, and send Read only if the thread is
  visible.
- After visible-thread realtime receive or successful send, schedule one short
  debounced `fetchMessages` reconciliation for that thread so local store and
  Server-Side Inbox lag does not leave the transcript stale.
- When a realtime message belongs to another thread, update that thread's
  preview/unread state and do not mark it read until the user opens it.
- Normalize all realtime and fetched message batches through one merge path,
  sorted oldest-to-newest by SDK `submittedAt`/`createdAt`; preserve insertion
  order when timestamps are equal and scroll to the newest message without
  reversing the visual list.
- Never seed welcome/card demo rows into a real SDK thread while history is
  loading. Show loading, then an empty state if the SDK returns no messages.
- De-duplicate by SDK transaction ID/message ID and by a short-lived outgoing
  fingerprint so publish echoes update the optimistic row instead of appending
  a duplicate.

## CANNOT

- CANNOT generate a Podfile, use CocoaPods as the default dependency manager,
  or ask users to install SDK pods.
- CANNOT ask for Android-only push providers such as FCM or HMS.
- CANNOT claim an `.ipa` or simulator build succeeded unless Xcode actually
  completed the selected build.
- CANNOT render raw SDK payloads, tokens, transaction IDs, or debug values as
  chat messages.
- CANNOT show static demo shortcut chips in an open SDK thread; quick replies
  and actions must come from SDK message payloads.
- CANNOT mark other-thread inbound messages as read while the user is viewing
  a different thread.

## Source Links

- iOS Quick Start Guide: https://developers.webexconnect.io/docs/ios-quick-start-guide
- iOS SDK SPM integration: https://developers.webexconnect.io/docs/integrating-the-ios-sdk-with-swift-package-manager
- iOS Core modular SDK: https://developers.webexconnect.io/docs/webex-connect-ios-core-modularization-sdk-300
- iOS Push modular SDK: https://developers.webexconnect.io/docs/ios-push-modularization-sdk-300
- iOS In-App Messaging modular SDK: https://developers.webexconnect.io/docs/ios-core-in-app-messaging-modularized-sdk-300
- iOS SDK release notes: https://developers.webexconnect.io/docs/ios-sdk-release-notes

## Next Skills

- Use `webex-connect-setup` when tenant, app asset, credential, JWT, or
  regional endpoint setup is missing.
- Use `webexconnect-push-sendmessage` for server-side push payload creation.
- Use `webexconnect-livechat-inapp-sendmessage` for server-side in-app message
  and rich-template payload creation.
- Use `webexconnect-webhooks-events` for receipts, callbacks, and event
  pipeline validation.
