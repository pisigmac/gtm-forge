"""Statistics engine: bootstrap CIs and Mann-Whitney U against known cases."""

import random

import pytest

from gtm_forge.skills.growth.stats import analyze, bootstrap_ci, mann_whitney, mean


def test_mean():
    assert mean([1.0, 2.0, 3.0]) == 2.0
    with pytest.raises(ValueError):
        mean([])


def _sample(mu, n, seed):
    rng = random.Random(seed)
    return [rng.gauss(mu, 1.0) for _ in range(n)]


def test_bootstrap_detects_real_difference():
    control = _sample(10.0, 30, seed=1)
    treatment = _sample(12.0, 30, seed=2)
    result = bootstrap_ci(control, treatment, n_boot=2000, seed=7)
    assert result.point > 0
    assert result.excludes_zero
    assert result.low < result.point < result.high


def test_bootstrap_no_difference_includes_zero():
    control = _sample(10.0, 30, seed=3)
    treatment = _sample(10.0, 30, seed=4)
    result = bootstrap_ci(control, treatment, n_boot=2000, seed=8)
    assert not result.excludes_zero


def test_bootstrap_requires_two_observations():
    with pytest.raises(ValueError):
        bootstrap_ci([1.0], [1.0, 2.0])


def test_mann_whitney_clearly_separated():
    result = mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
    assert result.u == 0
    assert result.p_value < 0.05
    assert result.cles == 1.0  # treatment always wins


def test_mann_whitney_all_ties():
    result = mann_whitney([1, 1], [1, 1])
    assert result.p_value == 1.0


def test_mann_whitney_reversed_direction():
    result = mann_whitney([6, 7, 8, 9, 10], [1, 2, 3, 4, 5])
    assert result.p_value < 0.05
    assert result.cles == 0.0  # treatment never wins


def test_analyze_ship_verdict():
    control = _sample(5.0, 25, seed=11)
    treatment = _sample(8.0, 25, seed=12)
    report = analyze(control, treatment, n_boot=2000, seed=13)
    assert report.significant
    assert report.verdict.startswith("SHIP IT")


def test_analyze_kill_verdict():
    control = _sample(8.0, 25, seed=14)
    treatment = _sample(5.0, 25, seed=15)
    report = analyze(control, treatment, n_boot=2000, seed=16)
    assert report.significant
    assert report.verdict.startswith("KILL IT")


def test_analyze_inconclusive():
    control = _sample(10.0, 15, seed=17)
    treatment = _sample(10.1, 15, seed=18)
    report = analyze(control, treatment, n_boot=2000, seed=19)
    assert not report.significant
    assert report.verdict.startswith("INCONCLUSIVE")
