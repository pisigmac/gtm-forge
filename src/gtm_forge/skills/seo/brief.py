"""SEO attack briefs (LLM-assisted) and keyword cannibalization detection (pure Python)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from gtm_forge.llm.base import Provider

_WORD = re.compile(r"[a-z0-9]+")


def token_set(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass(slots=True)
class Page:
    url: str
    title: str
    keywords: list[str]


@dataclass(slots=True)
class Conflict:
    url_a: str
    url_b: str
    similarity: float
    shared_tokens: list[str]


def find_cannibals(pages: list[Page], *, threshold: float = 0.6) -> list[Conflict]:
    """Flag page pairs whose keyword footprints overlap enough to compete with each other."""
    footprints = [(p, token_set(p.title + " " + " ".join(p.keywords))) for p in pages]
    conflicts: list[Conflict] = []
    for i in range(len(footprints)):
        for j in range(i + 1, len(footprints)):
            (pa, ta), (pb, tb) = footprints[i], footprints[j]
            sim = jaccard(ta, tb)
            if sim >= threshold:
                conflicts.append(
                    Conflict(
                        url_a=pa.url,
                        url_b=pb.url,
                        similarity=round(sim, 3),
                        shared_tokens=sorted(ta & tb),
                    )
                )
    return sorted(conflicts, key=lambda c: c.similarity, reverse=True)


_BRIEF_SYSTEM = (
    "You are an SEO strategist writing an attack brief: a plan to win one keyword. "
    "Be specific and ruthless. Structure the brief in markdown with exactly these sections: "
    "## Search intent, ## SERP gaps to exploit, ## Recommended angle, "
    "## Outline (H2/H3), ## Internal links to add, ## Differentiators, ## Risks. "
    "No filler. Every claim must be actionable."
)


def build_brief(
    provider: Provider,
    *,
    keyword: str,
    audience: str,
    serp_notes: str = "",
    model: str,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> str:
    """Generate a markdown attack brief for a target keyword."""
    prompt = f"Target keyword: {keyword}\nAudience: {audience}\n"
    if serp_notes:
        prompt += f"\nNotes on the current SERP (what ranks today):\n{serp_notes}\n"
    prompt += "\nWrite the attack brief."
    return provider.complete(
        system=_BRIEF_SYSTEM,
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    ).text


def brief_dry_run(keyword: str, audience: str, serp_notes: str = "") -> dict:
    return {
        "keyword": keyword,
        "audience": audience,
        "sections": [
            "Search intent",
            "SERP gaps to exploit",
            "Recommended angle",
            "Outline (H2/H3)",
            "Internal links to add",
            "Differentiators",
            "Risks",
        ],
        "serp_notes_chars": len(serp_notes),
    }
