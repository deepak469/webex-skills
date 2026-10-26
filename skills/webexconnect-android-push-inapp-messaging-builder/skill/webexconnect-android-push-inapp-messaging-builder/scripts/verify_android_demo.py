#!/usr/bin/env python3
"""Verify a Webex Connect Android Push + In-App Messaging demo project."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BANNED_TERMS = (
    "twi" + "lio",
    "send" + "grid",
    "programmable" + " messaging",
    "messaging service" + " sid",
    "inter" + "com",
)

CORE_KOTLIN_MARKERS = (
    "DeviceProfile.defaultDeviceId",
    "WebexConnect.instance.register",
    "WebexConnect.instance.isRegistered",
    "WebexConnect.instance.updateProfileParam",
    "WebexConnect.instance.removeProfileParam",
    "WebexConnect.instance.unregister",
    "DeviceProfileParam.CUSTOMER_ID",
    "restoreRegisteredSession",
    "PREFS_NAME",
    "KEY_USER_ID",
    "BackHandler",
    "upsertMessage",
)

INAPP_KOTLIN_MARKERS = (
    "InAppMessaging.instance.connect",
    "InAppMessaging.instance.registerConnectionStatusListener",
    "InAppMessaging.instance.registerMessagingListener",
    "InAppMessaging.instance.createThread",
    "InAppMessaging.instance.updateThread",
    "InAppMessaging.instance.fetchThreads",
    "InAppMessaging.instance.fetchThread",
    "InAppMessaging.instance.publishMessage",
    "InAppMessaging.instance.fetchMessages",
    "InAppMessaging.instance.deleteMessage",
    "InAppMessaging.instance.publishTypingIndicator",
    "InAppMessaging.instance.fetchUnreadThreadCount",
    "InAppMessaging.instance.sendMessageStatus",
    "InAppMessaging.instance.mediaFileManager",
    "InAppMessaging.instance.messageStore",
    "InAppMessaging.instance.messageSynchronizationPolicy",
    "DefaultMessageStore.create",
    "MessageSynchronizationPolicy(MessageSynchronizationMode.LIMITED",
    "FileUploadCallback",
    "FileDownloadCallback",
    "uploadFile",
    "downloadFile",
    "regenerateMediaURL",
    "InAppFileAttachment",
    "InAppThreadStatus.ACTIVE",
    "InAppThreadStatus.CLOSED",
    "InAppThreadType.ANNOUNCEMENT",
    "refreshThreads",
    "loadMoreThreads",
    "loadOlderMessages",
    "createNewThread",
    "openThread",
    "reopenThread",
    "closeThread",
    "deleteMessage",
    "activateThread",
    "toDemoThread",
    "upsertThread",
    "mergeThreads",
    "mergeHistory",
    "removeMessage",
    "publishUploadedFile",
    "replaceAttachmentUrl",
    "uploadSelectedMedia",
    "queryDisplayName",
    "safeUploadFileName",
    "contentResolver.openInputStream",
    "contentResolver.getType",
    "OpenableColumns.DISPLAY_NAME",
    "activeThreadClosed",
    "activeThreadAnnouncement",
    "canReplyToActiveThread",
    "pendingOutgoingIds",
    "pendingOutgoingFingerprints",
    "pendingReceiptStatuses",
    "pendingMessageRefreshes",
    "mainHandler.postDelayed",
    "lastRecoverySyncAt",
    "connectionStatusListener",
    "inAppMessagingListener",
    "InAppMessaging.instance.unregisterConnectionStatusListener",
    "InAppMessaging.instance.unregisterMessagingListener",
    "syncAfterConnectionRestored",
    "scheduleThreadMessageRefresh",
    "syncThreadMetadata(rendered.threadId)",
    "acknowledgeIncomingMessage",
    "InAppMessageStatus.DELIVERED",
    "markRead = visibleInActiveThread",
    "replaceMessage",
    "replaceHistory",
    "applyStatusReceipt",
    "normalizedDeliveryStatus",
    "preferredDeliveryStatus",
    "currentActiveThreadId",
    "shouldSuppressOutgoingEcho",
    "messageFingerprint",
    "visibleHistoryGraceMs",
    "loadingMessages",
    "return@inAppListener",
    "stableInAppMessageId",
    "isCustomerAuthoredMessage",
    "senderDescriptor",
    "messageDirection",
    'paddedDirectionValue.contains(" mt ")',
    'paddedDirectionValue.contains(" mo ")',
    "DemoMessageKind.GENERIC_TEMPLATE",
    "DemoMessageKind.FORM_TEMPLATE",
    "DemoMessageKind.MEDIA",
    "DemoMessageKind.LOCATION",
    "DemoMessageKind.RECEIPT",
    "DemoMessageKind.TYPING",
    "DemoMessageKind.THREAD_UPDATE",
    "DemoMessageKind.ALERT",
    "DemoMessageKind.DELETED",
    "InAppGenericTemplateAttachment",
    "InAppFormTemplateAttachment",
    "InAppGenericTemplateElement",
    "createPostbackMessage",
    "disabledInteractionIds",
    "disableInteraction",
    "sourceMessageId",
    "MessageRenderer.fromInAppMessage(message, currentActiveThreadId(), state.value.userId)",
    "MessageRenderer.fromInAppMessage(it, threadId, state.value.userId)",
    "threadId = message.thread?.id.orEmpty().ifBlank { currentThreadId }",
    "relatedId = message.relatedTransactionId.orEmpty()",
    "isCurrentUserMessage",
    "senderCandidates",
    "directionValue",
    "statusSourceType",
    "extras = extras",
    "toStringMap",
    "cleanPlainText",
    "shouldDisplayInActiveThread",
    "val activeId = currentActiveThreadId()",
    "customerPreviewText",
    "customerVisibleText",
    "val previousThreads = state.value.threads",
    "mergeThreads(previousThreads, incomingThreads)",
    "orderedMessages",
    "message.submittedAt?.time ?: message.createdAt?.time",
)

PUSH_KOTLIN_MARKERS = (
    "PushMessaging.instance.registerPushTokenListener",
    "PushMessaging.instance.unregisterPushTokenListener",
    "PushMessaging.instance.unregisterMessagingListener",
    "pushTokenListener",
    "pushMessagingListener",
    "PushMessaging.instance.registerMessagingListener",
    "PushMessaging.instance.requestNotificationPermission",
    "stablePushMessageId",
    "PushMessaging.instance.actionHandler",
    "PushMessaging.instance.inAppNotificationManager.registerListener",
    "NotificationActionHandler",
    "InAppNotificationCallback",
    "PushInteractiveData",
    "PushMessageStatus.DELIVERED",
    "PushMessageStatus.READ",
    "NotificationFactory.DEFAULT_CHANNEL_ID",
    "NotificationBuilderCallback",
    "R.drawable.ic_stat_webex_connect",
)

CALLING_UI_MARKERS = (
    "Request " + "callback",
    "Call " + "support",
    "Phone " + "callback",
    "Icons.Filled." + "Phone",
    "Icons.Filled." + "Call",
    "Local" + "Phone",
)

REQUIRED_TEST_TAGS = (
    "user-id-input",
    "login-button",
    "app-top-bar",
    "home-screen",
    "orders-screen",
    "support-entry",
    "notification-icon",
    "notification-center",
    "product-card",
    "order-card",
    "workflow-card",
    "agent-chat-card",
    "qa-panel",
    "account-tools-panel",
    "push-token-card",
    "copy-push-token-button",
    "push-token-value",
    "profile-customer-id-input",
    "profile-app-id",
    "profile-update-button",
    "sign-out-button",
    "switch-user-button",
    "advanced-sdk-panel",
    "sync-policy-button",
    "sync-thread-limit-input",
    "sync-message-limit-input",
    "profile-settings-screen",
    "profile-summary-card",
    "thread-list-panel",
    "thread-search-input",
    "thread-filter-button",
    "thread-filter-all",
    "thread-filter-unread",
    "thread-filter-open",
    "refresh-threads-button",
    "load-more-threads-button",
    "thread-list",
    "thread-list-row",
    "thread-avatar",
    "thread-presence-dot",
    "thread-row-time",
    "thread-unread-badge",
    "new-thread-toggle-button",
    "new-thread-dialog",
    "new-thread-create-row",
    "new-thread-title-input",
    "new-thread-button",
    "reopen-thread-button",
    "close-thread-button",
    "thread-closed-state",
    "thread-status-line",
    "thread-status-dot",
    "thread-menu-details",
    "thread-menu-search",
    "foreground-notification-banner",
    "chat-thread-screen",
    "chat-thread-header",
    "chat-back-button",
    "thread-header-title",
    "thread-identity-line",
    "thread-id-label",
    "copy-thread-id-button",
    "thread-header-menu-button",
    "thread-header-menu",
    "chat-composer",
    "composer-input-rail",
    "composer-divider",
    "message-list",
    "message-loading-state",
    "empty-conversation-state",
    "load-more-messages-button",
    "attachment-button",
    "message-input",
    "send-button",
    "card-carousel",
    "card-carousel-position",
    "template-card",
    "card-image-preview",
    "card-action",
    "dynamic-message-actions",
    "message-agent-avatar",
    "quick-reply-action",
    "form-field-input",
    "form-submit-button",
    "message-extras-preview",
    "attachment-image-preview",
)

RICH_UI_MARKERS = (
    "NavigationBar",
    "Icons.Filled.Notifications",
    "NotificationCenterSheet",
    "WebexBrandMark",
    "R.drawable.webex_logo",
    "HomeScreen",
    "OrdersScreen",
    "SupportWorkspace",
    "ConversationInboxScreen",
    "ProfileScreen",
    "ProfileSummaryCard",
    "ProfileMetric",
    "AccountToolsPanel",
    "webexConnectAppId",
    "App ID:",
    "PushTokenCard",
    "AdvancedSdkToolsPanel",
    "syncMaxThreads",
    "syncMaxMessagesPerThread",
    "Apply sync limits",
    "SDK version:",
    "Started:",
    "Registered:",
    "Logger: app-managed",
    "Security token: app-managed",
    "WebexConnect.instance.startup",
    "WebexConnect.instance.sdkVersion",
    "WebexConnect.instance.isStarted",
    "ThreadListPanel",
    "ThreadInboxRow",
    "EmptyThreadInbox",
    "MessageLoadingState",
    "EmptyConversationState",
    "CircularProgressIndicator",
    "ThreadPresenceDot",
    "ThreadMetadataPill",
    "threadPreview",
    "threadTimeLabel",
    "supportThreadOpen",
    "onThreadOpenChange",
    "onOpenThread",
    "ChatThreadHeader",
    "ThreadStatusLine",
    "selectedThreadTitle",
    "compactThreadId",
    "LocalClipboardManager",
    "AnnotatedString",
    "Icons.Filled.ContentCopy",
    "contentWindowInsets = WindowInsets(left = 0.dp, top = 0.dp, right = 0.dp, bottom = 0.dp)",
    "ThreadClosedState",
    "ChatThreadMenu",
    "DropdownMenu",
    "DropdownMenuItem",
    "View details",
    "Search in conversation",
    "Close thread",
    "Reopen thread",
    "Icons.Filled.Lock",
    "Icons.Filled.LockOpen",
    "MessageAvatar",
    "messageTimeLabel",
    "conversationDateLabel",
    "CardActionButton",
    "ChatComposer",
    "BasicTextField",
    "SolidColor(DemoBlue)",
    "Add attachment",
    "AlertDialog",
    "containerColor = DemoPaper",
    "tonalElevation = 0.dp",
    "private val DemoCanvas = Color(0xFF1A1A1A)",
    "private val DemoPaper = Color(0xFF262626)",
    "private val DemoElevated = Color(0xFF303030)",
    "private val DemoActive = Color(0x1CFFFFFF)",
    "private val DemoBlue = Color(0xFF3492EB)",
    "primaryContainer = DemoActive",
    "WindowInsets.safeDrawing",
    "heightIn(min = 68.dp",
    "statusBarsPadding",
    "imePadding",
    "navigationBarsPadding",
    "DemoColorScheme",
    "darkColorScheme",
    "NavigationBarItemDefaults.colors",
    "OutlinedTextFieldDefaults.colors",
    "RemoteImagePreview",
    "BitmapFactory.decodeStream",
    "connectTimeout = 4_000",
    "readTimeout = 4_000",
    "ContentScale.Crop",
    "rememberLauncherForActivityResult",
    "ActivityResultContracts.GetContent",
    "LocalFocusManager",
    "focusManager.clearFocus",
    "animateScrollToItem(state.messages.lastIndex)",
    "val maxBubbleWidth = if (message.kind == DemoMessageKind.GENERIC_TEMPLATE) 342.dp else 300.dp",
    "messageDisplayText",
    "stripDiagnosticPayload",
    "maxLines = 8",
    "ExtrasPreview",
    "Icons.Filled.Search",
    "Icons.Filled.Tune",
    "ForegroundNotificationBanner",
    "ProductSpotlightCard",
    "OrderStatusCard",
    "AutomationWorkflowCard",
    "MessageBubble",
    "outgoingMessageStatus",
    'if (!message.outgoing) return ""',
    "CardCarousel",
    "RichMessageCard",
    "card.imageUrls",
    "ActionRow",
    "itemsIndexed",
    "messageListKey",
    "cardListKey",
    "actionListKey",
    "FormMessagePreview(message",
    "FilterChip",
    "formPayload",
    '"fields", JSONObject',
    "fieldKey",
    "enabled = !disabled",
    "repliesEnabled",
    "thread.closed",
    "selectedThread?.announcement",
    "selectedThread?.closed",
    "lastMessage",
    "recordInactiveThreadMessage",
    "updateThreadsFromMessage",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--capability", choices=("push", "inapp", "both"))
    parser.add_argument("--provider", choices=("fcm", "hms"))
    parser.add_argument("--package", help="Expected Android package/application ID.")
    parser.add_argument("--build-type", choices=("debug", "release"), default="debug")
    parser.add_argument("--strict-config", action="store_true")
    parser.add_argument("--run-gradle", action="store_true")
    return parser.parse_args()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def all_files(root: Path) -> list[Path]:
    ignored = {".git", ".gradle", "build", ".idea"}
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in ignored for part in path.parts)
    ]


def check(condition: bool, label: str, failures: list[str]) -> None:
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label}")
        failures.append(label)


def includes_push(args: argparse.Namespace) -> bool:
    return args.capability in {"push", "both"}


def includes_inapp(args: argparse.Namespace) -> bool:
    return args.capability in {"inapp", "both"}


def main() -> int:
    args = parse_args()
    if not args.capability:
        args.capability = "both" if args.provider else "both"
    if includes_push(args) and not args.provider:
        print("[FAIL] Push verification requires --provider fcm or --provider hms")
        return 2
    if not includes_push(args):
        args.provider = None

    root = Path(args.project_root).resolve()
    failures: list[str] = []

    files = all_files(root)
    combined = "\n".join(read(path) for path in files)
    lower_combined = combined.lower()
    app_gradle = read(root / "app/build.gradle.kts") or read(root / "app/build.gradle")
    gradle_properties = read(root / "gradle.properties")
    manifest = read(root / "app/src/main/AndroidManifest.xml")
    strings = read(root / "app/src/main/res/values/strings.xml")
    ignore_rules = read(root / ".gitignore")
    kotlin_combined = "\n".join(read(path) for path in files if path.suffix == ".kt")
    message_renderer = "\n".join(read(path) for path in files if path.name == "MessageRenderer.kt")

    check(bool(files), "project has files", failures)
    for term in BANNED_TERMS:
        check(term not in lower_combined, f"no banned term: {term}", failures)
    for marker in CALLING_UI_MARKERS:
        check(marker not in combined, f"unsupported calling UI absent: {marker}", failures)

    check("Webex Connect Demo" in strings or 'android:label="Webex Connect Demo"' in manifest, "app label is Webex Connect Demo", failures)
    check('android:icon="@mipmap/ic_launcher"' in manifest, "manifest uses Webex launcher icon", failures)
    check('android:roundIcon="@mipmap/ic_launcher_round"' in manifest, "manifest uses Webex round launcher icon", failures)
    check("android.permission.INTERNET" in manifest, "manifest has internet permission", failures)
    check("android.permission.POST_NOTIFICATIONS" in manifest, "manifest has Android 13 notification permission", failures)
    check("com.webex.connect:webexconnect-core" in app_gradle, "core SDK dependency is present", failures)
    if includes_inapp(args):
        check("com.webex.connect:webexconnect-inappmessaging" in app_gradle, "in-app SDK dependency is present", failures)
    else:
        check("com.webex.connect:webexconnect-inappmessaging" not in app_gradle, "in-app SDK dependency is omitted for Push-only", failures)
    check("androidx.compose.material:material-icons-extended" in app_gradle, "Material icons dependency is present", failures)
    check("org.jetbrains.kotlin.plugin.compose" in app_gradle, "Kotlin Compose plugin is applied", failures)
    check("android.useAndroidX=true" in gradle_properties, "AndroidX is enabled in gradle.properties", failures)
    check("sourceCompatibility = JavaVersion.VERSION_17" in app_gradle, "Java source compatibility is pinned to 17", failures)
    check("JvmTarget.JVM_17" in app_gradle, "Kotlin JVM target is pinned to 17", failures)
    check("compileSdk = 37" in app_gradle, "compileSdk matches modular SDK 3.1.0 docs", failures)
    check("targetSdk = 37" in app_gradle, "targetSdk matches modular SDK 3.1.0 docs", failures)
    check(not ("webexconnect-fcm" in app_gradle and "webexconnect-hms" in app_gradle), "does not mix FCM and HMS in one build", failures)
    check("getByName(\"debug\")" in app_gradle, "debug build type is configured", failures)
    check("getByName(\"release\")" in app_gradle, "release build type is configured", failures)

    if args.package:
        check(f'namespace = "{args.package}"' in app_gradle, "namespace matches expected package", failures)
        check(f'applicationId = "{args.package}"' in app_gradle, "applicationId matches expected package", failures)

    if args.provider == "fcm":
        google_services = root / "app/google-services.json"
        check("com.webex.connect:webexconnect-push" in app_gradle, "push SDK dependency is present", failures)
        check("com.webex.connect:webexconnect-fcm" in app_gradle, "FCM module is present", failures)
        if args.strict_config or google_services.exists():
            check("com.google.gms.google-services" in app_gradle, "Google services plugin is present", failures)
            check(google_services.exists(), "google-services.json exists", failures)
        else:
            check("com.google.gms.google-services" not in app_gradle, "Google services plugin is deferred until google-services.json exists", failures)
    elif args.provider == "hms":
        agconnect_services = root / "app/agconnect-services.json"
        check("com.webex.connect:webexconnect-push" in app_gradle, "push SDK dependency is present", failures)
        check("com.webex.connect:webexconnect-hms" in app_gradle, "HMS module is present", failures)
        check("https://developer.huawei.com/repo/" in combined, "Huawei repository is present", failures)
        if args.strict_config or agconnect_services.exists():
            check("com.huawei.agconnect" in app_gradle, "Huawei AGConnect plugin is present", failures)
            check(agconnect_services.exists(), "agconnect-services.json exists", failures)
        else:
            check("com.huawei.agconnect" not in app_gradle, "Huawei AGConnect plugin is deferred until agconnect-services.json exists", failures)
    else:
        check("webexconnect-push" not in app_gradle and "webexconnect-fcm" not in app_gradle and "webexconnect-hms" not in app_gradle, "push SDK dependencies are omitted for In-App-only", failures)

    assets = root / "app/src/main/assets"
    real_config = assets / "WebexConnectConfig.properties"
    legacy_real_config = assets / "IMIconnectConfig.properties"
    example_config = assets / "WebexConnectConfig.properties.example"
    legacy_example_config = assets / "IMIconnectConfig.properties.example"
    configured_real_config = real_config if real_config.exists() else legacy_real_config
    check(real_config.exists() or legacy_real_config.exists() or example_config.exists() or legacy_example_config.exists(), "Connect config file or example exists", failures)
    if args.strict_config:
        check(configured_real_config.exists(), "real WebexConnectConfig.properties or legacy IMIconnectConfig.properties exists", failures)
        config_text = read(configured_real_config)
        check("appId=" in config_text and "<APP_ID>" not in config_text, "Connect appId is configured", failures)
        check("clientKey=" in config_text and "<CLIENT_KEY>" not in config_text, "Connect clientKey is configured", failures)
    check("app/src/main/assets/WebexConnectConfig.properties" in ignore_rules, "current Connect config is gitignored", failures)
    check("app/src/main/assets/IMIconnectConfig.properties" in ignore_rules, "Connect config is gitignored", failures)
    check("app/google-services.json" in ignore_rules, "FCM provider config is gitignored", failures)
    check("app/agconnect-services.json" in ignore_rules, "HMS provider config is gitignored", failures)

    res = root / "app/src/main/res"
    check((res / "drawable-nodpi/webex_logo.png").exists(), "Webex logo drawable asset exists", failures)
    check((res / "drawable/ic_stat_webex_connect.xml").exists(), "Webex notification small icon exists", failures)
    for density in ("mipmap-mdpi", "mipmap-hdpi", "mipmap-xhdpi", "mipmap-xxhdpi", "mipmap-xxxhdpi"):
        check((res / density / "ic_launcher.png").exists(), f"launcher icon exists for {density}", failures)
        check((res / density / "ic_launcher_round.png").exists(), f"round launcher icon exists for {density}", failures)

    for marker in CORE_KOTLIN_MARKERS:
        check(marker in kotlin_combined, f"SDK marker present: {marker}", failures)
    if includes_push(args):
        for marker in PUSH_KOTLIN_MARKERS:
            check(marker in kotlin_combined, f"Push SDK marker present: {marker}", failures)
    else:
        for marker in ("PushMessaging.", "PushMessage", "NotificationBuilderCallback", "NotificationFactory.DEFAULT_CHANNEL_ID"):
            check(marker not in kotlin_combined, f"Push SDK marker omitted for In-App-only: {marker}", failures)
    if includes_inapp(args):
        for marker in INAPP_KOTLIN_MARKERS:
            check(marker in kotlin_combined, f"In-App SDK marker present: {marker}", failures)
    else:
        for marker in ("InAppMessaging.", "InAppMessage", "InAppThread", "InAppButton", "InAppGenericTemplateAttachment"):
            check(marker not in kotlin_combined, f"In-App SDK marker omitted for Push-only: {marker}", failures)
    for marker in RICH_UI_MARKERS:
        check(marker in kotlin_combined, f"rich UI marker present: {marker}", failures)
    for tag in REQUIRED_TEST_TAGS:
        check(tag in kotlin_combined, f"UI test tag present: {tag}", failures)
    check("items(state.messages, key = { it.id })" not in kotlin_combined, "message list does not key only by SDK transaction ID", failures)
    check("key = { it.id + it.title }" not in kotlin_combined, "action rows do not use duplicate-prone id+title keys", failures)
    check("message.cards.forEach" not in kotlin_combined, "generic template cards render as one carousel rail", failures)
    check("Hi, I am Maya" not in kotlin_combined, "real SDK threads do not show seeded welcome copy", failures)
    check("welcome-options" not in kotlin_combined, "real SDK threads do not show seeded card templates", failures)
    check("state.loadingMessages && state.messages.isEmpty()" in kotlin_combined, "history loading state does not hide existing messages", failures)
    check("createdAt = System.currentTimeMillis()" in kotlin_combined, "optimistic outgoing messages carry a local timestamp", failures)
    check("replacePendingOutgoing(message.copy(outgoing = true))" in kotlin_combined, "SDK outgoing echoes preserve user bubble direction", failures)
    check("if (!message.outgoing)" in kotlin_combined, "incoming/backend messages are not consumed as outgoing echoes", failures)
    check('json?.optString("userId"),' not in message_renderer, "renderer does not classify top-level recipient userId as sender", failures)
    check('json?.optString("customerId"),' not in message_renderer, "renderer does not classify top-level recipient customerId as sender", failures)
    check("DemoMessageKind.ALERT -> \"\"" in kotlin_combined, "alert messages do not render a redundant Alert label", failures)
    check(("Media preview " + "available") not in kotlin_combined, "card and attachment images are not replaced by generic media-preview text", failures)
    check(("Image preview " + "available") not in kotlin_combined, "image URLs render inline instead of as preview text", failures)
    check("A realistic commerce shell" not in kotlin_combined, "visible UI avoids demo-explainer copy", failures)
    check("ChatThreadStatusCard" not in kotlin_combined, "chat thread metadata is not rendered as a separate status card", failures)
    check('testTag("thread-status-card")' not in kotlin_combined, "thread status card test tag is absent from chat body", failures)
    check("ThreadHeaderMetadata" not in kotlin_combined, "chat header no longer renders metadata pill row", failures)
    check('testTag("thread-closed-banner")' not in kotlin_combined, "closed thread uses centered recovery panel instead of warning banner", failures)
    check('testTag("notification-button")' not in kotlin_combined, "thread header omits redundant notification bell", failures)
    check(' + " through " + state.provider' not in kotlin_combined, "top bar does not expose user/provider routing text", failures)
    check('"Thread: " + state.threadId' not in kotlin_combined, "profile SDK status omits selected thread ID", failures)
    check('"Thread state: "' not in kotlin_combined, "profile SDK status omits selected thread state", failures)
    check('"Unread: "' not in kotlin_combined, "profile SDK status omits unread count", failures)
    check('"Media: "' not in kotlin_combined, "profile SDK status omits media transfer state", failures)
    check('"Push token: "' not in kotlin_combined, "profile SDK status omits inline push token", failures)
    check('testTag("media-upload-button")' not in kotlin_combined, "profile omits global media upload button", failures)
    check('testTag("media-download-button")' not in kotlin_combined, "profile omits global media download button", failures)
    check('testTag("media-regenerate-button")' not in kotlin_combined, "profile omits global media URL refresh button", failures)
    check("PushTokenCard(state = state)" in kotlin_combined, "profile renders push token in a separate card", failures)
    check("copy-push-token-button" in kotlin_combined, "push token card has copy action", failures)
    check("MessageSynchronizationPolicy(MessageSynchronizationMode.LIMITED, threadLimit, messageLimit)" in kotlin_combined, "sync policy uses editable thread/message limits", failures)
    check('Text("Webex Connect Demo", style = MaterialTheme.typography.titleMedium' not in kotlin_combined, "chat header title is selected thread data, not a fixed demo title", failures)
    check("val title = selectedThreadTitle(selectedThread)" in kotlin_combined, "chat header resolves title from selected thread", failures)
    check("Copy thread ID" in kotlin_combined, "chat header exposes a copy action for the SDK thread ID", failures)
    check("statusBarsPadding()" in kotlin_combined, "chat header uses compact status-bar padding", failures)
    check("heightIn(min = 72.dp)" in kotlin_combined, "chat thread header uses compact minimum height with title and ID", failures)
    check("Text(message.status.ifBlank { message.type }" not in kotlin_combined, "message footer does not mix delivery status with message type", failures)
    check("ConfigGuard.webexConnectAppId(context)" in kotlin_combined, "profile App ID is loaded from Webex Connect config", failures)
    check('if (repliesEnabled)' in kotlin_combined, "composer is omitted when thread is closed/read-only", failures)
    check("This thread is closed" in kotlin_combined, "closed thread recovery state is present", failures)
    check('modifier = Modifier.testTag("close-thread-button")' in kotlin_combined, "close thread action is available from overflow menu", failures)
    check("View details" in kotlin_combined and "Search in conversation" in kotlin_combined, "overflow menu includes detail and conversation search entries", failures)
    check('testTag("composer-input-rail")' in kotlin_combined, "composer uses one compact rail", failures)
    check('testTag("composer-divider")' in kotlin_combined, "composer includes the reference-style divider", failures)
    check('contentDescription = "Add attachment"' in kotlin_combined, "composer attachment action uses plus affordance", failures)
    check('modifier = Modifier.weight(1f).heightIn(min = 50.dp).testTag("message-input")' not in kotlin_combined, "composer no longer uses bulky outlined message field", failures)
    check('"Type a message..."' in kotlin_combined, "composer uses the compact reference placeholder", failures)
    check('"Write a message..."' not in kotlin_combined, "composer no longer uses the older placeholder copy", failures)
    check("ChatQuickActions(" not in kotlin_combined, "opened thread does not render static demo shortcut rail", failures)
    check('"Help with a request", "Start a support chat", "Check order status"' not in kotlin_combined, "thread conversation actions come from dynamic SDK messages", failures)
    check("MessageAvatar()" in kotlin_combined, "incoming messages render Webex avatar rows", failures)
    check("MessageMetaLine(timeText = timeText, statusText = statusText, outgoing = outgoing)" in kotlin_combined, "status and timestamp render once outside the bubble", failures)
    check("messageTimeLabel(message.createdAt)" in kotlin_combined, "message timestamp comes from SDK message time", failures)
    check("conversationDateLabel(it.createdAt)" in kotlin_combined, "date separator comes from message history", failures)
    check("rememberLazyListState()" in kotlin_combined, "card carousel tracks visible position", failures)
    check("CardActionButton(sourceMessageId, action, disabled, onAction)" in kotlin_combined, "card actions render as dynamic CTA buttons", failures)
    for stale_color in ("EAF2FF", "E8F7F3", "E7F7F4", "F7F8FC", "FFF1E8", "F8FBFF", "F0F4F9", "E6EAF2"):
        check(stale_color not in kotlin_combined, f"stale light UI color absent: {stale_color}", failures)
    check("lightColorScheme" not in kotlin_combined, "generated app uses dark Figma-derived color scheme", failures)
    check('Regex("\\s+")' not in kotlin_combined, "Kotlin whitespace regex is double escaped", failures)
    check('Regex("\\d' not in kotlin_combined, "Kotlin digit regex is double escaped", failures)
    check(":\\-]" not in kotlin_combined and ":\\-]+" not in kotlin_combined, "Kotlin token regex avoids invalid escaped hyphen", failures)
    check("FormMessagePreview(message.fields)" not in kotlin_combined, "form templates render editable inputs from the whole message", failures)
    check("ThreadSummaryChip" not in kotlin_combined, "thread list uses inbox rows instead of chip rail", failures)
    check("UUID.randomUUID()" not in message_renderer, "message renderer uses deterministic fallback IDs for realtime/history reconciliation", failures)
    if not includes_push(args):
        check("PushMessage" not in message_renderer, "In-App-only renderer does not reference Push classes", failures)

    if args.run_gradle:
        gradlew = root / "gradlew"
        task = "assembleDebug" if args.build_type == "debug" else "assembleRelease"
        command = [str(gradlew) if gradlew.exists() else "gradle", task]
        result = subprocess.run(command, cwd=root, text=True)
        check(result.returncode == 0, f"Gradle {task} succeeds", failures)

    if failures:
        print("\nVerification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nVerification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
