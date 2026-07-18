"""OpenAI provider (optional dependency: gtm-forge[openai]). Works with any
OpenAI-compatible endpoint via base_url."""

from __future__ import annotations

from gtm_forge.llm.base import LLMError, LLMResult


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, api_key: str | None, base_url: str | None, timeout_s: float) -> None:
        try:
            import openai
        except ImportError as exc:
            raise LLMError(
                "The 'openai' package is not installed. Run: pip install 'gtm-forge[openai]'"
            ) from exc
        kwargs: dict[str, object] = {"timeout": timeout_s}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResult:
        resp = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        choice = resp.choices[0]
        usage = getattr(resp, "usage", None)
        return LLMResult(
            text=choice.message.content or "",
            model=model,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )
