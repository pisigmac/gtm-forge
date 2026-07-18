"""Cost estimation and per-run budget enforcement."""

from __future__ import annotations

from gtm_forge.config import DEFAULT_PRICES


class BudgetExceededError(RuntimeError):
    """Raised when a run exceeds its configured per-run USD budget."""


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    prices: dict[str, dict[str, float]] | None = None,
) -> float:
    """USD cost for one call. Unknown models cost 0.0 and count as untracked."""
    table = prices or DEFAULT_PRICES
    price = table.get(model)
    if price is None:
        return 0.0
    return (input_tokens * price.get("input", 0.0) + output_tokens * price.get("output", 0.0)) / 1_000_000


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 4) used for dry-run previews."""
    return max(1, len(text) // 4)


def check_budget(spent_usd: float, budget_usd: float | None) -> None:
    if budget_usd is not None and spent_usd > budget_usd:
        raise BudgetExceededError(
            f"Run budget exceeded: ${spent_usd:.4f} spent, budget is ${budget_usd:.4f}. "
            "Raise costs.budget_usd_per_run in config.yaml to continue."
        )
