from __future__ import annotations

from domain.priors import decay_rate_prior, lead_time_cv_prior


def test_lpi_prior_is_monotone_and_labelled():
    de, jo, ng = lead_time_cv_prior("DEU"), lead_time_cv_prior("JOR"), lead_time_cv_prior("NGA")
    assert de.provenance == "PUBLIC_BENCHMARK" and 0.10 <= de.value < jo.value < ng.value <= 0.80
    assert "LPI" in de.source and "ASSUMED" in de.basis
    unk = lead_time_cv_prior(None)
    assert unk.provenance == "ASSUMED" and unk.value == 0.35


def test_decay_prior_from_category_and_default():
    leafy = decay_rate_prior("Spinach", "Leafy Greens")
    roots = decay_rate_prior("Carrots", "Root Vegetables")
    assert leafy.value > roots.value and leafy.provenance in ("ASSUMED", "PUBLIC_BENCHMARK")
    assert decay_rate_prior(None, None).value == 0.05
    assert decay_rate_prior("shelf-stable").value == 0.0


def test_agriculture_policy_uses_prior_unless_measured():
    from domain.model import agriculture_policy
    leafy = agriculture_policy(commodity="Fresh spinach", category="Leafy Greens")
    roots = agriculture_policy(commodity="Fresh carrots", category="Root Vegetables")
    measured = agriculture_policy(decay_rate_per_period=0.011)
    assert leafy.decay_rate_per_period > roots.decay_rate_per_period
    assert measured.decay_rate_per_period == 0.011
    assert agriculture_policy().decay_rate_per_period == 0.05          # legacy default preserved


def test_ers_prior_used_when_cached():
    from domain.priors import decay_rate_prior
    pr = decay_rate_prior("Fresh bell peppers")
    assert pr.provenance == "PUBLIC_BENCHMARK" and 0.0 < pr.value < 0.1 and "ERS" in pr.source
