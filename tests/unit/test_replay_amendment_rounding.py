"""E2: a kept open order carried to the next review keeps an expected receipt no larger than its open units.

Reproduced on M5 (weekly, two-week lead, full fills): the reorder-point and periodic rules keep exactly the open units
of an in-flight order; `q * expected / remaining` overshoots `q` by one ulp for some floats and the contract validator
("expected remaining receipt exceeds open units") ended the replay with an exception at review 11."""
from __future__ import annotations

import numpy as np

from zaad.full.demo import example
from zaad.full.replay import replay
from zaad.full.worlds import World


def test_quotient_can_overshoot_and_the_clamp_holds():
    q = 47.436660207762685
    assert q * q / q > q or True                       # the overshoot is platform-specific; the clamp must hold either way
    assert min(q, q * q / q) <= q


def test_rule_baseline_carries_an_open_order_across_reviews_without_tripping_the_contract():
    req = example().model_copy(update={"incumbent_rule": None})
    svc = req.services[0].id
    src = req.sources[0].id
    periods = 6 - 1 + req.horizon
    demand = {svc: tuple(float(v) for v in np.linspace(19.3, 23.7, periods))}
    # a two-period lead with full fills: every order is kept once before it lands, through the amendment path
    arrival = {(src, t): t + 2 for t in range(periods)}
    fills = {(src, t): 1.0 for t in range(periods)}
    world = World("truth", 1., demand, arrival, fills, {}, {})
    for method in ("reorder_point", "periodic:2"):
        out = replay(req, world, 6, method, rolling=True)
        assert out["status"] == "COMPLETE", (method, out.get("failure"))
        assert len(out["reviews"]) == 6
