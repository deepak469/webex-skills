---
name: build-livechat-widget
description: Build a browser live chat widget using the latest Webex Connect JavaScript SDK and required dependencies.
---

Use the `webexconnect-livechat-widget` skill from this plugin.

When this command is invoked from the plugin UI and the user has not already
provided the widget build choices, stop and ask for the selections in the
conversation UI before installing SDK assets, copying the starter, or writing
widget code. Do not scaffold first and ask for required configuration as a
follow-up.

Ask for these values as one concise grouped prompt:

- Widget target: new vanilla/static widget or an existing framework app, plus
  the target entry point
- Existing `imi-environments.js`, or `appId`, `clientKey`, and environment
  values for an example config
- Visitor identity strategy: host-supplied User ID/Customer ID, an identity
  callback, or anonymous/guest; actual runtime IDs stay in the widget/host
- Browser push: enabled or disabled; when enabled, Firebase web config and
  service-worker/manifest paths
- Site base path plus SDK asset and service-worker root paths
- SDK source: latest GitHub distribution or a supplied local `dist.zip`
- Whether to install/copy the widget now and run static/build verification

Do not ask the user to paste security tokens or app secrets. If tenant config
is not available yet, create an example config and a visible
configuration-required state, but do not claim the widget is connected or
production-ready. After the user answers, proceed with the selected scaffold
and integration path.

Create a browser live chat widget that installs the Webex Connect JavaScript SDK from the latest supported source, adds required dependencies, creates a configuration file from user inputs, and implements send/receive chat behavior with supported message types. Include verification steps for SDK loading, initialization, registration, connection state, incoming messages, outgoing messages, attachments, quick replies, forms, cards, carousel rendering, and callback-driven action disabling.

The starter must use a two-stage page flow:

- The first page is a static login/identity form for User ID, optional Customer
  ID, and optional stable Device ID. Do not show the widget, thread list, New
  conversation button, or composer until login succeeds.
- After login, initialize/register the SDK for that identity and reveal the
  Chat launcher. If the identity changes, isolate storage and SDK registration
  before fetching threads.

The generated widget must provide a conversation inbox, not only a single
text transcript. Use the dark Webex visual language used by the Android and
iOS examples (dark surfaces, blue primary actions, teal connection state, and
rounded cards):

- Toggle the widget when the visitor clicks the Chat launcher: open it when
  hidden and hide it when open. Keep the widget in a single-column flow: show
  the conversation list first, then replace it with the selected conversation
  and provide a back action.
- Render the New conversation title prompt inside the widget panel as an
  in-widget view; do not use a page-level or detached overlay.
- Put settings and diagnostics inside the widget view. Include a header
  settings icon and an expand icon that switches the widget to full-screen
  mode; do not render SDK settings outside the widget.

- Show a `New conversation` action that first asks the visitor for a thread
  title, then creates an `IMI.ICThread` with that title and selects the
  returned thread. Do not use `New Conversation` as the persisted title.
- Load and show the existing thread list with `fetchThreads(offset, limit,
  callback)`.
- Let the user click an existing thread and load its older messages with
  `fetchMessages(threadId, beforeDate, limit, callback)` before showing the
  composer for that thread.
- Keep the composer at the bottom of the selected conversation view, with a
  rounded message field and send action; do not show the composer on the inbox
  view before a thread is selected or created.
- Provide thread lifecycle actions for closing and reopening the selected
  thread using `closeThread` and `updateThread`/the SDK's reopen operation;
  disable the composer while a thread is closed.
- Provide a settings/diagnostics view showing non-sensitive SDK state such as
  SDK version, application ID, registration, and connection status. Never
  display security tokens.
- Keep the selected thread and its message history separate from other
  threads; update unread counts/previews when a message arrives in another
  thread.
- Scope selected-thread storage to the active User ID/Customer ID and verify
  the SDK registration belongs to that identity. On identity changes,
  unregister and register the new visitor before fetching threads so one user
  never sees another user's inbox.
- Render the SDK-supported customer-visible message surface: text, file,
  image, audio, video, location, generic-template card carousels, editable
  form templates, quick replies, template postbacks, alerts, typing state,
  and receipt status updates. Do not display raw SDK objects or JSON dumps.
- Deduplicate overlapping SDK attachment/media/interactive getters so a form,
  card, carousel, or attachment is rendered once per received message.
