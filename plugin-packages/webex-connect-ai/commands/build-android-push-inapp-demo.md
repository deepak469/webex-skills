---
name: build-android-push-inapp-demo
description: Build or update a Webex Connect Android Push and In-App Messaging demo app with configuration prompts and QA.
---

Use the `webexconnect-android-push-inapp-messaging-builder` skill from this plugin.

Create or update a native Android application named `Webex Connect Demo` that
supports the selected scope:

- Push messaging only
- In-app messaging only
- Both push and in-app messaging

When this command is invoked from the plugin UI and the user has not already
provided build choices, stop and ask for the selections in the conversation UI
before running any generator script. Do not silently default to FCM or generate
an app first and leave provider choice as a follow-up.

Ask for these values as one concise grouped prompt:

- Capability: Push, In-App, or Both
- Provider: FCM or HMS when Push is selected
- `appId`, `clientKey`, and environment, or a `WebexConnectConfig.properties`
  path; accept legacy `IMIconnectConfig.properties` for existing projects
- `google-services.json` or `agconnect-services.json` when Push is selected
- Package/application ID
- Build type: debug or release
- Whether to build the APK now

If the user wants UI choices too, ask for these bounded experience selections:

- Demo scenario: retail/service support default, travel, financial services,
  healthcare, or custom product/order labels
- Feature coverage: standard chat, full rich messaging default, or QA-heavy SDK
  coverage
- Thread policy: active only, or closed/reopen plus announcement read-only
  threads
- Media handling: sample media only, or Android picker plus upload/download/URL
  regeneration
- Notification UX: notification center only, or foreground banners plus push
  actions when Push is selected
- SDK source: latest Maven Central, pinned version, or local/GitHub SDK checkout
- QA depth: static verifier, Gradle build, or emulator smoke run

After the user answers, run the Android builder script with explicit flags.
Apply optional experience selections by editing the generated Compose UI, demo
data, QA checklist, and build notes when there is no matching script flag.
Use `--interactive` only from a real terminal where stdin is a TTY; Codex
plugin tasks should normally collect answers in chat and pass non-interactive
arguments.

Build a production-quality embedded messaging experience, not a plain SDK test
screen. Use the supplied Figma screen structure and the Webex dark token set:
`#1A1A1A` canvas, `#262626` surface, `#303030` elevated surface, `#3492EB`
active blue, `#17C7A8` success teal, and `#F55868` alert red. The generated app
should include a realistic customer shell, safe-area aware top bars, compact chat bubbles,
conversation list, modal thread creation, thread detail, closed-thread state,
reopen action, message pagination, receive-message rendering, media
upload/download, foreground notification banners, profile switching, and QA
verification.

Keep the customer-facing app top bar branded and clean. Do not show User ID,
capability, provider, or route text there; show App ID, provider, SDK status,
and tenant diagnostics in Profile/settings.

In the dedicated thread conversation screen, follow the opened/closed thread
reference: back button, Webex logo, `Webex Connect Demo` title, dot status
line, and three-dot menu. Do not show metadata pills, a redundant notification
bell, or a separate status card. Put View details, Search in conversation, and
Close/Reopen thread in the overflow menu. Closed threads must preserve history,
show a centered lock recovery state, and omit quick actions/composer until
reopened.

Build the chat composer as one compact bottom rail that follows the app's
existing dark Webex Connect tokens: circular plus attachment action, subtle
divider, inline text entry, and send arrow. Keep attachment upload wired to the
Android picker and SDK media flow.

For APK generation, use `./gradlew` only when the generated project has a
trusted Gradle wrapper. Otherwise require local Gradle on PATH and run the same
task with `gradle`. The plugin must not silently claim an APK was built when the
environment lacks both.

Render the current Webex Connect message surface: text, extras, quick replies,
thread alerts, typing indicators, read/delivered/clicked/deleted receipts,
push alert rows, location, generic-template carousels, form templates with
editable inputs, and file/image/audio/video attachments with inline image
previews. Do not render SDK object dumps, device or push tokens, transaction
IDs, callback data, or raw JSON wrappers as customer chat text. Do not include
calling features.

For received messages, render current-user messages on the right and
agent/platform messages on the left by using the logged-in User ID plus SDK
sender/source/direction metadata before falling back to `isOutgoing`. Delivery,
read, and clicked receipts must update the existing outgoing bubble status
(`Sent` -> `Delivered` -> `Read`) in one footer and must not appear as their own
chat rows.

Realtime listener events and fetched history must go through one ordered merge
path. Show active-thread realtime messages immediately, schedule one short
debounced `fetchMessages` reconciliation after visible receive or successful
send, and keep the transcript oldest-to-newest with the newest message at the
bottom.
