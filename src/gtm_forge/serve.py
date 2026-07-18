"""Optional REST API: expose skills over HTTP.

Only dependency-free skills are served directly; LLM-backed endpoints build a
provider from the loaded config at request time. Requires: gtm-forge[serve].

Note: no `from __future__ import annotations` here — FastAPI must resolve the
request models eagerly at route-registration time.
"""

from typing import Any

from gtm_forge import __version__
from gtm_forge.config import Settings, load_settings
from gtm_forge.core.state import StateStore


def create_app(settings: Settings | None = None, state: StateStore | None = None) -> Any:
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError(
            "The REST API requires extra dependencies. Run: pip install 'gtm-forge[serve]'"
        ) from exc

    from gtm_forge.skills.content_eval.panel import run_panel
    from gtm_forge.skills.growth.stats import analyze
    from gtm_forge.skills.outbound.icp import ICPConfig, score_lead
    from gtm_forge.skills.seo.brief import Page, find_cannibals

    settings = settings or load_settings()
    state = state or StateStore(settings.paths.state_db)

    app = FastAPI(title="gtm-forge API", version=__version__)

    class AnalyzeRequest(BaseModel):
        control: list[float] = Field(min_length=2)
        treatment: list[float] = Field(min_length=2)
        alpha: float = 0.05
        n_boot: int = 5000
        seed: int = 42

    class EvalRequest(BaseModel):
        idea: str
        context: str = ""
        gate: int = 90

    class ScoreRequest(BaseModel):
        lead: dict[str, str]
        icp: dict[str, Any] = Field(default_factory=dict)

    class CannibalizeRequest(BaseModel):
        pages: list[dict[str, Any]]
        threshold: float = 0.6

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/costs/summary")
    def costs_summary() -> dict[str, Any]:
        rows = state.costs_summary()
        return {
            "models": [
                {
                    "model": r["model"],
                    "calls": r["calls"],
                    "input_tokens": r["input_tokens"],
                    "output_tokens": r["output_tokens"],
                    "cost_usd": round(float(r["cost_usd"]), 6),
                }
                for r in rows
            ],
            "total_usd": round(sum(float(r["cost_usd"]) for r in rows), 6),
        }

    @app.post("/skills/growth/analyze")
    def growth_analyze(req: AnalyzeRequest) -> dict[str, Any]:
        try:
            report = analyze(req.control, req.treatment, alpha=req.alpha, n_boot=req.n_boot, seed=req.seed)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "verdict": report.verdict,
            "significant": report.significant,
            "difference": report.bootstrap.point,
            "ci": [report.bootstrap.low, report.bootstrap.high],
            "p_value": report.mann_whitney.p_value,
            "cles": report.mann_whitney.cles,
        }

    @app.post("/skills/outbound/score")
    def outbound_score(req: ScoreRequest) -> dict[str, Any]:
        config = ICPConfig(
            weights=req.icp.get("weights", {}),
            keyword_weights=req.icp.get("keyword_weights", {}),
            range_weights=req.icp.get("range_weights", {}),
            thresholds=req.icp.get("thresholds", {"hot": 70, "warm": 40}),
        )
        breakdown = score_lead(req.lead, config)
        return {"total": breakdown.total, "label": breakdown.label, "reasons": breakdown.reasons}

    @app.post("/skills/seo/cannibalize")
    def seo_cannibalize(req: CannibalizeRequest) -> dict[str, Any]:
        pages = [
            Page(
                url=str(p["url"]),
                title=str(p.get("title", "")),
                keywords=[str(k) for k in p.get("keywords", [])],
            )
            for p in req.pages
        ]
        conflicts = find_cannibals(pages, threshold=req.threshold)
        return {
            "conflicts": [
                {
                    "url_a": c.url_a,
                    "url_b": c.url_b,
                    "similarity": c.similarity,
                    "shared_tokens": c.shared_tokens,
                }
                for c in conflicts
            ]
        }

    @app.post("/skills/content-eval/run")
    def content_eval_run(req: EvalRequest) -> dict[str, Any]:
        from gtm_forge.llm.factory import build_provider

        provider = build_provider(settings, state, "serve")
        report = run_panel(
            provider,
            idea=req.idea,
            context=req.context,
            gate=req.gate,
            model=settings.llm.resolved_model(),
        )
        return {
            "mean": report.mean,
            "gate": report.gate,
            "passed": report.passed,
            "scores": [
                {
                    "expert": s.expert,
                    "score": s.score,
                    "fix": s.fix,
                    "strengths": s.strengths,
                    "weaknesses": s.weaknesses,
                }
                for s in report.scores
            ],
        }

    return app
