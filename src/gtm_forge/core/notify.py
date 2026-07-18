"""Run notifications: Slack webhook and SMTP email.

Notifications must never crash a run — every send is isolated and failures are
only logged. Configure via `notifications:` in config.yaml.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import httpx

from gtm_forge.config import Settings
from gtm_forge.core.logging import get_logger

log = get_logger("gtm_forge.notify")


def _send_slack(webhook_url: str, title: str, body: str) -> bool:
    try:
        resp = httpx.post(webhook_url, json={"text": f"*{title}*\n{body}"}, timeout=10.0)
        return resp.status_code < 300
    except Exception as exc:  # noqa: BLE001 - notifications must not crash runs
        log.warning("slack notification failed: %s", exc)
        return False


def _send_email(settings: Settings, title: str, body: str) -> bool:
    cfg = settings.notifications.email
    if not cfg.enabled or not cfg.recipients:
        return False
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(cfg.recipients)
    msg.set_content(body)
    try:
        username = os.environ.get(cfg.username_env) if cfg.username_env else None
        password = os.environ.get(cfg.password_env) if cfg.password_env else None
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as smtp:
            if cfg.starttls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("email notification failed: %s", exc)
        return False


def notify(settings: Settings, title: str, body: str, *, success: bool) -> list[str]:
    """Send to all configured channels that subscribed to this outcome."""
    cfg = settings.notifications
    if success and not cfg.on_success:
        return []
    if not success and not cfg.on_failure:
        return []
    sent: list[str] = []
    webhook = os.environ.get(cfg.slack_webhook_env)
    if webhook and _send_slack(webhook, title, body):
        sent.append("slack")
    if _send_email(settings, title, body):
        sent.append("email")
    return sent


def notify_run_finished(
    settings: Settings,
    *,
    skill: str,
    status: str,
    run_id: str,
    cost_usd: float,
    error: str | None,
    dry_run: bool,
) -> list[str]:
    if dry_run:
        return []
    success = status == "success"
    title = f"gtm-forge {skill}: {status}"
    body = f"run_id: {run_id}\ncost: ${cost_usd:.4f}"
    if error:
        body += f"\nerror: {error}"
    return notify(settings, title, body, success=success)
