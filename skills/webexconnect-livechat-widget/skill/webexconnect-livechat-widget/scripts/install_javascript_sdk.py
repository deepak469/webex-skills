#!/usr/bin/env python3
"""Install Webex Connect JavaScript SDK assets into a web project."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_SDK_URL = (
    "https://github.com/webex/webexconnect-javascript-sdk/"
    "releases/latest/download/dist.zip"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download/extract the latest Webex Connect JavaScript SDK dist.zip."
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Target web project root. Defaults to current directory.",
    )
    parser.add_argument(
        "--sdk-url",
        default=DEFAULT_SDK_URL,
        help="SDK dist.zip URL. Defaults to GitHub latest release asset.",
    )
    parser.add_argument(
        "--sdk-zip",
        help="Use a local dist.zip instead of downloading from GitHub.",
    )
    parser.add_argument(
        "--environment-file",
        help="Optional tenant-specific imi-environments.js file from Webex Connect UI.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing SDK, service worker, manifest, and environment files.",
    )
    parser.add_argument(
        "--skip-service-worker",
        action="store_true",
        help="Do not copy sw.min.js to the project root.",
    )
    parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Do not copy manifest.json to assets/manifest.",
    )
    parser.add_argument(
        "--copy-template",
        action="store_true",
        help="Copy the bundled vanilla widget template into the project root.",
    )
    return parser.parse_args()


def copy_file(src: Path, dest: Path, force: bool) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        return f"kept existing {dest}"
    shutil.copy2(src, dest)
    return f"installed {dest}"


def copy_template(project_root: Path, force: bool) -> list[str]:
    skill_root = Path(__file__).resolve().parents[1]
    template_root = skill_root / "assets" / "vanilla-widget-template"
    results: list[str] = []
    for src in sorted(path for path in template_root.rglob("*") if path.is_file()):
        rel = src.relative_to(template_root)
        dest = project_root / rel
        results.append(copy_file(src, dest, force))
    return results


def safe_extract(zip_path: Path, output_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            member_path = output_dir / member.filename
            resolved = member_path.resolve()
            if not str(resolved).startswith(str(output_dir.resolve())):
                raise ValueError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(output_dir)


def find_required(root: Path, filename: str) -> Path:
    matches = [
        path
        for path in root.rglob(filename)
        if "__MACOSX" not in path.parts and path.is_file()
    ]
    if not matches:
        raise FileNotFoundError(f"Could not find {filename} in SDK archive")
    return matches[0]


def download(url: str, dest: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            dest.write_bytes(response.read())
            return
    except Exception as error:
        curl = shutil.which("curl")
        if not curl:
            raise RuntimeError(
                f"Python download failed and curl is not available: {error}"
            ) from error
        subprocess.run(
            [curl, "-L", "--fail", "-o", str(dest), url],
            check=True,
        )


def write_environment_example(dest: Path) -> str:
    example = dest.with_name("imi-environments.example.js")
    if example.exists():
        return f"kept existing {example}"
    example.write_text(
        """// Download the real imi-environments.js from the Webex Connect UI.
// The file is tenant-specific and must contain asset.appId, asset.appSecret,
// target, pathConfig.assetPath, pathConfig.root, and notification settings.
window.__WEBEX_CONNECT_ENVIRONMENT_REQUIRED__ = true;
""",
        encoding="utf-8",
    )
    return f"created {example}"


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="webexconnect-sdk-") as tmp:
        tmp_dir = Path(tmp)
        zip_path = Path(args.sdk_zip).resolve() if args.sdk_zip else tmp_dir / "dist.zip"
        if not args.sdk_zip:
            print(f"Downloading {args.sdk_url}")
            download(args.sdk_url, zip_path)

        extract_dir = tmp_dir / "extract"
        extract_dir.mkdir()
        safe_extract(zip_path, extract_dir)

        sdk_js = find_required(extract_dir, "webex-connect-sdk.min.js")
        sw_js = find_required(extract_dir, "sw.min.js")
        manifest = find_required(extract_dir, "manifest.json")

        results = [
            copy_file(sdk_js, project_root / "assets/js/webex-connect-sdk.min.js", args.force)
        ]
        if not args.skip_service_worker:
            results.append(copy_file(sw_js, project_root / "sw.min.js", args.force))
        if not args.skip_manifest:
            results.append(
                copy_file(manifest, project_root / "assets/manifest/manifest.json", args.force)
            )

        env_dest = project_root / "assets/js/imi-environments.js"
        if args.environment_file:
            results.append(copy_file(Path(args.environment_file).resolve(), env_dest, args.force))
        elif not env_dest.exists():
            env_dest.parent.mkdir(parents=True, exist_ok=True)
            results.append(write_environment_example(env_dest))
            results.append("missing tenant file: add assets/js/imi-environments.js from Webex Connect UI")
        else:
            results.append(f"found existing {env_dest}")

        if args.copy_template:
            results.extend(copy_template(project_root, args.force))

    print("\n".join(results))
    print("\nAdd these scripts before your widget code:")
    print('<script src="https://code.jquery.com/jquery-1.12.4.js"></script>')
    print('<script src="/assets/js/imi-environments.js"></script>')
    print('<script src="/assets/js/webex-connect-sdk.min.js"></script>')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
