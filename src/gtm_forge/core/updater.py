"""Self-update: check GitHub Releases for a newer version and upgrade the install."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

import httpx

GITHUB_REPO = "pisigmac/gtm-forge"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    current: str
    latest: str | None
    update_available: bool
    url: str | None = None
    error: str | None = None


def _parse_version(tag: str) -> tuple[int, ...]:
    return tuple(int(p) for p in tag.lstrip("v").split(".") if p.isdigit())


def check_for_update(current: str, *, timeout_s: float = 5.0) -> UpdateInfo:
    """Ask GitHub for the latest release. Network failures are non-fatal."""
    try:
        resp = httpx.get(RELEASES_API, timeout=timeout_s, follow_redirects=True)
        if resp.status_code == 404:
            return UpdateInfo(current, None, False, error="no releases published yet")
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 - update checks must never break the CLI
        return UpdateInfo(current, None, False, error=str(exc))
    latest = str(data.get("tag_name", "")).lstrip("v")
    available = bool(latest) and _parse_version(latest) > _parse_version(current)
    return UpdateInfo(current, latest or None, available, url=data.get("html_url"))


def self_update() -> tuple[bool, str]:
    """Upgrade the installed package using whichever installer owns it."""
    if shutil.which("uv"):
        cmd = ["uv", "tool", "upgrade", "gtm-forge"]
    elif shutil.which("pipx"):
        cmd = ["pipx", "upgrade", "gtm-forge"]
    else:
        return False, "Neither uv nor pipx found. Run: pip install --upgrade gtm-forge"
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or proc.stdout.strip()
    return True, proc.stdout.strip() or "Upgraded."
