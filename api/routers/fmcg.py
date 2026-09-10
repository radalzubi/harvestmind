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

from typing import Any

import statistics as st
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_conn, legacy_planner_gate, rate_limiter, require_operator
from backtesting.counterfactual import (
    EXTRA_CANDIDATES, FoldInputs, _optimizer_kwargs, _scenarios, _supply_df,
    policy_deterministic_sp, policy_order_up_to, policy_stochastic_sp,
)
from backtesting.incumbent import configured_incumbent, infer_incumbent
from backtesting.regime import diagnose, summarize as regime_summary
from adaptive.plain_language import explain_state
from backtesting.safe_selector import INCUMBENT, SafeSelectionConfig, run_candidate, safe_select
from adaptive.controller import explain_posture
from adaptive.engine import estimate, in_recovery_by_route, p_disruptive_by_route
from adaptive.indicators import load_all_indicators
from adaptive.signals import SignalStore, load_portwatch_signals
from domain.carrying_cost import CarryingCostComponents, sensitivity_grid
from domain.economics import Provenance, ServiceTarget
from ingestion.pilot_readiness import assess as assess_readiness
from optimization.safe_stochastic import regret_summary
from optimization.vss_evpi import value_of_information
from dataclasses import replace as _replace

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


def _economics(conn) -> tuple[dict, dict]:
    """Operator-supplied economic parameters with provenance."""
    try:
        df = _df(conn, "SELECT key, value, provenance FROM stg_fmcg_economics")
    except Exception:  # noqa: BLE001
        return {}, {}
    vals: dict[str, object] = {}
    prov: dict[str, str] = {}
    for r in df.itertuples():
        try:
            vals[str(r.key)] = float(r.value)
        except (TypeError, ValueError):
            vals[str(r.key)] = str(r.value)
        prov[str(r.key)] = str(r.provenance or Provenance.OPERATOR.value)
    return vals, prov


def build_inputs(conn, *, horizon: int, train_weeks: int, service_level: float,
                 holding_rate_per_week: float | None, currency: str, as_of: date | None = None,
                 incumbent_cover_weeks: float | None = None) -> tuple[FoldInputs, dict]:
    """Planning inputs plus a PROVENANCE report. Nothing commercially
    decisive is invented: a missing margin is UNKNOWN (and anchors the
    SKU to the incumbent), a missing capacity is INFERRED from the PO
    history and labelled, a missing carrying rate falls back to the public
    benchmark and says so."""
    skus = _df(conn, "SELECT * FROM stg_fmcg_skus")
    orders = _df(conn, "SELECT sku, order_date, qty_ordered FROM stg_fmcg_orders")
    pos = _df(conn, "SELECT po_id, po_date, supplier_id, sku, qty_ordered FROM stg_fmcg_purchase_orders")
    rec = _df(conn, "SELECT po_id, receipt_date, qty_received FROM stg_fmcg_receipts")
    inv = _df(conn, "SELECT sku, snapshot_date, on_hand, in_transit FROM stg_fmcg_inventory")
    promo = _df(conn, "SELECT sku, week_start, uplift FROM stg_fmcg_promotions")
    try:
        sup_master = _df(conn, "SELECT supplier_id, route, manufacturer, capacity_per_week, origin_iso3 FROM stg_fmcg_suppliers")
    except Exception:  # noqa: BLE001
        sup_master = pd.DataFrame()
    econ, econ_prov = _economics(conn)
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
    products = [s for s in skus["sku"] if s in wk.index.get_level_values(0) and wk.xs(s, level="sku").sum() > 0]
    if not products:
        raise HTTPException(422, "No SKU in the master has order history.")
    provenance: dict = {}
    warnings: list = []
    sup_of = {r.sku: (r.supplier_id if isinstance(r.supplier_id, str) and r.supplier_id else "UNKNOWN")
              for r in skus.itertuples()}
    cost = {r.sku: float(r.unit_cost) for r in skus.itertuples()}
    provenance["unit_cost"] = Provenance.OPERATOR.value

    # ── margin: OPERATOR contribution margin, else price-derived, else UNKNOWN ──
    margin, unknown_margin = {}, []
    for r in skus.itertuples():
        cm = _num(getattr(r, "contribution_margin", None), None)
        pr = _num(r.unit_price, None)
        if cm is not None and cm > 0:
            margin[r.sku] = float(cm)
        elif pr is not None and pr > cost[r.sku]:
            margin[r.sku] = float(pr - cost[r.sku])
        else:
            unknown_margin.append(r.sku)
            margin[r.sku] = 0.01 * cost[r.sku]     # a near-zero placeholder the anchoring will not exploit
    if unknown_margin:
        provenance["shortage_cost_per_unit"] = Provenance.UNKNOWN.value
        warnings.append(f"{len(unknown_margin)} SKU(s) have no contribution margin or price; their shortage "
                        f"cost is UNKNOWN, so they are anchored to the incumbent (e.g. {unknown_margin[:3]})")
    else:
        provenance["shortage_cost_per_unit"] = Provenance.OPERATOR.value
    margin = {j: margin[j] for j in products}
    train_dem = {j: [float(wk.get((j, w), 0.0)) for w in range(-train_weeks, 0)] for j in products}

    # ── supplier fill, lead and the timestamped event log ──
    lead_of: dict[str, int] = {}
    train_fill: dict[str, list] = {}
    supply_events: dict[str, dict] = {}
    po_hist: list[dict] = []
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
            for r in g.itertuples():
                rel = int((r.po_date - origin).days // 7)
                lead_w = int(round(r.lead_w)) if r.lead_w == r.lead_w else lead_of[str(s_)]
                if rel < 0:
                    supply_events.setdefault(str(s_), {})[rel] = (float(r.fill), max(lead_w, 0))
        for r in past.itertuples():
            po_hist.append({"sku": r.sku, "period": int((r.po_date - origin).days // 7),
                            "qty": float(r.qty_ordered), "inventory_position_before": None})
        provenance["supplier_fill"] = Provenance.MEASURED.value
        provenance["lead_time"] = Provenance.MEASURED.value
    else:
        provenance["supplier_fill"] = Provenance.ASSUMED.value
        provenance["lead_time"] = Provenance.ASSUMED.value
        warnings.append("no PO/receipt history: supplier fill 0.95 and lead 2 weeks are ASSUMED")
    for s_ in set(sup_of.values()):
        train_fill.setdefault(s_, [0.95])
        lead_of.setdefault(s_, 2)

    # ── capacity: OPERATOR per SKU, else supplier master, else INFERRED from PO peaks ──
    cap, cap_src = {}, set()
    sup_cap = {str(r.supplier_id): _num(r.capacity_per_week, None) for r in sup_master.itertuples()} if len(sup_master) else {}
    po_peak = {}
    if po_hist:
        by = pd.DataFrame(po_hist).groupby(["sku", "period"])["qty"].sum().groupby("sku").max()
        po_peak = by.to_dict()
    for r in skus.itertuples():
        j = r.sku
        if j not in products:
            continue
        c_op = _num(getattr(r, "supplier_capacity_per_week", None), None)
        if c_op:
            cap[j] = float(c_op)
            cap_src.add(Provenance.OPERATOR.value)
        elif sup_cap.get(sup_of[j]):
            n_sk = sum(1 for x in sup_of.values() if x == sup_of[j])
            cap[j] = float(sup_cap[sup_of[j]]) / max(n_sk, 1)
            cap_src.add(Provenance.OPERATOR.value)
        elif j in po_peak and po_peak[j] > 0:
            cap[j] = float(po_peak[j]) * 1.25
            cap_src.add(Provenance.MEASURED.value)
        else:
            cap[j] = max(st.mean(train_dem[j]) * 2.0, 1.0)
            cap_src.add(Provenance.ASSUMED.value)
    provenance["supplier_capacity"] = (Provenance.OPERATOR.value if cap_src == {Provenance.OPERATOR.value}
                                       else Provenance.MEASURED.value if Provenance.ASSUMED.value not in cap_src
                                       else Provenance.ASSUMED.value)
    if Provenance.ASSUMED.value in cap_src or Provenance.MEASURED.value in cap_src:
        warnings.append("supplier capacity not supplied for every SKU: INFERRED from historical PO peaks "
                        "(x1.25) or ASSUMED at 2x mean demand; capacity-bound recommendations are advisory")

    # ── opening stock, pipeline, promotions ──
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
        provenance["opening_inventory"] = Provenance.OPERATOR.value
    else:
        provenance["opening_inventory"] = Provenance.UNKNOWN.value
        warnings.append("no inventory snapshot: opening stock UNKNOWN (treated as zero)")
    promo_mult: dict = {}
    if len(promo):
        promo["week_start"] = pd.to_datetime(promo["week_start"])
        for r in promo.itertuples():
            t = int((r.week_start - origin).days // 7)
            if 0 <= t < horizon and r.sku in sup_of:
                promo_mult[(r.sku, t)] = float(r.uplift)

    # ── carrying cost: OPERATOR components, else the request's rate, else PUBLIC benchmark ──
    comp_keys = ("cost_of_capital_annual", "storage_handling_annual", "insurance_annual",
                 "shrink_obsolescence_annual", "other_annual")
    if any(k in econ for k in comp_keys):
        comps = CarryingCostComponents(**{k: float(str(econ.get(k, 0.0))) for k in comp_keys},
                                       provenance={k: econ_prov.get(k, "operator") for k in comp_keys if k in econ})
        holding = comps.per_period("week")
        provenance["holding_rate_per_period"] = Provenance.OPERATOR.value
    elif holding_rate_per_week is not None:
        comps = CarryingCostComponents(other_annual=holding_rate_per_week * 52)
        holding = holding_rate_per_week
        provenance["holding_rate_per_period"] = Provenance.ASSUMED.value
    else:
        comps = CarryingCostComponents(cost_of_capital_annual=0.10, storage_handling_annual=0.08,
                                       insurance_annual=0.01, shrink_obsolescence_annual=0.05)
        holding = comps.per_period("week")
        provenance["holding_rate_per_period"] = Provenance.PUBLIC.value
        warnings.append("carrying cost not supplied: PUBLIC benchmark 24%/yr used; the policy ranking is "
                        "sensitive to it, see carrying_cost_sensitivity")

    cc = CostConfig(currency=currency, holding_rate_per_period=holding,
                    shortage_cost_per_unit=margin, waste_cost_per_unit={j: cost[j] for j in products},
                    emergency_cost_multiplier=1.0, emergency_capacity_factor=0.0,
                    provenance={k: v for k, v in provenance.items()
                                if k in ("holding_rate_per_period", "shortage_cost_per_unit")})
    policy = fmcg_policy({r.sku: _pack_spec(r._asdict()) for r in skus.itertuples()},
                         cost_config=cc, service_level=service_level)
    classes = {r.sku: str(r.service_class) for r in skus.itertuples()
               if isinstance(getattr(r, "service_class", None), str) and r.service_class}
    if classes:
        by_class = {c: ServiceTarget(min(0.995, service_level + (0.02 if c.upper().startswith("A") else 0.0)),
                                     scope="sku_class", key=c) for c in set(classes.values())}
        by_class.update({c: ServiceTarget(float(econ[f"service_{c}"]), scope="sku_class", key=c)
                         for c in set(classes.values()) if f"service_{c}" in econ})
        policy = _replace(policy, service_by_class=by_class, sku_class=classes)
    policy.validate_products(products)

    mean_dem = {j: st.mean(train_dem[j]) for j in products}
    if incumbent_cover_weeks is not None:
        incumbent = configured_incumbent(cover_weeks=incumbent_cover_weeks)
    elif po_hist:
        incumbent = infer_incumbent(po_hist, mean_dem)
    else:
        incumbent = configured_incumbent(cover_weeks=max(lead_of.values()) + 1.0)
        warnings.append("no PO history to infer the incumbent from; a lead+1 order-up-to stands in")
    # Lead-time variability: measured from receipts where the supplier has
    # enough of them, otherwise a public prior by origin country (labelled).
    from domain.priors import lead_time_cv_prior
    origin_iso = {str(r.supplier_id): (str(r.origin_iso3) if isinstance(getattr(r, "origin_iso3", None), str)
                                        and r.origin_iso3 else None) for r in sup_master.itertuples()}
    lead_cv_prior: dict = {}
    priors_report: dict = {}
    for s_ in sorted(set(sup_of.values())):
        n_ev = len(supply_events.get(s_, {}))
        if n_ev < 8:
            pr = lead_time_cv_prior(origin_iso.get(s_))
            lead_cv_prior[s_] = pr.value
            priors_report[s_] = {**pr.as_dict(), "receipts_recorded": n_ev,
                                 "note": "prior in use; replaced by measured lead times once 8+ receipts exist"}
    route_of = {str(r.supplier_id): str(r.route) for r in sup_master.itertuples()
                if isinstance(getattr(r, "route", None), str) and r.route} if len(sup_master) else {}
    fi = FoldInputs(origin=int(origin.timestamp() // 604800), horizon=horizon, products=products,
                    supplier_of={j: sup_of[j] for j in products}, lead_of=lead_of,
                    train_demand=train_dem, train_fill=train_fill,
                    unit_cost={j: cost[j] for j in products}, margin=margin, capacity=cap,
                    opening=opening, pipeline=pipeline, policy=policy, promo_multiplier=promo_mult,
                    supply_events=supply_events, incumbent=incumbent, route_of=route_of,
                    lead_cv_prior=lead_cv_prior,
                    provenance=provenance)
    report = {"provenance": provenance, "warnings": warnings, "unknown_margin_skus": unknown_margin,
              "carrying_cost": comps.breakdown("week"),
              "carrying_cost_sensitivity": sensitivity_grid(comps, "week"),
              "incumbent": incumbent.label, "incumbent_notes": incumbent.notes[:5],
              "supply_history_events": {k: len(v) for k, v in supply_events.items()},
              "route_tags": len(route_of), "priors": priors_report}
    return fi, report


PORTWATCH_CSV = Path(__file__).resolve().parents[2] / "data" / "external" / "portwatch" / "regional_ports_daily.csv"
PORT_OF_ROUTE = {"aqaba": "AQABA", "red_sea": "AQABA", "sea": "AQABA", "haifa": "HAIFA"}


_SIGNAL_CACHE: dict = {}


def _indicator_signature() -> tuple:
    """mtimes of every indicator file; the store is rebuilt only when one changes."""
    from adaptive.indicators import IND, PORTWATCH
    sig = []
    for root in (PORTWATCH, IND):
        try:
            sig.extend(sorted((p.name, p.stat().st_mtime_ns) for p in Path(root).glob("*.csv")))
        except OSError:
            continue
    return tuple(sig)


def _signal_store() -> tuple[SignalStore, dict]:
    """Logistics evidence available to the planner: IMF PortWatch monthly
    throughput (REAL PUBLIC) for the ports the operator's routes touch.
    A missing file yields an EMPTY store, which the estimator reads as
    evidence UNAVAILABLE, never as normal conditions. The store is public
    data shared by every workspace, so it is built once per process and
    reused until an indicator file changes."""
    sig = _indicator_signature()
    hit = _SIGNAL_CACHE.get("store")
    if hit and hit[0] == sig:
        return hit[1], dict(hit[2])
    store = SignalStore(max_age_days=75.0)          # monthly series: two missed months = stale
    n = load_portwatch_signals(store, PORTWATCH_CSV, ports=("Aqaba",))
    counts = load_all_indicators(store)             # chokepoints, GSCPI, freight, fuel, news, demand
    src = {"portwatch_rows": n, "path": str(PORTWATCH_CSV.name), "provenance": "REAL_PUBLIC" if n else None,
           "indicators": counts, "indicator_cache": "data/external/indicators (scripts/fetch_indicators.py)"}
    _SIGNAL_CACHE["store"] = (sig, store, src)
    return store, dict(src)


def _state_for(fi, evidence_strength: float = 0.0):
    store, src = _signal_store()
    est = estimate(fi, store, evidence_strength=evidence_strength, port_of_route=PORT_OF_ROUTE)
    est.posture.p_disruptive_by_route = p_disruptive_by_route(est, fi)  # type: ignore[attr-defined]
    est.posture.in_recovery_by_route = in_recovery_by_route(est, fi)    # type: ignore[attr-defined]
    return est, src


def _replan_triggers(est) -> list:
    p = est.portfolio
    out = [f"portfolio p(disruptive) crosses {'0.35 (exit)' if p.p_disruptive() > 0.6 else '0.60 (enter)'}",
           "a change-point alarm on any supplier's fill or lead series",
           "demand level shift beyond 2 sd on any SKU (CUSUM)",
           "port throughput index below 0.85 on a route the operator uses, or the signal going stale",
           "inventory discrepancy above 10%", "promotion calendar change inside the horizon"]
    return out


@router.get("/state")
def state(
    horizon_weeks: int = Query(12, ge=4, le=26),
    train_weeks: int = Query(52, ge=MIN_HISTORY_WEEKS, le=156),
    conn=Depends(get_conn),
    authed: str | None = Depends(require_operator),
):
    """The operating state as the engine sees it: regime probabilities,
    stress with its named components, change points, signal freshness,
    and the posture the optimizer would be given. Read-only."""
    fi, report = build_inputs(conn, horizon=horizon_weeks, train_weeks=train_weeks, service_level=0.97,
                              holding_rate_per_week=None, currency="USD", incumbent_cover_weeks=None)
    est, src = _state_for(fi)
    out = {**est.as_dict(), "signal_sources": src, "economics_provenance": report["provenance"],
           "mode": est.posture.mode,
           "replan_triggers": _replan_triggers(est),
           "classification": "state estimate from operator history and public logistics signals; not a forecast"}
    out["plain"] = explain_state(out)
    return out



def latest_gate_decision(operator_id: str | None, n_products: int, history_periods: int,
                         max_age_days: int = 14) -> dict | None:
    """Most recent finished diagnostic for this workspace whose data shape
    matches what is loaded now (same product count and history length).
    Returns None when there is none, so the caller can ask for one."""
    import json
    from datetime import datetime, timedelta, timezone
    from infrastructure.operator_registry import OperatorRegistry
    if not operator_id:
        return None
    reports = OperatorRegistry().vault_dir(operator_id) / "reports"
    if not reports.exists():
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    best: dict | None = None
    for path in reports.glob("job_*.json"):
        try:
            rec = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        summ = rec.get("summary") or {}
        # older report files were written a moment before the job flipped to
        # "done", so the summary, not the status flag, is the evidence
        if rec.get("status") == "failed" or rec.get("kind") != "diagnostic" or not summ.get("decision"):
            continue
        finished = rec.get("finished_at") or rec.get("created_at") or ""
        try:
            when = datetime.fromisoformat(finished)
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when < cutoff:
            continue
        if summ.get("products") != n_products or summ.get("history_periods") != history_periods:
            continue
        if best is None or finished > best["finished_at"]:
            best = {"job_id": rec.get("id"), "finished_at": finished, "decision": summ["decision"],
                    "reason": summ.get("reason", ""), "improvement": summ.get("improvement"),
                    "candidates": summ.get("candidates", {})}
    return best

@router.post("/plan", dependencies=[Depends(rate_limiter)])
def plan(
    mode: str = Query("canonical", pattern="^(canonical|safe|adaptive|selected|stochastic|deterministic|order_up_to|incumbent|anchored)$"),
    horizon_weeks: int = Query(12, ge=4, le=26),
    commit_window_weeks: int = Query(4, ge=1, le=8),
    train_weeks: int = Query(52, ge=MIN_HISTORY_WEEKS, le=156),
    service_level: float = Query(0.97, gt=0.5, le=1.0),
    holding_rate_per_week: float | None = Query(None, ge=0.0, le=0.1),
    incumbent_cover_weeks: float | None = Query(None, gt=0.0, le=26),
    warehouse_cap_weeks: float | None = Query(None, ge=0.5, le=52),
    scenarios: int = Query(30, ge=10, le=200),
    currency: str = Query("USD", pattern="^[A-Z]{3}$"),
    seed: int = Query(0, ge=0),
    min_rel_improvement: float = Query(0.03, ge=0.0, le=0.5),
    diagnostics: bool = Query(False, description="also compute VSS/EVPI (20+ extra solves)"),
    skus: str | None = Query(None, description="canonical mode: comma-separated SKU subset to plan (default: every SKU with history)"),
    max_solve_seconds: float = Query(15., gt=0, le=120, description="canonical mode: the frozen engine's per-candidate solve budget"),
    conn=Depends(get_conn),
    authed: str | None = Depends(require_operator),
):
    """Rolling-horizon purchase plan. Only the first ``commit_window_weeks``
    are EXECUTABLE
    later weeks are ADVISORY and will be re-optimised at the
    next review. ``mode=safe`` (default) departs from the incumbent only on
    credible evidence and returns ``mode_run=incumbent`` otherwise, which is
    a successful outcome."""
    if mode == "canonical":
        # The canonical product path (post-P1 integration): the operator's vault -> the frozen P1
        # optimizer's compact Request -> the frozen planner -> this page's purchase-plan rows. The
        # frozen engine keeps its own product defaults (three stratified worlds, its solve budget);
        # `scenarios`, `train_weeks`, `holding_rate_per_week`, `warehouse_cap_weeks` and
        # `min_rel_improvement` belong to the superseded engine and are ignored here.
        from zaad.full.planner import plan as frozen_plan
        from zaad.full.workspace import WorkspaceError, build_request, to_purchase_plan
        try:
            subset = [x.strip() for x in skus.split(",") if x.strip()] if skus else None
            req, build = build_request(conn, authed or "workspace", horizon=horizon_weeks, service_target=service_level, seed=seed or 41001,
                                       skus=subset, max_solve_seconds=max_solve_seconds)
        except WorkspaceError as exc:
            raise HTTPException(422, {"code": "workspace_not_ready", "message": str(exc)}) from exc
        report = frozen_plan(req)
        return to_purchase_plan(req, report, build, commit_window_weeks=commit_window_weeks, run_id=str(report.get("input_fingerprint", "")))
    legacy_planner_gate()
    fi, report = build_inputs(conn, horizon=horizon_weeks, train_weeks=train_weeks, service_level=service_level,
                              holding_rate_per_week=holding_rate_per_week, currency=currency,
                              incumbent_cover_weeks=incumbent_cover_weeks)
    cap_total = (sum(st.mean(fi.train_demand[j]) for j in fi.products) * warehouse_cap_weeks
                 if warehouse_cap_weeks else None)
    rng = np.random.default_rng(seed)
    warnings = list(report["warnings"])
    decision: Any = None
    sched: Any = None
    meta: dict = {}
    cfg = SafeSelectionConfig(min_rel_improvement=min_rel_improvement, n_scen=scenarios)
    # ── adaptive state: estimated BEFORE any candidate runs, from history and signals only ──
    est, signal_src = _state_for(fi)
    fi.posture = est.posture
    commit_window_requested = commit_window_weeks
    commit_window_weeks = min(commit_window_weeks, int(est.posture.commit_window))
    gate_source: dict | None = None
    if mode == "safe":
        # The gate (rolling folds x candidates x scenarios) is the slow part
        # and the diagnostic job has already run it on this workspace. Reuse
        # that verdict when it matches the data as it stands now; otherwise
        # ask for a diagnostic rather than block the request for minutes.
        gate_source = latest_gate_decision(authed, n_products=len(fi.products),
                                           history_periods=min(len(v) for v in fi.train_demand.values()) if fi.train_demand else 0)
        if gate_source is None:
            raise HTTPException(409, {"code": "diagnostic_required",
                                      "message": "Run the diagnostic first. It backtests the candidates on your "
                                                 "history and decides whether the optimizer may change your orders; "
                                                 "the plan then solves in seconds."})
        mode_run = gate_source["decision"]
        sched, meta = run_candidate(mode_run, fi, cap_total, rng, scenarios,
                                    {"anchored_sp": EXTRA_CANDIDATES["anchored_sp"],
                                     "adaptive_sp": EXTRA_CANDIDATES["adaptive_sp"]})
        meta = dict(meta)
        warnings.append(f"gate verdict reused from diagnostic {gate_source['job_id']} finished "
                        f"{gate_source['finished_at'][:16].replace('T', ' ')} UTC: {gate_source['reason']}")
    elif mode == "selected":
        decision = safe_select(fi, cap_total, rng, cfg, posture=est.posture,
                               extra_candidates={"anchored_sp": EXTRA_CANDIDATES["anchored_sp"],
                                                 "adaptive_sp": EXTRA_CANDIDATES["adaptive_sp"]})
        sched, meta, mode_run = decision.schedule, dict(decision.meta), decision.mode_run
        warnings += decision.warnings
    elif mode == "adaptive":
        sched, meta = EXTRA_CANDIDATES["adaptive_sp"](fi, cap_total, rng, scenarios)  # type: ignore[operator]
        mode_run = "adaptive_sp"
    elif mode == "incumbent":
        sched, meta, mode_run = fi.incumbent.build_schedule(fi), {"status": "heuristic"}, INCUMBENT  # type: ignore[union-attr]
    elif mode == "stochastic":
        sched, meta = policy_stochastic_sp(fi, cap_total, rng, scenarios)
        mode_run = "stochastic_sp"
    elif mode == "deterministic":
        sched, meta = policy_deterministic_sp(fi, cap_total, rng)
        mode_run = "deterministic_sp"
    elif mode == "anchored":
        sched, meta = EXTRA_CANDIDATES["anchored_sp"](fi, cap_total, rng, scenarios)  # type: ignore[operator]
        mode_run = "anchored_sp"
    else:
        sched, meta, mode_run = policy_order_up_to(fi), {"status": "heuristic"}, "order_up_to"
    if sched is None:
        raise HTTPException(409, {"message": "The optimizer could not produce a usable plan.",
                                  "solver_status": meta.get("status"), "warnings": meta.get("warnings", [])})

    # ── diagnostics: regime, VSS/EVPI, baseline-relative regret ──
    regimes = diagnose(fi)
    reg_sum = regime_summary(regimes)
    info = None
    if not diagnostics:
        warnings.append("VSS/EVPI not computed (pass diagnostics=true; it is 20+ extra solves)")
    else:
      try:
        scen, leads, fills = _scenarios(fi, min(scenarios, 20), np.random.default_rng(seed + 1))
        iv = value_of_information(_optimizer_kwargs(fi, cap_total), scen, _supply_df(fi), leads, fills, fi.opening,
                                  distribution_confidence="low" if fi.history_periods_low() else "unknown")
        info = iv.as_dict()
      except Exception as exc:  # noqa: BLE001  diagnostics never block the plan
        warnings.append(f"VSS/EVPI unavailable ({type(exc).__name__})")
    regret = {}
    if meta.get("regret_by_scenario"):
        regret = regret_summary(meta["regret_by_scenario"], meta["scenario_weights"])

    fills_mean = {s_: st.mean(v) for s_, v in fi.train_fill.items()}
    ex = explain_schedule(sched, demand_history=fi.train_demand, on_hand=fi.opening, inbound=fi.pipeline,
                          expected_fill=fills_mean, lead_of=fi.lead_of, supplier_of=fi.supplier_of,
                          service_target=service_level, pack_specs=fi.policy.pack_specs,
                          solver_status=meta.get("status", "heuristic"), gap=meta.get("gap"))
    base_sched = fi.incumbent.build_schedule(fi)  # type: ignore[union-attr]
    orders = []
    for e in ex:
        spec = fi.policy.pack_spec_for(e.product_id)
        key = (e.supplier_id, e.product_id, e.period)
        base_q = float(base_sched.get(key, 0.0))
        orders.append({
            "sku": e.product_id, "supplier_id": e.supplier_id, "week_offset": e.period,
            "status": "EXECUTABLE" if e.period < commit_window_weeks else "ADVISORY",
            "order_units": e.order_units, "lots": e.lots, "lot_unit": spec.order_multiple.value,
            "units_per_lot": spec.lot_units, "quantity": e.order_units, "unit": "each",
            "incumbent_units": base_q, "deviation_from_incumbent": e.order_units - base_q,
            "regime": regimes[e.product_id].regime if e.product_id in regimes else None,
            "regime_reason": regimes[e.product_id].reasons[0] if e.product_id in regimes else None,
            "purchase_value": money_breakdown({"purchase": e.order_units * fi.unit_cost[e.product_id]}, currency)["total"],
            "explanation": e.reasons,
        })
    purchase = {"purchase_value": sum(o["order_units"] for o in orders if o["status"] == "EXECUTABLE") and
                sum(o["order_units"] * fi.unit_cost[o["sku"]] for o in orders if o["status"] == "EXECUTABLE")}
    audit = record_run(domain="fmcg", config={"mode": mode, "horizon_weeks": horizon_weeks, "commit_window_weeks": commit_window_weeks,
                                              "train_weeks": train_weeks, "service_level": service_level,
                                              "scenarios": scenarios, "currency": currency, "gates": cfg.__dict__},
                       inputs={"train_demand": fi.train_demand, "supply_events": fi.supply_events, "opening": fi.opening},
                       result={**{k: v for k, v in meta.items() if k not in ("model",)}, "usable": True, "run_id": None},
                       operator_id=authed, seed=seed,
                       scenario_config={"n_scen": scenarios, "seasonal": True, "promotions": len(fi.promo_multiplier),
                                        "supply_paths": "block_bootstrap" if fi.supply_events else "iid"},
                       objective_breakdown={"vss_evpi": info or {}, "regret": regret, "regime": reg_sum})
    improvement = None
    if gate_source and gate_source.get("improvement"):
        improvement = gate_source["improvement"]
    if decision and mode_run in decision.evidence and decision.evidence[mode_run].stats:
        stt = decision.evidence[mode_run].stats
        improvement = {"mean": stt.get("mean"), "lower_bound": stt.get("lower_bound"),
                       "downside_regret": stt.get("downside_regret", 0.0)}
    narrative = explain_posture(est.portfolio, est.posture, info, report["incumbent"], mode_run,
                                decision.reason if decision else f"{mode_run} run as requested",
                                improvement, commit_window_weeks, horizon_weeks)
    resp = {
        "run_id": audit.run_id, "mode_requested": mode, "mode_run": mode_run,
        "state": {**est.as_dict(), "signal_sources": signal_src},
        "posture": est.posture.as_dict(),
        "autonomy": {"score": est.posture.autonomy, "reasons": est.posture.reasons},
        "narrative": narrative,
        "baseline_policy": report["incumbent"], "incumbent_notes": report["incumbent_notes"],
        "reason": decision.reason if decision else f"{mode_run} run as requested; no selection performed",
        "candidate_policies": (list(decision.evidence) if decision else []),
        "candidate_evidence": (decision.as_dict()["candidates"] if decision else {}),
        "selection_gates": (decision.gates_config if decision else None),
        "candidates_admitted": meta.get("candidates_admitted"),
        "selection_basis": meta.get("selection_basis", "backtest" if decision else "requested"),
        "mode": est.posture.mode,
        "commit_window_requested": commit_window_requested,
        "conservative_improvement_vs_baseline": (
            decision.evidence[mode_run].stats.get("lower_bound") if decision and mode_run in decision.evidence else None),
        "service_difference_vs_baseline_pt": (
            (st.mean(decision.evidence[mode_run].service_diff) * 100) if decision and mode_run in decision.evidence
            and decision.evidence[mode_run].service_diff else None),
        "downside_regret_vs_baseline": (
            decision.evidence[mode_run].stats.get("downside_regret") if decision and mode_run in decision.evidence else None),
        "regret_scenarios": regret, "vss_evpi": info,
        "regime": {"dominant": reg_sum["dominant"], "counts": reg_sum["counts"],
                   "by_sku": {k: v.regime for k, v in regimes.items()}},
        "economics_provenance": report["provenance"], "carrying_cost": report["carrying_cost"],
        "priors_in_use": report.get("priors", {}),
        "carrying_cost_sensitivity": report["carrying_cost_sensitivity"],
        "constraint_provenance": {"supplier_capacity": report["provenance"].get("supplier_capacity"),
                                  "pack_structure": Provenance.OPERATOR.value},
        "supply_model": {"history_events": report["supply_history_events"], "route_tags": report["route_tags"],
                         "method": "moving_block_bootstrap" if fi.supply_events else "iid_fill_mean_lead"},
        "executable_until_week": commit_window_weeks, "advisory_horizon_weeks": horizon_weeks,
        "next_replan": {"cadence_weeks": commit_window_weeks, "adaptive_commit_window": est.posture.commit_window,
                        "triggers": _replan_triggers(est)},
        "solver_status": meta.get("status", "heuristic"), "warnings": warnings + list(meta.get("warnings", [])),
        "horizon_weeks": horizon_weeks, "unit": "each", "currency": currency,
        "products_planned": len(fi.products), "promotions_applied": len(fi.promo_multiplier),
        "orders": orders,
        "purchase_value_executable": money_breakdown(purchase, currency)["total"],
        "domain_policy": fi.policy.describe(),
        "classification": "operator data as uploaded; a recommendation, not a realised saving",
    }
    return resp


@router.get("/readiness")
def readiness(conn=Depends(get_conn), authed: str | None = Depends(require_operator)):
    """Pilot data completeness and the conclusions the gaps weaken."""
    return assess_readiness(conn).as_dict()


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
