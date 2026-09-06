"""Independent causal/accounting probes for the bounded Zaad policy search."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from pydantic import ValidationError

from zaad import engine
from zaad.contracts import PlanningRequest


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def request(**updates):
    """One explicit observed route: no benchmark generator assumptions needed."""
    known = NOW - timedelta(days=200)
    item = dict(id="A", location="dc", known_at=known, base_cost=5,
                selling_price=10, holding_per_period=.1, service_target=.5)
    values = dict(
        operator_id="audit", as_of=NOW, items=[item],
        nodes=[dict(id="supplier", kind="supplier", country="US", known_at=known),
               dict(id="dc", kind="dc", country="US", known_at=known)],
        edges=[dict(id="edge", origin="supplier", destination="dc", mode="road",
                    capacity=100, known_at=known)],
        routes=[dict(id="route", supplier="supplier", item="A", edges=["edge"],
                     landed_cost=5, capacity=100, approved=True, compliance="cleared",
                     valid_until=NOW + timedelta(days=365), quote_reference="audit-only",
                     known_at=known)],
        demand=[dict(item="A", period=t, quantity=10, known_at=known)
                for t in range(-16, 0)],
        deliveries=[dict(route="route", period=t, ordered=10, confirmed=10,
                         received=10, accepted=10, lead_periods=1, known_at=known)
                    for t in range(-16, 0)],
        warehouse_capacity=1000, review_budget=10000, horizon=4, scenarios=8,
        evidence_label="SYNTHETIC",
    )
    values.update(updates)
    return PlanningRequest.model_validate(values)


def prepared(req):
    forecasts, cards, warnings = engine.prepare(req)
    assert not warnings
    paths = engine.draw_paths(req, forecasts, cards, seed=1, deterministic=True)
    return forecasts, cards, paths


def test_future_operator_observation_is_rejected_not_trainable():
    req = request().model_dump()
    req["deliveries"][0]["known_at"] = NOW + timedelta(seconds=1)
    with pytest.raises(ValidationError, match="not known"):
        PlanningRequest.model_validate(req)


def test_pipeline_expected_acceptance_is_not_haircut_twice():
    req = request(
        pipeline=[dict(id="po", route="route", ordered=80, expected_accepted=40,
                       due_in=0, stage="confirmed", known_at=NOW)],
        warehouse_capacity=100,
    )
    forecasts, cards, paths = prepared(req)
    row = engine.settle(req, forecasts, cards, engine.Policy("lean", 0), paths, 0)
    assert row["trace"][0]["served"] == 10
    assert row["trace"][0]["inventory_value"] == 150


def test_reserved_stock_still_occupies_warehouse_space():
    req = request(
        inventory=[dict(id="lot", item="A", quantity=100, reserved=90,
                        expires_in=100, known_at=NOW)],
        warehouse_capacity=100,
    )
    forecasts, cards, _ = prepared(req)
    stock, pending = engine.initial_state(req)
    actions = engine.order_actions(req, forecasts, cards, engine.POLICIES[0], stock, pending)
    assert not actions, "Reserved units remain physically present, so there is no free space"


def test_emitted_first_action_equals_simulated_first_action_with_due_now_po():
    req = request(
        pipeline=[dict(id="po", route="route", ordered=50, expected_accepted=20,
                       due_in=0, stage="confirmed", known_at=NOW)],
        warehouse_capacity=40,
    )
    forecasts, cards, paths = prepared(req)
    report = engine.plan(req)
    emitted = report.incumbent_actions
    stock, pending = engine.initial_state(req)
    direct = engine.order_actions(req, forecasts, cards, engine.POLICIES[0], stock, pending)
    row = engine.settle(req, forecasts, cards, engine.POLICIES[0], paths, 0)
    assert sum(a.quantity for a in emitted) == row["trace"][0]["ordered"]
    assert sum(a.quantity for a in direct) == row["trace"][0]["ordered"]


def test_current_unobserved_demand_and_future_lead_do_not_change_first_action():
    req = request()
    forecasts, cards, paths = prepared(req)
    paths["demand"]["A"][0, :] = 0
    paths["demand"]["A"][1, :] = 1000
    paths["supply"]["route"]["leads"][1, :] = 5
    first = engine.settle(req, forecasts, cards, engine.POLICIES[0], paths, 0)
    second = engine.settle(req, forecasts, cards, engine.POLICIES[0], paths, 1)
    assert first["trace"][0]["ordered"] == second["trace"][0]["ordered"]


def test_common_ledger_conserves_assets_and_does_not_double_charge_shortage():
    req = request(
        inventory=[dict(id="lot", item="A", quantity=20, expires_in=100, known_at=NOW)],
    )
    forecasts, cards, paths = prepared(req)
    row = engine.settle(req, forecasts, cards, engine.POLICIES[0], paths, 0)
    assert row["consumed_cost"] == pytest.approx(
        row["opening_assets"] + row["purchase_base_cash"]
        - row["closing_inventory_assets"] - row["closing_pipeline_assets"])
    assert row["total_cost"] == pytest.approx(
        row["consumed_cost"] + row["freight_premium"] + row["holding"]
        + row["disposal"] + row["lost_sales_revenue"])
    assert row["served"]["A"] == 40


def test_actions_cannot_exceed_route_edge_budget_or_pack_limits():
    raw = request().model_dump()
    raw["items"][0].update(pack=4, moq=8)
    raw["edges"][0]["capacity"] = 19
    raw["routes"][0]["capacity"] = 18
    raw["review_budget"] = 70
    req = PlanningRequest.model_validate(raw)
    forecasts, cards, _ = prepared(req)
    stock, pending = engine.initial_state(req)
    actions = engine.order_actions(req, forecasts, cards, engine.Policy("protected", 3), stock, pending)
    assert actions
    assert sum(a.quantity for a in actions) <= 18
    assert sum(a.cash for a in actions) <= 70
    assert all(a.quantity % 4 == 0 and a.quantity >= 8 for a in actions)


@pytest.mark.parametrize("change", [dict(approved=False), dict(compliance="blocked"),
                                    dict(valid_until=NOW)])
def test_unapproved_illegal_or_expired_route_is_not_recommended(change):
    raw = request().model_dump()
    raw["routes"][0].update(change)
    report = engine.plan(PlanningRequest.model_validate(raw))
    assert report.status == "ABSTAIN"
    assert not report.actions


def test_quote_expiry_is_checked_on_each_simulated_and_live_review():
    raw = request().model_dump()
    raw["routes"][0]["valid_until"] = NOW + timedelta(days=1)
    req = PlanningRequest.model_validate(raw)
    forecasts, cards, paths = prepared(req)
    row = engine.settle(req, forecasts, cards, engine.POLICIES[0], paths, 0)
    assert all(t["ordered"] == 0 for t in row["trace"][1:]), \
        "Future quote renewal cannot be presumed to have occurred"
    raw["as_of"] = NOW + timedelta(days=7)
    next_review = engine.plan(PlanningRequest.model_validate(raw))
    assert next_review.status == "ABSTAIN"
    assert not next_review.actions


def test_identical_inputs_and_seeds_reproduce_paths_and_settlement():
    req = request()
    forecasts, cards, paths = prepared(req)
    again = engine.draw_paths(req, forecasts, cards, seed=1, deterministic=True)
    assert np.array_equal(paths["demand"]["A"], again["demand"]["A"])
    assert engine.settle(req, forecasts, cards, engine.POLICIES[0], paths, 0) == \
        engine.settle(req, forecasts, cards, engine.POLICIES[0], again, 0)


def test_report_economic_delta_uses_paired_worlds_not_selection_vs_confirmation(monkeypatch):
    req = request()

    def draw(_request, _forecasts, _cards, seed, *args, **kwargs):
        return {"seed": seed}

    def evaluate(_request, _forecasts, _cards, policy, paths):
        confirmation = paths["seed"] == req.seed + 1
        cost = 1000 if confirmation else 200
        if policy.name == "base_stock":
            cost = 800 if confirmation else 100
        return [{"total_cost": cost, "served": {"A": 100}, "demand": {"A": 100},
                 "capacity_breach": False, "average_inventory_value": cost / 2,
                 "peak_inventory_value": cost, "freight_premium": 0,
                 "holding": cost / 10, "churn_units": 0} for _ in range(8)]

    monkeypatch.setattr(engine, "draw_paths", draw)
    monkeypatch.setattr(engine, "evaluate", evaluate)
    report = engine.plan(req)
    assert report.selected_policy == "base_stock"
    assert report.status == "RECOMMEND_FOR_REVIEW"
    # Independent confirmation: incumbent=1000, candidate=800, paired gain=200.
    assert report.economics["modeled_horizon_benefit"] == 200
    assert report.economics["inventory_release_not_profit"] == 100
    assert report.economics["recurring_carry_benefit_in_horizon"] == 20


def test_policy_search_does_not_claim_global_stochastic_optimality():
    report = engine.plan(request())
    assert report.evidence["method"] == "finite_policy_stochastic_search"
    assert any("no global optimality" in note for note in report.limitations)
