#!/usr/bin/env python3
"""Generate a Webex Connect iOS Push and In-App Messaging demo app."""

from __future__ import annotations

import argparse
import json
import plistlib
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path


DEFAULT_APP_NAME = "Webex Connect Demo"
DEFAULT_BUNDLE_ID = "com.example.webexconnectdemo"
DEFAULT_SDK_VERSION = "3.1.0"
SPM_URL = "https://github.com/webex/wxconnect-ios-sdk"
TARGET_NAME = "WebexConnectDemo"
GENERATED_MARKER = ".webex-connect-ios-builder.json"


@dataclass(frozen=True)
class Options:
    root: Path
    app_name: str
    bundle_id: str
    capability: str
    sdk_version: str
    config_path: Path | None
    app_id: str | None
    client_key: str | None
    environment: str | None
    team_id: str | None
    apns_environment: str
    thread_limit: int
    message_limit: int
    force: bool
    resolve_packages: bool
    build: bool

    @property
    def has_push(self) -> bool:
        return self.capability in {"push", "both"}

    @property
    def has_inapp(self) -> bool:
        return self.capability in {"inapp", "both"}

    @property
    def app_dir(self) -> Path:
        return self.root / TARGET_NAME

    @property
    def project_dir(self) -> Path:
        return self.root / f"{TARGET_NAME}.xcodeproj"


def ask(prompt: str, default: str | None = None) -> str:
    label = f"{prompt}"
    if default:
        label += f" [{default}]"
    label += ": "
    value = input(label).strip()
    return value or (default or "")


def ask_bool(prompt: str, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{suffix}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "true", "1"}


def interactive_args(namespace: argparse.Namespace) -> argparse.Namespace:
    namespace.capability = ask("Capability (push, inapp, both)", namespace.capability or "both")
    namespace.bundle_id = ask("Bundle identifier", namespace.bundle_id or DEFAULT_BUNDLE_ID)
    config = ask("Path to WebexConnectConfig.plist or IMIConnectConfig.plist (optional)", "")
    namespace.config = config or namespace.config
    if not namespace.config:
        namespace.app_id = ask("Webex Connect App ID", namespace.app_id or "")
        namespace.client_key = ask("Webex Connect Client Key", namespace.client_key or "")
        namespace.environment = ask("Webex Connect environment/region", namespace.environment or "")
    if namespace.capability in {"push", "both"}:
        namespace.apns_environment = ask("APNs environment (development, production)", namespace.apns_environment or "development")
    namespace.team_id = ask("Apple Team ID (optional)", namespace.team_id or "")
    namespace.resolve_packages = ask_bool("Resolve SPM packages now", namespace.resolve_packages)
    namespace.build = ask_bool("Run an Xcode build now", namespace.build)
    return namespace


def parse_args(argv: list[str] | None = None) -> Options:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path, help="Directory for the generated iOS app")
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--capability", choices=("push", "inapp", "both"), default="both")
    parser.add_argument("--sdk-version", default=DEFAULT_SDK_VERSION)
    parser.add_argument("--config", type=Path, help="Existing WebexConnectConfig.plist or IMIConnectConfig.plist")
    parser.add_argument("--app-id")
    parser.add_argument("--client-key")
    parser.add_argument("--environment")
    parser.add_argument("--team-id")
    parser.add_argument("--apns-environment", choices=("development", "production"), default="development")
    parser.add_argument("--thread-limit", type=int, default=50)
    parser.add_argument("--message-limit", type=int, default=50)
    parser.add_argument("--interactive", action="store_true", help="Prompt for missing build inputs in a real terminal")
    parser.add_argument("--force", action="store_true", help="Overwrite files from a previous generated app")
    parser.add_argument("--resolve-packages", action="store_true", help="Run xcodebuild -resolvePackageDependencies")
    parser.add_argument("--build", action="store_true", help="Run an unsigned simulator build after generation")
    args = parser.parse_args(argv)
    if args.interactive:
        if not sys.stdin.isatty():
            parser.error("--interactive requires a real TTY")
        args = interactive_args(args)

    if args.thread_limit < 1 or args.message_limit < 1:
        parser.error("--thread-limit and --message-limit must be positive integers")

    return Options(
        root=args.project_root.resolve(),
        app_name=args.app_name,
        bundle_id=args.bundle_id,
        capability=args.capability,
        sdk_version=args.sdk_version,
        config_path=args.config.resolve() if args.config else None,
        app_id=args.app_id,
        client_key=args.client_key,
        environment=args.environment,
        team_id=args.team_id or None,
        apns_environment=args.apns_environment,
        thread_limit=args.thread_limit,
        message_limit=args.message_limit,
        force=args.force,
        resolve_packages=args.resolve_packages,
        build=args.build,
    )


def ensure_can_write(options: Options) -> None:
    options.root.mkdir(parents=True, exist_ok=True)
    marker = options.root / GENERATED_MARKER
    generated_before = marker.is_file()
    existing = [path.name for path in options.root.iterdir() if path.name not in {".DS_Store", GENERATED_MARKER}]
    if existing and not generated_before and not options.force:
        raise SystemExit(
            f"{options.root} is not empty. Use --force only when you intend to write the Webex Connect iOS demo files here."
        )
    options.app_dir.mkdir(parents=True, exist_ok=True)
    options.project_dir.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def copy_logo(options: Options) -> None:
    source = Path(__file__).resolve().parents[1] / "assets" / "webex-icon-400.png"
    imageset = options.app_dir / "Assets.xcassets" / "WebexLogo.imageset"
    imageset.mkdir(parents=True, exist_ok=True)
    if source.is_file():
        shutil.copy2(source, imageset / "webex-icon-400.png")
    write_text(
        imageset / "Contents.json",
        json.dumps(
            {
                "images": [
                    {
                        "filename": "webex-icon-400.png",
                        "idiom": "universal",
                        "scale": "1x",
                    },
                    {"idiom": "universal", "scale": "2x"},
                    {"idiom": "universal", "scale": "3x"},
                ],
                "info": {"author": "xcode", "version": 1},
            },
            indent=2,
        ),
    )
    write_text(
        options.app_dir / "Assets.xcassets" / "AccentColor.colorset" / "Contents.json",
        json.dumps(
            {
                "colors": [
                    {
                        "idiom": "universal",
                        "color": {
                            "color-space": "srgb",
                            "components": {"red": "0x34", "green": "0x92", "blue": "0xEB", "alpha": "1.000"},
                        },
                    }
                ],
                "info": {"author": "xcode", "version": 1},
            },
            indent=2,
        ),
    )
    write_text(
        options.app_dir / "Assets.xcassets" / "Contents.json",
        json.dumps({"info": {"author": "xcode", "version": 1}}, indent=2),
    )


def write_config(options: Options) -> list[str]:
    resources: list[str] = ["Assets.xcassets"]
    if options.config_path:
        if not options.config_path.is_file():
            raise SystemExit(f"Config plist not found: {options.config_path}")
        destination_name = "IMIConnectConfig.plist" if options.config_path.name == "IMIConnectConfig.plist" else "WebexConnectConfig.plist"
        shutil.copy2(options.config_path, options.app_dir / destination_name)
        resources.append(destination_name)
        return resources

    if options.app_id and options.client_key and options.environment:
        payload = {
            "appId": options.app_id,
            "clientKey": options.client_key,
            "environment": options.environment,
        }
        with (options.app_dir / "WebexConnectConfig.plist").open("wb") as handle:
            plistlib.dump(payload, handle, sort_keys=True)
        resources.append("WebexConnectConfig.plist")
    else:
        example = {
            "appId": "YOUR_WEBEX_CONNECT_APP_ID",
            "clientKey": "YOUR_WEBEX_CONNECT_CLIENT_KEY",
            "environment": "YOUR_WEBEX_CONNECT_ENVIRONMENT",
        }
        with (options.app_dir / "WebexConnectConfig.plist.example").open("wb") as handle:
            plistlib.dump(example, handle, sort_keys=True)
    return resources


def swift_conditions(options: Options, debug: bool) -> str:
    values = []
    if debug:
        values.append("DEBUG")
    values.append("WEBEX_CONNECT_CORE")
    if options.has_push:
        values.append("WEBEX_CONNECT_PUSH")
    if options.has_inapp:
        values.append("WEBEX_CONNECT_INAPP")
    return " ".join(values)


class IdFactory:
    def __init__(self) -> None:
        self._used: set[str] = set()

    def get(self, label: str) -> str:
        seed = label
        counter = 0
        while True:
            digest = sha1(f"{seed}:{counter}".encode("utf-8")).hexdigest().upper()[:24]
            if digest not in self._used:
                self._used.add(digest)
                return digest
            counter += 1


def pbx_quote(value: str) -> str:
    if all(ch.isalnum() or ch in "._/$" for ch in value):
        return value
    return json.dumps(value)


def build_file_reference(file_id: str, name: str, file_type: str, path: str | None = None) -> str:
    parts = [f"{file_id} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {file_type};"]
    if path:
        parts.append(f"path = {pbx_quote(path)};")
    else:
        parts.append(f"path = {pbx_quote(name)};")
    parts.append('sourceTree = "<group>"; };')
    return " ".join(parts)


def write_xcode_project(options: Options, resources: list[str]) -> None:
    ids = IdFactory()
    main_group = ids.get("mainGroup")
    app_group = ids.get("appGroup")
    products_group = ids.get("productsGroup")
    target = ids.get("target")
    product = ids.get("product")
    project = ids.get("project")
    sources_phase = ids.get("sourcesPhase")
    frameworks_phase = ids.get("frameworksPhase")
    resources_phase = ids.get("resourcesPhase")
    project_config = ids.get("projectConfigList")
    target_config = ids.get("targetConfigList")
    debug_project = ids.get("debugProject")
    release_project = ids.get("releaseProject")
    debug_target = ids.get("debugTarget")
    release_target = ids.get("releaseTarget")
    package_ref = ids.get("webexPackage")

    source_names = [
        "WebexConnectDemoApp.swift",
        "AppDelegate.swift",
        "DemoModels.swift",
        "MessageRenderer.swift",
        "WebexConnectRuntime.swift",
        "DemoViews.swift",
    ]
    extra_file_names = ["Info.plist"]
    if options.has_push:
        extra_file_names.append("WebexConnectDemo.entitlements")

    file_refs: dict[str, str] = {name: ids.get(f"file:{name}") for name in source_names + resources + extra_file_names}
    source_builds = {name: ids.get(f"build:{name}") for name in source_names}
    resource_builds = {name: ids.get(f"build:{name}") for name in resources}
    products = ["WebexConnectCore"]
    if options.has_push:
        products.append("WebexConnectPush")
    if options.has_inapp:
        products.append("WebexConnectInAppMessaging")
    product_deps = {name: ids.get(f"productDep:{name}") for name in products}
    framework_builds = {name: ids.get(f"frameworkBuild:{name}") for name in products}

    file_ref_lines = [
        f'{product} /* {TARGET_NAME}.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = {TARGET_NAME}.app; sourceTree = BUILT_PRODUCTS_DIR; }};'
    ]
    for name in source_names:
        file_ref_lines.append(build_file_reference(file_refs[name], name, "sourcecode.swift"))
    for name in resources:
        file_type = "folder.assetcatalog" if name.endswith(".xcassets") else "text.plist.xml"
        file_ref_lines.append(build_file_reference(file_refs[name], name, file_type))
    for name in extra_file_names:
        file_type = "text.plist.xml" if name.endswith(".plist") else "text.plist.entitlements"
        file_ref_lines.append(build_file_reference(file_refs[name], name, file_type))

    build_file_lines = []
    for name in source_names:
        build_file_lines.append(f"{source_builds[name]} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_refs[name]} /* {name} */; }};")
    for name in resources:
        build_file_lines.append(f"{resource_builds[name]} /* {name} in Resources */ = {{isa = PBXBuildFile; fileRef = {file_refs[name]} /* {name} */; }};")
    for name in products:
        build_file_lines.append(f"{framework_builds[name]} /* {name} in Frameworks */ = {{isa = PBXBuildFile; productRef = {product_deps[name]} /* {name} */; }};")

    app_group_children = [file_refs[name] for name in source_names + extra_file_names + resources]
    source_build_refs = [source_builds[name] for name in source_names]
    resource_build_refs = [resource_builds[name] for name in resources]
    framework_build_refs = [framework_builds[name] for name in products]
    product_dep_refs = [product_deps[name] for name in products]

    team_setting = f"DEVELOPMENT_TEAM = {options.team_id};" if options.team_id else ""
    entitlements_setting = f"CODE_SIGN_ENTITLEMENTS = {TARGET_NAME}/{TARGET_NAME}.entitlements;" if options.has_push else ""
    debug_conditions = swift_conditions(options, debug=True)
    release_conditions = swift_conditions(options, debug=False)

    pbx = f"""// !$*UTF8*$!
{{
  archiveVersion = 1;
  classes = {{
  }};
  objectVersion = 77;
  objects = {{

/* Begin PBXBuildFile section */
    {chr(10).join('    ' + line for line in build_file_lines)}
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
    {chr(10).join('    ' + line for line in file_ref_lines)}
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
    {frameworks_phase} /* Frameworks */ = {{
      isa = PBXFrameworksBuildPhase;
      buildActionMask = 2147483647;
      files = (
        {','.join(framework_build_refs)}
      );
      runOnlyForDeploymentPostprocessing = 0;
    }};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
    {main_group} = {{
      isa = PBXGroup;
      children = (
        {app_group},
        {products_group},
      );
      sourceTree = "<group>";
    }};
    {app_group} /* {TARGET_NAME} */ = {{
      isa = PBXGroup;
      children = (
        {','.join(app_group_children)}
      );
      path = {TARGET_NAME};
      sourceTree = "<group>";
    }};
    {products_group} /* Products */ = {{
      isa = PBXGroup;
      children = (
        {product} /* {TARGET_NAME}.app */,
      );
      name = Products;
      sourceTree = "<group>";
    }};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
    {target} /* {TARGET_NAME} */ = {{
      isa = PBXNativeTarget;
      buildConfigurationList = {target_config} /* Build configuration list for PBXNativeTarget "{TARGET_NAME}" */;
      buildPhases = (
        {sources_phase},
        {frameworks_phase},
        {resources_phase},
      );
      buildRules = (
      );
      dependencies = (
      );
      name = {TARGET_NAME};
      packageProductDependencies = (
        {','.join(product_dep_refs)}
      );
      productName = {TARGET_NAME};
      productReference = {product} /* {TARGET_NAME}.app */;
      productType = "com.apple.product-type.application";
    }};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
    {project} /* Project object */ = {{
      isa = PBXProject;
      attributes = {{
        BuildIndependentTargetsInParallel = 1;
        LastSwiftUpdateCheck = 2660;
        LastUpgradeCheck = 2660;
        TargetAttributes = {{
          {target} = {{
            CreatedOnToolsVersion = 26.6;
          }};
        }};
      }};
      buildConfigurationList = {project_config} /* Build configuration list for PBXProject "{TARGET_NAME}" */;
      compatibilityVersion = "Xcode 15.0";
      developmentRegion = en;
      hasScannedForEncodings = 0;
      knownRegions = (
        en,
        Base,
      );
      mainGroup = {main_group};
      minimizedProjectReferenceProxies = 1;
      packageReferences = (
        {package_ref} /* XCRemoteSwiftPackageReference "{SPM_URL}" */,
      );
      preferredProjectObjectVersion = 77;
      productRefGroup = {products_group} /* Products */;
      projectDirPath = "";
      projectRoot = "";
      targets = (
        {target} /* {TARGET_NAME} */,
      );
    }};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
    {resources_phase} /* Resources */ = {{
      isa = PBXResourcesBuildPhase;
      buildActionMask = 2147483647;
      files = (
        {','.join(resource_build_refs)}
      );
      runOnlyForDeploymentPostprocessing = 0;
    }};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
    {sources_phase} /* Sources */ = {{
      isa = PBXSourcesBuildPhase;
      buildActionMask = 2147483647;
      files = (
        {','.join(source_build_refs)}
      );
      runOnlyForDeploymentPostprocessing = 0;
    }};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
    {debug_project} /* Debug */ = {{
      isa = XCBuildConfiguration;
      buildSettings = {{
        ALWAYS_SEARCH_USER_PATHS = NO;
        CLANG_ANALYZER_NONNULL = YES;
        CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
        CLANG_ENABLE_MODULES = YES;
        CLANG_ENABLE_OBJC_ARC = YES;
        CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
        GCC_C_LANGUAGE_STANDARD = gnu17;
        IPHONEOS_DEPLOYMENT_TARGET = 16.0;
        SDKROOT = iphoneos;
        SWIFT_VERSION = 5.0;
      }};
      name = Debug;
    }};
    {release_project} /* Release */ = {{
      isa = XCBuildConfiguration;
      buildSettings = {{
        ALWAYS_SEARCH_USER_PATHS = NO;
        CLANG_ANALYZER_NONNULL = YES;
        CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
        CLANG_ENABLE_MODULES = YES;
        CLANG_ENABLE_OBJC_ARC = YES;
        CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
        GCC_C_LANGUAGE_STANDARD = gnu17;
        IPHONEOS_DEPLOYMENT_TARGET = 16.0;
        SDKROOT = iphoneos;
        SWIFT_COMPILATION_MODE = wholemodule;
        SWIFT_VERSION = 5.0;
      }};
      name = Release;
    }};
    {debug_target} /* Debug */ = {{
      isa = XCBuildConfiguration;
      buildSettings = {{
        ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
        CODE_SIGN_STYLE = Automatic;
        {entitlements_setting}
        {team_setting}
        INFOPLIST_FILE = {TARGET_NAME}/Info.plist;
        PRODUCT_BUNDLE_IDENTIFIER = {pbx_quote(options.bundle_id)};
        PRODUCT_NAME = "$(TARGET_NAME)";
        SWIFT_ACTIVE_COMPILATION_CONDITIONS = "{debug_conditions}";
        SWIFT_VERSION = 5.0;
        TARGETED_DEVICE_FAMILY = "1,2";
      }};
      name = Debug;
    }};
    {release_target} /* Release */ = {{
      isa = XCBuildConfiguration;
      buildSettings = {{
        ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
        CODE_SIGN_STYLE = Automatic;
        {entitlements_setting}
        {team_setting}
        INFOPLIST_FILE = {TARGET_NAME}/Info.plist;
        PRODUCT_BUNDLE_IDENTIFIER = {pbx_quote(options.bundle_id)};
        PRODUCT_NAME = "$(TARGET_NAME)";
        SWIFT_ACTIVE_COMPILATION_CONDITIONS = "{release_conditions}";
        SWIFT_VERSION = 5.0;
        TARGETED_DEVICE_FAMILY = "1,2";
      }};
      name = Release;
    }};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
    {project_config} /* Build configuration list for PBXProject "{TARGET_NAME}" */ = {{
      isa = XCConfigurationList;
      buildConfigurations = (
        {debug_project} /* Debug */,
        {release_project} /* Release */,
      );
      defaultConfigurationIsVisible = 0;
      defaultConfigurationName = Release;
    }};
    {target_config} /* Build configuration list for PBXNativeTarget "{TARGET_NAME}" */ = {{
      isa = XCConfigurationList;
      buildConfigurations = (
        {debug_target} /* Debug */,
        {release_target} /* Release */,
      );
      defaultConfigurationIsVisible = 0;
      defaultConfigurationName = Release;
    }};
/* End XCConfigurationList section */

/* Begin XCRemoteSwiftPackageReference section */
    {package_ref} /* XCRemoteSwiftPackageReference "{SPM_URL}" */ = {{
      isa = XCRemoteSwiftPackageReference;
      repositoryURL = "{SPM_URL}";
      requirement = {{
        kind = exactVersion;
        version = {options.sdk_version};
      }};
    }};
/* End XCRemoteSwiftPackageReference section */

/* Begin XCSwiftPackageProductDependency section */
    {chr(10).join('    ' + f'{product_deps[name]} /* {name} */ = {{isa = XCSwiftPackageProductDependency; package = {package_ref} /* XCRemoteSwiftPackageReference "{SPM_URL}" */; productName = {name}; }};' for name in products)}
/* End XCSwiftPackageProductDependency section */
  }};
  rootObject = {project} /* Project object */;
}}
"""
    write_text(options.project_dir / "project.pbxproj", pbx)
    write_text(options.project_dir / "project.xcworkspace" / "contents.xcworkspacedata", workspace_data())
    write_text(options.project_dir / "xcshareddata" / "xcschemes" / f"{TARGET_NAME}.xcscheme", xcode_scheme(target))


def workspace_data() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Workspace
   version = "1.0">
   <FileRef
      location = "self:">
   </FileRef>
</Workspace>"""


def xcode_scheme(target_id: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "2660"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES"
      buildArchitectures = "Automatic">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "{target_id}"
               BuildableName = "{TARGET_NAME}.app"
               BlueprintName = "{TARGET_NAME}"
               ReferencedContainer = "container:{TARGET_NAME}.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "{target_id}"
            BuildableName = "{TARGET_NAME}.app"
            BlueprintName = "{TARGET_NAME}"
            ReferencedContainer = "container:{TARGET_NAME}.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
</Scheme>"""


def write_package_swift(options: Options) -> None:
    products = ['"WebexConnectCore"']
    conditions = ['"WEBEX_CONNECT_CORE"']
    if options.has_push:
        products.append('"WebexConnectPush"')
        conditions.append('"WEBEX_CONNECT_PUSH"')
    if options.has_inapp:
        products.append('"WebexConnectInAppMessaging"')
        conditions.append('"WEBEX_CONNECT_INAPP"')

    product_dependencies = ",\n        ".join(
        f'.product(name: {name}, package: "wxconnect-ios-sdk")' for name in products
    )
    conditions_swift = ", ".join(conditions)
    write_text(
        options.root / "Package.swift",
        f"""// swift-tools-version: 5.9
import PackageDescription

let package = Package(
  name: "{TARGET_NAME}",
  defaultLocalization: "en",
  platforms: [.iOS(.v16)],
  products: [
    .library(name: "{TARGET_NAME}Support", targets: ["{TARGET_NAME}Support"])
  ],
  dependencies: [
    .package(url: "{SPM_URL}", exact: "{options.sdk_version}")
  ],
  targets: [
    .target(
      name: "{TARGET_NAME}Support",
      dependencies: [
        {product_dependencies}
      ],
      swiftSettings: [
        .define("WEBEX_CONNECT_GENERATED_PACKAGE"),
        {', '.join(f'.define({condition})' for condition in conditions)}
      ]
    )
  ]
)

// The generated Xcode project is the runnable iOS app target. This manifest is
// included so SPM dependency choices are visible, auditable, and reusable when
// moving the generated support code into an existing application.
""",
    )
    support_imports = ["#if WEBEX_CONNECT_CORE\n@_exported import WebexConnectCore\n#endif"]
    if options.has_push:
        support_imports.append("#if WEBEX_CONNECT_PUSH\n@_exported import WebexConnectPush\n#endif")
    if options.has_inapp:
        support_imports.append("#if WEBEX_CONNECT_INAPP\n@_exported import WebexConnectInAppMessaging\n#endif")
    write_text(
        options.root / "Sources" / f"{TARGET_NAME}Support" / f"{TARGET_NAME}Support.swift",
        f"""import Foundation
{chr(10).join(support_imports)}

public enum WebexConnectDemoSupportPackage {{
  public static let sdkVersion = "{options.sdk_version}"
  public static let packageRepository = "{SPM_URL}"
}}
""",
    )


def write_info_plist(options: Options) -> None:
    plist: dict[str, object] = {
        "CFBundleDevelopmentRegion": "$(DEVELOPMENT_LANGUAGE)",
        "CFBundleExecutable": "$(EXECUTABLE_NAME)",
        "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "$(PRODUCT_NAME)",
        "CFBundlePackageType": "$(PRODUCT_BUNDLE_PACKAGE_TYPE)",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1",
        "LSRequiresIPhoneOS": True,
        "UIApplicationSupportsIndirectInputEvents": True,
        "UILaunchScreen": {},
        "UISupportedInterfaceOrientations": ["UIInterfaceOrientationPortrait"],
        "UISupportedInterfaceOrientations~ipad": [
            "UIInterfaceOrientationPortrait",
            "UIInterfaceOrientationPortraitUpsideDown",
            "UIInterfaceOrientationLandscapeLeft",
            "UIInterfaceOrientationLandscapeRight",
        ],
        "NSPhotoLibraryUsageDescription": "Select media to attach to Webex Connect in-app messages.",
        "NSCameraUsageDescription": "Capture media to attach to Webex Connect in-app messages.",
        "NSMicrophoneUsageDescription": "Record audio to attach to Webex Connect in-app messages.",
        "NSLocationWhenInUseUsageDescription": "Attach location when a Webex Connect message requests it.",
    }
    if options.has_push:
        plist["UIBackgroundModes"] = ["fetch", "remote-notification"]
    with (options.app_dir / "Info.plist").open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=True)


def write_entitlements(options: Options) -> None:
    if not options.has_push:
        return
    with (options.app_dir / f"{TARGET_NAME}.entitlements").open("wb") as handle:
        plistlib.dump({"aps-environment": options.apns_environment}, handle, sort_keys=True)


def template_app(options: Options) -> str:
    app_delegate = '@UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate\n  ' if options.has_push else ""
    return f"""
import SwiftUI

@main
struct WebexConnectDemoApp: App {{
  {app_delegate}@StateObject private var runtime = WebexConnectRuntime.shared

  var body: some Scene {{
    WindowGroup {{
      RootAppView()
        .environmentObject(runtime)
        .task {{
          await runtime.bootstrap()
        }}
    }}
  }}
}}
"""


def template_app_delegate(options: Options) -> str:
    if not options.has_push:
        return r"""
import UIKit

final class AppDelegate: NSObject, UIApplicationDelegate {
  func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
  ) -> Bool {
    true
  }
}
"""
    return r"""
import UIKit
import UserNotifications
#if WEBEX_CONNECT_PUSH
import WebexConnectPush
#endif

final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
  func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
  ) -> Bool {
    UNUserNotificationCenter.current().delegate = self
    return true
  }

  func application(
    _ application: UIApplication,
    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
  ) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    Task { @MainActor in
      WebexConnectRuntime.shared.apnsToken = token
      WebexConnectRuntime.shared.lastStatus = "APNs token received"
    }
    #if WEBEX_CONNECT_PUSH
    PushMessagingProvider.instance.processPushToken(token, type: .apns) { error in
      Task { @MainActor in
        WebexConnectRuntime.shared.lastStatus = error == nil
          ? "APNs token registered with Webex Connect"
          : "APNs token registration failed: \(error!.localizedDescription)"
      }
    }
    #endif
  }

  func application(
    _ application: UIApplication,
    didFailToRegisterForRemoteNotificationsWithError error: Error
  ) {
    Task { @MainActor in
      WebexConnectRuntime.shared.lastStatus = "APNs registration failed: \(error.localizedDescription)"
    }
  }

  func application(
    _ application: UIApplication,
    didReceiveRemoteNotification userInfo: [AnyHashable: Any],
    fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
  ) {
    Task { @MainActor in
      WebexConnectRuntime.shared.recordForegroundPush(userInfo)
    }
    completionHandler(.noData)
  }

  func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    willPresent notification: UNNotification,
    withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
  ) {
    Task { @MainActor in
      WebexConnectRuntime.shared.recordForegroundPush(notification.request.content.userInfo)
    }
    completionHandler([.banner, .list, .sound, .badge])
  }

  func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    didReceive response: UNNotificationResponse,
    withCompletionHandler completionHandler: @escaping () -> Void
  ) {
    Task { @MainActor in
      WebexConnectRuntime.shared.recordPushAction(response.notification.request.content.userInfo)
    }
    completionHandler()
  }
}
"""


def template_models() -> str:
    return """
import Foundation

enum AppTab: String, CaseIterable, Identifiable {
  case shop
  case orders
  case support
  case profile

  var id: String { rawValue }

  var title: String {
    switch self {
    case .shop: "Shop"
    case .orders: "Orders"
    case .support: "Support"
    case .profile: "Profile"
    }
  }

  var icon: String {
    switch self {
    case .shop: "house.fill"
    case .orders: "shippingbox.fill"
    case .support: "headphones"
    case .profile: "person.fill"
    }
  }
}

enum ConversationStatus: String {
  case active
  case inactive
  case closed
  case announcement
  case connecting

  var label: String {
    switch self {
    case .active: "Active"
    case .inactive: "Inactive"
    case .closed: "Thread closed"
    case .announcement: "Announcement"
    case .connecting: "Connecting"
    }
  }
}

struct ConversationThread: Identifiable {
  var id: String
  var title: String
  var preview: String
  var updatedAt: Date
  var unreadCount: Int
  var status: ConversationStatus
  var isConversation: Bool
  var sdkThread: Any?

  var canPublish: Bool {
    isConversation && status != .closed && status != .announcement
  }
}

enum MessageDirection: String {
  case user
  case agent
  case system
}

enum MessageStatus: String {
  case queued
  case sent
  case delivered
  case read
  case failed
  case none

  var label: String {
    switch self {
    case .queued: "Sending"
    case .sent: "Sent"
    case .delivered: "Delivered"
    case .read: "Read"
    case .failed: "Failed"
    case .none: ""
    }
  }

  var rank: Int {
    switch self {
    case .none: 0
    case .queued: 1
    case .failed: 1
    case .sent: 2
    case .delivered: 3
    case .read: 4
    }
  }
}

enum MessageKind: String {
  case text
  case alert
  case carousel
  case cards
  case form
  case attachment
  case quickReplies
  case typing
  case status
}

struct MessageAttachment: Identifiable {
  var id = UUID().uuidString
  var name: String
  var contentType: String
  var url: URL?
  var thumbnailUrl: URL?
  var duration: String?
}

struct RichCard: Identifiable {
  var id = UUID().uuidString
  var title: String
  var subtitle: String
  var imageUrl: URL?
  var price: String?
  var actions: [QuickReplyAction]
  var isComplete: Bool
}

struct QuickReplyAction: Identifiable {
  var id = UUID().uuidString
  var title: String
  var postbackData: String
  var isComplete: Bool
}

struct FormField: Identifiable {
  var id = UUID().uuidString
  var key: String
  var title: String
  var placeholder: String
  var required: Bool
  var value: String = ""
}

struct FormTemplate: Identifiable {
  var id = UUID().uuidString
  var title: String
  var fields: [FormField]
  var submitTitle: String
  var postbackData: String
  var isComplete: Bool
}

struct ChatMessage: Identifiable {
  var id: String
  var threadId: String
  var transactionId: String?
  var relatedTransactionId: String?
  var direction: MessageDirection
  var kind: MessageKind
  var text: String
  var createdAt: Date
  var status: MessageStatus
  var attachments: [MessageAttachment]
  var cards: [RichCard]
  var quickReplies: [QuickReplyAction]
  var form: FormTemplate?
  var sdkMessage: Any?

  var isUserMessage: Bool { direction == .user }
  var isReceiptOnly: Bool { kind == .status }
}

struct PushNotificationRow: Identifiable {
  var id = UUID().uuidString
  var title: String
  var body: String
  var receivedAt: Date
}
"""


def template_renderer() -> str:
    return r"""
import Foundation
#if WEBEX_CONNECT_INAPP
import WebexConnectInAppMessaging
#endif

struct MessageRenderer {
  func compactThreadId(_ threadId: String) -> String {
    guard threadId.count > 14 else { return threadId }
    return "\(threadId.prefix(8))...\(threadId.suffix(6))"
  }

  #if WEBEX_CONNECT_INAPP
  func renderThread(_ sdkThread: InAppThread) -> ConversationThread {
    let id = firstString(from: sdkThread, keys: ["threadId", "id", "uid"]) ?? UUID().uuidString
    let title = firstString(from: sdkThread, keys: ["title", "threadTitle", "name"]).flatMap(cleanText) ?? "Webex Connect Demo Chat"
    let preview = firstString(from: sdkThread, keys: ["preview", "lastMessage", "lastMessageText"]).flatMap(cleanText) ?? "Demo support conversation"
    let unread = firstInt(from: sdkThread, keys: ["unreadCount", "unreadMessageCount"]) ?? 0
    let statusText = firstString(from: sdkThread, keys: ["status", "threadStatus"]).map { $0.lowercased() } ?? "active"
    let typeText = firstString(from: sdkThread, keys: ["type", "threadType"]).map { $0.lowercased() } ?? "conversation"
    let status: ConversationStatus
    if typeText.contains("announcement") {
      status = .announcement
    } else if statusText.contains("closed") {
      status = .closed
    } else if statusText.contains("inactive") {
      status = .inactive
    } else {
      status = .active
    }
    return ConversationThread(
      id: id,
      title: title,
      preview: preview,
      updatedAt: firstDate(from: sdkThread, keys: ["updatedAt", "lastUpdatedAt", "createdAt"]) ?? Date(),
      unreadCount: unread,
      status: status,
      isConversation: !typeText.contains("announcement"),
      sdkThread: sdkThread
    )
  }

  func renderInAppMessage(_ sdkMessage: InAppMessage, currentUserId: String?) -> ChatMessage? {
    if isReceipt(sdkMessage) {
      return ChatMessage(
        id: messageIdentity(sdkMessage),
        threadId: threadId(from: sdkMessage),
        transactionId: firstString(from: sdkMessage, keys: ["transactionId", "messageId", "id"]),
        relatedTransactionId: firstString(from: sdkMessage, keys: ["relatedTransactionId", "relatedMessageId", "referenceTransactionId"]),
        direction: .system,
        kind: .status,
        text: "",
        createdAt: messageDate(sdkMessage),
        status: status(from: sdkMessage),
        attachments: [],
        cards: [],
        quickReplies: [],
        form: nil,
        sdkMessage: sdkMessage
      )
    }

    return ChatMessage(
      id: messageIdentity(sdkMessage),
      threadId: threadId(from: sdkMessage),
      transactionId: firstString(from: sdkMessage, keys: ["transactionId", "messageId", "id"]),
      relatedTransactionId: firstString(from: sdkMessage, keys: ["relatedTransactionId", "relatedMessageId", "referenceTransactionId"]),
      direction: messageDirection(sdkMessage, currentUserId: currentUserId),
      kind: messageKind(sdkMessage),
      text: customerText(from: sdkMessage),
      createdAt: messageDate(sdkMessage),
      status: status(from: sdkMessage),
      attachments: renderAttachments(sdkMessage),
      cards: renderCards(sdkMessage),
      quickReplies: renderQuickReplies(sdkMessage),
      form: renderForm(sdkMessage),
      sdkMessage: sdkMessage
    )
  }
  #endif

  func localOutgoing(threadId: String, text: String) -> ChatMessage {
    ChatMessage(
      id: "local-\(UUID().uuidString)",
      threadId: threadId,
      transactionId: nil,
      relatedTransactionId: nil,
      direction: .user,
      kind: .text,
      text: cleanText(text) ?? text,
      createdAt: Date(),
      status: .queued,
      attachments: [],
      cards: [],
      quickReplies: [],
      form: nil,
      sdkMessage: nil
    )
  }

  #if WEBEX_CONNECT_INAPP
  func messageIdentity(_ sdkMessage: InAppMessage) -> String {
    if let explicitId = firstString(from: sdkMessage, keys: ["messageId", "transactionId", "id", "uid"]),
       !explicitId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
      return explicitId
    }
    let type = firstString(from: sdkMessage, keys: ["type", "messageType", "eventType"]) ?? "message"
    let dateMillis = Int64((firstDate(from: sdkMessage, keys: ["submittedAt", "createdAt", "timestamp", "receivedAt"])?.timeIntervalSince1970 ?? 0) * 1000)
    let seed = [
      threadId(from: sdkMessage),
      type,
      "\(dateMillis)",
      customerText(from: sdkMessage).prefix(96).description
    ].joined(separator: "|")
    let checksum = seed.utf8.reduce(UInt64(5381)) { (($0 << 5) &+ $0) &+ UInt64($1) }
    return "sdk-\(checksum)"
  }

  func threadId(from sdkMessage: InAppMessage) -> String {
    if let direct = firstString(from: sdkMessage, keys: ["threadId"]) {
      return direct
    }
    if let thread = firstValue(from: sdkMessage, keys: ["thread"]) {
      return firstString(from: thread, keys: ["threadId", "id", "uid"]) ?? ""
    }
    return ""
  }

  func isReceipt(_ sdkMessage: InAppMessage) -> Bool {
    let type = firstString(from: sdkMessage, keys: ["type", "messageType", "eventType"])?.lowercased() ?? ""
    let status = firstString(from: sdkMessage, keys: ["status", "messageStatus"])?.lowercased() ?? ""
    return type.contains("receipt")
      || type.contains("delivered")
      || type.contains("read")
      || type.contains("clicked")
      || type.contains("deleted")
      || ["delivered", "read", "clicked", "deleted"].contains(status)
  }

  func messageDirection(_ sdkMessage: InAppMessage, currentUserId: String?) -> MessageDirection {
    let type = firstString(from: sdkMessage, keys: ["type", "messageType", "eventType"])?.lowercased() ?? ""
    if type.contains("alert") || type.contains("thread") || type.contains("typing") {
      return .agent
    }

    let source = firstString(from: sdkMessage, keys: ["source", "senderType", "direction"])?.lowercased() ?? ""
    if source.contains("agent") || source.contains("bot") || source.contains("system") || source.contains("platform") {
      return .agent
    }
    if source.contains("user") || source.contains("customer") || source.contains("outgoing") {
      return .user
    }
    if let outgoing = firstBool(from: sdkMessage, keys: ["isOutgoing", "outgoing"]), outgoing {
      return .user
    }
    let senderId = firstString(from: sdkMessage, keys: ["senderId", "from", "createdBy"])
    if let currentUserId, let senderId, senderId.caseInsensitiveCompare(currentUserId) == .orderedSame {
      return .user
    }
    return .agent
  }

  func messageKind(_ sdkMessage: InAppMessage) -> MessageKind {
    let type = firstString(from: sdkMessage, keys: ["type", "messageType", "eventType"])?.lowercased() ?? ""
    if type.contains("typing") { return .typing }
    if type.contains("alert") || type.contains("thread") { return .alert }
    if renderForm(sdkMessage) != nil { return .form }
    if !renderCards(sdkMessage).isEmpty { return .carousel }
    if !renderAttachments(sdkMessage).isEmpty { return .attachment }
    if !renderQuickReplies(sdkMessage).isEmpty { return .quickReplies }
    return .text
  }

  func status(from sdkMessage: InAppMessage) -> MessageStatus {
    let raw = firstString(from: sdkMessage, keys: ["status", "messageStatus", "deliveryStatus"])?.lowercased() ?? ""
    if raw.contains("read") { return .read }
    if raw.contains("delivered") { return .delivered }
    if raw.contains("sent") || raw.contains("submitted") { return .sent }
    if raw.contains("failed") { return .failed }
    return .none
  }

  func messageDate(_ sdkMessage: InAppMessage) -> Date {
    firstDate(from: sdkMessage, keys: ["submittedAt", "createdAt", "timestamp", "receivedAt"]) ?? Date()
  }

  func customerText(from sdkMessage: InAppMessage) -> String {
    let text = firstString(from: sdkMessage, keys: ["message", "text", "body", "title"]).flatMap(cleanText)
    if let text, !looksLikeRawDiagnostic(text) {
      return text
    }
    let alert = firstString(from: sdkMessage, keys: ["alert", "subtitle", "summary"]).flatMap(cleanText)
    if let alert, !looksLikeRawDiagnostic(alert) {
      return alert
    }
    return ""
  }

  func renderAttachments(_ sdkMessage: InAppMessage) -> [MessageAttachment] {
    arrayValue(from: sdkMessage, keys: ["attachments", "media", "files"]).compactMap { item in
      if item is InAppTemplateAttachment {
        return nil
      }
      return MessageAttachment(
        name: firstString(from: item, keys: ["name", "fileName", "title"]) ?? "Attachment",
        contentType: firstString(from: item, keys: ["contentType", "mimeType", "type"]) ?? "file",
        url: firstURL(from: item, keys: ["url", "mediaUrl", "downloadUrl"]),
        thumbnailUrl: firstURL(from: item, keys: ["thumbnailUrl", "previewUrl"]),
        duration: firstString(from: item, keys: ["duration"])
      )
    }
  }

  func renderCards(_ sdkMessage: InAppMessage) -> [RichCard] {
    let directItems = arrayValue(from: sdkMessage, keys: ["cards", "elements", "items"])
    let templateItems = arrayValue(from: sdkMessage, keys: ["attachments"]).flatMap { item -> [Any] in
      guard let template = item as? InAppGenericTemplateAttachment else { return [] }
      return template.elements ?? []
    }
    return (directItems + templateItems).map { item in
      RichCard(
        title: firstString(from: item, keys: ["title", "name"]) ?? "Card",
        subtitle: firstString(from: item, keys: ["subTitle", "subtitle", "description", "body"]) ?? "",
        imageUrl: firstURL(from: item, keys: ["imageUrl", "image", "mediaUrl"])
          ?? firstImageUrl(from: item),
        price: firstString(from: item, keys: ["price"]),
        actions: renderQuickReplies(item),
        isComplete: firstBool(from: item, keys: ["isComplete", "completed", "disabled"]) ?? false
      )
    }
  }

  func firstImageUrl(from object: Any) -> URL? {
    let values = arrayValue(from: object, keys: ["imageURLs", "imageUrls", "images"])
    for value in values {
      if let url = value as? URL { return url }
      if let string = value as? String, let url = URL(string: string) { return url }
    }
    return nil
  }

  func renderQuickReplies(_ object: Any) -> [QuickReplyAction] {
    var candidates = arrayValue(from: object, keys: ["quickReplies", "replies", "buttons", "actions"])
    if let quickReply = firstValue(from: object, keys: ["quickReply"]) {
      candidates.append(contentsOf: arrayValue(from: quickReply, keys: ["buttons"]))
    }
    return candidates.compactMap { item in
      let title = firstString(from: item, keys: ["title", "label", "text"])
      guard let title, !title.isEmpty else { return nil }
      return QuickReplyAction(
        title: title,
        postbackData: firstString(from: item, keys: ["postbackData", "payload", "id"]) ?? title,
        isComplete: firstBool(from: item, keys: ["isComplete", "completed", "disabled"]) ?? false
      )
    }
  }

  func renderForm(_ sdkMessage: InAppMessage) -> FormTemplate? {
    let directForm = firstValue(from: sdkMessage, keys: ["form", "formTemplate", "template"])
    let attachmentForm = arrayValue(from: sdkMessage, keys: ["attachments"]).first { item in
      item is InAppFormTemplateAttachment
    }
    guard let form = directForm ?? attachmentForm else {
      return nil
    }
    let fields = arrayValue(from: form, keys: ["fields", "inputs", "formFields"]).map { item in
      FormField(
        key: firstString(from: item, keys: ["key", "name", "id"]) ?? UUID().uuidString,
        title: firstString(from: item, keys: ["title", "label", "name"]) ?? "Field",
        placeholder: firstString(from: item, keys: ["placeholder", "hint", "fieldDescription"]) ?? "",
        required: firstBool(from: item, keys: ["required", "isRequired", "isMandatory"]) ?? false
      )
    }
    guard !fields.isEmpty else { return nil }
    return FormTemplate(
      title: firstString(from: form, keys: ["formTitle", "title", "name"]) ?? "Form",
      fields: fields,
      submitTitle: firstString(from: form, keys: ["submitTitle", "buttonTitle"]) ?? "Submit",
      postbackData: firstString(from: form, keys: ["postbackData", "payload"]) ?? "submit",
      isComplete: firstBool(from: form, keys: ["isComplete", "completed", "disabled"]) ?? false
    )
  }
  #endif

  func cleanText(_ raw: String) -> String? {
    let value = raw.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !value.isEmpty else { return nil }
    if looksLikeRawDiagnostic(value) { return nil }
    return value
  }

  func looksLikeRawDiagnostic(_ value: String) -> Bool {
    let lowered = value.lowercased()
    return lowered.contains("transactionid")
      || lowered.contains("apns")
      || lowered.contains("pushtoken")
      || lowered.contains("callbackdata")
      || (value.hasPrefix("{") && value.hasSuffix("}"))
      || (value.hasPrefix("[") && value.hasSuffix("]"))
  }

  func firstValue(from object: Any, keys: [String]) -> Any? {
    let mirror = Mirror(reflecting: object)
    for child in mirror.children {
      guard let label = child.label else { continue }
      if keys.contains(where: { $0.caseInsensitiveCompare(label) == .orderedSame }) {
        return child.value
      }
    }
    if let nsObject = object as? NSObject {
      for key in keys {
        if nsObject.responds(to: NSSelectorFromString(key)),
           let value = nsObject.value(forKey: key),
           !(value is NSNull) {
          return value
        }
      }
    }
    return nil
  }

  func firstString(from object: Any, keys: [String]) -> String? {
    guard let value = firstValue(from: object, keys: keys) else { return nil }
    if let string = value as? String {
      return string
    }
    if let custom = value as? CustomStringConvertible {
      return custom.description
    }
    return nil
  }

  func firstInt(from object: Any, keys: [String]) -> Int? {
    guard let value = firstValue(from: object, keys: keys) else { return nil }
    if let int = value as? Int { return int }
    if let number = value as? NSNumber { return number.intValue }
    if let string = value as? String { return Int(string) }
    return nil
  }

  func firstBool(from object: Any, keys: [String]) -> Bool? {
    guard let value = firstValue(from: object, keys: keys) else { return nil }
    if let bool = value as? Bool { return bool }
    if let number = value as? NSNumber { return number.boolValue }
    if let string = value as? String { return ["true", "yes", "1"].contains(string.lowercased()) }
    return nil
  }

  func firstDate(from object: Any, keys: [String]) -> Date? {
    guard let value = firstValue(from: object, keys: keys) else { return nil }
    if let date = value as? Date { return date }
    if let number = value as? NSNumber { return Date(timeIntervalSince1970: number.doubleValue / 1000.0) }
    if let string = value as? String { return ISO8601DateFormatter().date(from: string) }
    return nil
  }

  func firstURL(from object: Any, keys: [String]) -> URL? {
    guard let string = firstString(from: object, keys: keys) else { return nil }
    return URL(string: string)
  }

  func arrayValue(from object: Any, keys: [String]) -> [Any] {
    guard let value = firstValue(from: object, keys: keys) else { return [] }
    if let array = value as? [Any] { return array }
    if let set = value as? Set<AnyHashable> { return set.map { $0 as Any } }
    return []
  }
}
"""


def template_runtime(options: Options) -> str:
    return f"""
import Foundation
import SwiftUI
import UIKit
#if WEBEX_CONNECT_CORE
import WebexConnectCore
#endif
#if WEBEX_CONNECT_PUSH
import UserNotifications
import WebexConnectPush
#endif
#if WEBEX_CONNECT_INAPP
import WebexConnectInAppMessaging
#endif

@MainActor
final class WebexConnectRuntime: NSObject, ObservableObject {{
  static let shared = WebexConnectRuntime()

  @Published var selectedTab: AppTab = .shop
  @Published var currentUserId: String = UserDefaults.standard.string(forKey: "webex.currentUserId") ?? ""
  @Published var customerId: String = UserDefaults.standard.string(forKey: "webex.customerId") ?? ""
  @Published var isConfigured: Bool = false
  @Published var isStarted: Bool = false
  @Published var isRegistered: Bool = false
  @Published var isConnected: Bool = false
  @Published var appId: String = "{options.app_id or ''}"
  @Published var sdkVersion: String = "{options.sdk_version}"
  @Published var apnsToken: String = "pending"
  @Published var lastStatus: String = "Waiting for startup"
  @Published var threadLimit: Int = UserDefaults.standard.integer(forKey: "webex.threadLimit") > 0 ? UserDefaults.standard.integer(forKey: "webex.threadLimit") : {options.thread_limit}
  @Published var messageLimit: Int = UserDefaults.standard.integer(forKey: "webex.messageLimit") > 0 ? UserDefaults.standard.integer(forKey: "webex.messageLimit") : {options.message_limit}
  @Published var threads: [ConversationThread] = []
  @Published var messagesByThread: [String: [ChatMessage]] = [:]
  @Published var visibleThreadId: String?
  @Published var selectedThread: ConversationThread?
  @Published var pushNotifications: [PushNotificationRow] = []
  @Published var isCreatingThread = false
  @Published var isLoadingThreads = false
  @Published var isLoadingMessages = false

  let renderer = MessageRenderer()
  private var pendingOutgoing: [String: String] = [:]
  private var pendingMessageRefreshTasks: [String: Task<Void, Never>] = [:]

  private override init() {{
    super.init()
  }}

  func bootstrap() async {{
    loadConfigSummary()
    guard isConfigured else {{
      lastStatus = "Add WebexConnectConfig.plist in the app target"
      return
    }}
    startCoreIfNeeded()
    if !currentUserId.isEmpty {{
      registerCurrentUser()
    }}
  }}

  func loadConfigSummary() {{
    let bundle = Bundle.main
    let configUrl = bundle.url(forResource: "WebexConnectConfig", withExtension: "plist")
      ?? bundle.url(forResource: "IMIConnectConfig", withExtension: "plist")
    isConfigured = configUrl != nil
    guard let configUrl, let payload = NSDictionary(contentsOf: configUrl) as? [String: Any] else {{
      return
    }}
    appId = payload["appId"] as? String ?? payload["appID"] as? String ?? appId
  }}

  func updateSyncLimits(threadLimit: Int, messageLimit: Int) {{
    self.threadLimit = max(threadLimit, 1)
    self.messageLimit = max(messageLimit, 1)
    UserDefaults.standard.set(self.threadLimit, forKey: "webex.threadLimit")
    UserDefaults.standard.set(self.messageLimit, forKey: "webex.messageLimit")
    configureInAppStore()
    lastStatus = "Local message store and sync policy configured"
  }}

  func copyToClipboard(_ value: String) {{
    UIPasteboard.general.string = value
    lastStatus = "Copied"
  }}

  func registerUser(_ userId: String) {{
    currentUserId = userId.trimmingCharacters(in: .whitespacesAndNewlines)
    UserDefaults.standard.set(currentUserId, forKey: "webex.currentUserId")
    registerCurrentUser()
  }}

  func updateCustomerId(_ customerId: String) {{
    self.customerId = customerId.trimmingCharacters(in: .whitespacesAndNewlines)
    UserDefaults.standard.set(self.customerId, forKey: "webex.customerId")
    lastStatus = "Customer ID updated"
  }}

  func startCoreIfNeeded() {{
    #if WEBEX_CONNECT_CORE
    startCoreIfNeeded(afterStart: nil)
    #else
    lastStatus = "Webex Connect Core product is not enabled"
    #endif
  }}

  func startCoreIfNeeded(afterStart: (() -> Void)? = nil) {{
    #if WEBEX_CONNECT_CORE
    guard !isStarted else {{
      afterStart?()
      return
    }}
    WebexConnectProvider.instance.startup {{ [weak self] error in
      Task {{ @MainActor in
        if let error {{
          self?.isStarted = false
          self?.lastStatus = "Core startup failed: \\(error.localizedDescription)"
          return
        }}
        self?.isStarted = true
        self?.isRegistered = WebexConnectProvider.instance.isRegistered
        self?.sdkVersion = WebexConnectProvider.instance.sdkVersion
        self?.lastStatus = "Webex Connect core started"
        self?.configurePushIfNeeded()
        self?.configureInAppStore()
        afterStart?()
      }}
    }}
    #else
    lastStatus = "Webex Connect Core product is not enabled"
    #endif
  }}

  func registerCurrentUser() {{
    guard isConfigured else {{
      lastStatus = "Configuration required before registration"
      return
    }}
    guard !currentUserId.isEmpty else {{
      lastStatus = "Enter a User ID to register this device"
      return
    }}
    startCoreIfNeeded {{ [weak self] in
      self?.registerDeviceProfile()
    }}
  }}

  private func registerDeviceProfile() {{
    #if WEBEX_CONNECT_CORE
    let deviceId = DeviceProfile.defaultDeviceId()
    let profile = DeviceProfile(deviceId: deviceId, userId: currentUserId)
    WebexConnectProvider.instance.register(deviceProfile: profile) {{ [weak self] _, error in
      Task {{ @MainActor in
        if let error {{
          self?.isRegistered = false
          self?.lastStatus = "Registration failed: \\(error.localizedDescription)"
          return
        }}
        self?.isRegistered = true
        self?.lastStatus = "Device registered"
        self?.connectInAppIfNeeded()
      }}
    }}
    #endif
  }}

  func unregisterUser() {{
    visibleThreadId = nil
    selectedThread = nil
    threads = []
    messagesByThread = [:]
    pendingMessageRefreshTasks.values.forEach {{ $0.cancel() }}
    pendingMessageRefreshTasks.removeAll()
    pendingOutgoing.removeAll()
    #if WEBEX_CONNECT_INAPP
    try? InAppMessagingProvider.instance.disconnect()
    #endif
    #if WEBEX_CONNECT_CORE
    WebexConnectProvider.instance.unregister {{ [weak self] _, error in
      Task {{ @MainActor in
        self?.isRegistered = false
        self?.isConnected = false
        self?.lastStatus = error == nil ? "Device unregistered" : "Unregister failed: \\(error!.localizedDescription)"
      }}
    }}
    #endif
  }}

  func appBecameActive() {{
    if isRegistered {{
      #if WEBEX_CONNECT_INAPP
      if isConnected {{
        fetchThreads()
        if let selectedThread {{
          fetchMessages(for: selectedThread, before: nil)
        }}
      }} else {{
        connectInAppIfNeeded()
      }}
      #endif
    }}
  }}

  func recordForegroundPush(_ userInfo: [AnyHashable: Any]) {{
    let title = userInfo["title"] as? String ?? "Webex Connect notification"
    let body = userInfo["body"] as? String ?? userInfo["alert"] as? String ?? "Notification received"
    pushNotifications.insert(PushNotificationRow(title: title, body: body, receivedAt: Date()), at: 0)
    lastStatus = "Foreground push received"
  }}

  func recordPushAction(_ userInfo: [AnyHashable: Any]) {{
    recordForegroundPush(userInfo)
    selectedTab = .support
  }}

  func configurePushIfNeeded() {{
    #if WEBEX_CONNECT_PUSH
    PushMessagingProvider.instance.pushMessagingDelegate = self
    PushMessagingProvider.instance.pushTokenDelegate = self
    PushMessagingProvider.instance.actionsDelegate = self
    PushMessagingProvider.instance.foregroundNotificationPresentationOptions = [.banner, .list, .sound, .badge]
    PushMessagingProvider.instance.setAppDelegateMethodSwizzlingEnabled(true)
    PushMessagingProvider.instance.setNotificationCenterMethodSwizzlingEnabled(true)
    Task {{
      let center = UNUserNotificationCenter.current()
      let granted = try? await center.requestAuthorization(options: [.alert, .badge, .sound])
      await MainActor.run {{
        self.lastStatus = granted == true ? "Notification authorization granted" : "Notification authorization pending"
        UIApplication.shared.registerForRemoteNotifications()
      }}
    }}
    #endif
  }}

  func configureInAppStore() {{
    #if WEBEX_CONNECT_INAPP
    InAppMessagingProvider.instance.messageStore = DefaultMessageStore(password: "WebexConnectDemoStore")
    let policy = MessageSynchronizationPolicy(
      mode: .limited,
      maxThreads: threadLimit,
      maxMessagesPerThread: messageLimit
    )
    InAppMessagingProvider.instance.messageSynchronizationPolicy = policy
    #endif
  }}

  func connectInAppIfNeeded() {{
    #if WEBEX_CONNECT_INAPP
    configureInAppStore()
    InAppMessagingProvider.instance.delegate = self
    do {{
      try InAppMessagingProvider.instance.connect()
      fetchThreads()
    }} catch {{
      lastStatus = "In-App connect failed: \\(error.localizedDescription)"
    }}
    #endif
  }}

  func fetchThreads(before: Date? = nil) {{
    #if WEBEX_CONNECT_INAPP
    guard isRegistered else {{
      lastStatus = "Register the device before fetching threads"
      return
    }}
    isLoadingThreads = true
    InAppMessagingProvider.instance.fetchThreads(beforeDate: before ?? Date(), limit: threadLimit, category: nil) {{ [weak self] sdkThreads, _, error in
      Task {{ @MainActor in
        self?.isLoadingThreads = false
        if let error {{
          self?.lastStatus = "Fetch threads failed: \\(error.localizedDescription)"
        }} else {{
          let mapped = sdkThreads.map {{ self?.renderer.renderThread($0) }}.compactMap {{ $0 }}
          self?.mergeThreads(mapped)
          self?.lastStatus = "Threads refreshed"
        }}
      }}
    }}
    #endif
  }}

  func fetchThread(threadId: String) {{
    #if WEBEX_CONNECT_INAPP
    InAppMessagingProvider.instance.fetchThread(forThreadId: threadId) {{ [weak self] sdkThread, error in
      Task {{ @MainActor in
        if let error {{
          self?.lastStatus = "Fetch thread failed: \\(error.localizedDescription)"
        }} else if let sdkThread {{
          let rendered = self?.renderer.renderThread(sdkThread)
          self?.mergeThreads([rendered].compactMap {{ $0 }})
          if let rendered, self?.visibleThreadId == rendered.id {{
            self?.selectedThread = rendered
            self?.fetchMessages(for: rendered, before: nil)
          }}
        }}
      }}
    }}
    #endif
  }}

  func createThread(title: String) {{
    #if WEBEX_CONNECT_INAPP
    let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmed.isEmpty else {{ return }}
    isCreatingThread = true
    let sdkThread = InAppThread()
    sdkThread.title = trimmed
    sdkThread.status = .active
    InAppMessagingProvider.instance.createThread(sdkThread) {{ [weak self] sdkThread, error in
      Task {{ @MainActor in
        self?.isCreatingThread = false
        if let error {{
          self?.lastStatus = "Create thread failed: \\(error.localizedDescription)"
        }} else if let sdkThread {{
          let thread = self?.renderer.renderThread(sdkThread)
          if let thread {{
            self?.mergeThreads([thread])
            self?.openThread(thread)
          }}
          self?.fetchThreads()
        }}
      }}
    }}
    #endif
  }}

  func openThread(_ thread: ConversationThread) {{
    selectedThread = thread
    visibleThreadId = thread.id
    selectedTab = .support
    if messagesByThread[thread.id] == nil {{
      messagesByThread[thread.id] = []
    }}
    fetchMessages(for: thread, before: nil)
  }}

  func closeThreadView() {{
    visibleThreadId = nil
    selectedThread = nil
  }}

  func fetchMessages(for thread: ConversationThread, before: Date?) {{
    #if WEBEX_CONNECT_INAPP
    guard thread.sdkThread is InAppThread else {{
      lastStatus = "Thread SDK object unavailable; refresh threads"
      fetchThread(threadId: thread.id)
      return
    }}
    isLoadingMessages = true
    InAppMessagingProvider.instance.fetchMessages(forThreadId: thread.id, beforeDate: before ?? Date(), limit: messageLimit) {{ [weak self] sdkMessages, _, error in
      Task {{ @MainActor in
        self?.isLoadingMessages = false
        if let error {{
          self?.lastStatus = "Fetch messages failed: \\(error.localizedDescription)"
        }} else {{
          let mapped = sdkMessages.compactMap {{ self?.renderer.renderInAppMessage($0, currentUserId: self?.currentUserId) }}
          self?.mergeMessages(mapped, for: thread.id)
          self?.markVisibleMessagesRead(threadId: thread.id)
          self?.lastStatus = "Messages refreshed"
        }}
      }}
    }}
    #endif
  }}

  func sendText(_ text: String) {{
    #if WEBEX_CONNECT_INAPP
    guard let thread = selectedThread, thread.canPublish else {{ return }}
    guard let sdkThread = thread.sdkThread as? InAppThread else {{
      lastStatus = "Refresh thread before sending"
      return
    }}
    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmed.isEmpty else {{ return }}

    var optimistic = renderer.localOutgoing(threadId: thread.id, text: trimmed)
    let fingerprint = outgoingFingerprint(threadId: thread.id, text: trimmed)
    pendingOutgoing[fingerprint] = optimistic.id
    mergeMessages([optimistic], for: thread.id)

    let outbound = InAppMessage()
    outbound.message = trimmed
    outbound.thread = sdkThread
    InAppMessagingProvider.instance.publishMessage(outbound) {{ [weak self] error in
      Task {{ @MainActor in
        if let error {{
          optimistic.status = .failed
          self?.replaceMessage(localId: optimistic.id, with: optimistic, threadId: thread.id)
          self?.lastStatus = "Send failed: \\(error.localizedDescription)"
        }} else {{
          optimistic.status = .sent
          self?.replaceMessage(localId: optimistic.id, with: optimistic, threadId: thread.id)
          self?.lastStatus = "Message sent"
          self?.scheduleMessageRefresh(threadId: thread.id)
        }}
      }}
    }}
    #endif
  }}

  func sendQuickReply(_ action: QuickReplyAction, parent: ChatMessage) {{
    #if WEBEX_CONNECT_INAPP
    guard let thread = selectedThread, thread.canPublish else {{ return }}
    sendText(action.title)
    disableAction(action.id, in: parent.id, threadId: thread.id)
    #endif
  }}

  func submitForm(_ form: FormTemplate, values: [String: String]) {{
    #if WEBEX_CONNECT_INAPP
    guard let data = try? JSONSerialization.data(withJSONObject: values, options: [.sortedKeys]),
          let payload = String(data: data, encoding: .utf8) else {{
      return
    }}
    sendText(payload)
    #endif
  }}

  func uploadAttachmentData(_ data: Data, fileName: String) {{
    #if WEBEX_CONNECT_INAPP
    guard let thread = selectedThread,
          thread.canPublish,
          let sdkThread = thread.sdkThread as? InAppThread else {{ return }}
    let tempUrl = FileManager.default.temporaryDirectory.appendingPathComponent(fileName)
    do {{
      try data.write(to: tempUrl, options: .atomic)
    }} catch {{
      lastStatus = "Attachment staging failed: \\(error.localizedDescription)"
      return
    }}
    InAppMessagingProvider.instance.mediaFileManager.upload(fileURL: tempUrl, progressHandler: nil) {{ [weak self] mediaId, error in
      Task {{ @MainActor in
        if let error {{
          self?.lastStatus = "Upload failed: \\(error.localizedDescription)"
        }} else if let mediaId {{
          let attachment = InAppMediaAttachment()
          attachment.mediaId = mediaId
          let outbound = InAppMessage()
          outbound.thread = sdkThread
          outbound.attachments = [attachment]
          InAppMessagingProvider.instance.publishMessage(outbound) {{ publishError in
            Task {{ @MainActor in
              if let publishError {{
                self?.lastStatus = "Publish attachment failed: \\(publishError.localizedDescription)"
              }} else {{
                self?.lastStatus = "Attachment sent"
                self?.scheduleMessageRefresh(threadId: thread.id)
              }}
            }}
          }}
        }}
      }}
    }}
    #endif
  }}

  func downloadAttachment(_ attachment: MessageAttachment, from message: ChatMessage) {{
    #if WEBEX_CONNECT_INAPP
    guard let url = attachment.url else {{ return }}
    InAppMessagingProvider.instance.mediaFileManager.downloadFile(at: url, progressHandler: nil) {{ [weak self] localUrl, error in
      Task {{ @MainActor in
        if let error {{
          self?.lastStatus = "Download failed: \\(error.localizedDescription)"
        }} else if let localUrl {{
          self?.lastStatus = "Attachment downloaded: \\(localUrl.lastPathComponent)"
        }}
      }}
    }}
    #endif
  }}

  func regenerateMediaUrl(_ attachment: MessageAttachment, in message: ChatMessage) {{
    #if WEBEX_CONNECT_INAPP
    guard let url = attachment.url else {{ return }}
    InAppMessagingProvider.instance.mediaFileManager.regenerateMediaURL(url) {{ [weak self] _, error in
      Task {{ @MainActor in
        if let error {{
          self?.lastStatus = "Media URL refresh failed: \\(error.localizedDescription)"
        }} else {{
          self?.lastStatus = "Media URL refreshed"
        }}
      }}
    }}
    #endif
  }}

  func closeSelectedThread() {{
    #if WEBEX_CONNECT_INAPP
    guard var thread = selectedThread, let sdkThread = thread.sdkThread as? InAppThread else {{ return }}
    sdkThread.status = .closed
    InAppMessagingProvider.instance.updateThread(sdkThread) {{ [weak self] updated, error in
      Task {{ @MainActor in
        if let error {{
          self?.lastStatus = "Close thread failed: \\(error.localizedDescription)"
        }} else if let updated {{
          thread = self?.renderer.renderThread(updated) ?? thread
          self?.selectedThread = thread
          self?.mergeThreads([thread])
          self?.lastStatus = "Thread closed"
        }}
      }}
    }}
    #endif
  }}

  func reopenSelectedThread() {{
    #if WEBEX_CONNECT_INAPP
    guard var thread = selectedThread, let sdkThread = thread.sdkThread as? InAppThread else {{ return }}
    sdkThread.status = .active
    InAppMessagingProvider.instance.updateThread(sdkThread) {{ [weak self] updated, error in
      Task {{ @MainActor in
        if let error {{
          self?.lastStatus = "Reopen thread failed: \\(error.localizedDescription)"
        }} else if let updated {{
          thread = self?.renderer.renderThread(updated) ?? thread
          self?.selectedThread = thread
          self?.mergeThreads([thread])
          self?.lastStatus = "Thread reopened"
        }}
      }}
    }}
    #endif
  }}

  func sendTyping(_ isTyping: Bool) {{
    #if WEBEX_CONNECT_INAPP
    guard let sdkThread = selectedThread?.sdkThread as? InAppThread else {{ return }}
    InAppMessagingProvider.instance.publishTypingIndicator(on: sdkThread, typing: isTyping, completionHandler: nil)
    #endif
  }}

  func handleRealtimeMessage(_ sdkMessage: Any) {{
    #if WEBEX_CONNECT_INAPP
    guard let sdkMessage = sdkMessage as? InAppMessage,
          let rendered = renderer.renderInAppMessage(sdkMessage, currentUserId: currentUserId) else {{
      return
    }}
    if rendered.isReceiptOnly {{
      applyReceipt(rendered)
      return
    }}
    let threadId = rendered.threadId
    mergeMessages([rendered], for: threadId)
    if visibleThreadId == threadId {{
      sendStatus(for: sdkMessage, status: InAppMessageStatus.delivered)
      sendStatus(for: sdkMessage, status: InAppMessageStatus.read)
      markVisibleMessagesRead(threadId: threadId)
      scheduleMessageRefresh(threadId: threadId)
    }} else {{
      updateInboxPreview(from: rendered)
      fetchThread(threadId: threadId)
    }}
    #endif
  }}

  func sendStatus(for sdkMessage: Any, status: Any) {{
    #if WEBEX_CONNECT_INAPP
    guard let sdkMessage = sdkMessage as? InAppMessage,
          let status = status as? InAppMessageStatus,
          let transactionId = sdkMessage.transactionId else {{ return }}
    InAppMessagingProvider.instance.sendMessageStatus(for: [transactionId], status: status) {{ _ in }}
    #endif
  }}

  func scheduleMessageRefresh(threadId: String, delay: UInt64 = 900_000_000) {{
    let cleanThreadId = threadId.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !cleanThreadId.isEmpty else {{ return }}
    pendingMessageRefreshTasks[cleanThreadId]?.cancel()
    pendingMessageRefreshTasks[cleanThreadId] = Task {{ [weak self] in
      try? await Task.sleep(nanoseconds: delay)
      await MainActor.run {{
        guard let self else {{ return }}
        self.pendingMessageRefreshTasks.removeValue(forKey: cleanThreadId)
        if self.visibleThreadId == cleanThreadId,
           let thread = self.selectedThread,
           thread.id == cleanThreadId {{
          self.fetchMessages(for: thread, before: nil)
        }} else {{
          self.fetchThread(threadId: cleanThreadId)
        }}
      }}
    }}
  }}

  func mergeThreads(_ incoming: [ConversationThread]) {{
    var byId = Dictionary(uniqueKeysWithValues: threads.map {{ ($0.id, $0) }})
    for thread in incoming {{
      byId[thread.id] = thread
    }}
    threads = byId.values.sorted {{ $0.updatedAt > $1.updatedAt }}
    if let selectedThread, let updated = byId[selectedThread.id] {{
      self.selectedThread = updated
    }}
  }}

  func mergeMessages(_ incoming: [ChatMessage], for threadId: String) {{
    var current = messagesByThread[threadId] ?? []
    var indexById: [String: Int] = [:]
    var indexByTransaction: [String: Int] = [:]
    for item in current.enumerated() {{
      indexById[item.element.id] = item.offset
      if let transactionId = item.element.transactionId {{
        indexByTransaction[transactionId] = item.offset
      }}
    }}

    for message in incoming where !message.isReceiptOnly {{
      if let existing = indexById[message.id] {{
        current[existing] = preferred(existing: current[existing], incoming: message)
      }} else if let tx = message.transactionId, let existing = indexByTransaction[tx] {{
        current[existing] = preferred(existing: current[existing], incoming: message)
      }} else if message.direction == .user,
                let localId = pendingOutgoing.removeValue(forKey: outgoingFingerprint(threadId: threadId, text: message.text)),
                let existing = indexById[localId] {{
        current[existing] = preferred(existing: current[existing], incoming: message)
      }} else {{
        indexById[message.id] = current.count
        if let tx = message.transactionId {{ indexByTransaction[tx] = current.count }}
        current.append(message)
      }}
    }}
    messagesByThread[threadId] = orderedMessages(current)
  }}

  func replaceMessage(localId: String, with message: ChatMessage, threadId: String) {{
    var current = messagesByThread[threadId] ?? []
    if let index = current.firstIndex(where: {{ $0.id == localId }}) {{
      current[index] = message.id == localId ? message : ChatMessage(
        id: message.id,
        threadId: message.threadId,
        transactionId: message.transactionId,
        relatedTransactionId: message.relatedTransactionId,
        direction: .user,
        kind: message.kind,
        text: message.text,
        createdAt: current[index].createdAt,
        status: message.status == .none ? .sent : message.status,
        attachments: message.attachments,
        cards: message.cards,
        quickReplies: message.quickReplies,
        form: message.form,
        sdkMessage: message.sdkMessage
      )
    }}
    messagesByThread[threadId] = orderedMessages(current)
  }}

  func preferred(existing: ChatMessage, incoming: ChatMessage) -> ChatMessage {{
    var output = incoming
    if existing.direction == .user && incoming.direction == .user {{
      output.direction = .user
    }}
    output.status = incoming.status.rank >= existing.status.rank ? incoming.status : existing.status
    if output.text.isEmpty {{
      output.text = existing.text
    }}
    if output.transactionId == nil {{
      output.transactionId = existing.transactionId
    }}
    if output.relatedTransactionId == nil {{
      output.relatedTransactionId = existing.relatedTransactionId
    }}
    return output
  }}

  func applyReceipt(_ receipt: ChatMessage) {{
    guard let transactionId = receipt.relatedTransactionId ?? receipt.transactionId else {{ return }}
    for key in messagesByThread.keys {{
      guard var messages = messagesByThread[key],
            let index = messages.firstIndex(where: {{ $0.transactionId == transactionId || $0.id == transactionId }}) else {{
        continue
      }}
      messages[index].status = receipt.status.rank > messages[index].status.rank ? receipt.status : messages[index].status
      messagesByThread[key] = orderedMessages(messages)
    }}
  }}

  func updateInboxPreview(from message: ChatMessage) {{
    guard !message.threadId.isEmpty else {{ return }}
    if let index = threads.firstIndex(where: {{ $0.id == message.threadId }}) {{
      threads[index].preview = message.text.isEmpty ? message.kind.rawValue.capitalized : message.text
      threads[index].updatedAt = message.createdAt
      threads[index].unreadCount += message.direction == .agent ? 1 : 0
      threads.sort {{ $0.updatedAt > $1.updatedAt }}
    }}
  }}

  func orderedMessages(_ messages: [ChatMessage]) -> [ChatMessage] {{
    messages.enumerated()
      .sorted {{
        if $0.element.createdAt == $1.element.createdAt {{
          return $0.offset < $1.offset
        }}
        return $0.element.createdAt < $1.element.createdAt
      }}
      .map {{ $0.element }}
  }}

  func markVisibleMessagesRead(threadId: String) {{
    if let index = threads.firstIndex(where: {{ $0.id == threadId }}) {{
      threads[index].unreadCount = 0
    }}
  }}

  func disableAction(_ actionId: String, in messageId: String, threadId: String) {{
    guard var messages = messagesByThread[threadId],
          let index = messages.firstIndex(where: {{ $0.id == messageId }}) else {{
      return
    }}
    messages[index].quickReplies = messages[index].quickReplies.map {{ action in
      var action = action
      if action.id == actionId {{ action.isComplete = true }}
      return action
    }}
    messages[index].cards = messages[index].cards.map {{ card in
      var card = card
      card.actions = card.actions.map {{ action in
        var action = action
        if action.id == actionId {{ action.isComplete = true }}
        return action
      }}
      return card
    }}
    messagesByThread[threadId] = messages
  }}

  func outgoingFingerprint(threadId: String, text: String) -> String {{
    "\\(threadId)|\\(currentUserId)|\\(text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased())"
  }}
}}

#if WEBEX_CONNECT_INAPP
extension WebexConnectRuntime: InAppMessagingDelegate {{
  nonisolated func didReceiveInAppMessage(_ message: InAppMessage) {{
    Task {{ @MainActor in
      WebexConnectRuntime.shared.handleRealtimeMessage(message)
    }}
  }}

  nonisolated func didChangeConnectionStatus(_ status: ConnectionStatus) {{
    Task {{ @MainActor in
      WebexConnectRuntime.shared.isConnected = String(describing: status).lowercased().contains("connected")
      WebexConnectRuntime.shared.lastStatus = "In-App status: \\(status)"
      if WebexConnectRuntime.shared.isConnected {{
        WebexConnectRuntime.shared.fetchThreads()
        if let thread = WebexConnectRuntime.shared.selectedThread {{
          WebexConnectRuntime.shared.fetchMessages(for: thread, before: nil)
        }}
      }}
    }}
  }}
}}
#endif

#if WEBEX_CONNECT_PUSH
extension WebexConnectRuntime: PushMessagingDelegate, PushTokenDelegate, PushActionsDelegate {{
  nonisolated func didReceiveMessage(message: PushMessage, fromTap: Bool) {{
    Task {{ @MainActor in
      WebexConnectRuntime.shared.pushNotifications.insert(
        PushNotificationRow(
          title: message.title ?? "Webex Connect notification",
          body: message.message ?? "Notification received",
          receivedAt: message.submittedAt ?? message.createdAt ?? Date()
        ),
        at: 0
      )
      if fromTap {{
        WebexConnectRuntime.shared.selectedTab = .support
      }}
      WebexConnectRuntime.shared.lastStatus = "Push message received"
    }}
  }}

  nonisolated func didUpdatePushToken(_ pushToken: String, type: PushTokenType) {{
    Task {{ @MainActor in
      WebexConnectRuntime.shared.apnsToken = pushToken
      WebexConnectRuntime.shared.lastStatus = "Push token updated"
    }}
  }}

  nonisolated func handleAction(
    _ action: String,
    withIdentifier identifier: String,
    forMessage message: PushMessage,
    responseInfo: [String: Any]?
  ) -> Bool {{
    Task {{ @MainActor in
      let extras = message.extras ?? [:]
      let userInfo = Dictionary(uniqueKeysWithValues: extras.map {{ (AnyHashable($0.key), $0.value) }})
      WebexConnectRuntime.shared.recordPushAction(userInfo)
      WebexConnectRuntime.shared.lastStatus = "Push action: \\(action)"
    }}
    return false
  }}
}}
#endif
"""


def template_views() -> str:
    return r"""
import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

enum ConnectColor {
  static let canvas = Color(red: 0.043, green: 0.059, blue: 0.071)
  static let surface = Color(red: 0.071, green: 0.086, blue: 0.098)
  static let elevated = Color(red: 0.114, green: 0.133, blue: 0.153)
  static let card = Color(red: 0.161, green: 0.184, blue: 0.207)
  static let border = Color.white.opacity(0.12)
  static let text = Color.white
  static let secondary = Color.white.opacity(0.68)
  static let muted = Color.white.opacity(0.42)
  static let activeBlue = Color(red: 0.204, green: 0.573, blue: 0.922)
  static let success = Color(red: 0.09, green: 0.78, blue: 0.66)
  static let alert = Color(red: 0.96, green: 0.35, blue: 0.41)
}

struct RootAppView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime

  var body: some View {
    TabView(selection: $runtime.selectedTab) {
      NavigationStack { ShopView() }
        .tabItem { Label(AppTab.shop.title, systemImage: AppTab.shop.icon) }
        .tag(AppTab.shop)
      NavigationStack { OrdersView() }
        .tabItem { Label(AppTab.orders.title, systemImage: AppTab.orders.icon) }
        .tag(AppTab.orders)
      NavigationStack { SupportWorkspaceView() }
        .tabItem { Label(AppTab.support.title, systemImage: AppTab.support.icon) }
        .tag(AppTab.support)
      NavigationStack { ProfileView() }
        .tabItem { Label(AppTab.profile.title, systemImage: AppTab.profile.icon) }
        .tag(AppTab.profile)
    }
    .tint(ConnectColor.activeBlue)
    .preferredColorScheme(.dark)
    .onReceive(NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)) { _ in
      runtime.appBecameActive()
    }
  }
}

struct AppTopBar: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var title: String = "Webex Store"

  var body: some View {
    HStack(spacing: 14) {
      Image("WebexLogo")
        .resizable()
        .scaledToFit()
        .frame(width: 40, height: 40)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
      Text(title)
        .font(.system(size: 22, weight: .bold))
        .foregroundStyle(ConnectColor.text)
        .lineLimit(1)
      Spacer()
      Button {
        runtime.selectedTab = .support
      } label: {
        ZStack(alignment: .topTrailing) {
          Image(systemName: "bell.fill")
            .font(.system(size: 21, weight: .semibold))
            .foregroundStyle(ConnectColor.text)
          if !runtime.pushNotifications.isEmpty {
            Text("\(min(runtime.pushNotifications.count, 9))")
              .font(.caption2.bold())
              .foregroundStyle(.white)
              .padding(.horizontal, 5)
              .padding(.vertical, 2)
              .background(ConnectColor.alert, in: Capsule())
              .offset(x: 8, y: -8)
          }
        }
      }
      .buttonStyle(.plain)
    }
    .padding(.horizontal, 20)
    .padding(.vertical, 16)
    .background(ConnectColor.surface)
  }
}

struct ShopView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime

  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 22) {
        AppTopBar()
        VStack(alignment: .leading, spacing: 18) {
          Text("Track orders and talk to support in one place")
            .font(.system(size: 31, weight: .bold))
            .foregroundStyle(ConnectColor.text)
          Text("A commerce shell for testing Webex Connect app messaging inside a normal customer journey.")
            .font(.system(size: 17))
            .foregroundStyle(ConnectColor.secondary)
          Button {
            runtime.selectedTab = .support
          } label: {
            Label("Message support", systemImage: "message.fill")
              .font(.system(size: 17, weight: .bold))
              .padding(.horizontal, 18)
              .padding(.vertical, 14)
              .background(ConnectColor.activeBlue, in: Capsule())
              .foregroundStyle(.white)
          }
          .buttonStyle(.plain)
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .padding(.horizontal, 20)

        SectionHeader(title: "Recommended for you", subtitle: "Personalized product cards")
        ScrollView(.horizontal, showsIndicators: false) {
          HStack(spacing: 14) {
            ProductCard(title: "Everyday earbuds", subtitle: "Top rated audio", price: "$79", color: ConnectColor.success)
            ProductCard(title: "Desk organizer", subtitle: "Work setup favorite", price: "$32", color: ConnectColor.alert)
          }
          .padding(.horizontal, 20)
        }

        SectionHeader(title: "Need help?", subtitle: "Messaging can start from any app journey")
        Button {
          runtime.selectedTab = .support
        } label: {
          HStack(spacing: 16) {
            Image(systemName: "message.fill")
              .font(.title2)
              .frame(width: 56, height: 56)
              .background(ConnectColor.activeBlue.opacity(0.18), in: Circle())
            VStack(alignment: .leading, spacing: 6) {
              Text("Talk to an agent or launch a workflow")
                .font(.headline)
                .foregroundStyle(ConnectColor.text)
              Text("Returns, billing, delivery, and product questions all route through in-app messaging.")
                .font(.subheadline)
                .foregroundStyle(ConnectColor.secondary)
            }
            Spacer()
            Image(systemName: "chevron.right")
              .font(.headline)
              .foregroundStyle(ConnectColor.secondary)
          }
          .padding(18)
          .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
          .padding(.horizontal, 20)
        }
        .buttonStyle(.plain)
      }
      .padding(.bottom, 24)
    }
    .background(ConnectColor.canvas.ignoresSafeArea())
  }
}

struct OrdersView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  private let orders = [
    ("Noise cancelling headphones", "ORD-2048", "Out for delivery", "Arrives today", 0.78),
    ("Smart home starter kit", "ORD-1984", "Preparing return", "Pickup tomorrow", 0.44),
    ("Travel backpack", "ORD-1842", "Delivered", "Delivered yesterday", 1.0)
  ]

  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 18) {
        AppTopBar()
        SectionHeader(title: "Orders", subtitle: "Tap support when an order needs attention")
        ForEach(orders, id: \.1) { order in
          VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top, spacing: 14) {
              Image(systemName: "truck.box.fill")
                .foregroundStyle(ConnectColor.activeBlue)
                .frame(width: 36, height: 36)
              VStack(alignment: .leading, spacing: 4) {
                Text(order.0)
                  .font(.headline)
                  .foregroundStyle(ConnectColor.text)
                Text("\(order.1) - \(order.2)")
                  .foregroundStyle(ConnectColor.secondary)
              }
              Spacer()
              Text(order.3)
                .font(.headline)
                .foregroundStyle(ConnectColor.activeBlue)
                .multilineTextAlignment(.trailing)
            }
            ProgressView(value: order.4)
              .tint(ConnectColor.activeBlue)
            Button {
              runtime.selectedTab = .support
            } label: {
              Label("Ask about this order", systemImage: "message.fill")
                .font(.headline)
                .foregroundStyle(ConnectColor.activeBlue)
            }
            .buttonStyle(.plain)
          }
          .padding(20)
          .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
          .padding(.horizontal, 20)
        }
      }
      .padding(.bottom, 24)
    }
    .background(ConnectColor.canvas.ignoresSafeArea())
  }
}

struct SupportWorkspaceView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime

  var body: some View {
    Group {
      if let thread = runtime.selectedThread {
        ThreadConversationView(thread: thread)
      } else {
        ConversationInboxView()
      }
    }
    .background(ConnectColor.canvas.ignoresSafeArea())
  }
}

struct ConversationInboxView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  @State private var search = ""
  @State private var filter: String = "All"
  @State private var showCreate = false
  @State private var newThreadTitle = ""

  var filteredThreads: [ConversationThread] {
    runtime.threads.filter { thread in
      let matchesSearch = search.isEmpty || thread.title.localizedCaseInsensitiveContains(search)
      let matchesFilter = filter == "All"
        || (filter == "Unread" && thread.unreadCount > 0)
        || (filter == "Open" && thread.status != .closed)
      return matchesSearch && matchesFilter
    }
  }

  var body: some View {
    VStack(spacing: 0) {
      AppTopBar()
      ScrollView {
        VStack(alignment: .leading, spacing: 20) {
          HStack(alignment: .lastTextBaseline) {
            VStack(alignment: .leading, spacing: 4) {
              Text("Conversations")
                .font(.system(size: 30, weight: .bold))
                .foregroundStyle(ConnectColor.text)
              Text("\(filteredThreads.count) of \(runtime.threads.count) conversations")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(ConnectColor.secondary)
            }
            Spacer()
            Button { showCreate = true } label: {
              Image(systemName: "plus")
                .font(.system(size: 26, weight: .medium))
            }
            .buttonStyle(.plain)
            Button { runtime.fetchThreads() } label: {
              Image(systemName: "arrow.clockwise")
                .font(.system(size: 24, weight: .semibold))
                .foregroundStyle(ConnectColor.activeBlue)
            }
            .buttonStyle(.plain)
          }

          HStack(spacing: 14) {
            HStack(spacing: 12) {
              Image(systemName: "magnifyingglass")
                .foregroundStyle(ConnectColor.secondary)
              TextField("Search conversations", text: $search)
                .textInputAutocapitalization(.never)
                .foregroundStyle(ConnectColor.text)
            }
            .padding(.horizontal, 16)
            .frame(height: 56)
            .background(ConnectColor.elevated)
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(ConnectColor.border))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            Button { } label: {
              Image(systemName: "slider.horizontal.3")
                .font(.system(size: 22, weight: .semibold))
                .frame(width: 56, height: 56)
                .background(ConnectColor.elevated, in: Circle())
            }
            .buttonStyle(.plain)
          }

          HStack(spacing: 10) {
            ForEach(["All", "Unread", "Open"], id: \.self) { item in
              Button { filter = item } label: {
                Text(item)
                  .font(.subheadline.weight(.bold))
                  .padding(.horizontal, 18)
                  .padding(.vertical, 12)
                  .background(filter == item ? ConnectColor.success.opacity(0.22) : Color.clear)
                  .overlay(RoundedRectangle(cornerRadius: 10).stroke(filter == item ? Color.clear : ConnectColor.border))
                  .clipShape(RoundedRectangle(cornerRadius: 10))
              }
              .buttonStyle(.plain)
              .foregroundStyle(filter == item ? ConnectColor.text : ConnectColor.secondary)
            }
          }

          if runtime.isLoadingThreads && runtime.threads.isEmpty {
            ProgressView("Loading conversations")
              .frame(maxWidth: .infinity, minHeight: 140)
          } else if filteredThreads.isEmpty {
            EmptyThreadsView(showCreate: $showCreate)
          } else {
            LazyVStack(spacing: 14) {
              ForEach(filteredThreads) { thread in
                ThreadRow(thread: thread) {
                  runtime.openThread(thread)
                }
              }
            }
          }
        }
        .padding(20)
      }
    }
    .sheet(isPresented: $showCreate) {
      CreateThreadSheet(title: $newThreadTitle) {
        runtime.createThread(title: newThreadTitle)
        newThreadTitle = ""
        showCreate = false
      }
      .presentationDetents([.height(260)])
    }
  }
}

struct ThreadConversationView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var thread: ConversationThread

  var activeThread: ConversationThread {
    runtime.selectedThread ?? thread
  }

  var messages: [ChatMessage] {
    runtime.messagesByThread[activeThread.id] ?? []
  }

  var body: some View {
    VStack(spacing: 0) {
      ThreadHeaderView(thread: activeThread)
      Divider().overlay(ConnectColor.border)
      ScrollViewReader { proxy in
        ScrollView {
          LazyVStack(alignment: .leading, spacing: 16) {
            DaySeparator(title: "Today")
            if activeThread.status == .closed {
              ClosedThreadState(thread: activeThread)
            }
            if runtime.isLoadingMessages && messages.isEmpty {
              ProgressView("Loading messages")
                .frame(maxWidth: .infinity, minHeight: 140)
            } else if messages.isEmpty {
              Text("No messages yet")
                .foregroundStyle(ConnectColor.secondary)
                .frame(maxWidth: .infinity, minHeight: 140)
            } else {
              ForEach(messages) { message in
                MessageBubbleView(message: message)
                  .id(message.id)
              }
            }
          }
          .padding(.horizontal, 20)
          .padding(.top, 16)
          .padding(.bottom, activeThread.canPublish ? 132 : 28)
        }
        .onChange(of: messages.last?.id) { _ in
          if let last = messages.last {
            withAnimation(.easeOut(duration: 0.2)) {
              proxy.scrollTo(last.id, anchor: .bottom)
            }
          }
        }
      }
    }
    .background(ConnectColor.canvas.ignoresSafeArea())
    .safeAreaInset(edge: .bottom, spacing: 0) {
      if activeThread.canPublish {
        ComposerView()
      }
    }
  }
}

struct ThreadHeaderView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var thread: ConversationThread

  var body: some View {
    HStack(spacing: 14) {
      Button { runtime.closeThreadView() } label: {
        Image(systemName: "chevron.left")
          .font(.system(size: 26, weight: .medium))
          .foregroundStyle(ConnectColor.text)
          .frame(width: 42, height: 42)
      }
      .buttonStyle(.plain)

      Image("WebexLogo")
        .resizable()
        .scaledToFit()
        .frame(width: 56, height: 56)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

      VStack(alignment: .leading, spacing: 5) {
        Text(thread.title)
          .font(.system(size: 21, weight: .bold))
          .lineLimit(1)
          .foregroundStyle(ConnectColor.text)
        HStack(spacing: 7) {
          Text("Thread ID \(runtime.renderer.compactThreadId(thread.id))")
            .font(.subheadline)
            .foregroundStyle(ConnectColor.secondary)
            .lineLimit(1)
          Button { runtime.copyToClipboard(thread.id) } label: {
            Image(systemName: "doc.on.doc")
              .font(.system(size: 13, weight: .semibold))
              .foregroundStyle(ConnectColor.secondary)
          }
          .buttonStyle(.plain)
        }
        HStack(spacing: 6) {
          Circle()
            .fill(thread.status == .closed ? ConnectColor.muted : ConnectColor.success)
            .frame(width: 8, height: 8)
          Text(thread.status.label)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(thread.status == .closed ? ConnectColor.secondary : ConnectColor.success)
        }
      }
      Spacer()
      ThreadMenu(thread: thread)
    }
    .padding(.horizontal, 20)
    .padding(.top, 10)
    .padding(.bottom, 14)
    .background(ConnectColor.surface)
  }
}

struct ThreadMenu: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var thread: ConversationThread

  var body: some View {
    Menu {
      Button { runtime.lastStatus = "Details selected" } label: {
        Label("View details", systemImage: "person.crop.circle")
      }
      Button { runtime.lastStatus = "Search selected" } label: {
        Label("Search in conversation", systemImage: "magnifyingglass")
      }
      if thread.status == .closed {
        Button { runtime.reopenSelectedThread() } label: {
          Label("Reopen thread", systemImage: "lock.open")
        }
      } else {
        Button(role: .destructive) { runtime.closeSelectedThread() } label: {
          Label("Close thread", systemImage: "lock")
        }
      }
    } label: {
      Image(systemName: "ellipsis")
        .font(.system(size: 24, weight: .bold))
        .foregroundStyle(ConnectColor.text)
        .frame(width: 44, height: 44)
    }
  }
}

struct MessageBubbleView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var message: ChatMessage

  var body: some View {
    HStack(alignment: .top, spacing: 10) {
      if message.isUserMessage { Spacer(minLength: 54) } else {
        Image("WebexLogo")
          .resizable()
          .scaledToFit()
          .frame(width: 34, height: 34)
          .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
      }
      VStack(alignment: message.isUserMessage ? .trailing : .leading, spacing: 7) {
        VStack(alignment: .leading, spacing: 10) {
          if !message.text.isEmpty {
            Text(message.text)
              .font(.system(size: 17))
              .foregroundStyle(ConnectColor.text)
              .fixedSize(horizontal: false, vertical: true)
          }
          if !message.cards.isEmpty {
            CardCarouselView(cards: message.cards, message: message)
          }
          if let form = message.form {
            FormTemplateView(form: form)
          }
          if !message.attachments.isEmpty {
            AttachmentStack(message: message)
          }
          if !message.quickReplies.isEmpty {
            QuickReplyRow(message: message, actions: message.quickReplies)
          }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 13)
        .background(message.isUserMessage ? ConnectColor.activeBlue : ConnectColor.elevated)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))

        HStack(spacing: 4) {
          if message.isUserMessage && message.status != .none {
            Image(systemName: message.status == .read || message.status == .delivered ? "checkmark" : "clock")
            Text(message.status.label)
          } else if !message.isUserMessage {
            Text(timeString(message.createdAt))
          }
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(ConnectColor.secondary)
        .padding(.horizontal, 4)
      }
      .frame(maxWidth: 318, alignment: message.isUserMessage ? .trailing : .leading)
      if !message.isUserMessage { Spacer(minLength: 54) }
    }
  }

  func timeString(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.timeStyle = .short
    return formatter.string(from: date)
  }
}

struct CardCarouselView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var cards: [RichCard]
  var message: ChatMessage

  var body: some View {
    ScrollView(.horizontal, showsIndicators: false) {
      HStack(spacing: 14) {
        ForEach(cards) { card in
          VStack(alignment: .leading, spacing: 12) {
            AsyncCardImage(url: card.imageUrl)
            Text(card.title)
              .font(.headline)
              .foregroundStyle(ConnectColor.text)
              .lineLimit(2)
            if !card.subtitle.isEmpty {
              Text(card.subtitle)
                .font(.subheadline)
                .foregroundStyle(ConnectColor.secondary)
                .lineLimit(3)
            }
            if let price = card.price {
              Text(price)
                .font(.headline)
                .foregroundStyle(ConnectColor.text)
            }
            ForEach(card.actions) { action in
              Button { runtime.sendQuickReply(action, parent: message) } label: {
                Text(action.title)
                  .font(.subheadline.weight(.bold))
                  .frame(maxWidth: .infinity)
                  .padding(.vertical, 11)
                  .background(ConnectColor.activeBlue.opacity(action.isComplete ? 0.35 : 1), in: RoundedRectangle(cornerRadius: 10))
              }
              .disabled(action.isComplete)
              .buttonStyle(.plain)
            }
          }
          .padding(14)
          .frame(width: 238)
          .background(ConnectColor.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
      }
    }
  }
}

struct QuickReplyRow: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var message: ChatMessage
  var actions: [QuickReplyAction]

  var body: some View {
    ScrollView(.horizontal, showsIndicators: false) {
      HStack(spacing: 10) {
        ForEach(actions) { action in
          Button { runtime.sendQuickReply(action, parent: message) } label: {
            Label(action.title, systemImage: "chevron.right")
              .font(.subheadline.weight(.bold))
              .padding(.horizontal, 14)
              .padding(.vertical, 10)
              .overlay(RoundedRectangle(cornerRadius: 12).stroke(ConnectColor.activeBlue))
          }
          .disabled(action.isComplete)
          .buttonStyle(.plain)
        }
      }
    }
  }
}

struct FormTemplateView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  @State private var values: [String: String] = [:]
  var form: FormTemplate

  var isValid: Bool {
    form.fields.allSatisfy { field in
      !field.required || !(values[field.key] ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
  }

  var body: some View {
    VStack(alignment: .leading, spacing: 12) {
      Text(form.title)
        .font(.headline)
      ForEach(form.fields) { field in
        TextField(field.placeholder.isEmpty ? field.title : field.placeholder, text: Binding(
          get: { values[field.key] ?? "" },
          set: { values[field.key] = $0 }
        ))
        .textFieldStyle(.plain)
        .padding(12)
        .background(ConnectColor.surface)
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(ConnectColor.border))
        .clipShape(RoundedRectangle(cornerRadius: 10))
      }
      Button {
        runtime.submitForm(form, values: values)
      } label: {
        Label(form.submitTitle, systemImage: "paperplane.fill")
          .frame(maxWidth: .infinity)
          .padding(.vertical, 12)
          .background(isValid ? ConnectColor.activeBlue : ConnectColor.muted, in: RoundedRectangle(cornerRadius: 12))
      }
      .disabled(!isValid || form.isComplete)
      .buttonStyle(.plain)
    }
  }
}

struct AttachmentStack: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var message: ChatMessage

  var body: some View {
    VStack(alignment: .leading, spacing: 8) {
      ForEach(message.attachments) { attachment in
        HStack(spacing: 10) {
          Image(systemName: icon(for: attachment.contentType))
            .foregroundStyle(ConnectColor.activeBlue)
          VStack(alignment: .leading, spacing: 2) {
            Text(attachment.name)
              .font(.subheadline.weight(.bold))
            if let duration = attachment.duration {
              Text(duration)
                .font(.caption)
                .foregroundStyle(ConnectColor.secondary)
            }
          }
          Spacer()
          Button { runtime.downloadAttachment(attachment, from: message) } label: {
            Image(systemName: "arrow.down.circle")
          }
          Button { runtime.regenerateMediaUrl(attachment, in: message) } label: {
            Image(systemName: "arrow.clockwise.circle")
          }
        }
        if let url = attachment.thumbnailUrl ?? attachment.url,
           attachment.contentType.lowercased().contains("image") {
          AsyncImage(url: url) { phase in
            switch phase {
            case .success(let image):
              image.resizable().scaledToFill()
            case .failure:
              Color.white.opacity(0.08)
            case .empty:
              ProgressView()
            @unknown default:
              EmptyView()
            }
          }
          .frame(height: 160)
          .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
      }
    }
  }

  func icon(for type: String) -> String {
    let value = type.lowercased()
    if value.contains("image") { return "photo" }
    if value.contains("audio") { return "waveform" }
    if value.contains("video") { return "play.rectangle" }
    if value.contains("location") { return "mappin.and.ellipse" }
    return "paperclip"
  }
}

struct ComposerView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  @State private var text = ""
  @FocusState private var focused: Bool

  var body: some View {
    VStack(spacing: 10) {
      HStack(spacing: 10) {
        QuickActionChip(title: "Help with a request")
        QuickActionChip(title: "Start a support chat")
      }
      .frame(maxWidth: .infinity, alignment: .leading)
      .padding(.horizontal, 20)
      .padding(.top, 12)

      HStack(spacing: 12) {
        Button { runtime.lastStatus = "Choose attachment" } label: {
          Image(systemName: "plus")
            .font(.system(size: 28, weight: .medium))
            .foregroundStyle(ConnectColor.text)
            .frame(width: 56, height: 56)
            .background(Color.white.opacity(0.10), in: Circle())
        }
        .buttonStyle(.plain)

        Rectangle()
          .fill(ConnectColor.border)
          .frame(width: 1, height: 34)

        TextField("Write a message...", text: $text, axis: .vertical)
          .focused($focused)
          .lineLimit(1...4)
          .foregroundStyle(ConnectColor.text)
          .onChange(of: focused) { newValue in runtime.sendTyping(newValue) }

        Button {
          let outgoing = text
          text = ""
          focused = false
          runtime.sendText(outgoing)
        } label: {
          Image(systemName: "paperplane.fill")
            .font(.system(size: 24, weight: .bold))
            .foregroundStyle(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? ConnectColor.muted : ConnectColor.activeBlue)
            .frame(width: 46, height: 46)
        }
        .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        .buttonStyle(.plain)
      }
      .padding(.horizontal, 10)
      .padding(.vertical, 8)
      .background(ConnectColor.elevated, in: Capsule())
      .padding(.horizontal, 20)
      .padding(.bottom, 12)
    }
    .background(.ultraThinMaterial)
  }
}

struct ProfileView: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  @State private var userId = ""
  @State private var customerId = ""
  @State private var threadLimit = "50"
  @State private var messageLimit = "50"

  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 18) {
        AppTopBar()
        SectionHeader(title: "Profile", subtitle: "Global Webex Connect settings")
        VStack(alignment: .leading, spacing: 12) {
          Text("App ID: \(runtime.appId.isEmpty ? "Not configured" : runtime.appId)")
            .font(.headline)
          LabeledInput(title: "User ID", text: $userId)
          Button("Register / Update") {
            runtime.registerUser(userId)
          }
          .buttonStyle(PrimaryButtonStyle())
          LabeledInput(title: "Customer ID", text: $customerId)
          Button("Update Customer ID") {
            runtime.updateCustomerId(customerId)
          }
          .buttonStyle(PrimaryButtonStyle())
        }
        .profileCard()

        PushTokenCard(token: runtime.apnsToken)

        VStack(alignment: .leading, spacing: 12) {
          Text("SDK tools")
            .font(.title3.bold())
          HStack(spacing: 12) {
            LabeledInput(title: "Threads", text: $threadLimit)
            LabeledInput(title: "Messages", text: $messageLimit)
          }
          Button("Apply sync limits") {
            runtime.updateSyncLimits(
              threadLimit: Int(threadLimit) ?? 50,
              messageLimit: Int(messageLimit) ?? 50
            )
          }
          .buttonStyle(PrimaryButtonStyle())
        }
        .profileCard()

        VStack(alignment: .leading, spacing: 10) {
          Text("SDK status")
            .font(.title3.bold())
          StatusLine(label: "Configured", value: "\(runtime.isConfigured)")
          StatusLine(label: "Started", value: "\(runtime.isStarted)")
          StatusLine(label: "Registered", value: "\(runtime.isRegistered)")
          StatusLine(label: "In-App connected", value: "\(runtime.isConnected)")
          StatusLine(label: "SDK version", value: runtime.sdkVersion)
          StatusLine(label: "Store policy", value: "limited / \(runtime.threadLimit) threads / \(runtime.messageLimit) messages")
          StatusLine(label: "Last status", value: runtime.lastStatus)
          Button("Unregister device") {
            runtime.unregisterUser()
          }
          .buttonStyle(BorderButtonStyle())
        }
        .profileCard()
      }
      .padding(.bottom, 28)
    }
    .background(ConnectColor.canvas.ignoresSafeArea())
    .onAppear {
      userId = runtime.currentUserId
      customerId = runtime.customerId
      threadLimit = "\(runtime.threadLimit)"
      messageLimit = "\(runtime.messageLimit)"
    }
  }
}

struct PushTokenCard: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var token: String

  var body: some View {
    VStack(alignment: .leading, spacing: 10) {
      HStack {
        Text("Push token")
          .font(.title3.bold())
        Spacer()
        Button { runtime.copyToClipboard(token) } label: {
          Image(systemName: "doc.on.doc")
        }
      }
      Text(token)
        .font(.footnote.monospaced())
        .foregroundStyle(ConnectColor.secondary)
        .textSelection(.enabled)
    }
    .profileCard()
  }
}

struct ThreadRow: View {
  var thread: ConversationThread
  var action: () -> Void

  var body: some View {
    Button(action: action) {
      HStack(spacing: 16) {
        ZStack(alignment: .bottomTrailing) {
          Circle()
            .fill(ConnectColor.activeBlue.opacity(0.18))
            .frame(width: 64, height: 64)
          Text(initials(thread.title))
            .font(.headline.bold())
            .foregroundStyle(ConnectColor.activeBlue)
          Circle()
            .fill(thread.status == .closed ? ConnectColor.muted : ConnectColor.success)
            .frame(width: 15, height: 15)
            .overlay(Circle().stroke(ConnectColor.elevated, lineWidth: 3))
        }
        VStack(alignment: .leading, spacing: 6) {
          Text(thread.title)
            .font(.headline)
            .foregroundStyle(ConnectColor.text)
            .lineLimit(1)
          Text(thread.preview)
            .font(.subheadline)
            .foregroundStyle(ConnectColor.secondary)
            .lineLimit(1)
          Text(thread.status == .closed ? "Closed support" : "Active support")
            .font(.caption.weight(.semibold))
            .foregroundStyle(ConnectColor.secondary)
        }
        Spacer()
        VStack(alignment: .trailing, spacing: 8) {
          Text(relativeTime(thread.updatedAt))
            .font(.caption.weight(.bold))
            .foregroundStyle(ConnectColor.secondary)
          if thread.unreadCount > 0 {
            Text("\(thread.unreadCount)")
              .font(.caption.bold())
              .padding(7)
              .background(ConnectColor.activeBlue, in: Circle())
          }
        }
        Image(systemName: "chevron.right")
          .foregroundStyle(ConnectColor.secondary)
      }
      .padding(18)
      .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
    .buttonStyle(.plain)
  }

  func initials(_ value: String) -> String {
    value.split(separator: " ").prefix(2).map { String($0.prefix(1)).uppercased() }.joined()
  }

  func relativeTime(_ date: Date) -> String {
    if Date().timeIntervalSince(date) < 60 { return "Now" }
    let formatter = RelativeDateTimeFormatter()
    formatter.unitsStyle = .abbreviated
    return formatter.localizedString(for: date, relativeTo: Date())
  }
}

struct CreateThreadSheet: View {
  @Binding var title: String
  var create: () -> Void

  var body: some View {
    VStack(alignment: .leading, spacing: 18) {
      Text("Start a new conversation")
        .font(.title2.bold())
        .foregroundStyle(ConnectColor.text)
      Text("Give the support conversation a clear title.")
        .foregroundStyle(ConnectColor.secondary)
      TextField("New conversation title", text: $title)
        .padding(16)
        .background(ConnectColor.surface)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(ConnectColor.border))
        .clipShape(RoundedRectangle(cornerRadius: 12))
      HStack {
        Spacer()
        Button("Create", action: create)
          .buttonStyle(PrimaryButtonStyle())
      }
    }
    .padding(24)
    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    .background(ConnectColor.elevated.ignoresSafeArea())
  }
}

struct EmptyThreadsView: View {
  @Binding var showCreate: Bool

  var body: some View {
    VStack(alignment: .leading, spacing: 12) {
      Image(systemName: "message.fill")
        .foregroundStyle(ConnectColor.activeBlue)
      Text("No conversations yet")
        .font(.headline)
      Text("Start a support conversation from the plus button.")
        .font(.subheadline)
        .foregroundStyle(ConnectColor.secondary)
      Button("Start conversation") { showCreate = true }
        .buttonStyle(PrimaryButtonStyle())
    }
    .frame(maxWidth: .infinity, alignment: .leading)
    .padding(18)
    .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
  }
}

struct ClosedThreadState: View {
  @EnvironmentObject private var runtime: WebexConnectRuntime
  var thread: ConversationThread

  var body: some View {
    VStack(spacing: 14) {
      Image(systemName: "lock.fill")
        .font(.system(size: 34, weight: .semibold))
        .frame(width: 74, height: 74)
        .background(ConnectColor.elevated, in: Circle())
      Text("This thread is closed")
        .font(.title3.bold())
      Text("You can no longer send messages in this thread.")
        .font(.subheadline)
        .foregroundStyle(ConnectColor.secondary)
        .multilineTextAlignment(.center)
      Button("Reopen thread") {
        runtime.reopenSelectedThread()
      }
      .buttonStyle(PrimaryButtonStyle())
    }
    .frame(maxWidth: .infinity)
    .padding(.vertical, 26)
  }
}

struct ProductCard: View {
  var title: String
  var subtitle: String
  var price: String
  var color: Color

  var body: some View {
    VStack(alignment: .leading, spacing: 14) {
      RoundedRectangle(cornerRadius: 16)
        .fill(color.opacity(0.18))
        .overlay(Image(systemName: "cart.fill").font(.system(size: 42)).foregroundStyle(color))
        .frame(height: 132)
      Text(title)
        .font(.headline)
      Text(subtitle)
        .foregroundStyle(ConnectColor.secondary)
      Text(price)
        .font(.headline)
    }
    .foregroundStyle(ConnectColor.text)
    .padding(16)
    .frame(width: 220, alignment: .leading)
    .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
  }
}

struct AsyncCardImage: View {
  var url: URL?

  var body: some View {
    Group {
      if let url {
        AsyncImage(url: url) { phase in
          switch phase {
          case .success(let image):
            image.resizable().scaledToFill()
          case .failure:
            fallback
          case .empty:
            ProgressView()
          @unknown default:
            fallback
          }
        }
      } else {
        fallback
      }
    }
    .frame(height: 150)
    .frame(maxWidth: .infinity)
    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
  }

  var fallback: some View {
    ConnectColor.activeBlue.opacity(0.18)
      .overlay(Image(systemName: "photo").font(.title).foregroundStyle(ConnectColor.activeBlue))
  }
}

struct SectionHeader: View {
  var title: String
  var subtitle: String

  var body: some View {
    VStack(alignment: .leading, spacing: 5) {
      Text(title)
        .font(.system(size: 29, weight: .bold))
        .foregroundStyle(ConnectColor.text)
      Text(subtitle)
        .font(.system(size: 17))
        .foregroundStyle(ConnectColor.secondary)
    }
    .padding(.horizontal, 20)
  }
}

struct DaySeparator: View {
  var title: String

  var body: some View {
    Text(title)
      .font(.subheadline.weight(.bold))
      .foregroundStyle(ConnectColor.secondary)
      .padding(.horizontal, 18)
      .padding(.vertical, 9)
      .background(ConnectColor.elevated, in: Capsule())
      .frame(maxWidth: .infinity)
  }
}

struct QuickActionChip: View {
  var title: String

  var body: some View {
    Label(title, systemImage: "message.fill")
      .font(.subheadline.weight(.bold))
      .lineLimit(1)
      .padding(.horizontal, 13)
      .padding(.vertical, 10)
      .overlay(RoundedRectangle(cornerRadius: 10).stroke(ConnectColor.border))
      .foregroundStyle(ConnectColor.text)
  }
}

struct LabeledInput: View {
  var title: String
  @Binding var text: String

  var body: some View {
    TextField(title, text: $text)
      .textInputAutocapitalization(.never)
      .padding(14)
      .background(ConnectColor.surface)
      .overlay(RoundedRectangle(cornerRadius: 10).stroke(ConnectColor.border))
      .clipShape(RoundedRectangle(cornerRadius: 10))
  }
}

struct StatusLine: View {
  var label: String
  var value: String

  var body: some View {
    VStack(alignment: .leading, spacing: 3) {
      Text(label)
        .font(.caption.weight(.bold))
        .foregroundStyle(ConnectColor.secondary)
      Text(value)
        .font(.subheadline)
        .foregroundStyle(ConnectColor.text)
        .textSelection(.enabled)
    }
  }
}

struct PrimaryButtonStyle: ButtonStyle {
  func makeBody(configuration: Configuration) -> some View {
    configuration.label
      .font(.headline)
      .foregroundStyle(.white)
      .padding(.horizontal, 18)
      .padding(.vertical, 13)
      .background(ConnectColor.activeBlue.opacity(configuration.isPressed ? 0.75 : 1), in: Capsule())
  }
}

struct BorderButtonStyle: ButtonStyle {
  func makeBody(configuration: Configuration) -> some View {
    configuration.label
      .font(.headline)
      .foregroundStyle(ConnectColor.text)
      .padding(.horizontal, 18)
      .padding(.vertical, 13)
      .overlay(Capsule().stroke(ConnectColor.border))
  }
}

extension View {
  func profileCard() -> some View {
    self
      .padding(18)
      .frame(maxWidth: .infinity, alignment: .leading)
      .background(ConnectColor.elevated, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
      .padding(.horizontal, 20)
  }
}
"""


def write_swift_sources(options: Options) -> None:
    write_text(options.app_dir / "WebexConnectDemoApp.swift", template_app(options))
    write_text(options.app_dir / "AppDelegate.swift", template_app_delegate(options))
    write_text(options.app_dir / "DemoModels.swift", template_models())
    write_text(options.app_dir / "MessageRenderer.swift", template_renderer())
    write_text(options.app_dir / "WebexConnectRuntime.swift", template_runtime(options))
    write_text(options.app_dir / "DemoViews.swift", template_views())


def write_docs(options: Options) -> None:
    capability_label = {"push": "Push", "inapp": "In-App Messaging", "both": "Push + In-App Messaging"}[options.capability]
    write_text(
        options.root / "BUILD_IOS.md",
        f"""# Build iOS Webex Connect Demo

This generated app is a SwiftUI iOS app target that uses Swift Package Manager
with `{SPM_URL}` pinned to `{options.sdk_version}`.

## Generated Scope

- App: `{options.app_name}`
- Bundle ID: `{options.bundle_id}`
- Capability: {capability_label}
- Dependency manager: Swift Package Manager
- Config file: `WebexConnectConfig.plist` or `IMIConnectConfig.plist`
- Local message-store limits: `{options.thread_limit}` threads / `{options.message_limit}` messages per thread

## Open And Run

1. Open `{TARGET_NAME}.xcodeproj` in Xcode.
2. Select the `{TARGET_NAME}` scheme.
3. Configure signing with your Apple team if `DEVELOPMENT_TEAM` is blank.
4. If this app was generated without a real config, replace
   `{TARGET_NAME}/WebexConnectConfig.plist.example` with
   `{TARGET_NAME}/WebexConnectConfig.plist` from the Webex Connect app asset.
5. Resolve packages from Xcode or run:

   ```bash
   xcodebuild -resolvePackageDependencies -project {TARGET_NAME}.xcodeproj -scheme {TARGET_NAME}
   ```

6. Build and run on a simulator for UI checks or a physical device for APNs
   token and push notification checks.

## Push Setup

- Enable Push Notifications for the app target.
- Enable Background Modes and select Remote notifications.
- Upload APNs credentials for this bundle ID in the Webex Connect app asset.
- APNs token is shown in Profile in a separate copyable card.
- APNs token registration uses
  `PushMessagingProvider.instance.processPushToken(_:type:completionHandler:)`.
- Foreground and tapped push callbacks are surfaced through the push module
  delegates and displayed as push notification diagnostics.

## In-App Runtime

- Core startup checks for `WebexConnectConfig.plist` before SDK startup.
- Device registration uses the in-app User ID from Profile.
- `DefaultMessageStore` and `MessageSynchronizationPolicy(.limited)` are set
  as the local message store before connect.
- `fetchThreads` runs on startup, app foreground, create/close/reopen, manual
  refresh, and connection restore.
- `fetchMessages` runs when opening a thread, paginating, and after connection
  restore for the visible thread.
- Realtime in-app messages are merged into the same transcript path as fetched
  messages and sorted oldest-to-newest by SDK message time.
- Current-thread inbound messages display immediately and are marked delivered
  and read. Other-thread inbound messages update inbox preview/unread only.
- Visible-thread realtime receives and successful sends schedule a short
  delayed `fetchMessages` reconciliation so Server-Side Inbox lag cannot leave
  the UI stale.
- Delivery/read receipts update one outgoing bubble footer instead of creating
  extra transcript rows.

## UI Notes

- Conversation header shows the selected thread title, compact copyable thread
  ID, status dot, and overflow menu.
- Closed threads preserve history, show a lock state, and hide composer actions
  until reopened.
- Profile holds global settings only: App ID, SDK state, APNs token, sync
  limits, registration controls, and diagnostics.
""",
    )
    write_text(
        options.root / "QA_CHECKLIST.md",
        """# QA Checklist

## Static

- `Package.swift` and the Xcode project both point to the Webex Connect iOS SPM repository.
- No Podfile or pod-based dependency workflow exists.
- Selected capability includes only the needed products.
- `WebexConnectConfig.plist` is present before real SDK startup.

## Runtime

- Register a User ID and confirm SDK status changes in Profile.
- Confirm App ID is visible in Profile, not in customer top bars.
- Confirm APNs token appears in a separate copyable card on a physical device.
- Change thread/message limits from Profile and confirm the local store policy updates.

## Threads

- Fetch threads and confirm real thread titles are shown.
- Create thread from the modal and confirm it appears immediately in the list.
- Open each thread and confirm the header uses that thread title and copyable thread ID.
- Closed thread: close a thread from the overflow menu and confirm composer/actions disappear.
- Reopen the thread and confirm composer/actions return.

## Messages

- Send text and confirm it appears once on the right.
- Confirm status moves from Sent to Delivered to Read in the same footer.
- Receive an agent/platform message in the visible thread and confirm it appears on the left.
- Receive a message for another thread and confirm inbox preview/unread updates without marking it read.
- Receive several messages, leave and re-enter the thread, and confirm realtime display plus delayed history reconciliation keep oldest messages at the top and newest messages at the bottom.
- Leave and re-enter a thread and confirm no seeded demo rows appear while SDK history loads.

## Rich Content

- Cards and carousel render as horizontal cards with inline images when URLs exist.
- Quick replies publish postback messages and disable only after success.
- Forms render editable fields, validate required values, and submit structured data.
- Image, file, audio, video, and location attachments render with correct controls.
- Attachment upload, download, and media URL refresh are handled inside thread context.

## Push

- Foreground push displays through the app notification path.
- Background/tapped push opens or updates the support area.
- Push payload details do not leak raw tokens or transaction IDs into chat bubbles.
""",
    )


def write_marker(options: Options) -> None:
    write_text(
        options.root / GENERATED_MARKER,
        json.dumps(
            {
                "generator": "webexconnect-ios-push-inapp-messaging-builder",
                "appName": options.app_name,
                "bundleId": options.bundle_id,
                "capability": options.capability,
                "sdkVersion": options.sdk_version,
                "dependencyManager": "spm",
                "threadLimit": options.thread_limit,
                "messageLimit": options.message_limit,
            },
            indent=2,
        ),
    )


def run_xcodebuild(options: Options, args: list[str]) -> None:
    command = ["xcodebuild", "-project", str(options.project_dir), "-scheme", TARGET_NAME, *args]
    subprocess.run(command, cwd=options.root, check=True)


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    ensure_can_write(options)
    copy_logo(options)
    resources = write_config(options)
    write_info_plist(options)
    write_entitlements(options)
    write_swift_sources(options)
    write_package_swift(options)
    write_xcode_project(options, resources)
    write_docs(options)
    write_marker(options)

    if options.resolve_packages:
        run_xcodebuild(options, ["-resolvePackageDependencies"])
    if options.build:
        run_xcodebuild(options, ["-destination", "generic/platform=iOS Simulator", "CODE_SIGNING_ALLOWED=NO", "build"])

    print(f"Generated Webex Connect iOS demo at {options.root}")
    print(f"Capability: {options.capability}; SPM SDK: {options.sdk_version}")
    print(f"Open {options.project_dir.name} in Xcode and configure signing before device Push QA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
