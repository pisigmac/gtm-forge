"""Statistics for growth experiments: bootstrap confidence intervals and the
Mann-Whitney U test. No "this post got more likes so it won" — real inference.

Both tests are non-parametric, so they work on skewed marketing data
(impressions, watch time, revenue) without normality assumptions.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(slots=True)
class BootstrapResult:
    point: float  # observed difference of means (treatment - control)
    low: float
    high: float
    n_boot: int
    alpha: float

    @property
    def excludes_zero(self) -> bool:
        return self.low > 0 or self.high < 0


@dataclass(slots=True)
class MannWhitneyResult:
    u: float
    z: float
    p_value: float
    cles: float  # P(treatment > control), the common-language effect size


@dataclass(slots=True)
class AnalysisReport:
    n_control: int
    n_treatment: int
    mean_control: float
    mean_treatment: float
    bootstrap: BootstrapResult
    mann_whitney: MannWhitneyResult
    alpha: float
    significant: bool
    verdict: str


def mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean() requires at least one observation.")
    return sum(xs) / len(xs)


def bootstrap_ci(
    control: Sequence[float],
    treatment: Sequence[float],
    *,
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 42,
) -> BootstrapResult:
    """Percentile bootstrap CI for the difference of means (treatment - control)."""
    if len(control) < 2 or len(treatment) < 2:
        raise ValueError("Both groups need at least 2 observations.")
    rng = random.Random(seed)
    n_c, n_t = len(control), len(treatment)
    diffs: list[float] = []
    for _ in range(n_boot):
        c = sum(control[rng.randrange(n_c)] for _ in range(n_c)) / n_c
        t = sum(treatment[rng.randrange(n_t)] for _ in range(n_t)) / n_t
        diffs.append(t - c)
    diffs.sort()
    low = diffs[int((alpha / 2) * n_boot)]
    high = diffs[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return BootstrapResult(
        point=mean(treatment) - mean(control), low=low, high=high, n_boot=n_boot, alpha=alpha
    )


def _average_ranks(values: list[float]) -> list[float]:
    """Ranks with tie averaging, aligned with the input order."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def mann_whitney(control: Sequence[float], treatment: Sequence[float]) -> MannWhitneyResult:
    """Two-sided Mann-Whitney U with tie correction and continuity correction.

    Uses the normal approximation, which is reliable for n >= ~8 per group.
    For tiny samples treat the p-value as directional, not exact.
    """
    n1, n2 = len(control), len(treatment)
    if n1 < 2 or n2 < 2:
        raise ValueError("Both groups need at least 2 observations.")
    combined = list(control) + list(treatment)
    ranks = _average_ranks(combined)
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    n = n1 + n2
    tie_sum = sum(c**3 - c for c in Counter(combined).values() if c > 1)
    var = (n1 * n2 / 12) * ((n + 1) - tie_sum / (n * (n - 1)))
    mu = n1 * n2 / 2
    if var <= 0:
        return MannWhitneyResult(u=u, z=0.0, p_value=1.0, cles=u2 / (n1 * n2))
    sigma = math.sqrt(var)
    # Continuity correction toward the mean, using the larger U for a two-sided test.
    u_stat = max(u1, u2)
    z = (u_stat - mu - 0.5) / sigma
    p = 2 * (1 - _phi(z))
    return MannWhitneyResult(u=u, z=z, p_value=min(1.0, max(0.0, p)), cles=u2 / (n1 * n2))


def analyze(
    control: Sequence[float],
    treatment: Sequence[float],
    *,
    alpha: float = 0.05,
    n_boot: int = 5000,
    seed: int = 42,
) -> AnalysisReport:
    """Full experiment readout: effect size, CI, p-value, and a plain-language verdict."""
    boot = bootstrap_ci(control, treatment, n_boot=n_boot, alpha=alpha, seed=seed)
    mw = mann_whitney(control, treatment)
    significant = mw.p_value < alpha and boot.excludes_zero

    if significant and boot.point > 0:
        verdict = (
            f"SHIP IT. Treatment beats control by {boot.point:.4g} on average "
            f"(95% CI [{boot.low:.4g}, {boot.high:.4g}], p={mw.p_value:.4f}). "
            f"The treatment wins {mw.cles:.0%} of head-to-head comparisons."
        )
    elif significant:
        verdict = (
            f"KILL IT. Treatment is worse by {abs(boot.point):.4g} on average "
            f"(95% CI [{boot.low:.4g}, {boot.high:.4g}], p={mw.p_value:.4f})."
        )
    else:
        verdict = (
            f"INCONCLUSIVE. Observed difference {boot.point:.4g} "
            f"(95% CI [{boot.low:.4g}, {boot.high:.4g}], p={mw.p_value:.4f}). "
            "Collect more data or accept the null."
        )
    return AnalysisReport(
        n_control=len(control),
        n_treatment=len(treatment),
        mean_control=mean(control),
        mean_treatment=mean(treatment),
        bootstrap=boot,
        mann_whitney=mw,
        alpha=alpha,
        significant=significant,
        verdict=verdict,
    )
