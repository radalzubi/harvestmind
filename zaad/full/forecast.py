"""Review-by-review causal demand adaptation and occurrence/size uncertainty."""
from __future__ import annotations

import math

import numpy as np

from zaad.forecast import point


def change_origin(y: np.ndarray, mode: str = "symmetric") -> int:
    """Clipped CUSUM change-point origin; two observations required, never one-spike reset.

    symmetric   the frozen PR23 rule: same threshold for upward and downward shifts.
    asymmetric  a downward shift needs a higher accumulated score AND the last two observations
                both below the base level, because under-ordering after a false downward alarm
                costs shortage penalties while over-ordering after a false upward alarm costs
                holding. Upward detection is unchanged.
    soft / ensemble use the symmetric origin; they blend forecasts instead of hard-resetting.
    page_hinkley / bocpd delegate to zaad.full.surge and keep the same origin contract.
    """
    if mode in ("page_hinkley", "bocpd"):
        from zaad.full.surge import DETECTORS
        return DETECTORS[mode](y)
    origin, positive, negative = 0, 0., 0.
    down_threshold = 6.5 if mode == "asymmetric" else 4.5
    for t in range(16, len(y)):
        base = y[max(origin, t - 26):t]
        if len(base) < 8:
            continue
        scale = max(float(np.std(base)), abs(float(np.mean(base))) * .1, 1.)
        z = float(np.clip((y[t] - np.mean(base)) / scale, -3, 3))
        positive = max(0., positive + z - .5)
        negative = max(0., negative - z - .5)
        if positive > 4.5:
            origin, positive, negative = max(0, t - 1), 0., 0.
        elif negative > down_threshold:
            if mode == "asymmetric":
                level = float(np.mean(base))
                if not (y[t] < level - .5 * scale and y[t - 1] < level - .5 * scale):
                    continue    # one dip does not confirm a persistent decline
            origin, positive, negative = max(0, t - 1), 0., 0.
    return origin


def _blend_weight(post: int, downward: bool, mode: str) -> float:
    """Weight on the post-change segment. Soft mode trusts a decline only as it persists."""
    if mode != "soft":
        return 1.
    return min(1., post / (12. if downward else 6.))


def _fit_segment(segment: np.ndarray, shortage: float, holding: float, seasonal: bool = True) -> tuple[str, float, dict]:
    methods = ["moving_average", "ewma", "croston_sba", "tsb", "recent_level"]
    if seasonal and len(segment) >= 68:
        # The 52-observation lag is an annual cycle on WEEKLY periods and nothing on any other period length; a
        # caller planning daily periods passes seasonal=False (E1, FreshRetailNet audit: on daily data the candidate
        # became eligible once the history passed 68 days and was selected on 197 of 1,100 such reviews).
        methods.append("seasonal_naive")

    def predict(a, method):
        return float(np.mean(a[-4:])) if method == "recent_level" else point(a, method)

    scores = {}
    for method in methods:
        losses = []
        for t in range(max(4, len(segment) - 12), len(segment)):
            q = predict(segment[:t], method)
            # Inventory decision loss, not MAE; same economic rates for all methods.
            losses.append(shortage * max(segment[t] - q, 0) + holding * max(q - segment[t], 0))
        scores[method] = float(np.mean(losses)) if losses else 0.
    method = min(methods, key=lambda m: (scores[m], methods.index(m)))
    if len(segment) < 4:
        method = "recent_level"
    return method, predict(segment, method), scores


def estimate(y: np.ndarray, shortage: float, holding: float, adaptive: bool = True, mode: str = "symmetric", seasonal: bool = True) -> dict:
    """`seasonal` offers the 52-lag candidate; it is meaningful only on weekly periods (`worlds.forecast_all` passes
    `req.period_days == 7`). The default keeps every weekly caller unchanged."""
    if len(y) < 16 or np.any(~np.isfinite(y)) or np.any(y < 0):
        raise ValueError("demand needs 16 finite, nonnegative, explicitly zero-filled observations")
    origin = change_origin(y, mode) if adaptive else 0
    segment = y[origin:]
    if adaptive and origin > 0 and mode in ("soft", "ensemble"):
        pre = y[:origin]
        method, post_mean, scores = _fit_segment(segment, shortage, holding, seasonal)
        pre_method, pre_mean, _ = _fit_segment(pre, shortage, holding, seasonal)
        downward = post_mean < pre_mean
        if mode == "soft":
            w = _blend_weight(len(segment), downward, mode)
        else:
            # Ensemble: weight the two levels by their recent decision loss on the observations
            # since the change; a decline that keeps costing holding wins, a dip that costs shortage loses.
            recent = y[origin:]
            loss_pre = float(np.mean([shortage * max(v - pre_mean, 0) + holding * max(pre_mean - v, 0) for v in recent]))
            loss_post = float(np.mean([shortage * max(v - post_mean, 0) + holding * max(post_mean - v, 0) for v in recent]))
            w = loss_pre / (loss_pre + loss_post) if loss_pre + loss_post > 0 else .5
        mean = w * post_mean + (1 - w) * pre_mean
        nonzero = segment[segment > 0] if len(segment[segment > 0]) >= 4 else y[y > 0]
        probability = float(np.mean(segment > 0)) if len(segment) >= 4 else float(np.mean(y > 0))
        sd = float(np.sqrt(w * np.var(segment) + (1 - w) * np.var(pre))) if len(segment) > 1 else float(np.std(pre))
        return {"method": method, "mean": float(mean), "segment_origin": origin, "adaptation": mode,
                "blend_weight_post": float(w), "pre_change_mean": float(pre_mean), "post_change_mean": float(post_mean),
                "history_count": len(y), "segment_count": len(segment),
                "zero_probability": 1 - probability, "decision_losses": scores,
                "sd": sd, "sizes": nonzero.tolist(),
                "interval_status": "empirical blend of pre/post-change segments; no coverage guarantee after drift"}
    method, mean, scores = _fit_segment(segment, shortage, holding, seasonal)
    nonzero = segment[segment > 0]
    probability = float(np.mean(segment > 0))
    if method == "tsb" and len(nonzero):
        probability = min(1., mean / float(np.mean(nonzero)))
    return {"method": method, "mean": mean, "segment_origin": origin, "adaptation": mode if adaptive else "frozen",
            "history_count": len(y), "segment_count": len(segment),
            "zero_probability": 1 - probability, "decision_losses": scores,
            # A young segment's own standard deviation is bounded below by the pre-change spread
            # (fading as the segment grows) so a run of identical readings never reports certainty.
            "sd": float(max(np.std(segment), (np.std(y[:origin]) if origin > 1 else 0.) * math.sqrt(max(0., 1. - len(segment) / 8.)))), "sizes": nonzero.tolist(),
            "interval_status": "empirical; no coverage guarantee after drift"}


def sample(fit: dict, rng: np.random.Generator, horizon: int, u: np.ndarray | None = None) -> np.ndarray:
    """One demand path. Without `u`: the bootstrap draw used since v1 (unchanged, so every
    truth path drawn by seed stays identical). With `u` (one uniform per period, P1): the same
    mixture distribution through its quantile function - zeros occupy the bottom of the unit
    interval, then the empirical size quantiles - so a stratified caller can place a period in
    the body or the tail of the fitted distribution deliberately."""
    sizes = np.asarray(fit["sizes"])
    if not len(sizes) or fit["mean"] == 0:
        return np.zeros(horizon)
    occurrence = 1 - fit["zero_probability"]
    scale = fit["mean"] / (occurrence * np.mean(sizes))
    if u is not None:
        u = np.asarray(u, dtype=float)
        zero = 1. - occurrence
        inner = np.clip((u - zero) / max(occurrence, 1e-12), 0., 1.)
        values = np.quantile(np.sort(sizes), inner, method="inverted_cdf") * scale
        return np.where(u < zero, 0., values)
    # Scaling nonzero size preserves estimated unconditional mean AND exact zeros.
    values = rng.choice(sizes, horizon) * scale
    return np.where(rng.random(horizon) < occurrence, values, 0.)
