"""Experiment lifecycle: create, collect, analyze, decide.

Experiments are stored as plain JSON files under <output_dir>/experiments/ so
they are diffable in git and editable by hand. The first variant is the control.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from gtm_forge.skills.growth.stats import AnalysisReport, analyze

VALID_STATUS = {"draft", "running", "promoted", "killed"}


@dataclass
class Experiment:
    id: str
    name: str
    hypothesis: str
    variable: str
    variants: list[str]
    metric: str
    status: str = "draft"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict[str, list[float]] = field(default_factory=dict)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "experiment"


def _dir(base_dir: Path) -> Path:
    target = base_dir / "experiments"
    target.mkdir(parents=True, exist_ok=True)
    return target


def create_experiment(
    base_dir: Path,
    *,
    name: str,
    hypothesis: str,
    variable: str,
    variants: list[str],
    metric: str,
) -> Experiment:
    if len(variants) < 2:
        raise ValueError("An experiment needs at least two variants (control first).")
    if len(set(variants)) != len(variants):
        raise ValueError("Variant names must be unique.")
    exp = Experiment(
        id=f"{_slug(name)}-{uuid.uuid4().hex[:6]}",
        name=name,
        hypothesis=hypothesis,
        variable=variable,
        variants=variants,
        metric=metric,
        status="running",
    )
    save_experiment(base_dir, exp)
    return exp


def save_experiment(base_dir: Path, exp: Experiment) -> Path:
    path = _dir(base_dir) / f"{exp.id}.json"
    path.write_text(json.dumps(asdict(exp), indent=2), encoding="utf-8")
    return path


def load_experiment(base_dir: Path, exp_id: str) -> Experiment:
    path = _dir(base_dir) / f"{exp_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No experiment '{exp_id}' in {path.parent}.")
    return Experiment(**json.loads(path.read_text(encoding="utf-8")))


def list_experiments(base_dir: Path) -> list[Experiment]:
    return [
        Experiment(**json.loads(p.read_text(encoding="utf-8"))) for p in sorted(_dir(base_dir).glob("*.json"))
    ]


def add_observations(exp: Experiment, variant: str, values: list[float]) -> Experiment:
    if variant not in exp.variants:
        raise ValueError(f"Unknown variant '{variant}'. Known: {exp.variants}")
    exp.data.setdefault(variant, []).extend(values)
    return exp


def analyze_experiment(
    exp: Experiment,
    *,
    alpha: float = 0.05,
    n_boot: int = 5000,
    seed: int = 42,
) -> dict[str, AnalysisReport]:
    """Compare every non-control variant against variants[0] (the control)."""
    control_name = exp.variants[0]
    control = exp.data.get(control_name, [])
    reports: dict[str, AnalysisReport] = {}
    for variant in exp.variants[1:]:
        treatment = exp.data.get(variant, [])
        reports[variant] = analyze(control, treatment, alpha=alpha, n_boot=n_boot, seed=seed)
    return reports


def decide(exp: Experiment, decision: str) -> Experiment:
    if decision not in {"promoted", "killed"}:
        raise ValueError("Decision must be 'promoted' or 'killed'.")
    exp.status = decision
    return exp
