"""Provider protocol shared by every LLM backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMError(RuntimeError):
    """Raised for provider misconfiguration or failed completions."""


@dataclass(slots=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class Provider(Protocol):
    name: str

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResult: ...
