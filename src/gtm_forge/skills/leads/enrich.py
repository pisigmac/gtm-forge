"""Cascade email verification: try providers in order, first conclusive answer wins.

Provider order comes from config (`leads.email_providers`). The built-in "regex"
provider is free and always available — syntax + disposable-domain check. Paid
providers are attempted only when their API key is present; without a key they
report "unknown" and the cascade moves on. Dry-run prints the planned cascade
without spending a single credit.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

#: Common disposable providers. Extend via PR, not config, to keep audit trails identical.
DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "tempmail.com",
    "guerrillamail.com",
    "10minutemail.com",
    "yopmail.com",
    "throwawaymail.com",
}


@dataclass(slots=True)
class VerifyResult:
    email: str
    provider: str
    status: str  # valid | invalid | disposable | unknown
    detail: str = ""

    @property
    def conclusive(self) -> bool:
        return self.status in {"valid", "invalid", "disposable"}


def verify_syntax(email: str) -> VerifyResult:
    """Free built-in check: syntax plus disposable-domain screening."""
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        return VerifyResult(email, "regex", "invalid", "malformed address")
    domain = email.rsplit("@", 1)[1]
    if domain in DISPOSABLE_DOMAINS:
        return VerifyResult(email, "regex", "disposable", f"disposable domain: {domain}")
    return VerifyResult(email, "regex", "unknown", "syntax ok; deliverability unverified")


class ApiVerifier(Protocol):
    name: str

    def verify(self, email: str) -> VerifyResult: ...


class NeverBounceVerifier:
    name = "neverbounce"
    endpoint = "https://api.neverbounce.com/v4/single/check"

    def __init__(self, api_key: str | None, timeout_s: float = 10.0) -> None:
        self._key = api_key
        self._timeout = timeout_s

    def verify(self, email: str) -> VerifyResult:
        if not self._key:
            return VerifyResult(email, self.name, "unknown", "no API key; skipped")
        try:
            resp = httpx.get(
                self.endpoint,
                params={"key": self._key, "email": email},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            result = str(resp.json().get("result", "")).lower()
        except Exception as exc:  # noqa: BLE001 - a flaky provider must not kill the cascade
            return VerifyResult(email, self.name, "unknown", f"request failed: {exc}")
        status = {"valid": "valid", "invalid": "invalid", "disposable": "disposable"}.get(result, "unknown")
        return VerifyResult(email, self.name, status, result or "unrecognized response")


class ZeroBounceVerifier:
    name = "zerobounce"
    endpoint = "https://api.zerobounce.net/v2/validate"

    def __init__(self, api_key: str | None, timeout_s: float = 10.0) -> None:
        self._key = api_key
        self._timeout = timeout_s

    def verify(self, email: str) -> VerifyResult:
        if not self._key:
            return VerifyResult(email, self.name, "unknown", "no API key; skipped")
        try:
            resp = httpx.get(
                self.endpoint,
                params={"api_key": self._key, "email": email},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            result = str(resp.json().get("status", "")).lower()
        except Exception as exc:  # noqa: BLE001
            return VerifyResult(email, self.name, "unknown", f"request failed: {exc}")
        status = {"valid": "valid", "invalid": "invalid"}.get(result, "unknown")
        return VerifyResult(email, self.name, status, result or "unrecognized response")


class _RegexVerifier:
    name = "regex"

    def verify(self, email: str) -> VerifyResult:
        return verify_syntax(email)


def _key_for(name: str) -> str | None:
    return os.environ.get(f"GTM_FORGE_{name.upper()}_KEY")


def build_cascade(providers: list[str], *, timeout_s: float = 10.0) -> list[ApiVerifier]:
    """Instantiate the verifier chain in the configured order."""
    cascade: list[ApiVerifier] = []
    for name in providers:
        if name == "neverbounce":
            cascade.append(NeverBounceVerifier(_key_for("neverbounce"), timeout_s))
        elif name == "zerobounce":
            cascade.append(ZeroBounceVerifier(_key_for("zerobounce"), timeout_s))
        elif name == "regex":
            cascade.append(_RegexVerifier())
        else:
            raise ValueError(f"Unknown email provider '{name}'.")
    return cascade


def verify_cascade(
    email: str,
    providers: list[str],
    *,
    timeout_s: float = 10.0,
    cascade: list[ApiVerifier] | None = None,
) -> tuple[VerifyResult, list[VerifyResult]]:
    """Walk the cascade. Returns (final verdict, full audit trail)."""
    chain = cascade if cascade is not None else build_cascade(providers, timeout_s=timeout_s)
    trail: list[VerifyResult] = []
    final = VerifyResult(email, "cascade", "unknown", "no providers configured")
    for verifier in chain:
        result = verifier.verify(email)
        trail.append(result)
        final = result
        if result.conclusive:
            break
    return final, trail
