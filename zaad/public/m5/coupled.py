"""Experiment B: coupled purchasing commitments. Several M5 items of one store buy from one declared supplier whose
terms couple them: a fixed cost per supplier order, a minimum order value, a pallet load cap shared by every line, case
multiples and minimum quantities per line, and a working-capital budget. All of it is SYNTHETIC and identical across
policies; nothing here was observed at Walmart. Demand per item is OBSERVED weekly sales.

The coupling uses engine constructs the rule baselines already respect in `policies.baseline_plan` (minimum order value,
pallet load cap, cash cap, lot rounding), so a projected rule is a competent constraint-aware comparator rather than a
rule that ignores the constraints and fails physically. The model enforces the same rows (`model.py` supplier-order
economics) and the settlement re-checks them, so a policy that breaches a cap is reported as a physical failure.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from typing import Any

import numpy as np

from zaad.full.contracts import Request
from zaad.full.worlds import World, draw
from zaad.public.m5.declaration import DEFAULT as WEEKLY_DEFAULT, SupplyScenario
from zaad.public.m5.request_builder import MIN_HISTORY_WEEKS, SeriesWeeks, knowledge_stamp
from zaad.public.m5.selection import week_start

COUPLED_VERSION = "m5-coupled-declaration-1"


@dataclass(frozen=True)
class Coupling:
    """The supplier relationship declared for one store group (SYNTHETIC)."""
    fixed_order_cost: float = 40.0             # dollars per supplier order-week (any line placed)
    mov_weeks: float = 0.5                     # minimum order value = this many weeks of the group's mean purchase value
    pallet_weeks: float = 1.5                  # a pallet holds this many weeks of an item's mean demand, in whole cases
    pallets_cap: int = 6                       # the truck: pallets per order-week, shared by every line of the group
    #: the engine's rule projections lift an order to the minimum order value and THEN scale it to the pallet cap, so when both
    #: bind at once the projection breaches its own MOV and the settlement records a physical failure (a limitation of the
    #: conventional projection, reported); the primary configuration keeps the two from binding together, `coupled_tight` does not
    case_multiple: float = 6.0                 # units per case, every line
    minimum_cases: float = 2.0                 # minimum order per line, in cases
    cash_weeks: float | None = None            # working-capital budget in weeks of group mean purchases; None = unconstrained (primary configuration)
    credit_weeks: float = 0.0                  # credit line in weeks of group mean purchases, used only with a cash budget
    margin_fraction: float = 0.30
    holding_annual: float = 0.25
    cost_of_capital_annual: float = 0.10
    salvage_fraction: float = 0.80
    shelf_life_weeks: int = 26
    opening_cover_weeks: float = 2.0
    service_target: float = 0.95
    line_capacity_multiple: float = 20.0
    zaad_incumbent_rule: str | None = "economic_lot"
    horizon_weeks: int = 8
    history_weeks: int = 52
    max_group: int = 6
    scenarios: int = 3
    max_solve_seconds: float = 40.0

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


DEFAULT = Coupling()
VARIANTS: dict[str, Coupling] = {
    "coupled": DEFAULT,                                                                  # pallet cap, MOV, fixed order cost, cases, MOQ; no cash budget
    "coupled_no_incumbent": replace(DEFAULT, zaad_incumbent_rule=None),
    "coupled_cash": replace(DEFAULT, cash_weeks=4.0, credit_weeks=1.0),                 # + working-capital budget with a one-week credit line
    "coupled_tight": replace(DEFAULT, pallets_cap=4, mov_weeks=1.0),
}
SUPPLY = {s.name: s for s in WEEKLY_DEFAULT.supply}


def groups(manifest_series: list[dict[str, Any]], *, max_group: int = DEFAULT.max_group) -> list[list[str]]:
    """Store groups from the frozen selection: the selected items of one store, at most `max_group`, in manifest order."""
    by_store: dict[str, list[str]] = {}
    for r in manifest_series:
        by_store.setdefault(r["store_id"], []).append(r["id"])
    return [ids[:max_group] for store, ids in sorted(by_store.items()) if len(ids) >= 2]


def build_group_request(series: list[SeriesWeeks], origin: date, *, scenario: str, coupling: Coupling = DEFAULT, seed: int = 41001) -> tuple[Request, dict[str, Any]]:
    if origin != week_start(origin):
        raise ValueError(f"{origin} is not a Saturday")
    supply: SupplyScenario = SUPPLY[scenario]
    H = coupling.horizon_weeks
    as_of = datetime.combine(origin, time(0, 0), tzinfo=timezone.utc)
    known = {"known_at": as_of - timedelta(seconds=1)}
    store = series[0].store_id
    if any(s.store_id != store for s in series):
        raise ValueError("a coupled group is one store")
    skus, sources, services, history, stock, upp, record_items, dropped = [], [], [], [], [], {}, [], []
    line_caps: list[float] = []
    weekly_rate = (coupling.holding_annual + coupling.cost_of_capital_annual) / 52.
    group_value = 0.
    usable = []
    for s in series:
        hist = s.before(origin)[-coupling.history_weeks:]
        price = s.price_at(origin)
        if len(hist) < MIN_HISTORY_WEEKS or price is None or sum(w.sales for w in hist) <= 0:
            dropped.append({"series_id": s.id, "reason": f"{len(hist)} weeks of history" if len(hist) < MIN_HISTORY_WEEKS
                            else f"not listed (no price) at {origin}" if price is None else f"no sales in the history before {origin}"})
            continue
        usable.append(s)
    if len(usable) < 2:
        raise ValueError(f"group has {len(usable)} usable items at {origin} (need 2): {dropped}")
    series = usable
    for s in series:
        hist = s.before(origin)[-coupling.history_weeks:]
        price = s.price_at(origin)
        assert price is not None
        cost = price * (1 - coupling.margin_fraction)
        demand = [w.sales for w in hist]
        mean = float(np.mean(demand))
        group_value += mean * cost
        cap = max(20., coupling.line_capacity_multiple * mean)
        case = coupling.case_multiple
        sku, src, svc = s.item_id, f"src_{s.item_id}_{store}", f"svc_{s.item_id}_{store}"
        skus.append({**known, "id": sku, "volume": 1., "asset_value": cost, "terminal_value": cost * coupling.salvage_fraction, "shelf_life": coupling.shelf_life_weeks, "disposal_fee": 0.})
        sources.append({**known, "id": src, "supplier": "declared_supplier", "sku": sku, "destination": store, "route": ["declared_supplier", store], "resources": ["supplier_cap"],
                        "capacity_by_period": [cap] * H, "unit_price": cost, "freight_per_unit": 0., "handling_per_unit": 0., "minimum": coupling.minimum_cases * case,
                        "multiple": case, "case_multiple": case, "maximum": cap, "fixed_order_fee": 0., "terms": "on_order", "order_calendar": "daily", "shipping_calendar": "daily",
                        "lead_days": supply.lead_days, "dispatch_days": 0, "fill_mean": supply.fill_mean, "fill_sd": supply.fill_sd, "lead_sd_days": supply.lead_sd_days,
                        "approved": True, "compliance": "cleared", "quote_expires": as_of + timedelta(days=365), "quote_reference": f"SYNTHETIC:{COUPLED_VERSION}:{supply.name}"})
        services.append({**known, "id": svc, "sku": sku, "location": store, "customer": "retail", "target": coupling.service_target, "selling_price": price, "sla_per_unmet": 0.})
        history += [{"known_at": knowledge_stamp(w), "service": svc, "period": -len(demand) + i, "quantity": q} for i, (w, q) in enumerate(zip(hist, demand))]
        opening = coupling.opening_cover_weeks * mean
        if opening > 0:
            stock.append({**known, "id": f"opening_{sku}", "sku": sku, "location": store, "quantity": opening, "reserved": 0., "damaged": 0., "quarantined": 0.,
                          "expires_in": coupling.shelf_life_weeks, "age_periods": 0})
        # a pallet holds `pallet_weeks` weeks of this item's mean demand, rounded up to whole cases; the supplier's truck carries
        # `pallets_cap` pallets per order-week for the whole group, so the cap binds when several lines order together
        upp[sku] = max(case, float(np.ceil(coupling.pallet_weeks * mean / case)) * case)
        line_caps.append(float(cap))
        record_items.append({"series_id": s.id, "item_id": sku, "mean_weekly_demand": mean, "price_at_origin": price, "unit_cost": cost, "opening_stock": opening, "line_capacity": cap, "units_per_pallet": upp[sku]})
    cash = None if coupling.cash_weeks is None else coupling.cash_weeks * group_value
    total_line_capacity = float(sum(line_caps))
    payload: dict[str, Any] = {
        "operator_id": "m5_coupled", "as_of": as_of, "currency": "USD", "period_days": 7, "horizon": H,
        "skus": skus, "locations": [{**known, "id": store, "kind": "branch", "capacity_volume": None, "holding_per_value_period": weekly_rate, "receiving_calendar": "daily"}],
        "calendars": [{**known, "id": "daily"}],
        # payment on order: the working-capital budget then binds at the moment of commitment, which is what the projected rules' cash
        # cap models; payment on arrival would create post-horizon obligations the settlement's terminal-solvency check rejects for
        # every policy (the first coupled smoke run) while the rules cannot see that row
        "terms": [{**known, "id": "on_order", "deposit_fraction": 0., "balance_trigger": "order", "net_days": 0, "financing_fee_fraction": 0., "fx_rate_to_currency": 1.,
                   "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}],
        # the contract needs a capacity resource per source; the shared binding constraint is the pallet cap in supplier_terms, so this
        # resource is the sum of the finite line caps (never a sentinel)
        "resources": [{**known, "id": "supplier_cap", "capacity_by_period": [total_line_capacity] * H, "failure_domains": ["supplier"]}],
        "sources": sources, "stock": stock, "transfers": [], "substitutions": [],
        "customers": [{**known, "id": "retail", "channel": "retail", "priority": 1.}], "services": services, "history": history, "pipeline": [],
        "supplier_terms": [{**known, "id": "declared_supplier_terms", "supplier": "declared_supplier", "minimum_order_value": coupling.mov_weeks * group_value,
                            "fixed_order_cost": coupling.fixed_order_cost, "units_per_pallet": upp, "max_pallets": float(coupling.pallets_cap),
                            "provenance": {}}],
        "liquidity": {**known, "opening_cash": cash, "minimum_cash": 0., "credit_limit": (coupling.credit_weeks * group_value) if cash is not None else None, "opening_debt": 0., "interest_per_period": 0.,
                      "cost_of_capital_per_period": coupling.cost_of_capital_annual / 52. if cash is not None else 0., "known_receivables": [0.] * H, "other_payments": [0.] * H},
        "stresses": [{"name": "declared_tail", "fill_multiplier": 0.9, "extra_lead_days": 7, "demand_multiplier": 1.1, "recovery_period": H, "shared_failure": True}],
        "seed": seed, "scenarios": coupling.scenarios, "max_solve_seconds": coupling.max_solve_seconds, "downside_cost_tolerance": .05, "service_tolerance": .01,
        "evidence_label": "SYNTHETIC", "incumbent_rule": coupling.zaad_incumbent_rule,
    }
    req = Request.model_validate(payload)
    record = {"store_id": store, "items": record_items, "group_size": len(series), "dropped_items": dropped, "origin": origin.isoformat(), "scenario": scenario, "coupling_version": COUPLED_VERSION,
              "coupling_hash": coupling.hash(), "minimum_order_value": coupling.mov_weeks * group_value, "fixed_order_cost": coupling.fixed_order_cost,
              "max_pallets": coupling.pallets_cap, "opening_cash": cash, "incumbent_rule": coupling.zaad_incumbent_rule,
              "evidence": {"demand": "OBSERVED weekly sales per item", "prices": "OBSERVED", "supplier_terms_capacity_budget_lots": "SYNTHETIC, identical for every policy"}}
    return req, record


def truth_world(req: Request, series: list[SeriesWeeks], origin: date, *, periods: int, seed: int) -> tuple[World, dict[str, Any]]:
    long = req.model_copy(update={"horizon": periods,
                                  "sources": tuple(s.model_copy(update={"capacity_by_period": tuple([s.capacity_by_period[0]] * periods)}) for s in req.sources),
                                  "resources": tuple(r.model_copy(update={"capacity_by_period": tuple([r.capacity_by_period[0]] * periods)}) for r in req.resources),
                                  "liquidity": req.liquidity.model_copy(update={"known_receivables": tuple([0.] * periods), "other_payments": tuple([0.] * periods)}),
                                  "stresses": tuple(s.model_copy(update={"recovery_period": periods}) for s in req.stresses)})
    drawn = draw(long, seed, 1)[0]
    demand = {}
    present = {svc.id for svc in req.services}
    for s in [x for x in series if f"svc_{x.item_id}_{x.store_id}" in present]:
        future = s.from_(origin)[:periods]
        if len(future) < periods:
            raise ValueError(f"{s.id}: only {len(future)} weeks from {origin}")
        demand[f"svc_{s.item_id}_{s.store_id}"] = tuple(float(w.sales) for w in future)
    world = replace(drawn, name=f"truth-coupled-{origin.isoformat()}", weight=1., demand=demand)
    return world, {"track": "observed", "periods": periods, "supply_seed": seed, "arrival_offsets": sorted({world.arrival[k] - k[1] for k in world.arrival}),
                   "fill_min": min(world.fills.values()), "supply_evidence": "SYNTHETIC draw from the declaration, shared by every policy"}


def coupling_record(coupling: Coupling) -> dict[str, Any]:
    return {**asdict(coupling), "version": COUPLED_VERSION, "hash": coupling.hash(), "supply_scenarios": {k: asdict(v) for k, v in SUPPLY.items()}}

