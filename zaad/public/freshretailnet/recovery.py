"""Track B: stockout-aware demand recovery (DERIVED, never observed ground truth).

Method: in-stock-profile scaling. For one series, the hourly share profile p_h of daily sales is estimated on the
fully in-stock business days (no out-of-stock hour in 06:00..21:59) STRICTLY BEFORE the decision origin. On a day
with out-of-stock hours, the sales observed in the in-stock business hours are scaled up by the share of the profile
those hours represent; night hours (outside 06:00..21:59, where 97.5 % of sales do not occur) are kept as observed.
Recovered demand is never below observed sales, and the scaling is capped (`max_uplift`) so a day observed in stock
for only a sliver of its profile cannot be inflated without bound. Whatever the cap truncates is reported.

This is a deliberately simple, inspectable estimator (the paper's own baselines are neural imputers); its purpose is
to move the demand input in the direction censoring biases it, with every assumption visible, and to let the pilot
report how much the policy comparison depends on that move. It is compared against the naive uniform-hour benchmark
(scale by 16 / in-stock hours) and against observed sales; the three are reported side by side.

Information boundary: the profile for a day at or after the origin uses only days before the origin; for days before
the origin (the planner's history) the profile uses only days before THAT origin as well, so a decision never
benefits from later observations. The evaluation week never enters any profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np

BUSINESS = slice(6, 22)         # hours 6..21
N_BUSINESS = 16
RECOVERY_VERSION = "frn-recovery-1 (in-stock-profile scaling, cap 3x)"


@dataclass(frozen=True)
class DayRecord:
    day: date
    sales: float                      # observed daily total (OBSERVED)
    hourly_sales: np.ndarray          # 24 values (OBSERVED)
    out_of_stock: np.ndarray          # 24 flags, 1 = out of stock (OBSERVED)

    @property
    def out_hours(self) -> int:
        return int(self.out_of_stock[BUSINESS].sum())


@dataclass(frozen=True)
class Recovered:
    day: date
    observed: float
    recovered: float                  # DERIVED
    naive: float                      # DERIVED benchmark: uniform-hour scaling
    method: str                       # "observed" (no stockout), "profile", "naive_fallback", "capped"
    profile_days: int                 # fully in-stock days the profile was fitted on


def profile(history: list[DayRecord]) -> tuple[np.ndarray | None, int]:
    """Hourly share profile over business hours from fully in-stock days; None when fewer than 7 such days exist."""
    clean = [d.hourly_sales[BUSINESS] for d in history if d.out_hours == 0 and d.sales > 0]
    if len(clean) < 7:
        return None, len(clean)
    total = np.sum(clean, axis=0)
    if total.sum() <= 0:
        return None, len(clean)
    return total / total.sum(), len(clean)


def recover_day(day: DayRecord, prof: np.ndarray | None, profile_days: int, *, max_uplift: float = 3.0) -> Recovered:
    out = day.out_of_stock[BUSINESS].astype(bool)
    k = int(out.sum())
    if k == 0:
        return Recovered(day.day, day.sales, day.sales, day.sales, "observed", profile_days)
    business = day.hourly_sales[BUSINESS]
    night = float(day.sales - business.sum())
    in_stock_sales = float(business[~out].sum())
    in_stock_hours = N_BUSINESS - k
    naive = night + (in_stock_sales * N_BUSINESS / in_stock_hours if in_stock_hours > 0 else in_stock_sales)
    if prof is None:
        estimate, method = naive, "naive_fallback"
    else:
        share = float(prof[~out].sum())
        estimate, method = (night + in_stock_sales / share, "profile") if share > 0 else (naive, "naive_fallback")
    cap = max(day.sales, day.sales * max_uplift)
    if estimate > cap:
        estimate, method = cap, "capped"
    estimate = max(estimate, day.sales)
    return Recovered(day.day, day.sales, float(estimate), float(max(naive, day.sales)), method, profile_days)


def recover_series(records: list[DayRecord], *, origin: date, max_uplift: float = 3.0) -> list[Recovered]:
    """Recovered demand for every record, each day using a profile fitted on fully in-stock days before `origin` only
    (and, for days before the origin, before that day as well, so history never looks forward)."""
    ordered = sorted(records, key=lambda r: r.day)
    out = []
    for r in ordered:
        boundary = min(origin, r.day) if r.day < origin else origin
        prof, n = profile([d for d in ordered if d.day < boundary])
        out.append(recover_day(r, prof, n, max_uplift=max_uplift))
    return out


def summary(rows: list[Recovered]) -> dict[str, Any]:
    obs = sum(r.observed for r in rows)
    rec = sum(r.recovered for r in rows)
    naive = sum(r.naive for r in rows)
    return {"version": RECOVERY_VERSION, "days": len(rows), "observed_total": obs, "recovered_total": rec, "naive_total": naive,
            "recovered_uplift": (rec / obs - 1) if obs > 0 else None, "naive_uplift": (naive / obs - 1) if obs > 0 else None,
            "days_by_method": {m: sum(1 for r in rows if r.method == m) for m in ("observed", "profile", "naive_fallback", "capped")},
            "evidence": "DERIVED: recovered demand is an estimate, never observed ground truth"}
