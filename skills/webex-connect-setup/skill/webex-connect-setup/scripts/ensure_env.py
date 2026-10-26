#!/usr/bin/env python3
"""Create or safely extend a local Webex Connect .env file."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "env.example"
KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
MCP_URLS = {
    "ca": "https://agentic-server-platform.prodca1.ciscoccservice.com/mcp/cpaas",
    "eu": "https://agentic-server-platform.prodeu2.ciscoccservice.com/mcp/cpaas",
    "uk": "https://agentic-server-platform.prodeu1.ciscoccservice.com/mcp/cpaas",
    "us": "https://agentic-server-platform.produs1.ciscoccservice.com/mcp/cpaas",
    "in": "https://agentic-server-platform.prodin1.ciscoccservice.com/mcp/cpaas",
    "au": "https://agentic-server-platform.prodanz1.ciscoccservice.com/mcp/cpaas",
    "sg": "https://agentic-server-platform.prodsg1.ciscoccservice.com/mcp/cpaas",
}
REGIONS = {"ca", "eu", "uk", "us", "in", "au", "sg"}
NON_SECRET_KEYS = {
    "WEBEX_CONNECT_ENVIRONMENT",
    "WEBEX_CONNECT_TENANT_DOMAIN",
    "WEBEX_CONNECT_REGION",
    "WEBEX_CONNECT_ORGANIZATION_ID",
    "WEBEX_CONNECT_API_BASE",
    "WEBEX_CONNECT_MESSAGING_V1_URL",
    "WEBEX_CONNECT_MESSAGING_V2_URL",
    "WEBEX_CONNECT_VOICE_API_BASE",
    "WEBEX_CONNECT_CONTACT_POLICY_BASE",
    "WEBEX_CONNECT_PROFILE_API_BASE",
    "WEBEX_CONNECT_AUDIT_LOGS_BASE",
    "WEBEX_CONNECT_DIGITAL_ASSET_API_BASE",
    "WEBEX_CONNECT_MCP_SERVER_URL",
}


def key_names(lines: list[str]) -> list[str]:
    names = []
    for line in lines:
        match = KEY_RE.match(line)
        if match:
            names.append(match.group(1))
    return names


def parse_set(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--set must use KEY=VALUE")
    key, setting = value.split("=", 1)
    if key not in NON_SECRET_KEYS:
        raise argparse.ArgumentTypeError(f"--set cannot write secret or unsupported key {key!r}")
    if not setting or "\n" in setting or "\r" in setting:
        raise argparse.ArgumentTypeError(f"--set requires a non-empty single-line value for {key}")
    return key, setting


def resolved_endpoints(environment: str, region: str) -> dict[str, str]:
    if region not in REGIONS:
        raise ValueError(f"unsupported region {region!r}; use the current official endpoint reference")
    if environment == "sandbox":
        return {
            "WEBEX_CONNECT_ENVIRONMENT": environment,
            "WEBEX_CONNECT_REGION": region,
            "WEBEX_CONNECT_MCP_SERVER_URL": "",
        }

    api = f"https://api.{region}.webexconnect.io"
    digital_asset_hosts = {
        "ca": "https://assetmanagement.ca.webexconnect.io/connectapi",
        "eu": "https://assetmanagement.eu.webexconnect.io/connectapi",
        "uk": "https://assetmanagement.uk.webexconnect.io/connectapi",
        "us": "https://assetmanagement.us.webexconnect.io/connectapi",
        "in": "https://assetmanagement.in.webexconnect.io/connectapi",
        "au": "https://assetmanagement.au.webexconnect.io/connectapi",
        "sg": "https://assetmanagement.sg.webexconnect.io/connectapi",
    }
    values = {
        "WEBEX_CONNECT_ENVIRONMENT": environment,
        "WEBEX_CONNECT_REGION": region,
        "WEBEX_CONNECT_API_BASE": api,
        "WEBEX_CONNECT_MESSAGING_V1_URL": f"{api}/resources/v1/messaging",
        "WEBEX_CONNECT_MESSAGING_V2_URL": f"{api}/v2/messages",
        "WEBEX_CONNECT_VOICE_API_BASE": api,
        "WEBEX_CONNECT_CONTACT_POLICY_BASE": f"https://contactpolicy.{region}.webexconnect.io",
        "WEBEX_CONNECT_PROFILE_API_BASE": api,
        "WEBEX_CONNECT_AUDIT_LOGS_BASE": f"https://{region}.webexconnect.io",
        "WEBEX_CONNECT_DIGITAL_ASSET_API_BASE": digital_asset_hosts.get(region, ""),
        "WEBEX_CONNECT_MCP_SERVER_URL": MCP_URLS.get(region, ""),
    }
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="Target .env path")
    parser.add_argument(
        "--environment",
        choices=("sandbox", "production"),
        help="Selected environment; production resolves all documented regional endpoints",
    )
    parser.add_argument(
        "--region",
        choices=sorted(REGIONS),
        help="Confirmed Webex Connect tenant region",
    )
    parser.add_argument(
        "--set",
        action="append",
        type=parse_set,
        default=[],
        metavar="KEY=VALUE",
        help="Set a non-secret tenant or endpoint value; may be repeated",
    )
    args = parser.parse_args()
    if (args.environment is None) != (args.region is None):
        parser.error("--environment and --region must be provided together")

    target = args.env_file.expanduser()
    if target.is_symlink():
        print("Refusing to modify a symlinked .env path.", file=sys.stderr)
        return 2

    try:
        template_lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
        if target.exists():
            original = target.read_text(encoding="utf-8")
            lines = original.splitlines()
            existing_keys = key_names(lines)
            duplicates = sorted({key for key in existing_keys if existing_keys.count(key) > 1})
            if duplicates:
                print(f"Duplicate .env keys must be resolved locally: {', '.join(duplicates)}", file=sys.stderr)
                return 2
            missing = [line for line in template_lines if (m := KEY_RE.match(line)) and m.group(1) not in existing_keys]
            if missing:
                if lines and lines[-1].strip():
                    lines.append("")
                lines.extend(["# Added by scripts/ensure_env.py; populate required values locally.", *missing])
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            lines = template_lines

        current: dict[str, int] = {}
        for index, line in enumerate(lines):
            match = KEY_RE.match(line)
            if match:
                current[match.group(1)] = index
        resolved = resolved_endpoints(args.environment, args.region) if args.environment else {}
        for key, value in {**resolved, **dict(args.set)}.items():
            index = current.get(key)
            line = f"{key}={value}"
            if index is None:
                lines.append(line)
                current[key] = len(lines) - 1
            else:
                lines[index] = line

        payload = "\n".join(lines).rstrip() + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            os.chmod(temp_name, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(temp_name, target)
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    except (OSError, UnicodeError) as exc:
        print(f"Unable to safely update .env: {exc}", file=sys.stderr)
        return 1

    if args.environment == "production":
        print(f"Resolved regional API endpoints for {args.region}; existing secrets were preserved and not displayed.")
    print(f"Prepared {target} with required keys; existing values were preserved and secrets were not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
