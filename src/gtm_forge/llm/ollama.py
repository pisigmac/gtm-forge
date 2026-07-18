"""Ollama provider: fully local, zero API cost, talks over plain HTTP."""

from __future__ import annotations

import httpx

from gtm_forge.llm.base import LLMError, LLMResult

DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    name = "ollama"

    def __init__(self, *, base_url: str | None, timeout_s: float) -> None:
        self._base = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout_s

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResult:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = httpx.post(f"{self._base}/api/chat", json=payload, timeout=self._timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        data = resp.json()
        return LLMResult(
            text=str(data.get("message", {}).get("content", "")),
            model=model,
            input_tokens=int(data.get("prompt_eval_count", 0) or 0),
            output_tokens=int(data.get("eval_count", 0) or 0),
        )
