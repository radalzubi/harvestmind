"""Multi-location workspace adapter (P2): the operator's vault -> a network `Request`.

Built on the frozen single-location adapter (`zaad.full.workspace.build_request`), which stays the
authority for SKUs, economics, supplier fits, order-level terms, pipeline and the leakage guard. When
the vault declares two or more locations (`stg_fmcg_locations`) this module re-shapes the frozen
request into a network:

* locations from `stg_fmcg_locations` (kind, holding rate, capacity);
* one service per (SKU, location) with order history at that location (`stg_fmcg_orders.location_id`),
  with its own weekly history; a location without orders serves nobody;
* opening stock per (SKU, location) from `stg_fmcg_inventory.location_id`;
* supplier sources delivered to the location their purchase orders name (`destination_id`), else the
  declared central DC, else the busiest location;
* lanes from `stg_fmcg_lanes` (one `Transfer` per lane and planned SKU; lead from the declaration or
  fitted from `stg_fmcg_transfers` receipts, capacity declared or a declared multiple of the
  destination's weekly demand, cost declared or zero with a warning, packs and dispatch fees as
  declared); open transfers become `inbound_transfers`;
* the incumbent network policy `network:rop` unless the economics table declares another rule;
* cross-location demand correlation declared in the economics table (`demand_correlation`) or
  estimated from the weekly history across locations per SKU (INFERRED_FROM_HISTORY, clipped to
  [0, 1]).

Every derived figure carries provenance; nothing after the origin is read; no customer ever needs
transfer history to get a diagnostic (declared lanes suffice). With fewer than two locations the
frozen adapter's request is returned unchanged.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from zaad.full.contracts import Request
from zaad.full.workspace import CALENDAR, CUSTOMER, LOCATION, WorkspaceError, _frame, _num, build_request

LANE_CAPACITY_WEEKS = 10.        # declared assumption when a lane's capacity is not given: ten weeks of the destination's demand per week
LANE_LEAD_DAYS = 7               # declared assumption when neither the lane nor its history gives a lead
# "No declared capacity" for a location. The frozen model uses the location capacity as the big-M of its
# depletion and FEFO rows; the single-location adapter's 1e9 is numerically unsafe once a second served
# location holds more than a period of demand (HiGHS reports infeasible), 1e8 is not. Ten million eaches
# is beyond any pilot vault and keeps the rows well conditioned.
UNBOUNDED_LOCATION_UNITS = 1e7


def _location_rows(conn) -> pd.DataFrame:
    try:
        return _frame(conn, "SELECT * FROM stg_fmcg_locations")
    except Exception:            # the table does not exist in an older vault
        return pd.DataFrame()


def _safe(conn, sql: str) -> pd.DataFrame:
    try:
        return _frame(conn, sql)
    except Exception:
        return pd.DataFrame()


def estimate_demand_correlation(weekly: pd.DataFrame) -> tuple[float | None, int]:
    """Mean pairwise correlation of weekly demand across locations, per SKU, over the SKUs with at
    least two locations and twelve overlapping weeks; clipped to [0, 1]. (value, pairs)."""
    values = []
    for _sku, group in weekly.groupby("sku"):
        table = group.pivot_table(index="week", columns="location_id", values="qty_ordered", aggfunc="sum").fillna(0.)
        if table.shape[1] < 2 or len(table) < 12:
            continue
        corr = table.corr().values
        for i in range(corr.shape[0]):
            for j in range(i + 1, corr.shape[1]):
                if np.isfinite(corr[i, j]):
                    values.append(float(corr[i, j]))
    if not values:
        return None, 0
    mean = float(np.mean(values))
    return float(min(1., max(0., mean))), len(values)


def build_network_request(conn: Any, operator_id: str, *, horizon: int = 12, period_days: int = 7, as_of: datetime | None = None,
                          service_target: float = .95, history_weeks: int = 52, seed: int = 41001, scenarios: int = 3,
                          max_solve_seconds: float = 15., skus: list[str] | None = None) -> tuple[Request, dict[str, Any]]:
    base, report = build_request(conn, operator_id, horizon=horizon, period_days=period_days, as_of=as_of, service_target=service_target,
                                 history_weeks=history_weeks, seed=seed, scenarios=scenarios, max_solve_seconds=max_solve_seconds, skus=skus)
    locations = _location_rows(conn)
    if len(locations) < 2:
        report["network"] = {"locations": int(len(locations)), "mode": "single_location", "note": "fewer than two declared locations: the frozen single-location request"}
        return base, report
    data = base.model_dump(mode="python")
    known = {"known_at": base.as_of - timedelta(seconds=1)}
    origin = pd.Timestamp(report["origin_monday"])
    warnings: list[str] = list(report.get("warnings", []))
    provenance: dict[str, str] = dict(report.get("provenance", {}))
    planned = [s["id"] for s in data["skus"]]
    economics = {str(r.key): r.value for r in _safe(conn, "SELECT key, value FROM stg_fmcg_economics").itertuples()} if len(_safe(conn, "SELECT key, value FROM stg_fmcg_economics")) else {}
    default_holding = data["locations"][0]["holding_per_value_period"]

    # ── locations ──
    loc_rows: list[dict[str, Any]] = []
    kinds: dict[str, str] = {}
    for row in locations.drop_duplicates("location_id", keep="last").itertuples():
        lid = str(row.location_id)
        kind = str(getattr(row, "kind", None) or "branch")
        if kind not in ("central_dc", "regional_dc", "branch", "warehouse"):
            kind = "branch"
        holding_annual = _num(getattr(row, "holding_annual", None), None)
        holding = holding_annual / 52. if holding_annual is not None else default_holding
        provenance[f"location.{lid}.holding_per_value_period"] = "CUSTOMER_PROVIDED" if holding_annual is not None else "CONFIGURED_ASSUMPTION"
        capacity = _num(getattr(row, "capacity_units", None), None)
        loc_rows.append({**known, "id": lid, "kind": kind, "capacity_volume": float(capacity) if capacity else UNBOUNDED_LOCATION_UNITS,
                         "holding_per_value_period": float(holding), "receiving_calendar": CALENDAR})
        kinds[lid] = kind
    ids = {r["id"] for r in loc_rows}
    central = next((r["id"] for r in loc_rows if r["kind"] == "central_dc"), None)

    # ── demand per (SKU, location) ──
    orders = _safe(conn, "SELECT sku, order_date, qty_ordered, location_id FROM stg_fmcg_orders")
    if orders.empty:
        raise WorkspaceError("Upload stg_fmcg_orders with a location_id column to plan a network.")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["location_id"] = orders["location_id"].fillna(LOCATION.upper()).astype(str)
    hist = orders[(orders["order_date"] < origin) & orders["sku"].astype(str).isin(planned)].copy()
    hist["sku"] = hist["sku"].astype(str)
    hist["week"] = (hist["order_date"] - origin).dt.days // 7
    span = report["compact"]["history_weeks"]
    unknown = sorted(set(hist["location_id"]) - ids)
    if unknown:
        warnings.append(f"orders name location(s) not in stg_fmcg_locations and are not planned: {unknown[:3]}")
        hist = hist[hist["location_id"].isin(ids)]
    weekly = hist.groupby(["sku", "location_id", "week"])["qty_ordered"].sum().reset_index()
    base_services = {s["sku"]: s for s in data["services"]}
    service_rows, history_rows = [], []
    serving: dict[str, set[str]] = {}
    for (sku, lid), group in weekly.groupby(["sku", "location_id"]):
        if float(group["qty_ordered"].sum()) <= 0 or sku not in base_services:
            continue
        template = base_services[sku]
        sid = f"svc_{sku}@{lid}"
        service_rows.append({**template, "id": sid, "location": lid})
        series = group.set_index("week")["qty_ordered"]
        history_rows += [{**known, "service": sid, "period": -k, "quantity": float(series.get(-k, 0.))} for k in range(span, 0, -1)]
        serving.setdefault(sku, set()).add(lid)
    if not service_rows:
        raise WorkspaceError("No (SKU, location) pair has order history at a declared location.")
    busiest = hist.groupby("location_id")["qty_ordered"].sum().idxmax() if len(hist) else next(iter(ids))

    # ── opening stock per (SKU, location) ──
    inventory = _safe(conn, "SELECT sku, snapshot_date, on_hand, location_id FROM stg_fmcg_inventory")
    stock_rows: list[dict[str, Any]] = []
    if len(inventory):
        inventory["snapshot_date"] = pd.to_datetime(inventory["snapshot_date"])
        inventory["location_id"] = inventory["location_id"].fillna(LOCATION.upper()).astype(str)
        snap = inventory[inventory["snapshot_date"] < origin]
        if len(snap):
            latest = snap[snap["snapshot_date"] == snap["snapshot_date"].max()].drop_duplicates(["sku", "location_id"], keep="last")
            shelf = {s["id"]: s["shelf_life"] for s in data["skus"]}
            for row in latest.itertuples():
                sku, lid = str(row.sku), str(row.location_id)
                if sku in shelf and lid in ids and float(row.on_hand or 0.) > 0:
                    stock_rows.append({**known, "id": f"open_{sku}@{lid}", "sku": sku, "location": lid, "quantity": float(row.on_hand),
                                       "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": shelf[sku], "age_periods": 0})

    # ── sources: where each supplier delivers ──
    pos = _safe(conn, "SELECT sku, supplier_id, qty_ordered, destination_id FROM stg_fmcg_purchase_orders")
    destination_of: dict[str, str] = {}
    if len(pos) and "destination_id" in pos:
        pos["destination_id"] = pos["destination_id"].fillna("").astype(str)
        for (sku, sup), group in pos[pos["destination_id"].isin(ids)].groupby(["sku", "supplier_id"]):
            destination_of[f"src_{sku}"] = str(group.groupby("destination_id")["qty_ordered"].sum().idxmax())
    source_rows = []
    for src in data["sources"]:
        dest = destination_of.get(src["id"]) or central or busiest
        provenance[f"source.{src['supplier']}.destination"] = "INFERRED_FROM_HISTORY" if src["id"] in destination_of else "CONFIGURED_ASSUMPTION"
        # a declared capacity that is not a whole pack is brought to the pack below it, so every legal
        # order is also a legal pack (the network policy projection and the settlement both check packs)
        packs = [m for m in (src["multiple"], src["case_multiple"], src["pallet_multiple"], src["transport_multiple"]) if m > 0]
        maximum = src["maximum"]
        if packs and maximum < 1e8:
            maximum = max(min(packs), math.floor(maximum / min(packs)) * min(packs))
        source_rows.append({**src, "destination": dest, "route": [src["supplier"], dest], "maximum": maximum,
                            "capacity_by_period": [min(c, maximum) for c in src["capacity_by_period"]]})
    source_dest = {s["id"]: s["destination"] for s in source_rows}

    # ── lanes ──
    lanes = _safe(conn, "SELECT * FROM stg_fmcg_lanes")
    transfers_hist = _safe(conn, "SELECT * FROM stg_fmcg_transfers")
    lead_fit: dict[tuple[str, str], tuple[int, int]] = {}
    inbound_rows: list[dict[str, Any]] = []
    if len(transfers_hist):
        for col in ("dispatch_date", "expected_arrival_date", "received_date"):
            if col in transfers_hist:
                transfers_hist[col] = pd.to_datetime(transfers_hist[col])
        closed = transfers_hist[transfers_hist["received_date"].notna() & (transfers_hist["received_date"] < origin)] if "received_date" in transfers_hist else pd.DataFrame()
        for (o, d), group in closed.groupby(["origin_id", "destination_id"]):
            days = (group["received_date"] - group["dispatch_date"]).dt.days
            days = days[days >= 0]
            if len(days) >= 3:
                lead_fit[str(o), str(d)] = (int(max(1, round(float(days.median())))), int(len(days)))
        open_rows = transfers_hist[(transfers_hist["dispatch_date"] < origin) & (transfers_hist["received_date"].isna() if "received_date" in transfers_hist else True)]
        shelf = {s["id"]: s["shelf_life"] for s in data["skus"]}
        for n, row in enumerate(open_rows.itertuples()):
            sku, o, d = str(row.sku), str(row.origin_id), str(row.destination_id)
            if sku not in shelf or d not in ids or o not in ids:
                continue
            eta = row.expected_arrival_date if ("expected_arrival_date" in open_rows and not pd.isna(row.expected_arrival_date)) else row.dispatch_date + pd.Timedelta(days=LANE_LEAD_DAYS)
            due_in = max(0, int((pd.Timestamp(eta) - origin).days // period_days))
            inbound_rows.append({**known, "id": f"inbound_{n}_{sku}", "sku": sku, "origin": o, "destination": d, "accepted_quantity": float(row.qty),
                                 "due_in": due_in, "expires_in": max(due_in + 1, shelf[sku])})
    demand_rate: dict[tuple[str, str], float] = {}
    for (sku, lid), group in weekly.groupby(["sku", "location_id"]):
        demand_rate[str(sku), str(lid)] = float(group["qty_ordered"].sum()) / max(1, span)
    transfer_rows: list[dict[str, Any]] = []
    if len(lanes):
        for row in lanes.itertuples():
            o, d = str(row.origin_id), str(row.destination_id)
            if o not in ids or d not in ids or o == d:
                warnings.append(f"lane {getattr(row, 'lane_id', '?')} references an unknown location and is ignored")
                continue
            if not bool(getattr(row, "approved", True) if getattr(row, "approved", None) is not None else True):
                continue
            sku_filter = getattr(row, "sku", None)
            for sku in ([str(sku_filter)] if isinstance(sku_filter, str) and sku_filter else planned):
                if sku not in planned:
                    continue
                lane_id = f"{getattr(row, 'lane_id', None) or f'{o}_{d}'}@{sku}"
                lead_days = _num(getattr(row, "lead_days", None), None)
                if lead_days is not None:
                    lead_prov = "CUSTOMER_PROVIDED"
                elif (o, d) in lead_fit:
                    lead_days, lead_prov = float(lead_fit[o, d][0]), "INFERRED_FROM_HISTORY"
                else:
                    lead_days, lead_prov = float(LANE_LEAD_DAYS), "CONFIGURED_ASSUMPTION"
                cost = _num(getattr(row, "cost_per_unit", None), None)
                if cost is None:
                    warnings.append(f"lane {lane_id}: no cost per unit declared; transfers on it are priced at zero")
                capacity = _num(getattr(row, "capacity_per_week", None), None)
                if capacity is None:
                    capacity = LANE_CAPACITY_WEEKS * max(1., demand_rate.get((sku, d), 0.))
                    cap_prov = "CONFIGURED_ASSUMPTION"
                else:
                    cap_prov = "CUSTOMER_PROVIDED"
                provenance[f"transfer.{lane_id}.lead"] = lead_prov
                provenance[f"transfer.{lane_id}.cost_per_unit"] = "CUSTOMER_PROVIDED" if cost is not None else "NOT_AVAILABLE"
                provenance[f"transfer.{lane_id}.capacity"] = cap_prov
                transfer_rows.append({**known, "id": lane_id, "sku": sku, "origin": o, "destination": d,
                                      "lead_periods": max(1, int(math.ceil(float(lead_days) / period_days))), "capacity": float(capacity),
                                      "cost_per_unit": float(cost or 0.), "loss_fraction": 0., "approved": True,
                                      "multiple": float(_num(getattr(row, "units_per_pack", None), 0.) or 0.),
                                      "fixed_cost_per_dispatch": float(_num(getattr(row, "fixed_cost_per_dispatch", None), 0.) or 0.)})
    else:
        warnings.append("no lanes declared in stg_fmcg_lanes: locations are planned as isolated (no transfers)")
    # isolated demand: a served location that neither buys nor is fed
    fed = {(a["sku"], a["destination"]) for a in transfer_rows}
    buys = {(s["sku"], s["destination"]) for s in source_rows}
    for s in service_rows:
        if (s["sku"], s["location"]) not in fed and (s["sku"], s["location"]) not in buys:
            warnings.append(f"{s['sku']}@{s['location']} has demand but no supplier delivery and no lane: it can only serve from stock on hand")

    # ── incumbent policy and correlation ──
    rule_override = economics.get("incumbent_rule")
    incumbent_rule = str(rule_override) if isinstance(rule_override, str) and rule_override else ("network:rop" if transfer_rows else data["incumbent_rule"])
    provenance["incumbent_rule"] = "CUSTOMER_PROVIDED" if isinstance(rule_override, str) and rule_override else "CONFIGURED_ASSUMPTION"
    declared_rho = _num(economics.get("demand_correlation"), None)
    if declared_rho is not None:
        rho, rho_prov, pairs = float(min(1., max(0., declared_rho))), "CUSTOMER_PROVIDED", 0
    else:
        est, pairs = estimate_demand_correlation(weekly)
        rho, rho_prov = (est, "INFERRED_FROM_HISTORY") if est is not None else (0., "NOT_AVAILABLE")
    provenance["demand_correlation"] = rho_prov

    from zaad.meio.topology import network_scenarios, network_solve_seconds
    longest = max((a["lead_periods"] for a in transfer_rows), default=0)
    worlds = max(int(data["scenarios"]), network_scenarios(longest))
    data.update({"locations": loc_rows, "services": service_rows, "history": history_rows, "stock": stock_rows, "sources": source_rows,
                 "transfers": transfer_rows, "inbound_transfers": inbound_rows, "incumbent_rule": incumbent_rule, "demand_correlation": rho,
                 "scenarios": worlds, "max_solve_seconds": network_solve_seconds(float(data["max_solve_seconds"]), worlds),
                 # pack lanes make the joint MILP general-integer: a 1e-4 optimality gap is the honest operational
                 # setting there (the frozen contract's own note on solver_mip_gap); continuous lanes keep the default
                 "solver_mip_gap": (1e-4 if any(a["multiple"] > 0 for a in transfer_rows) else data["solver_mip_gap"]),
                 "events": [{**e, "service": f"{e['service']}@{lid}"} for e in data["events"] for lid in serving.get(e["service"].split("svc_", 1)[-1], [])],
                 "customers": [{**known, "id": CUSTOMER, "channel": "wholesale", "priority": 1.}],
                 "pipeline": [{**po} for po in data["pipeline"] if po["source"] in source_dest],
                 "economics_provenance": {k: v for k, v in provenance.items() if v in ("CUSTOMER_PROVIDED", "INFERRED_FROM_HISTORY", "CONFIGURED_ASSUMPTION", "NOT_AVAILABLE")}})
    request = Request.model_validate(data)
    report["warnings"] = warnings
    report["provenance"] = provenance
    report["compact"].update({"locations": len(loc_rows), "services": len(service_rows), "lanes": len(transfer_rows), "history_observations": len(history_rows),
                              "stock_rows": len(stock_rows), "open_transfers": len(inbound_rows)})
    report["network"] = {"mode": "network", "locations": {r["id"]: r["kind"] for r in loc_rows}, "central": central, "lanes": [a["id"] for a in transfer_rows],
                         "lead_fits": {f"{o}->{d}": {"lead_days": v[0], "sample_size": v[1]} for (o, d), v in lead_fit.items()},
                         "demand_correlation": {"value": rho, "provenance": rho_prov, "pairs": pairs}, "incumbent_rule": incumbent_rule,
                         "source_destinations": source_dest}
    return request, report


def to_network_plan(request: Request, report: dict[str, Any], build: dict[str, Any], *, commit_window_weeks: int = 4, run_id: str = "") -> dict[str, Any]:
    """The workspace plan shape for a network: the purchase-plan rows plus the recommended transfers
    inside the commit window, the network block and the operator-facing explanations."""
    from zaad.full.workspace import to_purchase_plan
    out = to_purchase_plan(request, report, build, commit_window_weeks=commit_window_weeks, run_id=run_id)
    lanes = {a.id: a for a in request.transfers}
    moves: dict[tuple[str, int], float] = {}
    for action in report.get("actions") or []:
        if action.get("action") == "transfer" and action.get("period", 0) < commit_window_weeks and float(action.get("quantity", 0.)) > 0:
            moves[action["transfer"], int(action["period"])] = moves.get((action["transfer"], int(action["period"])), 0.) + float(action["quantity"])
    net = report.get("network") or {}
    explanations = (net.get("explanations") or {}).get("transfers", [])
    why = {row["transfer"]: row["summary"] for row in explanations}
    out["transfers"] = [{"transfer": arc_id, "sku": lanes[arc_id].sku, "origin": lanes[arc_id].origin, "destination": lanes[arc_id].destination,
                         "week_offset": t, "units": round(q, 2), "arrives_week": t + lanes[arc_id].lead_periods, "cost_per_unit": lanes[arc_id].cost_per_unit,
                         "transfer_value": {"amount": f"{q * lanes[arc_id].cost_per_unit:.2f}", "currency": request.currency},
                         "explanation": why.get(arc_id)} for (arc_id, t), q in sorted(moves.items())]
    out["mode_run"] = "canonical_p2_network" if request.transfers else out["mode_run"]
    out["engine"] = "zaad.full frozen P1 with the P2 network layer" if request.transfers else out["engine"]
    out["network"] = {k: net.get(k) for k in ("state", "router", "explanations", "declared")} if net else None
    out["network_service"] = {s["service"]: {"location": s["location"], "target": s["target"], "expected": s.get("achieved"), "breach_share": s.get("breach_share")}
                              for s in ((net.get("selected") or {}).get("services") or [])}
    out["build"]["network"] = build.get("network")
    return out
