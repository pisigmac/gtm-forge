"""Deal health rules and champion re-engagement targeting."""

from datetime import date, timedelta

from gtm_forge.skills.sales.champions import Champion, find_reengagement_targets
from gtm_forge.skills.sales.health import Deal, portfolio_health, score_deal

TODAY = date(2026, 7, 17)


def _deal(**overrides):
    base = dict(
        id="d1",
        name="Acme",
        amount=50_000,
        stage="proposal",
        stage_entered=TODAY - timedelta(days=5),
        last_activity=TODAY - timedelta(days=2),
        has_champion=True,
        contacts=3,
    )
    base.update(overrides)
    return Deal(**base)


def test_healthy_deal():
    report = score_deal(_deal(), today=TODAY)
    assert report.tier == "healthy"
    assert report.risk < 30


def test_critical_deal_all_signals():
    report = score_deal(
        _deal(
            stage_entered=TODAY - timedelta(days=90),
            last_activity=TODAY - timedelta(days=30),
            has_champion=False,
            contacts=1,
        ),
        today=TODAY,
    )
    assert report.tier == "critical"
    assert report.risk >= 60
    assert len(report.reasons) == 4


def test_portfolio_summary():
    deals = [
        _deal(),
        _deal(id="d2", name="Globex", has_champion=False, last_activity=TODAY - timedelta(days=20)),
    ]
    summary = portfolio_health(deals, today=TODAY)
    assert summary["total_deals"] == 2
    assert sum(summary["tiers"].values()) == 2
    # Globex is not healthy -> its amount counts toward at-risk
    assert summary["at_risk_amount"] == 50_000


def test_champion_targets():
    champions = [
        Champion(
            name="Priya",
            old_company="Acme",
            status="departed",
            new_company="Globex",
            role="VP Marketing",
            last_deal="$50k",
        ),
        Champion(name="Sam", old_company="Acme", status="active"),
        Champion(name="Lee", old_company="Initech", status="departed", new_company=""),
    ]
    targets = find_reengagement_targets(champions)
    assert len(targets) == 2
    assert targets[0].champion.name == "Priya"  # senior role -> high priority first
    assert targets[0].priority == "high"
    assert targets[1].priority == "medium"
