"""Transparent per-SKU and per-supplier regime diagnostics.

Statistical rules with stated thresholds. No fitted classifier: a regime
label must be explainable to a buyer in one sentence, and it must be
computable from the same training window the plan used.
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field

CALM, VOLATILE, CONSTRAINED, PROMOTION, DISRUPTION, RECOVERY = (
    "CALM", "VOLATILE_DEMAND", "SUPPLY_CONSTRAINED", "PROMOTION", "DISRUPTION", "RECOVERY")


@dataclass
class SkuRegime:
    sku: str
    regime: str
    demand_cv: float
    intermittency: float
    cover_periods: float
    supplier_fill_mean: float
    supplier_fill_sd: float
    lead_periods: int
    promo_ahead: bool
    drift: float
    features: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)


def _cv(xs):
    m = st.mean(xs) if xs else 0.0
    return (st.pstdev(xs) / m) if m > 0 and len(xs) > 1 else 0.0


def _drift(xs, k=8):
    """Recent mean vs prior mean, relative; a change-point indicator."""
    if len(xs) < 2 * k:
        return 0.0
    recent, prior = st.mean(xs[-k:]), st.mean(xs[-2 * k:-k])
    return (recent - prior) / prior if prior > 0 else 0.0


def diagnose(fi, thresholds: dict | None = None) -> dict:
    th = {"cv_volatile": 0.5, "intermittent": 0.35, "fill_low": 0.90, "fill_sd_high": 0.08,
          "cover_thin": 1.0, "drift_abs": 0.25, "recovery_fill_recent": 0.93}
    th.update(thresholds or {})
    out = {}
    for j in fi.products:
        hist = fi.train_demand[j]
        s_ = fi.supplier_of[j]
        fills = fi.train_fill.get(s_, [])
        mu = st.mean(hist) if hist else 0.0
        cv = _cv(hist)
        inter = (sum(1 for x in hist if x <= 0) / len(hist)) if hist else 0.0
        cover = (fi.opening.get(j, 0.0) + sum(q for (jj, t), q in fi.pipeline.items() if jj == j)) / mu if mu > 0 else 99.0
        fmean = st.mean(fills) if fills else 1.0
        fsd = st.pstdev(fills) if len(fills) > 1 else 0.0
        recent_fill = st.mean(fills[-4:]) if len(fills) >= 4 else fmean
        early_fill = st.mean(fills[-12:-4]) if len(fills) >= 12 else fmean
        promo = any(t < fi.horizon and v > 1.05 for (jj, t), v in fi.promo_multiplier.items() if jj == j)
        drift = _drift(hist)
        reasons = []
        if promo:
            regime = PROMOTION
            reasons.append("planned promotion inside the horizon")
        elif early_fill < th["fill_low"] and recent_fill >= th["recovery_fill_recent"]:
            regime = RECOVERY
            reasons.append(f"supplier fill recovered to {recent_fill:.0%} from {early_fill:.0%}")
        elif fmean < th["fill_low"] or fsd > th["fill_sd_high"] or (recent_fill < th["fill_low"] and fmean >= th["fill_low"]):
            regime = DISRUPTION if recent_fill < early_fill - 0.1 else CONSTRAINED
            reasons.append(f"supplier fill mean {fmean:.0%}, sd {fsd:.2f}, recent {recent_fill:.0%}")
        elif cv > th["cv_volatile"] or inter > th["intermittent"] or abs(drift) > th["drift_abs"]:
            regime = VOLATILE
            reasons.append(f"demand CV {cv:.2f}, zero-share {inter:.0%}, drift {drift:+.0%}")
        else:
            regime = CALM
            reasons.append(f"demand CV {cv:.2f}, fill {fmean:.0%}, cover {cover:.1f} periods")
        if cover < th["cover_thin"] and regime == CALM:
            reasons.append(f"cover thin at {cover:.1f} periods")
        out[j] = SkuRegime(sku=j, regime=regime, demand_cv=cv, intermittency=inter, cover_periods=cover,
                           supplier_fill_mean=fmean, supplier_fill_sd=fsd, lead_periods=int(fi.lead_of[s_]),
                           promo_ahead=promo, drift=drift,
                           features={"recent_fill": recent_fill, "early_fill": early_fill}, reasons=reasons)
    return out


def summarize(regimes: dict) -> dict:
    counts: dict = {}
    for r in regimes.values():
        counts[r.regime] = counts.get(r.regime, 0) + 1
    dominant = max(counts, key=lambda k: counts[k]) if counts else CALM
    return {"counts": counts, "dominant": dominant, "n": len(regimes)}
