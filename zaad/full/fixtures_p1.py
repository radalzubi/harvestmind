"""P1 development fixtures: one branch, one supplier, one or two SKUs, with every commercial term
explicit and every assumption labelled CONFIGURED_ASSUMPTION. These are development fixtures, not
customer economics; they exist to expose each purchasing mechanism in isolation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from zaad.full.contracts import Request

NOW = datetime(2026, 9, 7, tzinfo=timezone.utc)   # a Monday


def annual_to_period(rate_per_year: float, period_days: int) -> float:
    """Annual rate to a per-period rate, the only conversion fixtures use."""
    return rate_per_year * period_days / 365.


def p1_request(*, horizon: int = 12, period_days: int = 7, demand: float = 100., demand_sd_hint: float = .1,
               skus: tuple[str, ...] = ("A",), unit_price: float = 5., opening_units: float = 150.,
               minimum: float = 0., multiple: float = 0., case_multiple: float = 0., pallet_multiple: float = 0.,
               fixed_order_fee: float = 0., freight_per_unit: float = 0., handling_per_unit: float = 0.,
               lead_days: int = 7, order_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6), ship_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
               holding_per_year: float = .15, cost_of_capital_per_year: float = 0., interest_per_year: float = .10,
               deposit_fraction: float = 0., balance_trigger: str = "arrival", net_days: int = 0,
               capacity_volume: float = 1e6, opening_cash: float = 1e6, credit_limit: float = 1e6, receivables_per_period: float = 0.,
               supplier_terms: dict[str, Any] | None = None, pipeline: list[dict] | None = None,
               incumbent_orders: list[dict] | None = None, target: float = .95, seed: int = 41001, scenarios: int = 3,
               max_solve_seconds: float = 15., stresses: str = "none", incumbent_rule: str | None = None,
               extra: dict[str, Any] | None = None) -> Request:
    known = {"known_at": NOW - timedelta(days=1)}
    H = horizon
    sources, skus_rows, services, history, stock = [], [], [], [], []
    for sku in skus:
        skus_rows.append({**known, "id": sku, "volume": 1., "asset_value": unit_price, "terminal_value": unit_price * .8, "shelf_life": 52, "disposal_fee": 0.})
        sources.append({**known, "id": f"src_{sku}", "supplier": "supplier", "sku": sku, "destination": "branch",
                        "route": ["supplier", "branch"], "resources": ["supplier_cap"], "capacity_by_period": [1e6] * H,
                        "unit_price": unit_price, "freight_per_unit": freight_per_unit, "handling_per_unit": handling_per_unit,
                        "minimum": minimum, "multiple": multiple, "case_multiple": case_multiple, "pallet_multiple": pallet_multiple,
                        "maximum": 1e6, "fixed_order_fee": fixed_order_fee, "terms": "terms", "order_calendar": "order_days",
                        "shipping_calendar": "ship_days", "lead_days": lead_days, "dispatch_days": 0,
                        "fill_mean": .98, "fill_sd": .01, "lead_sd_days": 0., "approved": True, "compliance": "cleared",
                        "quote_expires": NOW + timedelta(days=730), "quote_reference": "p1-fixture"})
        services.append({**known, "id": f"svc_{sku}", "sku": sku, "location": "branch", "customer": "customer",
                         "target": target, "selling_price": unit_price * 2, "sla_per_unmet": unit_price * .5})
        history += [{**known, "service": f"svc_{sku}", "period": t, "quantity": demand * (1 + demand_sd_hint * (((t * 7919) % 11) - 5) / 5.)} for t in range(-52, 0)]
        stock.append({**known, "id": f"open_{sku}", "sku": sku, "location": "branch", "quantity": opening_units, "reserved": 0., "damaged": 0.,
                      "quarantined": 0., "expires_in": 52, "age_periods": 1})
    payload: dict[str, Any] = {
        "operator_id": "p1_fixture", "as_of": NOW, "currency": "USD", "period_days": period_days, "horizon": H,
        "skus": skus_rows,
        "locations": [{**known, "id": "branch", "kind": "branch", "capacity_volume": capacity_volume,
                       "holding_per_value_period": annual_to_period(holding_per_year, period_days), "receiving_calendar": "always"}],
        "calendars": [{**known, "id": "always"}, {**known, "id": "order_days", "weekdays": list(order_weekdays)}, {**known, "id": "ship_days", "weekdays": list(ship_weekdays)}],
        "terms": [{**known, "id": "terms", "deposit_fraction": deposit_fraction, "balance_trigger": balance_trigger, "net_days": net_days,
                   "financing_fee_fraction": 0., "fx_rate_to_currency": 1., "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}],
        "resources": [{**known, "id": "supplier_cap", "capacity_by_period": [1e6] * H, "failure_domains": ["supplier"]}], "sources": sources, "stock": stock, "transfers": [], "substitutions": [],
        "customers": [{**known, "id": "customer", "channel": "retail", "priority": 1.}],
        "services": services, "history": history, "pipeline": pipeline or [], "incumbent_orders": incumbent_orders or [],
        "liquidity": {**known, "opening_cash": opening_cash, "minimum_cash": 0., "credit_limit": credit_limit, "opening_debt": 0.,
                      "interest_per_period": annual_to_period(interest_per_year, period_days),
                      "cost_of_capital_per_period": annual_to_period(cost_of_capital_per_year, period_days),
                      "known_receivables": [receivables_per_period] * H, "other_payments": [0.] * H},
        # A declared stress is mandatory on every request. P1 is cycle-stock economics, not
        # disruption physics, so the default declared stress is nil (the fitted world itself): the
        # P0 stress gate then runs but cannot dominate the economics. "late" declares a one-week
        # delay with full fill for the sensitivity arm; "severe" is the P0-style envelope.
        "stresses": {"none": [{"name": "nil", "fill_multiplier": 1., "extra_lead_days": 0, "demand_multiplier": 1., "recovery_period": H, "shared_failure": True}],
                     "late": [{"name": "one_week_late", "fill_multiplier": 1., "extra_lead_days": 7, "demand_multiplier": 1., "recovery_period": H, "shared_failure": True}],
                     "severe": [{"name": "late", "fill_multiplier": .9, "extra_lead_days": 7, "demand_multiplier": 1.05, "recovery_period": H, "shared_failure": True}]}[stresses],
        "incumbent_rule": incumbent_rule,
        "seed": seed, "scenarios": scenarios, "max_solve_seconds": max_solve_seconds, "downside_cost_tolerance": .05, "service_tolerance": .01,
        "evidence_label": "SYNTHETIC",
        "economics_provenance": {"location.branch.holding_per_value_period": "CONFIGURED_ASSUMPTION",
                                 "liquidity.cost_of_capital_per_period": "CONFIGURED_ASSUMPTION" if cost_of_capital_per_year else "NOT_AVAILABLE"},
    }
    if supplier_terms:
        payload["supplier_terms"] = [{**known, "id": "supplier_terms", "supplier": "supplier",
                                      "provenance": {k: "CONFIGURED_ASSUMPTION" for k in supplier_terms}, **supplier_terms}]
    if extra:
        payload.update(extra)
    return Request.model_validate(payload)
