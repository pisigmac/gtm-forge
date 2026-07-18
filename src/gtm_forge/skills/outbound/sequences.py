"""Outbound sequence generation: multi-step, multi-channel, grounded in the lead's
ICP breakdown so personalization references real reasons, not mail-merge fluff."""

from __future__ import annotations

import json
from dataclasses import dataclass

from gtm_forge.llm.base import Provider
from gtm_forge.skills.outbound.icp import ScoreBreakdown

_SEQUENCE_SYSTEM = (
    "You are an outbound copywriter. Write a {steps}-step outreach sequence mixing "
    "email and LinkedIn over 14 days. Rules: short sentences, no buzzwords, every email "
    "under 90 words, one clear ask per step, reference the specific fit reasons provided. "
    "Respond with ONLY valid JSON: a list of "
    '[{"step": <int>, "day": <int>, "channel": "email"|"linkedin", '
    '"subject": "<email subject or empty>", "body": "<message>"}].'
)


@dataclass(slots=True)
class SequenceStep:
    step: int
    day: int
    channel: str
    subject: str
    body: str


def parse_sequence(text: str) -> list[SequenceStep]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON list in sequence response: {text[:200]!r}")
    raw = json.loads(text[start : end + 1])
    return [
        SequenceStep(
            step=int(item["step"]),
            day=int(item["day"]),
            channel=str(item["channel"]),
            subject=str(item.get("subject", "")),
            body=str(item["body"]),
        )
        for item in raw
    ]


def generate_sequence(
    provider: Provider,
    *,
    lead: dict[str, str],
    breakdown: ScoreBreakdown,
    steps: int = 5,
    model: str,
    max_tokens: int = 2500,
    temperature: float = 0.4,
) -> list[SequenceStep]:
    fit = "; ".join(breakdown.reasons) if breakdown.reasons else "no strong fit signals"
    lead_desc = ", ".join(f"{k}: {v}" for k, v in lead.items())
    prompt = (
        f"Lead: {lead_desc}\nICP fit ({breakdown.total:g} points, {breakdown.label}): {fit}\n"
        f"Write the {steps}-step sequence."
    )
    result = provider.complete(
        system=_SEQUENCE_SYSTEM.format(steps=steps),
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return parse_sequence(result.text)
