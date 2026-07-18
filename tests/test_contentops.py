"""Deterministic editorial calendar grid and markdown rendering."""

from __future__ import annotations

import json
from datetime import date

import pytest
from conftest import FakeProvider

from gtm_forge.skills.contentops.calendar import (
    deterministic_calendar,
    llm_calendar,
    render_markdown,
)

PILLARS = ["growth", "product", "founder lessons"]


def test_calendar_entry_count_matches_grid() -> None:
    entries = deterministic_calendar(PILLARS, weeks=4, posts_per_week=3, start=date(2026, 7, 20))
    assert len(entries) == 12


def test_default_posting_days_are_mon_wed_fri() -> None:
    entries = deterministic_calendar(PILLARS, weeks=2, posts_per_week=3, start=date(2026, 7, 20))
    assert {e.day.weekday() for e in entries} == {0, 2, 4}


def test_posts_per_week_scales_grid() -> None:
    one = deterministic_calendar(PILLARS, weeks=2, posts_per_week=1, start=date(2026, 7, 20))
    five = deterministic_calendar(PILLARS, weeks=2, posts_per_week=5, start=date(2026, 7, 20))
    assert len(one) == 2
    assert len(five) == 10
    assert {e.day.weekday() for e in one} == {0}


def test_pillars_rotate_in_order() -> None:
    entries = deterministic_calendar(PILLARS, weeks=1, posts_per_week=3, start=date(2026, 7, 20))
    assert [e.pillar for e in entries] == PILLARS
    entries2 = deterministic_calendar(PILLARS, weeks=2, posts_per_week=3, start=date(2026, 7, 20))
    assert [e.pillar for e in entries2] == PILLARS * 2


def test_start_bumps_forward_to_monday() -> None:
    # 2026-07-18 is a Saturday; the grid should start on Monday 2026-07-20.
    entries = deterministic_calendar(PILLARS, weeks=1, posts_per_week=1, start=date(2026, 7, 18))
    assert entries[0].day == date(2026, 7, 20)


def test_empty_pillars_raise() -> None:
    with pytest.raises(ValueError, match="pillar"):
        deterministic_calendar([], weeks=1, posts_per_week=1)


def test_render_markdown_has_header_and_rows() -> None:
    entries = deterministic_calendar(PILLARS, weeks=1, posts_per_week=2, start=date(2026, 7, 20))
    md = render_markdown(entries, title="Q3 plan")
    assert md.startswith("# Q3 plan")
    assert "| Date | Pillar | Format | Title | Hook |" in md
    assert md.count("\n|") >= 2
    assert "growth" in md


def test_llm_calendar_fills_titles_over_grid() -> None:
    payload = [
        {
            "day": "2026-07-20",
            "pillar": "growth",
            "format": "how-to",
            "title": "How we cut CAC by 40%",
            "hook": "We stopped doing the obvious thing.",
        }
    ]
    provider = FakeProvider(text=json.dumps(payload))
    entries = llm_calendar(
        provider,
        ["growth"],
        weeks=1,
        posts_per_week=1,
        start=date(2026, 7, 20),
        model="fake-model",
    )
    assert len(entries) == 1
    assert entries[0].title == "How we cut CAC by 40%"
    assert entries[0].hook.startswith("We stopped")
    assert entries[0].day == date(2026, 7, 20)
