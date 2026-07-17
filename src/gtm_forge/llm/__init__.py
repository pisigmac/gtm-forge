"""Provider-agnostic LLM layer: anthropic, openai, ollama, or a fake for tests."""

from gtm_forge.llm.base import LLMError, LLMResult, Provider
from gtm_forge.llm.factory import build_provider

__all__ = ["LLMError", "LLMResult", "Provider", "build_provider"]
