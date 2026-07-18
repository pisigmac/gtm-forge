"""Departed-champion tracking: when your buyer leaves, the relationship shouldn't.

Input is a CSV of champions with a status column. Departed champions with a known
new company become a re-engagement list; the LLM drafts a warm reopening message
grounded in the prior relationship.
"""

from __future__ import annotations

from dataclasses import dataclass

from gtm_forge.llm.base import Provider


@dataclass(slots=True)
class Champion:
    name: str
    old_company: str
    status: str  # active | departed
    new_company: str = ""
    role: str = ""
    last_deal: str = ""


@dataclass(slots=True)
class ReengagementTarget:
    champion: Champion
    priority: str  # high | medium
    reason: str


def find_reengagement_targets(champions: list[Champion]) -> list[ReengagementTarget]:
    """Departed champions who landed somewhere new, best opportunities first."""
    targets: list[ReengagementTarget] = []
    for c in champions:
        if c.status.strip().lower() != "departed":
            continue
        if not c.new_company:
            targets.append(ReengagementTarget(c, "medium", "departed; new company unknown — research needed"))
        else:
            senior = any(
                kw in c.role.lower() for kw in ("vp", "head", "director", "chief", "cfo", "cto", "cmo", "ceo")
            )
            priority = "high" if senior else "medium"
            targets.append(
                ReengagementTarget(c, priority, f"landed at {c.new_company} as {c.role or 'unknown role'}")
            )
    order = {"high": 0, "medium": 1}
    return sorted(targets, key=lambda t: order[t.priority])


_DRAFT_SYSTEM = (
    "You are a sales rep writing a warm re-engagement note to a former champion who "
    "changed jobs. 60-90 words. Reference the past win, congratulate them, and make one "
    "soft ask. No buzzwords, no fake enthusiasm. Return plain text only."
)


def draft_message(
    provider: Provider,
    *,
    target: ReengagementTarget,
    model: str,
    max_tokens: int = 300,
    temperature: float = 0.4,
) -> str:
    c = target.champion
    prompt = (
        f"Champion: {c.name}, previously at {c.old_company} "
        f"(past deal: {c.last_deal or 'worked together'}), now at {c.new_company} "
        f"as {c.role or 'unknown role'}. Write the note."
    )
    return provider.complete(
        system=_DRAFT_SYSTEM,
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    ).text
