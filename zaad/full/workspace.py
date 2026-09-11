"""Tenant workspace -> frozen optimizer Request (the canonical customer-data path, P1 scope).

    operator files / integrations
      -> validated tenant storage        (api/routers/intake.py, the operator's own DuckDB vault)
      -> normalised planning data        (this module: weekly periods, one row per SKU / supplier)
      -> forecasting / calibration       (the frozen engine's own fitting from the compact history and
                                          the shipment observations; nothing is re-fitted here)
      -> compact optimizer Request       (`zaad.full.contracts.Request`, the frozen contract)
      -> recommendation                  (`zaad.full.planner.plan`)
      -> report / UI                     (`to_purchase_plan` for the workspace page)

Reads the FMCG staging tables (migrations 013-015: stg_fmcg_skus, _orders, _purchase_orders,
_receipts, _inventory, _promotions, _suppliers, _economics) and translates them into the frozen
contract. Nothing decisive is invented: every number that is not customer-provided carries a
provenance (INFERRED_FROM_HISTORY with its sample size, CONFIGURED_ASSUMPTION, NOT_AVAILABLE) in the
build report, and the planner's own economics_provenance is populated from it. No future leakage:
history, receipts and fits use only rows dated before the planning origin; open purchase orders are
those placed before the origin and not yet fully received.

Raw history stays in the vault. The optimizer receives one weekly demand series per SKU over at most
`history_weeks` periods, one shipment observation per historical purchase order, the opening stock,
the open orders and the declared economics: hundreds of rows, not the raw tables.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from zaad.full.contracts import Request
from zaad.sectors.workspace import lot_expiry_periods, sku_physics_rows
from zaad.full.uncertainty import MIN_SUPPLY_RECORDS

LOCATION = "main"
CUSTOMER = "customers"
CALENDAR = "always"
UNBOUNDED = 1e9
PUBLIC_COST_OF_CAPITAL_ANNUAL = .10      # the same public benchmark the FMCG path falls back to
PUBLIC_STORAGE_HANDLING_ANNUAL = .08
ASSUMED_FILL = (.95, .05)                # (mean, sd) when fewer than MIN_SUPPLY_RECORDS closed orders
ASSUMED_LEAD_DAYS = 14
ASSUMED_LEAD_SD_DAYS = 2.
ASSUMED_SALVAGE_FRACTION = .8
ASSUMED_SHELF_LIFE_PERIODS = 52
ASSUMED_MARGIN_FRACTION = .3             # selling price over cost when no price is provided
MIN_HISTORY_WEEKS = 16


class WorkspaceError(ValueError):
    """The workspace cannot be planned yet (missing tables, too little history); message is operator-facing."""


def _frame(conn: Any, sql: str) -> pd.DataFrame:
    try:
        return conn.execute(sql).fetchdf()
    except Exception:  # noqa: BLE001 - a missing optional table is an empty frame, reported in the build
        return pd.DataFrame()


def _num(value: Any, default: float | None) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _monday(day: pd.Timestamp) -> pd.Timestamp:
    day = day.normalize()
    return day - pd.Timedelta(days=day.weekday())


def _economics(conn: Any) -> tuple[dict[str, Any], dict[str, str]]:
    frame = _frame(conn, "SELECT key, value, provenance FROM stg_fmcg_economics")
    values: dict[str, Any] = {}
    prov: dict[str, str] = {}
    for row in frame.itertuples():
        key = str(row.key)
        number = _num(row.value, None)
        values[key] = number if number is not None else str(row.value)
        prov[key] = str(row.provenance or "operator")
    return values, prov


def fit_supply(pos: pd.DataFrame, receipts: pd.DataFrame, origin: pd.Timestamp, promised_weeks: dict[str, float]) -> dict[str, dict[str, Any]]:
    """Per supplier: fill and lead fitted from purchase orders closed before the origin, with the sample
    size and the provenance; declared promises or configured assumptions otherwise. No order dated at or
    after the origin enters a fit."""
    out: dict[str, dict[str, Any]] = {}
    if len(pos) and len(receipts):
        got = receipts.groupby("po_id").agg(qty_received=("qty_received", "sum"), first=("receipt_date", "min"))
        joined = pos.join(got, on="po_id")
        joined = joined[(joined["po_date"] < origin) & joined["qty_received"].notna() & (joined["first"] < origin)]
        joined = joined.assign(fill=(joined["qty_received"] / joined["qty_ordered"]).clip(0., 1.),
                               lead_days=(joined["first"] - joined["po_date"]).dt.days.clip(lower=1))
        for supplier, group in joined.groupby("supplier_id"):
            fills = [float(x) for x in group["fill"]]
            leads = [float(x) for x in group["lead_days"]]
            n = len(fills)
            if n >= MIN_SUPPLY_RECORDS:
                out[str(supplier)] = {
                    "fill_mean": min(1., max(1e-3, statistics.fmean(fills))),
                    "fill_sd": min(.5, max(.005, statistics.pstdev(fills))),
                    "lead_days": max(1, int(round(statistics.fmean(leads)))),
                    "lead_sd_days": float(min(365., statistics.pstdev(leads))),
                    "sample_size": n, "provenance": "INFERRED_FROM_HISTORY"}
            else:
                out[str(supplier)] = {"sample_size": n, "provenance": "CONFIGURED_ASSUMPTION"}
    for supplier, weeks in promised_weeks.items():
        entry = out.setdefault(str(supplier), {"sample_size": 0, "provenance": "CONFIGURED_ASSUMPTION"})
        if entry["provenance"] != "INFERRED_FROM_HISTORY" and weeks and weeks > 0:
            entry.update({"lead_days": max(1, int(round(weeks * 7))), "lead_provenance": "CUSTOMER_PROVIDED"})
    for entry in out.values():
        entry.setdefault("fill_mean", ASSUMED_FILL[0])
        entry.setdefault("fill_sd", ASSUMED_FILL[1])
        entry.setdefault("lead_days", ASSUMED_LEAD_DAYS)
        entry.setdefault("lead_sd_days", ASSUMED_LEAD_SD_DAYS)
    return out


def infer_incumbent_rule(pos: pd.DataFrame, origin: pd.Timestamp) -> tuple[str, str]:
    """The operator's own ordering cadence as the frozen engine's incumbent rule: the median gap between
    purchase-order dates before the origin. Weekly buying -> replace_sold; a regular k-week cadence ->
    periodic:k; otherwise reorder_point."""
    if not len(pos):
        return "reorder_point", "NOT_AVAILABLE"
    days = sorted({d.normalize() for d in pos.loc[pos["po_date"] < origin, "po_date"]})
    if len(days) < 4:
        return "reorder_point", "NOT_AVAILABLE"
    gaps = [(b - a).days / 7. for a, b in zip(days, days[1:])]
    median = statistics.median(gaps)
    if median <= 1.5:
        return "replace_sold", "INFERRED_FROM_HISTORY"
    k = int(round(median))
    return (f"periodic:{k}" if 2 <= k <= 8 else "reorder_point"), "INFERRED_FROM_HISTORY"


def build_request(conn: Any, operator_id: str, *, horizon: int = 12, period_days: int = 7, as_of: datetime | None = None,
                  service_target: float = .95, history_weeks: int = 52, seed: int = 41001, scenarios: int = 3,
                  max_solve_seconds: float = 15., min_history_weeks: int = MIN_HISTORY_WEEKS,
                  shipment_observations_per_source: int = 60, skus: list[str] | None = None,
                  sector_mode: str | None = None) -> tuple[Request, dict[str, Any]]:
    """The frozen contract built from the operator's vault, plus the build report (rows read, compact
    dimensions, fits with sample sizes, provenance, warnings, leakage guard). Raises WorkspaceError with
    an operator-facing message when the workspace cannot be planned yet."""
    if period_days != 7:
        raise WorkspaceError("the workspace adapter plans in weekly periods")
    skus_frame = _frame(conn, "SELECT * FROM stg_fmcg_skus")
    orders = _frame(conn, "SELECT sku, order_date, qty_ordered FROM stg_fmcg_orders")
    pos = _frame(conn, "SELECT po_id, po_date, supplier_id, sku, qty_ordered, unit_cost, expected_delivery_date FROM stg_fmcg_purchase_orders")
    receipts = _frame(conn, "SELECT po_id, receipt_date, qty_received FROM stg_fmcg_receipts")
    inventory = _frame(conn, "SELECT * FROM stg_fmcg_inventory")
    promotions = _frame(conn, "SELECT sku, week_start, uplift FROM stg_fmcg_promotions")
    suppliers = _frame(conn, "SELECT * FROM stg_fmcg_suppliers")
    economics, economics_prov = _economics(conn)
    rows_read = {"stg_fmcg_skus": len(skus_frame), "stg_fmcg_orders": len(orders), "stg_fmcg_purchase_orders": len(pos),
                 "stg_fmcg_receipts": len(receipts), "stg_fmcg_inventory": len(inventory), "stg_fmcg_promotions": len(promotions),
                 "stg_fmcg_suppliers": len(suppliers), "stg_fmcg_economics": len(economics)}
    if skus_frame.empty or orders.empty:
        raise WorkspaceError("Upload stg_fmcg_skus and stg_fmcg_orders before planning.")
    sku_filter = {str(x) for x in skus} if skus else None
    master = skus_frame.drop_duplicates("sku", keep="last")
    if sku_filter is not None:
        master = master[master["sku"].astype(str).isin(sku_filter)]
        orders = orders[orders["sku"].astype(str).isin(sku_filter)]
        if len(pos):
            pos = pos[pos["sku"].astype(str).isin(sku_filter)]
        if master.empty or orders.empty:
            raise WorkspaceError("none of the requested SKUs has a master row and order history")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    if len(pos):
        pos["po_date"] = pd.to_datetime(pos["po_date"])
        if "expected_delivery_date" in pos:
            pos["expected_delivery_date"] = pd.to_datetime(pos["expected_delivery_date"])
    if len(receipts):
        receipts["receipt_date"] = pd.to_datetime(receipts["receipt_date"])
    if len(inventory):
        inventory["snapshot_date"] = pd.to_datetime(inventory["snapshot_date"])
    if len(promotions):
        promotions["week_start"] = pd.to_datetime(promotions["week_start"])

    if as_of is not None:
        stamp = pd.Timestamp(as_of)
        origin = _monday(stamp.tz_convert(None) if stamp.tzinfo is not None else stamp)
    else:
        origin = _monday(orders["order_date"].max() + pd.Timedelta(days=7))
    known_at = origin.to_pydatetime().replace(tzinfo=timezone.utc) - timedelta(seconds=1)
    known = {"known_at": known_at}
    warnings: list[str] = []
    provenance: dict[str, str] = {}

    # ── demand history: weekly units per SKU, strictly before the origin ──
    hist = orders[orders["order_date"] < origin]
    weeks_available = int(((origin - hist["order_date"].min()).days // 7)) if len(hist) else 0
    if weeks_available < min_history_weeks:
        raise WorkspaceError(f"Need at least {min_history_weeks} weeks of order history before {origin.date()}; found {weeks_available}.")
    hist = hist.assign(week=((hist["order_date"] - origin).dt.days // 7))
    weekly = hist.groupby(["sku", "week"])["qty_ordered"].sum()
    span = min(history_weeks, weeks_available)
    products = [str(s) for s in master["sku"] if s in weekly.index.get_level_values(0) and float(weekly.xs(s, level="sku").sum()) > 0]
    if not products:
        raise WorkspaceError("No SKU in stg_fmcg_skus has order history.")
    skipped = [str(s) for s in master["sku"] if str(s) not in products]
    if skipped:
        warnings.append(f"{len(skipped)} SKU(s) without order history are not planned (e.g. {skipped[:3]})")

    # ── economics with provenance ──
    def econ(key: str, default: float, label: str) -> float:
        value = _num(economics.get(key), None)
        provenance[label] = "CUSTOMER_PROVIDED" if value is not None else "CONFIGURED_ASSUMPTION"
        return float(value) if value is not None else default
    storage_annual = econ("storage_handling_annual", PUBLIC_STORAGE_HANDLING_ANNUAL, "location.main.holding_per_value_period")
    for key in ("insurance_annual", "obsolescence_annual", "other_annual"):
        storage_annual += float(_num(economics.get(key), 0.) or 0.)
    holding_per_period = storage_annual / 52.
    cost_of_capital_period = econ("cost_of_capital_annual", PUBLIC_COST_OF_CAPITAL_ANNUAL, "liquidity.cost_of_capital_per_period") / 52.
    interest_period = econ("interest_annual", 0., "liquidity.interest_per_period") / 52.
    salvage_fraction = econ("salvage_fraction", ASSUMED_SALVAGE_FRACTION, "sku.terminal_value")
    currency = str(economics.get("currency") or "USD")
    if not (isinstance(currency, str) and len(currency) == 3 and currency.isalpha() and currency.isupper()):
        currency = "USD"
    opening_cash = _num(economics.get("opening_cash"), None)
    provenance["liquidity.opening_cash"] = "CUSTOMER_PROVIDED" if opening_cash is not None else "NOT_AVAILABLE"
    rule_override = economics.get("incumbent_rule")
    if isinstance(rule_override, str) and rule_override:
        incumbent_rule, rule_prov = rule_override, "CUSTOMER_PROVIDED"
    else:
        incumbent_rule, rule_prov = infer_incumbent_rule(pos, origin)
    provenance["incumbent_rule"] = rule_prov

    # ── suppliers: capacity, promised lead, fits ──
    sup_rows = {str(r.supplier_id): r for r in suppliers.itertuples()} if len(suppliers) else {}
    promised = {sid: float(_num(getattr(r, "lead_time_promised_weeks", None), 0.) or 0.) for sid, r in sup_rows.items()}
    fits = fit_supply(pos, receipts, origin, promised)
    sku_supplier: dict[str, str] = {}
    supplier_prov: dict[str, str] = {}
    po_units_by_sku: dict[str, pd.Series] = {}
    if len(pos):
        past_pos = pos[pos["po_date"] < origin]
        for sku, group in past_pos.groupby("sku"):
            po_units_by_sku[str(sku)] = group.groupby("supplier_id")["qty_ordered"].sum()
    for row in master.itertuples():
        sku = str(row.sku)
        declared = getattr(row, "supplier_id", None)
        if isinstance(declared, str) and declared:
            sku_supplier[sku], supplier_prov[sku] = declared, "CUSTOMER_PROVIDED"
        elif sku in po_units_by_sku and len(po_units_by_sku[sku]):
            sku_supplier[sku], supplier_prov[sku] = str(po_units_by_sku[sku].idxmax()), "INFERRED_FROM_HISTORY"
    unsourced = [s for s in products if s not in sku_supplier]
    if unsourced:
        warnings.append(f"{len(unsourced)} SKU(s) have no supplier (master or purchase history) and cannot be sourced (e.g. {unsourced[:3]})")
    supplier_ids = sorted({sku_supplier[s] for s in products if s in sku_supplier})
    po_peak: dict[str, float] = {}
    if len(pos):
        past = pos[pos["po_date"] < origin].assign(week=((pos["po_date"] - origin).dt.days // 7))
        for sid, group in past.groupby("supplier_id"):
            po_peak[str(sid)] = float(group.groupby("week")["qty_ordered"].sum().max())
    capacity: dict[str, tuple[float, str]] = {}
    for sid in supplier_ids:
        master_cap = _num(getattr(sup_rows.get(sid), "capacity_per_week", None), None) if sid in sup_rows else None
        per_sku = [v for v in (_num(getattr(r, "supplier_capacity_per_week", None), None) for r in master.itertuples() if sku_supplier.get(str(r.sku)) == sid) if v]
        if master_cap:
            capacity[sid] = (master_cap, "CUSTOMER_PROVIDED")
        elif per_sku:
            capacity[sid] = (float(sum(per_sku)), "CUSTOMER_PROVIDED")
        elif sid in po_peak and po_peak[sid] > 0:
            capacity[sid] = (1.25 * po_peak[sid], "INFERRED_FROM_HISTORY")
        else:
            capacity[sid] = (UNBOUNDED, "NOT_AVAILABLE")
        provenance[f"resource.{sid}.capacity"] = capacity[sid][1]
        provenance[f"source.{sid}.fill"] = fits.get(sid, {}).get("provenance", "CONFIGURED_ASSUMPTION")
        provenance[f"source.{sid}.lead"] = fits.get(sid, {}).get("lead_provenance", fits.get(sid, {}).get("provenance", "CONFIGURED_ASSUMPTION"))

    # ── contract rows ──
    sku_rows, source_rows, service_rows, history_rows, stock_rows, event_rows, supplier_terms = [], [], [], [], [], [], []
    latest_cost: dict[str, float] = {}
    if len(pos):
        for sku, group in pos[pos["po_date"] < origin].sort_values("po_date").groupby("sku"):
            cost = _num(group["unit_cost"].dropna().iloc[-1], None) if group["unit_cost"].notna().any() else None
            if cost:
                latest_cost[str(sku)] = float(cost)
    pack: dict[str, dict[str, float]] = {}
    for row in master.itertuples():
        sku = str(row.sku)
        if sku not in products:
            continue
        unit_cost = _num(row.unit_cost, None) or latest_cost.get(sku)
        if not unit_cost or unit_cost <= 0:
            warnings.append(f"SKU {sku} has no unit cost; not planned")
            continue
        shelf_days = _num(getattr(row, "shelf_life_days", None), None)
        shelf_periods = max(1, int(round(shelf_days / period_days))) if shelf_days else ASSUMED_SHELF_LIFE_PERIODS
        provenance.setdefault("sku.shelf_life", "CUSTOMER_PROVIDED" if shelf_days else "CONFIGURED_ASSUMPTION")
        sku_rows.append({**known, "id": sku, "volume": 1., "asset_value": unit_cost, "terminal_value": unit_cost * salvage_fraction,
                         "shelf_life": min(520, shelf_periods), "disposal_fee": 0.})
        price = _num(getattr(row, "unit_price", None), None)
        margin = _num(getattr(row, "contribution_margin", None), None)
        selling = price if price and price > unit_cost else (unit_cost + margin if margin and margin > 0 else unit_cost * (1 + ASSUMED_MARGIN_FRACTION))
        provenance.setdefault("service.selling_price", "CUSTOMER_PROVIDED" if (price and price > unit_cost) or (margin and margin > 0) else "CONFIGURED_ASSUMPTION")
        service_class = getattr(row, "service_class", None)
        target = service_target
        if isinstance(service_class, str) and service_class and _num(economics.get(f"service_{service_class}"), None) is not None:
            target = float(economics[f"service_{service_class}"])
        service_rows.append({**known, "id": f"svc_{sku}", "sku": sku, "location": LOCATION, "customer": CUSTOMER,
                             "target": min(1., max(0., target)), "selling_price": float(selling), "sla_per_unmet": float(_num(economics.get("sla_per_unmet"), 0.) or 0.)})
        series = weekly.xs(sku, level="sku") if sku in weekly.index.get_level_values(0) else pd.Series(dtype=float)
        history_rows += [{**known, "service": f"svc_{sku}", "period": -k, "quantity": float(series.get(-k, 0.))} for k in range(span, 0, -1)]
        upc = _num(getattr(row, "units_per_case", None), None) or 0.
        cpl = _num(getattr(row, "cases_per_layer", None), None) or 0.
        lpp = _num(getattr(row, "layers_per_pallet", None), None) or 0.
        pack[sku] = {"case": upc, "pallet": upc * cpl * lpp if upc and cpl and lpp else 0.}
        sid = sku_supplier.get(sku)
        if sid is None:
            continue
        fit = fits.get(sid, {"fill_mean": ASSUMED_FILL[0], "fill_sd": ASSUMED_FILL[1], "lead_days": ASSUMED_LEAD_DAYS, "lead_sd_days": ASSUMED_LEAD_SD_DAYS})
        cap = capacity[sid][0]
        source_rows.append({**known, "id": f"src_{sku}", "supplier": sid, "sku": sku, "destination": LOCATION,
                            "route": [sid, LOCATION], "resources": [f"cap_{sid}"], "capacity_by_period": [cap] * horizon,
                            "unit_price": unit_cost, "freight_per_unit": float(_num(economics.get(f"freight_per_unit_{sid}"), 0.) or 0.),
                            "handling_per_unit": float(_num(economics.get("handling_per_unit"), 0.) or 0.),
                            "minimum": float(_num(getattr(row, "moq_units", None), 0.) or 0.), "multiple": 0., "case_multiple": float(upc),
                            "pallet_multiple": float(pack[sku]["pallet"]), "maximum": cap,
                            "fixed_order_fee": float(_num(getattr(row, "fixed_po_cost", None), 0.) or 0.),
                            "terms": f"terms_{sid}", "order_calendar": CALENDAR, "shipping_calendar": CALENDAR,
                            "lead_days": int(fit["lead_days"]), "dispatch_days": 0, "fill_mean": float(fit["fill_mean"]), "fill_sd": float(fit["fill_sd"]),
                            "lead_sd_days": float(fit["lead_sd_days"]), "approved": True, "compliance": "cleared",
                            "quote_expires": known_at + timedelta(days=365), "quote_reference": f"workspace:{operator_id}"})
    planned = {r["id"] for r in sku_rows}
    sourced = {r["sku"] for r in source_rows}
    physics_rows, physics_mode = sku_physics_rows(master, sorted(planned), period_days, provenance, warnings, sector_mode)

    # ── supplier terms (order-level economics the P1 engine prices) ──
    terms_rows, resource_rows = [], []
    for sid in supplier_ids:
        units_per_pallet = {s: pack[s]["pallet"] for s in sourced if sku_supplier.get(s) == sid and pack[s]["pallet"] > 0}
        fixed = _num(economics.get(f"fixed_order_cost_{sid}"), None)
        if fixed is None:
            fixed = _num(economics.get("fixed_order_cost"), None)
        mov = _num(economics.get(f"minimum_order_value_{sid}"), None)
        term_prov = {}
        if fixed is not None:
            term_prov["fixed_order_cost"] = "CUSTOMER_PROVIDED"
        if mov is not None:
            term_prov["minimum_order_value"] = "CUSTOMER_PROVIDED"
        # sector physics: a declared shipment weight cap on the supplier row (migration 017)
        max_weight = None
        if len(suppliers) and "max_shipment_weight" in suppliers.columns:
            cap_rows = suppliers[suppliers["supplier_id"].astype(str) == sid]
            if len(cap_rows):
                max_weight = _num(cap_rows.iloc[-1]["max_shipment_weight"], None)
                if max_weight is not None and max_weight > 0:
                    term_prov["max_shipment_weight"] = "CUSTOMER_PROVIDED"
                else:
                    max_weight = None
        if fixed is not None or mov is not None or units_per_pallet or max_weight is not None:
            supplier_terms.append({**known, "id": f"terms_{sid}", "supplier": sid, "fixed_order_cost": float(fixed or 0.),
                                   "minimum_order_value": float(mov or 0.), "units_per_pallet": units_per_pallet, "provenance": term_prov,
                                   **({"max_shipment_weight": float(max_weight)} if max_weight is not None else {})})
        net_days = _num(economics.get(f"net_days_{sid}"), None)
        if net_days is None:
            net_days = _num(economics.get("net_days"), 0.)
        provenance[f"terms.{sid}.net_days"] = "CUSTOMER_PROVIDED" if (economics.get(f"net_days_{sid}") is not None or economics.get("net_days") is not None) else "CONFIGURED_ASSUMPTION"
        terms_rows.append({**known, "id": f"terms_{sid}", "deposit_fraction": 0., "balance_trigger": "arrival", "net_days": int(net_days or 0),
                           "financing_fee_fraction": 0., "fx_rate_to_currency": 1., "currency": currency, "fx_basis": "same_currency", "letter_of_credit_fraction": 0.})
        resource_rows.append({**known, "id": f"cap_{sid}", "capacity_by_period": [capacity[sid][0]] * horizon, "failure_domains": [sid]})

    # ── opening stock (latest snapshot at or before the origin) and open orders ──
    if len(inventory):
        snap = inventory[inventory["snapshot_date"] < origin]
        if len(snap):
            latest_day = snap["snapshot_date"].max()
            if (origin - latest_day).days > 14:
                warnings.append(f"latest inventory snapshot is {(origin - latest_day).days} days before the plan date")
            latest = snap[snap["snapshot_date"] == latest_day].drop_duplicates("sku", keep="last")
            for row in latest.itertuples():
                sku = str(row.sku)
                if sku in planned and float(row.on_hand or 0.) > 0:
                    shelf = next(r["shelf_life"] for r in sku_rows if r["id"] == sku)
                    # sector physics: a lot with an expiry date carries its own remaining life (migration 017)
                    expires_in, lot_prov = lot_expiry_periods(getattr(row, "expiry_date", None), origin, period_days, shelf)
                    stock_rows.append({**known, "id": f"open_{sku}", "sku": sku, "location": LOCATION, "quantity": float(row.on_hand), "reserved": 0.,
                                       "damaged": 0., "quarantined": 0., "expires_in": expires_in, "age_periods": 0})
                    if lot_prov == "CUSTOMER_PROVIDED":
                        provenance["stock.expiry"] = "CUSTOMER_PROVIDED"
            provenance["stock.age"] = "NOT_AVAILABLE"
        else:
            warnings.append("no inventory snapshot before the plan date: opening stock is zero")
    else:
        warnings.append("no inventory snapshots uploaded: opening stock is zero")
    pipeline_rows, shipment_rows = [], []
    excluded_future = 0
    if len(pos):
        received_by_po = receipts.groupby("po_id")["qty_received"].sum() if len(receipts) else pd.Series(dtype=float)
        first_receipt = receipts.groupby("po_id")["receipt_date"].min() if len(receipts) else pd.Series(dtype="datetime64[ns]")
        for row in pos.itertuples():
            if row.po_date >= origin:
                excluded_future += 1
                continue
            sku, sid = str(row.sku), str(row.supplier_id)
            if sku not in sourced:
                continue
            ordered = float(row.qty_ordered or 0.)
            received = float(received_by_po.get(row.po_id, 0.))
            first = first_receipt.get(row.po_id)
            arrived = first is not None and not pd.isna(first) and first < origin
            elapsed = int(((first if arrived else origin) - row.po_date).days)
            shipment_rows.append({"known_at": (first if arrived else origin).to_pydatetime().replace(tzinfo=timezone.utc) - timedelta(seconds=1),
                                  "id": f"ship_{row.po_id}", "source": f"src_{sku}", "elapsed_days": max(0, elapsed), "arrived": bool(arrived),
                                  "stage": "received" if arrived else "ordered", "carrier": "unknown",
                                  "accepted_ratio": (min(1., received / ordered) if arrived and ordered > 0 else None)})
            remaining = max(0., ordered - received)
            if not arrived and remaining > 0:
                fit = fits.get(sid, {"fill_mean": ASSUMED_FILL[0], "lead_days": ASSUMED_LEAD_DAYS})
                eta = row.expected_delivery_date if ("expected_delivery_date" in pos and not pd.isna(row.expected_delivery_date)) else row.po_date + pd.Timedelta(days=int(fit["lead_days"]))
                eta = max(pd.Timestamp(eta), origin)
                due_in = max(0, int((pd.Timestamp(eta) - origin).days // period_days))
                net_days = _num(economics.get(f"net_days_{sid}"), None)
                if net_days is None:
                    net_days = _num(economics.get("net_days"), 0.)
                unit_cost = float(_num(getattr(row, "unit_cost", None), None) or next((s["unit_price"] for s in source_rows if s["sku"] == sku), 0.))
                # the frozen contract asks every open order for its "keep" option: what the operator pays
                # and when if the order is left as it is (the only option a workspace can declare)
                keep = {**known, "id": f"keep_{row.po_id}", "action": "keep", "due_in": due_in, "fee_per_unit": 0., "remaining_invoice_per_unit": unit_cost,
                        "payment_due_in": due_in + int((net_days or 0.) // period_days), "max_quantity": remaining,
                        "deadline": known_at + timedelta(days=period_days * horizon), "allowed_stages": ["ordered"], "contract_reference": str(row.po_id)}
                pipeline_rows.append({**known, "id": str(row.po_id), "source": f"src_{sku}", "revision": 1, "ordered": ordered, "confirmed": ordered,
                                      "shipped": received, "received": received, "rejected": 0., "expected_accepted_remaining": remaining * float(fit["fill_mean"]),
                                      "placed_at": row.po_date.to_pydatetime().replace(tzinfo=timezone.utc), "confirmed_at": None, "departed_at": None,
                                      "current_eta": pd.Timestamp(eta).to_pydatetime().replace(tzinfo=timezone.utc), "stage": "ordered", "carrier": "unknown",
                                      "cancellation_status": "none", "prepaid_per_remaining_unit": 0., "allow_split_amendments": False, "options": [keep]})

    # compaction: the engine's supply profile uses quantiles and the recent receipts of each source; the
    # most recent observations per source are enough, the raw purchase-order table stays in the vault
    by_source: dict[str, list[dict[str, Any]]] = {}
    for obs in sorted(shipment_rows, key=lambda r: r["known_at"]):
        by_source.setdefault(obs["source"], []).append(obs)
    shipment_rows = [obs for rows in by_source.values() for obs in rows[-shipment_observations_per_source:]]

    # ── promotions inside the window as demand multipliers ──
    if len(promotions):
        for row in promotions.itertuples():
            sku = str(row.sku)
            offset = int((row.week_start - origin).days // 7)
            uplift = _num(row.uplift, None)
            if sku in planned and 0 <= offset < horizon and uplift and uplift > 0:
                event_rows.append({**known, "id": f"promo_{sku}_{offset}", "service": f"svc_{sku}", "start": offset, "end": offset,
                                   "multiplier": float(uplift), "label": "promotion"})
        provenance["events.promotions"] = "CUSTOMER_PROVIDED"

    payload: dict[str, Any] = {
        "operator_id": operator_id, "as_of": known_at + timedelta(seconds=1), "currency": currency, "period_days": period_days, "horizon": horizon,
        "skus": sku_rows,
        "locations": [{**known, "id": LOCATION, "kind": "warehouse", "capacity_volume": UNBOUNDED, "holding_per_value_period": holding_per_period, "receiving_calendar": CALENDAR}],
        "calendars": [{**known, "id": CALENDAR}],
        "terms": terms_rows, "resources": resource_rows, "sources": source_rows, "stock": stock_rows, "transfers": [], "substitutions": [],
        "customers": [{**known, "id": CUSTOMER, "channel": "wholesale", "priority": 1.}],
        "services": service_rows, "history": history_rows, "events": event_rows, "shipment_history": shipment_rows,
        "pipeline": pipeline_rows, "incumbent_rule": incumbent_rule, "supplier_terms": supplier_terms,
        # sector physics (three-sector engine): profiles from the SKU master's physics columns, the
        # request default from the caller or the single sector the master declares; nothing when absent
        "sector_mode": physics_mode, "sku_physics": physics_rows,
        "liquidity": {**known, "opening_cash": float(opening_cash if opening_cash is not None else UNBOUNDED), "minimum_cash": 0.,
                      "credit_limit": float(_num(economics.get("credit_limit"), UNBOUNDED) or UNBOUNDED), "opening_debt": 0.,
                      "interest_per_period": interest_period, "cost_of_capital_per_period": cost_of_capital_period,
                      "known_receivables": [0.] * horizon, "other_payments": [0.] * horizon},
        # P1 scope: the fitted world itself is the declared stress (cycle-stock economics, not disruption
        # physics); declared disruption stresses travel through the network API payload.
        "stresses": [{"name": "nil", "fill_multiplier": 1., "extra_lead_days": 0, "demand_multiplier": 1., "recovery_period": horizon, "shared_failure": True}],
        "seed": seed, "scenarios": scenarios, "max_solve_seconds": max_solve_seconds, "downside_cost_tolerance": .05, "service_tolerance": .01,
        "evidence_label": "OPERATOR-SHADOW",
        "economics_provenance": {k: v for k, v in provenance.items() if v in ("CUSTOMER_PROVIDED", "INFERRED_FROM_HISTORY", "CONFIGURED_ASSUMPTION", "NOT_AVAILABLE")},
    }
    request = Request.model_validate(payload)
    report = {
        "operator_id": operator_id, "origin_monday": str(origin.date()), "period_days": period_days, "horizon": horizon,
        "rows_read": rows_read,
        "compact": {"skus": len(sku_rows), "sources": len(source_rows), "services": len(service_rows), "history_observations": len(history_rows),
                    "history_weeks": span, "shipment_observations": len(shipment_rows), "open_purchase_orders": len(pipeline_rows),
                    "stock_rows": len(stock_rows), "promotion_events": len(event_rows), "supplier_terms": len(supplier_terms)},
        "fits": fits, "incumbent_rule": {"rule": incumbent_rule, "provenance": rule_prov},
        "provenance": provenance, "economics_keys_used": sorted(k for k in economics if k in economics_prov),
        "leakage_guard": {"history_before": str(origin.date()), "purchase_orders_at_or_after_origin_excluded": excluded_future,
                          "fits_use_closed_orders_before_origin_only": True},
        "warnings": warnings,
    }
    return request, report


def to_purchase_plan(request: Request, report: dict[str, Any], build: dict[str, Any], *, commit_window_weeks: int = 4, run_id: str = "") -> dict[str, Any]:
    """The workspace purchase-plan shape (the /fmcg page contract) from a frozen network report: one row
    per recommended purchase inside the commit window, lots in the SKU's pack unit, the recommendation
    status and reasons as the explanation. Approval stays with the operator."""
    sources = {s.id: s for s in request.sources}
    skus = {s.id: s for s in request.skus}
    orders = []
    total = 0.
    reasons = [str(r) for r in (report.get("reasons") or [])]
    for action in report.get("actions") or []:
        if action.get("action") != "purchase" or action.get("period", 0) >= commit_window_weeks or float(action.get("quantity", 0.)) <= 0:
            continue
        source = sources[action["source"]]
        units = float(action["quantity"])
        lot = source.case_multiple if source.case_multiple > 0 else 1.
        value = units * source.unit_price
        total += value
        orders.append({"sku": source.sku, "supplier_id": source.supplier, "week_offset": int(action["period"]), "order_units": round(units, 2),
                       "lots": round(units / lot, 2), "lot_unit": "case" if source.case_multiple > 0 else "unit", "units_per_lot": lot,
                       "purchase_value": {"amount": f"{value:.2f}", "currency": request.currency},
                       "explanation": [f"planner: {report.get('orchestration', {}).get('planner_owner', 'n/a')}", f"status: {report.get('status')}",
                                       f"selected: {report.get('selected_policy')}", f"terminal value of {skus[source.sku].id}: cycle basis"] + reasons[:3]})
    orch = report.get("orchestration") or {}
    return {"run_id": run_id or str(report.get("input_fingerprint", "")), "mode_run": "canonical_p1", "engine": "zaad.full frozen P1",
            "solver_status": str(report.get("status")), "approval_required": True, "executable_purchase_order": False,
            "warnings": reasons + list(build.get("warnings", [])), "unit": "each", "currency": request.currency, "orders": orders,
            "purchase_value": {"amount": f"{total:.2f}", "currency": request.currency}, "commit_window_weeks": commit_window_weeks,
            "selection_backtest_costs": {}, "planner_owner": orch.get("planner_owner"), "p1_economics": orch.get("p1_economics"),
            "build": {k: build[k] for k in ("origin_monday", "rows_read", "compact", "fits", "incumbent_rule", "provenance", "leakage_guard") if k in build}}
