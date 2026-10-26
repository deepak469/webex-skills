#!/usr/bin/env python3
"""Generate a Webex Connect Android Push + In-App Messaging demo project."""

from __future__ import annotations

import argparse
import getpass
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


GROUP_ID = "com.webex.connect"
MAVEN_BASE = "https://repo1.maven.org/maven2/com/webex/connect"
FALLBACK_VERSION = "3.1.0"
CAPABILITY_CHOICES = ("push", "inapp", "both")
PUSH_PROVIDER_CHOICES = ("fcm", "hms")
BUILD_TYPES = {"debug": "Debug", "release": "Release"}
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
ANDROID_ICON_ASSETS = {
    "assets/android-icons/drawable-nodpi/webex_logo.png": "app/src/main/res/drawable-nodpi/webex_logo.png",
    "assets/android-icons/mipmap-mdpi/ic_launcher.png": "app/src/main/res/mipmap-mdpi/ic_launcher.png",
    "assets/android-icons/mipmap-mdpi/ic_launcher_round.png": "app/src/main/res/mipmap-mdpi/ic_launcher_round.png",
    "assets/android-icons/mipmap-hdpi/ic_launcher.png": "app/src/main/res/mipmap-hdpi/ic_launcher.png",
    "assets/android-icons/mipmap-hdpi/ic_launcher_round.png": "app/src/main/res/mipmap-hdpi/ic_launcher_round.png",
    "assets/android-icons/mipmap-xhdpi/ic_launcher.png": "app/src/main/res/mipmap-xhdpi/ic_launcher.png",
    "assets/android-icons/mipmap-xhdpi/ic_launcher_round.png": "app/src/main/res/mipmap-xhdpi/ic_launcher_round.png",
    "assets/android-icons/mipmap-xxhdpi/ic_launcher.png": "app/src/main/res/mipmap-xxhdpi/ic_launcher.png",
    "assets/android-icons/mipmap-xxhdpi/ic_launcher_round.png": "app/src/main/res/mipmap-xxhdpi/ic_launcher_round.png",
    "assets/android-icons/mipmap-xxxhdpi/ic_launcher.png": "app/src/main/res/mipmap-xxxhdpi/ic_launcher.png",
    "assets/android-icons/mipmap-xxxhdpi/ic_launcher_round.png": "app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.png",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--package", default="com.webex.connect.demo")
    parser.add_argument("--app-name", default="Webex Connect Demo")
    parser.add_argument("--capability", choices=CAPABILITY_CHOICES, help="Generate Push, In-App, or both messaging capabilities.")
    parser.add_argument("--provider", choices=sorted(PUSH_PROVIDER_CHOICES), help="FCM or HMS. Required only when Push is selected.")
    parser.add_argument("--version", help="Pin SDK version instead of resolving Maven metadata.")
    parser.add_argument("--interactive", action="store_true", help="Prompt for build-time inputs.")
    parser.add_argument("--app-id", help="Webex Connect mobile app asset ID.")
    parser.add_argument("--client-key", help="Webex Connect mobile app client key.")
    parser.add_argument("--environment", default="", help="Webex Connect SDK environment, for example UK.")
    parser.add_argument(
        "--connect-config",
        type=Path,
        help="Existing WebexConnectConfig.properties or IMIconnectConfig.properties to copy.",
    )
    parser.add_argument("--provider-config", type=Path, help="google-services.json for FCM or agconnect-services.json for HMS.")
    parser.add_argument("--build-type", choices=sorted(BUILD_TYPES), default="debug")
    parser.add_argument("--build-apk", action="store_true", help="Run assembleDebug or assembleRelease after generation.")
    parser.add_argument("--strict-inputs", action="store_true", help="Require tenant and provider config files.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    return parser.parse_args()


def can_prompt(args: argparse.Namespace) -> bool:
    return args.interactive and sys.stdin.isatty()


def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    if secret:
        value = getpass.getpass(f"{prompt}{suffix}: ").strip()
    else:
        value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_choice(prompt: str, choices: tuple[str, ...], default: str | None = None) -> str:
    choices_label = "/".join(choices)
    while True:
        value = ask(f"{prompt} ({choices_label})", default or "").lower()
        if value in choices:
            return value
        print(f"Choose one of: {choices_label}", file=sys.stderr)


def ask_bool(prompt: str, default: bool = False) -> bool:
    default_label = "y" if default else "n"
    while True:
        value = ask(f"{prompt} (y/n)", default_label).lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Choose y or n.", file=sys.stderr)


def expand_path(value: Path | None) -> Path | None:
    return value.expanduser().resolve() if value else None


def expected_provider_config(provider: str) -> str | None:
    if provider == "fcm":
        return "google-services.json"
    if provider == "hms":
        return "agconnect-services.json"
    return None


def includes_push(args: argparse.Namespace) -> bool:
    return args.capability in {"push", "both"}


def includes_inapp(args: argparse.Namespace) -> bool:
    return args.capability in {"inapp", "both"}


def module_artifacts(args: argparse.Namespace) -> list[str]:
    artifacts: list[str] = ["webexconnect-core"]
    if includes_push(args):
        artifacts.append("webexconnect-push")
        artifacts.append(f"webexconnect-{args.provider}")
    if includes_inapp(args):
        artifacts.append("webexconnect-inappmessaging")
    return artifacts


def capability_label(args: argparse.Namespace) -> str:
    if args.capability == "both":
        return "Push + In-App"
    if args.capability == "push":
        return "Push"
    return "In-App"


def runtime_provider_label(args: argparse.Namespace) -> str:
    label = capability_label(args)
    if includes_push(args):
        return f"{label} ({args.provider.upper()})"
    return label


def collect_inputs(args: argparse.Namespace) -> argparse.Namespace:
    if args.interactive and not sys.stdin.isatty():
        raise ValueError(
            "--interactive requires a terminal. In Codex/plugin UI, ask the user "
            "for capability (push, inapp, or both), provider when Push is selected "
            "(fcm or hms), package name, build type, Connect config "
            "(WebexConnectConfig.properties or appId/clientKey/environment), provider "
            "service file when Push is selected, and whether to build the APK. Then "
            "rerun with explicit flags."
        )

    if can_prompt(args):
        args.capability = args.capability or ask_choice("Messaging capability to build", CAPABILITY_CHOICES)
        if includes_push(args):
            args.provider = args.provider or ask_choice("Push provider selected at build time", PUSH_PROVIDER_CHOICES)
        args.package = ask("Android package/application ID", args.package)
        args.build_type = ask_choice("APK build type", ("debug", "release"), args.build_type)
        config_path = ask("Path to existing WebexConnectConfig.properties, or leave blank to enter values", "")
        if config_path:
            args.connect_config = Path(config_path)
        if not args.connect_config:
            args.app_id = args.app_id or ask("Webex Connect appId")
            args.client_key = args.client_key or ask("Webex Connect clientKey", secret=True)
            args.environment = args.environment or ask("Webex Connect environment", "UK")
        provider_filename = expected_provider_config(args.provider)
        if includes_push(args) and provider_filename:
            provider_path = ask(f"Path to {provider_filename}", "")
            if provider_path:
                args.provider_config = Path(provider_path)
        args.build_apk = ask_bool("Build APK after generation", args.build_apk)

    if not args.capability:
        args.capability = "both" if args.provider else None
    if not args.capability:
        raise ValueError(
            "Capability is required. Ask the user to choose Push, In-App, or Both, "
            "then pass --capability push, --capability inapp, or --capability both. "
            "Use --interactive only from a real terminal."
        )
    if includes_push(args) and not args.provider:
        raise ValueError(
            "Push builds require a build-time provider. Ask the user to choose FCM "
            "or HMS, then pass --provider fcm or --provider hms. Do not default to "
            "FCM or HMS."
        )
    if not includes_push(args):
        args.provider = ""
    if not PACKAGE_RE.match(args.package):
        raise ValueError(f"Invalid Android package name: {args.package}")
    args.connect_config = expand_path(args.connect_config)
    args.provider_config = expand_path(args.provider_config)
    return args


def fetch_text(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            return response.read().decode("utf-8")
    except Exception:
        curl = shutil.which("curl")
        if not curl:
            raise
        result = subprocess.run([curl, "-L", "--fail", url], check=True, capture_output=True, text=True)
        return result.stdout


def latest_version(artifact: str) -> str:
    metadata = fetch_text(f"{MAVEN_BASE}/{artifact}/maven-metadata.xml")
    root = ET.fromstring(metadata)
    return root.findtext("./versioning/latest") or root.findtext("./versioning/release") or FALLBACK_VERSION


def resolve_sdk_version(artifacts: list[str]) -> str:
    failures: list[str] = []
    for artifact in artifacts:
        try:
            return latest_version(artifact)
        except Exception as exception:
            failures.append(f"{artifact}: {exception}")
    print(
        "Warning: could not resolve Webex Connect Android SDK metadata from "
        f"Maven Central ({'; '.join(failures)}). Using {FALLBACK_VERSION}.",
        file=sys.stderr,
    )
    return FALLBACK_VERSION


def write_file(path: Path, content: str, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return f"kept {path}"
    path.write_text(content, encoding="utf-8")
    return f"wrote {path}"


def package_path(package_name: str) -> str:
    return package_name.replace(".", "/")


def dependencies(args: argparse.Namespace, version: str) -> str:
    return "\n".join(
        f'    implementation("{GROUP_ID}:{artifact}:{version}")'
        for artifact in module_artifacts(args)
    )


def has_provider_input(args: argparse.Namespace) -> bool:
    return bool(includes_push(args) and args.provider_config and expected_provider_config(args.provider))


def provider_plugin(args: argparse.Namespace) -> str:
    if not includes_push(args):
        return ""
    if args.provider == "fcm":
        if not has_provider_input(args):
            return "    // FCM service plugin is deferred until app/google-services.json is present."
        return '    id("com.google.gms.google-services")'
    if args.provider == "hms":
        if not has_provider_input(args):
            return "    // HMS service plugin is deferred until app/agconnect-services.json is present."
        return '    id("com.huawei.agconnect")'
    return ""


def project_plugins(args: argparse.Namespace) -> str:
    lines = [
        '    id("com.android.application") version "8.13.0" apply false',
        '    id("org.jetbrains.kotlin.android") version "2.2.20" apply false',
        '    id("org.jetbrains.kotlin.plugin.compose") version "2.2.20" apply false',
    ]
    if includes_push(args) and args.provider == "fcm" and has_provider_input(args):
        lines.append('    id("com.google.gms.google-services") version "4.4.3" apply false')
    if includes_push(args) and args.provider == "hms" and has_provider_input(args):
        lines.append('    id("com.huawei.agconnect") version "1.9.1.301" apply false')
    return "\n".join(lines)


def hms_repositories(provider: str) -> str:
    if provider != "hms":
        return ""
    return '        maven(url = "https://developer.huawei.com/repo/")\n'


def connect_config_files(args: argparse.Namespace) -> dict[str, str]:
    if args.connect_config:
        return {}
    if args.app_id and args.client_key and not args.connect_config:
        return {
            "app/src/main/assets/WebexConnectConfig.properties": f"""# Generated locally for Webex Connect Demo.
# Do not commit this file.
appId={args.app_id}
clientKey={args.client_key}
environment={args.environment}
"""
        }
    return {
        "app/src/main/assets/WebexConnectConfig.properties.example": """# Download the real WebexConnectConfig.properties from the Webex Connect
# Mobile/Web app asset configuration page, or generate it with:
# create_android_demo.py . --app-id APP_ID --client-key CLIENT_KEY --environment UK
# Do not commit production appId, clientKey, environment, or JWT values.
appId=<APP_ID>
clientKey=<CLIENT_KEY>
environment=<ENVIRONMENT>
"""
    }


def build_task(build_type: str) -> str:
    return f"assemble{BUILD_TYPES[build_type]}"


def build_command(build_type: str) -> str:
    return f"./gradlew {build_task(build_type)}"


def installed_gradle_command(build_type: str) -> str:
    return f"gradle {build_task(build_type)}"


def provider_file_status(args: argparse.Namespace) -> str:
    expected = expected_provider_config(args.provider)
    if not expected:
        return "not required"
    return f"expected at app/{expected}"


def provider_plugin_status(args: argparse.Namespace) -> str:
    expected = expected_provider_config(args.provider)
    if not expected:
        return "not required"
    if has_provider_input(args):
        return f"enabled because `{expected}` was provided"
    return f"deferred until `app/{expected}` is present; rerun with `--provider-config` before building an APK"


def build_files(args: argparse.Namespace, version: str) -> dict[str, str]:
    pkg_path = package_path(args.package)
    provider_label = runtime_provider_label(args)
    files = {
        ".gitignore": """.gradle/
build/
app/build/
local.properties
app/src/main/assets/IMIconnectConfig.properties
app/src/main/assets/WebexConnectConfig.properties
app/google-services.json
app/agconnect-services.json
*.jks
*.keystore
""",
        "gradle.properties": """android.useAndroidX=true
android.enableJetifier=true
org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8
""",
        "settings.gradle.kts": f"""pluginManagement {{
    repositories {{
{hms_repositories(args.provider)}        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}

dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
{hms_repositories(args.provider)}        google()
        mavenCentral()
    }}
}}

rootProject.name = "WebexConnectDemo"
include(":app")
""",
        "build.gradle.kts": f"""plugins {{
{project_plugins(args)}
}}
""",
        "app/build.gradle.kts": f"""plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
{provider_plugin(args)}
}}

android {{
    namespace = "{args.package}"
    compileSdk = 37

    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}

    defaultConfig {{
        applicationId = "{args.package}"
        minSdk = 23
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }}

    buildTypes {{
        getByName("debug") {{
            isDebuggable = true
        }}
        getByName("release") {{
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }}
    }}
}}

kotlin {{
    compilerOptions {{
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.17.0")
    implementation("androidx.activity:activity-compose:1.12.0")
    implementation(platform("androidx.compose:compose-bom:2026.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
{dependencies(args, version)}

    debugImplementation("androidx.compose.ui:ui-tooling")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.7.0")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
}}
""",
        "app/proguard-rules.pro": """-dontwarn org.eclipse.jetty.**
-dontwarn com.google.firebase.messaging.FirebaseMessaging
-dontwarn javax.servlet.**
-dontwarn org.slf4j.**
-keep class net.sqlcipher.** { *; }
-keep class net.sqlcipher.database.* { *; }
-keep class * extends androidx.work.Worker
-keep class * extends androidx.work.InputMerger
-keep public class * extends androidx.work.ListenableWorker { public <init>(...); }
-keep class androidx.work.WorkerParameters
-keep class org.eclipse.paho.client.mqttv3.** { *; }
-keep class org.eclipse.paho.android.service.** { *; }
-keepclasseswithmembers class org.eclipse.paho.** { *; }
""",
        "app/src/main/AndroidManifest.xml": f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />

    <application
        android:name=".WebexConnectDemoApplication"
        android:allowBackup="false"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:theme="@style/AppTheme">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""",
        "app/src/main/res/values/strings.xml": f"""<resources>
    <string name="app_name">{args.app_name}</string>
    <string name="channel_name">Webex Connect messages</string>
    <string name="channel_description">Notifications from Webex Connect Demo</string>
</resources>
""",
        "app/src/main/res/values/styles.xml": """<resources>
    <style name="AppTheme" parent="android:style/Theme.Material.NoActionBar" />
</resources>
""",
        "app/src/main/res/drawable/ic_stat_webex_connect.xml": """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="512"
    android:viewportHeight="512">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M181.196,399.355C107.777,399.355 82.789,306.377 77.19,288.289C63.129,242.869 58.854,201.956 58.402,197.662C55.791,172.887 75.634,155.647 97.412,155.647C113.902,155.647 133.04,165.531 135.575,189.513C136.015,193.547 139.367,228.336 151.227,266.243C163.603,305.805 176.733,321.019 186.188,321.019C201.457,321.019 210.773,281.747 219.009,244.353C225.077,216.804 231.636,189.043 244.585,164.383C267.114,121.483 301.157,111.5 330.567,111.5C395.055,111.5 427.331,186.319 427.331,205.704C427.331,238.099 400.946,246.362 389.51,246.362C364.497,246.362 356.018,229.579 348.881,214.869C342.462,201.635 335.757,190.631 327.089,190.631C324.241,190.631 321.601,192.076 319.16,194.561C297.615,216.489 290.391,331.205 247.313,375.049C223.431,399.355 197.446,399.355 181.196,399.355Z" />
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M415.439,155.647C412.532,155.647 409.608,155.921 406.74,156.487C420.372,176.171 427.193,196.792 427.193,205.702C427.193,238.097 400.807,246.36 389.371,246.36C380.447,246.36 373.629,244.222 368.224,240.806C368.174,241.008 368.124,241.21 368.074,241.412C366.466,247.842 365.198,254.878 363.002,261.726C358.78,274.892 353.085,289.932 347.003,301.57C340.448,314.116 333.958,321.457 326.222,321.072C317.425,320.634 310.292,309.279 301.427,277.186C298.568,266.838 295.921,255.493 293.467,244.353C287.382,216.722 279.912,188.937 267.14,164.383C246.28,124.282 210.694,111.5 182.284,111.5C155.937,111.5 136.253,123.991 120.79,139.729C116.516,144.079 111.849,149.938 107.16,156.825C120.647,160.078 133.4,170.244 135.437,189.511C135.838,193.185 138.653,222.361 148.109,256.172C150.822,247.695 154.778,235.141 163.969,214.869C168.473,205.585 172.538,199.463 176.205,195.73C179.569,192.307 182.598,190.893 185.325,190.893C188.266,190.893 198.309,193.589 208.086,227.945C220.211,270.547 229.235,338.348 263.614,374.347C278.777,390.227 299.997,400.5 329.406,400.5C355.211,400.5 376.725,389.119 392.065,373.288C417.286,347.256 431.106,304.216 436.035,288.289C450.063,242.978 453.992,201.998 454.449,197.662C457.06,172.887 436.217,155.647 415.439,155.647Z" />
</vector>
""",
        f"app/src/main/java/{pkg_path}/WebexConnectDemoApplication.kt": f"""package {args.package}

import android.app.Application

class WebexConnectDemoApplication : Application() {{
    override fun onCreate() {{
        super.onCreate()
        NotificationSupport.createDefaultChannel(this)
    }}
}}
""",
        f"app/src/main/java/{pkg_path}/MainActivity.kt": f"""package {args.package}

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent

class MainActivity : ComponentActivity() {{
    private val controller by lazy {{ WebexConnectSdkController(this, "{provider_label}") }}

    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        NotificationSupport.createDefaultChannel(this)
        setContent {{
            WebexConnectDemoApp(controller)
        }}
    }}

    override fun onDestroy() {{
        controller.release()
        super.onDestroy()
    }}
}}
""",
        f"app/src/main/java/{pkg_path}/ChatModels.kt": f"""package {args.package}

enum class DemoMessageKind {{
    TEXT,
    ALERT,
    QUICK_REPLY,
    GENERIC_TEMPLATE,
    FORM_TEMPLATE,
    MEDIA,
    LOCATION,
    RECEIPT,
    TYPING,
    THREAD_UPDATE,
    DELETED,
    UNKNOWN
}}

data class DemoAction(
    val id: String,
    val title: String,
    val payload: String = "",
    val type: String = ""
)

data class DemoCard(
    val title: String,
    val subtitle: String = "",
    val imageUrl: String = "",
    val imageUrls: List<String> = emptyList(),
    val actions: List<DemoAction> = emptyList()
)

data class DemoField(
    val label: String,
    val name: String = "",
    val value: String = "",
    val type: String = "",
    val required: Boolean = false,
    val options: List<String> = emptyList()
)

data class DemoAttachment(
    val kind: String,
    val label: String,
    val url: String = "",
    val metadata: String = ""
)

data class DemoMessage(
    val id: String,
    val text: String,
    val outgoing: Boolean,
    val status: String = "",
    val type: String = "message",
    val threadId: String = "",
    val relatedId: String = "",
    val kind: DemoMessageKind = DemoMessageKind.TEXT,
    val actions: List<DemoAction> = emptyList(),
    val cards: List<DemoCard> = emptyList(),
    val fields: List<DemoField> = emptyList(),
    val attachments: List<DemoAttachment> = emptyList(),
    val extras: Map<String, String> = emptyMap(),
    val createdAt: Long = 0L
)

data class DemoNotification(
    val id: String,
    val title: String,
    val body: String,
    val timeLabel: String,
    val category: String,
    val unread: Boolean = true
)

data class DemoOrder(
    val id: String,
    val title: String,
    val status: String,
    val eta: String,
    val progress: Float
)

data class DemoProduct(
    val title: String,
    val subtitle: String,
    val price: String,
    val accentName: String
)

data class DemoWorkflow(
    val title: String,
    val description: String,
    val actionLabel: String
)

data class DemoThread(
    val id: String,
    val title: String,
    val category: String = "",
    val status: String = "active",
    val type: String = "conversation",
    val unreadCount: Int = 0,
    val updatedAt: Long = 0L,
    val lastMessage: String = ""
) {{
    val closed: Boolean
        get() = status.equals("closed", ignoreCase = true)

    val announcement: Boolean
        get() = type.equals("announcement", ignoreCase = true)
}}

data class DemoState(
    val userId: String = "",
    val customerId: String = "",
    val appId: String = "",
    val sdkStarted: Boolean = false,
    val sdkVersion: String = "",
    val registered: Boolean = false,
    val connected: Boolean = false,
    val provider: String = "",
    val pushToken: String = "",
    val threadId: String = "",
    val selectedThreadId: String = "",
    val unreadCount: Int = 0,
    val hasMoreThreads: Boolean = false,
    val hasMoreMessages: Boolean = false,
    val creatingThread: Boolean = false,
    val loadingMoreThreads: Boolean = false,
    val loadingMessages: Boolean = false,
    val loadingMoreMessages: Boolean = false,
    val localStoreReady: Boolean = false,
    val syncMaxThreads: Int = 50,
    val syncMaxMessagesPerThread: Int = 50,
    val syncPolicyLabel: String = "",
    val mediaStatus: String = "",
    val lastError: String = "",
    val foregroundNotification: DemoNotification? = null,
    val notifications: List<DemoNotification> = defaultDemoNotifications(),
    val threads: List<DemoThread> = emptyList(),
    val messages: List<DemoMessage> = emptyList(),
    val disabledInteractionIds: Set<String> = emptySet()
)

fun defaultDemoNotifications(): List<DemoNotification> = listOf(
    DemoNotification(
        id = "delivery",
        title = "Delivery update",
        body = "Your order is out for delivery. Ask support if you need to change the address.",
        timeLabel = "Now",
        category = "Order"
    ),
    DemoNotification(
        id = "agent",
        title = "Agent reply",
        body = "Maya from support is available to help with your open request.",
        timeLabel = "5 min",
        category = "Support"
    ),
    DemoNotification(
        id = "offer",
        title = "Service reminder",
        body = "A guided workflow is ready for returns, refunds, and billing questions.",
        timeLabel = "Today",
        category = "Workflow",
        unread = false
    )
)

fun defaultDemoOrders(): List<DemoOrder> = listOf(
    DemoOrder("ORD-2048", "Noise cancelling headphones", "Out for delivery", "Arrives today", 0.78f),
    DemoOrder("ORD-1984", "Smart home starter kit", "Preparing return", "Pickup tomorrow", 0.44f),
    DemoOrder("ORD-1842", "Travel backpack", "Delivered", "Delivered yesterday", 1.0f)
)

fun defaultDemoProducts(): List<DemoProduct> = listOf(
    DemoProduct("Everyday earbuds", "Top rated audio", "\\$79", "mint"),
    DemoProduct("Desk organizer", "Work setup favorite", "\\$32", "coral"),
    DemoProduct("Travel charger", "Fast USB-C charging", "\\$49", "ocean")
)

fun defaultDemoWorkflows(): List<DemoWorkflow> = listOf(
    DemoWorkflow("Track an order", "Get delivery status, proof of delivery, or address help.", "Start tracking"),
    DemoWorkflow("Return or exchange", "Collect reason, pickup slot, photos, and refund preference.", "Start return"),
    DemoWorkflow("Billing help", "Create a secure billing support request with an agent handoff.", "Open billing")
)
""",
        f"app/src/main/java/{pkg_path}/WebexConnectSdkController.kt": f"""package {args.package}

import android.content.Context
import androidx.compose.runtime.mutableStateOf
import com.webex.connect.core.WebexConnect
import com.webex.connect.core.profile.DeviceProfile
import com.webex.connect.inapp.InAppMessaging
import com.webex.connect.inapp.message.InAppButton
import com.webex.connect.inapp.message.InAppMessage
import com.webex.connect.inapp.message.InAppMessageStatus
import com.webex.connect.inapp.message.InAppThread
import com.webex.connect.push.PushMessaging
import org.json.JSONObject
import java.util.Date
import java.util.UUID

class WebexConnectSdkController(
    private val context: Context,
    private val providerName: String
) {{
    val state = mutableStateOf(DemoState(provider = providerName, appId = ConfigGuard.webexConnectAppId(context)))
    private var activeThread: InAppThread? = null
    private val pendingOutgoingIds = mutableSetOf<String>()
    private val pendingOutgoingFingerprints = mutableSetOf<String>()

    fun login(userId: String) {{
        val cleanUserId = userId.trim()
        if (cleanUserId.isEmpty()) {{
            updateError("Enter a User ID")
            return
        }}
        if (!ConfigGuard.hasWebexConnectConfig(context)) {{
            updateError("Add WebexConnectConfig.properties under app/src/main/assets/")
            return
        }}

        val profile = DeviceProfile(DeviceProfile.defaultDeviceId, cleanUserId)
        if (WebexConnect.instance.isRegistered) {{
            state.value = state.value.copy(userId = cleanUserId, registered = true)
            startMessaging()
            return
        }}

        WebexConnect.instance.register(profile) {{ _, exception ->
            if (exception == null) {{
                state.value = state.value.copy(userId = cleanUserId, registered = true, lastError = "")
                startMessaging()
            }} else {{
                updateError(exception.message ?: "Registration failed")
            }}
        }}
    }}

    fun requestNotifications() {{
        PushMessaging.instance.requestNotificationPermission {{ granted ->
            state.value = state.value.copy(lastError = "Notification permission: ${{granted}}")
        }}
    }}

    private fun startMessaging() {{
        PushMessaging.instance.registerPushTokenListener {{ token ->
            state.value = state.value.copy(pushToken = token)
        }}
        PushMessaging.instance.registerMessagingListener {{ pushMessage ->
            upsertMessage(MessageRenderer.fromPushMessage(pushMessage))
            addNotification("New Webex Connect message", pushMessage.toString().take(120), "Push")
        }}
        InAppMessaging.instance.registerConnectionStatusListener {{ status ->
            state.value = state.value.copy(connected = InAppMessaging.instance.isConnected, lastError = status.toString())
        }}
        InAppMessaging.instance.registerMessagingListener {{ message ->
            val rendered = MessageRenderer.fromInAppMessage(message, state.value.threadId, state.value.userId)
            if (shouldSuppressOutgoingEcho(rendered)) {{
                return@registerMessagingListener
            }}
            upsertMessage(rendered)
            message.transactionId?.let {{
                InAppMessaging.instance.sendMessageStatus(it, InAppMessageStatus.READ, null) {{ _, _, exception ->
                    exception?.message?.let(::updateError)
                }}
            }}
        }}

        try {{
            InAppMessaging.instance.connect()
            ensureThread()
            fetchUnreadCount()
        }} catch (exception: Exception) {{
            updateError(exception.message ?: "In-app connection failed")
        }}
    }}

    private fun ensureThread() {{
        val thread = InAppThread().apply {{
            title = "Webex Connect Demo Chat"
            category = "demo"
        }}
        InAppMessaging.instance.createThread(thread) {{ created, exception ->
            if (exception == null && created != null) {{
                activeThread = created
                state.value = state.value.copy(threadId = created.id ?: "")
                fetchMessages()
            }} else {{
                updateError(exception?.message ?: "Thread creation failed")
            }}
        }}
    }}

    fun sendMessage(text: String) {{
        val thread = activeThread ?: return updateError("Thread is not ready")
        val cleanText = text.trim()
        if (cleanText.isEmpty()) return

        val message = InAppMessage().apply {{
            this.message = cleanText
            this.thread = thread
        }}
        publishOutgoing(message, cleanText)
    }}

    fun sendPostback(sourceMessageId: String, action: DemoAction) {{
        val thread = activeThread ?: return updateError("Thread is not ready")
        val title = action.title.trim()
        if (title.isEmpty()) return

        val baseMessage = InAppMessage().apply {{
            this.message = title
            this.thread = thread
        }}
        val button = InAppButton.fromJson(JSONObject().apply {{
            put("id", action.id)
            put("title", title)
            if (action.type.isNotBlank()) put("type", action.type)
            put("payload", JSONObject().apply {{
                put("value", action.payload)
            }})
        }})
        publishOutgoing(InAppMessaging.instance.createPostbackMessage(baseMessage, button), title, sourceMessageId)
    }}

    private fun publishOutgoing(message: InAppMessage, cleanText: String, sourceMessageId: String = "") {{
        val draft = DemoMessage(UUID.randomUUID().toString(), cleanText, true, "sending")
        val fingerprint = messageFingerprint(cleanText)
        if (fingerprint.isNotBlank()) {{
            pendingOutgoingFingerprints.add(fingerprint)
        }}
        upsertMessage(draft)
        InAppMessaging.instance.publishMessage(message) {{ published, exception ->
            if (exception == null) {{
                val id = published?.transactionId ?: draft.id
                if (id != draft.id) {{
                    pendingOutgoingIds.add(id)
                    pendingOutgoingFingerprints.remove(fingerprint)
                }}
                replaceMessage(draft.id, draft.copy(id = id, status = "sent"))
                disableInteraction(sourceMessageId)
            }} else {{
                pendingOutgoingFingerprints.remove(fingerprint)
                replaceMessage(draft.id, draft.copy(status = "failed"))
                updateError(exception.message ?: "Publish failed")
            }}
        }}
    }}

    private fun disableInteraction(sourceMessageId: String) {{
        if (sourceMessageId.isBlank()) return
        state.value = state.value.copy(
            disabledInteractionIds = state.value.disabledInteractionIds + sourceMessageId
        )
    }}

    fun fetchMessages() {{
        val threadId = state.value.threadId
        if (threadId.isBlank()) return
        InAppMessaging.instance.fetchMessages(threadId, Date(), 50) {{ messages, _, exception ->
            if (exception == null) {{
                replaceHistory(messages.map {{ MessageRenderer.fromInAppMessage(it, threadId, state.value.userId) }})
            }} else {{
                updateError(exception?.message ?: "Fetch messages failed")
            }}
        }}
    }}

    fun sendTyping(isTyping: Boolean) {{
        activeThread?.let {{ thread ->
            InAppMessaging.instance.publishTypingIndicator(thread, isTyping) {{ _, _, exception ->
                exception?.message?.let(::updateError)
            }}
        }}
    }}

    fun fetchUnreadCount() {{
        InAppMessaging.instance.fetchUnreadThreadCount {{ count, exception ->
            if (exception == null) state.value = state.value.copy(unreadCount = count ?: 0)
            else updateError(exception.message ?: "Unread count failed")
        }}
    }}

    fun release() {{
        try {{
            InAppMessaging.instance.disconnect()
        }} catch (_: Exception) {{
        }}
    }}

    private fun upsertMessage(message: DemoMessage) {{
        val current = state.value.messages
        val index = current.indexOfFirst {{ it.id == message.id }}
        val next = if (index >= 0) {{
            current.toMutableList().also {{ it[index] = message }}
        }} else {{
            current + message
        }}
        state.value = state.value.copy(messages = next)
    }}

    private fun replaceMessage(oldId: String, message: DemoMessage) {{
        val current = state.value.messages
        val fingerprint = messageFingerprint(message.text)
        val index = current.indexOfFirst {{
            it.id == oldId ||
                it.id == message.id ||
                (message.outgoing && it.outgoing && messageFingerprint(it.text) == fingerprint)
        }}
        if (index >= 0) {{
            val next = current.toMutableList().also {{ it[index] = message }}
            state.value = state.value.copy(messages = next)
        }} else {{
            upsertMessage(message)
        }}
    }}

    private fun replaceHistory(history: List<DemoMessage>) {{
        val existingById = state.value.messages.associateBy {{ it.id }}
        val merged = history.map {{ message ->
            val existing = existingById[message.id]
            if (existing?.outgoing == true) {{
                message.copy(outgoing = true, status = existing.status)
            }} else {{
                message
            }}
        }}.distinctBy {{ it.id }}
        state.value = state.value.copy(messages = merged)
    }}

    private fun shouldSuppressOutgoingEcho(message: DemoMessage): Boolean {{
        if (pendingOutgoingIds.remove(message.id)) {{
            replacePendingOutgoing(message)
            return true
        }}

        val fingerprint = messageFingerprint(message.text)
        if (fingerprint.isBlank() || !pendingOutgoingFingerprints.remove(fingerprint)) {{
            return false
        }}
        replacePendingOutgoing(message)
        return true
    }}

    private fun replacePendingOutgoing(message: DemoMessage) {{
        val fingerprint = messageFingerprint(message.text)
        val current = state.value.messages
        val index = current.indexOfLast {{ it.outgoing && messageFingerprint(it.text) == fingerprint }}
        if (index >= 0) {{
            val next = current.toMutableList().also {{
                it[index] = it[index].copy(id = message.id, status = "sent")
            }}
            state.value = state.value.copy(messages = next)
        }}
    }}

    private fun messageFingerprint(text: String): String {{
        return text.trim().lowercase()
    }}

    private fun addNotification(title: String, body: String, category: String) {{
        val notification = DemoNotification(
            id = UUID.randomUUID().toString(),
            title = title,
            body = body,
            timeLabel = "Now",
            category = category
        )
        state.value = state.value.copy(notifications = listOf(notification) + state.value.notifications)
    }}

    private fun updateError(message: String) {{
        state.value = state.value.copy(lastError = message)
    }}
}}
""",
        f"app/src/main/java/{pkg_path}/ConfigGuard.kt": f"""package {args.package}

import android.content.Context
import java.util.Properties

object ConfigGuard {{
    fun hasWebexConnectConfig(context: Context): Boolean =
        hasAsset(context, "WebexConnectConfig.properties") ||
            hasAsset(context, "IMIconnectConfig.properties")

    fun webexConnectAppId(context: Context): String =
        readProperty(context, "WebexConnectConfig.properties", "appId")
            .ifBlank {{ readProperty(context, "IMIconnectConfig.properties", "appId") }}
            .ifBlank {{ readProperty(context, "WebexConnectConfig.properties", "appID") }}
            .ifBlank {{ readProperty(context, "IMIconnectConfig.properties", "appID") }}
            .ifBlank {{ readProperty(context, "WebexConnectConfig.properties", "app_id") }}
            .ifBlank {{ readProperty(context, "IMIconnectConfig.properties", "app_id") }}

    private fun hasAsset(context: Context, name: String): Boolean =
        runCatching {{
            context.assets.open(name).close()
            true
        }}.getOrDefault(false)

    private fun readProperty(context: Context, assetName: String, key: String): String =
        runCatching {{
            context.assets.open(assetName).use {{ input ->
                Properties().apply {{ load(input) }}.getProperty(key).orEmpty().trim()
            }}
        }}.getOrDefault("")
}}
""",
        f"app/src/main/java/{pkg_path}/MessageRenderer.kt": f"""package {args.package}

import com.webex.connect.inapp.message.InAppButton
import com.webex.connect.inapp.message.InAppMessage
import com.webex.connect.inapp.message.InAppMessageType
import com.webex.connect.inapp.message.attachments.InAppAttachment
import com.webex.connect.inapp.message.attachments.media.InAppAudioAttachment
import com.webex.connect.inapp.message.attachments.media.InAppFileAttachment
import com.webex.connect.inapp.message.attachments.media.InAppImageAttachment
import com.webex.connect.inapp.message.attachments.media.InAppLocationAttachment
import com.webex.connect.inapp.message.attachments.media.InAppVideoAttachment
import com.webex.connect.inapp.message.attachments.templates.InAppFormTemplateAttachment
import com.webex.connect.inapp.message.attachments.templates.InAppGenericTemplateAttachment
import com.webex.connect.inapp.message.attachments.templates.InAppGenericTemplateElement
import com.webex.connect.push.message.PushMessage
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

object MessageRenderer {{
    fun fromInAppMessage(message: InAppMessage, currentThreadId: String = "", currentUserId: String = ""): DemoMessage {{
        val type = message.type?.value.orEmpty().ifBlank {{ message.type?.toString().orEmpty() }}.ifBlank {{ "message" }}
        val json = runCatching {{ message.toJson() }}.getOrNull()
        val attachments = message.attachments.orEmpty()
        val quickReplyActions = message.quickReply?.buttons.orEmpty().map(::toAction)
        val attachmentData = attachments.map(::toAttachment)
        val cards = attachments.filterIsInstance<InAppGenericTemplateAttachment>().flatMap {{ template ->
            template.elements.orEmpty().map(::toCard)
        }}
        val fields = attachments.filterIsInstance<InAppFormTemplateAttachment>().flatMap {{ template ->
            template.formFields.orEmpty().map {{ field ->
                DemoField(
                    label = field.label.orEmpty().ifBlank {{ field.name.orEmpty().ifBlank {{ "Field" }} }},
                    name = field.name.orEmpty(),
                    value = field.value.orEmpty().ifBlank {{ field.values.orEmpty().joinToString(", ") }},
                    type = field.type?.value.orEmpty().ifBlank {{ field.type?.toString().orEmpty() }},
                    required = field.isMandatory,
                    options = field.options.orEmpty()
                )
            }}
        }}
        val kind = kindFor(type, attachments, quickReplyActions, cards, fields)
        val text = readableText(message.message)
            ?: readableText(json?.optString("message"))
            ?: readableText(json?.optString("body"))
            ?: fallbackText(type, kind, attachments, cards, fields, message.status)
        val outgoing = isCustomerAuthoredMessage(kind, message, json, currentUserId)
        val statusSourceType = if (kind == DemoMessageKind.RECEIPT) type else ""
        val status = if (outgoing || kind == DemoMessageKind.RECEIPT) statusLabel(message.status, statusSourceType) else ""
        return DemoMessage(
            id = message.transactionId ?: message.relatedTransactionId ?: UUID.randomUUID().toString(),
            text = text,
            outgoing = outgoing,
            status = status,
            type = type,
            threadId = message.thread?.id.orEmpty().ifBlank {{ currentThreadId }},
            relatedId = message.relatedTransactionId.orEmpty(),
            kind = kind,
            actions = quickReplyActions + attachments.flatMap {{ attachmentActions(it) }},
            cards = cards,
            fields = fields,
            attachments = attachmentData,
            createdAt = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        )
    }}

    fun fromPushMessage(message: PushMessage): DemoMessage {{
        val json = runCatching {{ message.toJson() }}.getOrNull()
        val text = readableText(message.message)
            ?: readableText(message.title)
            ?: readableText(json?.optString("message"))
            ?: readableText(json?.optString("body"))
            ?: "Push notification"
        return DemoMessage(
            id = message.transactionId ?: UUID.randomUUID().toString(),
            text = text,
            outgoing = false,
            status = message.status?.toString().orEmpty().ifBlank {{ "push" }},
            type = "push",
            kind = DemoMessageKind.ALERT,
            createdAt = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        )
    }}

    private fun kindFor(
        type: String,
        attachments: List<InAppAttachment>,
        quickReplyActions: List<DemoAction>,
        cards: List<DemoCard>,
        fields: List<DemoField>
    ): DemoMessageKind {{
        return when {{
            typeMatches(type, InAppMessageType.TYPING_START, InAppMessageType.TYPING_STOP) -> DemoMessageKind.TYPING
            typeMatches(type, InAppMessageType.MESSAGE_DELETED) -> DemoMessageKind.DELETED
            typeMatches(type, InAppMessageType.DELIVERY_RECEIPT, InAppMessageType.READ_RECEIPT, InAppMessageType.CLICKED_RECEIPT) -> DemoMessageKind.RECEIPT
            typeMatches(type, InAppMessageType.THREAD_UPDATE) -> DemoMessageKind.THREAD_UPDATE
            typeMatches(type, InAppMessageType.ALERT) -> DemoMessageKind.ALERT
            fields.isNotEmpty() -> DemoMessageKind.FORM_TEMPLATE
            cards.isNotEmpty() -> DemoMessageKind.GENERIC_TEMPLATE
            quickReplyActions.isNotEmpty() -> DemoMessageKind.QUICK_REPLY
            attachments.any {{ it is InAppLocationAttachment }} -> DemoMessageKind.LOCATION
            attachments.any {{ it is InAppFileAttachment }} -> DemoMessageKind.MEDIA
            type.equals("message", ignoreCase = true) -> DemoMessageKind.TEXT
            else -> DemoMessageKind.UNKNOWN
        }}
    }}

    private fun typeMatches(type: String, vararg values: InAppMessageType): Boolean {{
        return values.any {{ value ->
            type.equals(value.value, ignoreCase = true) || type.equals(value.toString(), ignoreCase = true)
        }}
    }}

    private fun toAction(button: InAppButton): DemoAction {{
        return DemoAction(
            id = button.id.orEmpty(),
            title = button.title.orEmpty().ifBlank {{ "Choose" }},
            payload = button.payload?.toString().orEmpty(),
            type = button.type?.value.orEmpty().ifBlank {{ button.type?.toString().orEmpty() }}
        )
    }}

    private fun toCard(element: InAppGenericTemplateElement): DemoCard {{
        return DemoCard(
            title = element.title.orEmpty().ifBlank {{ "Webex Connect update" }},
            subtitle = element.subtitle.orEmpty(),
            imageUrl = element.imageUrls.orEmpty().firstOrNull().orEmpty(),
            actions = element.buttons.orEmpty().map(::toAction)
        )
    }}

    private fun attachmentActions(attachment: InAppAttachment): List<DemoAction> {{
        return when (attachment) {{
            is InAppGenericTemplateAttachment -> attachment.elements.orEmpty().flatMap {{ it.buttons.orEmpty().map(::toAction) }}
            else -> emptyList()
        }}
    }}

    private fun toAttachment(attachment: InAppAttachment): DemoAttachment {{
        return when (attachment) {{
            is InAppLocationAttachment -> DemoAttachment(
                kind = "location",
                label = "Shared location",
                metadata = "${{attachment.latitude}}, ${{attachment.longitude}}"
            )
            is InAppImageAttachment -> DemoAttachment("image", attachment.fileName.orEmpty().ifBlank {{ "Image" }}, attachment.url?.toString().orEmpty())
            is InAppVideoAttachment -> DemoAttachment("video", attachment.fileName.orEmpty().ifBlank {{ "Video" }}, attachment.url?.toString().orEmpty(), "${{attachment.duration}}s")
            is InAppAudioAttachment -> DemoAttachment("audio", attachment.fileName.orEmpty().ifBlank {{ "Audio" }}, attachment.url?.toString().orEmpty(), "${{attachment.duration}}s")
            is InAppFileAttachment -> {{
                val contentType = attachment.contentType.orEmpty()
                val kind = when {{
                    contentType.startsWith("image/", ignoreCase = true) -> "image"
                    contentType.startsWith("video/", ignoreCase = true) -> "video"
                    contentType.startsWith("audio/", ignoreCase = true) -> "audio"
                    else -> "file"
                }}
                DemoAttachment(kind, attachment.fileName.orEmpty().ifBlank {{ "File" }}, attachment.url?.toString().orEmpty(), contentType)
            }}
            else -> DemoAttachment("attachment", attachment.contentType.orEmpty().ifBlank {{ "Attachment" }})
        }}
    }}

    private fun fallbackText(
        type: String,
        kind: DemoMessageKind,
        attachments: List<InAppAttachment>,
        cards: List<DemoCard>,
        fields: List<DemoField>,
        status: Any?
    ): String {{
        return when (kind) {{
            DemoMessageKind.QUICK_REPLY -> "Choose a quick reply"
            DemoMessageKind.GENERIC_TEMPLATE -> "${{cards.size}} support option(s) available"
            DemoMessageKind.FORM_TEMPLATE -> "Complete the ${{fields.size}}-field support form"
            DemoMessageKind.LOCATION -> "Location shared"
            DemoMessageKind.MEDIA -> "${{attachments.size}} attachment(s)"
            DemoMessageKind.RECEIPT -> "Message status: ${{statusLabel(status)}}"
            DemoMessageKind.TYPING -> if (typeMatches(type, InAppMessageType.TYPING_STOP)) "Typing stopped" else "Typing..."
            DemoMessageKind.THREAD_UPDATE -> "Conversation updated"
            DemoMessageKind.DELETED -> "Message deleted"
            DemoMessageKind.ALERT -> "Webex Connect alert"
            else -> "Message received"
        }}
    }}

    private fun isCurrentUserMessage(message: InAppMessage, json: JSONObject?, currentUserId: String): Boolean {{
        val userId = currentUserId.trim()
        val senderCandidates = listOf(
            json?.optString("senderId"),
            json?.optString("sender_id"),
            json?.optString("from"),
            json?.optString("fromId"),
            json?.optString("from_id"),
            json?.optString("authorId"),
            json?.optString("author_id"),
            json?.optJSONObject("sender")?.optString("id"),
            json?.optJSONObject("from")?.optString("id"),
            json?.optJSONObject("author")?.optString("id")
        ).mapNotNull {{ it?.trim() }}.filter {{ it.isNotBlank() }}
        if (userId.isNotBlank() && senderCandidates.any {{ it.equals(userId, ignoreCase = true) }}) return true
        if (userId.isNotBlank() && senderCandidates.isNotEmpty()) return false
        val directionValue = listOf(
            json?.optString("direction"),
            json?.optString("source"),
            json?.optString("origin"),
            json?.optString("senderType"),
            json?.optString("sender_type"),
            json?.optString("messageOrigin"),
            json?.optJSONObject("sender")?.optString("type"),
            json?.optJSONObject("from")?.optString("type")
        ).mapNotNull {{ it?.trim() }}.firstOrNull {{ it.isNotBlank() }}.orEmpty().lowercase()
        return when {{
            listOf("agent", "bot", "business", "platform", "system", "outbound").any {{ directionValue.contains(it) }} -> false
            listOf("user", "customer", "consumer", "device", "app", "inbound").any {{ directionValue.contains(it) }} -> true
            else -> message.isOutgoing
        }}
    }}

    private fun statusLabel(status: Any?, type: String = ""): String {{
        val value = status?.toString().orEmpty().ifBlank {{ type }}.replace('_', ' ').lowercase()
        return when {{
            value.contains("read") -> "Read"
            value.contains("deliver") -> "Delivered"
            value.contains("sent") || value.contains("submit") || value.contains("success") -> "Sent"
            value.contains("send") -> "Sending"
            value.contains("fail") || value.contains("error") -> "Failed"
            else -> value.replaceFirstChar {{ it.uppercase() }}
        }}.ifBlank {{ "Sent" }}
    }}

    private fun readableText(value: String?): String? {{
        val text = value?.trim().orEmpty()
        if (text.isBlank()) return null
        if (!text.startsWith("{{") && !text.startsWith("[")) return text
        if (text.startsWith("[")) {{
            val array = runCatching {{ JSONArray(text) }}.getOrNull() ?: return null
            return (0 until array.length())
                .asSequence()
                .mapNotNull {{ index -> readableText(array.opt(index)?.toString()) }}
                .firstOrNull()
        }}
        val json = runCatching {{ JSONObject(text) }}.getOrNull() ?: return null
        return listOf(
            "text",
            "message",
            "body",
            "title",
            "description",
            "content",
            "displayText",
            "messageText",
            "notification",
            "alert",
            "data",
            "payload"
        ).asSequence()
            .mapNotNull {{ key ->
                json.opt(key)
                    ?.takeUnless {{ it == JSONObject.NULL }}
                    ?.toString()
                    ?.let(::readableText)
            }}
            .firstOrNull()
    }}
}}
""",
        f"app/src/main/java/{pkg_path}/NotificationSupport.kt": f"""package {args.package}

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import com.webex.connect.push.message.PushMessage
import com.webex.connect.push.notification.NotificationBuilderCallback
import com.webex.connect.push.notification.NotificationFactory
import com.webex.connect.push.PushMessaging

object NotificationSupport {{
    fun createDefaultChannel(context: Context) {{
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            val channel = NotificationChannel(
                NotificationFactory.DEFAULT_CHANNEL_ID,
                context.getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {{
                description = context.getString(R.string.channel_description)
            }}
            context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }}
        PushMessaging.instance.notificationFactory?.notificationBuilderCallback = DemoNotificationBuilder()
    }}
}}

class DemoNotificationBuilder : NotificationBuilderCallback {{
    override fun getActionIconId(context: Context, message: PushMessage, action: String, identifier: String): Int =
        R.drawable.ic_stat_webex_connect

    override fun onBuildNotification(
        context: Context,
        message: PushMessage,
        notificationId: Int,
        builder: NotificationCompat.Builder
    ) {{
        builder.setSmallIcon(R.drawable.ic_stat_webex_connect)
        builder.setContentTitle("Webex Connect Demo")
    }}
}}
""",
        f"app/src/main/java/{pkg_path}/WebexConnectDemoApp.kt": f"""package {args.package}

import android.graphics.BitmapFactory
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val DemoInk = Color(0xFFF2F2F2)
private val DemoMuted = Color(0xB3FFFFFF)
private val DemoSubtle = Color(0x80FFFFFF)
private val DemoCanvas = Color(0xFF1A1A1A)
private val DemoPaper = Color(0xFF262626)
private val DemoElevated = Color(0xFF303030)
private val DemoActive = Color(0x1CFFFFFF)
private val DemoBlue = Color(0xFF3492EB)
private val DemoMint = Color(0xFF17C7A8)
private val DemoCoral = Color(0xFFF55868)
private val DemoOcean = Color(0xFF4EA6FF)
private val DemoWarningContainer = Color(0xFF36220C)
private val DemoWarningText = Color(0xFFFFDA94)
private val DemoBorder = Color(0x33FFFFFF)
private val DemoColorScheme = darkColorScheme(
    primary = DemoBlue,
    onPrimary = Color.White,
    primaryContainer = DemoActive,
    onPrimaryContainer = DemoInk,
    secondary = DemoMint,
    onSecondary = DemoCanvas,
    secondaryContainer = DemoMint.copy(alpha = 0.16f),
    onSecondaryContainer = DemoInk,
    tertiary = DemoOcean,
    tertiaryContainer = DemoOcean.copy(alpha = 0.16f),
    onTertiaryContainer = DemoInk,
    background = DemoCanvas,
    onBackground = DemoInk,
    surface = DemoPaper,
    onSurface = DemoInk,
    surfaceVariant = DemoActive,
    onSurfaceVariant = DemoMuted,
    outline = DemoBorder,
    error = DemoCoral
)

private enum class DemoDestination(val label: String, val icon: ImageVector) {{
    Shop("Shop", Icons.Filled.Home),
    Orders("Orders", Icons.AutoMirrored.Filled.ReceiptLong),
    Support("Support", Icons.Filled.SupportAgent),
    Profile("Profile", Icons.Filled.Person)
}}

@Composable
private fun WebexBrandMark(modifier: Modifier = Modifier) {{
    Image(
        painter = painterResource(id = R.drawable.webex_logo),
        contentDescription = "Webex logo",
        modifier = modifier
    )
}}

@Composable
private fun RemoteImagePreview(url: String, modifier: Modifier = Modifier) {{
    var bitmap by remember(url) {{ mutableStateOf<android.graphics.Bitmap?>(null) }}
    var failed by remember(url) {{ mutableStateOf(false) }}

    LaunchedEffect(url) {{
        bitmap = null
        failed = false
        if (url.isBlank()) return@LaunchedEffect
        runCatching {{
            withContext(Dispatchers.IO) {{
                val connection = URL(url).openConnection().apply {{
                    connectTimeout = 4_000
                    readTimeout = 4_000
                }}
                connection.getInputStream().use {{ stream ->
                    BitmapFactory.decodeStream(stream)
                }}
            }}
        }}.onSuccess {{ decoded ->
            bitmap = decoded
            failed = decoded == null
        }}.onFailure {{
            failed = true
        }}
    }}

    val decoded = bitmap
    if (decoded != null) {{
        Image(
            bitmap = decoded.asImageBitmap(),
            contentDescription = "Message image",
            contentScale = ContentScale.Crop,
            modifier = modifier
        )
    }} else {{
        Box(
            modifier = modifier.background(DemoActive),
            contentAlignment = Alignment.Center
        ) {{
            Text(
                if (failed) "Image unavailable" else "Loading image",
                style = MaterialTheme.typography.labelSmall,
                color = DemoMuted
            )
        }}
    }}
}}

@Composable
private fun demoOutlinedTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = DemoInk,
    unfocusedTextColor = DemoInk,
    disabledTextColor = DemoSubtle,
    focusedContainerColor = DemoActive,
    unfocusedContainerColor = DemoActive,
    disabledContainerColor = DemoActive,
    cursorColor = DemoBlue,
    focusedBorderColor = DemoBlue,
    unfocusedBorderColor = DemoBorder,
    disabledBorderColor = DemoBorder,
    focusedLabelColor = DemoBlue,
    unfocusedLabelColor = DemoMuted,
    disabledLabelColor = DemoSubtle,
    focusedPlaceholderColor = DemoMuted,
    unfocusedPlaceholderColor = DemoMuted,
    disabledPlaceholderColor = DemoSubtle,
    focusedLeadingIconColor = DemoBlue,
    unfocusedLeadingIconColor = DemoMuted
)

@Composable
fun WebexConnectDemoApp(controller: WebexConnectSdkController) {{
    MaterialTheme(colorScheme = DemoColorScheme) {{
        val state by controller.state
        Surface(color = DemoCanvas) {{
            if (!state.registered) LoginScreen(controller) else WebexConnectAppShell(controller, state)
        }}
    }}
}}

@Composable
fun LoginScreen(controller: WebexConnectSdkController) {{
    var userId by remember {{ mutableStateOf("") }}
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DemoCanvas)
            .padding(24.dp)
    ) {{
        Column(
            modifier = Modifier.align(Alignment.Center),
            verticalArrangement = Arrangement.spacedBy(18.dp)
        ) {{
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {{
                WebexBrandMark(
                    Modifier
                        .size(52.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(Color.White)
                        .padding(6.dp)
                )
                Column {{
                    Text("Webex Connect Demo", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = DemoInk)
                    Text("Shopping, orders, notifications, and agent messaging", color = DemoMuted)
                }}
            }}
            Card(
                colors = CardDefaults.cardColors(containerColor = DemoPaper),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {{
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {{
                    Text("Start a customer session", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = DemoInk)
                    Text("Enter a demo User ID. The SDK registers this user after the app starts.", color = DemoMuted)
                    OutlinedTextField(
                        value = userId,
                        onValueChange = {{ userId = it }},
                        label = {{ Text("User ID") }},
                        leadingIcon = {{ Icon(Icons.Filled.Person, contentDescription = null) }},
                        colors = demoOutlinedTextFieldColors(),
                        modifier = Modifier.fillMaxWidth().testTag("user-id-input")
                    )
                    Button(
                        onClick = {{ controller.login(userId) }},
                        modifier = Modifier.fillMaxWidth().height(48.dp).testTag("login-button")
                    ) {{
                        Text("Continue to demo app")
                    }}
                }}
            }}
        }}
    }}
}}

@Composable
private fun WebexConnectAppShell(controller: WebexConnectSdkController, state: DemoState) {{
    var destination by remember {{ mutableStateOf(DemoDestination.Shop) }}
    var showNotifications by remember {{ mutableStateOf(false) }}
    var supportThreadOpen by remember {{ mutableStateOf(false) }}

    BackHandler(enabled = showNotifications) {{
        showNotifications = false
    }}
    BackHandler(enabled = !showNotifications && destination == DemoDestination.Support && supportThreadOpen) {{
        supportThreadOpen = false
    }}
    BackHandler(enabled = !showNotifications && destination != DemoDestination.Shop && !supportThreadOpen) {{
        destination = DemoDestination.Shop
    }}

    Box(Modifier.fillMaxSize()) {{
        Scaffold(
            contentWindowInsets = WindowInsets(left = 0.dp, top = 0.dp, right = 0.dp, bottom = 0.dp),
            topBar = {{
                if (!(destination == DemoDestination.Support && supportThreadOpen)) {{
                    DemoTopBar(
                        state = state,
                        onNotifications = {{ showNotifications = true }}
                    )
                }}
            }},
            bottomBar = {{
                if (!(destination == DemoDestination.Support && supportThreadOpen)) {{
                    NavigationBar(containerColor = DemoPaper) {{
                        DemoDestination.values().forEach {{ item ->
                            NavigationBarItem(
                                selected = destination == item,
                                onClick = {{
                                    destination = item
                                    if (item != DemoDestination.Support) supportThreadOpen = false
                                }},
                                icon = {{ Icon(item.icon, contentDescription = item.label) }},
                                label = {{ Text(item.label) }},
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = DemoBlue,
                                    selectedTextColor = DemoBlue,
                                    indicatorColor = DemoActive,
                                    unselectedIconColor = DemoMuted,
                                    unselectedTextColor = DemoMuted
                                )
                            )
                        }}
                    }}
                }}
            }}
        ) {{ padding ->
            when (destination) {{
                DemoDestination.Shop -> HomeScreen(
                    modifier = Modifier.padding(padding),
                    onOpenSupport = {{ destination = DemoDestination.Support }}
                )
                DemoDestination.Orders -> OrdersScreen(
                    modifier = Modifier.padding(padding),
                    onOpenSupport = {{ destination = DemoDestination.Support }}
                )
                DemoDestination.Support -> SupportWorkspace(
                    controller = controller,
                    state = state,
                    threadOpen = supportThreadOpen,
                    onThreadOpenChange = {{ supportThreadOpen = it }},
                    modifier = Modifier.padding(padding)
                )
                DemoDestination.Profile -> ProfileScreen(
                    controller = controller,
                    state = state,
                    modifier = Modifier.padding(padding)
                )
            }}
        }}

        if (showNotifications) {{
            NotificationCenterSheet(
                notifications = state.notifications,
                onDismiss = {{ showNotifications = false }},
                onOpenSupport = {{
                    showNotifications = false
                    destination = DemoDestination.Support
                    supportThreadOpen = false
                }},
                modifier = Modifier.align(Alignment.TopEnd)
            )
        }}
        state.foregroundNotification?.let {{ notification ->
            ForegroundNotificationBanner(
                notification = notification,
                onDismiss = controller::dismissForegroundNotification,
                onOpenSupport = {{
                    controller.dismissForegroundNotification()
                    destination = DemoDestination.Support
                    supportThreadOpen = false
                }},
                modifier = Modifier.align(Alignment.TopCenter)
            )
        }}
    }}
}}

@Composable
private fun DemoTopBar(state: DemoState, onNotifications: () -> Unit) {{
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(DemoPaper)
            .windowInsetsPadding(WindowInsets.safeDrawing.only(WindowInsetsSides.Top))
            .heightIn(min = 68.dp)
            .padding(horizontal = 16.dp, vertical = 8.dp)
            .testTag("app-top-bar"),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(9.dp)
    ) {{
        WebexBrandMark(
            Modifier
                .size(32.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(Color.White)
                .padding(3.dp)
        )
        Column(modifier = Modifier.weight(1f)) {{
            Text("Webex Store", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }}
        IconButton(onClick = onNotifications, modifier = Modifier.testTag("notification-icon")) {{
            BadgedBox(
                badge = {{
                    if (state.notifications.any {{ it.unread }}) {{
                        Badge {{ Text(state.notifications.count {{ it.unread }}.toString()) }}
                    }}
                }}
            ) {{
                Icon(Icons.Filled.Notifications, contentDescription = "Notifications", tint = DemoInk)
            }}
        }}
    }}
}}

@Composable
private fun HomeScreen(modifier: Modifier = Modifier, onOpenSupport: () -> Unit) {{
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("home-screen")
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {{
        item {{ HeroCard(onOpenSupport) }}
        item {{
            SectionTitle("Recommended for you", "Personalized product cards")
            LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {{
                items(defaultDemoProducts()) {{ product ->
                    ProductSpotlightCard(product)
                }}
            }}
        }}
        item {{
            SectionTitle("Need help?", "Support for orders, returns, and billing")
            SupportEntryCard(onOpenSupport)
        }}
    }}
}}

@Composable
private fun HeroCard(onOpenSupport: () -> Unit) {{
    Card(
        colors = CardDefaults.cardColors(containerColor = DemoElevated),
        modifier = Modifier.fillMaxWidth()
    ) {{
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {{
            Text("Orders, returns, and support", style = MaterialTheme.typography.titleLarge, color = DemoInk, fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text("Get delivery help, product answers, and agent support without leaving your account.", style = MaterialTheme.typography.bodyMedium, color = DemoMuted)
            Button(onClick = onOpenSupport, modifier = Modifier.testTag("support-entry")) {{
                Icon(Icons.Filled.SupportAgent, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Message support")
            }}
        }}
    }}
}}

@Composable
private fun ProductSpotlightCard(product: DemoProduct) {{
    val accent = when (product.accentName) {{
        "mint" -> DemoMint
        "coral" -> DemoCoral
        else -> DemoOcean
    }}
    Card(
        colors = CardDefaults.cardColors(containerColor = DemoPaper),
        modifier = Modifier.width(158.dp).height(174.dp).testTag("product-card")
    ) {{
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {{
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(66.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(accent.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {{
                Icon(Icons.Filled.ShoppingCart, contentDescription = null, tint = accent, modifier = Modifier.size(32.dp))
            }}
            Text(product.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(product.subtitle, style = MaterialTheme.typography.bodySmall, color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(product.price, style = MaterialTheme.typography.titleSmall, color = DemoInk, fontWeight = FontWeight.Bold)
        }}
    }}
}}

@Composable
private fun SupportEntryCard(onOpenSupport: () -> Unit) {{
    Card(colors = CardDefaults.cardColors(containerColor = DemoPaper), modifier = Modifier.fillMaxWidth()) {{
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {{
            Box(Modifier.size(52.dp).clip(CircleShape).background(DemoBlue.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {{
                Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null, tint = DemoBlue)
            }}
            Column(Modifier.weight(1f)) {{
                Text("Talk to support", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = DemoInk)
                Text("Returns, billing, delivery, and product questions route to the right support flow.", style = MaterialTheme.typography.bodyMedium, color = DemoMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }}
            IconButton(onClick = onOpenSupport) {{
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "Open support")
            }}
        }}
    }}
}}

@Composable
private fun OrdersScreen(modifier: Modifier = Modifier, onOpenSupport: () -> Unit) {{
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .testTag("orders-screen")
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {{
        item {{ SectionTitle("Orders", "Tap support when an order needs attention") }}
        items(defaultDemoOrders()) {{ order ->
            OrderStatusCard(order, onOpenSupport)
        }}
    }}
}}

@Composable
private fun OrderStatusCard(order: DemoOrder, onOpenSupport: () -> Unit) {{
    Card(colors = CardDefaults.cardColors(containerColor = DemoPaper), modifier = Modifier.fillMaxWidth().testTag("order-card")) {{
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {{
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {{
                Icon(Icons.Filled.LocalShipping, contentDescription = null, tint = DemoBlue, modifier = Modifier.size(22.dp))
                Column(Modifier.weight(1f)) {{
                    Text(order.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Text(order.id + " - " + order.status, style = MaterialTheme.typography.bodyMedium, color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }}
                Text(order.eta, style = MaterialTheme.typography.labelLarge, color = DemoBlue, fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }}
            Box(Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(99.dp)).background(DemoCanvas)) {{
                Box(Modifier.fillMaxWidth(order.progress).height(6.dp).background(DemoBlue))
            }}
            TextButton(onClick = onOpenSupport) {{
                Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Ask about this order")
            }}
        }}
    }}
}}

@Composable
private fun SupportWorkspace(
    controller: WebexConnectSdkController,
    state: DemoState,
    threadOpen: Boolean,
    onThreadOpenChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {{
    if (threadOpen && state.selectedThreadId.isNotBlank()) {{
        ChatScreen(
            controller = controller,
            state = state,
            onBack = {{ onThreadOpenChange(false) }},
            modifier = modifier
        )
    }} else {{
        ConversationInboxScreen(
            controller = controller,
            state = state,
            onOpenThread = {{ thread ->
                controller.openThread(thread.id)
                onThreadOpenChange(true)
            }},
            modifier = modifier
        )
    }}
}}

@Composable
private fun ConversationInboxScreen(
    controller: WebexConnectSdkController,
    state: DemoState,
    onOpenThread: (DemoThread) -> Unit,
    modifier: Modifier = Modifier
) {{
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(DemoCanvas)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {{
        ThreadListPanel(
            controller = controller,
            state = state,
            onOpenThread = onOpenThread,
            modifier = Modifier.weight(1f)
        )
    }}
}}

@Composable
private fun ProfileScreen(
    controller: WebexConnectSdkController,
    state: DemoState,
    modifier: Modifier = Modifier
) {{
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(DemoCanvas)
            .padding(18.dp)
            .testTag("profile-settings-screen"),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        contentPadding = PaddingValues(bottom = 18.dp)
    ) {{
        item {{ ProfileSummaryCard(state = state, onSwitchUser = controller::signOut) }}
        item {{ AccountToolsPanel(controller = controller, state = state) }}
        item {{ PushTokenCard(state = state) }}
        item {{ AdvancedSdkToolsPanel(controller = controller, state = state) }}
        item {{ QaPanel(state) }}
    }}
}}

@Composable
private fun ProfileSummaryCard(state: DemoState, onSwitchUser: () -> Unit) {{
    Card(
        colors = CardDefaults.cardColors(containerColor = DemoElevated),
        modifier = Modifier.fillMaxWidth().testTag("profile-summary-card")
    ) {{
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {{
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {{
                Box(
                    modifier = Modifier
                        .size(72.dp)
                        .clip(CircleShape)
                        .background(DemoActive),
                    contentAlignment = Alignment.Center
                ) {{
                    WebexBrandMark(Modifier.size(48.dp).clip(RoundedCornerShape(14.dp)).background(Color.White).padding(5.dp))
                }}
                Column(Modifier.weight(1f)) {{
                    Text(state.userId.ifBlank {{ "Registered user" }}, color = DemoInk, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(state.customerId.ifBlank {{ "No Customer ID set" }}, color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(state.provider, color = DemoMint, style = MaterialTheme.typography.labelMedium)
                }}
            }}
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                ProfileMetric("Started", if (state.sdkStarted) "Yes" else "No", Modifier.weight(1f))
                ProfileMetric("Registered", if (state.registered) "Yes" else "No", Modifier.weight(1f))
                ProfileMetric("Store", if (state.localStoreReady) "Ready" else "Pending", Modifier.weight(1f))
            }}
            Button(onClick = onSwitchUser, modifier = Modifier.fillMaxWidth().testTag("switch-user-button")) {{
                Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(8.dp))
                Text("Switch user")
            }}
        }}
    }}
}}

@Composable
private fun ProfileMetric(label: String, value: String, modifier: Modifier = Modifier) {{
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(DemoActive)
            .padding(horizontal = 10.dp, vertical = 9.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {{
        Text(value, color = DemoInk, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(label, color = DemoMuted, style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }}
}}

@Composable
private fun PushTokenCard(state: DemoState) {{
    val clipboardManager = LocalClipboardManager.current
    val pushEnabled = state.provider.contains("Push", ignoreCase = true)
    val token = when {{
        state.pushToken.isNotBlank() -> state.pushToken
        pushEnabled -> "Waiting for push token"
        else -> "Push is not enabled in this build"
    }}
    Card(colors = CardDefaults.cardColors(containerColor = DemoPaper), modifier = Modifier.fillMaxWidth().testTag("push-token-card")) {{
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {{
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                Icon(Icons.Filled.Notifications, contentDescription = null, tint = DemoBlue)
                Column(Modifier.weight(1f)) {{
                    Text("Push token", fontWeight = FontWeight.Bold, color = DemoInk)
                    Text("Device token from the push listener.", color = DemoMuted, style = MaterialTheme.typography.labelMedium)
                }}
                IconButton(
                    enabled = state.pushToken.isNotBlank(),
                    onClick = {{ clipboardManager.setText(AnnotatedString(state.pushToken)) }},
                    modifier = Modifier.testTag("copy-push-token-button")
                ) {{
                    Icon(Icons.Filled.ContentCopy, contentDescription = "Copy push token", tint = if (state.pushToken.isNotBlank()) DemoBlue else DemoSubtle)
                }}
            }}
            Text(
                token,
                color = DemoMuted,
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.testTag("push-token-value")
            )
        }}
    }}
}}

@Composable
private fun AccountToolsPanel(controller: WebexConnectSdkController, state: DemoState) {{
    var customerId by remember(state.customerId, state.userId) {{ mutableStateOf(state.customerId) }}
    Card(colors = CardDefaults.cardColors(containerColor = DemoPaper), modifier = Modifier.fillMaxWidth().testTag("account-tools-panel")) {{
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {{
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                Icon(Icons.Filled.Person, contentDescription = null, tint = DemoBlue)
                Column(Modifier.weight(1f)) {{
                    Text("Profile", fontWeight = FontWeight.Bold, color = DemoInk)
                    Text("User ID: " + state.userId.ifBlank {{ "pending" }}, color = DemoMuted, style = MaterialTheme.typography.labelMedium)
                    Text("App ID: " + state.appId.ifBlank {{ "Not configured" }}, color = DemoMuted, style = MaterialTheme.typography.labelMedium, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.testTag("profile-app-id"))
                }}
                TextButton(onClick = controller::signOut, modifier = Modifier.testTag("sign-out-button")) {{
                    Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Switch user")
                }}
            }}
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                OutlinedTextField(
                    value = customerId,
                    onValueChange = {{ customerId = it }},
                    modifier = Modifier.weight(1f).testTag("profile-customer-id-input"),
                    label = {{ Text("Customer ID") }},
                    colors = demoOutlinedTextFieldColors(),
                    singleLine = true
                )
                Button(onClick = {{ controller.updateProfileCustomerId(customerId) }}, modifier = Modifier.testTag("profile-update-button")) {{
                    Text("Update")
                }}
            }}
        }}
    }}
}}

@Composable
private fun AdvancedSdkToolsPanel(controller: WebexConnectSdkController, state: DemoState) {{
    var threadLimit by remember(state.syncMaxThreads) {{ mutableStateOf(state.syncMaxThreads.toString()) }}
    var messageLimit by remember(state.syncMaxMessagesPerThread) {{ mutableStateOf(state.syncMaxMessagesPerThread.toString()) }}
    Card(colors = CardDefaults.cardColors(containerColor = DemoPaper), modifier = Modifier.fillMaxWidth().testTag("advanced-sdk-panel")) {{
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {{
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                Icon(Icons.Filled.Sync, contentDescription = null, tint = DemoMint)
                Column(Modifier.weight(1f)) {{
                    Text("Message sync", fontWeight = FontWeight.Bold, color = DemoInk)
                    Text(
                        if (state.localStoreReady) "Local store: " + state.syncPolicyLabel else "Local store pending",
                        color = DemoMuted,
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }}
            }}
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {{
                OutlinedTextField(
                    value = threadLimit,
                    onValueChange = {{ threadLimit = syncLimitInputValue(it) }},
                    modifier = Modifier.weight(1f).testTag("sync-thread-limit-input"),
                    label = {{ Text("Threads") }},
                    colors = demoOutlinedTextFieldColors(),
                    singleLine = true
                )
                OutlinedTextField(
                    value = messageLimit,
                    onValueChange = {{ messageLimit = syncLimitInputValue(it) }},
                    modifier = Modifier.weight(1f).testTag("sync-message-limit-input"),
                    label = {{ Text("Messages") }},
                    colors = demoOutlinedTextFieldColors(),
                    singleLine = true
                )
            }}
            Button(
                onClick = {{
                    controller.configureLocalStoreAndSync(
                        parsedSyncLimit(threadLimit, state.syncMaxThreads),
                        parsedSyncLimit(messageLimit, state.syncMaxMessagesPerThread)
                    )
                }},
                modifier = Modifier.fillMaxWidth().testTag("sync-policy-button")
            ) {{
                Text("Apply sync limits")
            }}
            Text("Default is 50 threads and 50 messages per thread. Adjust before reconnecting when QA needs a wider local history window.", color = DemoMuted, style = MaterialTheme.typography.labelSmall)
        }}
    }}
}}

@Composable
private fun AutomationWorkflowCard(workflow: DemoWorkflow, controller: WebexConnectSdkController) {{
    Card(colors = CardDefaults.cardColors(containerColor = DemoPaper), modifier = Modifier.width(250.dp).testTag("workflow-card")) {{
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {{
            Icon(Icons.Filled.Build, contentDescription = null, tint = DemoCoral)
            Text(workflow.title, fontWeight = FontWeight.Bold, color = DemoInk)
            Text(workflow.description, color = DemoMuted, minLines = 2)
            TextButton(onClick = {{ controller.sendMessage(workflow.actionLabel) }}) {{
                Text(workflow.actionLabel)
            }}
        }}
    }}
}}

@Composable
private fun ThreadListPanel(
    controller: WebexConnectSdkController,
    state: DemoState,
    onOpenThread: (DemoThread) -> Unit,
    modifier: Modifier = Modifier
) {{
    var newThreadTitle by remember {{ mutableStateOf("") }}
    var threadSearch by remember {{ mutableStateOf("") }}
    var threadFilter by remember {{ mutableStateOf("all") }}
    var showNewThreadDialog by remember {{ mutableStateOf(false) }}
    val visibleThreads = remember(state.threads, threadSearch, threadFilter) {{
        state.threads.filter {{ thread ->
            val query = threadSearch.trim()
            val matchesSearch = query.isBlank() ||
                thread.title.contains(query, ignoreCase = true) ||
                thread.category.contains(query, ignoreCase = true) ||
                thread.status.contains(query, ignoreCase = true) ||
                thread.type.contains(query, ignoreCase = true)
            val matchesFilter = when (threadFilter) {{
                "unread" -> thread.unreadCount > 0
                "open" -> !thread.closed && !thread.announcement
                else -> true
            }}
            matchesSearch && matchesFilter
        }}
    }}
    Column(
        modifier = modifier.fillMaxSize().testTag("thread-list-panel"),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {{
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {{
                Column(Modifier.weight(1f)) {{
                    Text("Conversations", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(
                        if (state.threads.isEmpty()) "Start a conversation or refresh existing threads." else visibleThreads.size.toString() + " of " + state.threads.size.toString() + " conversations",
                        color = DemoMuted,
                        style = MaterialTheme.typography.labelMedium
                    )
                }}
                IconButton(
                    onClick = {{ showNewThreadDialog = true }},
                    modifier = Modifier.testTag("new-thread-toggle-button")
                ) {{
                    Icon(Icons.Filled.Add, contentDescription = "New conversation", tint = DemoInk)
                }}
                IconButton(onClick = controller::refreshThreads, modifier = Modifier.testTag("refresh-threads-button")) {{
                    Icon(Icons.Filled.Refresh, contentDescription = "Refresh threads", tint = DemoBlue)
                }}
            }}

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {{
                OutlinedTextField(
                    value = threadSearch,
                    onValueChange = {{ threadSearch = it }},
                    modifier = Modifier.weight(1f).heightIn(min = 54.dp).testTag("thread-search-input"),
                    leadingIcon = {{ Icon(Icons.Filled.Search, contentDescription = null) }},
                    label = {{ Text("Search conversations") }},
                    colors = demoOutlinedTextFieldColors(),
                    singleLine = true
                )
                IconButton(
                    onClick = {{
                        threadFilter = when (threadFilter) {{
                            "all" -> "unread"
                            "unread" -> "open"
                            else -> "all"
                        }}
                    }},
                    modifier = Modifier
                        .size(52.dp)
                        .clip(CircleShape)
                        .background(if (threadFilter != "all") DemoBlue.copy(alpha = 0.18f) else DemoActive)
                        .testTag("thread-filter-button")
                ) {{
                    Icon(Icons.Filled.Tune, contentDescription = "Filter conversations", tint = if (threadFilter != "all") DemoBlue else DemoInk)
                }}
            }}

            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {{
                FilterChip(
                    selected = threadFilter == "all",
                    onClick = {{ threadFilter = "all" }},
                    label = {{ Text("All", maxLines = 1) }},
                    modifier = Modifier.testTag("thread-filter-all")
                )
                FilterChip(
                    selected = threadFilter == "unread",
                    onClick = {{ threadFilter = "unread" }},
                    label = {{ Text("Unread", maxLines = 1) }},
                    modifier = Modifier.testTag("thread-filter-unread")
                )
                FilterChip(
                    selected = threadFilter == "open",
                    onClick = {{ threadFilter = "open" }},
                    label = {{ Text("Open", maxLines = 1) }},
                    modifier = Modifier.testTag("thread-filter-open")
                )
            }}

            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .testTag("thread-list")
            ) {{
                if (visibleThreads.isEmpty()) {{
                    item {{
                        EmptyThreadInbox(
                            hasThreads = state.threads.isNotEmpty()
                        )
                    }}
                }} else {{
                    itemsIndexed(
                        visibleThreads,
                        key = {{ index, thread -> "thread-" + index + "-" + thread.id }}
                    ) {{ index, thread ->
                        ThreadInboxRow(
                            thread = thread,
                            selected = thread.id == state.selectedThreadId,
                            onOpen = {{ onOpenThread(thread) }},
                            modifier = Modifier.testTag("thread-list-row-" + index)
                        )
                    }}
                }}

                if (state.hasMoreThreads) {{
                    item {{
                        TextButton(
                            enabled = !state.loadingMoreThreads,
                            onClick = controller::loadMoreThreads,
                            modifier = Modifier.fillMaxWidth().testTag("load-more-threads-button")
                        ) {{
                            Icon(Icons.Filled.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(if (state.loadingMoreThreads) "Loading conversations" else "Load older conversations")
                        }}
                    }}
                }}
            }}
    }}
    if (showNewThreadDialog) {{
        NewThreadDialog(
            title = newThreadTitle,
            creating = state.creatingThread,
            onTitleChange = {{ newThreadTitle = it }},
            onDismiss = {{ showNewThreadDialog = false }},
            onCreate = {{
                controller.createNewThread(newThreadTitle.ifBlank {{ "Support conversation" }})
                newThreadTitle = ""
                showNewThreadDialog = false
            }}
        )
    }}
}}

@Composable
private fun NewThreadDialog(
    title: String,
    creating: Boolean,
    onTitleChange: (String) -> Unit,
    onDismiss: () -> Unit,
    onCreate: () -> Unit
) {{
    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("new-thread-dialog"),
        containerColor = DemoPaper,
        tonalElevation = 0.dp,
        title = {{
            Text("New conversation", fontWeight = FontWeight.Bold, color = DemoInk)
        }},
        text = {{
            Column(
                modifier = Modifier.testTag("new-thread-create-row"),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {{
                Text("Add a short title so this support thread is easy to find later.", color = DemoMuted)
                OutlinedTextField(
                    value = title,
                    onValueChange = onTitleChange,
                    modifier = Modifier.fillMaxWidth().testTag("new-thread-title-input"),
                    label = {{ Text("Conversation title") }},
                    colors = demoOutlinedTextFieldColors(),
                    singleLine = true
                )
            }}
        }},
        confirmButton = {{
            Button(
                enabled = !creating,
                onClick = onCreate,
                modifier = Modifier.testTag("new-thread-button")
            ) {{
                Text(if (creating) "Creating" else "Create")
            }}
        }},
        dismissButton = {{
            TextButton(onClick = onDismiss) {{
                Text("Cancel")
            }}
        }}
    )
}}

@Composable
private fun EmptyThreadInbox(hasThreads: Boolean) {{
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 18.dp, vertical = 28.dp)
            .clip(RoundedCornerShape(24.dp))
            .background(DemoPaper)
            .padding(18.dp)
            .testTag("empty-thread-inbox"),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {{
        Box(Modifier.size(58.dp).clip(CircleShape).background(DemoBlue.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {{
            Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null, tint = DemoBlue)
        }}
        Text(if (hasThreads) "No matching conversations" else "No conversations yet", fontWeight = FontWeight.Bold, color = DemoInk)
        Text(
            if (hasThreads) "Adjust search or filters to see more threads." else "Tap + to start a support conversation.",
            color = DemoMuted,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }}
}}

@Composable
private fun ThreadInboxRow(thread: DemoThread, selected: Boolean, onOpen: () -> Unit, modifier: Modifier = Modifier) {{
    val avatarColor = threadAvatarColor(thread)
    Card(
        colors = CardDefaults.cardColors(containerColor = if (selected) DemoActive else DemoPaper),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
        shape = RoundedCornerShape(16.dp),
        modifier = modifier
            .fillMaxWidth()
            .testTag("thread-list-row")
    ) {{
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onOpen)
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {{
            Box(Modifier.size(54.dp).testTag("thread-avatar")) {{
                Box(
                    Modifier
                        .matchParentSize()
                        .clip(CircleShape)
                        .background(avatarColor.copy(alpha = 0.14f)),
                    contentAlignment = Alignment.Center
                ) {{
                    Text(threadInitials(thread), color = avatarColor, fontWeight = FontWeight.Bold)
                }}
                ThreadPresenceDot(thread, Modifier.align(Alignment.BottomEnd))
            }}

            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(5.dp)) {{
                Row(verticalAlignment = Alignment.CenterVertically) {{
                    Text(threadTitle(thread), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                    Text(threadTimeLabel(thread.updatedAt), color = DemoMuted, style = MaterialTheme.typography.labelMedium, modifier = Modifier.testTag("thread-row-time"))
                }}
                Text(threadPreview(thread), style = MaterialTheme.typography.bodyMedium, color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {{
                    if (thread.unreadCount > 0) {{
                        ThreadMetadataPill(thread.unreadCount.toString() + " unread", "thread-unread-badge", selected = true)
                    }}
                    if (thread.closed) {{
                        ThreadMetadataPill("Closed", "thread-closed-badge")
                    }}
                    if (thread.announcement) {{
                        ThreadMetadataPill("Announcement", "thread-announcement-badge")
                    }}
                    if (!thread.closed && !thread.announcement && thread.unreadCount == 0) {{
                        Text("Active support", color = DemoMuted, style = MaterialTheme.typography.labelSmall)
                    }}
                }}
            }}
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "Open conversation", tint = DemoMuted)
        }}
    }}
}}

@Composable
private fun ThreadPresenceDot(thread: DemoThread, modifier: Modifier = Modifier) {{
    Box(
        modifier
            .size(18.dp)
            .clip(CircleShape)
            .background(DemoPaper)
            .padding(3.dp)
            .testTag("thread-presence-dot")
    ) {{
        Box(
            Modifier
                .matchParentSize()
                .clip(CircleShape)
                .background(
                    when {{
                        thread.closed -> DemoMuted.copy(alpha = 0.55f)
                        thread.announcement -> DemoBlue
                        else -> DemoMint
                    }}
                )
        )
    }}
}}

@Composable
private fun ThreadMetadataPill(label: String, tag: String, selected: Boolean = false) {{
    Text(
        label,
        color = if (selected) Color.White else DemoMuted,
        style = MaterialTheme.typography.labelSmall,
        modifier = Modifier
            .clip(RoundedCornerShape(99.dp))
            .background(if (selected) DemoBlue else DemoActive)
            .padding(horizontal = 8.dp, vertical = 4.dp)
            .testTag(tag)
    )
}}

private fun threadTitle(thread: DemoThread): String =
    thread.title.ifBlank {{ if (thread.announcement) "Webex Announcement" else "Webex Care" }}

private fun threadPreview(thread: DemoThread): String = when {{
    thread.lastMessage.isNotBlank() -> compactPreviewText(thread.lastMessage)
    thread.closed -> "Thread closed. Reopen it to continue the conversation."
    thread.announcement -> "Platform announcement from Webex Connect."
    thread.unreadCount > 0 -> "New message waiting in this conversation."
    thread.category.isNotBlank() -> thread.category.replaceFirstChar {{ it.uppercase() }} + " support conversation"
    else -> "Ready to help with delivery, returns, billing, or product questions."
}}

private fun compactPreviewText(value: String): String =
    stripDiagnosticPayload(value)
        .replace(Regex("\\\\s+"), " ")
        .trim()
        .ifBlank {{ "New Webex Connect message" }}

private fun syncLimitInputValue(value: String): String =
    value.filter {{ it.isDigit() }}.take(3)

private fun parsedSyncLimit(value: String, fallback: Int): Int =
    (value.toIntOrNull() ?: fallback).coerceIn(1, 500)

private fun threadInitials(thread: DemoThread): String {{
    val parts = threadTitle(thread).split(" ").filter {{ it.isNotBlank() }}
    return parts.take(2).joinToString("") {{ it.first().uppercaseChar().toString() }}.ifBlank {{ "WC" }}
}}

private fun threadAvatarColor(thread: DemoThread): Color {{
    val colors = listOf(DemoBlue, DemoMint, DemoCoral, DemoOcean, Color(0xFF0F766E))
    val index = (thread.id.hashCode() and Int.MAX_VALUE) % colors.size
    return colors[index]
}}

private fun threadTimeLabel(updatedAt: Long): String {{
    if (updatedAt <= 0L) return "Now"
    val diff = System.currentTimeMillis() - updatedAt
    val minute = 60_000L
    val hour = 60L * minute
    val day = 24L * hour
    return when {{
        diff < minute -> "Now"
        diff < hour -> (diff / minute).toString() + "m"
        diff < day -> SimpleDateFormat("hh:mm a", Locale.getDefault()).format(Date(updatedAt))
        diff < 2L * day -> "Yesterday"
        else -> SimpleDateFormat("dd/MM/yyyy", Locale.getDefault()).format(Date(updatedAt))
    }}
}}

private fun conversationDateLabel(createdAt: Long): String {{
    if (createdAt <= 0L) return "Today"
    val diff = System.currentTimeMillis() - createdAt
    val day = 24L * 60L * 60L * 1000L
    return when {{
        diff < day -> "Today"
        diff < 2L * day -> "Yesterday"
        else -> SimpleDateFormat("dd/MM/yyyy", Locale.getDefault()).format(Date(createdAt))
    }}
}}

private fun messageTimeLabel(createdAt: Long): String =
    if (createdAt <= 0L) "" else SimpleDateFormat("hh:mm a", Locale.getDefault()).format(Date(createdAt))

@Composable
fun ChatScreen(
    controller: WebexConnectSdkController,
    state: DemoState,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {{
    var draft by remember {{ mutableStateOf("") }}
    val focusManager = LocalFocusManager.current
    val attachmentPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) {{ uri ->
        uri?.let(controller::uploadSelectedMedia)
    }}
    val selectedThread = state.threads.firstOrNull {{ it.id == state.selectedThreadId }}
    val repliesEnabled = selectedThread != null && selectedThread.closed != true && selectedThread.announcement != true
    val dateLabel = state.messages.firstOrNull {{ it.createdAt > 0L }}
        ?.let {{ conversationDateLabel(it.createdAt) }}
        ?: "Today"
    val listState = rememberLazyListState()
    LaunchedEffect(state.messages.size, state.messages.lastOrNull()?.id) {{
        if (state.messages.isNotEmpty()) {{
            listState.animateScrollToItem(state.messages.lastIndex)
        }}
    }}
    Box(modifier.fillMaxSize().background(DemoCanvas).testTag("chat-thread-screen")) {{
        Column(Modifier.fillMaxSize().testTag("agent-chat-card")) {{
            ChatThreadHeader(
                selectedThread = selectedThread,
                state = state,
                onBack = onBack,
                onCloseThread = controller::closeThread,
                onReopenThread = controller::reopenThread
            )
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .background(DemoCanvas)
                    .testTag("message-list"),
                state = listState,
                contentPadding = PaddingValues(horizontal = 14.dp, top = 8.dp, bottom = 14.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {{
                if (selectedThread?.closed == true) {{
                    item {{
                        ThreadClosedState(onReopenThread = controller::reopenThread)
                    }}
                }}
                item {{ ChatDateChip(dateLabel) }}
                if (state.hasMoreMessages) {{
                    item {{
                        TextButton(
                            enabled = !state.loadingMoreMessages,
                            onClick = controller::loadOlderMessages,
                            modifier = Modifier.fillMaxWidth().testTag("load-more-messages-button")
                        ) {{
                            Icon(Icons.Filled.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text(if (state.loadingMoreMessages) "Loading messages" else "Load older messages")
                        }}
                    }}
                }}
                if (state.loadingMessages && state.messages.isEmpty()) {{
                    item {{ MessageLoadingState() }}
                }} else if (state.messages.isEmpty() && selectedThread?.closed != true) {{
                    item {{ EmptyConversationState() }}
                }} else {{
                    itemsIndexed(
                        state.messages,
                        key = {{ index, message -> messageListKey(index, message) }}
                    ) {{ _, message ->
                        MessageBubble(
                            message,
                            disabled = !repliesEnabled || state.disabledInteractionIds.contains(message.id),
                            onAction = controller::sendPostback,
                            onDelete = controller::deleteMessage
                        )
                    }}
                }}
            }}
            if (repliesEnabled) {{
                ChatComposer(
                    draft = draft,
                    enabled = true,
                    onDraftChange = {{
                        draft = it
                        controller.sendTyping(it.isNotEmpty())
                    }},
                    onAttach = {{
                        focusManager.clearFocus()
                        attachmentPicker.launch("*/*")
                    }},
                    onSend = {{
                        val message = draft
                        focusManager.clearFocus()
                        controller.sendMessage(message)
                        draft = ""
                    }}
                )
            }}
        }}
    }}
}}

@Composable
private fun MessageLoadingState() {{
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 18.dp)
            .testTag("message-loading-state"),
        horizontalArrangement = Arrangement.Center
    ) {{
        Surface(
            color = DemoElevated,
            shape = RoundedCornerShape(99.dp)
        ) {{
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {{
                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp, color = DemoBlue)
                Text("Loading conversation", color = DemoMuted, style = MaterialTheme.typography.labelMedium)
            }}
        }}
    }}
}}

@Composable
private fun EmptyConversationState() {{
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 28.dp)
            .testTag("empty-conversation-state"),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {{
        Box(Modifier.size(54.dp).clip(CircleShape).background(DemoElevated), contentAlignment = Alignment.Center) {{
            Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null, tint = DemoBlue, modifier = Modifier.size(24.dp))
        }}
        Text("No messages yet", color = DemoInk, fontWeight = FontWeight.Bold)
        Text(
            "Send a message to start this conversation.",
            color = DemoMuted,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center
        )
    }}
}}

@Composable
private fun ChatThreadHeader(
    selectedThread: DemoThread?,
    state: DemoState,
    onBack: () -> Unit,
    onCloseThread: () -> Unit,
    onReopenThread: () -> Unit
) {{
    val title = selectedThreadTitle(selectedThread)
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(DemoCanvas)
            .statusBarsPadding()
            .heightIn(min = 72.dp)
            .padding(horizontal = 10.dp, vertical = 4.dp)
            .testTag("chat-thread-header"),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {{
        IconButton(onClick = onBack, modifier = Modifier.testTag("chat-back-button")) {{
            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to conversations", tint = DemoInk)
        }}
        WebexBrandMark(
            Modifier
                .size(42.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color.White)
                .padding(5.dp)
        )
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {{
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.testTag("thread-header-title"))
            ThreadStatusLine(selectedThread = selectedThread, state = state)
            ThreadIdentityLine(selectedThread = selectedThread, state = state)
        }}
        ChatThreadMenu(
            selectedThread = selectedThread,
            onCloseThread = onCloseThread,
            onReopenThread = onReopenThread
        )
    }}
}}

private fun selectedThreadTitle(selectedThread: DemoThread?): String =
    selectedThread?.let(::threadTitle)?.trim()?.takeIf {{ it.isNotBlank() }} ?: "Webex Connect Demo"

private fun compactThreadId(threadId: String): String {{
    val cleanId = threadId.trim()
    return if (cleanId.length <= 18) cleanId else cleanId.take(8) + "..." + cleanId.takeLast(6)
}}

@Composable
private fun ThreadIdentityLine(selectedThread: DemoThread?, state: DemoState) {{
    val clipboardManager = LocalClipboardManager.current
    val threadId = selectedThread?.id.orEmpty().ifBlank {{ state.selectedThreadId.ifBlank {{ state.threadId }} }}
    if (threadId.isBlank()) return
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier.testTag("thread-identity-line")
    ) {{
        Text(
            "Thread ID " + compactThreadId(threadId),
            color = DemoSubtle,
            style = MaterialTheme.typography.labelSmall,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f).testTag("thread-id-label")
        )
        Icon(
            Icons.Filled.ContentCopy,
            contentDescription = "Copy thread ID",
            tint = DemoSubtle,
            modifier = Modifier
                .size(24.dp)
                .clip(CircleShape)
                .clickable {{ clipboardManager.setText(AnnotatedString(threadId)) }}
                .padding(4.dp)
                .testTag("copy-thread-id-button")
        )
    }}
}}

@Composable
private fun ThreadStatusLine(selectedThread: DemoThread?, state: DemoState) {{
    val closed = selectedThread?.closed == true
    val announcement = selectedThread?.announcement == true
    val label = when {{
        closed -> "Thread closed"
        announcement -> "Announcement"
        state.connected -> "Active"
        else -> "Connecting"
    }}
    val color = when {{
        closed -> DemoSubtle
        announcement -> DemoMuted
        state.connected -> DemoMint
        else -> DemoMuted
    }}
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier.testTag("thread-status-line")
    ) {{
        Box(Modifier.size(8.dp).clip(CircleShape).background(color).testTag("thread-status-dot"))
        Text(
            label,
            color = color,
            style = MaterialTheme.typography.labelLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }}
}}

@Composable
private fun ChatThreadMenu(
    selectedThread: DemoThread?,
    onCloseThread: () -> Unit,
    onReopenThread: () -> Unit
) {{
    var expanded by remember {{ mutableStateOf(false) }}
    Box {{
        IconButton(onClick = {{ expanded = true }}, modifier = Modifier.testTag("thread-header-menu-button")) {{
            Icon(Icons.Filled.MoreVert, contentDescription = "Conversation options", tint = DemoInk)
        }}
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = {{ expanded = false }},
            modifier = Modifier.testTag("thread-header-menu")
        ) {{
            DropdownMenuItem(
                text = {{ Text("View details") }},
                leadingIcon = {{ Icon(Icons.Filled.Person, contentDescription = null) }},
                onClick = {{ expanded = false }},
                modifier = Modifier.testTag("thread-menu-details")
            )
            DropdownMenuItem(
                text = {{ Text("Search in conversation") }},
                leadingIcon = {{ Icon(Icons.Filled.Search, contentDescription = null) }},
                onClick = {{ expanded = false }},
                modifier = Modifier.testTag("thread-menu-search")
            )
            when {{
                selectedThread == null -> DropdownMenuItem(
                    text = {{ Text("No conversation selected") }},
                    enabled = false,
                    onClick = {{ }}
                )
                selectedThread.closed -> DropdownMenuItem(
                    text = {{ Text("Reopen thread") }},
                    leadingIcon = {{ Icon(Icons.Filled.LockOpen, contentDescription = null) }},
                    onClick = {{
                        expanded = false
                        onReopenThread()
                    }},
                    modifier = Modifier.testTag("reopen-thread-button")
                )
                selectedThread.announcement -> DropdownMenuItem(
                    text = {{ Text("Read-only announcement") }},
                    enabled = false,
                    onClick = {{ }}
                )
                else -> DropdownMenuItem(
                    text = {{ Text("Close thread") }},
                    leadingIcon = {{ Icon(Icons.Filled.Delete, contentDescription = null) }},
                    onClick = {{
                        expanded = false
                        onCloseThread()
                    }},
                    modifier = Modifier.testTag("close-thread-button")
                )
            }}
        }}
    }}
}}

@Composable
private fun ThreadClosedState(onReopenThread: () -> Unit) {{
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 34.dp, bottom = 10.dp)
            .testTag("thread-closed-state"),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {{
        Box(
            Modifier
                .size(78.dp)
                .clip(CircleShape)
                .background(DemoActive),
            contentAlignment = Alignment.Center
        ) {{
            Icon(Icons.Filled.Lock, contentDescription = null, tint = DemoInk, modifier = Modifier.size(40.dp))
        }}
        Text("This thread is closed", color = DemoInk, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(
            "You can no longer send messages\\nin this thread.",
            color = DemoMuted,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
        Button(onClick = onReopenThread, modifier = Modifier.testTag("reopen-thread-button")) {{
            Text("Reopen thread")
        }}
        Box(Modifier.fillMaxWidth().height(1.dp).background(DemoBorder))
    }}
}}

@Composable
private fun ChatDateChip(label: String) {{
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {{
        Text(
            label,
            color = DemoMuted,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier
                .clip(RoundedCornerShape(99.dp))
                .background(DemoElevated)
                .padding(horizontal = 14.dp, vertical = 6.dp)
        )
    }}
}}

@Composable
private fun ChatComposer(
    draft: String,
    enabled: Boolean,
    onDraftChange: (String) -> Unit,
    onAttach: () -> Unit,
    onSend: () -> Unit
) {{
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .background(DemoPaper)
            .imePadding()
            .navigationBarsPadding()
            .padding(horizontal = 14.dp, vertical = 10.dp)
            .testTag("chat-composer"),
        color = DemoPaper,
        tonalElevation = 0.dp
    ) {{
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 58.dp)
                .clip(RoundedCornerShape(28.dp))
                .background(DemoElevated)
                .padding(horizontal = 8.dp, vertical = 6.dp)
                .testTag("composer-input-rail"),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {{
            IconButton(
                enabled = enabled,
                onClick = onAttach,
                modifier = Modifier
                    .size(42.dp)
                    .clip(CircleShape)
                    .background(if (enabled) DemoActive else DemoActive.copy(alpha = 0.55f))
                    .testTag("attachment-button")
            ) {{
                Icon(Icons.Filled.Add, contentDescription = "Add attachment", tint = if (enabled) DemoInk else DemoSubtle)
            }}
            Box(
                Modifier
                    .width(1.dp)
                    .height(28.dp)
                    .background(DemoBorder)
                    .testTag("composer-divider")
            )
            BasicTextField(
                value = draft,
                onValueChange = onDraftChange,
                enabled = enabled,
                singleLine = true,
                cursorBrush = SolidColor(DemoBlue),
                textStyle = MaterialTheme.typography.bodyLarge.copy(color = if (enabled) DemoInk else DemoSubtle),
                modifier = Modifier
                    .weight(1f)
                    .heightIn(min = 40.dp)
                    .testTag("message-input"),
                decorationBox = {{ innerTextField ->
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {{
                        if (draft.isBlank()) {{
                            Text(
                                if (enabled) "Type a message..." else "Replies disabled",
                                color = DemoMuted,
                                style = MaterialTheme.typography.bodyLarge,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }}
                        innerTextField()
                    }}
                }}
            )
            IconButton(
                enabled = enabled && draft.isNotBlank(),
                onClick = onSend,
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(if (enabled && draft.isNotBlank()) DemoBlue else Color.Transparent)
                    .testTag("send-button")
            ) {{
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = if (enabled && draft.isNotBlank()) Color.White else DemoSubtle)
            }}
        }}
    }}
}}

@Composable
private fun MessageBubble(
    message: DemoMessage,
    disabled: Boolean = false,
    onAction: (String, DemoAction) -> Unit,
    onDelete: (String) -> Unit = {{}}
) {{
    val outgoing = message.outgoing
    val displayText = messageDisplayText(message)
    val statusText = outgoingMessageStatus(message)
    val timeText = messageTimeLabel(message.createdAt)
    val kindLabel = messageKindLabel(message.kind)
    val maxBubbleWidth = if (message.kind == DemoMessageKind.GENERIC_TEMPLATE) 342.dp else 300.dp
    val standaloneActions = message.actions.isNotEmpty() &&
        message.kind != DemoMessageKind.GENERIC_TEMPLATE &&
        message.kind != DemoMessageKind.FORM_TEMPLATE
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (outgoing) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Top
    ) {{
        if (!outgoing) {{
            MessageAvatar()
            Spacer(Modifier.width(8.dp))
        }}
        Column(
            modifier = Modifier.widthIn(max = maxBubbleWidth),
            horizontalAlignment = if (outgoing) Alignment.End else Alignment.Start,
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {{
            Surface(
                color = if (outgoing) DemoBlue else DemoElevated,
                shape = messageBubbleShape(outgoing),
                modifier = Modifier.fillMaxWidth()
            ) {{
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {{
                    if (kindLabel.isNotBlank()) {{
                        Text(
                            kindLabel,
                            color = if (outgoing) Color.White.copy(alpha = 0.78f) else DemoBlue,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold
                        )
                    }}
                    if (displayText.isNotBlank()) {{
                        Text(
                            displayText,
                            color = if (outgoing) Color.White else DemoInk,
                            style = MaterialTheme.typography.bodyLarge,
                            maxLines = 8,
                            overflow = TextOverflow.Ellipsis
                        )
                    }}
                    if (message.extras.isNotEmpty()) {{
                        ExtrasPreview(message.extras, outgoing)
                    }}
                    when (message.kind) {{
                        DemoMessageKind.GENERIC_TEMPLATE -> CardCarousel(message, disabled, onAction)
                        DemoMessageKind.FORM_TEMPLATE -> FormMessagePreview(message, disabled, onAction)
                        DemoMessageKind.MEDIA,
                        DemoMessageKind.LOCATION -> message.attachments.forEach {{ attachment -> AttachmentPreview(attachment) }}
                        DemoMessageKind.RECEIPT -> ReceiptPreview(message.status)
                        else -> Unit
                    }}
                }}
            }}
            MessageMetaLine(timeText = timeText, statusText = statusText, outgoing = outgoing)
            if (!outgoing && standaloneActions) {{
                ActionRow(
                    sourceMessageId = message.id,
                    actions = message.actions,
                    disabled = disabled,
                    onAction = onAction,
                    testTag = if (message.kind == DemoMessageKind.QUICK_REPLY) "quick-reply-action" else "message-action"
                )
            }}
            if (disabled && hasInteractiveContent(message)) {{
                Text("Submitted", style = MaterialTheme.typography.labelSmall, color = DemoMuted)
            }}
        }}
    }}
}}

@Composable
private fun MessageAvatar() {{
    Box(
        Modifier
            .size(34.dp)
            .clip(RoundedCornerShape(11.dp))
            .background(Color.White)
            .padding(4.dp)
            .testTag("message-agent-avatar"),
        contentAlignment = Alignment.Center
    ) {{
        WebexBrandMark(Modifier.fillMaxSize())
    }}
}}

private fun messageBubbleShape(outgoing: Boolean): RoundedCornerShape =
    RoundedCornerShape(
        topStart = 22.dp,
        topEnd = 22.dp,
        bottomEnd = if (outgoing) 6.dp else 22.dp,
        bottomStart = if (outgoing) 22.dp else 6.dp
    )

@Composable
private fun MessageMetaLine(timeText: String, statusText: String, outgoing: Boolean) {{
    val metaColor = if (outgoing) DemoBlue else DemoSubtle
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (outgoing) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.CenterVertically
    ) {{
        if (outgoing && statusText.isNotBlank()) {{
            Text(statusText, style = MaterialTheme.typography.labelSmall, color = metaColor, maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (timeText.isNotBlank()) Spacer(Modifier.width(8.dp))
        }}
        if (timeText.isNotBlank()) {{
            Text(timeText, style = MaterialTheme.typography.labelSmall, color = DemoSubtle, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }}
    }}
}}

@Composable
private fun CardCarousel(message: DemoMessage, disabled: Boolean, onAction: (String, DemoAction) -> Unit) {{
    val listState = rememberLazyListState()
    val activeIndex = if (message.cards.isEmpty()) 0 else listState.firstVisibleItemIndex.coerceIn(0, message.cards.lastIndex)
    LazyRow(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("card-carousel"),
        state = listState,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {{
        itemsIndexed(
            message.cards,
            key = {{ index, card -> cardListKey(message, index, card) }}
        ) {{ _, card ->
            RichMessageCard(message.id, card, disabled, onAction)
        }}
    }}
    if (message.cards.size > 1) {{
        Row(
            modifier = Modifier.fillMaxWidth().testTag("card-carousel-position"),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {{
            repeat(message.cards.size.coerceAtMost(5)) {{ index ->
                Box(
                    Modifier
                        .padding(horizontal = 3.dp)
                        .size(if (index == activeIndex) 8.dp else 7.dp)
                        .clip(CircleShape)
                        .background(if (index == activeIndex) DemoBlue else DemoSubtle)
                )
            }}
            Spacer(Modifier.width(10.dp))
            Text((activeIndex + 1).toString() + " of " + message.cards.size.toString(), color = DemoSubtle, style = MaterialTheme.typography.labelMedium)
        }}
    }}
}}

@Composable
private fun RichMessageCard(sourceMessageId: String, card: DemoCard, disabled: Boolean, onAction: (String, DemoAction) -> Unit) {{
    val imageUrls = card.imageUrls.ifEmpty {{ listOfNotNull(card.imageUrl.takeIf {{ it.isNotBlank() }}) }}
    Card(
        colors = CardDefaults.cardColors(containerColor = DemoPaper),
        modifier = Modifier
            .width(244.dp)
            .testTag("template-card")
    ) {{
        Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {{
            if (imageUrls.isNotEmpty()) {{
                RemoteImagePreview(
                    url = imageUrls.first(),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(168.dp)
                        .testTag("card-image-preview")
                        .clip(RoundedCornerShape(14.dp))
                )
                if (imageUrls.size > 1) {{
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {{
                        itemsIndexed(imageUrls.drop(1), key = {{ index, imageUrl -> "card-image-" + index + "-" + imageUrl }}) {{ _, imageUrl ->
                            RemoteImagePreview(
                                url = imageUrl,
                                modifier = Modifier
                                    .size(42.dp)
                                    .clip(RoundedCornerShape(10.dp))
                            )
                        }}
                    }}
                }}
            }} else {{
                Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(132.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(DemoBlue.copy(alpha = 0.18f)),
                    contentAlignment = Alignment.Center
                ) {{
                    Icon(Icons.Filled.ShoppingCart, contentDescription = null, tint = DemoBlue, modifier = Modifier.size(32.dp))
                }}
            }}
            Text(card.title, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 2, overflow = TextOverflow.Ellipsis)
            if (card.subtitle.isNotBlank()) {{
                Text(card.subtitle, color = DemoMuted, maxLines = 3, overflow = TextOverflow.Ellipsis)
            }}
            card.actions.take(3).forEach {{ action ->
                CardActionButton(sourceMessageId, action, disabled, onAction)
            }}
        }}
    }}
}}

@Composable
private fun CardActionButton(sourceMessageId: String, action: DemoAction, disabled: Boolean, onAction: (String, DemoAction) -> Unit) {{
    Button(
        enabled = !disabled,
        onClick = {{ onAction(sourceMessageId, action) }},
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 44.dp)
            .testTag("card-action")
    ) {{
        Text(action.title, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }}
}}

@Composable
private fun ExtrasPreview(extras: Map<String, String>, outgoing: Boolean) {{
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier.testTag("message-extras-preview")
    ) {{
        itemsIndexed(extras.entries.take(4).toList(), key = {{ index, entry -> "extra-" + index + "-" + entry.key }}) {{ _, entry ->
            Text(
                entry.key + ": " + entry.value,
                color = if (outgoing) Color.White.copy(alpha = 0.82f) else DemoMuted,
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier
                    .clip(RoundedCornerShape(99.dp))
                    .background(if (outgoing) Color.White.copy(alpha = 0.14f) else DemoActive)
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }}
    }}
}}

@Composable
private fun FormMessagePreview(message: DemoMessage, disabled: Boolean, onAction: (String, DemoAction) -> Unit) {{
    var values by remember(message.id) {{
        mutableStateOf(message.fields.associate {{ fieldKey(it) to it.value }}.toMutableMap())
    }}
    val requiredComplete = message.fields
        .filter {{ it.required }}
        .all {{ values[fieldKey(it)].orEmpty().isNotBlank() }}

    Card(colors = CardDefaults.cardColors(containerColor = DemoActive), modifier = Modifier.fillMaxWidth()) {{
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {{
            Text("Support form", fontWeight = FontWeight.Bold, color = DemoInk)
            message.fields.forEach {{ field ->
                val key = fieldKey(field)
                val current = values[key].orEmpty()
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {{
                    OutlinedTextField(
                        value = current,
                        onValueChange = {{ next ->
                            values = values.toMutableMap().also {{ it[key] = next }}
                        }},
                        enabled = !disabled,
                        label = {{ Text(field.label + if (field.required) " *" else "") }},
                        placeholder = {{ Text(field.type.ifBlank {{ "Enter value" }}) }},
                        modifier = Modifier.fillMaxWidth().testTag("form-field-input"),
                        colors = demoOutlinedTextFieldColors(),
                        maxLines = 3
                    )
                    if (field.options.isNotEmpty()) {{
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {{
                            itemsIndexed(field.options, key = {{ index, option -> "option-" + key + "-" + index + "-" + option }}) {{ _, option ->
                                FilterChip(
                                    selected = current == option,
                                    enabled = !disabled,
                                    onClick = {{ values = values.toMutableMap().also {{ it[key] = option }} }},
                                    label = {{ Text(option, maxLines = 1, overflow = TextOverflow.Ellipsis) }}
                                )
                            }}
                        }}
                    }}
                }}
            }}
            Button(
                enabled = !disabled && requiredComplete,
                onClick = {{
                    onAction(
                        message.id,
                        DemoAction(
                            id = "form-submit-" + message.id,
                            title = "Submit form",
                            payload = formPayload(values),
                            type = "form-submit"
                        )
                    )
                }},
                modifier = Modifier.testTag("form-submit-button")
            ) {{
                Text(if (disabled) "Submitted" else "Submit form")
            }}
        }}
    }}
}}

@Composable
private fun AttachmentPreview(attachment: DemoAttachment) {{
    Card(colors = CardDefaults.cardColors(containerColor = DemoActive), modifier = Modifier.fillMaxWidth()) {{
        Column(Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {{
            if (attachment.kind == "image" && attachment.url.isNotBlank()) {{
                RemoteImagePreview(
                    url = attachment.url,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(150.dp)
                        .testTag("attachment-image-preview")
                        .clip(RoundedCornerShape(11.dp))
                )
            }}
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {{
                Icon(if (attachment.kind == "location") Icons.Filled.LocalShipping else Icons.Filled.AttachFile, contentDescription = null, tint = DemoBlue)
                Column(Modifier.weight(1f)) {{
                    Text(attachment.label, fontWeight = FontWeight.SemiBold, color = DemoInk)
                    val detail = attachment.metadata.ifBlank {{
                        attachment.url.takeIf {{ it.isNotBlank() }} ?: attachment.kind
                    }}
                    if (detail.isNotBlank()) {{
                        Text(detail, style = MaterialTheme.typography.labelSmall, color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }}
                }}
            }}
        }}
    }}
}}

@Composable
private fun ReceiptPreview(status: String) {{
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {{
        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = DemoMint, modifier = Modifier.size(16.dp))
        Text(status.ifBlank {{ "Message status updated" }}, style = MaterialTheme.typography.labelSmall, color = DemoMuted)
    }}
}}

@Composable
private fun ActionRow(
    sourceMessageId: String,
    actions: List<DemoAction>,
    disabled: Boolean,
    onAction: (String, DemoAction) -> Unit,
    testTag: String
) {{
    if (actions.isEmpty()) return
    LazyRow(
        modifier = Modifier.testTag("dynamic-message-actions"),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {{
        itemsIndexed(
            actions,
            key = {{ index, action -> actionListKey(index, action) }}
        ) {{ _, action ->
            Row(
                modifier = Modifier
                    .heightIn(min = 42.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .border(1.dp, if (disabled) DemoBorder else DemoBlue, RoundedCornerShape(16.dp))
                    .clickable(enabled = !disabled) {{ onAction(sourceMessageId, action) }}
                    .padding(horizontal = 14.dp, vertical = 9.dp)
                    .testTag(testTag),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {{
                Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = null, tint = if (disabled) DemoSubtle else DemoBlue, modifier = Modifier.size(16.dp))
                Text(action.title, color = if (disabled) DemoSubtle else DemoBlue, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }}
        }}
    }}
}}

private fun messageKindLabel(kind: DemoMessageKind): String =
    when (kind) {{
        DemoMessageKind.QUICK_REPLY -> "Quick replies"
        DemoMessageKind.GENERIC_TEMPLATE -> "Cards"
        DemoMessageKind.FORM_TEMPLATE -> "Form"
        DemoMessageKind.MEDIA -> "Attachment"
        DemoMessageKind.LOCATION -> "Location"
        DemoMessageKind.RECEIPT -> "Receipt"
        DemoMessageKind.TYPING -> "Typing"
        DemoMessageKind.THREAD_UPDATE -> "Conversation update"
        DemoMessageKind.DELETED -> "Deleted message"
        DemoMessageKind.ALERT -> ""
        DemoMessageKind.UNKNOWN -> "Webex Connect message"
        DemoMessageKind.TEXT -> ""
    }}

private fun messageDisplayText(message: DemoMessage): String {{
    val text = stripDiagnosticPayload(message.text)
        .replace(Regex("\\\\s+"), " ")
        .trim()
    if (text.isNotBlank()) return if (text.length > 360) text.take(357).trimEnd() + "..." else text
    return when (message.kind) {{
        DemoMessageKind.GENERIC_TEMPLATE -> ""
        DemoMessageKind.FORM_TEMPLATE -> "Complete the support form"
        DemoMessageKind.MEDIA -> "Attachment received"
        DemoMessageKind.LOCATION -> "Location shared"
        DemoMessageKind.RECEIPT -> "Message status updated"
        DemoMessageKind.TYPING -> "Typing..."
        DemoMessageKind.THREAD_UPDATE -> "Conversation updated"
        DemoMessageKind.DELETED -> "Message deleted"
        DemoMessageKind.ALERT -> "Webex Connect alert"
        else -> "Message received"
    }}
}}

private fun stripDiagnosticPayload(value: String): String {{
    var text = value.replace(Regex("\\\\s+"), " ").trim()
    listOf("Webex Connect Demo Chat", "Webex Connect Demo", "APA91").forEach {{ marker ->
        val index = text.indexOf(marker)
        if (index > 0) text = text.take(index).trim()
    }}
    text = text
        .replace(Regex("[A-Za-z0-9_-]{{12,}}:APA[0-9A-Za-z_:-]+"), "")
        .replace(Regex("\\\\d{{10,}}\\\\d{{4}}-\\\\d{{2}}-\\\\d{{2}}T[^\\\\s]+"), " ")
        .trim()
    return text.ifBlank {{ value.take(180).trim() }}
}}

private fun messageListKey(index: Int, message: DemoMessage): String =
    "message-" + index + "-" + message.id + "-" + message.createdAt

private fun cardListKey(message: DemoMessage, index: Int, card: DemoCard): String =
    "card-" + message.id + "-" + index + "-" + card.title + "-" + card.subtitle

private fun actionListKey(index: Int, action: DemoAction): String =
    "action-" + index + "-" + action.id + "-" + action.title

private fun hasInteractiveContent(message: DemoMessage): Boolean =
    message.actions.isNotEmpty() ||
        message.cards.any {{ it.actions.isNotEmpty() }} ||
        message.kind == DemoMessageKind.FORM_TEMPLATE

private fun canDeleteMessage(message: DemoMessage): Boolean =
    message.id.isNotBlank() &&
        !message.id.startsWith("welcome") &&
        message.type != "push" &&
        message.kind != DemoMessageKind.TYPING

private fun outgoingMessageStatus(message: DemoMessage): String {{
    if (!message.outgoing) return ""
    val value = message.status.trim().lowercase()
    return when {{
        value.contains("read") -> "Read"
        value.contains("deliver") -> "Delivered"
        value.contains("sent") -> "Sent"
        value.contains("send") -> "Sending"
        value.contains("fail") -> "Failed"
        else -> message.status.trim()
    }}
}}

private fun fieldKey(field: DemoField): String =
    field.name.ifBlank {{ field.label.ifBlank {{ field.type.ifBlank {{ "field" }} }} }}

private fun formPayload(values: Map<String, String>): String =
    JSONObject().apply {{
        put("type", "form-submit")
        put("fields", JSONObject().apply {{
            values.forEach {{ entry -> put(entry.key, entry.value) }}
        }})
    }}.toString()

@Composable
private fun QaPanel(state: DemoState) {{
    Card(
        colors = CardDefaults.cardColors(containerColor = DemoPaper),
        modifier = Modifier.padding(horizontal = 14.dp).fillMaxWidth().testTag("qa-panel")
    ) {{
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {{
            Text("SDK status", fontWeight = FontWeight.Bold, color = DemoInk)
            Text("SDK version: " + state.sdkVersion.ifBlank {{ "pending" }}, color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("Provider: " + state.provider, color = DemoMuted)
            Text("Started: " + state.sdkStarted.toString(), color = DemoMuted)
            Text("Registered: " + state.registered.toString(), color = DemoMuted)
            Text("Connected: " + state.connected.toString(), color = DemoMuted)
            Text("Store/sync: " + if (state.localStoreReady) state.syncPolicyLabel else "pending", color = DemoMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("Logger: app-managed", color = DemoMuted)
            Text("Security token: app-managed", color = DemoMuted)
            Text("Last status: " + state.lastError.ifBlank {{ "none" }}, color = DemoMuted, maxLines = 2)
        }}
    }}
}}

@Composable
private fun ForegroundNotificationBanner(
    notification: DemoNotification,
    onDismiss: () -> Unit,
    onOpenSupport: () -> Unit,
    modifier: Modifier = Modifier
) {{
    Card(
        colors = CardDefaults.cardColors(containerColor = DemoElevated),
        modifier = modifier
            .padding(14.dp)
            .fillMaxWidth()
            .testTag("foreground-notification-banner")
    ) {{
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {{
            Box(Modifier.size(42.dp).clip(CircleShape).background(DemoActive), contentAlignment = Alignment.Center) {{
                Icon(Icons.Filled.Notifications, contentDescription = null, tint = DemoBlue)
            }}
            Column(Modifier.weight(1f)) {{
                Text(notification.title, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(notification.body, color = DemoMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }}
            TextButton(onClick = onOpenSupport) {{
                Text("Open")
            }}
            IconButton(onClick = onDismiss) {{
                Icon(Icons.Filled.Close, contentDescription = "Dismiss", tint = DemoInk)
            }}
        }}
    }}
}}

@Composable
private fun NotificationCenterSheet(
    notifications: List<DemoNotification>,
    onDismiss: () -> Unit,
    onOpenSupport: () -> Unit,
    modifier: Modifier = Modifier
) {{
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.55f))
            .testTag("notification-center")
    ) {{
        Card(
            colors = CardDefaults.cardColors(containerColor = DemoPaper),
            modifier = modifier
                .padding(16.dp)
                .fillMaxWidth()
        ) {{
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {{
                Row(verticalAlignment = Alignment.CenterVertically) {{
                    Icon(Icons.Filled.Notifications, contentDescription = null, tint = DemoBlue)
                    Spacer(Modifier.width(8.dp))
                    Text("Notifications", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = DemoInk, modifier = Modifier.weight(1f))
                    IconButton(onClick = onDismiss) {{
                        Icon(Icons.Filled.Close, contentDescription = "Close")
                    }}
                }}
                notifications.forEach {{ notification ->
                    NotificationRow(notification, onOpenSupport)
                }}
            }}
        }}
    }}
}}

@Composable
private fun NotificationRow(notification: DemoNotification, onOpenSupport: () -> Unit) {{
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(if (notification.unread) DemoActive else DemoElevated)
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {{
        Box(Modifier.size(42.dp).clip(CircleShape).background(DemoBlue.copy(alpha = 0.12f)), contentAlignment = Alignment.Center) {{
            Icon(if (notification.unread) Icons.Filled.Notifications else Icons.Filled.CheckCircle, contentDescription = null, tint = DemoBlue)
        }}
        Column(Modifier.weight(1f)) {{
            Text(notification.title, fontWeight = FontWeight.Bold, color = DemoInk)
            Text(notification.body, color = DemoMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(notification.category + " - " + notification.timeLabel, style = MaterialTheme.typography.labelSmall, color = DemoMuted)
        }}
        TextButton(onClick = onOpenSupport) {{
            Text("Open")
        }}
    }}
}}

@Composable
private fun SectionTitle(title: String, subtitle: String) {{
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {{
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = DemoInk, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = DemoMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
    }}
}}
""",
        f"app/src/androidTest/java/{pkg_path}/WebexConnectDemoSmokeTest.kt": f"""package {args.package}

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import org.junit.Rule
import org.junit.Test

class WebexConnectDemoSmokeTest {{
    @get:Rule
    val compose = createAndroidComposeRule<MainActivity>()

    @Test
    fun loginScreenIsVisible() {{
        compose.onNodeWithTag("user-id-input").assertIsDisplayed()
        compose.onNodeWithTag("login-button").assertIsDisplayed()
    }}
}}
""",
        "BUILD_APK.md": f"""# Webex Connect Demo Build

Selected capability: `{capability_label(args)}`
Selected provider: `{args.provider.upper() if includes_push(args) else "not required"}`
Package name: `{args.package}`
Selected build type: `{args.build_type}`
SDK version: `{version}`
Provider Gradle service plugin: {provider_plugin_status(args)}

Prerequisite: add a Gradle wrapper to this generated project with a trusted
local Gradle installation, or install Gradle so `gradle` is available on PATH.
The generator does not vendor Gradle wrapper binaries.

Build command:

```bash
{build_command(args.build_type)}
# or, when no Gradle wrapper is present:
{installed_gradle_command(args.build_type)}
```

Release builds require a signing configuration before distribution.
User ID is intentionally entered in the running app, not at build time.
""",
        "QA_CHECKLIST.md": f"""# Webex Connect Demo QA Checklist

- Build: `{build_command(args.build_type)}` when a wrapper exists, or
  `{installed_gradle_command(args.build_type)}` when Gradle is installed
- Unit tests: `./gradlew testDebugUnitTest` or `gradle testDebugUnitTest`
- Android test: `./gradlew connectedDebugAndroidTest` or
  `gradle connectedDebugAndroidTest`
- Verify app label: Webex Connect Demo
- Verify selected capability: `{capability_label(args)}`
- Verify selected provider: `{args.provider.upper() if includes_push(args) else "not required"}`
- Verify package name: `{args.package}`
- Verify home screen shows product/service content, support entry, and bottom navigation
- Verify orders screen shows order status cards and support handoff
- Verify notification icon opens the notification center
- Verify support screen shows a clean conversation inbox and dedicated rich agent chat
- Verify profile/settings screen contains Customer ID, App ID, SDK version,
  started/registered/connected state, separate copyable push token, editable
  local store/sync limits, QA diagnostics, and switch-user
- Verify profile SDK status does not include selected thread ID, selected
  thread state, unread count, media transfer state, or inline push token
- Verify the support screen thread list can refresh existing threads, open a
  selected thread, and create a new thread
- Verify the thread list looks like a modern chat inbox with search/filter,
  avatars, presence dots, previews, updated time, unread count, and status badges
- Verify inbox, chat, modal, chips, cards, and empty states use one Webex
  blue/teal Material color scheme with no default purple surfaces
- Verify tapping a thread row opens a dedicated thread chat screen with back
  navigation, message list, quick actions, and rounded composer
- Verify the chat thread title is visible below the device status/cutout area
- Verify the chat header uses the opened/closed thread reference: back button,
  Webex logo, Webex Connect Demo title, and dot status line only
- Verify no metadata pill row, redundant thread-header notification bell, or
  separate selected-thread status card appears above the message list
- Verify the three-dot menu contains View details, Search in conversation, and
  Close/Reopen thread
- Verify closed threads show the centered lock recovery state, preserve
  history, and hide quick actions/composer until reopened
- Verify the new conversation title input appears in a modal only after tapping
  the plus icon near the Conversations header, then Create calls the SDK thread
  flow
- Verify load older threads and load older messages controls page older SDK data
- Verify local message store and editable sync policy are configured before
  connection, defaulting to 50 threads and 50 messages per thread
- Verify message delete removes the row only after SDK callback succeeds
- Verify short outgoing messages render as compact chat bubbles, not large
  full-width blocks
- Verify the paperclip opens the Android document picker, selected files upload
  through the SDK mediaFileManager, and the returned attachment publishes
- Verify selected-file media upload publishes a file attachment, media download
  caches remote media, and media URL refresh updates attachment metadata from
  the thread attachment flow
- Verify card/carousel image URLs and image attachments render as inline images,
  not placeholder media labels
- Verify send, quick reply, and attachment actions clear input focus so the
  keyboard toolbar does not cover the chat header and no extra bottom gap remains
- Verify foreground push notification banner appears from SDK callback and
  notification actions update status
- Verify Customer ID update/remove works and Switch user unregisters then
  returns to login
- Verify closed threads keep history visible but disable composer,
  attachments, quick replies, card actions, and form submit until reopened
- Verify announcement threads are visible and read-only
- Add sanitized `WebexConnectConfig.properties` in `app/src/main/assets/`
- Add provider config: `{provider_file_status(args)}`
- Login with a test User ID
- Confirm registration, copyable push token, notification permission,
  connection, thread ID, thread status, and unread count in their relevant
  screens
- Send one in-app message and verify it appears once while status changes from `sending` to `sent`
- Verify SDK listener echoes, delivery/read receipts, and history reloads reconcile by transaction ID/fingerprint instead of creating duplicate bubbles
- Receive several in-app messages, leave and re-enter the thread, and verify realtime display plus delayed history reconciliation preserve oldest-to-newest order with the newest message at the bottom
- Receive an in-app message and verify current-user messages align right while agent/platform messages align left
- Verify active-thread inbound messages render in the open chat and
  other-thread inbound messages update the inbox preview/unread state
- Restart app and fetch message history
- Trigger push and verify notification channel/action handling
- Search generated project for non-Webex sample/vendor names before sharing
""",
    }
    files.update(connect_config_files(args))
    files[f"app/src/main/java/{pkg_path}/WebexConnectSdkController.kt"] = webex_connect_sdk_controller_file(args)
    files[f"app/src/main/java/{pkg_path}/MessageRenderer.kt"] = message_renderer_file(args)
    files[f"app/src/main/java/{pkg_path}/NotificationSupport.kt"] = notification_support_file(args)
    return files


def webex_connect_sdk_controller_file(args: argparse.Namespace) -> str:
    imports = [
        "import android.content.Context",
        "import android.net.Uri",
        "import android.os.Handler",
        "import android.os.Looper",
        "import androidx.compose.runtime.mutableStateOf",
        "import com.webex.connect.core.errorhandling.WebexConnectException",
        "import com.webex.connect.core.WebexConnect",
        "import com.webex.connect.core.profile.DeviceProfile",
        "import com.webex.connect.core.profile.DeviceProfileParam",
        "import java.util.UUID",
    ]
    if includes_inapp(args):
        imports.extend([
            "import com.webex.connect.inapp.ConnectionStatus",
            "import com.webex.connect.inapp.InAppMessaging",
            "import com.webex.connect.inapp.media.FileDownloadCallback",
            "import com.webex.connect.inapp.media.FileUploadCallback",
            "import com.webex.connect.inapp.message.InAppButton",
            "import com.webex.connect.inapp.message.InAppMessage",
            "import com.webex.connect.inapp.message.InAppMessageStatus",
            "import com.webex.connect.inapp.message.InAppThread",
            "import com.webex.connect.inapp.message.InAppThreadStatus",
            "import com.webex.connect.inapp.message.InAppThreadType",
            "import com.webex.connect.inapp.message.attachments.InAppAttachment",
            "import com.webex.connect.inapp.message.attachments.media.InAppFileAttachment",
            "import com.webex.connect.inapp.message.db.DefaultMessageStore",
            "import com.webex.connect.inapp.synchronization.MessageSynchronizationMode",
            "import com.webex.connect.inapp.synchronization.MessageSynchronizationPolicy",
            "import android.provider.OpenableColumns",
            "import org.json.JSONObject",
            "import java.io.File",
            "import java.util.Date",
            "import java.net.URL",
        ])
    if includes_push(args):
        imports.extend([
            "import com.webex.connect.push.PushMessaging",
            "import com.webex.connect.push.message.PushMessage",
        ])

    sdk_fields = ""
    if includes_push(args):
        sdk_fields += """
    private val pushTokenListener: (String) -> Unit = { token ->
        state.value = state.value.copy(pushToken = token)
    }
    private val pushMessagingListener: (PushMessage) -> Unit = { pushMessage ->
        val rendered = MessageRenderer.fromPushMessage(pushMessage)
        upsertMessage(rendered)
        addNotification("New Webex Connect message", customerPreviewText(rendered), "Push")
    }
"""
    if includes_inapp(args):
        sdk_fields += """
    private var activeThread: InAppThread? = null
    private var lastRecoverySyncAt = 0L
    private val pendingOutgoingIds = mutableSetOf<String>()
    private val pendingOutgoingFingerprints = mutableSetOf<String>()
    private val pendingReceiptStatuses = mutableMapOf<String, String>()
    private val mainHandler = Handler(Looper.getMainLooper())
    private val pendingMessageRefreshes = mutableMapOf<String, Runnable>()
    private val connectionStatusListener: (ConnectionStatus) -> Unit = { status ->
        val connected = InAppMessaging.instance.isConnected
        state.value = state.value.copy(connected = connected, lastError = status.toString())
        if (connected && messagingStarted) {
            syncAfterConnectionRestored(openDefaultWhenEmpty = true)
        }
    }
    private val inAppMessagingListener: (InAppMessage) -> Unit = inAppListener@ { message ->
        val rendered = MessageRenderer.fromInAppMessage(message, currentActiveThreadId(), state.value.userId)
        if (applyStatusReceipt(rendered)) {
            fetchUnreadCount()
            return@inAppListener
        }
        if (shouldSuppressOutgoingEcho(rendered)) {
            return@inAppListener
        }
        val visibleInActiveThread = shouldDisplayInActiveThread(rendered)
        acknowledgeIncomingMessage(message, rendered, markRead = visibleInActiveThread)
        if (!visibleInActiveThread) {
            recordInactiveThreadMessage(rendered)
            syncThreadMetadata(rendered.threadId)
            fetchUnreadCount()
            return@inAppListener
        }
        upsertMessage(rendered)
        if (rendered.kind == DemoMessageKind.THREAD_UPDATE || rendered.kind == DemoMessageKind.DELETED) {
            syncThreadMetadata(rendered.threadId)
        }
        scheduleThreadMessageRefresh(rendered.threadId)
        fetchUnreadCount()
    }
"""

    push_request = """
        PushMessaging.instance.requestNotificationPermission { granted ->
            state.value = state.value.copy(lastError = "Notification permission: ${granted}")
        }
"""
    if not includes_push(args):
        push_request = """
        updateError("Push messaging is not included in this build")
"""

    push_start = ""
    if includes_push(args):
        push_start = """
        NotificationSupport.configurePushPresentation(
            context = context,
            onForegroundNotification = { notification ->
                addForegroundNotification(notification.title, notification.body, notification.category)
            },
            onStatus = ::updateError
        )
        PushMessaging.instance.registerPushTokenListener(pushTokenListener)
        PushMessaging.instance.registerMessagingListener(pushMessagingListener)
"""

    inapp_start = ""
    inapp_methods = push_only_inapp_stubs()
    release_body = ""
    inapp_helpers = ""
    if includes_inapp(args):
        inapp_start = """
        InAppMessaging.instance.registerConnectionStatusListener(connectionStatusListener)
        InAppMessaging.instance.registerMessagingListener(inAppMessagingListener)

        try {
            configureLocalStoreAndSync()
            InAppMessaging.instance.connect()
            syncAfterConnectionRestored(openDefaultWhenEmpty = true)
        } catch (exception: Exception) {
            updateError(exception.message ?: "In-app connection failed")
        }
"""
        inapp_methods = inapp_controller_methods()
        inapp_helpers = inapp_controller_helpers()

    release_blocks = []
    if includes_push(args):
        release_blocks.append("""
        try {
            PushMessaging.instance.unregisterPushTokenListener(pushTokenListener)
            PushMessaging.instance.unregisterMessagingListener(pushMessagingListener)
        } catch (_: Exception) {
        }
""")
    if includes_inapp(args):
        release_blocks.append("""
        try {
            InAppMessaging.instance.unregisterConnectionStatusListener(connectionStatusListener)
            InAppMessaging.instance.unregisterMessagingListener(inAppMessagingListener)
            InAppMessaging.instance.disconnect()
        } catch (_: Exception) {
        }
""")
    if release_blocks:
        release_blocks.append("""
        messagingStarted = false
""")
    release_body = "".join(release_blocks)

    template = """package __PACKAGE__

__IMPORTS__

class WebexConnectSdkController(
    private val context: Context,
    private val providerName: String
) {
    val state = mutableStateOf(
        DemoState(
            provider = providerName,
            appId = ConfigGuard.webexConnectAppId(context),
            sdkStarted = WebexConnect.instance.isStarted,
            sdkVersion = WebexConnect.instance.sdkVersion,
            registered = WebexConnect.instance.isRegistered
        )
    )
    private val preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private var messagingStarted = false
__SDK_FIELDS__
    init {
        restoreRegisteredSession()
    }

    private fun restoreRegisteredSession() {
        if (!ConfigGuard.hasWebexConnectConfig(context)) return
        if (WebexConnect.instance.isRegistered) {
            val restoredUserId = preferences.getString(KEY_USER_ID, "").orEmpty().ifBlank { "registered-user" }
            ensureSdkStarted {
                state.value = state.value.copy(
                    userId = restoredUserId,
                    sdkStarted = WebexConnect.instance.isStarted,
                    sdkVersion = WebexConnect.instance.sdkVersion,
                    registered = true,
                    lastError = "Restored registered session"
                )
                startMessaging()
            }
        }
    }

    fun login(userId: String) {
        val cleanUserId = userId.trim()
        if (cleanUserId.isEmpty()) {
            updateError("Enter a User ID")
            return
        }
        if (!ConfigGuard.hasWebexConnectConfig(context)) {
            updateError("Add WebexConnectConfig.properties under app/src/main/assets/")
            return
        }

        ensureSdkStarted {
            registerDevice(cleanUserId)
        }
    }

    private fun ensureSdkStarted(onReady: () -> Unit) {
        if (WebexConnect.instance.isStarted) {
            refreshGlobalSdkStatus()
            onReady()
            return
        }
        WebexConnect.instance.startup { exception ->
            refreshGlobalSdkStatus()
            if (exception == null && WebexConnect.instance.isStarted) {
                onReady()
            } else {
                updateError(exception?.message ?: "Webex Connect startup failed")
            }
        }
    }

    private fun registerDevice(cleanUserId: String) {
        val profile = DeviceProfile(DeviceProfile.defaultDeviceId, cleanUserId)
        if (WebexConnect.instance.isRegistered) {
            preferences.edit().putString(KEY_USER_ID, cleanUserId).apply()
            state.value = state.value.copy(
                userId = cleanUserId,
                sdkStarted = WebexConnect.instance.isStarted,
                sdkVersion = WebexConnect.instance.sdkVersion,
                registered = true,
                lastError = ""
            )
            startMessaging()
            return
        }

        WebexConnect.instance.register(profile) { _, exception ->
            if (exception == null) {
                preferences.edit().putString(KEY_USER_ID, cleanUserId).apply()
                state.value = state.value.copy(
                    userId = cleanUserId,
                    sdkStarted = WebexConnect.instance.isStarted,
                    sdkVersion = WebexConnect.instance.sdkVersion,
                    registered = true,
                    lastError = ""
                )
                startMessaging()
            } else {
                updateError(exception.message ?: "Registration failed")
            }
        }
    }

    fun requestNotifications() {
__PUSH_REQUEST__
    }

    fun updateProfileCustomerId(customerId: String) {
        val cleanCustomerId = customerId.trim()
        if (cleanCustomerId.isBlank()) {
            WebexConnect.instance.removeProfileParam(DeviceProfileParam.CUSTOMER_ID) { _, exception ->
                if (exception == null) {
                    state.value = state.value.copy(customerId = "", lastError = "Customer ID removed")
                } else {
                    updateError(exception.message ?: "Profile update failed")
                }
            }
            return
        }

        WebexConnect.instance.updateProfileParam(DeviceProfileParam.CUSTOMER_ID, cleanCustomerId) { _, exception ->
            if (exception == null) {
                state.value = state.value.copy(customerId = cleanCustomerId, lastError = "Customer ID updated")
            } else {
                updateError(exception.message ?: "Profile update failed")
            }
        }
    }

    fun signOut() {
        release()
        WebexConnect.instance.unregister { _, exception ->
            if (exception == null) {
                preferences.edit().clear().apply()
                messagingStarted = false
                resetInAppSessionState()
                state.value = DemoState(
                    provider = providerName,
                    appId = ConfigGuard.webexConnectAppId(context),
                    sdkStarted = WebexConnect.instance.isStarted,
                    sdkVersion = WebexConnect.instance.sdkVersion,
                    registered = WebexConnect.instance.isRegistered,
                    lastError = "Signed out"
                )
            } else {
                updateError(exception.message ?: "Sign out failed")
            }
        }
    }

    fun dismissForegroundNotification() {
        state.value = state.value.copy(foregroundNotification = null)
    }

    private fun startMessaging() {
        if (messagingStarted) return
        messagingStarted = true
__PUSH_START____INAPP_START__
    }

__INAPP_METHODS__
    fun release() {
__RELEASE_BODY__
    }

    private fun upsertMessage(message: DemoMessage) {
        val snapshot = state.value
        val current = snapshot.messages
        val index = current.indexOfFirst { it.id == message.id }
        val next = if (index >= 0) {
            current.toMutableList().also { it[index] = message }
        } else {
            current + message
        }
        state.value = snapshot.copy(
            messages = orderedMessages(next),
            threads = updateThreadsFromMessage(snapshot.threads, message),
            loadingMessages = false
        )
    }

    private fun updateThreadsFromMessage(threads: List<DemoThread>, message: DemoMessage): List<DemoThread> {
        val messageThreadId = message.threadId.trim()
        if (messageThreadId.isBlank()) return threads
        val activeId = state.value.selectedThreadId.ifBlank { state.value.threadId }
        val isActiveThread = activeId == messageThreadId
        val updatedAt = if (message.createdAt > 0L) message.createdAt else System.currentTimeMillis()
        val preview = customerPreviewText(message).take(96)
        var matched = false
        val updatedThreads = threads.map { thread ->
            if (thread.id == messageThreadId) {
                matched = true
                val nextUnread = when {
                    isActiveThread -> 0
                    message.outgoing -> thread.unreadCount
                    else -> thread.unreadCount + 1
                }
                thread.copy(
                    unreadCount = nextUnread,
                    updatedAt = maxOf(thread.updatedAt, updatedAt),
                    lastMessage = preview
                )
            } else {
                thread
            }
        }
        val withFallback = if (matched) {
            updatedThreads
        } else {
            listOf(
                DemoThread(
                    id = messageThreadId,
                    title = "Support conversation",
                    unreadCount = if (!message.outgoing && !isActiveThread) 1 else 0,
                    updatedAt = updatedAt,
                    lastMessage = preview
                )
            ) + updatedThreads
        }
        return withFallback.sortedWith(compareByDescending<DemoThread> { it.updatedAt }.thenBy { it.title.lowercase() })
    }

    private fun recordInactiveThreadMessage(message: DemoMessage) {
        val snapshot = state.value
        state.value = snapshot.copy(
            threads = updateThreadsFromMessage(snapshot.threads, message),
            lastError = "Received message in another conversation"
        )
        addNotification(
            title = "New Webex Connect message",
            body = customerPreviewText(message).ifBlank { "Open the conversation to view the latest message." }.take(120),
            category = "In-App"
        )
    }

__INAPP_HELPERS__
    private fun addNotification(title: String, body: String, category: String) {
        val notification = DemoNotification(
            id = UUID.randomUUID().toString(),
            title = title,
            body = body,
            timeLabel = "Now",
            category = category
        )
        state.value = state.value.copy(notifications = listOf(notification) + state.value.notifications)
    }

    private fun addForegroundNotification(title: String, body: String, category: String) {
        val notification = DemoNotification(
            id = UUID.randomUUID().toString(),
            title = title,
            body = body,
            timeLabel = "Now",
            category = category
        )
        state.value = state.value.copy(
            foregroundNotification = notification,
            notifications = listOf(notification) + state.value.notifications
        )
    }

    private fun updateError(message: String) {
        state.value = state.value.copy(
            sdkStarted = WebexConnect.instance.isStarted,
            sdkVersion = WebexConnect.instance.sdkVersion,
            registered = WebexConnect.instance.isRegistered,
            lastError = message
        )
    }

    private fun refreshGlobalSdkStatus() {
        state.value = state.value.copy(
            sdkStarted = WebexConnect.instance.isStarted,
            sdkVersion = WebexConnect.instance.sdkVersion,
            registered = WebexConnect.instance.isRegistered
        )
    }

    private fun customerPreviewText(message: DemoMessage): String {
        val cleanText = customerVisibleText(message.text)
        if (cleanText.isNotBlank()) return cleanText
        return when (message.kind) {
            DemoMessageKind.QUICK_REPLY -> "Quick replies"
            DemoMessageKind.GENERIC_TEMPLATE -> "Card options"
            DemoMessageKind.FORM_TEMPLATE -> "Form request"
            DemoMessageKind.MEDIA -> "Attachment"
            DemoMessageKind.LOCATION -> "Location"
            DemoMessageKind.RECEIPT -> "Message status"
            DemoMessageKind.TYPING -> "Typing"
            DemoMessageKind.THREAD_UPDATE -> "Conversation updated"
            DemoMessageKind.DELETED -> "Message deleted"
            DemoMessageKind.ALERT -> "Webex Connect alert"
            else -> "Webex Connect message"
        }
    }

    private fun customerVisibleText(value: String): String {
        var text = value.replace(Regex("\\\\s+"), " ").trim()
        listOf("Webex Connect Demo Chat", "Webex Connect Demo", "APA91").forEach { marker ->
            val index = text.indexOf(marker)
            if (index > 0) text = text.take(index).trim()
        }
        text = text
            .replace(Regex("[A-Za-z0-9_-]{12,}:APA[0-9A-Za-z_:-]+"), "")
            .replace(Regex("\\\\d{10,}\\\\d{4}-\\\\d{2}-\\\\d{2}T[^\\\\s]+"), " ")
            .trim()
        return text
    }

    companion object {
        private const val PREFS_NAME = "webex_connect_demo"
        private const val KEY_USER_ID = "user_id"
    }
}
"""
    return (
        template
        .replace("__PACKAGE__", args.package)
        .replace("__IMPORTS__", "\n".join(sorted(imports)))
        .replace("__SDK_FIELDS__", sdk_fields)
        .replace("__PUSH_REQUEST__", push_request.rstrip())
        .replace("__PUSH_START__", push_start)
        .replace("__INAPP_START__", inapp_start)
        .replace("__INAPP_METHODS__", inapp_methods)
        .replace("__RELEASE_BODY__", release_body.rstrip())
        .replace("__INAPP_HELPERS__", inapp_helpers)
    )


def push_only_inapp_stubs() -> str:
    return """
    fun sendMessage(text: String) {
        if (text.trim().isNotEmpty()) {
            updateError("In-App messaging is not included in this build")
        }
    }

    fun sendPostback(sourceMessageId: String, action: DemoAction) {
        updateError("In-App messaging is not included in this build")
    }

    fun fetchMessages() {
        updateError("In-App messaging is not included in this build")
    }

    fun loadOlderMessages() {
        updateError("In-App messaging is not included in this build")
    }

    fun refreshThreads() {
        updateError("In-App messaging is not included in this build")
    }

    fun loadMoreThreads() {
        updateError("In-App messaging is not included in this build")
    }

    fun fetchThreads(openDefaultWhenEmpty: Boolean = false) {
        updateError("In-App messaging is not included in this build")
    }

    fun createNewThread(title: String = "", category: String = "demo") {
        updateError("In-App messaging is not included in this build")
    }

    fun openThread(threadId: String) {
        updateError("In-App messaging is not included in this build")
    }

    fun reopenThread() {
        updateError("In-App messaging is not included in this build")
    }

    fun closeThread() {
        updateError("In-App messaging is not included in this build")
    }

    fun deleteMessage(messageId: String) {
        updateError("In-App messaging is not included in this build")
    }

    fun uploadSampleMedia() {
        updateError("In-App messaging is not included in this build")
    }

    fun uploadSelectedMedia(uri: Uri) {
        updateError("In-App messaging is not included in this build")
    }

    fun downloadFirstMediaAttachment() {
        updateError("In-App messaging is not included in this build")
    }

    fun regenerateFirstMediaUrl() {
        updateError("In-App messaging is not included in this build")
    }

    fun configureLocalStoreAndSync(
        maxThreads: Int = state.value.syncMaxThreads,
        maxMessagesPerThread: Int = state.value.syncMaxMessagesPerThread
    ) {
        state.value = state.value.copy(
            syncMaxThreads = maxThreads.coerceIn(1, 500),
            syncMaxMessagesPerThread = maxMessagesPerThread.coerceIn(1, 500),
            syncPolicyLabel = "In-App messaging is not included"
        )
    }

    fun sendTyping(isTyping: Boolean) {
    }

    fun fetchUnreadCount() {
        state.value = state.value.copy(unreadCount = 0)
    }

    private fun resetInAppSessionState() {
    }
"""


def inapp_controller_methods() -> str:
    return """
    fun configureLocalStoreAndSync(
        maxThreads: Int = state.value.syncMaxThreads,
        maxMessagesPerThread: Int = state.value.syncMaxMessagesPerThread
    ) {
        val threadLimit = maxThreads.coerceIn(1, 500)
        val messageLimit = maxMessagesPerThread.coerceIn(1, 500)
        val storeName = "webex_connect_demo_" + providerName.lowercase().replace(" ", "_")
        val store = DefaultMessageStore.create(context, storeName)
        InAppMessaging.instance.messageStore = store
        val policy = MessageSynchronizationPolicy(MessageSynchronizationMode.LIMITED, threadLimit, messageLimit)
        InAppMessaging.instance.messageSynchronizationPolicy = policy
        state.value = state.value.copy(
            localStoreReady = true,
            syncMaxThreads = threadLimit,
            syncMaxMessagesPerThread = messageLimit,
            syncPolicyLabel = policy.messageSynchronizationMode.value + " / " + policy.maxThreads + " threads / " + policy.maxMessagesPerThread + " messages",
            lastError = "Local message store and sync policy configured"
        )
    }

    fun refreshThreads() {
        fetchThreads(beforeDate = Date(), openDefaultWhenEmpty = false, append = false)
    }

    fun loadMoreThreads() {
        if (!state.value.hasMoreThreads || state.value.loadingMoreThreads) return
        val oldestUpdatedAt = state.value.threads
            .filter { it.updatedAt > 0L }
            .minOfOrNull { it.updatedAt } ?: System.currentTimeMillis()
        val beforeDate = Date((oldestUpdatedAt - 1L).coerceAtLeast(0L))
        fetchThreads(beforeDate = beforeDate, openDefaultWhenEmpty = false, append = true)
    }

    fun fetchThreads(openDefaultWhenEmpty: Boolean = false) {
        fetchThreads(beforeDate = Date(), openDefaultWhenEmpty = openDefaultWhenEmpty, append = false)
    }

    private fun fetchThreads(beforeDate: Date, openDefaultWhenEmpty: Boolean, append: Boolean) {
        if (append) {
            state.value = state.value.copy(loadingMoreThreads = true)
        }
        InAppMessaging.instance.fetchThreads(beforeDate, 50, { threads, hasMore, exception ->
            if (exception == null) {
                val incomingThreads = threads.map(::toDemoThread)
                val previousThreads = state.value.threads
                val demoThreads = if (append || previousThreads.isNotEmpty()) {
                    mergeThreads(previousThreads, incomingThreads)
                } else {
                    incomingThreads
                }
                val currentSelected = state.value.selectedThreadId
                val selected = demoThreads.firstOrNull { it.id == currentSelected } ?: demoThreads.firstOrNull()
                state.value = state.value.copy(
                    threads = demoThreads,
                    hasMoreThreads = hasMore == true,
                    loadingMoreThreads = false,
                    threadId = selected?.id.orEmpty(),
                    selectedThreadId = selected?.id.orEmpty(),
                    lastError = ""
                )

                when {
                    selected != null -> {
                        val sdkThread = threads.firstOrNull { it.id == selected.id }
                        if (sdkThread != null) {
                            activateThread(sdkThread, resetMessages = currentSelected != selected.id)
                            fetchMessages()
                        } else {
                            openThread(selected.id)
                        }
                    }
                    openDefaultWhenEmpty -> createNewThread("Webex Connect Demo Chat", "demo")
                }
            } else {
                state.value = state.value.copy(loadingMoreThreads = false)
                updateError(exception?.message ?: "Fetch threads failed")
            }
        }, null, null)
    }

    fun createNewThread(title: String = "", category: String = "demo") {
        if (state.value.creatingThread) return
        val cleanTitle = title.trim().ifBlank { "Support conversation" }
        val thread = InAppThread().apply {
            this.title = cleanTitle
            this.category = category.trim().ifBlank { "demo" }
            this.status = InAppThreadStatus.ACTIVE
        }
        state.value = state.value.copy(creatingThread = true, lastError = "")
        InAppMessaging.instance.createThread(thread) { created, exception ->
            state.value = state.value.copy(creatingThread = false)
            if (exception == null && created != null) {
                val demoThread = toDemoThread(created)
                state.value = state.value.copy(
                    threads = upsertThread(state.value.threads, demoThread),
                    threadId = demoThread.id,
                    selectedThreadId = demoThread.id,
                    messages = emptyList(),
                    disabledInteractionIds = emptySet(),
                    hasMoreMessages = false,
                    loadingMessages = true,
                    loadingMoreMessages = false
                )
                activateThread(created, resetMessages = true)
                fetchThreads(openDefaultWhenEmpty = false)
                fetchMessages()
            } else {
                updateError(exception?.message ?: "Thread creation failed")
            }
        }
    }

    fun openThread(threadId: String) {
        val cleanThreadId = threadId.trim()
        if (cleanThreadId.isBlank()) return
        val existingThread = state.value.threads.firstOrNull { it.id == cleanThreadId }
        if (existingThread != null && state.value.selectedThreadId != cleanThreadId) {
            state.value = state.value.copy(
                threadId = cleanThreadId,
                selectedThreadId = cleanThreadId,
                messages = emptyList(),
                disabledInteractionIds = emptySet(),
                hasMoreMessages = false,
                loadingMessages = true,
                loadingMoreMessages = false
            )
        }
        InAppMessaging.instance.fetchThread(cleanThreadId) { thread, exception ->
            if (exception == null && thread != null) {
                activateThread(thread, resetMessages = state.value.selectedThreadId != cleanThreadId)
                fetchMessages()
                fetchUnreadCount()
            } else {
                updateError(exception?.message ?: "Fetch thread failed")
            }
        }
    }

    fun reopenThread() {
        updateActiveThreadStatus(InAppThreadStatus.ACTIVE, "Reopened from Webex Connect Demo")
    }

    fun closeThread() {
        updateActiveThreadStatus(InAppThreadStatus.CLOSED, "Closed from Webex Connect Demo")
    }

    fun sendMessage(text: String) {
        val thread = activeThread ?: return updateError("Thread is not ready")
        val cleanText = text.trim()
        if (cleanText.isEmpty()) return
        if (!canReplyToActiveThread()) return updateError(replyBlockedReason())

        val message = InAppMessage().apply {
            this.message = cleanText
            this.thread = thread
        }
        publishOutgoing(message, cleanText)
    }

    fun sendPostback(sourceMessageId: String, action: DemoAction) {
        val thread = activeThread ?: return updateError("Thread is not ready")
        val title = action.title.trim()
        if (title.isEmpty()) return
        if (!canReplyToActiveThread()) return updateError(replyBlockedReason())

        val baseMessage = InAppMessage().apply {
            this.message = title
            this.thread = thread
        }
        val button = InAppButton.fromJson(JSONObject().apply {
            put("id", action.id)
            put("title", title)
            if (action.type.isNotBlank()) put("type", action.type)
            put("payload", JSONObject().apply {
                put("value", action.payload)
            })
        })
        publishOutgoing(InAppMessaging.instance.createPostbackMessage(baseMessage, button), title, sourceMessageId)
    }

    private fun publishOutgoing(message: InAppMessage, cleanText: String, sourceMessageId: String = "") {
        val draft = DemoMessage(
            id = UUID.randomUUID().toString(),
            text = cleanText,
            outgoing = true,
            status = "sending",
            threadId = activeThread?.id.orEmpty().ifBlank { state.value.threadId },
            createdAt = System.currentTimeMillis()
        )
        val fingerprint = messageFingerprint(cleanText)
        if (fingerprint.isNotBlank()) {
            pendingOutgoingFingerprints.add(fingerprint)
        }
        upsertMessage(draft)
        InAppMessaging.instance.publishMessage(message) { published, exception ->
            if (exception == null) {
                val id = published?.transactionId ?: draft.id
                if (id != draft.id) {
                    pendingOutgoingIds.add(id)
                    pendingOutgoingFingerprints.remove(fingerprint)
                }
                val receiptStatus = pendingReceiptStatuses.remove(id).orEmpty()
                replaceMessage(draft.id, draft.copy(id = id, status = preferredDeliveryStatus("sent", receiptStatus)))
                disableInteraction(sourceMessageId)
                scheduleThreadMessageRefresh(draft.threadId)
            } else {
                pendingOutgoingFingerprints.remove(fingerprint)
                replaceMessage(draft.id, draft.copy(status = "failed"))
                updateError(exception.message ?: "Publish failed")
            }
        }
    }

    private fun disableInteraction(sourceMessageId: String) {
        if (sourceMessageId.isBlank()) return
        state.value = state.value.copy(
            disabledInteractionIds = state.value.disabledInteractionIds + sourceMessageId
        )
    }

    fun fetchMessages() {
        fetchMessages(beforeDate = Date(), appendOlder = false)
    }

    fun loadOlderMessages() {
        if (!state.value.hasMoreMessages || state.value.loadingMoreMessages) return
        val oldestCreatedAt = state.value.messages
            .filter { it.createdAt > 0L }
            .minOfOrNull { it.createdAt } ?: System.currentTimeMillis()
        val beforeDate = Date((oldestCreatedAt - 1L).coerceAtLeast(0L))
        fetchMessages(beforeDate = beforeDate, appendOlder = true)
    }

    private fun fetchMessages(beforeDate: Date, appendOlder: Boolean) {
        val threadId = state.value.threadId
        if (threadId.isBlank()) {
            state.value = state.value.copy(loadingMessages = false, loadingMoreMessages = false)
            return
        }
        if (appendOlder) {
            state.value = state.value.copy(loadingMoreMessages = true)
        } else {
            state.value = state.value.copy(loadingMessages = true)
        }
        InAppMessaging.instance.fetchMessages(threadId, beforeDate, 50) { messages, hasMore, exception ->
            if (exception == null) {
                mergeHistory(
                    history = messages.map { MessageRenderer.fromInAppMessage(it, threadId, state.value.userId) },
                    appendOlder = appendOlder
                )
                state.value = state.value.copy(
                    hasMoreMessages = hasMore == true,
                    loadingMessages = false,
                    loadingMoreMessages = false
                )
            } else {
                state.value = state.value.copy(loadingMessages = false, loadingMoreMessages = false)
                updateError(exception?.message ?: "Fetch messages failed")
            }
        }
    }

    fun deleteMessage(messageId: String) {
        val cleanMessageId = messageId.trim()
        if (cleanMessageId.isBlank()) return
        InAppMessaging.instance.deleteMessage(cleanMessageId) { deletedId, exception ->
            if (exception == null) {
                removeMessage(deletedId ?: cleanMessageId)
                state.value = state.value.copy(lastError = "Message deleted")
            } else {
                updateError(exception.message ?: "Delete message failed")
            }
        }
    }

    fun uploadSampleMedia() {
        if (!canReplyToActiveThread()) return updateError(replyBlockedReason())
        val uploadFile = File(context.cacheDir, "webex-connect-demo-upload.txt").apply {
            writeText("Webex Connect Demo upload for " + state.value.userId)
        }
        uploadMediaFile(uploadFile, "text/plain")
    }

    fun uploadSelectedMedia(uri: Uri) {
        if (!canReplyToActiveThread()) return updateError(replyBlockedReason())
        val contentType = context.contentResolver.getType(uri) ?: "application/octet-stream"
        val displayName = queryDisplayName(uri)
        val uploadFile = File(context.cacheDir, System.currentTimeMillis().toString() + "-" + safeUploadFileName(displayName))
        runCatching {
            context.contentResolver.openInputStream(uri)?.use { input ->
                uploadFile.outputStream().use { output -> input.copyTo(output) }
            } ?: throw IllegalArgumentException("Could not read selected attachment")
            uploadMediaFile(uploadFile, contentType)
        }.onFailure { exception ->
            state.value = state.value.copy(mediaStatus = "Attachment unavailable")
            updateError(exception.message ?: "Attachment upload failed")
        }
    }

    private fun uploadMediaFile(uploadFile: File, contentType: String) {
        val thread = activeThread ?: return updateError("Thread is not ready")
        if (!canReplyToActiveThread()) return updateError(replyBlockedReason())
        val manager = InAppMessaging.instance.mediaFileManager
        if (manager.isFileUploading(uploadFile)) {
            state.value = state.value.copy(mediaStatus = "Upload already in progress")
            return
        }
        state.value = state.value.copy(mediaStatus = "Uploading " + uploadFile.name)
        manager.uploadFile(uploadFile, contentType, object : FileUploadCallback {
            override fun onFileUploadProgress(file: File, bytesUploaded: Long, bytesTotal: Long) {
                state.value = state.value.copy(mediaStatus = progressLabel("Uploading", bytesUploaded, bytesTotal))
            }

            override fun onFileUploadComplete(file: File, mediaReference: String?, exception: WebexConnectException?) {
                if (exception == null && mediaReference.orEmpty().isNotBlank()) {
                    publishUploadedFile(thread, file, mediaReference.orEmpty(), contentType)
                } else {
                    state.value = state.value.copy(mediaStatus = "Upload failed")
                    updateError(exception?.message ?: "Media upload failed")
                }
            }
        })
    }

    fun downloadFirstMediaAttachment() {
        val attachment = firstRemoteAttachment() ?: return updateError("No remote media attachment is available")
        val url = runCatching { URL(attachment.url) }.getOrNull() ?: return updateError("Media URL is invalid")
        val manager = InAppMessaging.instance.mediaFileManager
        val cachedFile = manager.getCachedFile(url)
        if (cachedFile != null && cachedFile.exists()) {
            state.value = state.value.copy(mediaStatus = "Cached media: " + cachedFile.name)
            return
        }
        if (manager.isFileDownloading(url)) {
            state.value = state.value.copy(mediaStatus = "Download already in progress")
            return
        }
        state.value = state.value.copy(mediaStatus = "Downloading media")
        manager.downloadFile(url, object : FileDownloadCallback {
            override fun onFileDownloadProgress(url: URL, bytesDownloaded: Long, bytesTotal: Long) {
                state.value = state.value.copy(mediaStatus = progressLabel("Downloading", bytesDownloaded, bytesTotal))
            }

            override fun onFileDownloadComplete(url: URL, file: File?, exception: WebexConnectException?) {
                if (exception == null && file != null) {
                    state.value = state.value.copy(mediaStatus = "Downloaded media: " + file.name)
                } else {
                    state.value = state.value.copy(mediaStatus = "Download failed")
                    updateError(exception?.message ?: "Media download failed")
                }
            }
        })
    }

    fun regenerateFirstMediaUrl() {
        val attachment = firstRemoteAttachment() ?: return updateError("No remote media attachment is available")
        val url = runCatching { URL(attachment.url) }.getOrNull() ?: return updateError("Media URL is invalid")
        state.value = state.value.copy(mediaStatus = "Regenerating media URL")
        InAppMessaging.instance.mediaFileManager.regenerateMediaURL(url) { regeneratedUrl, exception ->
            if (exception == null && regeneratedUrl != null) {
                replaceAttachmentUrl(url.toString(), regeneratedUrl.toString())
                state.value = state.value.copy(mediaStatus = "Media URL refreshed")
            } else {
                state.value = state.value.copy(mediaStatus = "Media URL refresh failed")
                updateError(exception?.message ?: "Media URL regeneration failed")
            }
        }
    }

    fun sendTyping(isTyping: Boolean) {
        if (!canReplyToActiveThread()) return
        activeThread?.let { thread ->
            InAppMessaging.instance.publishTypingIndicator(thread, isTyping) { _, _, exception ->
                exception?.message?.let(::updateError)
            }
        }
    }

    fun fetchUnreadCount() {
        InAppMessaging.instance.fetchUnreadThreadCount { count, exception ->
            if (exception == null) state.value = state.value.copy(unreadCount = count ?: 0)
            else updateError(exception.message ?: "Unread count failed")
        }
    }
"""


def inapp_controller_helpers() -> str:
    return """
    private fun resetInAppSessionState() {
        activeThread = null
        lastRecoverySyncAt = 0L
        pendingMessageRefreshes.values.forEach(mainHandler::removeCallbacks)
        pendingMessageRefreshes.clear()
        pendingOutgoingIds.clear()
        pendingOutgoingFingerprints.clear()
        pendingReceiptStatuses.clear()
    }

    private fun scheduleThreadMessageRefresh(threadId: String = currentActiveThreadId(), delayMs: Long = 900L) {
        val cleanThreadId = threadId.trim().ifBlank { currentActiveThreadId() }
        if (cleanThreadId.isBlank()) return
        pendingMessageRefreshes.remove(cleanThreadId)?.let(mainHandler::removeCallbacks)
        val refresh = Runnable {
            pendingMessageRefreshes.remove(cleanThreadId)
            if (currentActiveThreadId() == cleanThreadId) {
                fetchMessages()
            } else {
                syncThreadMetadata(cleanThreadId)
            }
        }
        pendingMessageRefreshes[cleanThreadId] = refresh
        mainHandler.postDelayed(refresh, delayMs)
    }

    private fun syncAfterConnectionRestored(openDefaultWhenEmpty: Boolean) {
        val now = System.currentTimeMillis()
        if (now - lastRecoverySyncAt < 1500L) return
        lastRecoverySyncAt = now
        fetchThreads(openDefaultWhenEmpty = openDefaultWhenEmpty)
        fetchUnreadCount()
    }

    private fun syncThreadMetadata(threadId: String) {
        val cleanThreadId = threadId.trim()
        if (cleanThreadId.isBlank()) {
            fetchThreads(openDefaultWhenEmpty = false)
            return
        }
        InAppMessaging.instance.fetchThread(cleanThreadId) { thread, exception ->
            if (exception == null && thread != null) {
                val activeId = currentActiveThreadId()
                if (activeId == cleanThreadId) {
                    activeThread = thread
                }
                state.value = state.value.copy(
                    threads = upsertThread(state.value.threads, toDemoThread(thread))
                )
            } else {
                fetchThreads(openDefaultWhenEmpty = false)
            }
        }
    }

    private fun acknowledgeIncomingMessage(message: InAppMessage, rendered: DemoMessage, markRead: Boolean) {
        if (rendered.outgoing) return
        if (rendered.kind == DemoMessageKind.RECEIPT ||
            rendered.kind == DemoMessageKind.TYPING ||
            rendered.kind == DemoMessageKind.THREAD_UPDATE ||
            rendered.kind == DemoMessageKind.DELETED
        ) {
            return
        }
        val transactionId = message.transactionId.orEmpty()
        if (transactionId.isBlank()) return
        InAppMessaging.instance.sendMessageStatus(transactionId, InAppMessageStatus.DELIVERED, null) { _, _, exception ->
            exception?.message?.let(::updateError)
        }
        if (markRead) {
            InAppMessaging.instance.sendMessageStatus(transactionId, InAppMessageStatus.READ, null) { _, _, exception ->
                exception?.message?.let(::updateError)
            }
        }
    }

    private fun activateThread(thread: InAppThread, resetMessages: Boolean) {
        activeThread = thread
        val demoThread = toDemoThread(thread)
        val nextMessages = if (resetMessages) emptyList() else state.value.messages
        val nextDisabled = if (resetMessages) emptySet() else state.value.disabledInteractionIds
        state.value = state.value.copy(
            threads = upsertThread(state.value.threads, demoThread),
            threadId = demoThread.id,
            selectedThreadId = demoThread.id,
            messages = nextMessages,
            disabledInteractionIds = nextDisabled,
            hasMoreMessages = false,
            loadingMessages = if (resetMessages) true else state.value.loadingMessages,
            loadingMoreMessages = false,
            lastError = ""
        )
    }

    private fun updateActiveThreadStatus(nextStatus: InAppThreadStatus, reason: String) {
        val thread = activeThread ?: return updateError("Select a thread first")
        thread.status = nextStatus
        thread.reasonForStatusChange = reason
        InAppMessaging.instance.updateThread(thread) { updated, exception ->
            if (exception == null) {
                val nextThread = updated ?: thread
                activateThread(nextThread, resetMessages = false)
                fetchThreads(openDefaultWhenEmpty = false)
                val statusLabel = if (nextStatus == InAppThreadStatus.CLOSED) "closed" else "reopened"
                updateError("Thread " + statusLabel)
            } else {
                updateError(exception.message ?: "Thread update failed")
            }
        }
    }

    private fun toDemoThread(thread: InAppThread): DemoThread {
        val status = thread.status?.value.orEmpty()
            .ifBlank { thread.status?.toString().orEmpty() }
            .ifBlank { "active" }
            .lowercase()
        val type = thread.type?.value.orEmpty()
            .ifBlank { thread.type?.toString().orEmpty() }
            .ifBlank { "conversation" }
            .lowercase()
        val title = thread.title.orEmpty()
            .ifBlank { thread.lastMessagePreview.orEmpty().take(48) }
            .ifBlank { "Support conversation" }
        return DemoThread(
            id = thread.id.orEmpty(),
            title = title,
            category = thread.category.orEmpty(),
            status = status,
            type = type,
            unreadCount = thread.unreadMessageCount,
            updatedAt = thread.updatedAt?.time ?: thread.createdAt?.time ?: 0L,
            lastMessage = customerVisibleText(thread.lastMessagePreview.orEmpty())
        )
    }

    private fun upsertThread(current: List<DemoThread>, thread: DemoThread): List<DemoThread> {
        if (thread.id.isBlank()) return current
        return mergeThreads(current, listOf(thread))
    }

    private fun mergeThreads(current: List<DemoThread>, incoming: List<DemoThread>): List<DemoThread> {
        return (incoming + current)
            .filter { it.id.isNotBlank() }
            .distinctBy { it.id }
            .sortedWith(compareByDescending<DemoThread> { it.updatedAt }.thenBy { it.title.lowercase() })
    }

    private fun activeDemoThread(): DemoThread? {
        val selectedId = state.value.selectedThreadId.ifBlank { state.value.threadId }
        return state.value.threads.firstOrNull { it.id == selectedId }
    }

    private fun activeThreadClosed(): Boolean =
        activeDemoThread()?.closed == true || activeThread?.status == InAppThreadStatus.CLOSED

    private fun activeThreadAnnouncement(): Boolean =
        activeDemoThread()?.announcement == true || activeThread?.type == InAppThreadType.ANNOUNCEMENT

    private fun canReplyToActiveThread(): Boolean =
        !activeThreadClosed() && !activeThreadAnnouncement()

    private fun replyBlockedReason(): String =
        when {
            activeThreadClosed() -> "Thread is closed. Reopen it before replying."
            activeThreadAnnouncement() -> "Announcement threads are read-only."
            else -> "Thread is not ready"
        }

    private fun replaceMessage(oldId: String, message: DemoMessage) {
        val current = state.value.messages
        val fingerprint = messageFingerprint(message.text)
        val index = current.indexOfFirst {
            it.id == oldId ||
                it.id == message.id ||
                (message.outgoing && it.outgoing && messageFingerprint(it.text) == fingerprint)
        }
        if (index >= 0) {
            val next = current.toMutableList().also { it[index] = message }
            state.value = state.value.copy(messages = orderedMessages(next))
        } else {
            upsertMessage(message)
        }
    }

    private fun applyStatusReceipt(message: DemoMessage): Boolean {
        if (message.kind != DemoMessageKind.RECEIPT) return false
        val targetId = message.relatedId.ifBlank { message.id }
        val nextStatus = normalizedDeliveryStatus(message.status.ifBlank { message.type })
        if (targetId.isBlank() || nextStatus.isBlank()) return true
        val current = state.value.messages
        var matched = false
        val next = current.map { existing ->
            if (existing.outgoing && existing.id == targetId) {
                matched = true
                existing.copy(status = preferredDeliveryStatus(existing.status, nextStatus))
            } else {
                existing
            }
        }
        if (matched) {
            state.value = state.value.copy(messages = orderedMessages(next))
        } else {
            pendingReceiptStatuses[targetId] = nextStatus
        }
        return true
    }

    private fun replaceHistory(history: List<DemoMessage>) {
        mergeHistory(history, appendOlder = false)
    }

    private fun mergeHistory(history: List<DemoMessage>, appendOlder: Boolean) {
        history.filter { it.kind == DemoMessageKind.RECEIPT }.forEach(::applyStatusReceipt)
        val displayHistory = history.filterNot { it.kind == DemoMessageKind.RECEIPT }
        val existingById = state.value.messages.associateBy { it.id }
        val normalizedHistory = displayHistory.map { message ->
            val existing = existingById[message.id]
            if (existing?.outgoing == true) {
                message.copy(outgoing = true, status = preferredDeliveryStatus(existing.status, message.status))
            } else {
                message
            }
        }
        val now = System.currentTimeMillis()
        val visibleHistoryGraceMs = 2 * 60 * 1000L
        val carriedForward = state.value.messages.filter { message ->
            val missingFromHistory = normalizedHistory.none {
                it.id == message.id || messageFingerprint(it.text) == messageFingerprint(message.text)
            }
            val stillPublishing = message.status.equals("sending", ignoreCase = true) ||
                message.status.equals("failed", ignoreCase = true)
            val recentlyVisible = message.createdAt <= 0L || now - message.createdAt < visibleHistoryGraceMs
            missingFromHistory && (stillPublishing || recentlyVisible)
        }
        val merged = if (appendOlder) {
            (normalizedHistory + state.value.messages).distinctBy { it.id }
        } else {
            (normalizedHistory + carriedForward).distinctBy { it.id }
        }
        state.value = state.value.copy(messages = orderedMessages(merged))
    }

    private fun removeMessage(messageId: String) {
        state.value = state.value.copy(
            messages = state.value.messages.filterNot { it.id == messageId },
            disabledInteractionIds = state.value.disabledInteractionIds - messageId
        )
    }

    private fun publishUploadedFile(thread: InAppThread, file: File, url: String, contentType: String) {
        val attachment = InAppFileAttachment().apply {
            fileName = file.name
            size = file.length()
            this.contentType = contentType
            this.url = URL(url)
        }
        val message = InAppMessage().apply {
            this.message = "Uploaded " + file.name
            this.thread = thread
            this.attachments = listOf<InAppAttachment>(attachment)
        }
        state.value = state.value.copy(mediaStatus = "Upload complete; publishing attachment")
        publishOutgoing(message, "Uploaded " + file.name)
    }

    private fun queryDisplayName(uri: Uri): String {
        return context.contentResolver
            .query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { cursor ->
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (nameIndex >= 0 && cursor.moveToFirst()) cursor.getString(nameIndex).orEmpty() else ""
            }
            .orEmpty()
            .ifBlank { uri.lastPathSegment?.substringAfterLast('/').orEmpty() }
            .ifBlank { "webex-connect-upload" }
    }

    private fun safeUploadFileName(name: String): String =
        name.replace(Regex("[^A-Za-z0-9._-]"), "_").ifBlank { "webex-connect-upload" }

    private fun firstRemoteAttachment(): DemoAttachment? =
        state.value.messages
            .flatMap { it.attachments }
            .firstOrNull { it.url.startsWith("http://") || it.url.startsWith("https://") }

    private fun replaceAttachmentUrl(oldUrl: String, newUrl: String) {
        state.value = state.value.copy(
            messages = orderedMessages(state.value.messages.map { message ->
                message.copy(
                    attachments = message.attachments.map { attachment ->
                        if (attachment.url == oldUrl) {
                            attachment.copy(url = newUrl, metadata = "Regenerated media URL")
                        } else {
                            attachment
                        }
                    }
                )
            })
        )
    }

    private fun progressLabel(prefix: String, completedBytes: Long, totalBytes: Long): String {
        return if (totalBytes > 0L) {
            prefix + " " + ((completedBytes * 100L) / totalBytes).coerceIn(0L, 100L) + "%"
        } else {
            prefix
        }
    }

    private fun shouldSuppressOutgoingEcho(message: DemoMessage): Boolean {
        if (pendingOutgoingIds.remove(message.id)) {
            replacePendingOutgoing(message.copy(outgoing = true))
            return true
        }

        if (!message.outgoing) {
            return false
        }
        val fingerprint = messageFingerprint(message.text)
        if (fingerprint.isBlank() || !pendingOutgoingFingerprints.remove(fingerprint)) {
            return false
        }
        replacePendingOutgoing(message)
        return true
    }

    private fun shouldDisplayInActiveThread(message: DemoMessage): Boolean {
        val messageThreadId = message.threadId.trim()
        if (messageThreadId.isBlank()) return true
        val activeId = currentActiveThreadId()
        return activeId.isBlank() || activeId == messageThreadId
    }

    private fun replacePendingOutgoing(message: DemoMessage) {
        val fingerprint = messageFingerprint(message.text)
        val receiptStatus = pendingReceiptStatuses.remove(message.id).orEmpty()
        val current = state.value.messages
        val index = current.indexOfLast { it.outgoing && messageFingerprint(it.text) == fingerprint }
        if (index >= 0) {
            val next = current.toMutableList().also {
                it[index] = it[index].copy(
                    id = message.id,
                    status = preferredDeliveryStatus(
                        it[index].status,
                        preferredDeliveryStatus(message.status.ifBlank { "sent" }, receiptStatus)
                    )
                )
            }
            state.value = state.value.copy(messages = orderedMessages(next))
        }
    }

    private fun orderedMessages(messages: List<DemoMessage>): List<DemoMessage> =
        messages.withIndex()
            .sortedWith(
                compareBy<IndexedValue<DemoMessage>> { item ->
                    if (item.value.createdAt > 0L) item.value.createdAt else Long.MAX_VALUE
                }.thenBy { item ->
                    item.index
                }
            )
            .map { item ->
                item.value
            }

    private fun currentActiveThreadId(): String =
        activeThread?.id.orEmpty().ifBlank { state.value.selectedThreadId.ifBlank { state.value.threadId } }

    private fun normalizedDeliveryStatus(status: String): String {
        val value = status.trim().replace('_', ' ').lowercase()
        return when {
            value.contains("read") -> "Read"
            value.contains("deliver") -> "Delivered"
            value.contains("sent") || value.contains("submit") || value.contains("success") -> "Sent"
            value.contains("send") -> "Sending"
            value.contains("fail") || value.contains("error") -> "Failed"
            else -> status.trim()
        }
    }

    private fun preferredDeliveryStatus(current: String, next: String): String {
        val normalizedNext = normalizedDeliveryStatus(next)
        if (normalizedNext.isBlank()) return current
        if (current.isBlank()) return normalizedNext
        return if (deliveryStatusRank(normalizedNext) >= deliveryStatusRank(current)) normalizedNext else current
    }

    private fun deliveryStatusRank(status: String): Int {
        val value = status.lowercase()
        return when {
            value.contains("read") -> 4
            value.contains("deliver") -> 3
            value.contains("sent") -> 2
            value.contains("send") -> 1
            value.contains("fail") -> 0
            else -> 1
        }
    }

    private fun messageFingerprint(text: String): String {
        return text.trim().lowercase()
    }
"""


def notification_support_file(args: argparse.Namespace) -> str:
    if not includes_push(args):
        return """package __PACKAGE__

import android.content.Context

object NotificationSupport {
    fun createDefaultChannel(context: Context) {
    }
}
""".replace("__PACKAGE__", args.package)

    return """package __PACKAGE__

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.webex.connect.push.inappdisplay.InAppNotificationCallback
import com.webex.connect.push.PushMessaging
import com.webex.connect.push.message.PushInteractiveData
import com.webex.connect.push.message.PushMessage
import com.webex.connect.push.message.PushMessageStatus
import com.webex.connect.push.notification.NotificationBuilderCallback
import com.webex.connect.push.notification.NotificationFactory
import com.webex.connect.push.notification.action.NotificationActionHandler

object NotificationSupport {
    fun createDefaultChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NotificationFactory.DEFAULT_CHANNEL_ID,
                context.getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = context.getString(R.string.channel_description)
            }
            context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
        PushMessaging.instance.notificationFactory?.notificationBuilderCallback = DemoNotificationBuilder()
    }

    fun configurePushPresentation(
        context: Context,
        onForegroundNotification: (DemoNotification) -> Unit,
        onStatus: (String) -> Unit
    ) {
        createDefaultChannel(context)
        PushMessaging.instance.actionHandler = DemoNotificationActionHandler(onStatus)
        PushMessaging.instance.inAppNotificationManager.registerListener(
            DemoInAppNotificationListener(onForegroundNotification, onStatus)
        )
        onStatus("Push action handler and foreground notification listener configured")
    }
}

class DemoNotificationBuilder : NotificationBuilderCallback {
    override fun getActionIconId(context: Context, message: PushMessage, action: String, identifier: String): Int =
        R.drawable.ic_stat_webex_connect

    override fun onBuildNotification(
        context: Context,
        message: PushMessage,
        notificationId: Int,
        builder: NotificationCompat.Builder
    ) {
        builder.setSmallIcon(R.drawable.ic_stat_webex_connect)
        builder.setContentTitle("Webex Connect Demo")
    }
}

class DemoNotificationActionHandler(
    private val onStatus: (String) -> Unit
) : NotificationActionHandler {
    override fun handleAction(context: Context, action: String, intent: Intent): Boolean {
        val actionName = action.ifBlank { intent.action.orEmpty() }.ifBlank { "notification action" }
        val identifier = intent.getStringExtra("identifier").orEmpty()
        onStatus("Push action received: " + actionName + if (identifier.isBlank()) "" else " / " + identifier)
        return false
    }
}

class DemoInAppNotificationListener(
    private val onForegroundNotification: (DemoNotification) -> Unit,
    private val onStatus: (String) -> Unit
) : InAppNotificationCallback {
    override fun onNotificationDisplayed(message: PushMessage?) {
        onForegroundNotification(
            DemoNotification(
                id = message?.transactionId ?: "foreground-" + System.currentTimeMillis(),
                title = message?.title.orEmpty().ifBlank { "Webex Connect message" },
                body = message?.message.orEmpty().ifBlank { "Foreground notification displayed" },
                timeLabel = "Now",
                category = "Foreground",
                unread = true
            )
        )
        message?.transactionId?.let { id ->
            PushMessaging.instance.sendMessageStatus(id, PushMessageStatus.DELIVERED, null) { _, _, exception ->
                exception?.message?.let(onStatus)
            }
        }
    }

    override fun onNotificationClicked(message: PushMessage?, action: String?, value: String?) {
        onStatus("Foreground notification clicked: " + action.orEmpty().ifBlank { "open" })
        val transactionId = message?.transactionId ?: return
        val interactiveData = PushInteractiveData().apply {
            this.action = action.orEmpty()
            this.identifier = value.orEmpty()
            this.category = message.category.orEmpty()
            this.value = action.orEmpty().ifBlank { "open" }
        }
        PushMessaging.instance.sendMessageStatus(transactionId, PushMessageStatus.READ, interactiveData) { _, _, exception ->
            exception?.message?.let(onStatus)
        }
    }

    override fun onNotificationDismissed(message: PushMessage?) {
        onStatus("Foreground notification dismissed")
    }
}
""".replace("__PACKAGE__", args.package)


def message_renderer_file(args: argparse.Namespace) -> str:
    if includes_inapp(args):
        return inapp_message_renderer_file(args)
    return push_message_renderer_file(args)


def push_message_renderer_file(args: argparse.Namespace) -> str:
    return """package __PACKAGE__

import com.webex.connect.push.message.PushMessage
import org.json.JSONArray
import org.json.JSONObject

object MessageRenderer {
    fun fromPushMessage(message: PushMessage): DemoMessage {
        val json = runCatching { message.toJson() }.getOrNull()
        val text = readableText(message.message)
            ?: readableText(message.title)
            ?: readableText(json?.optString("message"))
            ?: readableText(json?.optString("body"))
            ?: "Push notification"
        return DemoMessage(
            id = stablePushMessageId(message, json, text),
            text = text,
            outgoing = false,
            status = message.status?.toString().orEmpty().ifBlank { "push" },
            type = "push",
            kind = DemoMessageKind.ALERT,
            createdAt = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        )
    }

    private fun stablePushMessageId(message: PushMessage, json: JSONObject?, text: String): String {
        val explicitId = listOf(
            message.transactionId,
            json?.optString("transactionId"),
            json?.optString("messageId"),
            json?.optString("id")
        ).mapNotNull { it?.trim() }.firstOrNull { it.isNotBlank() }
        if (explicitId != null) return explicitId
        val timestamp = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        return "push-" + listOf(timestamp.toString(), text.take(96)).joinToString("|").hashCode().toString()
    }

    private fun readableText(value: String?): String? {
        val text = value?.trim().orEmpty()
        if (text.isBlank()) return null
        if (!text.startsWith("{") && !text.startsWith("[")) {
            return cleanPlainText(text).takeIf { it.isNotBlank() }
        }
        if (text.startsWith("[")) {
            val array = runCatching { JSONArray(text) }.getOrNull() ?: return null
            return (0 until array.length())
                .asSequence()
                .mapNotNull { index -> readableText(array.opt(index)?.toString()) }
                .firstOrNull()
        }
        val json = runCatching { JSONObject(text) }.getOrNull() ?: return null
        return listOf(
            "text",
            "message",
            "body",
            "title",
            "description",
            "content",
            "displayText",
            "messageText",
            "notification",
            "alert",
            "data",
            "payload"
        ).asSequence()
            .mapNotNull { key ->
                json.opt(key)
                    ?.takeUnless { it == JSONObject.NULL }
                    ?.toString()
                    ?.let(::readableText)
            }
            .firstOrNull()
    }

    private fun cleanPlainText(value: String): String {
        var text = value.replace(Regex("\\\\s+"), " ").trim()
        listOf("Webex Connect Demo Chat", "Webex Connect Demo", "APA91").forEach { marker ->
            val index = text.indexOf(marker)
            if (index > 0) text = text.take(index).trim()
        }
        text = text
            .replace(Regex("[A-Za-z0-9_-]{12,}:APA[0-9A-Za-z_:-]+"), "")
            .replace(Regex("\\\\d{10,}\\\\d{4}-\\\\d{2}-\\\\d{2}T[^\\\\s]+"), " ")
            .trim()
        return text.ifBlank { value.take(180).trim() }
    }
}
""".replace("__PACKAGE__", args.package)


def inapp_message_renderer_file(args: argparse.Namespace) -> str:
    push_import = "import com.webex.connect.push.message.PushMessage\n" if includes_push(args) else ""
    push_function = """
    fun fromPushMessage(message: PushMessage): DemoMessage {
        val json = runCatching { message.toJson() }.getOrNull()
        val text = readableText(message.message)
            ?: readableText(message.title)
            ?: readableText(json?.optString("message"))
            ?: readableText(json?.optString("body"))
            ?: "Push notification"
        return DemoMessage(
            id = stablePushMessageId(message, json, text),
            text = text,
            outgoing = false,
            status = message.status?.toString().orEmpty().ifBlank { "push" },
            type = "push",
            kind = DemoMessageKind.ALERT,
            createdAt = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        )
    }

    private fun stablePushMessageId(message: PushMessage, json: JSONObject?, text: String): String {
        val explicitId = listOf(
            message.transactionId,
            json?.optString("transactionId"),
            json?.optString("messageId"),
            json?.optString("id")
        ).mapNotNull { it?.trim() }.firstOrNull { it.isNotBlank() }
        if (explicitId != null) return explicitId
        val timestamp = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        return "push-" + listOf(timestamp.toString(), text.take(96)).joinToString("|").hashCode().toString()
    }

""" if includes_push(args) else ""
    template = """package __PACKAGE__

import com.webex.connect.inapp.message.InAppButton
import com.webex.connect.inapp.message.InAppMessage
import com.webex.connect.inapp.message.InAppMessageType
import com.webex.connect.inapp.message.attachments.InAppAttachment
import com.webex.connect.inapp.message.attachments.media.InAppAudioAttachment
import com.webex.connect.inapp.message.attachments.media.InAppFileAttachment
import com.webex.connect.inapp.message.attachments.media.InAppImageAttachment
import com.webex.connect.inapp.message.attachments.media.InAppLocationAttachment
import com.webex.connect.inapp.message.attachments.media.InAppVideoAttachment
import com.webex.connect.inapp.message.attachments.templates.InAppFormTemplateAttachment
import com.webex.connect.inapp.message.attachments.templates.InAppGenericTemplateAttachment
import com.webex.connect.inapp.message.attachments.templates.InAppGenericTemplateElement
__PUSH_IMPORT__import org.json.JSONArray
import org.json.JSONObject

object MessageRenderer {
    fun fromInAppMessage(message: InAppMessage, currentThreadId: String = "", currentUserId: String = ""): DemoMessage {
        val type = message.type?.value.orEmpty().ifBlank { message.type?.toString().orEmpty() }.ifBlank { "message" }
        val json = runCatching { message.toJson() }.getOrNull()
        val extras = json?.optJSONObject("extras")?.let(::toStringMap).orEmpty()
        val attachments = message.attachments.orEmpty()
        val quickReplyActions = message.quickReply?.buttons.orEmpty().map(::toAction)
        val attachmentData = attachments.map(::toAttachment)
        val cards = attachments.filterIsInstance<InAppGenericTemplateAttachment>().flatMap { template ->
            template.elements.orEmpty().map(::toCard)
        }
        val fields = attachments.filterIsInstance<InAppFormTemplateAttachment>().flatMap { template ->
            template.formFields.orEmpty().map { field ->
                DemoField(
                    label = field.label.orEmpty().ifBlank { field.name.orEmpty().ifBlank { "Field" } },
                    name = field.name.orEmpty(),
                    value = field.value.orEmpty().ifBlank { field.values.orEmpty().joinToString(", ") },
                    type = field.type?.value.orEmpty().ifBlank { field.type?.toString().orEmpty() },
                    required = field.isMandatory,
                    options = field.options.orEmpty()
                )
            }
        }
        val kind = kindFor(type, attachments, quickReplyActions, cards, fields)
        val text = readableText(message.message)
            ?: readableText(json?.optString("message"))
            ?: readableText(json?.optString("body"))
            ?: fallbackText(type, kind, attachments, cards, fields, message.status)
        val outgoing = isCustomerAuthoredMessage(kind, message, json, currentUserId)
        val statusSourceType = if (kind == DemoMessageKind.RECEIPT) type else ""
        val status = if (outgoing || kind == DemoMessageKind.RECEIPT) statusLabel(message.status, statusSourceType) else ""
        val threadId = message.thread?.id.orEmpty().ifBlank { currentThreadId }
        return DemoMessage(
            id = stableInAppMessageId(message, json, threadId, type, text),
            text = text,
            outgoing = outgoing,
            status = status,
            type = type,
            threadId = threadId,
            relatedId = message.relatedTransactionId.orEmpty(),
            kind = kind,
            actions = quickReplyActions + attachments.flatMap { attachmentActions(it) },
            cards = cards,
            fields = fields,
            attachments = attachmentData,
            extras = extras,
            createdAt = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        )
    }

__PUSH_FUNCTION__    private fun kindFor(
        type: String,
        attachments: List<InAppAttachment>,
        quickReplyActions: List<DemoAction>,
        cards: List<DemoCard>,
        fields: List<DemoField>
    ): DemoMessageKind {
        return when {
            typeMatches(type, InAppMessageType.TYPING_START, InAppMessageType.TYPING_STOP) -> DemoMessageKind.TYPING
            typeMatches(type, InAppMessageType.MESSAGE_DELETED) -> DemoMessageKind.DELETED
            typeMatches(type, InAppMessageType.DELIVERY_RECEIPT, InAppMessageType.READ_RECEIPT, InAppMessageType.CLICKED_RECEIPT) -> DemoMessageKind.RECEIPT
            typeMatches(type, InAppMessageType.THREAD_UPDATE) -> DemoMessageKind.THREAD_UPDATE
            typeMatches(type, InAppMessageType.ALERT) -> DemoMessageKind.ALERT
            fields.isNotEmpty() -> DemoMessageKind.FORM_TEMPLATE
            cards.isNotEmpty() -> DemoMessageKind.GENERIC_TEMPLATE
            quickReplyActions.isNotEmpty() -> DemoMessageKind.QUICK_REPLY
            attachments.any { it is InAppLocationAttachment } -> DemoMessageKind.LOCATION
            attachments.any { it is InAppFileAttachment } -> DemoMessageKind.MEDIA
            type.equals("message", ignoreCase = true) -> DemoMessageKind.TEXT
            else -> DemoMessageKind.UNKNOWN
        }
    }

    private fun typeMatches(type: String, vararg values: InAppMessageType): Boolean {
        return values.any { value ->
            type.equals(value.value, ignoreCase = true) || type.equals(value.toString(), ignoreCase = true)
        }
    }

    private fun toAction(button: InAppButton): DemoAction {
        return DemoAction(
            id = button.id.orEmpty(),
            title = button.title.orEmpty().ifBlank { "Choose" },
            payload = button.payload?.toString().orEmpty(),
            type = button.type?.value.orEmpty().ifBlank { button.type?.toString().orEmpty() }
        )
    }

    private fun toCard(element: InAppGenericTemplateElement): DemoCard {
        return DemoCard(
            title = element.title.orEmpty().ifBlank { "Webex Connect update" },
            subtitle = element.subtitle.orEmpty(),
            imageUrl = element.imageUrls.orEmpty().firstOrNull().orEmpty(),
            imageUrls = element.imageUrls.orEmpty(),
            actions = element.buttons.orEmpty().map(::toAction)
        )
    }

    private fun attachmentActions(attachment: InAppAttachment): List<DemoAction> {
        return when (attachment) {
            is InAppGenericTemplateAttachment -> attachment.elements.orEmpty().flatMap { it.buttons.orEmpty().map(::toAction) }
            else -> emptyList()
        }
    }

    private fun toAttachment(attachment: InAppAttachment): DemoAttachment {
        return when (attachment) {
            is InAppLocationAttachment -> DemoAttachment(
                kind = "location",
                label = "Shared location",
                metadata = "${attachment.latitude}, ${attachment.longitude}"
            )
            is InAppImageAttachment -> DemoAttachment("image", attachment.fileName.orEmpty().ifBlank { "Image" }, attachment.url?.toString().orEmpty())
            is InAppVideoAttachment -> DemoAttachment("video", attachment.fileName.orEmpty().ifBlank { "Video" }, attachment.url?.toString().orEmpty(), "${attachment.duration}s")
            is InAppAudioAttachment -> DemoAttachment("audio", attachment.fileName.orEmpty().ifBlank { "Audio" }, attachment.url?.toString().orEmpty(), "${attachment.duration}s")
            is InAppFileAttachment -> {
                val contentType = attachment.contentType.orEmpty()
                val kind = when {
                    contentType.startsWith("image/", ignoreCase = true) -> "image"
                    contentType.startsWith("video/", ignoreCase = true) -> "video"
                    contentType.startsWith("audio/", ignoreCase = true) -> "audio"
                    else -> "file"
                }
                DemoAttachment(kind, attachment.fileName.orEmpty().ifBlank { "File" }, attachment.url?.toString().orEmpty(), contentType)
            }
            else -> DemoAttachment("attachment", attachment.contentType.orEmpty().ifBlank { "Attachment" })
        }
    }

    private fun fallbackText(
        type: String,
        kind: DemoMessageKind,
        attachments: List<InAppAttachment>,
        cards: List<DemoCard>,
        fields: List<DemoField>,
        status: Any?
    ): String {
        return when (kind) {
            DemoMessageKind.QUICK_REPLY -> "Choose a quick reply"
            DemoMessageKind.GENERIC_TEMPLATE -> "${cards.size} support option(s) available"
            DemoMessageKind.FORM_TEMPLATE -> "Complete the ${fields.size}-field support form"
            DemoMessageKind.LOCATION -> "Location shared"
            DemoMessageKind.MEDIA -> "${attachments.size} attachment(s)"
            DemoMessageKind.RECEIPT -> "Message status: ${statusLabel(status)}"
            DemoMessageKind.TYPING -> if (typeMatches(type, InAppMessageType.TYPING_STOP)) "Typing stopped" else "Typing..."
            DemoMessageKind.THREAD_UPDATE -> "Conversation updated"
            DemoMessageKind.DELETED -> "Message deleted"
            DemoMessageKind.ALERT -> "Webex Connect alert"
            else -> "Message received"
        }
    }

    private fun stableInAppMessageId(
        message: InAppMessage,
        json: JSONObject?,
        threadId: String,
        type: String,
        text: String
    ): String {
        val explicitId = listOf(
            message.transactionId,
            message.relatedTransactionId,
            json?.optString("transactionId"),
            json?.optString("relatedTransactionId"),
            json?.optString("messageId"),
            json?.optString("id")
        ).mapNotNull { it?.trim() }.firstOrNull { it.isNotBlank() }
        if (explicitId != null) return explicitId
        val timestamp = message.submittedAt?.time ?: message.createdAt?.time ?: 0L
        return "inapp-" + listOf(threadId, type, timestamp.toString(), text.take(96)).joinToString("|").hashCode().toString()
    }

    private fun isCustomerAuthoredMessage(
        kind: DemoMessageKind,
        message: InAppMessage,
        json: JSONObject?,
        currentUserId: String
    ): Boolean {
        return when (kind) {
            DemoMessageKind.ALERT,
            DemoMessageKind.THREAD_UPDATE,
            DemoMessageKind.DELETED,
            DemoMessageKind.RECEIPT,
            DemoMessageKind.TYPING -> false
            else -> isCurrentUserMessage(message, json, currentUserId)
        }
    }

    private fun isCurrentUserMessage(message: InAppMessage, json: JSONObject?, currentUserId: String): Boolean {
        val userId = currentUserId.trim()
        val senderDescriptor = listOf(
            json?.optString("senderType"),
            json?.optString("sender_type"),
            json?.optString("source"),
            json?.optString("origin"),
            json?.optString("messageOrigin"),
            json?.optString("actorType"),
            json?.optString("actor_type"),
            json?.optString("authorType"),
            json?.optString("author_type"),
            json?.optJSONObject("sender")?.optString("type"),
            json?.optJSONObject("from")?.optString("type"),
            json?.optJSONObject("author")?.optString("type"),
            json?.optJSONObject("createdBy")?.optString("type")
        ).mapNotNull { it?.trim() }.joinToString(" ").lowercase()
        if (listOf("agent", "bot", "business", "platform", "system", "automation", "admin").any { senderDescriptor.contains(it) }) {
            return false
        }
        if (listOf("customer", "consumer", "appuser", "app_user", "mobileuser", "mobile_user", "enduser", "end_user").any { senderDescriptor.contains(it) }) {
            return true
        }

        val directionValue = listOf(
            json?.optString("direction"),
            json?.optString("messageDirection"),
            json?.optString("message_direction"),
            json?.optString("source"),
            json?.optString("origin"),
            json?.optString("senderType"),
            json?.optString("sender_type"),
            json?.optString("messageOrigin"),
            json?.optJSONObject("sender")?.optString("type"),
            json?.optJSONObject("from")?.optString("type")
        ).mapNotNull { it?.trim() }.joinToString(" ").lowercase()

        if (directionValue.isNotBlank()) {
            val paddedDirectionValue = " $directionValue "
            when {
                paddedDirectionValue.contains(" mt ") ||
                    directionValue.contains("mobile terminated") ||
                    directionValue.contains("outbound") ||
                    listOf("agent", "bot", "business", "platform", "system", "automation").any { directionValue.contains(it) } -> return false
                paddedDirectionValue.contains(" mo ") ||
                    directionValue.contains("mobile originated") ||
                    directionValue.contains("inbound") ||
                    listOf("customer", "consumer", "device", "appuser", "app_user", "mobileuser", "mobile_user", "enduser", "end_user").any { directionValue.contains(it) } -> return true
            }
        }

        val senderCandidates = listOf(
            json?.optString("senderId"),
            json?.optString("sender_id"),
            json?.optString("from"),
            json?.optString("fromId"),
            json?.optString("from_id"),
            json?.optString("authorId"),
            json?.optString("author_id"),
            json?.optString("createdBy"),
            json?.optString("created_by"),
            json?.optString("submittedBy"),
            json?.optString("submitted_by"),
            json?.optJSONObject("sender")?.optString("id"),
            json?.optJSONObject("from")?.optString("id"),
            json?.optJSONObject("author")?.optString("id"),
            json?.optJSONObject("createdBy")?.optString("id")
        ).mapNotNull { it?.trim() }.filter { it.isNotBlank() }
        if (userId.isNotBlank() && senderCandidates.any { it.equals(userId, ignoreCase = true) }) {
            return true
        }

        return message.isOutgoing
    }

    private fun statusLabel(status: Any?, type: String = ""): String {
        val value = status?.toString().orEmpty().ifBlank { type }.replace('_', ' ').lowercase()
        return when {
            value.contains("read") -> "Read"
            value.contains("deliver") -> "Delivered"
            value.contains("sent") || value.contains("submit") || value.contains("success") -> "Sent"
            value.contains("send") -> "Sending"
            value.contains("fail") || value.contains("error") -> "Failed"
            else -> value.replaceFirstChar { it.uppercase() }
        }.ifBlank { "Sent" }
    }

    private fun toStringMap(json: JSONObject): Map<String, String> {
        val result = mutableMapOf<String, String>()
        val keys = json.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val value = json.opt(key)?.takeUnless { it == JSONObject.NULL }?.toString().orEmpty()
            if (value.isNotBlank() && value.length <= 120) {
                result[key] = value
            }
        }
        return result
    }

    private fun readableText(value: String?): String? {
        val text = value?.trim().orEmpty()
        if (text.isBlank()) return null
        if (!text.startsWith("{") && !text.startsWith("[")) {
            return cleanPlainText(text).takeIf { it.isNotBlank() }
        }
        if (text.startsWith("[")) {
            val array = runCatching { JSONArray(text) }.getOrNull() ?: return null
            return (0 until array.length())
                .asSequence()
                .mapNotNull { index -> readableText(array.opt(index)?.toString()) }
                .firstOrNull()
        }
        val json = runCatching { JSONObject(text) }.getOrNull() ?: return null
        return listOf(
            "text",
            "message",
            "body",
            "title",
            "description",
            "content",
            "displayText",
            "messageText",
            "notification",
            "alert",
            "data",
            "payload"
        ).asSequence()
            .mapNotNull { key ->
                json.opt(key)
                    ?.takeUnless { it == JSONObject.NULL }
                    ?.toString()
                    ?.let(::readableText)
            }
            .firstOrNull()
    }

    private fun cleanPlainText(value: String): String {
        var text = value.replace(Regex("\\\\s+"), " ").trim()
        listOf("Webex Connect Demo Chat", "Webex Connect Demo", "APA91").forEach { marker ->
            val index = text.indexOf(marker)
            if (index > 0) text = text.take(index).trim()
        }
        text = text
            .replace(Regex("[A-Za-z0-9_-]{12,}:APA[0-9A-Za-z_:-]+"), "")
            .replace(Regex("\\\\d{10,}\\\\d{4}-\\\\d{2}-\\\\d{2}T[^\\\\s]+"), " ")
            .trim()
        return text.ifBlank { value.take(180).trim() }
    }
}
"""
    return (
        template
        .replace("__PACKAGE__", args.package)
        .replace("__PUSH_IMPORT__", push_import)
        .replace("__PUSH_FUNCTION__", push_function)
    )


def copy_file(src: Path, dest: Path, force: bool) -> str:
    if not src.exists():
        raise FileNotFoundError(f"Input file does not exist: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return f"kept {dest}"
    shutil.copy2(src, dest)
    return f"copied {src} -> {dest}"


def copy_input_files(args: argparse.Namespace, project_root: Path) -> list[str]:
    messages: list[str] = []
    if args.connect_config:
        messages.append(copy_file(
            args.connect_config,
            project_root / "app/src/main/assets/WebexConnectConfig.properties",
            args.force,
        ))
    expected_provider = expected_provider_config(args.provider)
    if args.provider_config and expected_provider:
        if args.provider_config.name != expected_provider:
            raise ValueError(f"{args.provider} requires {expected_provider}, got {args.provider_config.name}")
        messages.append(copy_file(args.provider_config, project_root / "app" / expected_provider, args.force))
    return messages


def copy_android_icon_assets(project_root: Path, force: bool) -> list[str]:
    skill_root = Path(__file__).resolve().parents[1]
    messages: list[str] = []
    for source_rel, dest_rel in ANDROID_ICON_ASSETS.items():
        messages.append(copy_file(skill_root / source_rel, project_root / dest_rel, force))
    return messages


def has_real_connect_config(project_root: Path) -> bool:
    primary_config = project_root / "app/src/main/assets/WebexConnectConfig.properties"
    legacy_config = project_root / "app/src/main/assets/IMIconnectConfig.properties"
    config = primary_config if primary_config.exists() else legacy_config
    if not config.exists():
        return False
    text = config.read_text(encoding="utf-8", errors="ignore")
    return "appId=" in text and "clientKey=" in text and "<APP_ID>" not in text and "<CLIENT_KEY>" not in text


def has_provider_config(args: argparse.Namespace, project_root: Path) -> bool:
    expected = expected_provider_config(args.provider)
    if not expected:
        return True
    return (project_root / "app" / expected).exists()


def validate_required_inputs(args: argparse.Namespace, project_root: Path) -> None:
    if not (args.strict_inputs or args.build_apk):
        return
    missing: list[str] = []
    if not has_real_connect_config(project_root):
        missing.append("WebexConnectConfig.properties or --app-id/--client-key/--environment")
    if not has_provider_config(args, project_root):
        missing.append(expected_provider_config(args.provider) or "provider config")
    if missing:
        raise ValueError(
            "Cannot build APK until required build-time inputs are present: "
            + ", ".join(missing)
        )


def run_gradle_build(args: argparse.Namespace, project_root: Path) -> int:
    gradlew = project_root / "gradlew"
    executable = str(gradlew) if gradlew.exists() else shutil.which("gradle")
    if not executable:
        print("Gradle wrapper or gradle executable not found; generated project only.", file=sys.stderr)
        return 1
    command = [executable, build_task(args.build_type)]
    print("Running " + " ".join(command))
    return subprocess.run(command, cwd=project_root, text=True).returncode


def main() -> int:
    args = collect_inputs(parse_args())
    project_root = Path(args.project_root).resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    artifacts = module_artifacts(args)
    version = args.version or resolve_sdk_version(artifacts)
    files = build_files(args, version)
    for rel_path, content in files.items():
        print(write_file(project_root / rel_path, content, args.force))
    for message in copy_android_icon_assets(project_root, args.force):
        print(message)
    for message in copy_input_files(args, project_root):
        print(message)
    validate_required_inputs(args, project_root)
    print(f"Resolved Webex Connect Android SDK version: {version}")
    print(f"Capability: {capability_label(args)}")
    print(f"Provider: {args.provider.upper() if includes_push(args) else 'not required'}")
    print(f"Package: {args.package}")
    print(f"Build type: {args.build_type}")
    if args.build_apk:
        return run_gradle_build(args, project_root)
    print("Use --build-apk after tenant/provider config files are present.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exception:
        print(f"Error: {exception}", file=sys.stderr)
        raise SystemExit(2)
