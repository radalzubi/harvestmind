"""End-to-end signal -> graph -> scenario/action causal controls.

Synthetic fixtures test wiring, not predictive warning accuracy or customer ROI.
"""
from datetime import timedelta

import numpy as np
import pytest

from zaad.contracts import PlanningRequest
from zaad.engine import POLICIES, draw_paths, initial_state, order_actions, plan, prepare, route_parameters
from zaad.signals import Signal


@pytest.fixture
def plan_request():
    from zaad.demo import demo_request
    return demo_request(case="balanced")


def make_signal(plan_request, **changes):
    now = plan_request.as_of
    first_route = plan_request.routes[0]
    data = dict(id="risk-test", provider="fixture_sensor", entity_ids=(first_route.id,), kind="physical",
                observed_at=now, published_at=now, ingested_at=now, effective_at=now,
                valid_until=now + timedelta(days=2), magnitude=0.8, direction="deterioration",
                confidence=1.0, source_url="https://example.org/test-physical-observation",
                syndication_key="fixture-event", adapter_version="fixture-v1",
                license_status="open_verified", availability_basis="synthetic_fixture")
    data.update(changes)
    return Signal(**data)


def with_signals(plan_request, *signals, json_shaped=False):
    data = plan_request.model_dump(mode="json" if json_shaped else "python")
    data["signals"] = tuple(s.model_dump(mode="json" if json_shaped else "python") for s in signals)
    return PlanningRequest.model_validate(data)


def assert_same_paths(left, right):
    for item in left["demand"]:
        np.testing.assert_array_equal(left["demand"][item], right["demand"][item])
    for route in left["supply"]:
        np.testing.assert_array_equal(left["supply"][route]["fills"], right["supply"][route]["fills"])
        np.testing.assert_array_equal(left["supply"][route]["leads"], right["supply"][route]["leads"])


@pytest.mark.parametrize("control", ["future_ingestion", "future_publication", "future_effective", "stale",
                                      "irrelevant", "unlicensed", "news_only", "reconstructed"])
def test_unusable_or_news_only_evidence_cannot_shift_supply_or_orders(plan_request, control):
    future = plan_request.as_of + timedelta(hours=1)
    overrides = {
        "future_ingestion": {"ingested_at": future},
        "future_publication": {"published_at": future, "ingested_at": future},
        "future_effective": {"effective_at": future},
        "stale": {"observed_at": plan_request.as_of - timedelta(days=10),
                  "published_at": plan_request.as_of - timedelta(days=10)},
        "irrelevant": {"entity_ids": ("UNRELATED:OTHER_OCEAN",)},
        "unlicensed": {"license_status": "legal_review"},
        "news_only": {"kind": "news"},
        "reconstructed": {"availability_basis": "reconstructed_date_only", "historical_eligible": False},
    }[control]
    altered = with_signals(plan_request, make_signal(plan_request, **overrides))
    f0, c0, w0 = prepare(plan_request)
    f1, c1, w1 = prepare(altered)
    assert w1 == w0
    assert [c["severity"] for c in c1] == [c["severity"] for c in c0]
    assert_same_paths(draw_paths(plan_request, f0, c0, 71), draw_paths(altered, f1, c1, 71))
    stock, pending = initial_state(plan_request)
    for policy in POLICIES:
        assert order_actions(plan_request, f0, c0, policy, stock, pending) == order_actions(
            altered, f1, c1, policy, stock, pending)


def test_api_shaped_signal_json_survives_strict_signal_boundary(plan_request):
    altered = with_signals(plan_request, make_signal(plan_request), json_shaped=True)
    _, cards, _ = prepare(altered)
    assert next(c for c in cards if c["route"] == plan_request.routes[0].id)["severity"] > 0


def test_observed_physical_signal_changes_only_exposed_route_distribution(plan_request):
    altered = with_signals(plan_request, make_signal(plan_request))
    f0, c0, _ = prepare(plan_request)
    f1, c1, _ = prepare(altered)
    base = {c["route"]: c for c in c0}
    changed = {c["route"]: c for c in c1}
    rid = plan_request.routes[0].id
    assert route_parameters(changed[rid], True)[1] > route_parameters(base[rid], True)[1]
    assert route_parameters(changed[rid], False) == route_parameters(base[rid], False)
    p0, p1 = draw_paths(plan_request, f0, c0, 99), draw_paths(altered, f1, c1, 99)
    assert np.all(p1["supply"][rid]["leads"] > p0["supply"][rid]["leads"])
    assert np.all(p1["supply"][rid]["fills"] <= p0["supply"][rid]["fills"])
    for other in set(p0["supply"]) - {rid}:
        np.testing.assert_array_equal(p0["supply"][other]["leads"], p1["supply"][other]["leads"])
    assert not changed[rid]["probability_calibrated"]


def test_syndication_does_not_multiply_news_confirmation_or_hazard(plan_request):
    a = make_signal(plan_request, id="article1", provider="paper1", kind="news")
    b = make_signal(plan_request, id="article2", provider="paper2", kind="news")
    _, cards, _ = prepare(with_signals(plan_request, a, b))
    card = next(c for c in cards if c["route"] == plan_request.routes[0].id)
    assert card["evidence"]["independent_news_count"] == 1
    assert card["severity"] == 0


def test_blocked_unapproved_expired_and_unavailable_routes_never_ordered(plan_request):
    f0, c0, _ = prepare(plan_request)
    candidates = [c for c in c0 if c["feasible"]]
    assert candidates
    target = candidates[0]["route"]
    route = next(r for r in plan_request.routes if r.id == target)
    for reason, changed_route in (
        ("blocked", route.model_copy(update={"compliance": "blocked"})),
        ("unreviewed", route.model_copy(update={"compliance": "unreviewed"})),
        ("unapproved", route.model_copy(update={"approved": False})),
        ("expired", route.model_copy(update={"valid_until": plan_request.as_of})),
    ):
        changed = plan_request.model_copy(update={"routes": tuple(changed_route if r.id == target else r for r in plan_request.routes)})
        f, cards, _ = prepare(changed)
        assert not next(c for c in cards if c["route"] == target)["feasible"], reason
        stock, pending = initial_state(changed)
        for policy in POLICIES:
            assert all(a.route != target for a in order_actions(changed, f, cards, policy, stock, pending))
    edge_id = route.edges[0]
    changed = plan_request.model_copy(update={"edges": tuple(e.model_copy(update={"available": False})
                                 if e.id == edge_id else e for e in plan_request.edges)})
    f, cards, _ = prepare(changed)
    assert not next(c for c in cards if c["route"] == target)["feasible"]


def test_shared_failure_domain_couples_actual_draws_not_just_route_labels(plan_request):
    assert len(plan_request.routes) >= 2
    r1, r2 = plan_request.routes[:2]
    history = []
    for route in plan_request.routes:
        rows = [d for d in plan_request.deliveries if d.route == route.id]
        assert len(rows) >= 12
        for k, row in enumerate(rows):
            ratio = .2 + .8 * (k % 12) / 11
            history.append(row.model_copy(update={"confirmed": row.ordered, "received": row.ordered,
                           "accepted": row.ordered * ratio, "lead_periods": 1 + (11-k % 12)//3}))
    coupled = plan_request.model_copy(update={"deliveries": tuple(history), "edges": tuple(
        e.model_copy(update={"failure_domains": ("COMMON_PORT",)}) for e in plan_request.edges)})
    f, cards, _ = prepare(coupled)
    samples = draw_paths(coupled, f, cards, 918, count=2048)
    left = samples["supply"][r1.id]["fills"].ravel()
    right = samples["supply"][r2.id]["fills"].ravel()
    assert np.corrcoef(left, right)[0, 1] > .2
    independent = coupled.model_copy(update={"edges": tuple(e.model_copy(update={"failure_domains": ()})
                                                           for e in coupled.edges)})
    f2, c2, _ = prepare(independent)
    p2 = draw_paths(independent, f2, c2, 918, count=2048)
    assert abs(np.corrcoef(p2["supply"][r1.id]["fills"].ravel(),
                          p2["supply"][r2.id]["fills"].ravel())[0, 1]) < .05


def test_shared_domain_signal_reaches_both_routes_but_unshared_domain_does_not(plan_request):
    shared = plan_request.model_copy(update={"edges": tuple(e.model_copy(update={"failure_domains": ("COMMON_PORT",)})
                                                      for e in plan_request.edges)})
    exposed = with_signals(shared, make_signal(shared, entity_ids=("COMMON_PORT",)))
    _, cards, _ = prepare(exposed)
    assert all(c["severity"] > 0 for c in cards)


def test_news_only_cannot_change_selected_plan_economics(plan_request):
    without = plan(plan_request)
    with_news = plan(with_signals(plan_request, make_signal(plan_request, kind="news")))
    assert with_news.actions == without.actions
    assert with_news.selected_policy == without.selected_policy
    assert with_news.economics == without.economics
