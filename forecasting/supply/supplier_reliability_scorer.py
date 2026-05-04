"""Supplier reliability scorer: updates dim_suppliers.avg_reliability weekly.

Reliability = weighted average of:
  - Delivery fill rate (qty_received / qty_committed)
  - Rejection rate (1 - qty_rejected / qty_received)
  - On-time delivery rate
  - Quality score (grade distribution)
"""

from __future__ import annotations

import pandas as pd


FILL_RATE_WEIGHT = 0.40
QUALITY_WEIGHT = 0.35
REJECTION_WEIGHT = 0.15
ONTIME_WEIGHT = 0.10
DECAY = 0.85  # exponential decay factor for older observations


def score_suppliers(
    deliveries_df: pd.DataFrame,
    po_df: pd.DataFrame,
    n_weeks: int = 13,  # trailing window
) -> pd.DataFrame:
    """Compute reliability scores for each supplier.

    Parameters
    ----------
    deliveries_df : [supplier_id, delivery_date, qty_received_kg, qty_rejected_kg,
                     grade_received, temp_on_arrival_c]
    po_df         : [supplier_id, week_start, qty_committed_kg, delivery_window_end]

    Returns
    -------
    DataFrame [supplier_id, avg_reliability, fill_rate, rejection_rate, quality_score,
               n_deliveries, as_of_date]
    """
    deliveries_df = deliveries_df.copy()
    po_df = po_df.copy()
    deliveries_df["delivery_date"] = pd.to_datetime(deliveries_df["delivery_date"])
    po_df["week_start"] = pd.to_datetime(po_df["week_start"])

    cutoff = deliveries_df["delivery_date"].max()
    window_start = cutoff - pd.Timedelta(weeks=n_weeks)
    del_window = deliveries_df[deliveries_df["delivery_date"] >= window_start].copy()

    if del_window.empty:
        return pd.DataFrame(columns=["supplier_id","avg_reliability"])

    # Age-weighted fill rate
    del_window["age_weeks"] = (cutoff - del_window["delivery_date"]).dt.days / 7
    del_window["weight"] = DECAY ** del_window["age_weeks"]

    # Merge PO commitments to compute fill rate
    po_window = po_df[po_df["week_start"] >= window_start][["supplier_id","week_start","qty_committed_kg"]].copy()
    po_window = po_window.groupby("supplier_id")["qty_committed_kg"].sum().rename("total_committed")
    del_agg = del_window.groupby("supplier_id").apply(
        lambda g: pd.Series({
            "total_received": (g["qty_received_kg"] * g["weight"]).sum(),
            "total_rejected": (g["qty_rejected_kg"] * g["weight"]).sum(),
            "total_weight": g["weight"].sum(),
            "n_deliveries": len(g),
        })
    )
    del_agg = del_agg.join(po_window, how="left")
    del_agg["total_committed"] = del_agg["total_committed"].fillna(del_agg["total_received"])

    scores = []
    for sup_id, row in del_agg.iterrows():
        w = row["total_weight"] if row["total_weight"] > 0 else 1.0
        fill = min(1.0, row["total_received"] / row["total_committed"]) if row["total_committed"] > 0 else 0.0
        rejection = 1.0 - (row["total_rejected"] / row["total_received"]) if row["total_received"] > 0 else 0.0
        # Quality score: proxy via rejection rate + temp compliance (if available)
        quality = rejection
        ontime = 0.90  # placeholder (would need delivery_date vs committed date)
        reliability = (
            FILL_RATE_WEIGHT * fill
            + QUALITY_WEIGHT * quality
            + REJECTION_WEIGHT * rejection
            + ONTIME_WEIGHT * ontime
        )
        scores.append({
            "supplier_id": sup_id,
            "avg_reliability": round(min(1.0, max(0.0, reliability)), 4),
            "fill_rate": round(fill, 4),
            "rejection_rate": round(1 - rejection, 4),
            "quality_score": round(quality, 4),
            "n_deliveries": int(row["n_deliveries"]),
            "as_of_date": cutoff.date(),
        })

    return pd.DataFrame(scores).sort_values("avg_reliability", ascending=False)
