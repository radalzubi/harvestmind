"""Finite-horizon continuation value of the stock left at the end of an evaluation window.

Evaluation only: nothing here enters a solve, a candidate's objective or the settlement ledger. The
realised ledger keeps crediting residual stock at the declared salvage (`terminal_value`); this module
reports, separately, what that stock is worth in expectation beyond the truncated window, and the
adjustment between the two. It exists because a window that ends inside a policy's lot cycle credits
a lot that will be consumed within a few weeks at salvage, which measures the window, not the policy
(P1 close-out, sections D5 and H7).

Derivation, per SKU/location, from the last review's fitted demand and the declared economics only:

* residual units become available at their arrival time (on hand: 0; in transit: due period);
* they are consumed in order of availability, then earliest expiry, at the fitted mean demand rate
  mu per period (the same continuation demand the model's own post-horizon term uses);
* the k-th unit consumed at time tau_k avoids a purchase of one unit (`asset_value`), less the
  carrying and cost of capital it accrues until then, `asset_value * (holding + capital) * tau_k`;
* a unit that would expire before it is consumed, or that is never consumed (mu = 0), is worth its
  salvage less nothing more; every unit is worth at least its salvage, which the operator can always
  realise;
* no unit is ever worth more than the purchase it avoids.

There is no fixture constant, no cap on the horizon, and no policy-specific term: a policy with a
lot straddling the window end and a policy that stops one lot earlier are valued by the same rule.
"""
from __future__ import annotations

from zaad.full.contracts import Request


def continuation_value(req: Request, end_stock: list[dict], pending: list, fits: dict, window_end: int = 1,
                       landed: dict[str, float] | None = None) -> dict:
    """Value residual stock beyond the window. `end_stock` rows are the last settlement's
    (sku, location, expiry, quantity); `pending` its in-transit tuples (sku, location, expiry, due,
    quantity, kind); `fits` the last review's forecast (mean per service). Returns the salvage credit
    the ledger already holds, the continuation credit, and the adjustment (continuation minus
    salvage, as a cost delta: negative when the stock is worth more than salvage). `window_end` is the
    settlement step count of the last review (1 in a rolling replay): due and expiry indices in the
    settlement are counted from that review's period 0, so post-window time is offset by it. `landed`
    (optional, per SKU) is the unit cost the consumption of a residual unit avoids when that cost is
    more than the bare unit price: price plus the freight, ordering and receiving cost per unit the
    policy actually incurred (benchmark pass J correction 1). Carrying stays on the asset value, as
    the ledger charges it. Without `landed` the avoided purchase is `asset_value`, as before."""
    skus = {s.id: s for s in req.skus}
    locs = {loc.id: loc for loc in req.locations}
    mu: dict[tuple[str, str], float] = {}
    for s in req.services:
        mu[s.sku, s.location] = mu.get((s.sku, s.location), 0.) + float(fits[s.id]["mean"])
    lots: dict[tuple[str, str], list[tuple[float, float, float]]] = {}
    for row in end_stock:
        if row["quantity"] > 1e-9:
            lots.setdefault((row["sku"], row["location"]), []).append((0., float(row["expiry"]) - window_end, float(row["quantity"])))
    for sku, location, expiry, due, quantity, _kind in pending:
        if quantity > 1e-9:
            lots.setdefault((sku, location), []).append((max(0., float(due) - window_end), float(expiry) - window_end, float(quantity)))
    salvage_credit = continuation_credit = units = 0.
    detail = {}
    for key, rows in lots.items():
        sku, location = key
        asset, salvage = skus[sku].asset_value, skus[sku].terminal_value
        price = max(asset, (landed or {}).get(sku, asset))
        rate = float(locs[location].holding_per_value_period + req.liquidity.cost_of_capital_per_period)
        demand = mu.get(key, 0.)
        consumed_before = 0.       # units consumed ahead of the lot being valued
        value_here = salvage_here = 0.
        consumed_units = 0.
        for available, expiry, quantity in sorted(rows, key=lambda r: (r[0], r[1])):
            salvage_here += quantity * salvage
            if demand <= 0:
                value_here += quantity * salvage
                consumed_before += quantity
                continue
            # units are consumed one at a time from the lot's availability at the fitted rate; the
            # first unit of this lot waits for the units still ahead of it in the queue
            start = max(available, consumed_before / demand)
            n = int(quantity)
            frac = quantity - n
            for k in range(n + (1 if frac > 1e-9 else 0)):
                q = 1. if k < n else frac
                tau = start + (k + .5) / demand
                if tau >= expiry:
                    value_here += q * salvage
                else:
                    value_here += q * min(price, max(salvage, price - asset * rate * tau))
                    consumed_units += q
            consumed_before += quantity
        salvage_credit += salvage_here
        continuation_credit += value_here
        units += sum(r[2] for r in rows)
        detail[f"{sku}@{location}"] = {"units": sum(r[2] for r in rows), "consumed_before_expiry": consumed_units, "fitted_demand_per_period": demand,
                                       "periods_to_consume": (sum(r[2] for r in rows) / demand if demand > 0 else None),
                                       "salvage_credit": salvage_here, "continuation_credit": value_here}
    return {"units": units, "salvage_credit": salvage_credit, "continuation_credit": continuation_credit,
            "adjustment": -(continuation_credit - salvage_credit),
            "scope": ("evaluation only: residual stock valued at the purchase each unit avoids when consumed at the fitted "
                      "demand rate, less carrying and cost of capital until then, floored at salvage and capped at unit value; "
                      "expired-before-consumption units at salvage; the settlement ledger is unchanged"),
            "detail": detail}
