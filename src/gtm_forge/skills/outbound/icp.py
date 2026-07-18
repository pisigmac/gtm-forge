"""ICP scoring: deterministic, explainable points against your ideal customer profile.

Weights live in YAML — no model calls, no black box. Every point is accounted for
in the breakdown, so sales can see *why* a lead scored the way it did.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ICPConfig:
    """Scoring rules.

    weights: field -> {value -> points} exact-match scoring (case-insensitive)
    keyword_weights: field -> {keyword -> points} substring scoring
    range_weights: field -> list of {min, max, points} numeric range scoring
    thresholds: label cutoffs, e.g. {"hot": 70, "warm": 40}
    """

    weights: dict[str, dict[str, float]] = field(default_factory=dict)
    keyword_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    range_weights: dict[str, list[dict[str, float]]] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=lambda: {"hot": 70, "warm": 40})

    @classmethod
    def from_yaml(cls, path: str | Path) -> ICPConfig:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"ICP file {path} must be a YAML mapping.")
        return cls(
            weights={k: dict(v) for k, v in (raw.get("weights") or {}).items()},
            keyword_weights={k: dict(v) for k, v in (raw.get("keyword_weights") or {}).items()},
            range_weights={k: list(v) for k, v in (raw.get("range_weights") or {}).items()},
            thresholds=dict(raw.get("thresholds") or {"hot": 70, "warm": 40}),
        )


@dataclass(slots=True)
class ScoreBreakdown:
    total: float
    label: str
    reasons: list[str]


def _label(total: float, thresholds: dict[str, float]) -> str:
    ordered = sorted(thresholds.items(), key=lambda kv: kv[1], reverse=True)
    for name, cutoff in ordered:
        if total >= cutoff:
            return name
    return "cold"


def _exact_points(
    normalized: dict[str, str], weights: dict[str, dict[str, float]], reasons: list[str]
) -> float:
    points = 0.0
    for field_name, table in weights.items():
        value = normalized.get(field_name.lower())
        if value is None:
            continue
        scored = table.get(value)
        if scored:
            points += scored
            reasons.append(f"{field_name}={value} (+{scored:g})")
    return points


def _keyword_points(
    normalized: dict[str, str], weights: dict[str, dict[str, float]], reasons: list[str]
) -> float:
    points = 0.0
    for field_name, table in weights.items():
        value = normalized.get(field_name.lower(), "")
        for keyword, scored in table.items():
            if keyword.lower() in value:
                points += scored
                reasons.append(f"{field_name} contains '{keyword}' (+{scored:g})")
    return points


def _range_points(
    normalized: dict[str, str], weights: dict[str, list[dict[str, float]]], reasons: list[str]
) -> float:
    points = 0.0
    for field_name, ranges in weights.items():
        raw = normalized.get(field_name.lower(), "")
        try:
            number = float(raw.replace(",", ""))
        except ValueError:
            continue
        for rule in ranges:
            lo = float(rule.get("min", float("-inf")))
            hi = float(rule.get("max", float("inf")))
            if lo <= number <= hi:
                scored = float(rule.get("points", 0))
                points += scored
                reasons.append(f"{field_name}={number:g} in [{lo:g}, {hi:g}] (+{scored:g})")
                break
    return points


def score_lead(lead: dict[str, Any], icp: ICPConfig) -> ScoreBreakdown:
    """Score one lead (a flat dict, e.g. a CSV row) against the ICP."""
    normalized = {str(k).lower(): str(v).strip().lower() for k, v in lead.items()}
    reasons: list[str] = []
    total = (
        _exact_points(normalized, icp.weights, reasons)
        + _keyword_points(normalized, icp.keyword_weights, reasons)
        + _range_points(normalized, icp.range_weights, reasons)
    )
    return ScoreBreakdown(total=total, label=_label(total, icp.thresholds), reasons=reasons)


def score_leads(leads: list[dict[str, Any]], icp: ICPConfig) -> list[tuple[dict[str, Any], ScoreBreakdown]]:
    """Score and rank a list of leads, best first."""
    scored = [(lead, score_lead(lead, icp)) for lead in leads]
    return sorted(scored, key=lambda pair: pair[1].total, reverse=True)
