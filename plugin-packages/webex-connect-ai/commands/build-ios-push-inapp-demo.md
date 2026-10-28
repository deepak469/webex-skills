---
name: build-ios-push-inapp-demo
description: Build or update a Webex Connect iOS Push and In-App Messaging demo app with SPM, configuration prompts, and QA.
---

Use the `webexconnect-ios-push-inapp-messaging-builder` skill from this plugin.
Swift Package Manager is the only dependency manager for this generated iOS app.

Create or update a native iOS application named `Webex Connect Demo` that
supports the selected scope:

- Push messaging only
- In-app messaging only
- Both push and in-app messaging

When this command is invoked from the plugin UI and the user has not already
provided build choices, stop and ask for the selections in the conversation UI
before running any generator script. Do not silently generate with placeholder
configuration when the missing value is a required build choice.

Ask for these values as one concise grouped prompt:

- Capability: Push, In-App, or Both
- `WebexConnectConfig.plist`, legacy `IMIConnectConfig.plist`, or `appId`,
  `clientKey`, and environment
- iOS bundle identifier
- Apple signing team, or confirmation that signing will be configured later
- APNs environment: development or production, only when Push is selected
- Whether to resolve SPM packages or run an Xcode build now

Do not ask for FCM or HMS for iOS. iOS Push uses APNs. User ID is not a
build-time input; keep User ID entry in the running app and use it for device
registration.

After the user answers, run the iOS builder script with explicit flags.
Use `--interactive` only from a real terminal where stdin is a TTY; Codex plugin
tasks should normally collect answers in chat and pass non-interactive
arguments.

Build a production-quality embedded messaging experience, not a plain SDK test
screen. Use the Webex dark token set from the builder: `#0B0F12` canvas,
`#121619` surface, `#1D2227` elevated surface, `#3492EB` active blue,
`#17C7A8` success teal, and `#F55868` alert red. The generated app should
include a realistic customer shell, safe-area aware top bars, compact thread
conversation UI, conversation list, modal thread creation, profile/settings,
closed-thread state, reopen action, message pagination, receive-message
rendering, media upload/download, APNs token diagnostics, and QA verification.

Keep customer-facing top bars branded and clean. Do not show App ID, User ID,
capability, APNs environment, or route text there; show App ID, SDK status,
APNs token, and tenant diagnostics in Profile/settings.

In the dedicated thread conversation screen, follow the opened/closed thread
reference: back button, Webex logo, selected SDK thread title, compact copyable
thread ID, dot status line, and three-dot menu. Do not show metadata pills, a
redundant notification bell, extra top whitespace, or a separate status card.
Put View details, Search in conversation, and Close/Reopen thread in the
overflow menu. Closed threads must preserve history, show a centered lock
recovery state, and omit quick actions/composer until reopened.

Build the chat composer as one compact bottom rail using the app's dark Webex
Connect tokens: circular plus attachment action, subtle divider, inline text
entry, and send arrow. Keep attachment upload wired to the iOS picker and SDK
media flow.

Render the current Webex Connect message surface: text, extras, quick replies,
thread alerts, typing indicators, read/delivered/clicked/deleted receipts,
push alert rows, location, generic-template carousels, form templates with
editable inputs, and file/image/audio/video attachments with inline image
previews. Do not render SDK object dumps, APNs tokens, transaction IDs,
callback data, or raw JSON wrappers as customer chat text.

For received messages, render current-user messages on the right and
agent/platform messages on the left by using the logged-in User ID plus SDK
sender/source/direction metadata before falling back to an SDK outgoing flag.
Delivery, read, and clicked receipts must update the existing outgoing bubble
status (`Sent` -> `Delivered` -> `Read`) in one footer and must not appear as
their own chat rows.

Realtime listener events and fetched history must go through one ordered merge
path. Show active-thread realtime messages immediately, schedule one short
debounced `fetchMessages` reconciliation after visible receive or successful
send, and keep the transcript oldest-to-newest with the newest message at the
bottom.
