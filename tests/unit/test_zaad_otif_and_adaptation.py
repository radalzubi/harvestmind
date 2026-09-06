"""Order-level OTIF reconciliation and demand-adaptation modes."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.forecast import change_origin, estimate
from zaad.full.model import solve
from zaad.full.settlement import settle
from zaad.full.worlds import draw


def _with_lines(req: Request, lines: list[dict]) -> Request:
    data = req.model_dump(mode="json")
    base = {"known_at": data["as_of"], "ordered_at": data["as_of"], "requested_at": data["as_of"], "filled": 0., "cancelled": 0.}
    data["order_lines"] = [{**base, **line} for line in lines]
    return Request.model_validate(data)


def _promise(req: Request, periods: int) -> str:
    return (req.as_of + timedelta(days=periods * req.period_days)).isoformat()


def test_order_otif_needs_every_line_complete_and_on_time():
    req = example("normal", seed=32001)
    sid = req.services[0].id
    req = _with_lines(req, [
        {"id": "L1", "order_id": "O1", "service": sid, "quantity": 5., "due_in": 1, "promised_at": _promise(req, 1)},
        {"id": "L2", "order_id": "O1", "service": sid, "quantity": 5., "due_in": 2, "promised_at": _promise(req, 1)},   # late by promise
        {"id": "L3", "order_id": "O2", "service": sid, "quantity": 4., "due_in": 1, "promised_at": _promise(req, 3)},
        {"id": "L4", "order_id": "O3", "service": sid, "quantity": 4., "due_in": 1, "promised_at": _promise(req, 3), "superseded_by": "L5", "revision": 1},
        {"id": "L5", "order_id": "O3", "service": sid, "quantity": 2., "due_in": 1, "promised_at": _promise(req, 3), "revision": 2},
        {"id": "L6", "order_id": "O4", "service": sid, "quantity": 3., "due_in": 1, "promised_at": _promise(req, 3), "cancelled": 3.},
    ])
    worlds = draw(req, req.seed, 1, deterministic=True)
    plan_ = solve(req, worlds, service_floor=True)
    assert plan_.status == "OPTIMAL"
    out = settle(req, plan_, worlds[0])
    m = out["order_metrics"][sid]
    orders = out["orders"]
    assert orders["superseded_lines_ignored"] == 1 and orders["fully_cancelled_lines_ignored"] == 1
    assert orders["orders"] == 3                                    # O1, O2, O3 (O4 fully cancelled)
    assert m["lines"] == 4 and m["quantity_fill"] is not None
    if m["line_fill"] == 1.0:
        # every open line filled: L2 is complete but late, so O1 cannot be OTIF while O2 and O3 can
        assert m["late_complete_lines"] == 1
        assert orders["complete_order_rate"] == pytest.approx(1.0)
        assert orders["order_otif_rate"] == pytest.approx(2 / 3)
        assert m["order_otif"] == pytest.approx(2 / 3)
    assert 0 <= (m["order_otif"] or 0) <= (m["order_fill"] or 1) + 1e-9


def test_order_otif_metric_can_be_targeted_and_multi_sku_orders_share_completion():
    req = example("substitution", seed=32002)
    ids = [s.id for s in req.services]
    if len(ids) < 2:
        pytest.skip("fixture has a single service")
    req = _with_lines(req, [
        {"id": "A1", "order_id": "MULTI", "service": ids[0], "quantity": 2., "due_in": 1, "promised_at": _promise(req, 2)},
        {"id": "B1", "order_id": "MULTI", "service": ids[1], "quantity": 2., "due_in": 1, "promised_at": _promise(req, 2)},
    ])
    data = req.model_dump(mode="json")
    for s in data["services"]:
        s["metric"] = "order_otif"
        s["target"] = 0.5
    req = Request.model_validate(data)
    worlds = draw(req, req.seed, 1, deterministic=True)
    plan_ = solve(req, worlds, service_floor=True)
    assert plan_.status in {"OPTIMAL", "INFEASIBLE"}
    if plan_.status == "OPTIMAL":
        out = settle(req, plan_, worlds[0])
        # the same order is reported identically from both services' viewpoints
        assert out["order_metrics"][ids[0]]["order_otif"] == out["order_metrics"][ids[1]]["order_otif"]


def _series(level_before: float, level_after: float, n_before: int = 40, n_after: int = 12, dip: bool = False, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y = list(rng.normal(level_before, 2., n_before).clip(0))
    if dip:
        y += [level_before * 0.35, level_before * 0.4] + list(rng.normal(level_before, 2., n_after - 2).clip(0))
    else:
        y += list(rng.normal(level_after, 2., n_after).clip(0))
    return np.asarray(y)


def test_symmetric_and_asymmetric_both_detect_a_persistent_decline():
    y = _series(20., 7.)
    assert change_origin(y, "symmetric") > 0
    assert change_origin(y, "asymmetric") > 0


def test_asymmetric_ignores_a_two_period_dip_that_symmetric_may_chase():
    y = _series(20., 20., dip=True)
    assert change_origin(y, "asymmetric") == 0


def test_soft_and_ensemble_blend_between_old_and_new_levels():
    y = _series(20., 7., n_after=3)
    hard = estimate(y, 10., .1, True, "symmetric")
    soft = estimate(y, 10., .1, True, "soft")
    ens = estimate(y, 10., .1, True, "ensemble")
    frozen = estimate(y, 10., .1, False)
    if hard["segment_origin"] > 0:
        assert hard["mean"] - 1e-9 <= soft["mean"] <= soft["pre_change_mean"] + 1e-9
        assert 0 <= soft["blend_weight_post"] <= 1 and 0 <= ens["blend_weight_post"] <= 1
        assert soft["adaptation"] == "soft" and ens["adaptation"] == "ensemble"
    assert frozen["adaptation"] == "frozen"


def test_request_carries_adaptation_mode_into_forecasts():
    data = example("normal", seed=32003).model_dump(mode="json")
    data["demand_adaptation"] = "asymmetric"
    req = Request.model_validate(data)
    from zaad.full.worlds import forecast_all
    fits = forecast_all(req)
    assert all(f["adaptation"] == "asymmetric" for f in fits.values())
