"""One FreshRetailNet series at one decision origin as a daily-period `zaad.full.contracts.Request`.

The builder is pure: it reads the loaded dataset, never writes, and is deterministic for (series, origin, track,
scenario, declaration). It bypasses the workspace adapter on purpose (that adapter plans weekly periods and needs 16
weeks of history); the frozen planner, replay and settlement are used unchanged through the core contract with
`period_days = 1`.

Information boundary. The history holds exactly the days strictly before the origin, each stamped with the
knowledge rule (23:59:59 UTC of its day), and nothing dated at or after the origin is read from the dataset for the
request: the contract's own integrity validator rejects any stamp after `as_of`, and a test perturbs post-origin
rows to prove the request bytes do not change.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import duckdb
import numpy as np

from zaad.full.contracts import Request
from zaad.public.freshretailnet import recovery
from zaad.public.freshretailnet.declaration import DEFAULT, Declaration

TRACKS = ("observed", "recovered")
MIN_HISTORY_DAYS = 16               # the frozen estimator's floor (zaad/full/forecast.py); the builder refuses below it
BIG = 1e6


@dataclass(frozen=True)
class SeriesDays:
    store_id: int
    product_id: int
    records: list[recovery.DayRecord]             # every loaded day of the series, both splits, ascending

    def before(self, origin: date) -> list[recovery.DayRecord]:
        return [r for r in self.records if r.day < origin]

    def from_(self, origin: date) -> list[recovery.DayRecord]:
        return [r for r in self.records if r.day >= origin]


def load_series(conn: duckdb.DuckDBPyConnection, store_id: int, product_id: int) -> SeriesDays:
    daily = conn.execute("SELECT d, sale_amount FROM frn_daily WHERE store_id = ? AND product_id = ? ORDER BY d", [store_id, product_id]).fetchall()
    hourly = conn.execute("SELECT d, hour, sale, out_of_stock FROM frn_hourly WHERE store_id = ? AND product_id = ? ORDER BY d, hour",
                          [store_id, product_id]).fetchall()
    by_day: dict[date, tuple[np.ndarray, np.ndarray]] = {}
    for d, h, s, o in hourly:
        sales, flags = by_day.setdefault(d, (np.zeros(24), np.zeros(24, dtype=int)))
        sales[h] = s
        flags[h] = o
    records = [recovery.DayRecord(d, float(s), by_day[d][0], by_day[d][1]) for d, s in daily]
    return SeriesDays(store_id, product_id, records)


def knowledge_stamp(day: date) -> datetime:
    """When the observations of `day` become knowable: 23:59:59 UTC of that day (declared rule)."""
    return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)


def demand_inputs(series: SeriesDays, origin: date, track: str, *, history_days: int = DEFAULT.history_days) -> tuple[list[float], dict[str, Any]]:
    """The daily demand history before `origin` for the chosen track (the most recent `history_days` days, oldest first),
    with its provenance record. Recovery (track B) still fits its profile on every pre-origin day."""
    if track not in TRACKS:
        raise ValueError(f"track must be one of {TRACKS}")
    history = series.before(origin)
    if len(history) < MIN_HISTORY_DAYS:
        raise ValueError(f"{len(history)} days before {origin}; the frozen estimator needs {MIN_HISTORY_DAYS}")
    if track == "recovered":
        rec = recovery.recover_series(history, origin=origin)[-history_days:]
        return [r.recovered for r in rec], {"track": "recovered", **recovery.summary(rec)}
    history = history[-history_days:]
    return [r.sales for r in history], {"track": "observed", "evidence": "OBSERVED daily sales (censored on stockout days)"}


def build_request(series: SeriesDays, origin: date, *, track: str, scenario: str, declaration: Declaration = DEFAULT,
                  seed: int = 41001, horizon: int | None = None) -> tuple[Request, dict[str, Any]]:
    """The daily-period request for one series at one origin, plus a provenance record for the result rows."""
    supply = declaration.supply_named(scenario)
    eco = declaration.economics
    H = horizon or declaration.horizon_days
    as_of = datetime.combine(origin, time(0, 0), tzinfo=timezone.utc)
    known = {"known_at": as_of - timedelta(seconds=1)}
    demand, demand_record = demand_inputs(series, origin, track, history_days=declaration.history_days)
    sku, loc = f"p{series.product_id}", f"s{series.store_id}"
    service, source = f"svc_{sku}_{loc}", f"src_{sku}_{loc}"
    mean_demand = float(np.mean(demand))
    opening = eco.opening_cover_days * mean_demand
    history_rows = series.before(origin)[-len(demand):]
    payload: dict[str, Any] = {
        "operator_id": "frn_pilot", "as_of": as_of, "currency": "USD", "period_days": declaration.period_days, "horizon": H,
        "skus": [{**known, "id": sku, "volume": 1., "asset_value": eco.unit_cost, "terminal_value": eco.terminal_value,
                  "shelf_life": eco.shelf_life_days, "disposal_fee": eco.disposal_fee}],
        "locations": [{**known, "id": loc, "kind": "branch", "capacity_volume": None, "holding_per_value_period": eco.holding_per_value_day,
                       "receiving_calendar": "daily"}],
        "calendars": [{**known, "id": "daily"}],
        "terms": [{**known, "id": "immediate", "deposit_fraction": 0., "balance_trigger": "arrival", "net_days": 0, "financing_fee_fraction": 0.,
                   "fx_rate_to_currency": 1., "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}],
        "resources": [{**known, "id": "supplier_cap", "capacity_by_period": [BIG] * H, "failure_domains": ["supplier"]}],
        "sources": [{**known, "id": source, "supplier": "declared_supplier", "sku": sku, "destination": loc, "route": ["declared_supplier", loc],
                     "resources": ["supplier_cap"], "capacity_by_period": [BIG] * H, "unit_price": eco.unit_cost, "freight_per_unit": 0.,
                     "handling_per_unit": 0., "minimum": 0., "multiple": 0., "maximum": BIG, "fixed_order_fee": 0., "terms": "immediate",
                     "order_calendar": "daily", "shipping_calendar": "daily", "lead_days": supply.lead_days, "dispatch_days": 0,
                     "fill_mean": supply.fill_mean, "fill_sd": supply.fill_sd, "lead_sd_days": supply.lead_sd_days, "approved": True,
                     "compliance": "cleared", "quote_expires": as_of + timedelta(days=365), "quote_reference": f"SYNTHETIC:{declaration.version}:{supply.name}"}],
        "stock": ([{**known, "id": "opening_declared", "sku": sku, "location": loc, "quantity": opening, "reserved": 0., "damaged": 0., "quarantined": 0.,
                    "expires_in": eco.shelf_life_days, "age_periods": 0}] if opening > 0 else []),
        "transfers": [], "substitutions": [],
        "customers": [{**known, "id": "retail", "channel": "retail", "priority": 1.}],
        "services": [{**known, "id": service, "sku": sku, "location": loc, "customer": "retail", "target": eco.service_target,
                      "selling_price": eco.selling_price, "sla_per_unmet": eco.sla_per_unmet}],
        "history": [{"known_at": knowledge_stamp(r.day), "service": service, "period": -len(demand) + i, "quantity": q}
                    for i, (r, q) in enumerate(zip(history_rows, demand))],
        "pipeline": [],
        "liquidity": {**known, "opening_cash": BIG, "minimum_cash": 0., "credit_limit": 0., "opening_debt": 0., "interest_per_period": 0.,
                      "known_receivables": [0.] * H, "other_payments": [0.] * H},
        "stresses": [{**declaration.stress, "recovery_period": H}],
        "seed": seed, "scenarios": declaration.scenarios, "max_solve_seconds": declaration.max_solve_seconds,
        "downside_cost_tolerance": .05, "service_tolerance": .01, "evidence_label": "SYNTHETIC",
    }
    req = Request.model_validate(payload)
    record = {"store_id": series.store_id, "product_id": series.product_id, "origin": origin.isoformat(), "track": track, "scenario": scenario,
              "declaration_version": declaration.version, "declaration_hash": declaration.hash(), "history_days": len(demand),
              "mean_history_demand": mean_demand, "opening_stock": opening, "demand": demand_record,
              "evidence": {"demand_history": demand_record["evidence"] if "evidence" in demand_record else "DERIVED (recovered)",
                           "opening_stock": "SYNTHETIC (declared cover x DERIVED mean)", "supply": "SYNTHETIC", "economics": "SYNTHETIC",
                           "evidence_label_on_request": "SYNTHETIC (the contract's label vocabulary; demand is public observed data)"}}
    return req, record
