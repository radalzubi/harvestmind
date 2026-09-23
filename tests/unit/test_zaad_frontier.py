"""Frontier oracle decomposition (frontier decomposition pass): the per-service frontier solved on the
exact connected components of the built model returns the values the released monolithic oracle
returns, on every coupling the model can carry.

A  independent components         B  shared supplier capacity        C  capital coupling (declared cash)
D  MOQ / MOV supplier order         E  location volume and transfer lanes   F  fully independent (maximum split)
G  degenerate / tie: identical report and plan under both oracle modes
plus the exact skips (witness at the bound, proven infeasibility) and the partition itself."""
from __future__ import annotations

import numpy as np
import pytest

import zaad.full.planner as planner
from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.fixtures_p1 import p1_request
from zaad.full.frontier import extract, partition
from zaad.full.model import Linear, solve
from zaad.full.worlds import draw


def _independent(n: int = 3, demand: float = 100., opening: float = 30., **kw) -> Request:
    """n SKUs, each on its own supplier resource, no declared capital, no declared storage capacity:
    nothing in the data couples them."""
    req = p1_request(skus=tuple(chr(65 + k) for k in range(n)), demand=demand, opening_units=opening, seed=41001, **kw)
    data = req.model_dump(mode="python")
    data["resources"] = [{**data["resources"][0], "id": f"cap_{s['sku']}"} for s in data["sources"]]
    for s in data["sources"]:
        s["resources"] = [f"cap_{s['sku']}"]
        s["capacity_by_period"] = [demand] * req.horizon
        s["maximum"] = demand
    data["locations"][0]["capacity_volume"] = None
    data["liquidity"].update(opening_cash=None, credit_limit=None)
    return Request.model_validate(data)


def _both(req: Request, witnesses: list | None = None):
    """(monolithic values, component solution) on the oracle's own world."""
    det = draw(req, req.seed, 1, deterministic=True)
    ids = tuple(s.id for s in req.services)
    mono = {s: solve(req, det, service_first=s, service_only=True) for s in ids}
    comp = solve(req, det, service_first="all", service_only=True, frontier_services=ids, frontier_witnesses=witnesses)
    return {s: mono[s].projected_service.get(s) for s in ids}, {s: mono[s].status for s in ids}, comp


def _assert_identical(req: Request, expected_components: int | None = None, witnesses: list | None = None):
    old, statuses, new = _both(req, witnesses)
    assert new.frontier is not None
    for s in req.services:
        assert statuses[s.id] == "OPTIMAL"
        assert old[s.id] is not None
        assert new.projected_service.get(s.id) == pytest.approx(old[s.id], abs=1e-9), s.id
    if expected_components is not None:
        assert new.frontier["service_components"] == expected_components
    return old, new


# A / F. independent components: one component per SKU, each service solved on its own SKU's block

def test_independent_products_split_into_one_component_each_and_agree():
    req = _independent(4)
    old, new = _assert_identical(req, expected_components=4)
    solves = new.frontier["solves"]
    assert len(solves) == 4 and len({s["component"] for s in solves}) == 4
    assert max(s["columns"] for s in solves) * 2 < new.variables       # every solve well below the whole model
    assert any(v < 1. for v in old.values())                            # a thin opening: the frontier is below one somewhere


# B. shared supplier capacity: a binding resource row keeps the products in one component

def test_shared_supplier_capacity_is_one_component():
    req = _independent(2, demand=100., opening=10.)
    data = req.model_dump(mode="python")
    data["resources"] = [{**data["resources"][0], "id": "shared_cap", "capacity_by_period": [60.] * req.horizon}]
    for s in data["sources"]:
        s["resources"] = ["shared_cap"]
    shared = Request.model_validate(data)
    old, new = _assert_identical(shared, expected_components=1)
    # the coupling is real: alone, each service may use the whole supplier; the split fixture (no shared row) serves more
    old_split, _ = _assert_identical(req, expected_components=2)
    assert all(old[s] <= old_split[s] + 1e-9 for s in old)


# C. capital coupling: independent physics, one declared cash balance

def test_declared_cash_merges_independent_products_and_the_frontier_honours_it():
    free = _independent(3, demand=100., opening=10.)
    data = free.model_dump(mode="python")
    # unmet demand costs SLA cash and served demand costs purchase cash: a balance and facility that can
    # pay every penalty (feasible) but cannot fund serving any one service in full (the frontier binds)
    data["liquidity"].update(opening_cash=600., credit_limit=10000.)
    tight = Request.model_validate(data)
    old, new = _assert_identical(tight, expected_components=1)
    old_free, _ = _assert_identical(free, expected_components=3)
    assert any(old[s] < old_free[s] - 1e-6 for s in old)   # cash binds: the coupled frontier is lower than the free one


# D. MOQ / MOV: supplier-order economics link the lines of one supplier

def test_supplier_order_economics_keep_the_lines_in_one_component():
    req = _independent(2, demand=100., opening=10., minimum=40.,
                       supplier_terms={"minimum_order_value": 400., "fixed_order_cost": 50.})
    _assert_identical(req, expected_components=1)


# E. location volume and transfer lanes

def test_declared_location_capacity_merges_the_products_of_the_location():
    free = _independent(2, demand=100., opening=10.)
    data = free.model_dump(mode="python")
    data["locations"][0]["capacity_volume"] = 150.
    capped = Request.model_validate(data)
    _assert_identical(capped, expected_components=1)


def test_transfer_network_is_one_component_and_agrees():
    from tests.unit.test_zaad_meio_recovery_v6 import _two_branches
    req = _two_branches()
    _assert_identical(req, expected_components=1)


# G. degenerate / tie: the whole planner returns the identical report under both oracle modes

@pytest.mark.parametrize("case", ["normal", "understock"])
def test_planner_report_is_identical_under_both_oracle_modes(case, monkeypatch):
    from scripts.plan_report_compare import compare
    req = example(case)
    monkeypatch.setattr(planner, "FRONTIER_MODE", "monolithic")
    released = planner.plan(req)
    monkeypatch.setattr(planner, "FRONTIER_MODE", "component")
    decomposed = planner.plan(req)
    assert compare(released, decomposed, 1e-9) == []
    assert released["service_frontier"] == decomposed["service_frontier"]
    assert decomposed["orchestration"]["frontier"]["mode"] == "component"
    assert released["orchestration"]["frontier"] is None


def test_planner_report_is_identical_on_independent_products(monkeypatch):
    from scripts.plan_report_compare import compare
    req = _independent(3, demand=100., opening=60., incumbent_rule="reorder_point")
    monkeypatch.setattr(planner, "FRONTIER_MODE", "monolithic")
    released = planner.plan(req)
    monkeypatch.setattr(planner, "FRONTIER_MODE", "component")
    decomposed = planner.plan(req)
    assert compare(released, decomposed, 1e-9) == []
    assert released["actions"] == decomposed["actions"]
    telemetry = decomposed["orchestration"]["frontier"]
    assert telemetry["service_components"] == 3


# exact skips

def test_witness_at_the_bound_skips_the_solve_with_the_same_value():
    req = _independent(3, demand=100., opening=2000.)           # ample stock: every service alone serves in full
    det = draw(req, req.seed, 1, deterministic=True)
    base = solve(req, det)                                         # a restriction on the same world: a valid witness
    assert base.usable_plan and all(v == 1. for v in base.projected_service.values())
    old, new = _assert_identical(req, expected_components=3, witnesses=[base])
    assert new.frontier["skipped_proven"] == sorted(s.id for s in req.services)
    assert new.frontier["solves"] == []                            # proven at the bound: nothing solved
    assert all(old[s.id] == 1. == new.projected_service[s.id] for s in req.services)
    # an unusable or adaptive witness proves nothing
    none = solve(req, det, service_first="all", service_only=True, frontier_services=tuple(s.id for s in req.services),
                 frontier_witnesses=[None])
    assert len(none.frontier["solves"]) == 3


def test_witness_only_proves_the_services_it_serves_in_full():
    req = _independent(2, demand=100., opening=10.)
    det = draw(req, req.seed, 1, deterministic=True)
    base = solve(req, det)
    served = [s for s, v in base.projected_service.items() if v == 1.]
    ids = tuple(s.id for s in req.services)
    comp = solve(req, det, service_first="all", service_only=True, frontier_services=ids, frontier_witnesses=[base])
    assert comp.frontier["skipped_proven"] == sorted(served)
    assert {s["service"] for s in comp.frontier["solves"]} == set(ids) - set(served)
    assert comp.frontier["feasibility_solves"] == 0                # the witness proves every component feasible


def test_proven_infeasibility_reports_no_frontier_for_any_service():
    req = _independent(2, demand=100., opening=100.)
    data = req.model_dump(mode="python")
    data["locations"][0]["capacity_volume"] = 20.                   # below the opening stock: infeasible
    tight = Request.model_validate(data)
    det = draw(tight, tight.seed, 1, deterministic=True)
    ids = tuple(s.id for s in tight.services)
    mono = {s: solve(tight, det, service_first=s, service_only=True) for s in ids}
    assert all(m.status == "INFEASIBLE" and m.projected_service == {} for m in mono.values())
    comp = solve(tight, det, service_first="all", service_only=True, frontier_services=ids)
    assert comp.status == "INFEASIBLE" and comp.projected_service == {}


def test_service_less_components_are_checked_for_feasibility_without_a_witness():
    req = _independent(2, demand=100., opening=10.)
    data = req.model_dump(mode="python")
    # a third SKU with stock and a source but no service: its own component, nothing to optimise
    data["skus"] = [*data["skus"], {**data["skus"][0], "id": "Z"}]
    data["stock"] = [*data["stock"], {**data["stock"][0], "id": "open_Z", "sku": "Z"}]
    data["sources"] = [*data["sources"], {**data["sources"][0], "id": "src_Z", "sku": "Z", "resources": ["cap_Z"]}]
    data["resources"] = [*data["resources"], {**data["resources"][0], "id": "cap_Z"}]
    req3 = Request.model_validate(data)
    det = draw(req3, req3.seed, 1, deterministic=True)
    ids = tuple(s.id for s in req3.services)
    comp = solve(req3, det, service_first="all", service_only=True, frontier_services=ids)
    assert comp.frontier["service_components"] == 2 and comp.frontier["feasibility_solves"] == 1
    with_witness = solve(req3, det, service_first="all", service_only=True, frontier_services=ids, frontier_witnesses=[solve(req3, det)])
    assert with_witness.frontier["feasibility_solves"] == 0
    assert with_witness.projected_service == pytest.approx(comp.projected_service, abs=1e-9)


# the partition itself

def test_partition_follows_the_rows_and_extract_keeps_them_verbatim():
    m = Linear()
    a, b, c, d = (m.var(("v", k), upper=k + 1., integer=(k == 1)) for k in range(4))
    m.row({a: 1., b: 2.}, upper=3.)        # block one
    m.row({c: 1.}, lower=.5)               # block two
    m.row({d: -1., c: 1.}, 0., 0.)         # joins d to block two
    m.row({}, upper=1.)                    # empty, satisfiable
    part = partition(m.rows, len(m.names))
    assert part.count == 2 and part.empty_rows == [3]
    assert part.column_label[a] == part.column_label[b] != part.column_label[c] == part.column_label[d]
    sub, col_map = extract(m, part, int(part.column_label[c]))
    assert sub.names == [("v", 2), ("v", 3)] and sub.upper == [3., 4.] and sub.integer == [0, 0]
    assert sub.rows == [{col_map[c]: 1.}, {col_map[d]: -1., col_map[c]: 1.}] and sub.lo == [.5, 0.] and sub.hi == [np.inf, 0.]
