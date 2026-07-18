"""A panel of expert critics that scores a content idea before you produce it.

Seven perspectives, one numeric gate. Nothing ships below the gate (default 90).
The panel asks each expert for strict JSON so results are machine-checkable and
comparable over time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from gtm_forge.core.costs import estimate_tokens
from gtm_forge.llm.base import Provider

#: (key, display name, system prompt). Each expert owns one lens and scores strictly.
EXPERTS: list[tuple[str, str, str]] = [
    (
        "brand",
        "Brand strategist",
        "You are a brand strategist. Judge whether this idea strengthens a coherent, "
        "memorable brand position. Penalize anything generic that a competitor could post.",
    ),
    (
        "seo",
        "SEO lead",
        "You are an SEO lead. Judge search demand, keyword targeting, and whether the idea "
        "can rank against what already wins the SERP.",
    ),
    (
        "audience",
        "Audience growth lead",
        "You are an audience growth lead. Judge shareability, hook strength, and whether "
        "the target reader would stop scrolling for this.",
    ),
    (
        "conversion",
        "Conversion strategist",
        "You are a conversion strategist. Judge whether this idea moves a reader toward a "
        "business outcome, not just applause.",
    ),
    (
        "competitive",
        "Competitive analyst",
        "You are a competitive analyst. Judge how this idea compares to the best content "
        "already published in the space. Score against the winners, not the average.",
    ),
    (
        "voice",
        "Voice editor",
        "You are a voice editor. Judge whether the idea can be executed in a distinct, "
        "consistent voice. Penalize ideas that force bland, committee-sounding output.",
    ),
    (
        "platform",
        "Platform specialist",
        "You are a platform specialist. Judge native fit for the target platform: format, "
        "length, hook timing, and distribution mechanics.",
    ),
]

_SCORE_INSTRUCTION = (
    "Score the content idea from 0-100 from your perspective only. "
    "Respond with ONLY valid JSON, no prose outside the JSON:\n"
    '{"score": <int 0-100>, "strengths": ["...", "..."], '
    '"weaknesses": ["...", "..."], "fix": "<one sentence that would raise the score most>"}'
)


@dataclass(slots=True)
class ExpertScore:
    expert: str
    expert_name: str
    score: int
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    fix: str = ""


@dataclass(slots=True)
class PanelReport:
    idea: str
    scores: list[ExpertScore]
    gate: int

    @property
    def mean(self) -> float:
        return sum(s.score for s in self.scores) / len(self.scores) if self.scores else 0.0

    @property
    def passed(self) -> bool:
        return self.mean >= self.gate

    @property
    def weakest(self) -> ExpertScore | None:
        return min(self.scores, key=lambda s: s.score) if self.scores else None

    def to_markdown(self) -> str:
        lines = [
            f"# Content Eval — {self.idea}",
            "",
            f"**Panel mean: {self.mean:.1f} / 100 — gate {self.gate} — "
            f"{'PASS' if self.passed else 'REVISE'}**",
            "",
            "| Expert | Score | Top fix |",
            "|---|---|---|",
        ]
        for s in sorted(self.scores, key=lambda x: x.score):
            lines.append(f"| {s.expert_name} | {s.score} | {s.fix} |")
        if self.weakest:
            lines += [
                "",
                f"Start with the weakest lens ({self.weakest.expert_name}): {self.weakest.fix}",
            ]
        return "\n".join(lines)


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response, tolerating fences."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in response: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def run_panel(
    provider: Provider,
    *,
    idea: str,
    context: str = "",
    gate: int = 90,
    model: str,
    max_tokens: int = 800,
    temperature: float = 0.2,
    experts: list[tuple[str, str, str]] = EXPERTS,
) -> PanelReport:
    """Run every expert against the idea and aggregate the scores."""
    scores: list[ExpertScore] = []
    brief = f"Content idea: {idea}\n"
    if context:
        brief += f"\nContext (audience, platform, goals):\n{context}\n"
    for key, name, system in experts:
        result = provider.complete(
            system=f"{system}\n\n{_SCORE_INSTRUCTION}",
            prompt=brief,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        payload = extract_json(result.text)
        scores.append(
            ExpertScore(
                expert=key,
                expert_name=name,
                score=max(0, min(100, int(payload.get("score", 0)))),
                strengths=[str(s) for s in payload.get("strengths", [])][:3],
                weaknesses=[str(s) for s in payload.get("weaknesses", [])][:3],
                fix=str(payload.get("fix", "")),
            )
        )
    return PanelReport(idea=idea, scores=scores, gate=gate)


def dry_run_plan(idea: str, context: str = "", gate: int = 90) -> dict:
    """What a panel run would do, with a rough token/cost preview."""
    prompt_tokens = estimate_tokens(f"Content idea: {idea}\n{context}")
    per_expert_in = prompt_tokens + 220  # system prompt overhead
    per_expert_out = 160  # typical JSON verdict size
    return {
        "idea": idea,
        "gate": gate,
        "experts": [name for _, name, _ in EXPERTS],
        "estimated_input_tokens": per_expert_in * len(EXPERTS),
        "estimated_output_tokens": per_expert_out * len(EXPERTS),
        "note": "Estimates use chars/4. Actual usage is recorded per run.",
    }
