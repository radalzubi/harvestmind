"""Backtest: deterministic policy vs distribution + shelf-life policy.

Compares two commitment policies on the same operator history and estimates
how much realized loss the newer policy's additional conservatism would have
avoided:

    OLD: recommendations_by_product   (point-estimate fill rate, binary expiry)
    NEW: safe_commit_recommendations  (supplier downside quantile + shelf-life)

The estimate is deliberately bounded so it cannot overclaim. For each product,
the new policy is more conservative by (old_commit - new_commit) kg. We credit
that extra holdback against the loss that actually occurred on that product,
capped at the realized loss. You can never "avoid" more loss than the operator
actually incurred.

This is an estimate of avoided exposure, not an audited P&L, and it is computed
on whatever data is loaded. On the sample dataset it is a demonstration. On a
real operator's 6-12 months of history it becomes the dollar figure that
justifies the engagement. The fully rigorous version runs each policy through
the rolling-origin engine (decision at time t, scored on t+1 outcomes); this
function is the single-window form of that comparison.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import duckdb

from dashboard.lib.diagnostic_metrics import (
    recommendations_by_product, waste_loss_usd, shortage_loss_usd,
)
from risk.safe_commit import safe_commit_recommendations

_EPS = 1e-9


def _realized_losses(conn: duckdb.DuckDBPyConnection) -> dict[str, dict[str, float]]:
    """Realized waste and shortage per product from the loaded history."""
    waste = waste_loss_usd(conn)
    shortage = shortage_loss_usd(conn)

    out: dict[str, dict[str, float]] = {}
    for row in waste["by_product"]:
        name = row.get("product_name") or "—"
        e = out.setdefault(name, {"waste_kg": 0.0, "waste_usd": 0.0,
                                  "shortage_kg": 0.0, "shortage_usd": 0.0})
        e["waste_kg"] += float(row.get("quantity_lost_kg") or 0.0)
        e["waste_usd"] += float(row.get("loss_usd") or 0.0)
    for row in shortage["by_product"]:
        name = row.get("product_name") or "—"
        e = out.setdefault(name, {"waste_kg": 0.0, "waste_usd": 0.0,
                                  "shortage_kg": 0.0, "shortage_usd": 0.0})
        e["shortage_kg"] += float(row.get("missed_kg") or 0.0)
        e["shortage_usd"] += float(row.get("loss_usd") or 0.0)
    return out


def compare_policies(
    conn: duckdb.DuckDBPyConnection,
    as_of_date: date | None = None,
    lead_time_days: float = 3.0,
    quantile: float = 0.10,
) -> dict[str, Any]:
    """Compare deterministic vs distribution+shelf-life commitment policy.

    Returns per-product rows and a summary. The headline figure is the
    estimated avoided loss: realized loss on each product scaled by the
    fraction of it the new policy's extra holdback would have covered.
    """
    today = as_of_date or date.today()

    old = {r["product_name"]: r for r in recommendations_by_product(conn, as_of_date=today)}
    new = {r["product_name"]: r for r in safe_commit_recommendations(
        conn, as_of_date=today, lead_time_days=lead_time_days, quantile=quantile)}
    realized = _realized_losses(conn)

    products = sorted(set(old) | set(new) | set(realized))
    rows: list[dict[str, Any]] = []
    total_realized = 0.0
    total_avoided = 0.0

    for p in products:
        old_commit = float(old.get(p, {}).get("safe_commit_kg", 0.0))
        new_commit = float(new.get(p, {}).get("safe_commit_kg", 0.0))
        delta_kg = old_commit - new_commit  # positive = new more conservative

        rl = realized.get(p, {"waste_kg": 0.0, "waste_usd": 0.0,
                              "shortage_kg": 0.0, "shortage_usd": 0.0})
        realized_kg = rl["waste_kg"] + rl["shortage_kg"]
        realized_usd = rl["waste_usd"] + rl["shortage_usd"]
        total_realized += realized_usd

        # Fraction of realized loss the extra holdback would have covered,
        # capped at 100%. No coverage when the new policy is not more
        # conservative, or when there was no realized loss.
        if delta_kg > 0 and realized_kg > _EPS:
            covered_fraction = min(delta_kg / realized_kg, 1.0)
            avoided_usd = realized_usd * covered_fraction
        else:
            covered_fraction = 0.0
            avoided_usd = 0.0
        total_avoided += avoided_usd

        rows.append({
            "product_name": p,
            "old_safe_commit_kg": round(old_commit, 1),
            "new_safe_commit_kg": round(new_commit, 1),
            "extra_holdback_kg": round(max(delta_kg, 0.0), 1),
            "realized_loss_usd": round(realized_usd, 2),
            "covered_fraction": round(covered_fraction, 3),
            "estimated_avoided_usd": round(avoided_usd, 2),
        })

    rows.sort(key=lambda r: r["estimated_avoided_usd"], reverse=True)
    reduction_pct = (total_avoided / total_realized) if total_realized > _EPS else 0.0

    return {
        "as_of": today.isoformat(),
        "lead_time_days": lead_time_days,
        "quantile": quantile,
        "products": rows,
        "total_realized_loss_usd": round(total_realized, 2),
        "total_estimated_avoided_usd": round(total_avoided, 2),
        "estimated_reduction_pct": round(reduction_pct, 4),
        "note": ("Estimated avoided exposure, bounded by realized loss per "
                 "product. Single-window comparison on loaded data; the "
                 "rolling-origin engine produces the time-validated version "
                 "on a full operator history."),
    }
