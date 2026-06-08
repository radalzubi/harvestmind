"""Naive same-week-last-year commitment policy.

Acts as the no-AI baseline a planner would use without HarvestMind:
"commit whatever the supplier delivered same week last year." When that
data isn't available, fall back to the trailing 4-week mean.

This baseline is deliberately naive — it ignores demand forecasts, supplier
reliability, and waste history — so the LP and SP optimizers can produce a
meaningful improvement against it (in waste, spot premium, and fill rate).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


@dataclass
class NaivePolicyConfig:
    """Knobs that simulate the data-quality reality of a real food hub.

    A perfect spreadsheet of last-year-same-week deliveries (the synthetic
    case) is the strongest possible naive baseline. Real partners have
    incomplete records, supplier turnover, and noisy quantities. These knobs
    let the stress-test harness *degrade* the naive baseline to realistic
    quality and measure how the optimizer's relative advantage grows.
    """
    missing_rate: float = 0.0              # fraction of last-year lookups that fail
    noise_cv: float = 0.0                  # log-normal noise on commit qty (CV)
    supplier_turnover_rate: float = 0.0    # fraction of suppliers absent from this year
    seed: int = 42


def naive_lastyear_commitments(
    deliveries_train: pd.DataFrame,
    decision_date: date,
    horizon_weeks: list[date],
    fallback_lookback_weeks: int = 4,
    config: NaivePolicyConfig | None = None,
) -> pd.DataFrame:
    """Build a commitment plan that mirrors same-week-last-year deliveries.

    Args:
      deliveries_train: training-window slice of fact_deliveries
        (must have columns: supplier_id, product_id, delivery_date,
        qty_received_kg, optional qty_rejected_kg)
      decision_date: today, the commit decision is made on this date
      horizon_weeks: weeks the planner is committing for
      fallback_lookback_weeks: when no same-week-last-year data is available,
        commit the avg of this many trailing weeks instead.

    Returns:
      DataFrame [supplier_id, product_id, committed_kg, price_per_kg]
      shaped exactly like the LP/SP solvers' output, so it can be fed
      directly to simulate_recourse().
    """
    config = config or NaivePolicyConfig()
    rng = np.random.default_rng(config.seed)

    if deliveries_train.empty:
        return pd.DataFrame(
            columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"]
        )

    df = deliveries_train.copy()
    df["delivery_date"] = pd.to_datetime(df["delivery_date"]).dt.date
    received = df["qty_received_kg"].fillna(0.0)
    rejected = df["qty_rejected_kg"].fillna(0.0) if "qty_rejected_kg" in df.columns else 0.0
    df["accepted_kg"] = (received - rejected).clip(lower=0.0)

    # Optional: simulate supplier turnover by dropping a fraction of suppliers
    if config.supplier_turnover_rate > 0:
        unique_suppliers = df["supplier_id"].unique()
        n_drop = int(round(len(unique_suppliers) * config.supplier_turnover_rate))
        if n_drop > 0:
            dropped = rng.choice(unique_suppliers, size=n_drop, replace=False)
            df = df[~df["supplier_id"].isin(dropped)]

    # Pair each horizon week with the same calendar week from one year prior
    rows = []
    for horizon_week in horizon_weeks:
        # Optional: simulate missing same-week-last-year history
        if config.missing_rate > 0 and rng.random() < config.missing_rate:
            slice_ = pd.DataFrame()  # force fallback path
        else:
            last_year_week = horizon_week - timedelta(days=364)  # exact week alignment
            last_year_lo = last_year_week - timedelta(days=3)
            last_year_hi = last_year_week + timedelta(days=3)
            slice_ = df[
                (df["delivery_date"] >= last_year_lo)
                & (df["delivery_date"] <= last_year_hi)
            ]

        if slice_.empty:
            # Fallback: trailing-window WEEKLY RUN-RATE per supplier × product.
            # (Previously this used the mean *delivery size*, which on
            # high-volume data with multiple deliveries/week over-commits
            # badly — the run-rate is the fair "commit what we typically move
            # in a week" baseline. Appended once per horizon week below, so the
            # horizon total = weekly_rate × horizon_weeks.)
            fb_start = decision_date - timedelta(weeks=fallback_lookback_weeks)
            fb_slice = df[
                (df["delivery_date"] >= fb_start) & (df["delivery_date"] <= decision_date)
            ]
            if fb_slice.empty:
                continue
            weekly = (
                fb_slice.groupby(["supplier_id", "product_id"])["accepted_kg"]
                .sum()
                / max(fallback_lookback_weeks, 1)
            )
            agg = weekly.reset_index().rename(columns={"accepted_kg": "committed_kg"})
        else:
            agg = (
                slice_.groupby(["supplier_id", "product_id"])["accepted_kg"]
                .sum()
                .reset_index()
                .rename(columns={"accepted_kg": "committed_kg"})
            )

        rows.append(agg)

    if not rows:
        return pd.DataFrame(
            columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"]
        )

    # Sum across horizon weeks
    combined = pd.concat(rows, ignore_index=True)
    out = (
        combined.groupby(["supplier_id", "product_id"])["committed_kg"]
        .sum()
        .reset_index()
    )

    # Optional: log-normal noise on commit qty (CV)
    if config.noise_cv > 0 and not out.empty:
        sigma = float(config.noise_cv)
        # Multiplier = exp(N(-σ²/2, σ²)) so mean is preserved
        noise = np.exp(rng.normal(-0.5 * sigma * sigma, sigma, size=len(out)))
        out["committed_kg"] = (out["committed_kg"] * noise).clip(lower=0.0)

    out["price_per_kg"] = 2.0  # contract price stand-in
    return out
