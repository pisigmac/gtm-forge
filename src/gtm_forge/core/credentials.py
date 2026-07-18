"""Secret resolution: environment variable first, OS keychain second.

Never hardcode keys. Store them in your shell env (`export ANTHROPIC_API_KEY=...`)
or in the OS keychain via `gtm keys set` (uses the optional `keyring` package).
"""

from __future__ import annotations

import os


class CredentialError(RuntimeError):
    pass


def resolve_secret(
    env_name: str | None,
    *,
    keyring_service: str | None = None,
    keyring_username: str | None = None,
    required: bool = False,
) -> str | None:
    """Resolve a secret from env, then keychain. Returns None unless required."""
    if env_name:
        value = os.environ.get(env_name)
        if value:
            return value
    if keyring_service and keyring_username:
        try:
            import keyring  # type: ignore[import-not-found]
        except ImportError:
            pass
        else:
            value = keyring.get_password(keyring_service, keyring_username)
            if value:
                return str(value)
    if required:
        raise CredentialError(
            f"Missing secret. Set env var {env_name or '(unspecified)'} "
            + (
                f"or store it in the OS keychain as {keyring_service}/{keyring_username}."
                if keyring_service
                else "or configure the OS keychain."
            )
        )
    return None


def store_secret(service: str, username: str, value: str) -> bool:
    """Store a secret in the OS keychain. Returns False when keyring is unavailable."""
    try:
        import keyring  # type: ignore[import-not-found]
    except ImportError:
        return False
    keyring.set_password(service, username, value)
    return True
