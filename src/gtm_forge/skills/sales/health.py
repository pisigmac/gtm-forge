"""Deal health scoring: transparent rules, no black box.

A deal decays for four reasons: it sits in a stage too long, nobody has touched
it, there is no champion, or it is single-threaded. Each reason adds points to
a risk score with a written explanation a rep can argue with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TypedDict

#: Median days a healthy deal spends per stage, by stage name (lowercased).
#: Override via config skills.sales.stage_median_days.
DEFAULT_STAGE_MEDIANS: dict[str, int] = {
    "discovery": 14,
    "qualification": 10,
    "demo": 14,
    "proposal": 21,
    "negotiation": 21,
    "default": 21,
}


@dataclass(slots=True)
class Deal:
    id: str
    name: str
    amount: float
    stage: str
    stage_entered: date
    last_activity: date
    has_champion: bool = False
    contacts: int = 1


@dataclass(slots=True)
class HealthReport:
    deal_id: str
    name: str
    risk: int  # 0-100, higher is worse
    tier: str  # healthy | at-risk | critical
    reasons: list[str] = field(default_factory=list)


class PortfolioSummary(TypedDict):
    total_deals: int
    tiers: dict[str, int]
    at_risk_amount: float
    reports: list[HealthReport]


def score_deal(
    deal: Deal,
    *,
    today: date | None = None,
    stage_medians: dict[str, int] | None = None,
) -> HealthReport:
    today = today or date.today()
    medians = stage_medians or DEFAULT_STAGE_MEDIANS
    risk = 0
    reasons: list[str] = []

    days_in_stage = (today - deal.stage_entered).days
    median = medians.get(deal.stage.lower(), medians["default"])
    if days_in_stage > median * 2:
        risk += 40
        reasons.append(f"stuck in {deal.stage} for {days_in_stage}d (median {median}d)")
    elif days_in_stage > median:
        risk += 20
        reasons.append(f"slow in {deal.stage}: {days_in_stage}d (median {median}d)")

    idle = (today - deal.last_activity).days
    if idle > 14:
        risk += 25
        reasons.append(f"no activity for {idle} days")
    elif idle > 7:
        risk += 10
        reasons.append(f"quiet for {idle} days")

    if not deal.has_champion:
        risk += 20
        reasons.append("no internal champion identified")
    if deal.contacts <= 1:
        risk += 15
        reasons.append("single-threaded: only one contact on the account")

    risk = min(100, risk)
    tier = "healthy" if risk < 30 else ("at-risk" if risk < 60 else "critical")
    return HealthReport(deal_id=deal.id, name=deal.name, risk=risk, tier=tier, reasons=reasons)


def portfolio_health(
    deals: list[Deal],
    *,
    today: date | None = None,
    stage_medians: dict[str, int] | None = None,
) -> PortfolioSummary:
    pairs = [(d, score_deal(d, today=today, stage_medians=stage_medians)) for d in deals]
    at_risk_amount = sum(d.amount for d, r in pairs if r.tier != "healthy")
    reports = sorted((r for _, r in pairs), key=lambda r: r.risk, reverse=True)
    tiers = {"healthy": 0, "at-risk": 0, "critical": 0}
    for r in reports:
        tiers[r.tier] += 1
    return {
        "total_deals": len(deals),
        "tiers": tiers,
        "at_risk_amount": at_risk_amount,
        "reports": reports,
    }
