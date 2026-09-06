"""Review-by-review causal demand adaptation and occurrence/size uncertainty."""
from __future__ import annotations

import numpy as np

from zaad.forecast import point


def change_origin(y: np.ndarray) -> int:
    """Two-sided clipped CUSUM; two observations required, never one-spike reset."""
    origin, positive, negative = 0, 0., 0.
    for t in range(16, len(y)):
        base = y[max(origin, t - 26):t]
        if len(base) < 8:
            continue
        scale = max(float(np.std(base)), abs(float(np.mean(base))) * .1, 1.)
        z = float(np.clip((y[t] - np.mean(base)) / scale, -3, 3))
        positive = max(0., positive + z - .5)
        negative = max(0., negative - z - .5)
        if max(positive, negative) > 4.5:
            origin, positive, negative = max(0, t - 1), 0., 0.
    return origin


def estimate(y: np.ndarray, shortage: float, holding: float, adaptive: bool = True) -> dict:
    if len(y) < 16 or np.any(~np.isfinite(y)) or np.any(y < 0):
        raise ValueError("demand needs 16 finite, nonnegative, explicitly zero-filled observations")
    origin = change_origin(y) if adaptive else 0
    segment = y[origin:]
    methods = ["moving_average", "ewma", "croston_sba", "tsb", "recent_level"]
    if len(segment) >= 68:
        methods.append("seasonal_naive")
    def predict(a, method):
        return float(np.mean(a[-4:])) if method == "recent_level" else point(a, method)
    scores = {}
    for method in methods:
        losses = []
        for t in range(max(4, len(segment) - 12), len(segment)):
            history = segment[:t]
            q = predict(history, method)
            # Inventory decision loss, not MAE; same economic rates for all methods.
            losses.append(shortage * max(segment[t] - q, 0) + holding * max(q - segment[t], 0))
        scores[method] = float(np.mean(losses)) if losses else 0.
    method = min(methods, key=lambda m: (scores[m], methods.index(m)))
    if len(segment) < 4:
        method = "recent_level"
    mean = predict(segment, method)
    nonzero = segment[segment > 0]
    probability = float(np.mean(segment > 0))
    if method == "tsb" and len(nonzero):
        probability = min(1., mean / float(np.mean(nonzero)))
    return {"method": method, "mean": mean, "segment_origin": origin,
            "history_count": len(y), "segment_count": len(segment),
            "zero_probability": 1 - probability, "decision_losses": scores,
            "sd": float(np.std(segment)), "sizes": nonzero.tolist(),
            "interval_status": "empirical; no coverage guarantee after drift"}


def sample(fit: dict, rng: np.random.Generator, horizon: int) -> np.ndarray:
    sizes = np.asarray(fit["sizes"])
    if not len(sizes) or fit["mean"] == 0:
        return np.zeros(horizon)
    occurrence = 1 - fit["zero_probability"]
    # Scaling nonzero size preserves estimated unconditional mean AND exact zeros.
    values = rng.choice(sizes, horizon) * fit["mean"] / (occurrence * np.mean(sizes))
    return np.where(rng.random(horizon) < occurrence, values, 0.)
