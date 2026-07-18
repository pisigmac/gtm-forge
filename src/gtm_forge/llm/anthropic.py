"""Anthropic provider (optional dependency: gtm-forge[anthropic])."""

from __future__ import annotations

from gtm_forge.llm.base import LLMError, LLMResult


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, *, api_key: str | None, base_url: str | None, timeout_s: float) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "The 'anthropic' package is not installed. Run: pip install 'gtm-forge[anthropic]'"
            ) from exc
        kwargs: dict[str, object] = {"timeout": timeout_s}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.Anthropic(**kwargs)

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResult:
        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        usage = getattr(resp, "usage", None)
        return LLMResult(
            text=text,
            model=model,
            input_tokens=int(getattr(usage, "input_tokens", 0)),
            output_tokens=int(getattr(usage, "output_tokens", 0)),
        )
