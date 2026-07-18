"""Cost estimation math and budget enforcement."""

from __future__ import annotations

import pytest

from gtm_forge.core.costs import (
    BudgetExceededError,
    check_budget,
    estimate_cost,
    estimate_tokens,
)


def test_known_model_cost_math() -> None:
    # claude-sonnet-4-5: $3/M input, $15/M output.
    cost = estimate_cost("claude-sonnet-4-5", 1_000_000, 100_000)
    assert cost == pytest.approx(3.0 + 1.5)


def test_unknown_model_is_free_and_untracked() -> None:
    assert estimate_cost("some-future-model", 10_000, 10_000) == 0.0


def test_custom_price_table_overrides_defaults() -> None:
    prices = {"my-model": {"input": 1.0, "output": 2.0}}
    assert estimate_cost("my-model", 1_000_000, 1_000_000, prices) == pytest.approx(3.0)
    # The custom table replaces the default one entirely.
    assert estimate_cost("claude-sonnet-4-5", 1_000, 1_000, prices) == 0.0


def test_estimate_tokens_is_rough_but_monotonic() -> None:
    assert estimate_tokens("") == 1  # never zero
    assert estimate_tokens("abcd") == 1
    long_text = "x" * 4000
    assert estimate_tokens(long_text) == 1000


def test_check_budget_allows_spend_within_limit() -> None:
    check_budget(0.50, 1.00)  # should not raise
    check_budget(1.00, 1.00)  # exactly at the limit is fine


def test_check_budget_unlimited_when_none() -> None:
    check_budget(1_000_000.0, None)  # should not raise


def test_check_budget_raises_over_limit() -> None:
    with pytest.raises(BudgetExceededError, match="budget"):
        check_budget(1.01, 1.00)
