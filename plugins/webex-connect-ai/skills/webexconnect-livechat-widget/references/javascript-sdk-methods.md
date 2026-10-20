# JavaScript SDK Method Reference

Use this reference when building or reviewing a Webex Connect browser Live Chat
Widget. Prefer the current Webex Connect docs for exact signatures when the SDK
version changes.

## Table of Contents

- Asset and setup checklist
- Core `IMI.IMIconnect` methods
- `IMI.ICDeviceProfile`
- `IMI.ICMessaging` methods
- Receiver callbacks
- Message object methods
- Thread, topic, and attachment classes
- Interactive and template classes
- Enums and message types
- Source links

## Asset and Setup Checklist

- Create a Web Application asset in Webex Connect.
- Configure browser push only when needed. For Chrome/Firefox this usually
  includes FCM setup and Firebase compat scripts.
- Download the latest JavaScript SDK from GitHub:
  `https://github.com/webex/webexconnect-javascript-sdk/releases/latest/download/dist.zip`.
- Add SDK scripts to the site, commonly:
  - `assets/js/webex-connect-sdk.min.js`
  - `assets/js/imi-environments.js`
- Place the service worker file at the path configured by
  `asset.pathConfig.root`. Browser push normally needs service worker scope at
  the website root.
- Place `manifest.json` under the configured assets/manifest path when push is
  enabled.
- Verify `imi-environments.js` has the right `target`, `asset.appId`,
  `asset.appSecret`, `asset.pathConfig.assetPath`, `asset.pathConfig.root`, and
  `imiclient.shouldRequestNotificationPermission` for the environment.
- Do not commit tenant-specific config from production into reusable packages.

The GitHub SDK archive contains SDK runtime assets such as
`webex-connect-sdk.min.js`, `sw.min.js`, and `manifest.json`. It does not
contain the tenant-specific `imi-environments.js`; download that file from the
Webex Connect UI for the relevant Web App asset.

## Core `IMI.IMIconnect` Methods

Use these before messaging APIs:

| Method | Widget use |
| --- | --- |
| `startup()` | Initialize the SDK with the downloaded environment config. |
| `shutdown()` | Clean up the SDK when the host app intentionally stops it. |
| `isRegistered()` | Check registration on each page/app launch. |
| `register(deviceProfile, callback)` | Register the browser/device profile. |
| `unregister()` | Remove registration for logout or account disconnect. |
| `updateProfileData(param, value, callback)` | Update registered `UserId` or `CustomerId`. |
| `removeProfileData(param, callback)` | Remove registered profile data when supported. |
| `setSecurityToken(token)` | Provide the SDK security token/JWT. |
| `registerSecurityTokenListener(callback)` | Handle token expiration/failure. |
| `unRegisterSecurityTokenListener(callback)` | Remove the token listener. |

Avoid deprecated `registerListener` and `unregisterListener` in new code.

## `IMI.ICDeviceProfile`

Create a device profile with a stable browser/device identifier and a user or
customer identifier. The quickstart pattern uses:

```javascript
const profile = new IMI.ICDeviceProfile(deviceId, userId, customerId);
IMI.IMIconnect.register(profile, callback);
```

Generate `deviceId` intentionally. Random per-refresh IDs create duplicate
profiles and poor conversation continuity.

## `IMI.ICMessaging` Methods

Create the singleton with `const messaging = IMI.ICMessaging.getInstance()`.

| Method | Use |
| --- | --- |
| `deleteMessage(messageTransactionId, callback)` | Delete a message transaction from the platform. |
| `connect()` | Establish RTM connection after registration. |
| `disconnect()` | Disconnect RTM connection. |
| `getConnectionStatus()` | Read current `IMI.ICConnectionStatus`. |
| `isConnected()` | Convenience check for connected status. |
| `setICMessagingReceiver(callback)` | Register connection and message callbacks. |
| `publishMessage(message, callback)` | Send an `IMI.ICMessage` on a thread/topic. |
| `createThread(thread, callback)` | Create a conversation thread. |
| `updateThread(thread, callback)` | Update thread details such as title. |
| `closeThread(thread, callback)` | Close a conversation thread. |
| `fetchThreads(offset, limit, callback)` | Load existing threads and unread counts. |
| `fetchThread(threadId, callback)` | Retrieve a specific thread. |
| `fetchMessages(threadId, beforeDate, limit, callback)` | Load message history. |
| `fetchStreams(callback)` | Load streams when stream-based routing is configured. |
| `fetchUnreadThreadCount(callback)` | Load total unread thread count. |
| `getOutgoing()` | Read whether a message object is outgoing. |
| `setOutgoing(value)` | Mark a message object as outgoing in local handling. |
| `setMessageAsRead(transactionId, callback)` | Mark one message as read. |
| `setMessagesAsRead(transactionIds, callback)` | Mark multiple messages as read. |
| `publishTypingIndicator(thread, started, callback)` | Send typing start/stop. |
| `sendClickedEvent(transactionId, button, callback)` | Report button click/clicked receipt. |
| `createPostbackMessage(message, button)` | Build a postback message for quick replies/buttons. |
| `fetchTopics(filter, callback)` | Load configured topics. |
| `subscribeTopic(topic, callback)` | Subscribe to a readable topic. |
| `unsubscribeTopic(topic, callback)` | Unsubscribe from a topic. |
| `requestPushPermission(callback)` | Trigger browser push permission flow. |
| `getSDKVersion()` | Show SDK version in debug diagnostics. |

`publishTypingIndicator` is throttled by the SDK; do not send it on every
keypress.

## Receiver Callbacks

Register the receiver before calling `connect()`:

```javascript
messaging.setICMessagingReceiver({
  onConnectionStatusChanged(status) {},
  onMessageReceived(message) {}
});
```

Handle connection statuses from `IMI.ICConnectionStatus`: `None`,
`Connecting`, `Connected`, `Refused`, `Closed`, and `Error`.

## Message Object Methods

Outgoing text:

```javascript
const message = new IMI.ICMessage();
message.setMessage(text);
message.setThread(thread);
messaging.publishMessage(message, callback);
```

Common getters to normalize inbound messages:

- `getType()`
- `getMessage()`
- `getThread()`
- `getTopic()`
- `getTransactionId()`
- `getTemporaryId()`
- `getSenderId()`
- `getUserId()`
- `getChannel()`
- `getCategory()`
- `getAttachments()`
- `getMedia()`
- `getQuickReplyData()`
- `getInteractiveData()`
- `getCustomTags()`
- `getExtras()`
- `getReplyTo()`
- `getRelatedTransactionId()`
- `getSubmittedAt()`
- `getDeliveredAt()`
- `getReadAt()`

Common setters for outbound or postback messages:

- `setMessage(message)`
- `setThread(thread)`
- `setTopic(topic)`
- `setSenderId(senderId)`
- `setAttachments(attachments)`
- `setMedia(files)`
- `setQuickReplyData(quickReplyData)`
- `setCustomTags(tags)`
- `setRelatedTransactionId(transactionId)`

## Thread, Topic, and Attachment Classes

Use `IMI.ICThread` for conversation state. Common thread fields/methods include
ID, title, stream name, created/updated times, reason for status change, status,
and type. Set thread status/type with enum values such as
`IMI.ICThreadStatus.Active` and `IMI.ICThreadType.Conversation` when creating a
thread.

Use topic APIs only when the app asset is designed around topics. Topic access
depends on `IMI.ICAccessLevel` and `IMI.ICAccessLevelFilter`.

Attachment and media classes to account for in rendering:

- `IMI.ICAttachment`
- `IMI.ICMediaAttachment`
- `IMI.ICLocationAttachment`
- `IMI.ICFileAttachment`
- `IMI.ICAudioAttachment`
- `IMI.ICVideoAttachment`
- `IMI.ICImageAttachment`
- deprecated `IMI.ICMediaFile`

Attachment/media metadata can include URL, content type, size, preview,
duration, latitude, and longitude.

Use `IMI.ICMediaFileManager.uploadFile(file, file.type, callback)` for widget
file uploads before attaching media to an outbound message. Implement the
`onFileUploadComplete(file, mediaId, error, resp)` callback path and show upload
failure separately from message publish failure.

## Interactive and Template Classes

Implement UI renderers for these classes when rich messages are enabled:

- `IMI.ICInteractiveData`
- `IMI.ICButton`
- `IMI.ICQuickReplyData`
- `IMI.ICTemplateAttachment`
- `IMI.ICFormTemplateAttachment`
- `IMI.ICGenericTemplateAttachment`
- `IMI.ICGenericTemplateElement`
- `IMI.ICFormField`

For quick replies and template buttons, use `createPostbackMessage` for
postback messages and `sendClickedEvent` for click reporting where applicable.

## Enums and Message Types

Interactive data types:

- `FormResponse`
- `WebURL`
- `TemplatePostback`
- `QuickReplyPostback`

Template types:

- `Form`
- `Generic`

Form field types:

- `Text`
- `Name`
- `Email`
- `Integer`
- `Decimal`
- `Date`
- `Dropdown`
- `MultiSelectDropdown`

Content types:

- `Audio`
- `File`
- `Video`
- `Image`
- `Url`
- `Template`

Message statuses:

- `None`
- `NotSent`
- `Sent`
- `Delivered`
- `Read`
- `Clicked`

Message types to route in the widget:

- `Message`
- `ReadReceipt`
- `Republish`
- `ClickedReceipt`
- `Delivered`
- `Deleted`
- `MessageNotification`
- `UpdateThread`
- `ReopenThread`
- `CloseThread`
- `TypingStart`
- `TypingStop`
- `Alert`

Error codes to surface in diagnostics include not initialized, already
initialized, not registered, feature not supported, invalid parameter,
permission not granted, not connected, connection failure, publish failed,
subscribe/unsubscribe failed, invalid token, token expired, token required,
already processing, invalid content type, internal error, duplicate listener,
and SDK version not supported.

## Source Links

- https://developers.webexconnect.io/docs/javascript-sdk-quickstart-guide
- https://developers.webexconnect.io/docs/javascript-sdk-api-reference
- https://developers.webexconnect.io/docs/javascript-sdk-messaging
- https://developers.webexconnect.io/docs/enumerations
- https://developers.webexconnect.io/docs/managing-assets
