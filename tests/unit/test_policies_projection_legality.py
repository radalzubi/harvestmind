"""The rule projections must never emit a supplier order the settlement rejects.

Reproduced on the M5 coupled experiment (first run, commit 70c10db): `economic_lot`, `reorder_point` and `periodic:1`
ended with PHYSICAL_FAILURE "pack violation" (a line capped at a maximum that is not a case multiple), "shipment exceeds
the supplier's maximum load" (line minimums alone exceed the pallet cap after the proportional scale-down, and only one
line was dropped) and "supplier minimum order value" (the MOV lift was undone by the later load-cap scaling), and the
planner abstained on the same groups because its declared incumbent had no feasible projection. A baseline that fails
its own constraints is a straw man, so the projection now applies the lot, MOV, load and cash rules jointly and cancels
an order-week it cannot make legal rather than ship an illegal one."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from zaad.full.demo import example
from zaad.full.policies import apply_order_constraints, baseline_plan, lot_round
from zaad.full.replay import replay
from zaad.public.m5 import coupled as C
from zaad.public.m5.request_builder import SeriesWeeks, WeekRecord

RULES = ("economic_lot", "reorder_point", "periodic:1")


def _series(item: str, store: str, mean: float, price: float, start: date, weeks: int, seed: int) -> SeriesWeeks:
    rng = np.random.default_rng(seed)
    rows = [WeekRecord(start + timedelta(weeks=i), start + timedelta(weeks=i, days=6), float(rng.poisson(mean)), price) for i in range(weeks)]
    return SeriesWeeks(id=f"{item}_{store}", item_id=item, store_id=store, dept_id="FOODS_3", cat_id="FOODS", weeks=rows)


def _group(store: str = "CA_9", start: date = date(2014, 1, 4)):
    specs = [("FOODS_3_001", 2.0, 3.0), ("FOODS_3_002", 2.3, 2.5), ("FOODS_3_003", 2.6, 4.0), ("FOODS_3_004", 3.0, 1.5), ("FOODS_3_005", 2.1, 6.0), ("FOODS_3_006", 12.0, 2.0)]
    return [_series(item, store, mean, price, start, 60, 100 + i) for i, (item, mean, price) in enumerate(specs)]


def test_lot_round_never_returns_a_quantity_above_a_non_multiple_maximum():
    src = example().sources[0].model_copy(update={"minimum": 12., "multiple": 6., "case_multiple": 6., "maximum": 46.})
    assert lot_round(src, 44.) == 42.                   # 44 -> 48 exceeds the cap; the largest legal lot below it
    assert lot_round(src, 46.) == 42.
    assert lot_round(src, 1.) == 12.                    # the minimum, a legal multiple
    small = src.model_copy(update={"maximum": 10.})     # no legal quantity exists: order nothing rather than breach
    assert lot_round(small, 5.) == 0.


def test_coupled_rule_projections_survive_settlement_for_every_rule():
    series = _group()
    origin = date(2014, 1, 4) + timedelta(weeks=40)
    reviews = 4
    for scenario in ("stable", "fill_only"):
        req, _ = C.build_group_request(series, origin, scenario=scenario, coupling=C.DEFAULT)
        req = req.model_copy(update={"incumbent_rule": None})
        world, _ = C.truth_world(req, series, origin, periods=reviews - 1 + req.horizon, seed=7)
        for rule in RULES:
            out = replay(req, world, reviews, rule, rolling=True)
            assert out["status"] == "COMPLETE", (scenario, rule, out.get("failure"), len(out.get("reviews", [])))
            assert len(out["reviews"]) == reviews


def test_the_coupled_group_binds_the_cap_so_the_test_is_not_vacuous():
    series = _group()
    origin = date(2014, 1, 4) + timedelta(weeks=40)
    req, record = C.build_group_request(series, origin, scenario="stable", coupling=C.DEFAULT)
    st = req.supplier_terms[0]
    # five low-volume lines whose minimum (two cases) is two pallets each: every line at its minimum already exceeds the cap
    pallets_at_minimum = sum(s.minimum / st.units_per_pallet[s.sku] for s in req.sources)
    assert pallets_at_minimum > st.max_pallets
    assert any(s.maximum % s.case_multiple for s in req.sources), "a non-multiple line cap is part of the reproduction"
    plan = baseline_plan(req.model_copy(update={"incumbent_rule": None}), "periodic:1")
    assert any(w.startswith("projection:") for w in plan.warnings), "the projection must say when it cancelled or cut an order-week"


def test_order_constraints_are_a_no_op_without_lot_mov_load_or_cash_terms():
    req = example().model_copy(update={"incumbent_rule": None})
    assert all(st.minimum_order_value == 0 and st.max_pallets is None for st in req.supplier_terms) or not req.supplier_terms
    plan = baseline_plan(req, "reorder_point")
    before = dict(plan.purchases)
    notes: list[str] = []
    apply_order_constraints(req, plan.purchases, notes)
    assert plan.purchases == before and notes == []


def test_order_constraints_are_a_no_op_on_a_single_sku_m5_request():
    """Experiment A requests carry no MOV, pallet cap or lots, so the fix cannot touch their projections."""
    from zaad.public.m5 import request_builder as RB
    s = _series("FOODS_3_777", "TX_1", 8.0, 2.5, date(2014, 1, 4), 70, 3)
    origin = date(2014, 1, 4) + timedelta(weeks=60)
    req, _ = RB.build_request(s, origin, scenario="uncertain")
    req = req.model_copy(update={"incumbent_rule": None})
    for rule in ("reorder_point", "periodic:1", "base_stock" if False else "economic_lot"):
        plan = baseline_plan(req, rule)
        before, notes = dict(plan.purchases), []
        apply_order_constraints(req, plan.purchases, notes)
        assert plan.purchases == before and notes == [] and plan.warnings == [f"baseline:{rule}"]
