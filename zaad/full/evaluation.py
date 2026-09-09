"""Extended-window evaluation of the rolling replay (P1 benchmark pass, evaluation only).

Two pieces, neither of which enters a solve, a candidate or the settlement ledger:

* `long_truth`: one truth path long enough for a rolling replay, stitched from fixed-length draws of the
  same request so that every period has the fitted distribution and the first segment is bit-identical
  to the legacy truth (`draw(req, seed, 1)[0]` when `req.horizon == segment`).
* `endpoint`: the score of a rolling replay at any endpoint W (reviews scored), reconstructed from the
  per-review settlements: the opening assets of review 0, every ledger component of reviews 0..W-1, and
  the terminal state of review W-1 valued under the salvage rule (the ledger's own `closing_assets`) and
  under the continuation rule (`zaad/full/terminal.py`), at the bare unit price and at the policy's own
  landed unit cost (correction 1 of the pre-registration). The reconstruction is identical to a replay
  stopped at W (tested), so one run yields the whole convergence curve.

Service, breaches and unmet are measured inside the window only. The same function scores every
policy: there is no policy argument and no fixture constant.
"""
from __future__ import annotations

from datetime import timedelta

from zaad.full.contracts import Request
from zaad.full.economics import cost_breakdown
from zaad.full.terminal import continuation_value
from zaad.full.worlds import World, draw


def long_truth(req: Request, seed: int, periods: int, segment: int | None = None) -> World:
    """Truth over `periods` periods. Segment k is `draw` on the request with `as_of` advanced by
    k * segment periods and seed `seed + k`; arrivals are shifted back to review-0 periods. PO due
    dates and fills come from segment 0 (they only matter at review 0)."""
    segment = req.horizon if segment is None else segment
    base = req if req.horizon == segment else req.model_copy(update={"horizon": segment})
    demand: dict[str, list[float]] = {s.id: [] for s in req.services}
    arrival: dict[tuple[str, int], int] = {}
    fills: dict[tuple[str, int], float] = {}
    po_due, po_fill = {}, {}
    for k in range(-(-periods // segment)):
        shifted = base if k == 0 else base.model_copy(update={"as_of": base.as_of + timedelta(days=k * segment * base.period_days)})
        world = draw(shifted, seed + k, 1)[0]
        if k == 0:
            po_due, po_fill = dict(world.po_due), dict(world.po_fill)
        for s in req.services:
            demand[s.id].extend(world.demand[s.id])
        for (source, t), a in world.arrival.items():
            arrival[source, k * segment + t] = a + k * segment
        for (source, t), f in world.fills.items():
            fills[source, k * segment + t] = f
    return World(f"long:{seed}:{periods}", 1., {s: tuple(v[:periods]) for s, v in demand.items()},
                 {key: a for key, a in arrival.items() if key[1] < periods}, {key: f for key, f in fills.items() if key[1] < periods},
                 po_due, po_fill)


def endpoint(initial: Request, reviews_log: list[dict], W: int) -> dict:
    """Score the first W reviews of a rolling replay. Returns the realised (salvage) cost, the
    continuation-valued cost, the ledger and its components, service inside the window, and the
    terminal state (on hand, in transit, next arrival)."""
    if not 1 <= W <= len(reviews_log):
        raise ValueError("endpoint outside the replayed window")
    rows = reviews_log[:W]
    ledger: dict[str, float] = {}
    for row in rows:
        for key, value in row["settlement"]["ledger"].items():
            if key not in {"opening_assets", "closing_assets"}:
                ledger[key] = ledger.get(key, 0.) + value
    ledger["opening_assets"] = rows[0]["settlement"]["ledger"]["opening_assets"]
    ledger["closing_assets"] = rows[-1]["settlement"]["ledger"]["closing_assets"]
    realized = sum(ledger.values())
    last = rows[-1]["settlement"]
    term = continuation_value(initial, last.get("end_stock", []), last.get("pending", []), rows[-1]["forecast"])
    # Landed-cost variant (correction 1): each SKU's avoided purchase is its unit price plus the freight,
    # ordering and receiving cost per unit this policy incurred over the window (zero when it bought nothing).
    components = cost_breakdown(ledger)
    units_bought = sum(p["quantity"] for row in rows for p in row["purchases"])
    premium = (components["FREIGHT"] + components["ORDERING"] + components["RECEIVING"]) / units_bought if units_bought > 0 else 0.
    landed = {s.id: s.asset_value + premium for s in initial.skus}
    term_landed = continuation_value(initial, last.get("end_stock", []), last.get("pending", []), rows[-1]["forecast"], landed=landed)
    served = demand = 0.
    targets = {s.id: s.target for s in initial.services}
    breaches = 0
    inventory = []
    for row in rows:
        st = row["settlement"]
        s_ = sum(x["served"] for x in st["service_by_period"])
        d_ = sum(x["demand"] for x in st["service_by_period"])
        served += s_
        demand += d_
        if d_ > 0 and any(s_ / d_ < targets[k] - initial.service_tolerance for k in targets):
            breaches += 1
        inventory.append(sum(x["quantity"] for x in st["end_stock"]))
    on_hand = sum(x["quantity"] for x in last.get("end_stock", []))
    pending = last.get("pending", [])
    in_transit = sum(p[4] for p in pending)
    next_due = min((p[3] for p in pending), default=None)
    return {"W": W, "realized": realized, "continuation": realized + term["adjustment"], "continuation_landed": realized + term_landed["adjustment"],
            "salvage_credit": term["salvage_credit"], "continuation_credit": term["continuation_credit"], "continuation_landed_credit": term_landed["continuation_credit"],
            "landed_premium_per_unit": premium,
            "ledger": ledger, "components": {k: components[k] for k in ("PURCHASE", "FREIGHT", "ORDERING", "RECEIVING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE")},
            "service": served / demand if demand else None, "unmet": demand - served, "breaches": breaches,
            "avg_inventory_units": sum(inventory) / len(inventory), "terminal_on_hand": on_hand, "terminal_in_transit": in_transit,
            "next_arrival_periods_after_window": (next_due - 1) if next_due is not None else None,
            "weeks_to_consume_terminal": ((on_hand + in_transit) / sum(v["mean"] for v in rows[-1]["forecast"].values())) if rows[-1]["forecast"] else None}


def curve(initial: Request, reviews_log: list[dict]) -> list[dict]:
    """Endpoint scores at every W from 1 to the number of reviews replayed."""
    return [endpoint(initial, reviews_log, W) for W in range(1, len(reviews_log) + 1)]
