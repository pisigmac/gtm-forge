"""Config-driven settings for gtm-forge.

Everything is controlled by a single YAML file (default: ~/.gtm-forge/config.yaml).
Override the location with --config, the GTM_FORGE_CONFIG env var, or change the
home directory entirely with GTM_FORGE_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

APP_DIR_NAME = ".gtm-forge"
CONFIG_FILENAME = "config.yaml"
ENV_CONFIG = "GTM_FORGE_CONFIG"
ENV_HOME = "GTM_FORGE_HOME"

#: Default model used when `llm.model` is not set, per provider.
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4.1-mini",
    "ollama": "llama3.1",
}

#: Default price table in USD per 1M tokens. These are starting points only —
#: edit `costs.prices` in your config.yaml to match your actual plan.
DEFAULT_PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "gpt-4.1": {"input": 2.0, "output": 8.0},
    "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
    "gpt-4.1-nano": {"input": 0.1, "output": 0.4},
    "llama3.1": {"input": 0.0, "output": 0.0},
}


def default_home() -> Path:
    """Directory that holds config.yaml, state.db, and cached artifacts."""
    return Path(os.environ.get(ENV_HOME, Path.home() / APP_DIR_NAME))


def config_path(explicit: str | Path | None = None) -> Path:
    """Resolve the config file path: explicit flag > env var > default home."""
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get(ENV_CONFIG)
    if env:
        return Path(env).expanduser()
    return default_home() / CONFIG_FILENAME


class LLMSettings(BaseModel):
    provider: str = "anthropic"  # anthropic | openai | ollama
    model: str | None = None  # None -> provider default from DEFAULT_MODELS
    api_key_env: str | None = None  # env var holding the API key
    base_url: str | None = None  # custom endpoint; ollama defaults to localhost
    max_tokens: int = 4096
    temperature: float = 0.2
    request_timeout_s: float = 60.0

    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "unknown")


class Paths(BaseModel):
    state_db: Path = Field(default_factory=lambda: default_home() / "state.db")
    output_dir: Path = Path("gtm-output")


class ResilienceSettings(BaseModel):
    retries: int = 3
    backoff_base_s: float = 0.5
    backoff_max_s: float = 8.0
    breaker_threshold: int = 5
    breaker_cooldown_s: float = 60.0


class CostSettings(BaseModel):
    track: bool = True
    budget_usd_per_run: float | None = None  # hard stop when exceeded; None = unlimited
    prices: dict[str, dict[str, float]] = Field(default_factory=lambda: dict(DEFAULT_PRICES))


class EmailSettings(BaseModel):
    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 25
    sender: str = "gtm-forge@localhost"
    recipients: list[str] = Field(default_factory=list)
    username_env: str | None = None
    password_env: str | None = None
    starttls: bool = True


class NotificationSettings(BaseModel):
    slack_webhook_env: str = "GTM_FORGE_SLACK_WEBHOOK"
    on_success: bool = False
    on_failure: bool = True
    email: EmailSettings = Field(default_factory=EmailSettings)


class VideoSettings(BaseModel):
    whisper: str = "local"  # local (whisper.cpp CLI) | openai (Whisper API)
    whisper_bin: str = "whisper-cli"
    whisper_model_path: str = "models/ggml-base.en.bin"
    ffmpeg_bin: str = "ffmpeg"
    window_seconds: int = 90  # transcript chunk size offered to the scorer
    clip_count: int = 4


class LeadSettings(BaseModel):
    # Cascade order for email verification. "regex" is the free built-in fallback.
    email_providers: list[str] = Field(default_factory=lambda: ["neverbounce", "zerobounce", "regex"])
    http_timeout_s: float = 10.0


class FeatureFlags(BaseModel):
    flags: dict[str, bool] = Field(default_factory=dict)

    def enabled(self, name: str, default: bool = False) -> bool:
        return bool(self.flags.get(name, default))


class Settings(BaseModel):
    version: int = 1
    llm: LLMSettings = Field(default_factory=LLMSettings)
    paths: Paths = Field(default_factory=Paths)
    resilience: ResilienceSettings = Field(default_factory=ResilienceSettings)
    costs: CostSettings = Field(default_factory=CostSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    leads: LeadSettings = Field(default_factory=LeadSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    # Free-form per-skill overrides (ICP weights, expert rosters, thresholds...).
    skills: dict[str, dict[str, Any]] = Field(default_factory=dict)


def load_settings(explicit: str | Path | None = None) -> Settings:
    """Load settings from YAML; fall back to defaults when the file is absent."""
    path = config_path(explicit)
    if not path.exists():
        return Settings()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping at the top level.")
    return Settings.model_validate(raw)


def save_settings(settings: Settings, path: str | Path | None = None) -> Path:
    """Write settings to disk, creating the parent directory as needed."""
    target = Path(path).expanduser() if path else config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.model_dump(mode="json")
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return target


def starter_config() -> Settings:
    """A safe starter config used by `gtm init`."""
    return Settings()
