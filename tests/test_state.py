"""SQLite state store: runs, costs, breaker, kv."""

import pytest


def test_run_lifecycle(state):
    state.start_run("r1", "eval", "run", dry_run=False)
    state.finish_run("r1", "success")
    runs = state.list_runs()
    assert runs[0]["run_id"] == "r1"
    assert runs[0]["status"] == "success"
    assert runs[0]["finished_at"] is not None


def test_cost_ledger(state):
    state.start_run("r1", "eval", "run", dry_run=False)
    state.record_cost("r1", "claude-sonnet-4-5", 1000, 500, 0.0105)
    state.record_cost("r1", "claude-sonnet-4-5", 2000, 100, 0.0075)
    assert state.run_cost("r1") == pytest.approx(0.018)
    summary = state.costs_summary()
    assert summary[0]["model"] == "claude-sonnet-4-5"
    assert summary[0]["calls"] == 2


def test_kv_roundtrip(state):
    assert state.kv_get("missing") is None
    state.kv_set("key", "value")
    state.kv_set("key", "updated")
    assert state.kv_get("key") == "updated"


def test_breaker_default_row(state):
    row = state.breaker_get("never-seen")
    assert row["state"] == "closed"
    assert row["failures"] == 0
