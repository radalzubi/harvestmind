"""One M5 store-item series at one Saturday origin as a weekly-period `zaad.full.contracts.Request` (Experiment A)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import duckdb
import numpy as np

from zaad.full.contracts import Request
from zaad.public.m5.declaration import DEFAULT, Declaration
from zaad.public.m5.selection import week_start

MIN_HISTORY_WEEKS = 16
MILLION = 1e6


@dataclass(frozen=True)
class WeekRecord:
    start: date                 # Saturday
    end: date                   # Friday
    sales: float                # OBSERVED weekly units
    price: float | None         # OBSERVED shelf price for the Walmart week (None when not listed)


@dataclass(frozen=True)
class SeriesWeeks:
    id: str
    item_id: str
    store_id: str
    dept_id: str
    cat_id: str
    weeks: list[WeekRecord]      # ascending, full Walmart weeks only

    def before(self, origin: date) -> list[WeekRecord]:
        return [w for w in self.weeks if w.end < origin]

    def from_(self, origin: date) -> list[WeekRecord]:
        return [w for w in self.weeks if w.start >= origin]

    def price_at(self, origin: date) -> float | None:
        """The shelf price knowable at `origin`: the origin week's price (set at the week start), else the last known."""
        current = next((w.price for w in self.weeks if w.start == origin), None)
        if current is not None:
            return current
        known = [w.price for w in self.before(origin) if w.price is not None]
        return known[-1] if known else None


def load_series(conn: duckdb.DuckDBPyConnection, series_id: str) -> SeriesWeeks:
    meta = conn.execute("SELECT item_id, store_id, dept_id, cat_id FROM m5_daily WHERE id = ? LIMIT 1", [series_id]).fetchone()
    if meta is None:
        raise KeyError(series_id)
    item, store, dept, cat = meta
    rows = conn.execute("""SELECT c.wm_yr_wk, min(m.d), max(m.d), count(*), sum(m.qty), any_value(p.sell_price)
                           FROM m5_daily m JOIN m5_calendar c USING (d)
                           LEFT JOIN m5_prices p ON p.store_id = m.store_id AND p.item_id = m.item_id AND p.wm_yr_wk = c.wm_yr_wk
                           WHERE m.id = ? GROUP BY c.wm_yr_wk HAVING count(*) = 7 ORDER BY c.wm_yr_wk""", [series_id]).fetchall()
    weeks = [WeekRecord(start, end, float(q), (float(price) if price is not None else None)) for _, start, end, n, q, price in rows]
    for w in weeks:
        if w.start != week_start(w.start) or (w.end - w.start).days != 6:
            raise ValueError(f"{series_id}: week {w.start}..{w.end} is not a full Saturday-to-Friday Walmart week")
    return SeriesWeeks(series_id, item, store, dept, cat, weeks)


def knowledge_stamp(week: WeekRecord) -> datetime:
    return datetime.combine(week.end, time(23, 59, 59), tzinfo=timezone.utc)


def build_request(series: SeriesWeeks, origin: date, *, scenario: str, declaration: Declaration = DEFAULT, seed: int = 41001,
                  horizon: int | None = None) -> tuple[Request, dict[str, Any]]:
    if origin != week_start(origin):
        raise ValueError(f"{origin} is not a Saturday (Walmart week start)")
    supply = declaration.supply_named(scenario)
    eco = declaration.economics
    H = horizon or declaration.horizon_weeks
    history = series.before(origin)[-declaration.history_weeks:]
    if len(history) < MIN_HISTORY_WEEKS:
        raise ValueError(f"{len(history)} weeks before {origin}; the estimator needs {MIN_HISTORY_WEEKS}")
    if any(w.end >= origin for w in history):
        raise AssertionError("history leaks the origin")
    price = series.price_at(origin)
    if price is None:
        raise ValueError(f"{series.id}: no shelf price knowable at {origin}")
    unit_cost = price * (1. - eco.margin_fraction)
    demand = [w.sales for w in history]
    mean_weekly = float(np.mean(demand))
    opening = eco.opening_cover_weeks * mean_weekly
    cap = max(eco.line_capacity_floor, eco.line_capacity_multiple * mean_weekly)
    as_of = datetime.combine(origin, time(0, 0), tzinfo=timezone.utc)
    known = {"known_at": as_of - timedelta(seconds=1)}
    sku, loc = series.item_id, series.store_id
    service, source = f"svc_{sku}_{loc}", f"src_{sku}_{loc}"
    cash = None if eco.cash_weeks is None else eco.cash_weeks * mean_weekly * unit_cost
    payload: dict[str, Any] = {
        "operator_id": "m5_pilot", "as_of": as_of, "currency": "USD", "period_days": declaration.period_days, "horizon": H,
        "skus": [{**known, "id": sku, "volume": 1., "asset_value": unit_cost, "terminal_value": unit_cost * eco.salvage_fraction,
                  "shelf_life": eco.shelf_life_weeks, "disposal_fee": unit_cost * eco.disposal_fee_fraction}],
        "locations": [{**known, "id": loc, "kind": "branch", "capacity_volume": None, "holding_per_value_period": eco.holding_per_value_week, "receiving_calendar": "daily"}],
        "calendars": [{**known, "id": "daily"}],
        "terms": [{**known, "id": "immediate", "deposit_fraction": 0., "balance_trigger": "arrival", "net_days": 0, "financing_fee_fraction": 0.,
                   "fx_rate_to_currency": 1., "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}],
        "resources": [{**known, "id": "supplier_cap", "capacity_by_period": [cap] * H, "failure_domains": ["supplier"]}],
        "sources": [{**known, "id": source, "supplier": "declared_supplier", "sku": sku, "destination": loc, "route": ["declared_supplier", loc],
                     "resources": ["supplier_cap"], "capacity_by_period": [cap] * H, "unit_price": unit_cost, "freight_per_unit": 0., "handling_per_unit": 0.,
                     "minimum": 0., "multiple": eco.order_multiple, "maximum": cap, "fixed_order_fee": 0., "terms": "immediate", "order_calendar": "daily",
                     "shipping_calendar": "daily", "lead_days": supply.lead_days, "dispatch_days": 0, "fill_mean": supply.fill_mean, "fill_sd": supply.fill_sd,
                     "lead_sd_days": supply.lead_sd_days, "approved": True, "compliance": "cleared", "quote_expires": as_of + timedelta(days=365),
                     "quote_reference": f"SYNTHETIC:{declaration.version}:{supply.name}"}],
        "stock": ([{**known, "id": "opening_declared", "sku": sku, "location": loc, "quantity": opening, "reserved": 0., "damaged": 0., "quarantined": 0.,
                    "expires_in": eco.shelf_life_weeks, "age_periods": 0}] if opening > 0 else []),
        "transfers": [], "substitutions": [],
        "customers": [{**known, "id": "retail", "channel": "retail", "priority": 1.}],
        "services": [{**known, "id": service, "sku": sku, "location": loc, "customer": "retail", "target": eco.service_target, "selling_price": price,
                      "sla_per_unmet": eco.sla_per_unmet}],
        "history": [{"known_at": knowledge_stamp(w), "service": service, "period": -len(demand) + i, "quantity": q} for i, (w, q) in enumerate(zip(history, demand))],
        "pipeline": [],
        "liquidity": {**known, "opening_cash": cash, "minimum_cash": 0., "credit_limit": 0. if cash is not None else None, "opening_debt": 0.,
                      "interest_per_period": 0., "cost_of_capital_per_period": eco.cost_of_capital_annual / 52. if cash is not None else 0.,
                      "known_receivables": [0.] * H, "other_payments": [0.] * H},
        "stresses": [{**declaration.stress, "recovery_period": H}],
        "seed": seed, "scenarios": declaration.scenarios, "max_solve_seconds": declaration.max_solve_seconds, "downside_cost_tolerance": .05,
        "service_tolerance": .01, "evidence_label": "SYNTHETIC", "incumbent_rule": declaration.zaad_incumbent_rule,
    }
    req = Request.model_validate(payload)
    record = {"series_id": series.id, "item_id": sku, "store_id": loc, "dept_id": series.dept_id, "cat_id": series.cat_id, "origin": origin.isoformat(),
              "scenario": scenario, "declaration_version": declaration.version, "declaration_hash": declaration.hash(), "history_weeks": len(demand),
              "mean_weekly_demand": mean_weekly, "price_at_origin": price, "unit_cost": unit_cost, "opening_stock": opening, "line_capacity": cap,
              "opening_cash": cash, "incumbent_rule": declaration.zaad_incumbent_rule,
              "evidence": {"demand_history": "OBSERVED weekly unit sales", "price": "OBSERVED", "unit_cost": "DERIVED (price x declared margin)",
                           "opening_stock": "SYNTHETIC", "supply": "SYNTHETIC", "economics": "SYNTHETIC"}}
    return req, record
