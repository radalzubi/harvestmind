"""Small-sample candidate forecast tournament; chronological scoring, no neural replacement."""
from __future__ import annotations

import numpy as np

from forecasting.supply_uncertainty.evaluation import pinball_loss, weighted_interval_score


def point(y: np.ndarray, method: str) -> float:
    if method == "seasonal_naive" and len(y) >= 52:
        return float(y[-52])
    if method == "moving_average":
        return float(np.mean(y[-13:]))
    if method == "ewma":
        value = float(y[0])
        for obs in y[1:]:
            value = .2 * float(obs) + .8 * value
        return value
    # Croston-SBA and TSB are separate candidates, not a zero-demand quantile shortcut.
    nonzero = np.flatnonzero(y > 0)
    if not len(nonzero):
        return 0.0
    size = float(y[nonzero[0]])
    interval = float(nonzero[0] + 1)
    elapsed = 1
    probability = 1 / interval
    for obs in y[nonzero[0] + 1:]:
        probability = .2 * float(obs > 0) + .8 * probability
        if obs > 0:
            size = .2 * float(obs) + .8 * size
            interval = .2 * elapsed + .8 * interval
            elapsed = 1
        else:
            elapsed += 1
    return size * probability if method == "tsb" else .9 * size / interval


def fit(y: np.ndarray) -> dict:
    """Last 12 training observations are forecast-selection data, never final evidence."""
    methods = ["moving_average", "ewma", "croston_sba", "tsb"]
    if len(y) >= 68:
        methods.append("seasonal_naive")
    start = max(8, len(y) - 12)
    scores = {}
    for method in methods:
        pred = np.asarray([point(y[:t], method) for t in range(start, len(y))])
        scale = np.asarray([max(float(np.std(y[max(0, t-26):t])), 1e-6)
                            for t in range(start, len(y))])
        q = {level: np.maximum(0, pred + z * scale)
             for level, z in ((.1, -1.28155), (.5, 0), (.9, 1.28155))}
        scores[method] = {
            "wis": weighted_interval_score(y[start:], q),
            "pinball_90": pinball_loss(y[start:], q[.9], .9),
            "bias": float(np.mean(pred - y[start:])),
            "coverage_80": float(np.mean((y[start:] >= q[.1]) & (y[start:] <= q[.9])))}
    method = min(methods, key=lambda m: (scores[m]["wis"], methods.index(m)))
    return {"method": method, "mean": point(y, method),
            "sd": float(np.std(y[-52:], ddof=1)), "history_count": len(y),
            "zero_share": float(np.mean(y == 0)), "selection_scores": scores,
            "interval_status": "empirical, not coverage-guaranteed",
            "forecast_selection_is_not_final_holdout": True}
