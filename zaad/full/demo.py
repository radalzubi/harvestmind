"""Deterministic, financially explicit synthetic contract fixtures."""
from datetime import datetime, timedelta, timezone
from typing import Any

from zaad.full.contracts import Request


def example(case: str = "normal", seed: int = 12001) -> Request:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    known = {"known_at": now - timedelta(days=1)}
    H = 6
    source = {**known, "id": "main", "supplier": "supplier", "sku": "A", "destination": "branch",
              "route": ["supplier", "port", "branch"], "resources": ["supplier_cap", "port_cap"],
              "capacity_by_period": [100.] * H, "unit_price": 5., "freight_per_unit": .2,
              "handling_per_unit": .1, "minimum": 0., "multiple": 0., "maximum": 100.,
              "fixed_order_fee": 0., "terms": "net30", "order_calendar": "daily", "shipping_calendar": "daily",
              "lead_days": 7, "dispatch_days": 0, "fill_mean": .95, "fill_sd": .03, "lead_sd_days": 1.,
              "approved": True, "compliance": "cleared", "quote_expires": now + timedelta(days=365), "quote_reference": "synthetic_quote"}
    payload: dict[str, Any] = {"operator_id": "synthetic_zaad", "as_of": now, "currency": "USD", "period_days": 7,
               "horizon": H, "skus": [{**known, "id": "A", "volume": 1., "asset_value": 5.,
                                       "terminal_value": 4., "shelf_life": 26, "disposal_fee": .1}],
               "locations": [{**known, "id": "branch", "kind": "branch", "capacity_volume": 1000.,
                               "holding_per_value_period": .01, "receiving_calendar": "daily"}],
               "calendars": [{**known, "id": "daily"}],
               "terms": [{**known, "id": "net30", "deposit_fraction": 0., "balance_trigger": "arrival",
                          "net_days": 30, "financing_fee_fraction": 0., "fx_rate_to_currency": 1.,
                          "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}],
               "resources": [{**known, "id": "supplier_cap", "capacity_by_period": [100.] * H, "failure_domains": ["supplier"]},
                             {**known, "id": "port_cap", "capacity_by_period": [100.] * H, "failure_domains": ["port"]}],
               "sources": [source], "stock": [{**known, "id": "opening", "sku": "A", "location": "branch",
                 "quantity": 50., "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": 20, "age_periods": 6}],
               "transfers": [], "substitutions": [],
               "customers": [{**known, "id": "customer", "channel": "retail", "priority": 1.}],
               "services": [{**known, "id": "retail_A", "sku": "A", "location": "branch", "customer": "customer",
                             "target": .95, "selling_price": 10., "sla_per_unmet": 1.}],
               "history": [{**known, "service": "retail_A", "period": t, "quantity": 20.} for t in range(-52, 0)],
               "pipeline": [], "liquidity": {**known, "opening_cash": 2000., "minimum_cash": 100., "credit_limit": 1000.,
                  "opening_debt": 0., "interest_per_period": .002, "known_receivables": [0.] * H, "other_payments": [0.] * H},
               "stresses": [{"name": "tail", "fill_multiplier": .8, "extra_lead_days": 14,
                              "demand_multiplier": 1.1, "recovery_period": H, "shared_failure": True}],
               "seed": seed, "scenarios": 3, "max_solve_seconds": 15., "downside_cost_tolerance": .05,
               "service_tolerance": .01, "evidence_label": "SYNTHETIC"}
    if case in {"transfer", "network"}:
        payload["locations"].append({**known, "id": "central", "kind": "central_dc", "capacity_volume": 1000.,
                                     "holding_per_value_period": .003, "receiving_calendar": "daily"})
        payload["stock"][0]["quantity"] = 20.
        payload["stock"].append({**known, "id": "excess_central", "sku": "A", "location": "central", "quantity": 100.,
                                 "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": 20, "age_periods": 6})
        payload["transfers"].append({**known, "id": "central_branch", "sku": "A", "origin": "central", "destination": "branch",
                                      "lead_periods": 1, "capacity": 100., "cost_per_unit": .2, "loss_fraction": 0., "approved": True})
    if case == "substitution":
        payload["skus"].append({**known, "id": "B", "volume": 1., "asset_value": 4., "terminal_value": 3., "shelf_life": 26, "disposal_fee": .1})
        payload["stock"].append({**known, "id": "sub_stock", "sku": "B", "location": "branch", "quantity": 100.,
                                 "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": 20, "age_periods": 6})
        payload["stock"][0]["quantity"] = 0.
        payload["substitutions"].append({**known, "id": "approved_B_for_A", "supplied_sku": "B", "requested_sku": "A",
            "customers": ["customer"], "channels": ["retail"], "input_per_output": 1., "penalty_per_output": .1,
            "service_equivalence": 1., "approved": True, "brand_approval_reference": "fixture", "cannibalization_assumption": "none"})
    if case == "recovery":
        payload["mode"] = "RECOVER"
        payload["stock"][0]["quantity"] = 140.
        payload["pipeline"] = [{**known, "id": "open", "source": "main", "revision": 1, "ordered": 100., "confirmed": 100.,
           "shipped": 0., "received": 0., "rejected": 0., "expected_accepted_remaining": 95., "placed_at": now - timedelta(days=7),
           "confirmed_at": now - timedelta(days=6), "departed_at": None, "current_eta": now + timedelta(days=14), "stage": "confirmed",
           "carrier": "fixture", "cancellation_status": "eligible", "prepaid_per_remaining_unit": 0., "allow_split_amendments": True,
           "options": [{**known, "id": action, "action": action, "due_in": due, "fee_per_unit": fee, "remaining_invoice_per_unit": price,
                        "payment_due_in": due, "max_quantity": 100., "deadline": now + timedelta(days=1), "allowed_stages": ["confirmed"],
                        "contract_reference": "fixture_explicit_terms"}
                       for action, due, fee, price in [("keep", 2, 0., 5.3), ("cancel", 2, .25, 0.), ("de_expedite", 4, .1, 5.)]]}]
    if case == "cash":
        payload["terms"][0].update(deposit_fraction=1., net_days=0)
        payload["liquidity"].update(opening_cash=200., credit_limit=0.)
    if case == "understock":
        payload["stock"][0]["quantity"] = 0.
    return Request.model_validate(payload)
