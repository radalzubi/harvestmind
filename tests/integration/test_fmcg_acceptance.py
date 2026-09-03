"""FMCG acceptance: a distributor's history in, purchase recommendations
out, with explanations that reconcile and an audit record that reproduces.

The flow runs at the library layer. The HTTP API and both frontends are
still produce-shaped (kilograms, harvest, shelf life); wiring FMCG through
them is a recorded P1 in COMMERCIAL_READINESS.md, not something this test
pretends exists.
"""
from __future__ import annotations

import statistics as st

import numpy as np
import pytest

from backtesting.counterfactual import policy_selected, settle
from optimization.audit_trail import record_run
from optimization.explain import explain_schedule
from scripts.run_fmcg_counterfactuals import fold_from_history
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history


@pytest.fixture(scope="module")
def case():
    spec = ArchetypeSpec(**{**ARCHETYPES["D_importer"].__dict__, "n_skus": 16, "n_suppliers": 3,
                            "n_customers": 6, "weeks": 110})
    h = build_history("D_importer", seed=5, spec=spec)
    fi, truth = fold_from_history(h, 70, 12, 52, 3.0, 0.95)
    cap = sum(st.mean(fi.train_demand[j]) for j in fi.products) * 8.0
    return h, fi, truth, cap


def test_master_data_and_transactions_are_complete(case):
    h, *_ = case
    for t, df in h.tables().items():
        assert len(df) > 0, t
    assert {"sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units"} <= set(h.skus.columns)
    assert {"po_id", "qty_ordered", "lots"} <= set(h.purchase_orders.columns)


def test_recommendation_is_whole_lots_and_respects_moq(case):
    h, fi, truth, cap = case
    sched, meta = policy_selected(fi, cap, np.random.default_rng(0), n_scen=12)
    assert sched is not None and meta.get("selected") in ("order_up_to", "deterministic_sp", "stochastic_sp")
    for (sup, sku, t), q in sched.items():
        spec = fi.policy.pack_spec_for(sku)
        assert q >= 0
        assert abs(q / spec.lot_units - round(q / spec.lot_units)) < 1e-6, (sku, q, spec.lot_units)
        assert q == 0 or q >= spec.moq_units - 1e-6


def test_explanations_reconcile_and_cover_every_order(case):
    h, fi, truth, cap = case
    sched, meta = policy_selected(fi, cap, np.random.default_rng(0), n_scen=12)
    ex = explain_schedule(sched, demand_history=fi.train_demand, on_hand=fi.opening,
                          inbound=fi.pipeline, expected_fill={s: st.mean(v) for s, v in fi.train_fill.items()},
                          lead_of=fi.lead_of, supplier_of=fi.supplier_of,
                          service_target=fi.policy.service_target.level,
                          pack_specs=fi.policy.pack_specs, solver_status=meta.get("status", "heuristic"))
    positive = [k for k, v in sched.items() if v > 0]
    assert len(ex) == len(positive)
    for e in ex:
        assert e.order_units == pytest.approx(sched[(e.supplier_id, e.product_id, e.period)])
        text = e.as_text()
        assert "expected demand" in text and "supplier expected fill" in text and "reconciles" in text
        assert "dual" not in text and "constraint" not in text.lower()


def test_settlement_components_reconcile_to_total(case):
    h, fi, truth, cap = case
    sched, _ = policy_selected(fi, cap, np.random.default_rng(0), n_scen=12)
    s = settle(sched, fi, truth, cap)
    assert s.total == pytest.approx(s.holding + s.shortage + s.disposal + s.sla_penalty)
    assert 0.0 <= s.fill_rate <= 1.0 and s.ending_inventory >= 0


def test_audit_record_reproduces_inputs(case, tmp_path):
    h, fi, truth, cap = case
    sched, meta = policy_selected(fi, cap, np.random.default_rng(0), n_scen=12)
    rec = record_run(domain="fmcg", config={"horizon": fi.horizon, "review": 4},
                     inputs={"skus": h.skus, "orders": h.order_lines, "pos": h.purchase_orders},
                     result={"status": meta.get("status", "heuristic"), "usable": True,
                             "objective": meta.get("objective"), "warnings": meta.get("warnings", [])},
                     seed=5, scenario_config={"n_scen": 12, "seasonal": True}, data_root=tmp_path)
    rec2 = record_run(domain="fmcg", config={"horizon": fi.horizon, "review": 4},
                      inputs={"skus": h.skus, "orders": h.order_lines, "pos": h.purchase_orders},
                      result={"status": "optimal", "usable": True}, data_root=tmp_path)
    assert rec.input_hashes == rec2.input_hashes
    assert (tmp_path / "runs" / f"{rec.run_id}.json").exists()
