"""FMCG planning API: a shelf-stable distributor's exports in, a purchase
plan out — with the explanation, the money, and the audit record attached.

Upload goes through the shared intake endpoint
(``POST /intake/upload/stg_fmcg_*``), which validates and stores the file
in the operator's vault. This router reads those staging tables, builds
the planning inputs the counterfactual harness uses (so the plan an
operator gets is the one the validation measured), runs the SELECTED
mode by default, and returns whole-lot orders in eaches.
"""
from __future__ import annotations

import statistics as st
from datetime import date

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_conn, rate_limiter, require_operator
from backtesting.counterfactual import (
    FoldInputs, policy_deterministic_sp, policy_order_up_to, policy_selected,
    policy_stochastic_sp,
)
from domain.economics import CostConfig
from domain.model import fmcg_policy
from domain.money import money_breakdown
from domain.uom import PackSpec, Unit
from optimization.audit_trail import record_run
from optimization.explain import explain_schedule

router = APIRouter(prefix="/fmcg", tags=["fmcg"])

MIN_HISTORY_WEEKS = 16


def _df(conn, sql: str) -> pd.DataFrame:
    return conn.execute(sql).df()


def _num(v, default):
    """CSV-sourced numbers arrive as NaN when blank; NaN is truthy."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return default if f != f else f


def _pack_spec(row) -> PackSpec:
    raw_mult = row.get("order_multiple")
    mult = str(raw_mult if isinstance(raw_mult, str) and raw_mult else "case").lower()
    unit = {"each": Unit.EACH, "case": Unit.CASE, "layer": Unit.LAYER, "pallet": Unit.PALLET}.get(mult, Unit.CASE)
    upc = int(_num(row.get("units_per_case"), 1) or 1)
    cpl_f = _num(row.get("cases_per_layer"), None)
    lpp_f = _num(row.get("layers_per_pallet"), None)
    cpl = int(cpl_f) if cpl_f else None
    lpp = int(lpp_f) if lpp_f else None
    if unit in (Unit.LAYER, Unit.PALLET) and (cpl is None or (unit is Unit.PALLET and lpp is None)):
        unit = Unit.CASE
    return PackSpec(units_per_case=max(upc, 1), cases_per_layer=cpl, layers_per_pallet=lpp,
                    order_multiple=unit, moq_units=float(_num(row.get("moq_units"), 0.0) or 0.0))


def build_inputs(conn, *, horizon: int, train_weeks: int, service_level: float,
                 holding_rate_per_week: float, currency: str, as_of: date | None = None) -> FoldInputs:
    skus = _df(conn, "SELECT * FROM stg_fmcg_skus")
    orders = _df(conn, "SELECT sku, order_date, qty_ordered FROM stg_fmcg_orders")
    pos = _df(conn, "SELECT po_id, po_date, supplier_id, sku, qty_ordered FROM stg_fmcg_purchase_orders")
    rec = _df(conn, "SELECT po_id, receipt_date, qty_received FROM stg_fmcg_receipts")
    inv = _df(conn, "SELECT sku, snapshot_date, on_hand, in_transit FROM stg_fmcg_inventory")
    promo = _df(conn, "SELECT sku, week_start, uplift FROM stg_fmcg_promotions")
    if skus.empty or orders.empty:
        raise HTTPException(422, "Upload stg_fmcg_skus and stg_fmcg_orders before planning.")
    skus = skus.drop_duplicates("sku", keep="last")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    origin = pd.Timestamp(as_of) if as_of else orders["order_date"].max() + pd.Timedelta(days=1)
    origin = origin.normalize() - pd.Timedelta(days=origin.weekday())      # Monday
    hist = orders[orders["order_date"] < origin]
    if hist["order_date"].nunique() < MIN_HISTORY_WEEKS * 3:
        raise HTTPException(422, f"Need at least {MIN_HISTORY_WEEKS} weeks of order history before the "
                                 f"plan date; found {hist['order_date'].nunique()} distinct order days.")
    hist = hist.assign(week=(hist["order_date"] - origin).dt.days // 7)
    wk = hist.groupby(["sku", "week"])["qty_ordered"].sum()
    products = [s for s in skus["sku"] if wk.xs(s, level="sku").sum() > 0] if len(wk) else []
    if not products:
        raise HTTPException(422, "No SKU in the master has order history.")
    sup_of = {r.sku: (r.supplier_id if isinstance(r.supplier_id, str) and r.supplier_id else "UNKNOWN")
              for r in skus.itertuples()}
    cost = {r.sku: float(r.unit_cost) for r in skus.itertuples()}
    price = {r.sku: (_num(r.unit_price, None) or cost[r.sku] * 1.2) for r in skus.itertuples()}
    margin = {j: max(price[j] - cost[j], 0.01 * cost[j]) for j in products}
    train_dem = {j: [float(wk.get((j, w), 0.0)) for w in range(-train_weeks, 0)] for j in products}

    # supplier fill and lead from PO vs receipts
    lead_of, train_fill = {}, {}
    if len(pos) and len(rec):
        pos["po_date"] = pd.to_datetime(pos["po_date"])
        rec["receipt_date"] = pd.to_datetime(rec["receipt_date"])
        got = rec.groupby("po_id").agg(qty_received=("qty_received", "sum"), first=("receipt_date", "min"))
        joined = pos.join(got, on="po_id")
        joined["fill"] = (joined["qty_received"].fillna(0) / joined["qty_ordered"]).clip(0, 1)
        joined["lead_w"] = (joined["first"] - joined["po_date"]).dt.days / 7.0
        past = joined[joined["po_date"] < origin]
        for s_, g in past.groupby("supplier_id"):
            train_fill[str(s_)] = [float(x) for x in g["fill"].dropna()] or [0.95]
            lead_of[str(s_)] = max(1, int(round(g["lead_w"].dropna().mean()))) if g["lead_w"].notna().any() else 2
    for s_ in set(sup_of.values()):
        train_fill.setdefault(s_, [0.95])
        lead_of.setdefault(s_, 2)

    # opening stock and pipeline from the latest snapshot
    opening = {j: 0.0 for j in products}
    pipeline: dict = {}
    if len(inv):
        inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
        latest = inv[inv["snapshot_date"] <= origin].sort_values("snapshot_date").groupby("sku").tail(1)
        for r in latest.itertuples():
            if r.sku in opening:
                opening[r.sku] = float(r.on_hand)
                if r.in_transit == r.in_transit and r.in_transit:
                    pipeline[(r.sku, min(lead_of[sup_of[r.sku]], horizon - 1))] = float(r.in_transit)
    promo_mult: dict = {}
    if len(promo):
        promo["week_start"] = pd.to_datetime(promo["week_start"])
        for r in promo.itertuples():
            t = int((r.week_start - origin).days // 7)
            if 0 <= t < horizon and r.sku in sup_of:
                promo_mult[(r.sku, t)] = float(r.uplift)
    mean_dem = {j: st.mean(train_dem[j]) for j in products}
    cap = {j: max(mean_dem[j] * 3.0, 1.0) for j in products}
    cc = CostConfig(currency=currency, holding_rate_per_period=holding_rate_per_week,
                    shortage_cost_per_unit={j: margin[j] for j in products},
                    waste_cost_per_unit={j: cost[j] for j in products},
                    emergency_cost_multiplier=1.0, emergency_capacity_factor=0.0)
    policy = fmcg_policy({r.sku: _pack_spec(r._asdict()) for r in skus.itertuples()},
                         cost_config=cc, service_level=service_level)
    policy.validate_products(products)
    return FoldInputs(origin=int(origin.timestamp() // 604800), horizon=horizon, products=products,
                      supplier_of={j: sup_of[j] for j in products}, lead_of=lead_of,
                      train_demand=train_dem, train_fill=train_fill,
                      unit_cost={j: cost[j] for j in products}, margin=margin, capacity=cap,
                      opening=opening, pipeline=pipeline, policy=policy, promo_multiplier=promo_mult)


@router.post("/plan", dependencies=[Depends(rate_limiter)])
def plan(
    mode: str = Query("selected", pattern="^(selected|stochastic|deterministic|order_up_to)$"),
    horizon_weeks: int = Query(12, ge=4, le=26),
    train_weeks: int = Query(52, ge=MIN_HISTORY_WEEKS, le=156),
    service_level: float = Query(0.97, gt=0.5, le=1.0),
    holding_rate_per_week: float = Query(0.02 / 4.33, ge=0.0, le=0.1),
    warehouse_cap_weeks: float | None = Query(None, ge=0.5, le=52),
    scenarios: int = Query(30, ge=10, le=200),
    currency: str = Query("USD", pattern="^[A-Z]{3}$"),
    seed: int = Query(0, ge=0),
    conn=Depends(get_conn),
    authed: str | None = Depends(require_operator),
):
    """Purchase plan for the next ``horizon_weeks`` from the staged FMCG history."""
    fi = build_inputs(conn, horizon=horizon_weeks, train_weeks=train_weeks, service_level=service_level,
                      holding_rate_per_week=holding_rate_per_week, currency=currency)
    cap_total = (sum(st.mean(fi.train_demand[j]) for j in fi.products) * warehouse_cap_weeks
                 if warehouse_cap_weeks else None)
    rng = np.random.default_rng(seed)
    if mode == "selected":
        sched, meta = policy_selected(fi, cap_total, rng, scenarios)
    elif mode == "stochastic":
        sched, meta = policy_stochastic_sp(fi, cap_total, rng, scenarios)
    elif mode == "deterministic":
        sched, meta = policy_deterministic_sp(fi, cap_total, rng)
    else:
        sched, meta = policy_order_up_to(fi), {"status": "heuristic"}
    if sched is None:
        raise HTTPException(409, {"message": "The optimizer could not produce a usable plan.",
                                  "solver_status": meta.get("status"), "warnings": meta.get("warnings", [])})
    fills = {s_: st.mean(v) for s_, v in fi.train_fill.items()}
    ex = explain_schedule(sched, demand_history=fi.train_demand, on_hand=fi.opening, inbound=fi.pipeline,
                          expected_fill=fills, lead_of=fi.lead_of, supplier_of=fi.supplier_of,
                          service_target=service_level, pack_specs=fi.policy.pack_specs,
                          solver_status=meta.get("status", "heuristic"), gap=meta.get("gap"))
    orders = []
    for e in ex:
        spec = fi.policy.pack_spec_for(e.product_id)
        orders.append({
            "sku": e.product_id, "supplier_id": e.supplier_id, "week_offset": e.period,
            "order_units": e.order_units, "lots": e.lots, "lot_unit": spec.order_multiple.value,
            "units_per_lot": spec.lot_units, "quantity": e.order_units, "unit": "each",
            "purchase_value": money_breakdown({"purchase": e.order_units * fi.unit_cost[e.product_id]}, currency)["total"],
            "explanation": e.reasons,
        })
    expected_cost = {"purchase_value": sum(o["order_units"] * fi.unit_cost[o["sku"]] for o in orders)}
    audit = record_run(domain="fmcg", config={"mode": mode, "horizon_weeks": horizon_weeks, "train_weeks": train_weeks,
                                              "service_level": service_level, "holding_rate_per_week": holding_rate_per_week,
                                              "scenarios": scenarios, "currency": currency},
                       inputs={"train_demand": fi.train_demand, "train_fill": fi.train_fill, "opening": fi.opening},
                       result={**meta, "usable": True, "run_id": None}, operator_id=authed, seed=seed,
                       scenario_config={"n_scen": scenarios, "seasonal": True, "promotions": len(fi.promo_multiplier)})
    return {
        "run_id": audit.run_id, "mode_requested": mode, "mode_run": meta.get("selected", mode),
        "selection_backtest_costs": ({k: money_breakdown({"cost": v}, currency)["total"]
                                      for k, v in meta.get("selection_costs", {}).items() if v != float("inf")}),
        "solver_status": meta.get("status", "heuristic"), "warnings": meta.get("warnings", []),
        "horizon_weeks": horizon_weeks, "unit": "each", "currency": currency,
        "products_planned": len(fi.products), "promotions_applied": len(fi.promo_multiplier),
        "orders": orders,
        "purchase_value": money_breakdown(expected_cost, currency)["total"],
        "domain_policy": fi.policy.describe(),
        "classification": "operator data as uploaded; plan is a recommendation, not a realised saving",
    }


@router.get("/status")
def status(conn=Depends(get_conn), authed: str | None = Depends(require_operator)):
    out = {}
    for t in ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders",
              "stg_fmcg_receipts", "stg_fmcg_inventory", "stg_fmcg_promotions"):
        try:
            out[t] = int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])  # nosec B608 - constant
        except Exception:  # noqa: BLE001
            out[t] = 0
    return {"tables": out, "ready_to_plan": out["stg_fmcg_skus"] > 0 and out["stg_fmcg_orders"] > 0,
            "minimum_history_weeks": MIN_HISTORY_WEEKS, "unit": "each"}
