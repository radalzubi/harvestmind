"""P3 production performance closure: structural regression for the shared-supplier-MOV pathology.

The 218 s production case (two SKUs, one supplier carrying a 5,000 minimum order value and a fixed
order cost, declared line capacity 1,000,000) solved slowly because the supplier-order linking rows
used the declared capacity as their big-M, so the linear relaxation never priced the order binaries.
These tests pin the structural indicators - the exact activation bound and the order-class search
route - without any wall-clock assertion.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import zaad.full.model as M
from zaad.full.contracts import Request
from zaad.full.planner import targets, v6_solve_terms
from zaad.full.protection import protection_profile
from zaad.full.uncertainty import supply_profiles
from zaad.full.worlds import draw, forecast_all
from zaad.meio.fixtures_p2 import p2_request
from zaad.sourcing.fixtures import build

SNAPSHOT = Path("docs/zaad_full/evidence/p3/perf_closure/shared_mov_prod_snapshot.json")


@pytest.fixture(scope="module")
def shared_mov() -> Request:
    return Request.model_validate(json.loads(SNAPSHOT.read_text()))


def _captured_model(req: Request, worlds, monkeypatch, **kw) -> M.Linear:
    """Build the candidate's model and capture it before the solver runs."""
    box: dict = {}

    class Stop(Exception):
        pass

    def grab(self, *args, **kwargs):
        box["m"] = self
        raise Stop()

    monkeypatch.setattr(M.Linear, "solve", grab)
    with pytest.raises(Stop):
        M.solve(req, worlds, **kw)
    return box["m"]


def _linking_bigm(m: M.Linear, source: str, t: int) -> float:
    """The -coefficient of the supplier-order binary in the line's linking row purchase <= M * order."""
    idx = {n: i for i, n in enumerate(m.names)}
    q = idx[("purchase", source, t)]
    for row in m.rows:
        if q in row and row[q] == 1 and len(row) == 2:
            other = next(c for c in row if c != q)
            if m.names[other][0] == "order":
                return -row[other]
    raise AssertionError("no linking row")


def test_activation_bound_is_the_undominated_quantity_not_the_declared_capacity(shared_mov):
    req = shared_mov
    det = draw(req, req.seed, 1, deterministic=True)
    bounds = M.activation_bounds(req, det, targets=None)
    cap = min(req.sources[0].maximum, req.sources[0].capacity_by_period[0])
    assert cap == 1_000_000.
    # demand-to-go from the next period plus nothing else: monotone, far below the declared capacity,
    # and never below the quantity the line needs to satisfy the supplier's MOV on its own (5,000 / 5.0)
    values = [bounds["src_A", t] for t in range(req.horizon)]
    assert all(v < cap / 100 for v in values)
    assert values == sorted(values, reverse=True)
    assert values[-1] == pytest.approx(1000.)
    assert values[0] > values[-1]
    # a source of a supplier without MOV has no floor: the last period bounds to demand-to-go only (zero)
    assert bounds["src_S2", req.horizon - 1] == 0.


def test_linking_rows_carry_the_tight_bound_and_the_purchase_column_keeps_its_capacity(shared_mov, monkeypatch):
    req = shared_mov
    det = draw(req, req.seed, 1, deterministic=True)
    m = _captured_model(req, det, monkeypatch, targets=targets(req))
    bounds = M.activation_bounds(req, det, targets=targets(req))
    idx = {n: i for i, n in enumerate(m.names)}
    for t in range(req.horizon):
        assert _linking_bigm(m, "src_A", t) == pytest.approx(bounds["src_A", t])
        assert m.upper[idx[("purchase", "src_A", t)]] == 1_000_000.
    # exactly one first-stage order binary per supplier and period, none per world
    assert sum(1 for n in m.names if n[0] == "order") == req.horizon


def test_fixed_plan_and_declared_shares_keep_the_declared_capacity(shared_mov):
    req = shared_mov
    det = draw(req, req.seed, 1, deterministic=True)
    assert M.activation_bounds(req, det, fixed=object()) == {}
    shared = build("C2_declared_min_max_share", 41001)
    from zaad.sourcing.contracts import resolve
    view = resolve(shared)
    bounds = M.activation_bounds(shared, draw(shared, shared.seed, 1, deterministic=True), sourcing=view)
    assert all(k[0] not in {s.id for s in shared.sources if (s.sku, s.destination) in view.shares} for k in bounds)


def test_seed_above_the_bound_is_rejected_with_the_reason(shared_mov, monkeypatch):
    req = shared_mov.model_copy(update={"warm_start_min_variables": 1})
    det = draw(req, req.seed, 1, deterministic=True)
    fits = forecast_all(req)
    v6 = v6_solve_terms(req, fits, protection_profile(req, fits, supply_profiles(req)))
    base = M.solve(req, det, targets=targets(req))
    dominated = M.Solution("OPTIMAL", {("src_A", 0): 50_000.}, {}, {}, {}, None, [], 0., 0, 0, None, None, [])
    out = M.solve(req, det, service_floor=True, seed=dominated, **v6)
    assert out.warm_start is not None and out.warm_start["accepted"] is False
    assert "activation bound" in out.warm_start["reason"]
    assert out.usable_plan and base.usable_plan


def test_tight_bound_reproduces_the_capacity_bigm_optimum(shared_mov, monkeypatch):
    """Dominance: the optimum with the exact bound equals the optimum with the declared capacity as M."""
    req = shared_mov
    det = draw(req, req.seed, 1, deterministic=True)
    fits = forecast_all(req)
    v6 = v6_solve_terms(req, fits, protection_profile(req, fits, supply_profiles(req)))
    tight = M.solve(req, det, service_floor=True, **v6)
    monkeypatch.setattr(M, "activation_bounds", lambda *a, **k: {})
    loose = M.solve(req, det, service_floor=True, **v6)
    assert tight.status == loose.status == "OPTIMAL"
    assert tight.projected_cost == pytest.approx(loose.projected_cost, rel=1e-6)
    for key in set(tight.purchases) | set(loose.purchases):
        assert tight.purchases.get(key, 0.) == pytest.approx(loose.purchases.get(key, 0.), abs=1e-3)


def test_scope_is_the_shared_supplier_order_class_only(shared_mov):
    """A supplier order linking several SKUs is in scope; a single-SKU MOV / MOQ request (E4), a
    request without supplier terms and the frozen P2 request keep the released formulation."""
    assert M.shared_supplier_orders(shared_mov) is True
    assert M.search_options(shared_mov) == {"mip_allow_restart": False}
    single = build("E4_moq_mov_small_order", 41001)
    assert single.supplier_terms and M.shared_supplier_orders(single) is False
    assert M.search_options(single) is None
    assert M.activation_bounds(single, draw(single, single.seed, 1, deterministic=True)) == {}
    frozen = p2_request()
    assert M.shared_supplier_orders(frozen) is False
    assert M.search_options(frozen) is None
    # the same shared order without a P3 sourcing block is a frozen P1 request: untouched
    legacy = shared_mov.model_copy(update={"sourcing": None})
    assert legacy.supplier_terms and M.shared_supplier_orders(legacy) is False
    assert M.activation_bounds(legacy, draw(legacy, legacy.seed, 1, deterministic=True)) == {}
