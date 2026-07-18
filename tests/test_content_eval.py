"""Content eval panel: scoring, aggregation, gate logic, dry-run."""

import pytest
from conftest import FakeProvider

from gtm_forge.skills.content_eval.panel import dry_run_plan, extract_json, run_panel


def test_panel_passes_high_scores():
    provider = FakeProvider()  # always returns score 95
    report = run_panel(provider, idea="Test idea", gate=90, model="fake")
    assert len(report.scores) == 7
    assert report.mean == 95
    assert report.passed
    assert len(provider.calls) == 7


def test_panel_fails_low_scores():
    provider = FakeProvider('{"score": 40, "strengths": [], "weaknesses": ["bland"], "fix": "start over"}')
    report = run_panel(provider, idea="Weak idea", gate=90, model="fake")
    assert report.mean == 40
    assert not report.passed
    assert report.weakest is not None


def test_extract_json_tolerates_fences():
    text = 'Sure! Here is the JSON:\n```json\n{"score": 88, "fix": "x"}\n```\nDone.'
    assert extract_json(text)["score"] == 88


def test_extract_json_missing():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_score_clamped():
    provider = FakeProvider('{"score": 140, "fix": "n/a"}')
    report = run_panel(provider, idea="x", gate=90, model="fake")
    assert all(s.score == 100 for s in report.scores)


def test_dry_run_plan():
    plan = dry_run_plan("An idea", gate=85)
    assert plan["gate"] == 85
    assert len(plan["experts"]) == 7
    assert plan["estimated_input_tokens"] > 0


def test_markdown_report():
    report = run_panel(FakeProvider(), idea="X", gate=90, model="fake")
    md = report.to_markdown()
    assert "PASS" in md
    assert "| Expert | Score | Top fix |" in md
