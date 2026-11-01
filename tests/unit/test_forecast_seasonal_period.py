"""E1: the estimator's 52-lag seasonal candidate is a weekly-period construct (FreshRetailNet audit, 2026-10-19).

On daily periods the candidate became eligible once the replay's growing history passed 68 observations and was
selected on 197 of 1,100 such reviews, forecasting a day from the day 52 days earlier. The candidate is now offered
only when the request's period is weekly; weekly callers are unchanged by default."""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from zaad.full.demo import example
from zaad.full.forecast import _fit_segment, estimate
from zaad.full.worlds import forecast_all


def _series(n: int = 80, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y = np.maximum(0., 20 + 3 * np.sin(np.arange(n) * 2 * np.pi / 52) + rng.normal(0, 2, n))
    y[-52] = 60.                     # a spike exactly one "year" back: the seasonal lag would copy it
    return y


def test_seasonal_candidate_is_offered_only_when_asked():
    y = _series()
    with_seasonal = _fit_segment(y, 10., .01, True)[2]
    without = _fit_segment(y, 10., .01, False)[2]
    assert "seasonal_naive" in with_seasonal and "seasonal_naive" not in without
    assert {k: v for k, v in with_seasonal.items() if k != "seasonal_naive"} == without      # the other candidates are untouched
    assert "seasonal_naive" not in estimate(y, 10., .01, adaptive=False, seasonal=False)["decision_losses"]
    assert "seasonal_naive" in estimate(y, 10., .01, adaptive=False)["decision_losses"]        # default: weekly behaviour


def test_forecast_all_passes_the_period_length():
    weekly = example()
    assert weekly.period_days == 7
    long_history = [{**h.model_dump(), "period": h.period - 20} for h in weekly.history]
    extra = [{"known_at": weekly.as_of - timedelta(days=1), "service": weekly.services[0].id, "period": t, "quantity": 20.} for t in range(-20, 0)]
    weekly = weekly.model_copy(update={"history": tuple(long_history + extra)})
    weekly = type(weekly).model_validate(weekly.model_dump())
    assert len(weekly.history) == 72 and sorted(h.period for h in weekly.history) == list(range(-72, 0))
    daily = weekly.model_copy(update={"period_days": 1})
    assert "seasonal_naive" in forecast_all(weekly, adaptive=False)[weekly.services[0].id]["decision_losses"]
    assert "seasonal_naive" not in forecast_all(daily, adaptive=False)[daily.services[0].id]["decision_losses"]
