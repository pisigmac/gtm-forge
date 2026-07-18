"""Shared fixtures: isolated home dir, state store, and a deterministic fake LLM."""

from __future__ import annotations

import pytest
import yaml

from gtm_forge.core.state import StateStore
from gtm_forge.llm.base import LLMResult


class FakeProvider:
    """Deterministic stand-in for a real LLM provider."""

    name = "fake"

    def __init__(self, text: str | None = None) -> None:
        self.text = text or (
            '{"score": 95, "strengths": ["strong hook"], "weaknesses": ["narrow"], '
            '"fix": "broaden the audience"}'
        )
        self.calls: list[dict[str, str]] = []

    def complete(self, *, system, prompt, model, max_tokens, temperature) -> LLMResult:
        self.calls.append({"system": system, "prompt": prompt})
        return LLMResult(text=self.text, model=model, input_tokens=100, output_tokens=50)


@pytest.fixture()
def state(tmp_path):
    store = StateStore(tmp_path / "state.db")
    yield store
    store.close()


@pytest.fixture()
def home(tmp_path, monkeypatch):
    """Isolated GTM_FORGE_HOME with an ollama config (no API key needed)."""
    d = tmp_path / "home"
    d.mkdir()
    monkeypatch.setenv("GTM_FORGE_HOME", str(d))
    (d / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {"provider": "ollama"},
                "paths": {"state_db": str(d / "state.db"), "output_dir": str(tmp_path / "out")},
                "notifications": {"on_success": False, "on_failure": False},
            }
        ),
        encoding="utf-8",
    )
    return d
