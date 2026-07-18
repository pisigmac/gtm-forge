"""Build a provider from settings and wrap it with retry, circuit breaking,
cost tracking, and per-run budget enforcement."""

from __future__ import annotations

from gtm_forge.config import Settings
from gtm_forge.core.breaker import CircuitBreaker, retry_call
from gtm_forge.core.costs import check_budget, estimate_cost
from gtm_forge.core.credentials import resolve_secret
from gtm_forge.core.logging import get_logger
from gtm_forge.core.state import StateStore
from gtm_forge.llm.base import LLMError, LLMResult, Provider

log = get_logger("gtm_forge.llm")

_DEFAULT_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama": None,
}


class TrackedProvider:
    """Wraps a raw Provider with resilience and cost accounting."""

    def __init__(
        self,
        inner: Provider,
        settings: Settings,
        state: StateStore | None,
        run_id: str,
    ) -> None:
        self._inner = inner
        self._settings = settings
        self._state = state
        self._run_id = run_id
        self.name = inner.name

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> LLMResult:
        cfg = self._settings.resilience
        breaker = (
            CircuitBreaker(
                self._state,
                f"llm:{self.name}",
                threshold=cfg.breaker_threshold,
                cooldown_s=cfg.breaker_cooldown_s,
            )
            if self._state
            else None
        )

        def call() -> LLMResult:
            return retry_call(
                lambda: self._inner.complete(
                    system=system,
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                retries=cfg.retries,
                base_s=cfg.backoff_base_s,
                max_s=cfg.backoff_max_s,
            )

        result = breaker.guard(call) if breaker else call()

        if self._settings.costs.track and self._state:
            cost = estimate_cost(
                model, result.input_tokens, result.output_tokens, self._settings.costs.prices
            )
            self._state.record_cost(self._run_id, model, result.input_tokens, result.output_tokens, cost)
            spent = self._state.run_cost(self._run_id)
            log.info(
                "llm call",
                extra={"run_id": self._run_id, "model": model, "cost_usd": round(cost, 6)},
            )
            check_budget(spent, self._settings.costs.budget_usd_per_run)
        return result


def build_provider(
    settings: Settings, state: StateStore | None = None, run_id: str = "adhoc"
) -> TrackedProvider:
    """Instantiate the configured provider and wrap it with tracking."""
    llm = settings.llm
    provider = llm.provider.lower()

    if provider == "anthropic":
        from gtm_forge.llm.anthropic import AnthropicProvider

        key = resolve_secret(llm.api_key_env or _DEFAULT_KEY_ENV["anthropic"])
        inner: Provider = AnthropicProvider(
            api_key=key, base_url=llm.base_url, timeout_s=llm.request_timeout_s
        )
    elif provider == "openai":
        from gtm_forge.llm.openai import OpenAIProvider

        key = resolve_secret(llm.api_key_env or _DEFAULT_KEY_ENV["openai"])
        inner = OpenAIProvider(api_key=key, base_url=llm.base_url, timeout_s=llm.request_timeout_s)
    elif provider == "ollama":
        from gtm_forge.llm.ollama import OllamaProvider

        inner = OllamaProvider(base_url=llm.base_url, timeout_s=llm.request_timeout_s)
    else:
        raise LLMError(f"Unknown llm.provider '{llm.provider}'. Expected one of: anthropic, openai, ollama.")
    return TrackedProvider(inner, settings, state, run_id)
