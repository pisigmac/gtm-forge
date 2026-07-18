"""REST API: health, pure-Python skill endpoints, costs."""

import pytest
from fastapi.testclient import TestClient

from gtm_forge.config import Settings
from gtm_forge.core.state import StateStore
from gtm_forge.serve import create_app


@pytest.fixture()
def client(tmp_path):
    settings = Settings()
    state = StateStore(tmp_path / "serve-state.db")
    app = create_app(settings=settings, state=state)
    yield TestClient(app)
    state.close()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_growth_analyze_endpoint(client):
    resp = client.post(
        "/skills/growth/analyze",
        json={
            "control": [1, 2, 3, 4, 5, 6, 7, 8],
            "treatment": [10, 11, 12, 13, 14, 15, 16, 17],
            "n_boot": 2000,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["significant"] is True
    assert body["difference"] > 0


def test_growth_analyze_validation(client):
    resp = client.post("/skills/growth/analyze", json={"control": [1], "treatment": [2]})
    assert resp.status_code == 422


def test_outbound_score_endpoint(client):
    resp = client.post(
        "/skills/outbound/score",
        json={
            "lead": {"industry": "saas", "title": "VP Sales"},
            "icp": {"weights": {"industry": {"saas": 50}}, "keyword_weights": {"title": {"vp": 20}}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 70.0


def test_cannibalize_endpoint(client):
    resp = client.post(
        "/skills/seo/cannibalize",
        json={
            "pages": [
                {"url": "/a", "title": "email marketing guide", "keywords": ["email marketing"]},
                {"url": "/b", "title": "email marketing guide", "keywords": ["email marketing"]},
            ],
            "threshold": 0.8,
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["conflicts"]) == 1


def test_costs_summary_endpoint(client):
    resp = client.get("/costs/summary")
    assert resp.status_code == 200
    assert resp.json()["total_usd"] == 0.0
