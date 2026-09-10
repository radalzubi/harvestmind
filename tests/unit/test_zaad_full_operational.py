from datetime import timedelta

import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.intake import export_bundle, import_bundle, resolve_po_revisions
from zaad.full.model import solve
from zaad.full.settlement import settle
from zaad.full.worlds import draw


def test_csv_roundtrip_all_financial_terms():
    req = example("recovery")
    assert import_bundle(export_bundle(req)) == req


def test_revision_resolver_never_chooses_future_revision():
    req = example("recovery")
    old = req.pipeline[0].model_dump()
    future = {**old, "revision": 2, "known_at": req.as_of + timedelta(days=1)}
    assert resolve_po_revisions([old, future], req.as_of) == [old]
    with pytest.raises(ValueError):
        resolve_po_revisions([old, old], req.as_of)


def test_pack_and_transport_increment_together():
    data = example().model_dump(mode="json")
    data["sources"][0].update(multiple=2., case_multiple=4., transport_multiple=12., minimum=12.)
    req = Request.model_validate(data)
    world = draw(req, 15, 1, deterministic=True)[0]
    result = solve(req, [world])
    assert result.status == "OPTIMAL"
    assert all(q / 12 == pytest.approx(round(q / 12)) for q in result.purchases.values())
    settle(req, result, world)


def test_priority_and_common_allocation_parity():
    data = example().model_dump(mode="json")
    data["horizon"] = 1
    data["stock"][0]["quantity"] = 20.
    data["customers"].append({**data["customers"][0], "id": "important", "priority": 10.})
    data["services"].append({**data["services"][0], "id": "priority_A", "customer": "important"})
    data["history"].extend({**r, "service": "priority_A"} for r in list(data["history"]))
    req = Request.model_validate(data)
    world = draw(req, 15, 1, deterministic=True)[0]
    result = solve(req, [world])
    actual = settle(req, result, world)
    assert actual["service"]["priority_A"] == 1
    assert actual["service"]["retail_A"] == 0
    assert actual["economic_cost"] == pytest.approx(result.projected_cost)


def test_line_level_otif_requires_real_lines():
    req = example()
    data = req.model_dump(mode="json")
    data["services"][0]["metric"] = "otif"
    with pytest.raises(ValueError):
        Request.model_validate(data)
    data["order_lines"] = [{"id": "line", "order_id": "order", "known_at": req.as_of,
                            "service": "retail_A", "quantity": 20., "due_in": 0,
                            "ordered_at": req.as_of, "requested_at": req.as_of, "promised_at": req.as_of,
                            "filled": 0., "cancelled": 0.}]
    req = Request.model_validate(data)
    world = draw(req, 15, 1, deterministic=True)[0]
    result = solve(req, [world], service_floor=True)
    assert result.status == "OPTIMAL"
    assert settle(req, result, world)["order_metrics"]["retail_A"]["otif"] == 1


def test_cash_deposit_is_paid_at_order_not_arrival():
    data = example().model_dump(mode="json")
    data["terms"][0].update(deposit_fraction=.5, net_days=30)
    req = Request.model_validate(data)
    world = draw(req, 15, 1, deterministic=True)[0]
    result = solve(req, [world])
    actual = settle(req, result, world)
    quantity = result.purchases.get(("main", 0), 0.)
    assert actual["trace"][0]["payments"] == pytest.approx(quantity * (2.5 + .3))


def test_ineligible_amendment_never_appears():
    req = example("recovery")
    data = req.model_dump(mode="json")
    for option in data["pipeline"][0]["options"]:
        if option["action"] != "keep":
            option["deadline"] = (req.as_of - timedelta(seconds=1)).isoformat()
    req = Request.model_validate(data)
    result = solve(req, draw(req, 15, 1, deterministic=True))
    assert set(result.amendments) == {("open", "keep")}


def overdue_request():
    data = example("recovery").model_dump(mode="json")
    data["locations"].append({**data["locations"][0], "id": "central"})
    data["stock"][0]["quantity"] = 0.
    data["sources"][0]["destination"] = "central"
    data["sources"][0]["route"][-1] = "central"
    data["pipeline"][0]["options"] = [{**data["pipeline"][0]["options"][0], "due_in": 0}]
    data["transfers"] = [{"id": "move", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": "branch",
                           "lead_periods": 1, "capacity": 100., "cost_per_unit": .1, "loss_fraction": 0., "approved": True}]
    return Request.model_validate(data)


def test_overdue_expected_po_is_not_physically_transferable():
    req = overdue_request()
    result = solve(req, draw(req, 3, 1, deterministic=True))
    assert result.status == "OPTIMAL"
    assert sum(q for (_, _, t), q in result.transfers.items() if t == 0) == 0


def test_first_transfer_bound_survives_optimistic_external_world():
    from dataclasses import replace

    req = overdue_request()
    world = replace(draw(req, 3, 1, deterministic=True)[0], po_due={"open": 0})
    result = solve(req, [world])
    assert result.status == "OPTIMAL"
    assert sum(q for (_, _, t), q in result.transfers.items() if t == 0) == 0


def test_first_transfer_bound_is_shared_across_arcs():
    from dataclasses import replace

    data = overdue_request().model_dump(mode="json")
    data["stock"].append({**data["stock"][0], "id": "real_stock", "location": "central", "quantity": 10.})
    data["transfers"].append({**data["transfers"][0], "id": "other_truck"})
    req = Request.model_validate(data)
    world = replace(draw(req, 3, 1, deterministic=True)[0], po_due={"open": 0})
    result = solve(req, [world])
    assert result.status == "OPTIMAL"
    assert sum(q for (_, _, t), q in result.transfers.items() if t == 0) <= 10. + 1e-6
