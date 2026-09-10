"""Common ex-ante valuation of a fixed candidate plan (P1 candidate-comparability pass).

Read-only. Takes an already-generated plan (its purchase, transfer and amendment controls) and
values it under one economic lens shared by every candidate: the fitted predictive demand
distribution of every service (the same zero probability, bootstrap atoms, calibration widening,
outlier cap and event multipliers `worlds.draw` samples from), the mean supply path of the review
(declared lead and fill), the declared shortage, SLA, carrying, purchase, freight, receiving,
financing and terminal economics, over the plan's own horizon.

Method. The deterministic-path settlement of the plan supplies every component that does not
depend on demand realisations (purchases, freight, order and receiving fees, financing on the
mean cash path, in-transit terminal credit). The demand-dependent components (carrying, shortage
and the terminal credit on stock still on hand) are replaced by their exact expectations under
the fitted mixture, obtained by propagating the on-hand inventory distribution period by period
on a unit grid: I_t = max(0, I_{t-1} + arrivals_t - D_t), lost sales, one SKU per location, with
the demand of every service at the location convolved atom by atom. The grid resolution is the
only approximation and its error is bounded by one unit of stock per period.

Nothing here alters quantities, timings, feasibility, the solver, the settlement or the ledger.
It is the number the selector may compare candidates on; it is never a realised cost."""
from __future__ import annotations

from typing import Any

import numpy as np

from zaad.full.contracts import Request
from zaad.full.model import Solution
from zaad.full.settlement import settle
from zaad.full.shortage import demand_atoms
from zaad.full.worlds import draw


def _period_atoms(req: Request, fits: dict, service, t: int) -> tuple[np.ndarray, float]:
    multiplier = 1.
    for event in req.events:
        if event.service == service.id and event.start <= t <= event.end:
            multiplier *= event.multiplier
    return demand_atoms(fits[service.id], multiplier)


def _convolve_services(dists: list[tuple[np.ndarray, float]]) -> tuple[np.ndarray, np.ndarray]:
    """Demand of every service at a location in one period: atoms and probabilities of the sum."""
    values, probs = np.zeros(1), np.ones(1)
    for atoms, zero in dists:
        if not len(atoms):
            continue
        a = np.concatenate([[0.], atoms])
        p = np.concatenate([[zero], np.full(len(atoms), (1. - zero) / len(atoms))])
        values = (values[:, None] + a[None, :]).reshape(-1)
        probs = (probs[:, None] * p[None, :]).reshape(-1)
        if len(values) > 4096:                      # merge equal values to keep the support small
            order = np.argsort(values)
            values, probs = values[order], probs[order]
            keep = np.concatenate([[True], np.diff(values) > 1e-9])
            idx = np.cumsum(keep) - 1
            merged = np.zeros(idx[-1] + 1)
            np.add.at(merged, idx, probs)
            values, probs = values[keep], merged
    return values, probs


def expected_inventory_path(opening: float, arrivals: np.ndarray, demand: list[tuple[np.ndarray, np.ndarray]],
                            grid: float = 1.) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Propagate the on-hand distribution. Returns (E[shortage_t], E[end inventory_t], P(shortage_t > 0))."""
    H = len(arrivals)
    cap = int(np.ceil((opening + arrivals.sum()) / grid)) + 1
    dist = np.zeros(cap)
    dist[min(cap - 1, int(round(opening / grid)))] = 1.
    levels = np.arange(cap) * grid
    e_short, e_inv, p_short = np.zeros(H), np.zeros(H), np.zeros(H)
    for t in range(H):
        avail = levels + arrivals[t]
        nxt = np.zeros(cap)
        values, probs = demand[t]
        for d, p in zip(values, probs):
            if p <= 0:
                continue
            short = np.maximum(d - avail, 0.)
            e_short[t] += p * float(np.dot(dist, short))
            p_short[t] += p * float(np.dot(dist, (short > 1e-9).astype(float)))
            end = np.maximum(avail - d, 0.)
            idx = np.minimum(cap - 1, np.rint(end / grid).astype(int))
            np.add.at(nxt, idx, p * dist)
        dist = nxt
        e_inv[t] = float(np.dot(dist, levels))
    return e_short, e_inv, p_short


def common_candidate_value(req: Request, solution: Solution, fits: dict, grid: float = 1.) -> dict[str, Any]:
    """Value a fixed plan under the common lens. Returns the components, the total and the
    mean-path settlement it was built from. Raises PhysicalViolation like settlement does when
    the plan is not executable on the mean path."""
    world = draw(req, req.seed, 1, deterministic=True)[0]
    mean = settle(req, solution, world)
    skus = {k.id: k for k in req.skus}
    locs = {loc.id: loc for loc in req.locations}
    sources = {s.id: s for s in req.sources}
    H = req.horizon
    # arrivals per SKU/location from the fixed controls on the mean supply path
    arrivals: dict[tuple[str, str], np.ndarray] = {}
    def add(key, t, q):
        if 0 <= t < H:
            arrivals.setdefault(key, np.zeros(H))[t] += q
    for (sid, t), q in solution.purchases.items():
        s = sources[sid]
        add((s.sku, s.destination), world.arrival[sid, t], q * world.fills[sid, t])
    for po in req.pipeline:
        keep = next(o.id for o in po.options if o.action == "keep")
        q = solution.amendments.get((po.id, keep), po.remaining)
        s = sources[po.source]
        add((s.sku, s.destination), world.po_due[po.id], q * world.po_fill[po.id])
    for row in req.inbound_transfers:
        add((row.sku, row.destination), row.due_in, row.accepted_quantity)
    opening = {(k.id, loc.id): sum(x.usable for x in req.stock if x.sku == k.id and x.location == loc.id) for k in req.skus for loc in req.locations}
    exp_short_cost = exp_holding = exp_end_value = 0.
    exp_short_units = 0.
    detail = {}
    for (sku, loc), services in _services_by_pair(req).items():
        demand = []
        for t in range(H):
            demand.append(_convolve_services([_period_atoms(req, fits, s, t) for s in services]))
        arr = arrivals.get((sku, loc), np.zeros(H))
        e_short, e_inv, p_short = expected_inventory_path(opening[sku, loc], arr, demand, grid)
        # shortage is charged at each service's declared penalty; with several services at one
        # location the units are split by mean demand
        weights = np.array([fits[s.id]["mean"] for s in services])
        weights = weights / max(weights.sum(), 1e-12)
        penalty = float(sum(w * (s.selling_price + s.sla_per_unmet) for w, s in zip(weights, services)))
        exp_short_units += float(e_short.sum())
        exp_short_cost += penalty * float(e_short.sum())
        exp_holding += float(e_inv.sum()) * skus[sku].asset_value * locs[loc].holding_per_value_period
        exp_end_value += float(e_inv[-1]) * skus[sku].terminal_value
        detail[f"{sku}@{loc}"] = {"expected_shortage_by_period": e_short.tolist(), "expected_end_inventory_by_period": e_inv.tolist(),
                                  "shortage_probability_by_period": p_short.tolist(), "arrivals": arr.tolist(), "opening": opening[sku, loc]}
    ledger = mean["ledger"]
    mean_holding = float(sum(x["inventory_value"] for x in mean["trace"]) * 0.)   # placeholder, recomputed below
    mean_holding = ledger.get("holding", 0.)
    mean_shortage = ledger.get("sla", 0.) + ledger.get("lost_sales_opportunity", 0.)
    on_hand_end_value = sum(x["quantity"] * skus[x["sku"]].terminal_value for x in mean["end_stock"])
    total = mean["economic_cost"] - mean_holding - mean_shortage + on_hand_end_value + exp_holding + exp_short_cost - exp_end_value
    return {"total": total, "mean_path_total": mean["economic_cost"],
            "components": {"purchase": ledger.get("procurement", 0.), "freight": ledger.get("freight", 0.), "ordering": ledger.get("order_fees", 0.) + ledger.get("ordering", 0.),
                           "receiving": ledger.get("handling", 0.) + ledger.get("receiving", 0.), "financing": ledger.get("financing", 0.) + ledger.get("working_capital", 0.),
                           "expected_carrying": exp_holding, "expected_shortage_cost": exp_short_cost, "expected_shortage_units": exp_short_units,
                           "terminal_on_hand_credit": -exp_end_value, "terminal_in_transit_credit": ledger.get("closing_assets", 0.) + on_hand_end_value,
                           "opening_assets": ledger.get("opening_assets", 0.), "other": ledger.get("disposal", 0.) + ledger.get("substitution", 0.) + ledger.get("transfer", 0.)},
            "mean_path": {"holding": mean_holding, "shortage": mean_shortage, "on_hand_end_value": on_hand_end_value},
            "detail": detail, "grid": grid}


def _services_by_pair(req: Request) -> dict[tuple[str, str], list]:
    out: dict[tuple[str, str], list] = {}
    for s in req.services:
        out.setdefault((s.sku, s.location), []).append(s)
    return out
