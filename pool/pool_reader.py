"""Pool query interface — what the models are allowed to see.

The reader returns POPULATION-LEVEL priors only: pooled distribution
parameters per category/region/season, with operator counts for
transparency. The operator_id column on the signals exists for audit and
withdrawal accounting; this interface never exposes it, and nothing here
returns a single operator's signal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

from pool.pool_contributor import DEFAULT_POOL_ROOT


class DemandPrior(BaseModel):
    category: str
    demand_cv: float
    trend_consensus: str
    n_signals: int
    n_operators: int


class YieldPrior(BaseModel):
    category: str
    region: str
    season: str
    fill_rate_mean: float
    fill_rate_std: float
    alpha: float                 # Beta(α, β) for the hierarchical model
    beta: float
    n_deliveries: int
    n_operators: int


class WastePrior(BaseModel):
    category: str
    waste_rate: float
    primary_reason: str
    n_signals: int
    n_operators: int


class PoolStats(BaseModel):
    n_operators_contributing: int
    n_signals: int
    coverage_by_category: dict[str, int]
    signals_by_type: dict[str, int]


class PoolReader:
    def __init__(self, pool_root: str | Path | None = None) -> None:
        self.pool_root = Path(pool_root) if pool_root else DEFAULT_POOL_ROOT

    def _read(self, signal: str) -> pd.DataFrame:
        d = self.pool_root / "signals" / signal
        files = sorted(d.glob("*.parquet")) if d.exists() else []
        if not files:
            return pd.DataFrame()
        return pd.concat([pd.read_parquet(f) for f in files],
                         ignore_index=True)

    # ── priors ───────────────────────────────────────────────────────────

    def get_demand_prior(self, category: str,
                         week_of_year: int | None = None
                         ) -> Optional[DemandPrior]:
        df = self._read("demand_patterns")
        if df.empty:
            return None
        sel = df[df["category"] == category]
        if week_of_year is not None and "week_of_year" in sel.columns:
            near = sel[(sel["week_of_year"] - week_of_year).abs() <= 4]
            if not near.empty:
                sel = near
        if sel.empty:
            return None
        return DemandPrior(
            category=category,
            demand_cv=round(float(sel["demand_cv"].mean()), 4),
            trend_consensus=sel["trend_direction"].mode().iloc[0],
            n_signals=int(len(sel)),
            n_operators=int(sel["operator_id"].nunique()),
        )

    def get_yield_prior(self, category: str, region: str | None = None,
                        season: str | None = None) -> Optional[YieldPrior]:
        df = self._read("yield_distributions")
        if df.empty:
            return None
        sel = df[df["category"] == category]
        if region and not sel[sel["region"] == region].empty:
            sel = sel[sel["region"] == region]
        if season and not sel[sel["season"] == season].empty:
            sel = sel[sel["season"] == season]
        if sel.empty:
            return None
        # delivery-count-weighted pooling across contributions
        w = sel["n_deliveries"].to_numpy(dtype=float)
        mean = float(np.average(sel["fill_rate_mean"], weights=w))
        std = float(np.average(sel["fill_rate_std"], weights=w))
        var = max(std ** 2, 1e-6)
        from risk.supplier_distribution import _beta_from_mean_var
        a, b = _beta_from_mean_var(mean, var)
        return YieldPrior(
            category=category,
            region=region or "all",
            season=season or "all",
            fill_rate_mean=round(mean, 4),
            fill_rate_std=round(std, 4),
            alpha=round(float(a), 4), beta=round(float(b), 4),
            n_deliveries=int(w.sum()),
            n_operators=int(sel["operator_id"].nunique()),
        )

    def get_waste_prior(self, category: str) -> Optional[WastePrior]:
        df = self._read("waste_profiles")
        if df.empty:
            return None
        sel = df[df["category"] == category]
        if sel.empty:
            return None
        return WastePrior(
            category=category,
            waste_rate=round(float(sel["waste_rate"].mean()), 4),
            primary_reason=sel["primary_reason"].mode().iloc[0],
            n_signals=int(len(sel)),
            n_operators=int(sel["operator_id"].nunique()),
        )

    # ── stats (dashboard indicator) ──────────────────────────────────────

    def get_pool_stats(self) -> PoolStats:
        operators: set[str] = set()
        total = 0
        by_type: dict[str, int] = {}
        by_cat: dict[str, int] = {}
        for signal in ("demand_patterns", "yield_distributions",
                       "waste_profiles"):
            df = self._read(signal)
            if df.empty:
                continue
            by_type[signal] = len(df)
            total += len(df)
            operators |= set(df["operator_id"].unique())
            for c, n in df["category"].value_counts().items():
                by_cat[c] = by_cat.get(c, 0) + int(n)
        return PoolStats(
            n_operators_contributing=len(operators),
            n_signals=total,
            coverage_by_category=by_cat,
            signals_by_type=by_type,
        )
