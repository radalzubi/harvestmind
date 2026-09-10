"""Deterministic synthetic distributor fixtures, never an operator training database."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from zaad.contracts import PlanningRequest


CASES = ("balanced", "overstock", "understock", "disruption", "false_alarm", "recovery")


def demo_request(case: str = "balanced", *, seed: int = 771) -> PlanningRequest:
    if case not in CASES:
        raise ValueError("unknown synthetic case")
    as_of = datetime(2026, 9, 1, tzinfo=timezone.utc)
    known = (as_of-timedelta(days=1)).isoformat()
    rng = np.random.default_rng(seed)
    nodes = [{"id": "origin", "kind": "supplier", "country": "US", "known_at": known},
             {"id": "regional", "kind": "supplier", "country": "US", "known_at": known},
             {"id": "port", "kind": "port", "country": "US", "known_at": known},
             {"id": "warehouse", "kind": "dc", "country": "US", "known_at": known}]
    edges = [{"id": "ocean", "origin": "origin", "destination": "port", "mode": "ocean",
              "capacity": 1000, "failure_domains": ["PORT:EXAMPLE", "CARRIER:EXAMPLE"], "known_at": known},
             {"id": "inland", "origin": "port", "destination": "warehouse", "mode": "road",
              "capacity": 1000, "failure_domains": ["PORT:EXAMPLE"], "known_at": known},
             {"id": "regional-road", "origin": "regional", "destination": "warehouse", "mode": "road",
              "capacity": 500, "failure_domains": ["LANE:REGIONAL"], "known_at": known}]
    items, routes, demand, deliveries, inventory, pipeline = [], [], [], [], [], []
    cover = {"balanced": 1.5, "overstock": 7., "understock": .1,
             "disruption": 1.5, "false_alarm": 1.5, "recovery": 5.}[case]
    for sku, mu, unit_cost in (("A", 100., 5.), ("B", 40., 8.)):
        items.append({"id": sku, "location": "warehouse", "base_cost": unit_cost,
                      "selling_price": unit_cost*1.8, "holding_per_period": unit_cost*.01,
                      "service_target": .95, "pack": 5, "criticality": 2 if sku == "A" else 1,
                      "segment": "A" if sku == "A" else "B", "known_at": known})
        for rid, supplier, path, premium, cap, lead in (
                (f"{sku}-main", "origin", ["ocean", "inland"], 1., mu*1.7, 2),
                (f"{sku}-alt", "regional", ["regional-road"], 1.3, mu*.9, 1)):
            routes.append({"id": rid, "supplier": supplier, "item": sku, "edges": path,
                           "landed_cost": unit_cost*premium, "capacity": cap, "approved": True,
                           "compliance": "cleared", "valid_until": (as_of+timedelta(days=365)).isoformat(),
                           "quote_reference": "SYNTHETIC-NOT-A-CARRIER-QUOTE", "known_at": known})
            for t in range(-78, 0):
                fill = float(np.clip(rng.normal(.97, .015), .8, 1.))
                deliveries.append({"route": rid, "period": t, "ordered": mu,
                                   "confirmed": mu, "received": mu*fill, "accepted": mu*fill,
                                   "lead_periods": lead,
                                   "known_at": (as_of+timedelta(days=7*t)).isoformat()})
        for t in range(-78, 0):
            demand.append({"item": sku, "period": t, "quantity": float(max(0,rng.normal(mu,mu*.12))),
                           "known_at": (as_of+timedelta(days=7*t)).isoformat()})
        inventory.append({"id": f"lot-{sku}", "item": sku, "quantity": mu*cover,
                          "expires_in": 104, "known_at": known})
        for due in (1, 2):
            pipeline.append({"id": f"po-{sku}-{due}", "route": f"{sku}-main", "ordered": mu/.97,
                             "expected_accepted": mu, "due_in": due, "stage": "in_transit", "known_at": known})
    signals = []
    if case in ("disruption", "false_alarm", "recovery"):
        from zaad.signals import Signal
        signals.append(Signal(
            id="synthetic-port-event", provider="synthetic", entity_ids=("PORT:EXAMPLE",),
            kind="physical" if case != "false_alarm" else "news", observed_at=as_of,
            published_at=as_of, ingested_at=as_of, effective_at=as_of,
            valid_until=as_of+timedelta(days=7), magnitude=.65, confidence=1.,
            direction="recovery" if case == "recovery" else "deterioration", source_url="https://example.com/synthetic-notice",
            syndication_key="synthetic-event", adapter_version="synthetic.v1",
            license_status="open_verified", availability_basis="synthetic_fixture"
        ).model_dump(mode="json"))
    return PlanningRequest.model_validate_json(__import__("json").dumps({
        "operator_id": "zaad-demo", "as_of": as_of.isoformat(), "items": items,
        "nodes": nodes, "edges": edges, "routes": routes, "demand": demand,
        "deliveries": deliveries, "inventory": inventory, "pipeline": pipeline,
        "signals": signals, "warehouse_capacity": 5000, "review_budget": 10000,
        "horizon": 12, "scenarios": 24, "seed": 1701,
        "prior_mode": "PROTECT" if case == "recovery" else "LEAN",
        "evidence_label": "SYNTHETIC"}))
