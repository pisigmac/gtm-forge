"""ICP scoring: exact, keyword, and range rules with explainable output."""

from gtm_forge.skills.outbound.icp import ICPConfig, score_lead, score_leads


def _icp():
    return ICPConfig(
        weights={"industry": {"saas": 30.0, "fintech": 25.0}},
        keyword_weights={"title": {"vp": 20.0, "head": 15.0}},
        range_weights={"employees": [{"min": 50, "max": 500, "points": 20.0}]},
        thresholds={"hot": 60, "warm": 30},
    )


def test_exact_match_scoring():
    breakdown = score_lead({"industry": "SaaS"}, _icp())
    assert breakdown.total == 30.0
    assert breakdown.label == "warm"
    assert any("industry" in r for r in breakdown.reasons)


def test_keyword_and_range_scoring():
    lead = {"industry": "saas", "title": "VP of Marketing", "employees": "250"}
    breakdown = score_lead(lead, _icp())
    assert breakdown.total == 70.0
    assert breakdown.label == "hot"


def test_no_match_is_cold():
    breakdown = score_lead({"industry": "construction"}, _icp())
    assert breakdown.total == 0.0
    assert breakdown.label == "cold"


def test_ranking_order():
    leads = [
        {"company": "low", "industry": "construction"},
        {"company": "high", "industry": "saas", "title": "vp sales"},
    ]
    ranked = score_leads(leads, _icp())
    assert ranked[0][0]["company"] == "high"


def test_from_yaml(tmp_path):
    path = tmp_path / "icp.yaml"
    path.write_text(
        "weights:\n  industry:\n    saas: 30\nthresholds:\n  hot: 50\n  warm: 20\n",
        encoding="utf-8",
    )
    config = ICPConfig.from_yaml(path)
    assert config.weights["industry"]["saas"] == 30
    assert config.thresholds["hot"] == 50
