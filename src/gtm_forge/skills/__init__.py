"""Skill registry: the eight production skills shipped with gtm-forge."""

SKILLS: dict[str, str] = {
    "experiment": "Growth experiments with real statistics (bootstrap CIs, Mann-Whitney U).",
    "eval": "Multi-expert content evaluation panel with a numeric quality gate.",
    "seo": "SEO attack briefs and keyword cannibalization detection.",
    "video": "Long-form video to clip pipeline: transcribe, score, cut.",
    "lead": "Company dossiers and cascade email verification.",
    "outbound": "ICP scoring and outbound sequence generation.",
    "content": "Editorial calendar generation with deterministic fallback.",
    "sales": "Deal health scoring and departed-champion tracking.",
}

__all__ = ["SKILLS"]
