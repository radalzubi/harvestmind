"""Recommendation confidence index.

AN INTERNAL INDEX, NOT A PROBABILITY. It combines two measured
quantities into one 0–100 number so an operator can rank trust across
recommendations, and its arithmetic is stated in the payload:

    demand component  = 1 − pooled out-of-sample WAPE of the demand
                        forecaster (rolling-origin, vs actuals)
    supply component  = 1 − average supplier interval spread
                        (posterior mean − downside, across suppliers)

    index = 100 × demand_component × supply_component

Both components are out-of-sample or distribution-derived — nothing in
the index is self-graded by the optimizer. When either input cannot be
measured (insufficient history) the index is None with the reason, never
a made-up default.
"""

from __future__ import annotations

from typing import Any


def recommendation_confidence(conn) -> dict[str, Any]:
    from forecasting.demand.demand_forecast_service import (
        evaluate_demand_forecaster,
    )
    from risk.supplier_distribution import supplier_fill_distributions

    ev = evaluate_demand_forecaster(conn)
    dists = supplier_fill_distributions(conn)
    spreads = [d["spread"] for sid, d in dists.items() if sid != "_prior"]

    if ev.get("status") != "ok" or not spreads:
        return {
            "index": None,
            "label": "internal index — not a probability",
            "reason": ("demand forecaster not yet evaluated on enough "
                       "history" if ev.get("status") != "ok"
                       else "no supplier distributions available"),
        }

    wape = float(ev["wape_model"])
    avg_spread = float(sum(spreads) / len(spreads))
    demand_component = max(1.0 - min(wape, 1.0), 0.0)
    supply_component = max(1.0 - min(avg_spread, 1.0), 0.0)
    index = round(100 * demand_component * supply_component)

    return {
        "index": index,
        "label": "internal index — not a probability",
        "arithmetic": "100 × (1 − OOS demand WAPE) × (1 − avg supplier "
                      "interval spread)",
        "components": {
            "demand_oos_wape": round(wape, 4),
            "avg_supplier_spread": round(avg_spread, 4),
        },
        "basis": "demand WAPE is rolling-origin out-of-sample; supplier "
                 "spread comes from the calibrated predictive Betas",
    }
