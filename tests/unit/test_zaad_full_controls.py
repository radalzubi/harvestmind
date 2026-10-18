from dataclasses import replace
from datetime import timedelta
import hashlib

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import app
from api.product.governance import actor_from as _actor_from
from api.dependencies import require_actor, require_operator
from zaad.full.contracts import Request, ShipmentObservation
from zaad.full.demo import example
from zaad.full.eta import conditional_eta
from zaad.full.forecast import change_origin, estimate, sample
from zaad.full.model import solve
from zaad.full.planner import plan
from zaad.full.replay import replay
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.shadow import ShadowConflict, ShadowLedger
from zaad.full.worlds import dates, draw


def modified(req, **updates):
    return Request.model_validate({**req.model_dump(), **updates})


def test_three_supplier_continuous_oracle():
    req = example()
    data = req.model_dump()
    data["horizon"] = 2
    data["skus"][0].update(asset_value=1., terminal_value=0.)
    data["stock"][0]["quantity"] = 0.
    data["sources"] = [{**data["sources"][0], "id": name, "resources": [name], "fill_mean": 1., "fill_sd": 0.,
                         "lead_sd_days": 0., "unit_price": price, "capacity_by_period": [cap] * 6}
                        for name, price, cap in [("s1", 1., 17.), ("s2", 2., 53.), ("s3", 3., 30.)]]
    data["resources"] = [{"id": s["id"], "known_at": req.as_of, "capacity_by_period": s["capacity_by_period"]} for s in data["sources"]]
    req = Request.model_validate(data)
    world = replace(draw(req, 1, 1, deterministic=True)[0], demand={"retail_A": (0., 100.)})
    result = solve(req, [world])
    assert result.status == "OPTIMAL"
    assert [result.purchases[s, 0] for s in ("s1", "s2", "s3")] == pytest.approx([17, 53, 30])


@pytest.mark.parametrize("mutation", ["future", "nan", "unknown_sku", "negative_cash_term", "duplicate", "mixed_currency", "missing_cost"])
def test_contract_fail_closed(mutation):
    req = example()
    data = req.model_dump()
    if mutation == "future":
        data["history"] = [{**r.model_dump(), "known_at": req.as_of + timedelta(days=1)} for r in req.history]
    elif mutation == "nan":
        data["liquidity"]["opening_cash"] = float("nan")
    elif mutation == "unknown_sku":
        data["sources"][0]["sku"] = "missing"
    elif mutation == "negative_cash_term":
        data["terms"][0]["deposit_fraction"] = -1
    elif mutation == "duplicate":
        data["sources"] += data["sources"]
    elif mutation == "mixed_currency":
        data["terms"][0]["currency"] = "EUR"
    else:
        del data["sources"][0]["unit_price"]
    with pytest.raises(ValidationError):
        Request.model_validate(data)


def test_censored_tail_is_not_completed_only_mean():
    req = example()
    rows = tuple(ShipmentObservation(id=str(i), known_at=req.as_of, source="main", elapsed_days=2 if i < 4 else 10,
                                    arrived=i < 4, stage="placed", carrier="c") for i in range(8))
    eta = conditional_eta(rows, "main", 0)
    assert eta.p50 == 2 and eta.p90 is None and eta.unresolved_mass == .5
    aged = conditional_eta(rows, "main", 5)
    assert aged.p50 is None and aged.unresolved_mass == 1


@pytest.mark.parametrize("direction", [1, -1])
def test_drift_requires_persistence_then_refits(direction):
    y = np.asarray([20.] * 40 + [20 + direction * 10.] * 5)
    assert change_origin(np.asarray([20.] * 40 + [20 + direction * 50.])) == 0
    assert change_origin(y) >= 39
    fitted = estimate(y, 10., .1)
    assert fitted["mean"] == pytest.approx(20 + direction * 10)


def test_intermit_zero_mass_not_clipped_residual_artifact():
    fitted = estimate(np.asarray([0., 20.] * 30), 10., 1.)
    samples = sample(fitted, np.random.default_rng(32), 10000)
    assert .4 < np.mean(samples == 0) < .6
    assert np.mean(samples) == pytest.approx(fitted["mean"], rel=.05)


def test_calendar_holiday_moves_real_arrival():
    req = example()
    data = req.model_dump()
    data["calendars"][0]["blackout_dates"] = [(req.as_of + timedelta(days=7)).date().isoformat()]
    changed = Request.model_validate(data)
    assert dates(changed, changed.sources[0], 0)[1] == 2


def test_shared_exposure_not_independent_even_with_different_suppliers():
    req = example()
    data = req.model_dump()
    data["sources"] = [*data["sources"], {**data["sources"][0], "id": "alternate", "supplier": "other", "route": ["other", "port", "branch"], "resources": ["port_cap"]}]
    req = Request.model_validate(data)
    worlds = draw(req, 5, 1000)
    corr = np.corrcoef([w.fills["main", 0] for w in worlds], [w.fills["alternate", 0] for w in worlds])[0, 1]
    assert corr > .5


def test_forced_unit_fills_never_opens_gate():
    report = plan(modified(example(), force_unit_fills=True))
    assert report["status"] != "PENDING_REVIEW"
    assert any("Unit-fill" in r for r in report["reasons"])


def test_shadow_tenant_hash_cas_and_expiry(tmp_path):
    req = example()
    report = {"operator_id": req.operator_id, "information_hash": hashlib.sha256(req.model_dump_json().encode()).hexdigest(), "status": "PENDING_REVIEW"}
    store = ShadowLedger(tmp_path / "shadow.sqlite")
    identity = store.save(req, report, req.operator_id, req.as_of)
    with pytest.raises(KeyError):
        store.get(identity, "other", req.as_of)
    with pytest.raises(ShadowConflict):
        store.review(identity, req.operator_id, "APPROVED", "0" * 64, 1, "checked", req.as_of)
    result = store.review(identity, req.operator_id, "APPROVED", report["information_hash"], 1, "checked", req.as_of)
    assert result["version"] == 2
    with pytest.raises(ShadowConflict):
        store.review(identity, req.operator_id, "REJECTED", report["information_hash"], 1, "stale", req.as_of)
    assert len(store.get(identity, req.operator_id)["events"]) == 2


def test_shadow_refuses_expired_review(tmp_path):
    req = example()
    report = {"operator_id": req.operator_id, "information_hash": hashlib.sha256(req.model_dump_json().encode()).hexdigest(), "status": "PENDING_REVIEW"}
    store = ShadowLedger(tmp_path / "shadow.sqlite")
    identity = store.save(req, report, req.operator_id, req.as_of)
    with pytest.raises(ShadowConflict):
        store.review(identity, req.operator_id, "APPROVED", report["information_hash"], 1, "late", req.as_of + timedelta(days=8))


@pytest.mark.parametrize("case", ["normal", "transfer", "substitution", "recovery"])
def test_dynamic_replay_updates_each_review_and_preserves_future_privacy(case):
    req = example(case)
    truth = draw(req, 87, 1, deterministic=True)[0]
    result = replay(req, truth, 5, "deterministic")
    assert result["status"] == "COMPLETE", result.get("failure")
    assert [r["forecast"]["retail_A"]["history_count"] for r in result["reviews"]] == [52, 53, 54, 55, 56]
    alternate = replace(truth, demand={"retail_A": (20., 20., 100., 100., 100., 100.)})
    other = replay(req, alternate, 2, "deterministic")
    assert result["reviews"][0]["purchases"] == other["reviews"][0]["purchases"]


@pytest.mark.parametrize("seed", range(10))
def test_random_identical_world_reconciliation(seed):
    req = example()
    worlds = draw(req, seed, 1)
    result = solve(req, worlds)
    actual = settle(req, result, worlds[0])
    assert actual["economic_cost"] == pytest.approx(result.projected_cost, abs=1e-4)
    assert all(r["cash"] >= req.liquidity.minimum_cash - 1e-5 for r in actual["trace"])


def test_settlement_rejects_phantom_transfer():
    req = example("transfer")
    world = draw(req, 1, 1)[0]
    result = solve(req, [world])
    invalid = replace(result, transfers={("central_branch", 20, 0): 10000.})
    with pytest.raises(PhysicalViolation):
        settle(req, invalid, world)


def test_api_shadow_requires_authentication_even_dev():
    app.dependency_overrides[require_operator] = lambda: None
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: None)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    try:
        client = TestClient(app)
        assert client.post("/api/zaad/network/shadow", json=example().model_dump(mode="json")).status_code == 401
    finally:
        app.dependency_overrides.pop(require_operator, None)


def test_api_rejects_cross_tenant():
    import duckdb
    from api.dependencies import get_conn
    app.dependency_overrides[require_operator] = lambda: "different"
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: "different")(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    # the route records the recommendation's exposure in the operator's vault (H3b); the unknown tenant must be refused as a mismatch, not as a missing vault
    app.dependency_overrides[get_conn] = lambda: duckdb.connect(":memory:")
    try:
        client = TestClient(app)
        assert client.post("/api/zaad/network/plan", json=example().model_dump(mode="json")).status_code == 403
    finally:
        app.dependency_overrides.pop(require_operator, None)
        app.dependency_overrides.pop(get_conn, None)
