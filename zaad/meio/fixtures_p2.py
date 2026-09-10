"""P2 development fixtures: one central location fed by a supplier and N branches fed by lanes,
with every economic and physical input declared as a CONFIGURED_ASSUMPTION. Development fixtures,
not customer economics; they exist to expose each network mechanism (pooling, correlation, transfer
lead / cost / capacity / pack, scarcity and allocation, shared supply, recovery) in isolation.

The single-branch degenerate form (`branches=("branch",)`, no lanes, the supplier delivering to the
branch) is byte-identical in structure to the P1 fixture builder and is used by the identity tests."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from zaad.full.contracts import Request
from zaad.full.fixtures_p1 import NOW, annual_to_period


def _history(demand: float, sd_hint: float, phase: int, weeks: int = 52) -> list[float]:
    """A deterministic, phase-shifted pseudo-random history around `demand` (no RNG; reproducible)."""
    return [max(0., demand * (1 + sd_hint * ((((t + phase) * 7919) % 11) - 5) / 5.)) for t in range(-weeks, 0)]


def p2_request(*, branches: tuple[str, ...] = ("north", "south"), horizon: int = 12, period_days: int = 7,
               demand: dict[str, float] | float = 100., demand_sd_hint: float = .15, target: dict[str, float] | float = .95,
               priority: dict[str, float] | float = 1., unit_price: float = 5., holding_per_year: float = .15,
               central_holding_per_year: float | None = None, cost_of_capital_per_year: float = 0.,
               opening_central: float = 300., opening_branch: dict[str, float] | float = 150.,
               supplier_lead_days: int = 7, supplier_fill: float = .98, supplier_fill_sd: float = .01, supplier_capacity: float = 1e6,
               minimum: float = 0., multiple: float = 0., fixed_order_cost: float = 0.,
               lane_lead_periods: dict[str, int] | int = 1, lane_cost: dict[str, float] | float = .2, lane_capacity: dict[str, float] | float = 1e6,
               lane_multiple: dict[str, float] | float = 0., lane_fixed_cost: dict[str, float] | float = 0., lane_loss: float = 0.,
               extra_lanes: list[dict[str, Any]] | None = None, local_sources: dict[str, dict[str, Any]] | None = None,
               demand_correlation: float = 0., stresses: str = "none", incumbent_rule: str | None = "network:rop",
               pipeline: list[dict] | None = None, inbound_transfers: list[dict] | None = None,
               seed: int = 41001, scenarios: int = 3, max_solve_seconds: float = 15., extra: dict[str, Any] | None = None) -> Request:
    def per_branch(value, default=None):
        return {b: (value[b] if isinstance(value, dict) else value) for b in branches} if value is not None else {b: default for b in branches}
    demand_b, target_b, priority_b = per_branch(demand), per_branch(target), per_branch(priority)
    opening_b, lead_b, cost_b = per_branch(opening_branch), per_branch(lane_lead_periods), per_branch(lane_cost)
    cap_b, mult_b, fixed_b = per_branch(lane_capacity), per_branch(lane_multiple), per_branch(lane_fixed_cost)
    known = {"known_at": NOW - timedelta(days=1)}
    H = horizon
    central = "central"
    single = len(branches) == 1 and branches[0] == "branch" and opening_central == 0 and extra is not None and extra.get("_single_node")
    locations = [] if single else [{**known, "id": central, "kind": "central_dc", "capacity_volume": 1e6,
                                    "holding_per_value_period": annual_to_period(central_holding_per_year if central_holding_per_year is not None else holding_per_year, period_days),
                                    "receiving_calendar": "always"}]
    for b in branches:
        locations.append({**known, "id": b, "kind": "branch", "capacity_volume": 1e6,
                          "holding_per_value_period": annual_to_period(holding_per_year, period_days), "receiving_calendar": "always"})
    supply_to = branches[0] if single else central
    sources: list[dict[str, Any]] = [{**known, "id": "src_A", "supplier": "supplier", "sku": "A", "destination": supply_to,
                                      "route": ["supplier", supply_to], "resources": ["supplier_cap"], "capacity_by_period": [supplier_capacity] * H,
                                      "unit_price": unit_price, "freight_per_unit": 0., "handling_per_unit": 0., "minimum": minimum, "multiple": multiple,
                                      "maximum": 1e6, "fixed_order_fee": 0., "terms": "terms", "order_calendar": "always", "shipping_calendar": "always",
                                      "lead_days": supplier_lead_days, "dispatch_days": 0, "fill_mean": supplier_fill, "fill_sd": supplier_fill_sd,
                                      "lead_sd_days": 0., "approved": True, "compliance": "cleared", "quote_expires": NOW + timedelta(days=730),
                                      "quote_reference": "p2-fixture"}]
    resources = [{**known, "id": "supplier_cap", "capacity_by_period": [supplier_capacity] * H, "failure_domains": ["supplier"]}]
    for b, spec in (local_sources or {}).items():
        sources.append({**sources[0], "id": f"src_A_{b}", "supplier": spec.get("supplier", f"local_{b}"), "destination": b, "route": [spec.get("supplier", f"local_{b}"), b],
                        "resources": [f"local_cap_{b}"], "unit_price": unit_price * (1 + spec.get("price_premium", .1)),
                        "lead_days": spec.get("lead_days", supplier_lead_days), "minimum": spec.get("minimum", 0.), "multiple": spec.get("multiple", 0.),
                        "capacity_by_period": [spec.get("capacity", 1e6)] * H, "fill_mean": spec.get("fill", supplier_fill)})
        resources.append({**known, "id": f"local_cap_{b}", "capacity_by_period": [spec.get("capacity", 1e6)] * H, "failure_domains": [f"local_{b}"]})
    transfers: list[dict[str, Any]] = []
    if not single:
        for b in branches:
            transfers.append({**known, "id": f"lane_{b}", "sku": "A", "origin": central, "destination": b, "lead_periods": int(lead_b[b]),
                              "capacity": float(cap_b[b]), "cost_per_unit": float(cost_b[b]), "loss_fraction": lane_loss, "approved": True,
                              "multiple": float(mult_b[b]), "fixed_cost_per_dispatch": float(fixed_b[b])})
        for lane in extra_lanes or []:
            transfers.append({**known, "sku": "A", "loss_fraction": lane_loss, "approved": True, "multiple": 0., "fixed_cost_per_dispatch": 0., **lane})
    stock: list[dict[str, Any]] = []
    if not single and opening_central > 0:
        stock.append({**known, "id": "open_central", "sku": "A", "location": central, "quantity": opening_central, "reserved": 0., "damaged": 0.,
                      "quarantined": 0., "expires_in": 52, "age_periods": 1})
    customers, services, history = [], [], []
    for n, b in enumerate(branches):
        if opening_b[b] > 0:
            stock.append({**known, "id": f"open_{b}", "sku": "A", "location": b, "quantity": opening_b[b], "reserved": 0., "damaged": 0.,
                          "quarantined": 0., "expires_in": 52, "age_periods": 1})
        customers.append({**known, "id": f"customer_{b}", "channel": "retail", "priority": float(priority_b[b])})
        services.append({**known, "id": f"svc_{b}", "sku": "A", "location": b, "customer": f"customer_{b}", "target": float(target_b[b]),
                         "selling_price": unit_price * 2, "sla_per_unmet": unit_price * .5})
        for t, q in zip(range(-52, 0), _history(float(demand_b[b]), demand_sd_hint, phase=3 * n)):
            history.append({**known, "service": f"svc_{b}", "period": t, "quantity": q})
    payload: dict[str, Any] = {
        "operator_id": "p2_fixture", "as_of": NOW, "currency": "USD", "period_days": period_days, "horizon": H,
        "skus": [{**known, "id": "A", "volume": 1., "asset_value": unit_price, "terminal_value": unit_price * .8, "shelf_life": 52, "disposal_fee": 0.}],
        "locations": locations,
        "calendars": [{**known, "id": "always"}],
        "terms": [{**known, "id": "terms", "deposit_fraction": 0., "balance_trigger": "arrival", "net_days": 0, "financing_fee_fraction": 0.,
                   "fx_rate_to_currency": 1., "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}],
        "resources": resources, "sources": sources, "stock": stock, "transfers": transfers, "substitutions": [],
        "customers": customers, "services": services, "history": history, "pipeline": pipeline or [], "inbound_transfers": inbound_transfers or [],
        "liquidity": {**known, "opening_cash": 1e6, "minimum_cash": 0., "credit_limit": 1e6, "opening_debt": 0.,
                      "interest_per_period": annual_to_period(.10, period_days),
                      "cost_of_capital_per_period": annual_to_period(cost_of_capital_per_year, period_days),
                      "known_receivables": [0.] * H, "other_payments": [0.] * H},
        "stresses": {"none": [{"name": "nil", "fill_multiplier": 1., "extra_lead_days": 0, "demand_multiplier": 1., "recovery_period": H, "shared_failure": True}],
                     "severe": [{"name": "shared_supplier_disruption", "fill_multiplier": .6, "extra_lead_days": 14, "demand_multiplier": 1., "recovery_period": 6, "shared_failure": True}],
                     "demand_shock": [{"name": "demand_surge", "fill_multiplier": 1., "extra_lead_days": 0, "demand_multiplier": 1.5, "recovery_period": 4, "shared_failure": True}]}[stresses],
        "incumbent_rule": incumbent_rule,
        "demand_correlation": demand_correlation,
        "order_smoothing": 0.,
        "materiality_cost_fraction": .01, "materiality_inventory_fraction": .05, "materiality_service": .005,
        "timing_tiebreak": 1e-4, "stratified_scenarios": True, "analytic_shortage": True,
        "seed": seed, "scenarios": scenarios, "max_solve_seconds": max_solve_seconds, "downside_cost_tolerance": .05, "service_tolerance": .01,
        "evidence_label": "SYNTHETIC",
        "economics_provenance": {**{f"location.{loc['id']}.holding_per_value_period": "CONFIGURED_ASSUMPTION" for loc in locations},
                                 **{f"transfer.{a['id']}.cost_per_unit": "CONFIGURED_ASSUMPTION" for a in transfers},
                                 "liquidity.cost_of_capital_per_period": "CONFIGURED_ASSUMPTION" if cost_of_capital_per_year else "NOT_AVAILABLE"},
    }
    if fixed_order_cost:
        payload["supplier_terms"] = [{**known, "id": "supplier_terms", "supplier": "supplier", "fixed_order_cost": fixed_order_cost,
                                      "provenance": {"fixed_order_cost": "CONFIGURED_ASSUMPTION"}}]
    if extra:
        payload.update({k: v for k, v in extra.items() if not k.startswith("_")})
    return Request.model_validate(payload)
