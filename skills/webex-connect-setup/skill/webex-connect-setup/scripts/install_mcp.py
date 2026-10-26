#!/usr/bin/env python3
"""Register the region-matched Webex Connect Production MCP endpoint.

This helper never accepts, stores, prints, or modifies bearer tokens. The user
must complete authentication through the selected MCP host after registration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


MCP_URLS = {
    "ca": "https://agentic-server-platform.prodca1.ciscoccservice.com/mcp/cpaas",
    "eu": "https://agentic-server-platform.prodeu2.ciscoccservice.com/mcp/cpaas",
    "uk": "https://agentic-server-platform.prodeu1.ciscoccservice.com/mcp/cpaas",
    "us": "https://agentic-server-platform.produs1.ciscoccservice.com/mcp/cpaas",
    "in": "https://agentic-server-platform.prodin1.ciscoccservice.com/mcp/cpaas",
    "au": "https://agentic-server-platform.prodanz1.ciscoccservice.com/mcp/cpaas",
    "sg": "https://agentic-server-platform.prodsg1.ciscoccservice.com/mcp/cpaas",
}
SERVER_NAME = "webex_connect_cpaas"


def atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
        os.chmod(path, mode)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def install_codex(config_path: Path, url: str, dry_run: bool) -> str:
    section = f"[mcp_servers.{SERVER_NAME}]"
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    section_re = re.compile(
        rf"(?ms)^\[mcp_servers\.{re.escape(SERVER_NAME)}\]\s*$.*?(?=^\[|\Z)"
    )
    replacement = f'{section}\nenabled = true\nurl = "{url}"\n'
    match = section_re.search(existing)
    if match:
        block = match.group(0)
        if "http_headers" in block or "headers" in block:
            replacement = block
            replacement = re.sub(r'(?m)^url\s*=\s*"[^"]*"\s*$', f'url = "{url}"', replacement)
            replacement = re.sub(r"(?m)^enabled\s*=\s*(true|false)\s*$", "enabled = true", replacement)
        new_text = existing[: match.start()] + replacement.rstrip() + "\n" + existing[match.end() :].lstrip("\n")
    else:
        separator = "\n" if existing and not existing.endswith("\n\n") else ""
        new_text = existing.rstrip() + separator + ("\n" if existing else "") + replacement
    if not dry_run:
        atomic_write(config_path, new_text)
    return str(config_path)


def install_cursor(config_path: Path, url: str, dry_run: bool) -> str:
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot safely update {config_path}: invalid JSON ({exc})") from exc
    else:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Cannot safely update {config_path}: the root must be a JSON object")
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"Cannot safely update {config_path}: mcpServers must be an object")
    entry = servers.setdefault(SERVER_NAME, {})
    if not isinstance(entry, dict):
        raise ValueError(f"Cannot safely update {config_path}: existing server entry is not an object")
    entry["url"] = url
    if not dry_run:
        atomic_write(config_path, json.dumps(data, indent=2) + "\n")
    return str(config_path)


def install_claude(url: str, dry_run: bool) -> str:
    command = ["claude", "mcp", "add", "--transport", "http", SERVER_NAME, url]
    if dry_run:
        return " ".join(command)
    if shutil.which("claude") is None:
        raise RuntimeError("claude CLI was not found; run the printed command manually")
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "Claude Code MCP registration failed")
    return " ".join(command)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=("sandbox", "production"))
    parser.add_argument("--region", required=True, choices=sorted(MCP_URLS))
    parser.add_argument("--client", required=True, choices=("codex", "claude", "cursor"))
    parser.add_argument("--config", type=Path, help="Override the Codex or Cursor config path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.environment != "production":
        parser.error("Sandbox has no Webex Connect MCP endpoint; use the Sandbox APIs instead")
    url = MCP_URLS[args.region]
    try:
        if args.client == "codex":
            path = args.config or Path.home() / ".codex" / "config.toml"
            target = install_codex(path, url, args.dry_run)
        elif args.client == "cursor":
            path = args.config or Path.home() / ".cursor" / "mcp.json"
            target = install_cursor(path, url, args.dry_run)
        else:
            target = install_claude(url, args.dry_run)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"MCP registration failed: {exc}", file=sys.stderr)
        return 1

    action = "would register" if args.dry_run else "registered"
    print(f"{action} {SERVER_NAME} for region {args.region} at {url}")
    print(f"Target: {target}")
    print("No bearer token was written. Complete authentication in the MCP host.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
