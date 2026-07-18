"""Editorial calendar generation.

Two modes: LLM-generated (creative titles and hooks) or deterministic rotation
(pillar + format grid, no API calls — useful offline, in CI, and as a fallback
when the model is unavailable).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

from gtm_forge.llm.base import Provider

FORMATS = ["how-to", "case study", "contrarian take", "checklist", "story", "data breakdown"]


@dataclass(slots=True)
class CalendarEntry:
    day: date
    pillar: str
    format: str
    title: str
    hook: str = ""


def deterministic_calendar(
    pillars: list[str],
    *,
    weeks: int = 4,
    posts_per_week: int = 3,
    start: date | None = None,
) -> list[CalendarEntry]:
    """Rotate pillars x formats across posting days (Mon/Wed/Fri pattern)."""
    if not pillars:
        raise ValueError("At least one content pillar is required.")
    start = start or date.today()
    # Move start to the next Monday for a clean grid.
    start += timedelta(days=(7 - start.weekday()) % 7)
    entries: list[CalendarEntry] = []
    weekdays = [0, 2, 4, 1, 3, 5, 6][: max(1, min(posts_per_week, 7))]  # Mon, Wed, Fri, ...
    slot = 0
    for week in range(weeks):
        for weekday in weekdays:
            day = start + timedelta(weeks=week, days=weekday)
            pillar = pillars[slot % len(pillars)]
            fmt = FORMATS[slot % len(FORMATS)]
            entries.append(
                CalendarEntry(day=day, pillar=pillar, format=fmt, title=f"{fmt.title()}: {pillar}")
            )
            slot += 1
    return entries


_CAL_SYSTEM = (
    "You are an editorial director. Build a content calendar as valid JSON only: a list of "
    '[{"day": "YYYY-MM-DD", "pillar": "<pillar>", "format": "<format>", '
    '"title": "<specific title>", "hook": "<first line>"}]. '
    "Titles must be specific enough to brief a writer. No generic listicles."
)


def llm_calendar(
    provider: Provider,
    pillars: list[str],
    *,
    weeks: int,
    posts_per_week: int,
    start: date | None = None,
    model: str,
    max_tokens: int = 3000,
    temperature: float = 0.5,
) -> list[CalendarEntry]:
    """Ask the model for creative titles over the deterministic day grid."""
    grid = deterministic_calendar(pillars, weeks=weeks, posts_per_week=posts_per_week, start=start)
    skeleton = [{"day": str(e.day), "pillar": e.pillar, "format": e.format} for e in grid]
    result = provider.complete(
        system=_CAL_SYSTEM,
        prompt=(
            f"Pillars: {', '.join(pillars)}\n"
            f"Fill in titles and hooks for this exact day grid (keep days/pillars/formats unchanged):\n"
            f"{json.dumps(skeleton)}"
        ),
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    start_idx, end_idx = result.text.find("["), result.text.rfind("]")
    raw = json.loads(result.text[start_idx : end_idx + 1])
    entries: list[CalendarEntry] = []
    for item in raw:
        entries.append(
            CalendarEntry(
                day=date.fromisoformat(str(item["day"])),
                pillar=str(item["pillar"]),
                format=str(item["format"]),
                title=str(item["title"]),
                hook=str(item.get("hook", "")),
            )
        )
    return entries


def render_markdown(entries: list[CalendarEntry], *, title: str = "Editorial calendar") -> str:
    lines = [f"# {title}", "", "| Date | Pillar | Format | Title | Hook |", "|---|---|---|---|---|"]
    for e in entries:
        lines.append(f"| {e.day.isoformat()} | {e.pillar} | {e.format} | {e.title} | {e.hook} |")
    return "\n".join(lines) + "\n"
