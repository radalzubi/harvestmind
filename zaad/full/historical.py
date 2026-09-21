"""Rolling historical replay of the ZAAD optimizer on an operator's own history.

The question answered here is different from the policy benchmark's:

    "If ZAAD had been operating at each historical decision date, re-solving with only the
     information available at that moment, what would it have recommended, and how would those
     decisions have performed under what then actually happened?"

Three legs run through ONE loop (`zaad.full.replay.replay`) and ONE settlement (`zaad.full.settlement`):

    actual   the operator's purchase orders exactly as placed (MEASURED decisions)
    rule     the operator's reconstructed purchasing rule, projected from each point-in-time snapshot
    zaad     the production optimizer, `zaad.full.planner.plan`, re-run at every weekly decision date on
             the state its own earlier decisions produced; a review on which the planner abstains keeps
             the operator's rule for that period, exactly as production does

Information boundary. Review 0 is `build_request(as_of=D0)` (history, fits, opening stock and open orders
strictly before D0). Afterwards `replay` reveals the truth only through observation: a week's demand enters
the history after the week settles, a receipt enters the shipment record when it arrives, and the
supplier fit is refitted from arrived receipts only. Nothing here hands the planner a number dated after
its `as_of`; `attest()` checks that on every planning snapshot and the tests perturb the future to prove it.

Counterfactual settlement. The truth `World` is reconstructed from the operator's own records where the
records exist and labelled where they cannot exist (a supplier never saw ZAAD's order):

    MEASURED   the operator's own received order in that week: observed lead and fill
    INFERRED   the observed lead and fill applied to a different quantity, or the nearest received order
               of the same supplier within ±4 weeks
    SIMULATED  a seeded draw from the supplier's empirical fill and lead over the history
    ASSUMED    no observation for the supplier at all: the source's declared / assumed lead and fill

Every decision row carries the label its settlement used; the summary reports the shares. Nothing is
estimated here that changes what the optimizer computes: the planner, its candidates, gates, scenario
counts and materiality rules are called unchanged.
"""
from __future__ import annotations

import copy
import logging
import math
import resource
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np
import pandas as pd

from zaad.full.contracts import Request
from zaad.full.economics import cost_breakdown
from zaad.full.evaluation import endpoint
from zaad.full.model import Solution
from zaad.full.replay import NETWORK_METHODS, choose, replay
from zaad.full.tolerance import is_dust
from zaad.full.workspace import WorkspaceError, build_request
from zaad.full.worlds import World

log = logging.getLogger("zaad.historical")

HISTORICAL_REPLAY_VERSION = "2026.09.3"
NEAREST_WEEKS = 4
DEFAULT_SKUS = 5
DEFAULT_REVIEWS = 26
DEFAULT_BUDGET_S = 1200.0
LEGS = ("actual", "rule", "zaad")


# ── truth reconstruction ──────────────────────────────────────────────────────
def _periods_between(later: pd.Timestamp, origin: pd.Timestamp, period_days: int) -> int:
    return int((later - origin).days // period_days)


def build_truth(conn: Any, initial: Request, *, periods: int, seed: int) -> tuple[World, dict]:
    """The realised environment after review 0, from the operator's records, with a provenance label per
    supply cell. Returns (world, provenance) where provenance carries `supply[(source, τ)]` labels,
    `open_po` labels and the shares."""
    origin = pd.Timestamp(initial.as_of).tz_convert(None) if pd.Timestamp(initial.as_of).tzinfo else pd.Timestamp(initial.as_of)
    origin = origin.normalize()
    pdays = initial.period_days
    end = origin + pd.Timedelta(days=pdays * periods)
    sku_of_service = {s.id: s.sku for s in initial.services}
    sku_of_source = {s.id: s.sku for s in initial.sources}
    supplier_of_source = {s.id: s.supplier for s in initial.sources}
    orders = conn.execute("SELECT sku, order_date, qty_ordered FROM stg_fmcg_orders WHERE order_date >= ? AND order_date < ?",
                          [origin.to_pydatetime(), end.to_pydatetime()]).fetchdf()
    pos = conn.execute("SELECT po_id, po_date, supplier_id, sku, qty_ordered FROM stg_fmcg_purchase_orders").fetchdf()
    receipts = conn.execute("SELECT po_id, receipt_date, qty_received FROM stg_fmcg_receipts").fetchdf()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    pos["po_date"] = pd.to_datetime(pos["po_date"])
    receipts["receipt_date"] = pd.to_datetime(receipts["receipt_date"])
    got = receipts.groupby("po_id").agg(qty_received=("qty_received", "sum"), first=("receipt_date", "min")) if len(receipts) else pd.DataFrame(columns=["qty_received", "first"])
    joined = pos.join(got, on="po_id")
    joined["received"] = joined["qty_received"].fillna(0.)
    joined["arrived"] = joined["first"].notna()
    joined["lead_days"] = (joined["first"] - joined["po_date"]).dt.days
    joined["fill"] = (joined["received"] / joined["qty_ordered"]).clip(0., 1.)
    joined["period"] = ((joined["po_date"] - origin).dt.days // pdays).astype(int)

    # demand: the operator's customer orders per SKU per week (MEASURED)
    demand: dict[str, tuple[float, ...]] = {}
    orders["period"] = ((orders["order_date"] - origin).dt.days // pdays).astype(int)
    weekly = orders.groupby(["sku", "period"])["qty_ordered"].sum() if len(orders) else pd.Series(dtype=float)
    for service_id, sku in sku_of_service.items():
        demand[service_id] = tuple(float(weekly.get((sku, t), 0.0)) if len(weekly) else 0.0 for t in range(periods))

    # supplier observations: received orders of each supplier, by period, over the whole history (settlement truth)
    received = joined[joined["arrived"] & (joined["lead_days"] >= 0)]
    by_supplier: dict[str, pd.DataFrame] = {str(k): g for k, g in received.groupby("supplier_id")}
    in_window = received[(received["period"] >= 0) & (received["period"] < periods)]
    rng = np.random.default_rng(seed)
    arrival: dict[tuple[str, int], int] = {}
    fills: dict[tuple[str, int], float] = {}
    supply_label: dict[str, str] = {}
    supply_actual_qty: dict[str, float] = {}
    for source in initial.sources:
        sku, sid = sku_of_source[source.id], supplier_of_source[source.id]
        own = in_window[in_window["sku"].astype(str) == sku]
        own_by_period = {int(t): g for t, g in own.groupby("period")}
        sup = by_supplier.get(str(sid))
        for t in range(periods):
            key = f"{source.id}|{t}"
            if t in own_by_period:
                g = own_by_period[t]
                w = g["qty_ordered"].astype(float)
                lead_days = float((g["lead_days"].astype(float) * w).sum() / w.sum()) if w.sum() > 0 else float(g["lead_days"].mean())
                fill = float((g["fill"].astype(float) * w).sum() / w.sum()) if w.sum() > 0 else float(g["fill"].mean())
                label = "MEASURED"
                supply_actual_qty[key] = float(w.sum())
            elif sup is not None and len(sup):
                near = sup[(sup["period"] - t).abs() <= NEAREST_WEEKS]
                if len(near):
                    near = near.iloc[(near["period"] - t).abs().argsort()[:3]]
                    lead_days = float(near["lead_days"].mean())
                    fill = float(near["fill"].mean())
                    label = "INFERRED"
                else:
                    lead_days = float(rng.choice(sup["lead_days"].astype(float).to_numpy()))
                    fill = float(rng.choice(sup["fill"].astype(float).to_numpy()))
                    label = "SIMULATED"
            else:
                lead_days = float(source.lead_days)
                fill = float(source.fill_mean)
                label = "ASSUMED"
            lead_periods = max(1, int(math.ceil(max(1.0, lead_days) / pdays)))
            arrival[source.id, t] = t + lead_periods
            fills[source.id, t] = float(min(1.0, max(0.0, fill)))
            supply_label[key] = label

    # open orders at D0: what actually happened to them
    po_due: dict[str, int] = {}
    po_fill: dict[str, float] = {}
    open_labels: dict[str, str] = {}
    after = receipts[receipts["receipt_date"] >= origin] if len(receipts) else receipts
    for po in initial.pipeline:
        rows = after[after["po_id"].astype(str) == str(po.id)] if len(after) else after
        keep = next(o for o in po.options if o.action == "keep")
        if len(rows):
            first = rows["receipt_date"].min()
            due = max(1, _periods_between(first, origin, pdays))
            ratio = float(rows["qty_received"].sum()) / po.remaining if po.remaining > 0 else 0.0
            po_due[po.id], po_fill[po.id], open_labels[po.id] = due, float(min(1.0, max(0.0, ratio))), "MEASURED"
        else:
            po_due[po.id] = max(1, keep.due_in)
            po_fill[po.id] = po.expected_accepted_remaining / po.remaining if po.remaining > 0 else 0.0
            open_labels[po.id] = "ASSUMED"
    counts = {k: sum(1 for v in supply_label.values() if v == k) for k in ("MEASURED", "INFERRED", "SIMULATED", "ASSUMED")}
    total = max(1, len(supply_label))
    provenance = {"supply": supply_label, "supply_actual_qty": supply_actual_qty, "open_po": open_labels,
                  "cell_shares": {k: round(v / total, 4) for k, v in counts.items()}, "cells": len(supply_label),
                  "demand": "MEASURED (customer orders as placed; recorded shortfalls do not reduce demand)",
                  "nearest_weeks": NEAREST_WEEKS, "seed": seed}
    world = World(f"historical:{origin.date()}:{periods}", 1.0, demand, arrival, fills, po_due, po_fill)
    return world, provenance


# ── the actual-orders leg ────────────────────────────────────────────────────
def actual_orders_by_review(conn: Any, initial: Request, reviews: int) -> dict[int, dict[str, float]]:
    """The operator's purchase orders per review period per source, exactly as placed."""
    origin = pd.Timestamp(initial.as_of).tz_convert(None) if pd.Timestamp(initial.as_of).tzinfo else pd.Timestamp(initial.as_of)
    origin = origin.normalize()
    pdays = initial.period_days
    end = origin + pd.Timedelta(days=pdays * reviews)
    pos = conn.execute("SELECT po_date, sku, qty_ordered FROM stg_fmcg_purchase_orders WHERE po_date >= ? AND po_date < ?",
                       [origin.to_pydatetime(), end.to_pydatetime()]).fetchdf()
    source_of_sku = {s.sku: s.id for s in initial.sources}
    out: dict[int, dict[str, float]] = {t: {} for t in range(reviews)}
    if not len(pos):
        return out
    pos["po_date"] = pd.to_datetime(pos["po_date"])
    pos["period"] = ((pos["po_date"] - origin).dt.days // pdays).astype(int)
    for (t, sku), q in pos.groupby(["period", "sku"])["qty_ordered"].sum().items():
        src = source_of_sku.get(str(sku))
        if src is not None and 0 <= int(t) < reviews and q > 0:
            out[int(t)][src] = float(q)
    return out


def _conform(source: Any, q: float, t: int = 0) -> tuple[float, str | None]:
    """The recorded quantity made physically admissible for the settlement: rounded to the declared pack /
    case / pallet / transport multiples and clamped to the source's minimum and capacity. Returns the
    quantity and a note when it had to change; the note is carried on the decision row."""
    from fractions import Fraction
    from math import lcm
    mults = [m for m in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple) if m and m > 0]
    out, note = float(q), None
    if mults:
        fr = [Fraction(m).limit_denominator(1000) for m in mults]
        den = lcm(*[f.denominator for f in fr])
        step = Fraction(lcm(*[int(f * den) for f in fr]), den)
        out = float(round(Fraction(out).limit_denominator(1000) / step) * step)
        if abs(out - q) > 1e-9:
            note = f"rounded from {q:g} to the declared multiple ({float(step):g})"
    cap = min(source.maximum, source.capacity_by_period[min(t, len(source.capacity_by_period) - 1)])
    if out > cap + 1e-9:
        out = float(math.floor(cap / float(step)) * float(step)) if mults else float(cap)
        note = (note + "; " if note else "") + f"capped at the declared capacity {cap:g}"
    if 0 < out < source.minimum - 1e-9:
        out = 0.0
        note = (note + "; " if note else "") + f"below the declared minimum {source.minimum:g}: dropped"
    return out, note


def _conform_shared(req: Request, purchases: dict[tuple[str, int], float]) -> tuple[dict[tuple[str, int], float], list[dict]]:
    """A projected plan made admissible against every shared resource (supplier capacity) the request declares:
    in each period whose lines together exceed a resource's capacity, every line is scaled by the same factor
    and rounded down to its declared multiples (a line that falls below its minimum is dropped). The
    reconstructed rule orders every SKU of a supplier in the same week, which the operator's own staggered
    orders never did; without this the rule's plan is physically unsettleable at wide scopes and the
    planner, handed it as the declared incumbent, abstains. Returns the plan and one note per changed line."""
    from fractions import Fraction
    from math import lcm
    sources = {s.id: s for s in req.sources}
    volume = {s.id: s.volume for s in req.skus}
    out = dict(purchases)
    notes: list[dict] = []
    for res in req.resources:
        for t in range(req.horizon):
            cap = res.capacity_by_period[min(t, len(res.capacity_by_period) - 1)]
            lines = [(sid, q) for (sid, k), q in out.items() if k == t and q > 0 and sid in sources and res.id in sources[sid].resources]
            load = sum(q * volume[sources[sid].sku] for sid, q in lines)
            if load <= cap + 1e-9:
                continue
            factor = cap / load
            for sid, q in lines:
                source = sources[sid]
                mults = [m for m in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple) if m and m > 0]
                scaled = q * factor
                if mults:
                    fr = [Fraction(m).limit_denominator(1000) for m in mults]
                    den = lcm(*[f.denominator for f in fr])
                    step = float(Fraction(lcm(*[int(f * den) for f in fr]), den))
                    scaled = math.floor(scaled / step + 1e-9) * step
                if 0 < scaled < source.minimum - 1e-9:
                    scaled = 0.0
                out[sid, t] = scaled
                notes.append({"review_period": t, "source": sid, "resource": res.id, "projected": q, "settled": scaled,
                              "note": f"scaled by {factor:.3f} to the declared capacity {cap:g} of {res.id} shared by {len(lines)} lines"})
    return out, notes


def _fixed_solution(req: Request, purchases: dict[str, float], note: str) -> Solution:
    """A fixed order set as a settleable plan: the purchases at period 0 and every open order kept
    (the same keep amendments the declared-rule baseline carries)."""
    from zaad.full.policies import _keep_amendments
    return Solution("OPTIMAL", {(src, 0): q for src, q in purchases.items() if q > 0}, {}, _keep_amendments(req), {}, None, [], 0.0, 0, 0, None, None, [note])


class _LegMethods:
    """Replay methods registered for one run and removed afterwards. Each takes the planning request
    `replay` built for the review (its `as_of` is the decision date)."""

    def __init__(self, initial: Request, actual: dict[int, dict[str, float]], on_solve: Callable[[dict], None] | None = None):
        self.initial, self.actual, self.on_solve = initial, actual, on_solve
        self.zaad_log: list[dict] = []
        self.solutions: dict[int, Solution] = {}   # the decision taken at each review, served again after a budget stop
        self.conformance: list[dict] = []   # recorded orders changed to satisfy the declared physical envelope

    def review_of(self, req: Request) -> int:
        return int(round((req.as_of - self.initial.as_of).total_seconds() / (86400 * req.period_days)))

    def actual_orders(self, req: Request) -> Solution:
        t = self.review_of(req)
        sources = {s.id: s for s in req.sources}
        conformed: dict[str, float] = {}
        for src, q in self.actual.get(t, {}).items():
            if src not in sources:
                continue
            out, note = _conform(sources[src], q)
            conformed[src] = out
            if note:
                self.conformance.append({"leg": "actual", "review": t, "source": src, "recorded": q, "settled": out, "note": note})
        return _fixed_solution(req, conformed, "ACTUAL_ORDERS")

    def rule(self, req: Request) -> Solution:
        """The reconstructed rule's own projection, made admissible against the declared shared capacity."""
        from zaad.full.policies import baseline_plan
        solution = baseline_plan(req, req.incumbent_rule or "reorder_point")
        conformed, notes = _conform_shared(req, solution.purchases)
        if notes:
            t = self.review_of(req)
            self.conformance += [{"leg": "rule", "review": t, **n} for n in notes]
            solution.purchases = conformed
        return solution

    def _conformed_incumbent(self, req: Request) -> Request:
        """The declared incumbent the planner is compared against, made admissible against shared capacity;
        the planner's own semantics (declared orders are the incumbent) are untouched."""
        if not req.incumbent_orders:
            return req
        declared = {(o.source, o.period): o.quantity for o in req.incumbent_orders}
        conformed, notes = _conform_shared(req, declared)
        if not notes:
            return req
        t = self.review_of(req)
        self.conformance += [{"leg": "zaad_incumbent", "review": t, **n} for n in notes]
        from zaad.full.contracts import IncumbentOrder
        return req.model_copy(update={"incumbent_orders": tuple(
            IncumbentOrder(known_at=o.known_at, source=o.source, period=o.period, quantity=conformed[o.source, o.period])
            for o in req.incumbent_orders if conformed[o.source, o.period] > 0)})

    def zaad(self, req: Request) -> Solution:
        """The production optimizer; an abstaining or unusable review keeps the operator's rule."""
        started = time.perf_counter()
        req = self._conformed_incumbent(req)
        solution = choose(req, "gated")
        seconds = time.perf_counter() - started
        status = solution.warnings[0] if solution.warnings else solution.status
        policy = solution.warnings[1] if len(solution.warnings) > 1 else None
        fallback = False
        if not solution.usable_plan:
            fallback = True
            solution = self.rule(req)
            solution.warnings = [f"{status}", str(policy), "fallback=operator_rule", *solution.warnings]
        review = self.review_of(req)
        entry = {"review": review, "as_of": req.as_of.isoformat(), "status": status, "selected_policy": policy,
                 "fallback_to_rule": fallback, "solve_seconds": round(seconds, 2),
                 "orchestration": getattr(solution, "orchestration", None), "history_periods": len({r.period for r in req.history})}
        self.zaad_log.append(entry)
        self.solutions[review] = copy.deepcopy(solution)
        if self.on_solve:
            self.on_solve(entry)
        return solution

    def zaad_recorded(self, req: Request) -> Solution:
        """The decision already taken at this review, served again (never re-solved) so the clean-prefix
        re-run after a budget stop costs settlement time only."""
        return copy.deepcopy(self.solutions[self.review_of(req)])


# ── point-in-time attestation ────────────────────────────────────────────────
def attest(requests: list[Request]) -> dict:
    """For every planning snapshot: the demand history ends before the decision date, no receipt is
    observed after it, no open order was placed after it, and every dated row is known at or before it."""
    checks = []
    for req in requests:
        as_of = req.as_of
        history_ok = all(r.period < 0 for r in req.history) and all(r.known_at <= as_of for r in req.history)
        receipts_ok = all((not r.arrived) or r.known_at <= as_of for r in req.shipment_history)
        pipeline_ok = all(p.placed_at <= as_of and p.known_at <= as_of for p in req.pipeline)
        stock_ok = all(s.known_at <= as_of for s in req.stock)
        checks.append({"as_of": as_of.isoformat(), "history_before_decision": history_ok, "no_receipt_after_decision": receipts_ok,
                       "no_order_placed_after_decision": pipeline_ok, "stock_known_at_or_before": stock_ok,
                       "history_periods": len({r.period for r in req.history}), "shipment_observations": len(req.shipment_history)})
    return {"snapshots": len(checks), "all_clean": all(all(v for k, v in c.items() if isinstance(v, bool)) for c in checks), "per_review": checks}


# ── scoring ──────────────────────────────────────────────────────────────────
def _per_review(initial: Request, out: dict) -> list[dict]:
    rows = []
    for r in out.get("reviews", []):
        st = r["settlement"]
        served = sum(x["served"] for x in st["service_by_period"])
        demand = sum(x["demand"] for x in st["service_by_period"])
        comps = cost_breakdown(st["ledger"])
        rows.append({"review": r["review"], "as_of": r["as_of"][:10], "cost": float(st["economic_cost"]),
                     "purchase": float(comps["PURCHASE"]), "carrying": float(comps["CARRYING"]), "shortage": float(comps["SHORTAGE"]),
                     "served": served, "demand": demand, "service": (served / demand) if demand > 0 else None,
                     "end_stock_units": sum(x["quantity"] for x in st["end_stock"]),
                     "purchases": {p["source"]: p["quantity"] for p in r["purchases"]},
                     "service_by_sku": {x["service"]: (x["served"], x["demand"]) for x in st["service_by_period"]},
                     "end_stock_by_sku": _stock_by_sku(st["end_stock"]),
                     "status": (r["warnings"] or [None])[0], "wall_seconds": r.get("wall_seconds")})
    return rows


def _stock_by_sku(end_stock: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for x in end_stock:
        out[x["sku"]] = out.get(x["sku"], 0.0) + float(x["quantity"])
    return out


def _block_bootstrap_ci(x: list[float], confidence: float = 0.8, block: int = 4, n_boot: int = 2000, seed: int = 0) -> tuple[float, float] | None:
    """80% block-bootstrap interval on the mean per-period difference; None below eight periods, where
    the interval would be a restatement of the sample."""
    if len(x) < 8:
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(x, dtype=float)
    n = len(arr)
    n_blocks = int(math.ceil(n / block))
    means = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, n - block + 1), size=n_blocks)
        sample = np.concatenate([arr[s:s + block] for s in starts])[:n]
        means.append(sample.mean())
    lo, hi = np.percentile(means, [(1 - confidence) / 2 * 100, (1 + confidence) / 2 * 100])
    return float(lo), float(hi)


def _summarise_difference(base: list[dict], cand: list[dict], W: int, base_score: dict | None = None, cand_score: dict | None = None) -> dict:
    """Per-period cost difference base − candidate (positive = candidate cheaper) over the first W reviews,
    each period's cost being that period's settlement (its own opening and closing stock valued), plus the
    window totals from the endpoint scores (which value stock once, at the window's ends)."""
    diffs = [b["cost"] - c["cost"] for b, c in zip(base[:W], cand[:W])]
    if not diffs:
        return {"periods": 0}
    ci = _block_bootstrap_ci(diffs)
    total = None
    if base_score and cand_score and base_score.get("realized_cost") is not None and cand_score.get("realized_cost") is not None:
        bt, ct = float(base_score["realized_cost"]), float(cand_score["realized_cost"])
        total = {"base": bt, "candidate": ct, "difference": bt - ct, "relative": ((bt - ct) / abs(bt)) if abs(bt) > 1e-9 else None,
                 "continuation_difference": float(base_score["continuation_cost"]) - float(cand_score["continuation_cost"])}
    return {"periods": len(diffs), "mean": float(statistics.fmean(diffs)), "median": float(statistics.median(diffs)),
            "worst": float(min(diffs)), "best": float(max(diffs)),
            "share_improved": float(sum(1 for d in diffs if d > 1e-9) / len(diffs)),
            "share_worse": float(sum(1 for d in diffs if d < -1e-9) / len(diffs)),
            "sd": float(statistics.pstdev(diffs)) if len(diffs) > 1 else 0.0,
            "ci80_mean": ci, "window": total, "series": [round(d, 2) for d in diffs]}


# ── the runner ───────────────────────────────────────────────────────────────
def select_skus(initial: Request, n: int) -> tuple[list[str], float]:
    """Top-n SKUs by demand value at D0 (mean weekly history × unit cost); returns the ids and the share
    of demand value they cover. A fixed rule, reported, never a choice of dates."""
    value: dict[str, float] = {}
    cost = {s.id: s.asset_value for s in initial.skus}
    sku_of_service = {s.id: s.sku for s in initial.services}
    hist: dict[str, list[float]] = {}
    for r in initial.history:
        hist.setdefault(sku_of_service[r.service], []).append(r.quantity)
    for sku, xs in hist.items():
        value[sku] = (statistics.fmean(xs) if xs else 0.0) * cost.get(sku, 0.0)
    ranked = sorted(value, key=lambda k: (-value[k], k))
    chosen = ranked[:n]
    total = sum(value.values()) or 1.0
    return chosen, sum(value[k] for k in chosen) / total


SCOPE_RULES = ("window_value", "d0_value")
INTERMITTENT_ZERO_SHARE = 0.35     # the diagnostic's own intermittency threshold (reports/diagnostic_v3.py synthesis)


def select_scope(conn: Any, probe: Request, n: int, *, origin: pd.Timestamp, periods: int, rule: str = "window_value") -> dict:
    """Which products the replay studies - a STUDY SELECTION, labelled as such: it may read the whole replay
    window (demand after the first decision date) to decide *which* products are replayed, and that is the
    only place window information is used; every decision request is then built strictly from data before
    its own date (attested per snapshot). Deterministic; ties broken by product id.

    "window_value": rank by demand value over the replay window (units ordered × unit cost), take the top n,
    then make the set stratified: if none of them is an intermittent-demand product (zero demand in at least
    35% of the window's weeks) and one exists, the last slot goes to the highest-value intermittent product.
    A top-by-value-at-D0 rule ("d0_value", the V3 rule) survives as an option; both coverages are reported.
    The rule never looks at outcomes, orders or the optimizer's results, only at demand value and demand
    pattern, so it cannot favour products where any policy did well."""
    if rule not in SCOPE_RULES:
        raise ValueError(f"scope rule must be one of {SCOPE_RULES}")
    cost = {s.id: s.asset_value for s in probe.skus}
    d0_ranked, _ = select_skus(probe, len(probe.skus))
    d0_value: dict[str, float] = {}
    sku_of_service = {s.id: s.sku for s in probe.services}
    hist: dict[str, list[float]] = {}
    for r in probe.history:
        hist.setdefault(sku_of_service[r.service], []).append(r.quantity)
    for sku, xs in hist.items():
        d0_value[sku] = (statistics.fmean(xs) if xs else 0.0) * cost.get(sku, 0.0)
    start, end = origin.to_pydatetime(), (origin + pd.Timedelta(days=7 * periods)).to_pydatetime()
    frame = conn.execute("SELECT sku, order_date, qty_ordered FROM stg_fmcg_orders WHERE order_date >= ? AND order_date < ?", [start, end]).fetchdf()
    window_units: dict[str, float] = {}
    zero_share: dict[str, float] = {}
    if len(frame):
        frame["order_date"] = pd.to_datetime(frame["order_date"])
        frame["week"] = ((frame["order_date"] - origin).dt.days // 7).astype(int)
        for sku, g in frame.groupby("sku"):
            k = str(sku)
            if k not in cost:
                continue
            window_units[k] = float(g["qty_ordered"].sum())
            weekly = g.groupby("week")["qty_ordered"].sum()
            zero_share[k] = 1.0 - float((weekly > 0).sum()) / max(1, periods)
    window_value = {k: window_units.get(k, 0.0) * cost.get(k, 0.0) for k in cost}
    for k in cost:
        zero_share.setdefault(k, 1.0)
    total_window = sum(window_value.values()) or 1.0
    total_d0 = sum(d0_value.values()) or 1.0
    if rule == "d0_value":
        chosen = list(d0_ranked[:n])
        swapped: list[dict] = []
    else:
        ranked = sorted(cost, key=lambda k: (-window_value[k], k))
        chosen = ranked[:n]
        swapped = []
        intermittent = [k for k in ranked if zero_share[k] >= INTERMITTENT_ZERO_SHARE and window_value[k] > 0]
        if chosen and intermittent and not any(zero_share[k] >= INTERMITTENT_ZERO_SHARE for k in chosen) and len(ranked) > n:
            dropped, added = chosen[-1], intermittent[0]
            chosen = chosen[:-1] + [added]
            swapped.append({"dropped": dropped, "added": added, "reason": "stratification: one intermittent-demand product in the study set"})
    chosen = sorted(chosen, key=lambda k: (-window_value[k], k))
    # purchase-order line coverage over the window (how much of the operator's ordering the study set carries)
    po = conn.execute("SELECT sku, COUNT(*) AS n FROM stg_fmcg_purchase_orders WHERE po_date >= ? AND po_date < ? GROUP BY sku", [start, end]).fetchall()
    po_lines = {str(r[0]): int(r[1]) for r in po}
    po_total = sum(po_lines.values()) or 1
    return {"skus": chosen, "rule": rule,
            "information": ("STUDY SELECTION: demand value and demand pattern over the whole replay window "
                            f"({origin.date()} to {(origin + pd.Timedelta(days=7 * periods - 1)).date()}), used only to choose which products are replayed; "
                            "no decision request reads anything after its own date (attested per snapshot)") if rule == "window_value" else
                           ("point-in-time: demand value over the history before the first decision date (V3 rule)"),
            "window": {"start": str(origin.date()), "end": str((origin + pd.Timedelta(days=7 * periods - 1)).date()), "weeks": periods},
            "coverage": {"window_demand_value_share": round(sum(window_value[k] for k in chosen) / total_window, 4),
                         "d0_demand_value_share": round(sum(d0_value.get(k, 0.0) for k in chosen) / total_d0, 4),
                         "purchase_order_line_share": round(sum(po_lines.get(k, 0) for k in chosen) / po_total, 4),
                         "sku_count": len(chosen), "skus_with_window_demand": sum(1 for v in window_value.values() if v > 0), "skus_in_workspace": len(cost)},
            "strata": {"intermittent": sum(1 for k in chosen if zero_share[k] >= INTERMITTENT_ZERO_SHARE), "regular": sum(1 for k in chosen if zero_share[k] < INTERMITTENT_ZERO_SHARE),
                       "threshold": f"zero demand in at least {int(INTERMITTENT_ZERO_SHARE * 100)}% of the window's weeks"},
            "swapped": swapped, "zero_share": {k: round(zero_share[k], 3) for k in chosen}}


def run_historical_replay(conn: Any, operator_id: str, *, skus: int | list[str] = DEFAULT_SKUS, reviews: int = DEFAULT_REVIEWS,
                          horizon: int = 12, budget_s: float = DEFAULT_BUDGET_S, seed: int = 41001,
                          progress: Callable[[str, dict], None] | None = None, end_before: datetime | None = None,
                          scope_rule: str = "window_value", fefo: str = "network") -> dict:
    """Run the three legs and score them on the common completed prefix. Never raises for a replay that
    cannot run: returns status "unavailable" with the reason."""
    started = time.perf_counter()
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # the window: the latest review origin that still leaves `horizon` weeks of truth after the last review
    row = conn.execute("SELECT MIN(order_date), MAX(order_date) FROM stg_fmcg_orders").fetchone()
    if not row or row[0] is None:
        return {"status": "unavailable", "reason": "no customer order history", "version": HISTORICAL_REPLAY_VERSION}
    last_day = pd.Timestamp(row[1])
    if end_before is not None:
        cap = pd.Timestamp(end_before)
        cap = cap.tz_convert(None) if cap.tzinfo is not None else cap
        last_day = min(last_day, cap)
    last_monday = (last_day - pd.Timedelta(days=last_day.weekday())).normalize()
    periods_needed = reviews - 1 + horizon
    origin = last_monday - pd.Timedelta(days=7 * periods_needed)
    first_day = pd.Timestamp(row[0])
    weeks_before = int((origin - first_day).days // 7)
    from zaad.full.workspace import MIN_HISTORY_WEEKS
    if weeks_before < MIN_HISTORY_WEEKS:
        # shorten the window rather than refuse: keep the minimum history before the origin
        origin = first_day + pd.Timedelta(days=7 * MIN_HISTORY_WEEKS)
        origin = origin - pd.Timedelta(days=origin.weekday())
        available = int((last_monday - origin).days // 7)
        reviews = max(0, available - horizon + 1)
        if reviews < 4:
            return {"status": "unavailable", "version": HISTORICAL_REPLAY_VERSION,
                    "reason": f"not enough history for a rolling replay: {int((last_monday - first_day).days // 7)} weeks of orders, "
                              f"{MIN_HISTORY_WEEKS} are needed before the first decision date and {horizon} after the last one"}
    as_of = origin.to_pydatetime().replace(tzinfo=timezone.utc)
    try:
        probe, _ = build_request(conn, operator_id, as_of=as_of, horizon=horizon)
    except WorkspaceError as exc:
        return {"status": "unavailable", "reason": str(exc), "version": HISTORICAL_REPLAY_VERSION}
    periods = reviews - 1 + horizon
    if isinstance(skus, int):
        selection = select_scope(conn, probe, skus, origin=origin, periods=periods, rule=scope_rule)
        chosen, value_share = selection["skus"], selection["coverage"]["d0_demand_value_share"]
    else:
        chosen, value_share = [s for s in skus if any(k.id == s for k in probe.skus)], None
        selection = {"skus": chosen, "rule": "explicit", "information": "an explicit product list supplied by the caller", "coverage": {}, "strata": {}, "swapped": []}
    if not chosen:
        return {"status": "unavailable", "reason": "no SKU with history at the replay origin", "version": HISTORICAL_REPLAY_VERSION}
    try:
        initial, build = build_request(conn, operator_id, as_of=as_of, horizon=horizon, skus=chosen, seed=seed)
    except WorkspaceError as exc:
        return {"status": "unavailable", "reason": str(exc), "version": HISTORICAL_REPLAY_VERSION}
    if fefo not in ("network", "certified", "all"):
        raise ValueError("fefo must be network, certified or all")
    if fefo != "network":
        # the engine choice rides on the request; the replay loop carries request fields forward
        initial = initial.model_copy(update={"fefo_symmetry_scope": fefo})
    import zaad.full.model as _model
    certificate_log: list[dict] = []
    _model.CERTIFICATE_LOG = certificate_log
    truth, truth_prov = build_truth(conn, initial, periods=periods, seed=seed)
    actual = actual_orders_by_review(conn, initial, reviews)
    methods = _LegMethods(initial, actual)
    tag = f"historical_{operator_id}_{int(started * 1000)}"
    NETWORK_METHODS[f"{tag}:actual"] = methods.actual_orders
    NETWORK_METHODS[f"{tag}:rule"] = methods.rule
    NETWORK_METHODS[f"{tag}:zaad"] = methods.zaad
    NETWORK_METHODS[f"{tag}:zaad_recorded"] = methods.zaad_recorded
    legs: dict[str, dict] = {}
    snapshots: dict[str, list[Request]] = {}
    stopped_at: int | None = None
    try:
        for leg in ("actual", "rule"):
            if progress:
                progress("replaying", {"leg": leg, "review": 0, "reviews": reviews})
            method = f"{tag}:actual" if leg == "actual" else f"{tag}:rule"
            keep: list[Request] = []
            if leg == "rule" and not initial.incumbent_rule:
                legs[leg] = {"status": "unavailable", "reason": "no reconstructed rule"}
                continue
            legs[leg] = replay(initial, truth, reviews, method, keep_requests=keep, rolling=True)
            snapshots[leg] = keep
        # the ZAAD leg: chronological, stopped at the budget, the completed prefix scored
        keep_z: list[Request] = []
        deadline = started + budget_s
        done_reviews = {"n": 0}

        def on_solve(entry: dict) -> None:
            done_reviews["n"] = entry["review"] + 1
            if progress:
                progress("replaying", {"leg": "zaad", "review": entry["review"] + 1, "reviews": reviews, "solve_seconds": entry["solve_seconds"]})
            if time.perf_counter() > deadline and entry["review"] + 1 < reviews:
                raise _BudgetExhausted(entry["review"] + 1)
        methods.on_solve = on_solve
        try:
            legs["zaad"] = replay(initial, truth, reviews, f"{tag}:zaad", keep_requests=keep_z, rolling=True)
        except _BudgetExhausted as stop:
            stopped_at = stop.reviews_done
            legs["zaad"] = _partial_from(initial, truth, stopped_at, f"{tag}:zaad_recorded", methods, keep_z)
        snapshots["zaad"] = keep_z
    finally:
        _model.CERTIFICATE_LOG = None
        NETWORK_METHODS.pop(f"{tag}:actual", None)
        NETWORK_METHODS.pop(f"{tag}:rule", None)
        NETWORK_METHODS.pop(f"{tag}:zaad", None)
        NETWORK_METHODS.pop(f"{tag}:zaad_recorded", None)
    W = min(len(leg_out.get("reviews", [])) for leg_out in legs.values() if leg_out.get("reviews") is not None) if legs else 0
    if W == 0:
        return {"status": "unavailable", "version": HISTORICAL_REPLAY_VERSION,
                "reason": "the replay produced no completed decision date: " + "; ".join(f"{k}: {v.get('status')} {v.get('failure') or v.get('reason') or ''}" for k, v in legs.items())}
    per = {leg: _per_review(initial, out) for leg, out in legs.items() if out.get("reviews")}
    scores = {leg: _score(initial, out, W) for leg, out in legs.items() if out.get("reviews")}
    decisions = _decision_rows(initial, per, methods, truth_prov, W)
    changes = _decision_changes(initial, per, methods, W)
    evidence = _evidence_basis(initial, per, truth_prov, W, build)
    regime_labels = [_review_regimes(r) for r in (snapshots.get("zaad") or [])[:W]]
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    elapsed = time.perf_counter() - started
    solves = [e["solve_seconds"] for e in methods.zaad_log]
    result: dict[str, Any] = {
        "version": HISTORICAL_REPLAY_VERSION, "status": "complete" if stopped_at is None else "partial",
        "engine": {"optimizer": "zaad.full.planner.plan (production path, unchanged)", "loop": "zaad.full.replay.replay(rolling=True)",
                   "settlement": "zaad.full.settlement.settle", "request": "zaad.full.workspace.build_request(as_of=decision date)",
                   "formulation": fefo, "formulation_note": ENGINE_NOTES[fefo], "certificates": _certificate_summary(certificate_log)},
        "scope": {"skus": chosen, "sku_count": len(chosen), "skus_in_workspace": len(probe.skus), "demand_value_share": None if value_share is None else round(value_share, 4),
                  "selection": selection, "currency": initial.currency,
                  "origin": str(origin.date()), "horizon": horizon, "period_days": initial.period_days, "reviews_planned": reviews,
                  "incumbent_rule": initial.incumbent_rule, "rule_provenance": (build.get("incumbent_rule") or {}).get("provenance"),
                  "history_weeks_before_origin": weeks_before if weeks_before >= MIN_HISTORY_WEEKS else int((origin - first_day).days // 7)},
        "coverage": {"reviews_completed": W, "reviews_planned": reviews, "stopped_by_budget": stopped_at is not None, "budget_s": budget_s,
                     "dates": [r["as_of"] for r in (per.get("zaad") or per.get("actual") or [])[:W]]},
        "legs": scores, "per_review": {leg: rows[:W] for leg, rows in per.items()},
        "differences": {"zaad_vs_actual": _summarise_difference(per["actual"], per["zaad"], W, scores.get("actual"), scores.get("zaad")) if "actual" in per and "zaad" in per else None,
                        "zaad_vs_rule": _summarise_difference(per["rule"], per["zaad"], W, scores.get("rule"), scores.get("zaad")) if "rule" in per and "zaad" in per else None,
                        "rule_vs_actual": _summarise_difference(per["actual"], per["rule"], W, scores.get("actual"), scores.get("rule")) if "rule" in per and "actual" in per else None},
        "decisions": decisions, "zaad_reviews": methods.zaad_log[:W],
        "actual_conformance": {"changed_orders": len([c for c in methods.conformance if c["review"] < W and c["leg"] == "actual"]),
                               "rows": [c for c in methods.conformance if c["review"] < W and c["leg"] == "actual"][:50],
                               "note": "recorded orders rounded to the declared pack multiple or clamped to the declared capacity / minimum so the settlement's physical checks hold; the recorded quantity is kept on each row"},
        "settlement_provenance": _settlement_shares(decisions, truth_prov),
        "attestation": {leg: attest(reqs[:W]) for leg, reqs in snapshots.items()},
        "regimes": _regime_split(per, methods.zaad_log, W, regime_labels),
        "decision_changes": changes, "evidence_basis": evidence,
        "rule_conformance": {"changed_lines": len([c for c in methods.conformance if c["review"] < W and c["leg"] != "actual"]),
                             "rows": [c for c in methods.conformance if c["review"] < W and c["leg"] != "actual"][:50],
                             "note": "the reconstructed rule's projected orders scaled to the declared shared supplier capacity where the rule would order every product of a supplier in the same week; applied to the rule leg and to the declared incumbent the optimizer is compared against"},
        "build": {"provenance": build.get("provenance"), "fits": build.get("fits"), "warnings": build.get("warnings"), "leakage_guard": build.get("leakage_guard")},
        "performance": {"decision_points": W, "optimizer_solves": len(methods.zaad_log), "skus": len(chosen), "sources": len(initial.sources),
                        "solve_seconds_mean": round(statistics.fmean(solves), 2) if solves else None, "solve_seconds_max": round(max(solves), 2) if solves else None,
                        "total_seconds": round(elapsed, 1), "peak_rss_mb": round(max(rss0, rss1) / (1024 * 1024 if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 1e7 else 1024), 1)},
    }
    try:
        n_loc = conn.execute("SELECT COUNT(DISTINCT COALESCE(location_id, 'MAIN')) FROM stg_fmcg_inventory").fetchone()
        result["scope"]["inventory_locations"] = int(n_loc[0] or 1) if n_loc else 1
    except Exception:  # noqa: BLE001  an older vault without the column
        result["scope"]["inventory_locations"] = 1
    result["confidence"] = replay_confidence(result, build, initial)
    return result


class _BudgetExhausted(Exception):
    def __init__(self, reviews_done: int):
        super().__init__(f"budget exhausted after {reviews_done} reviews")
        self.reviews_done = reviews_done


def _partial_from(initial: Request, truth: World, reviews_done: int, method: str, methods: "_LegMethods", keep: list[Request]) -> dict:
    """Re-run the ZAAD leg for exactly the completed reviews so its settlements are a clean prefix. The
    decisions already taken are served again from the record (`method` is the `:zaad_recorded` method),
    never re-solved: the state evolves identically, so the prefix reproduces at settlement cost only.
    The solve log is trimmed to the prefix."""
    methods.zaad_log = list(methods.zaad_log[:reviews_done])
    keep.clear()
    return replay(initial, truth, reviews_done, method, keep_requests=keep, rolling=True)


def _score(initial: Request, out: dict, W: int) -> dict:
    ep = endpoint(initial, out["reviews"], W)
    rows = out["reviews"][:W]
    units = sum(p["quantity"] for r in rows for p in r["purchases"])
    return {"status": out.get("status"), "reviews": W, "realized_cost": ep["realized"], "continuation_cost": ep["continuation"],
            "components": ep["components"], "service": ep["service"], "unmet_units": ep["unmet"], "breaches": ep["breaches"],
            "avg_inventory_units": ep["avg_inventory_units"], "terminal_on_hand": ep["terminal_on_hand"], "terminal_in_transit": ep["terminal_in_transit"],
            "units_purchased": units, "orders_placed": sum(1 for r in rows for p in r["purchases"] if not is_dust(p["quantity"]))}


def _decision_rows(initial: Request, per: dict[str, list[dict]], methods: "_LegMethods", truth_prov: dict, W: int) -> list[dict]:
    """One row per decision date per SKU: what each leg ordered, the settlement label ZAAD's order used, and
    the per-SKU service and end-stock outcome under each leg."""
    sku_of_source = {s.id: s.sku for s in initial.sources}
    supplier_of_source = {s.id: s.supplier for s in initial.sources}
    service_of_sku = {s.sku: s.id for s in initial.services}
    zlog = {e["review"]: e for e in methods.zaad_log}
    rows = []
    for t in range(W):
        for src, sku in sku_of_source.items():
            key = f"{src}|{t}"
            q = {leg: float(per[leg][t]["purchases"].get(src, 0.0)) for leg in per}
            label = truth_prov["supply"].get(key, "ASSUMED")
            used = label
            if q.get("zaad", 0.0) > 0 and label == "MEASURED" and abs(q["zaad"] - truth_prov["supply_actual_qty"].get(key, 0.0)) > 1e-6:
                used = "INFERRED"
            z = zlog.get(t, {})
            svc = service_of_sku.get(sku)
            outcome = {}
            for leg in per:
                served, dem = per[leg][t]["service_by_sku"].get(svc, (0.0, 0.0))
                outcome[leg] = {"served": served, "demand": dem, "end_stock": per[leg][t]["end_stock_by_sku"].get(sku, 0.0)}
            action = "no order" if q.get("zaad", 0.0) <= 0 else ("order" if q.get("actual", 0.0) <= 0 else ("more" if q["zaad"] > q["actual"] + 1e-6 else ("less" if q["zaad"] < q["actual"] - 1e-6 else "same")))
            timing = _timing_note(per, src, t, W)
            rows.append({"review": t, "date": per[next(iter(per))][t]["as_of"], "sku": sku, "supplier": supplier_of_source.get(src), "location": "main",
                         "actual_qty": q.get("actual"), "rule_qty": q.get("rule"), "zaad_qty": q.get("zaad"),
                         "quantity_difference": (q.get("zaad", 0.0) - q.get("actual", 0.0)) if "actual" in q and "zaad" in q else None,
                         "zaad_action": action, "zaad_status": z.get("status"), "zaad_policy": z.get("selected_policy"), "fallback_to_rule": z.get("fallback_to_rule"),
                         "timing": timing, "settlement": used if q.get("zaad", 0.0) > 0 else None, "settlement_cell": label,
                         "outcome": outcome, "economic_outcome": "portfolio level (the ledger is not attributed per SKU)"})
    return rows


def _timing_note(per: dict, src: str, t: int, W: int) -> str | None:
    if "actual" not in per or "zaad" not in per:
        return None
    zq = float(per["zaad"][t]["purchases"].get(src, 0.0))
    if zq <= 0:
        return None
    if float(per["actual"][t]["purchases"].get(src, 0.0)) > 0:
        return "same week"
    for d in (1, 2):
        for s in (t - d, t + d):
            if 0 <= s < W and float(per["actual"][s]["purchases"].get(src, 0.0)) > 0:
                return f"{d} week{'s' if d > 1 else ''} {'earlier' if s > t else 'later'} than the operator's nearest order"
    return "no operator order within 2 weeks"


def _settlement_shares(decisions: list[dict], truth_prov: dict) -> dict:
    used = [d["settlement"] for d in decisions if d.get("settlement")]
    total = max(1, len(used))
    by = {k: sum(1 for u in used if u == k) for k in ("MEASURED", "INFERRED", "SIMULATED", "ASSUMED")}
    return {"zaad_orders": len(used), "shares_by_zaad_order": {k: round(v / total, 4) for k, v in by.items()},
            "cell_shares": truth_prov.get("cell_shares"), "open_po": truth_prov.get("open_po"), "demand": truth_prov.get("demand"),
            "rules": {"MEASURED": "the operator's own received order that week: observed lead and fill",
                      "INFERRED": "observed lead and fill applied to a different quantity, or the nearest received order of the same supplier within ±4 weeks",
                      "SIMULATED": "a seeded draw from the supplier's empirical fill and lead over the history",
                      "ASSUMED": "no observation for the supplier: the declared or assumed lead and fill"}}


ENGINE_NOTES = {
    "network": "the released formulation, every FEFO indicator kept: the production planner's own search path (ties resolve as production resolves them on this machine)",
    "certified": "symmetry-reduced formulation accepted per solve only under an exact tie certificate, otherwise the released formulation: identical decisions by proof, at the certificate's cost",
    "all": "symmetry-reduced formulation (an exact projection: the same feasible decisions at the same objective) without a certificate: on an objective-flat tie the solver may return another optimal plan - an owner option, not the released default",
}


def _certificate_summary(log: list[dict]) -> dict | None:
    if not log:
        return None
    attempted = [c for c in log if c.get("attempted")]
    return {"solves": len(log), "attempted": len(attempted), "certified": sum(1 for c in attempted if c.get("certified")),
            "fallbacks": sum(1 for c in log if not c.get("certified")),
            "reasons": {r: sum(1 for c in log if c.get("reason") == r) for r in sorted({str(c.get("reason")) for c in log})},
            "certificate_seconds": round(sum(float(c.get("certificate_seconds") or 0.0) for c in attempted), 2),
            "certificate_seconds_max": round(max((float(c.get("certificate_seconds") or 0.0) for c in attempted), default=0.0), 2)}


def _decision_changes(initial: Request, per: dict, methods: "_LegMethods", W: int) -> dict:
    """How often, and by how much, ZAAD's executed decision differed from the reconstructed rule's on the same
    snapshot (§16): per review the planner's outcome; per line the quantity class; timing where a line moves
    by one week; source and open-order changes where the request allows them at all. Materiality is the
    production planner's own `materiality_cost_fraction` applied to the review's rule purchase value; a
    quantity difference below dust is "same"."""
    if "rule" not in per or "zaad" not in per:
        return {"available": False, "reason": "the rule leg or the ZAAD leg did not complete"}
    sources = {s.id: s for s in initial.sources}
    price = {s.id: float(s.unit_price + s.freight_per_unit + s.handling_per_unit) for s in initial.sources}
    pack = {s.id: max(s.multiple, s.case_multiple, s.pallet_multiple, s.transport_multiple, 0.0) or 1.0 for s in initial.sources}
    from zaad.full.tolerance import is_dust as _dust
    zlog = {e["review"]: e for e in methods.zaad_log}
    classes = {"same": 0, "more": 0, "less": 0, "new": 0, "dropped": 0}
    timing = {"advanced_one_week": 0, "deferred_one_week": 0}
    material_lines = 0
    material_reviews = 0
    units_added = units_removed = 0.0
    value_added = value_removed = 0.0
    review_outcomes = {"retained_rule": 0, "own_plan": 0, "abstained_or_fallback": 0}
    per_review: list[dict] = []
    for t in range(W):
        rq, zq = per["rule"][t]["purchases"], per["zaad"][t]["purchases"]
        e = zlog.get(t, {})
        if e.get("fallback_to_rule"):
            review_outcomes["abstained_or_fallback"] += 1
        elif str(e.get("status")) == "RETAIN_INCUMBENT":
            review_outcomes["retained_rule"] += 1
        else:
            review_outcomes["own_plan"] += 1
        rule_value = sum(q * price.get(sid, 0.0) for sid, q in rq.items())
        review_material = False
        line_rows = []
        for sid in sources:
            r, z = float(rq.get(sid, 0.0)), float(zq.get(sid, 0.0))
            d = z - r
            if _dust(d, pack[sid]):
                cls = "same"
            elif r <= 0 < z:
                cls = "new"
            elif z <= 0 < r:
                cls = "dropped"
            else:
                cls = "more" if d > 0 else "less"
            classes[cls] += 1
            if cls == "same":
                continue
            value = d * price.get(sid, 0.0)
            if d > 0:
                units_added += d
                value_added += value
            else:
                units_removed -= d
                value_removed -= value
            material = abs(value) > initial.materiality_cost_fraction * max(rule_value, 1e-9)
            material_lines += int(material)
            review_material = review_material or material
            # timing: a dropped line that ZAAD orders the next week (and the rule does not) is a deferral; a new line the rule orders the next week is an advance
            if cls == "dropped" and t + 1 < W and float(per["zaad"][t + 1]["purchases"].get(sid, 0.0)) > 0 and float(per["rule"][t + 1]["purchases"].get(sid, 0.0)) <= 0:
                timing["deferred_one_week"] += 1
            if cls == "new" and t + 1 < W and float(per["rule"][t + 1]["purchases"].get(sid, 0.0)) > 0 and float(per["zaad"][t + 1]["purchases"].get(sid, 0.0)) <= 0:
                timing["advanced_one_week"] += 1
            line_rows.append({"source": sid, "sku": sources[sid].sku, "rule": r, "zaad": z, "class": cls, "value_difference": round(value, 2), "material": material})
        material_reviews += int(review_material)
        per_review.append({"review": t, "as_of": per["zaad"][t]["as_of"], "status": e.get("status"), "selected_policy": e.get("selected_policy"),
                           "fallback_to_rule": bool(e.get("fallback_to_rule")), "changed_lines": len(line_rows), "material": review_material, "lines": line_rows[:20]})
    multi_source = any(sum(1 for s in initial.sources if s.sku == k.id) > 1 for k in initial.skus)
    non_keep = any(o.action != "keep" for p in initial.pipeline for o in p.options)
    return {"available": True, "reviews": W, "review_outcomes": review_outcomes, "lines": classes,
            "lines_total": sum(classes.values()), "changed_lines": sum(v for k, v in classes.items() if k != "same"),
            "material_lines": material_lines, "material_reviews": material_reviews, "timing": timing,
            "source_changes": ("not applicable: the workspace declares one source per product, so the optimizer had no source to switch" if not multi_source else "not measured"),
            "open_order_changes": ("not applicable: every open order carries keep-only options, so no amendment was available" if not non_keep else "not measured"),
            "magnitude": {"units_added": round(units_added, 1), "units_removed": round(units_removed, 1), "value_added": round(value_added, 2), "value_removed": round(value_removed, 2)},
            "materiality_rule": f"a line is material when its value difference exceeds {initial.materiality_cost_fraction:g} of the rule's purchase value at that review (the planner's own materiality fraction); a quantity difference below dust is the same order",
            "per_review": per_review}


def _evidence_basis(initial: Request, per: dict, truth_prov: dict, W: int, build: dict) -> dict:
    """Settlement basis at overall and metric level (§15): for each leg the units-weighted share of its supply
    that settled on MEASURED / INFERRED / SIMULATED / ASSUMED supplier behaviour; the demand side and the
    opening state carry their own provenance. Cost and service of a leg both rest on the same cells, so the
    metric-level basis is the leg's; nothing inferred is presented as observed."""
    supply, actual_qty = truth_prov.get("supply") or {}, truth_prov.get("supply_actual_qty") or {}
    out: dict = {"by_leg": {}, "demand": "MEASURED: the operator's customer orders, week by week",
                 "opening_state": "MEASURED: stock counts in the upload" if (build.get("provenance") or {}).get("stock.opening") not in ("CONFIGURED_ASSUMPTION", "NOT_AVAILABLE") else "ASSUMED",
                 "rules": {"MEASURED": "the operator's own received order in that week: its observed lead and fill, at the same quantity",
                           "INFERRED": "observed supplier behaviour applied to a different quantity, or the nearest received order of the same supplier within ±4 weeks",
                           "SIMULATED": "a seeded draw from the supplier's empirical fill and lead over the history",
                           "ASSUMED": "no observation for the supplier: the declared or assumed lead and fill"}}
    for leg, rows in per.items():
        units = {"MEASURED": 0.0, "INFERRED": 0.0, "SIMULATED": 0.0, "ASSUMED": 0.0}
        for t in range(min(W, len(rows))):
            for src, q in rows[t]["purchases"].items():
                if q <= 0:
                    continue
                key = f"{src}|{t}"
                label = supply.get(key, "ASSUMED")
                if label == "MEASURED" and abs(q - float(actual_qty.get(key, 0.0))) > 1e-6:
                    label = "INFERRED"
                units[label] += float(q)
        total = sum(units.values())
        out["by_leg"][leg] = {"units": round(total, 1), "shares": {k: (round(v / total, 4) if total > 0 else 0.0) for k, v in units.items()}}
    out["metrics"] = {m: "the leg's supply basis above (cost and service both settle on the same delivered units) with measured demand" for m in ("cost", "service", "inventory")}
    return out


def _review_regimes(req: Request) -> list[str]:
    """Operating-regime labels of one decision snapshot (§17), from the snapshot only (point in time):
    supplier deterioration (a source's recent fill 6 points below its longer record, or recent lead 1.3× it),
    intermittent demand (at least half the products with zero demand in 35%+ of the last 26 weeks),
    constrained inventory (at least half the products opening below one lead time of cover); "stable" when
    none applies. Analysis only: nothing here enters a request."""
    labels: list[str] = []
    by_source: dict[str, list] = {}
    for r in req.shipment_history:
        if getattr(r, "arrived", False):
            by_source.setdefault(r.source, []).append(r)
    deteriorated = 0
    for sid, obs in by_source.items():
        obs = sorted(obs, key=lambda r: r.known_at)
        if len(obs) < 8:
            continue
        recent, older = obs[-4:], obs[:-4]
        fr = [float(r.accepted_ratio) for r in recent if r.accepted_ratio is not None]
        fo = [float(r.accepted_ratio) for r in older if r.accepted_ratio is not None]
        lr = [float(r.elapsed_days) for r in recent]
        lo = [float(r.elapsed_days) for r in older]
        if (fr and fo and statistics.fmean(fr) < statistics.fmean(fo) - 0.06) or (lo and statistics.fmean(lr) > 1.3 * statistics.fmean(lo)):
            deteriorated += 1
    if deteriorated:
        labels.append("supplier_deterioration")
    series: dict[str, list[tuple[int, float]]] = {}
    for h in req.history:
        series.setdefault(h.service, []).append((int(h.period), float(h.quantity)))
    inter = 0
    mean_weekly: dict[str, float] = {}
    for svc, rows in series.items():
        rows = sorted(rows)[-26:]
        qs = [q for _, q in rows]
        if qs and sum(1 for q in qs if q <= 0) / len(qs) >= INTERMITTENT_ZERO_SHARE:
            inter += 1
        mean_weekly[svc] = statistics.fmean(qs) if qs else 0.0
    if series and inter / len(series) >= 0.5:
        labels.append("intermittent_demand")
    sku_of_service = {s.id: s.sku for s in req.services}
    stock: dict[str, float] = {}
    for lot in req.stock:
        stock[lot.sku] = stock.get(lot.sku, 0.0) + lot.usable
    lead_weeks = {s.sku: max(1.0, s.lead_days / max(1, req.period_days)) for s in req.sources}
    thin = 0
    for svc, mu in mean_weekly.items():
        sku = sku_of_service[svc]
        if mu > 0 and stock.get(sku, 0.0) / mu < lead_weeks.get(sku, 1.0):
            thin += 1
    if mean_weekly and thin / len(mean_weekly) >= 0.5:
        labels.append("constrained_inventory")
    return labels or ["stable"]


def _regime_split(per: dict, zlog: list[dict], W: int, labels: list[list[str]] | None = None) -> dict:
    """ZAAD − actual cost difference split by the planner's own review state and by whether the week's
    observed fill was short; reported only where each side has three or more periods."""
    if "actual" not in per or "zaad" not in per:
        return {}
    diffs = [per["actual"][t]["cost"] - per["zaad"][t]["cost"] for t in range(W)]
    states = {e["review"]: ((e.get("orchestration") or {}).get("state") or "unknown") for e in zlog}
    out: dict = {"by_planner_state": {}}
    groups: dict[str, list[float]] = {}
    for t in range(W):
        groups.setdefault(str(states.get(t, "unknown")), []).append(diffs[t])
    for k, xs in groups.items():
        if len(xs) >= 3:
            out["by_planner_state"][k] = {"periods": len(xs), "mean": float(statistics.fmean(xs)), "share_improved": float(sum(1 for x in xs if x > 0) / len(xs))}
    if labels:
        by_label: dict[str, list[float]] = {}
        for t in range(min(W, len(labels))):
            for lab in labels[t]:
                by_label.setdefault(lab, []).append(diffs[t])
        out["by_operating_regime"] = {k: {"periods": len(xs), "mean": float(statistics.fmean(xs)), "share_improved": float(sum(1 for x in xs if x > 0) / len(xs))}
                                      for k, xs in by_label.items() if len(xs) >= 3}
        out["labels_per_review"] = [labels[t] for t in range(min(W, len(labels)))]
        out["definitions"] = {"supplier_deterioration": "a supplier's last four receipts fill six points below its earlier record or arrive 1.3× later",
                              "intermittent_demand": "at least half the replayed products had zero demand in 35% or more of the last 26 weeks",
                              "constrained_inventory": "at least half the replayed products opened the week below one lead time of cover",
                              "stable": "none of the above"}
    return out


def replay_confidence(result: dict, build: dict, initial: Request) -> dict:
    """Deterministic, evidence-based confidence in the replay comparison. Each dimension is scored from the
    inputs that exist; the level is the weakest material dimension."""
    prov = build.get("provenance") or {}
    fits = build.get("fits") or {}
    shares = (result.get("settlement_provenance") or {}).get("shares_by_zaad_order") or {}
    cov = result.get("coverage") or {}
    reasons: list[str] = []
    scores: dict[str, str] = {}
    measured_like = (shares.get("MEASURED", 0) + shares.get("INFERRED", 0))
    if result.get("settlement_provenance", {}).get("zaad_orders", 0) == 0:
        scores["counterfactual_settlement"] = "n/a"
    elif shares.get("ASSUMED", 0) > 0.25 or shares.get("SIMULATED", 0) > 0.5:
        scores["counterfactual_settlement"] = "low"
        reasons.append(f"{shares.get('SIMULATED', 0) * 100:.0f}% of ZAAD's orders settled on simulated supplier behaviour and {shares.get('ASSUMED', 0) * 100:.0f}% on assumed behaviour")
    elif measured_like >= 0.7:
        scores["counterfactual_settlement"] = "high"
    else:
        scores["counterfactual_settlement"] = "moderate"
        reasons.append(f"{measured_like * 100:.0f}% of ZAAD's orders settled on observed supplier behaviour (the rest simulated from the supplier's own record)")
    n_receipts = sum(int(f.get("sample_size", 0) or 0) for f in fits.values())
    scores["supplier_observations"] = "high" if n_receipts >= 30 else "moderate" if n_receipts >= 10 else "low"
    if scores["supplier_observations"] != "high":
        reasons.append(f"{n_receipts} received purchase orders before the first decision date support the supplier fits")
    weeks = (result.get("scope") or {}).get("history_weeks_before_origin") or 0
    scores["demand_history"] = "high" if weeks >= 52 else "moderate" if weeks >= 26 else "low"
    if scores["demand_history"] != "high":
        reasons.append(f"{weeks} weeks of demand history before the first decision date")
    stock_age = next((w for w in (build.get("warnings") or []) if "inventory snapshot" in w), None)
    scores["opening_inventory"] = "low" if stock_age and ("no inventory" in stock_age) else "moderate" if stock_age else "high"
    if stock_age:
        reasons.append(stock_age)
    if result.get("scope", {}).get("inventory_locations", 1) > 1:
        scores["opening_inventory"] = "moderate" if scores["opening_inventory"] == "high" else scores["opening_inventory"]
        reasons.append(f"stock counts exist for {result['scope']['inventory_locations']} locations; the replay, like the production purchase plan, plans the main location's stock")
    econ_assumed = [k for k, v in prov.items() if v in ("CONFIGURED_ASSUMPTION", "NOT_AVAILABLE") and any(x in k for x in ("holding", "cost_of_capital", "terminal", "margin", "price"))]
    scores["economics"] = "high" if not econ_assumed else "moderate"
    if econ_assumed:
        reasons.append("economic inputs assumed: " + ", ".join(k.replace("_", " ") for k in econ_assumed[:4]))
    cap_inferred = [k for k, v in prov.items() if k.endswith(".capacity") and v != "CUSTOMER_PROVIDED"]
    scores["capacity"] = "high" if not cap_inferred else "moderate"
    if cap_inferred:
        reasons.append(f"supplier capacity inferred or unbounded for {len(cap_inferred)} supplier(s)")
    frac = (cov.get("reviews_completed") or 0) / max(1, cov.get("reviews_planned") or 1)
    scores["coverage"] = "high" if frac >= 0.9 else "moderate" if frac >= 0.5 else "low"
    if frac < 0.9:
        reasons.append(f"{cov.get('reviews_completed')} of {cov.get('reviews_planned')} planned decision dates completed within the time budget")
    share = (result.get("scope") or {}).get("demand_value_share")
    if share is not None and share < 0.5:
        reasons.append(f"the replayed SKUs carry {share * 100:.0f}% of demand value")
    order = {"low": 0, "moderate": 1, "high": 2, "n/a": 3}
    material = [v for k, v in scores.items() if v != "n/a"]
    level = min(material, key=lambda v: order[v]) if material else "low"
    return {"level": {"low": "Low", "moderate": "Moderate", "high": "High"}[level], "dimensions": scores, "reasons": reasons,
            "rule": "the level is the weakest of: counterfactual settlement (share of ZAAD orders settled on observed supplier behaviour), supplier observations, demand history, opening inventory, economics provenance, capacity provenance, decision-date coverage"}
