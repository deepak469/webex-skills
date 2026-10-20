#!/usr/bin/env python3
"""Static verifier for generated Webex Connect iOS demo apps."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SPM_URL = "https://github.com/webex/wxconnect-ios-sdk"
REQUIRED_ALWAYS = {
    "Package.swift": (
        SPM_URL,
        "WebexConnectCore",
    ),
    "WebexConnectDemo/WebexConnectDemoApp.swift": (
        "WebexConnectDemoApp",
        "WebexConnectRuntime.shared",
        "RootAppView",
    ),
    "WebexConnectDemo/WebexConnectRuntime.swift": (
        "WebexConnectProvider.instance",
        "DeviceProfile",
        "register(deviceProfile",
        "unregister",
        "threadLimit",
        "messageLimit",
        "copyToClipboard",
        "pendingMessageRefreshTasks",
        "scheduleMessageRefresh",
        "orderedMessages",
    ),
    "WebexConnectDemo/MessageRenderer.swift": (
        "ChatMessage",
        "renderInAppMessage",
        "currentUserId",
        "isReceipt",
        "messageDirection",
        "transactionId",
        "relatedTransactionId",
        "submittedAt",
        "compactThreadId",
    ),
    "WebexConnectDemo/DemoModels.swift": (
        "ConversationThread",
        "ChatMessage",
        "MessageDirection",
        "MessageStatus",
        "RichCard",
        "MessageAttachment",
        "QuickReplyAction",
        "FormTemplate",
    ),
    "WebexConnectDemo/DemoViews.swift": (
        "ConversationInboxView",
        "TabView",
        "NavigationStack",
        "ThreadConversationView",
        "ThreadHeaderView",
        "ThreadMenu",
        "MessageBubbleView",
        "CardCarouselView",
        "QuickReplyRow",
        "FormTemplateView",
        "ComposerView",
        "ProfileView",
        "PushTokenCard",
    ),
    "BUILD_IOS.md": (
        "Swift Package Manager",
        "Push Notifications",
        "Background Modes",
        "WebexConnectConfig.plist",
        "APNs",
        "message store",
        "fetchThreads",
        "fetchMessages",
    ),
    "QA_CHECKLIST.md": (
        "Receive an agent/platform message",
        "another thread",
        "Create thread",
        "Closed thread",
        "attachments",
        "Forms",
        "Cards and carousel",
    ),
}

REQUIRED_INAPP = {
    "Package.swift": ("WebexConnectInAppMessaging",),
    "WebexConnectDemo/WebexConnectRuntime.swift": (
        "InAppMessagingProvider.instance",
        "DefaultMessageStore",
        "MessageSynchronizationPolicy",
        "fetchThreads",
        "fetchMessages",
        "fetchThread",
        "createThread",
        "updateThread",
        "publishMessage",
        "sendMessageStatus",
        "publishTypingIndicator",
        "uploadAttachmentData",
        "downloadAttachment",
        "regenerateMediaUrl",
        "handleRealtimeMessage",
        "visibleThreadId",
        "removeValue(forKey: outgoingFingerprint",
        "relatedTransactionId ?? receipt.transactionId",
    ),
    "WebexConnectDemo/MessageRenderer.swift": (
        "quickReplies",
        "attachments",
        "renderCards",
        "renderForm",
    ),
}

REQUIRED_PUSH = {
    "Package.swift": ("WebexConnectPush",),
    "WebexConnectDemo/AppDelegate.swift": (
        "PushMessagingProvider.instance",
        "processPushToken",
        "didRegisterForRemoteNotifications",
        "didFailToRegisterForRemoteNotifications",
        "didReceiveRemoteNotification",
        "UNUserNotificationCenter",
        "apnsToken",
    ),
    "WebexConnectDemo/WebexConnectRuntime.swift": (
        "registerForRemoteNotifications",
        "pushMessagingDelegate",
        "PushTokenDelegate",
    ),
    "WebexConnectDemo/WebexConnectDemo.entitlements": ("aps-environment",),
    "WebexConnectDemo/Info.plist": (
        "UIBackgroundModes",
        "remote-notification",
    ),
}

BANNED_GENERATED_FILES = (
    "Podfile",
    "Podfile.lock",
)
BANNED_TEXT = (
    "pod 'Webex",
    "use_frameworks!",
)


def read(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"Missing {path}")
        return ""
    return path.read_text(encoding="utf-8")


def require_markers(root: Path, markers: dict[str, tuple[str, ...]], errors: list[str]) -> None:
    for relative, required in markers.items():
        text = read(root / relative, errors)
        if not text:
            continue
        for marker in required:
            if marker not in text:
                errors.append(f"{relative} missing marker: {marker}")


def detect_capability(package_text: str) -> tuple[bool, bool]:
    has_push = "WebexConnectPush" in package_text
    has_inapp = "WebexConnectInAppMessaging" in package_text
    return has_push, has_inapp


def validate_spm(root: Path, errors: list[str]) -> None:
    package_text = read(root / "Package.swift", errors)
    pbxproj_text = read(root / "WebexConnectDemo.xcodeproj" / "project.pbxproj", errors)
    if package_text and SPM_URL not in package_text:
        errors.append("Package.swift must reference the Webex Connect iOS SPM repository")
    if pbxproj_text and SPM_URL not in pbxproj_text:
        errors.append("Xcode project must reference the Webex Connect iOS SPM repository")
    if any((root / name).exists() for name in BANNED_GENERATED_FILES):
        errors.append("Generated iOS app must not include Podfile or Podfile.lock")
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix in {".png", ".xcassets"}:
            continue
        if path.name == "project.pbxproj" or path.suffix in {".swift", ".md", ".plist", ".entitlements"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for banned in BANNED_TEXT:
                if banned in text:
                    errors.append(f"{path.relative_to(root)} contains banned dependency marker: {banned}")


def validate_config(root: Path, errors: list[str]) -> None:
    config = root / "WebexConnectDemo" / "WebexConnectConfig.plist"
    legacy = root / "WebexConnectDemo" / "IMIConnectConfig.plist"
    example = root / "WebexConnectDemo" / "WebexConnectConfig.plist.example"
    if not (config.is_file() or legacy.is_file() or example.is_file()):
        errors.append("Missing Webex Connect config plist or example template")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path, help="Generated iOS app root")
    parser.add_argument(
        "--capability",
        choices=("auto", "push", "inapp", "both"),
        default="auto",
        help="Expected generated capability",
    )
    args = parser.parse_args(argv)

    root = args.project_root.resolve()
    errors: list[str] = []

    if not root.is_dir():
        print(f"Missing project root: {root}", file=sys.stderr)
        return 1

    require_markers(root, REQUIRED_ALWAYS, errors)
    validate_spm(root, errors)
    validate_config(root, errors)

    package_text = (root / "Package.swift").read_text(encoding="utf-8") if (root / "Package.swift").is_file() else ""
    has_push, has_inapp = detect_capability(package_text)
    expected_push = args.capability in {"push", "both"} if args.capability != "auto" else has_push
    expected_inapp = args.capability in {"inapp", "both"} if args.capability != "auto" else has_inapp

    if expected_push:
        require_markers(root, REQUIRED_PUSH, errors)
    elif has_push:
        errors.append("Package includes Push although verifier expected no Push capability")

    if expected_inapp:
        require_markers(root, REQUIRED_INAPP, errors)
    elif has_inapp:
        errors.append("Package includes In-App Messaging although verifier expected no In-App capability")

    if args.capability != "auto":
        if expected_push != has_push:
            errors.append(f"Push capability mismatch: expected {expected_push}, package has {has_push}")
        if expected_inapp != has_inapp:
            errors.append(f"In-App capability mismatch: expected {expected_inapp}, package has {has_inapp}")

    if errors:
        print("iOS demo verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    capabilities = []
    if has_push:
        capabilities.append("Push")
    if has_inapp:
        capabilities.append("In-App")
    print(f"Verified Webex Connect iOS demo ({' + '.join(capabilities) or 'Core'}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
