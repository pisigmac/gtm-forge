"""Config loading: defaults, YAML roundtrip, env overrides, and bad files."""

from __future__ import annotations

import pytest
import yaml

from gtm_forge.config import (
    ENV_CONFIG,
    ENV_HOME,
    Settings,
    config_path,
    load_settings,
    save_settings,
)


def test_defaults_are_sane() -> None:
    s = Settings()
    assert s.version == 1
    assert s.llm.provider == "anthropic"
    assert s.llm.resolved_model() == "claude-sonnet-4-5"
    assert s.resilience.retries == 3
    assert s.resilience.breaker_threshold == 5
    assert s.costs.track is True
    assert s.costs.budget_usd_per_run is None
    assert s.notifications.on_failure is True


def test_resolved_model_respects_override() -> None:
    s = Settings(llm={"provider": "openai", "model": "gpt-4.1"})  # type: ignore[arg-type]
    assert s.llm.resolved_model() == "gpt-4.1"


def test_yaml_roundtrip(tmp_path) -> None:
    path = tmp_path / "conf" / "config.yaml"
    original = Settings(llm={"provider": "ollama"}, resilience={"retries": 1})  # type: ignore[arg-type]
    save_settings(original, path)
    loaded = load_settings(path)
    assert loaded.llm.provider == "ollama"
    assert loaded.resilience.retries == 1
    assert loaded.llm.resolved_model() == "llama3.1"


def test_env_var_selects_config_file(tmp_path, monkeypatch) -> None:
    path = tmp_path / "elsewhere.yaml"
    path.write_text(yaml.safe_dump({"llm": {"provider": "openai"}}), encoding="utf-8")
    monkeypatch.setenv(ENV_CONFIG, str(path))
    assert config_path() == path
    assert load_settings().llm.provider == "openai"


def test_home_env_var_moves_default_config(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(ENV_CONFIG, raising=False)
    monkeypatch.setenv(ENV_HOME, str(tmp_path / "h"))
    assert config_path() == tmp_path / "h" / "config.yaml"


def test_missing_file_falls_back_to_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_CONFIG, str(tmp_path / "nope.yaml"))
    assert load_settings().llm.provider == "anthropic"


def test_malformed_top_level_raises(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_settings(path)
