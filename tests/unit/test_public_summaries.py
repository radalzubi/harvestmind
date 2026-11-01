"""The public-data summarisers: cross-stage pairing only over series both stages completed; coupled breaches and projection notes counted."""
from __future__ import annotations

from scripts import frn_compare, frn_summarize as S, m5_coupled_summarize as CS


def _row(policy, store, product, cont, fill, *, status="COMPLETE", window="final", track="observed", scenario="stable", warnings=(), provenance=None):
    return {"window": window, "track": track, "scenario": scenario, "policy": policy, "store_id": store, "product_id": product, "status": status,
            "endpoint": {"continuation": cont, "realized": cont + 1., "service": fill, "unmet": 0., "breaches": 0, "avg_inventory_units": 10., "components": {}} if status == "COMPLETE" else None,
            "derived": {"warnings": list(warnings), "reviews_completed": 3}, "provenance": provenance, "group": [product]}


def test_cross_stage_pairs_only_series_completed_in_both_stages():
    a = [_row("gated", "s", "p1", 10., .9), _row("gated", "s", "p2", 20., .9), _row("gated", "s", "p3", 5., .9, status="ABSTAIN")]
    b = [_row("gated", "s", "p1", 8., .95), _row("gated", "s", "p2", 21., .9), _row("gated", "s", "p3", 4., .9)]
    out = frn_compare.cross_stage(a, b, reps=200)
    cell = out["final|observed|stable"]
    assert cell["series_in_both"] == 2 and cell["only_in_a"] == 0 and cell["only_in_b"] == 1
    assert abs(cell["mean_difference_b_minus_a"] - ((8. - 10.) + (21. - 20.)) / 2) < 1e-9
    assert cell["b_better"] == 1 and cell["b_worse"] == 1


def test_within_stage_summary_reports_completion_and_the_reorder_point_pairing():
    rows = [_row("gated", "s", "p1", 10., .9), _row("gated", "s", "p2", 20., .9), _row("reorder_point", "s", "p1", 12., .9), _row("reorder_point", "s", "p2", 19., .9),
            _row("gated", "s", "p3", 1., .9, status="INFEASIBLE")]
    cell = frn_compare.cell_summary(rows)["final|observed|stable"]
    assert cell["zaad_complete"] == 2 and cell["zaad_runs"] == 3 and cell["zaad_statuses"]["INFEASIBLE"] == 1
    assert cell["paired"]["series"] == 2 and abs(cell["paired"]["mean_difference_zaad_minus_baseline"] - ((10 - 12) + (20 - 19)) / 2) < 1e-9


def test_coupled_group_table_counts_physical_failures_abstentions_and_projection_notes():
    rows = [_row("economic_lot", "CA_1", "a+b", 100., .95, warnings=["baseline:economic_lot", "projection:load_cap:declared_supplier:0:3 lines wanted 8.00 pallets, 2 shipped", "projection:cancelled:declared_supplier:2:supplier minimum order value"]),
            _row("economic_lot", "CA_2", "c+d", 100., .95, status="PHYSICAL_FAILURE"),
            _row("gated", "CA_1", "a+b", 90., .96, provenance={"own_share": .5, "RETAINED_INCUMBENT": 1}), _row("gated", "CA_2", "c+d", 1., .9, status="ABSTAIN")]
    for r in rows:
        r["failure"] = "pack violation" if r["status"] == "PHYSICAL_FAILURE" else None
    table = CS.group_table(rows)
    lot = table["final|stable|economic_lot"]
    assert lot["physical_failures"] == 1 and lot["complete"] == 1 and lot["breach_reasons"] == {"pack violation": 1}
    assert lot["projection_cancelled_order_weeks"]["mean"] == 1 and lot["projection_cut_order_weeks"]["mean"] == 1
    assert table["final|stable|gated"]["abstained"] == 1 and table["final|stable|gated"]["zaad_own_share"]["mean"] == .5
    fails = CS.failures(rows)
    assert fails["completion_by_policy"]["economic_lot"]["PHYSICAL_FAILURE"] == 1 and fails["completion_by_policy"]["gated"]["ABSTAIN"] == 1
    S.BASELINES = CS.BASELINES
    pairs = S.paired(rows, reps=100)
    assert "final|observed|stable|economic_lot|continuation_cost" not in pairs      # one common group: no interval is fabricated from a single pair


def test_markdown_tables_use_the_paired_metric_name():
    """The paired continuation table was empty in every earlier summary because it filtered on the endpoint key, not the metric name."""
    rows = [_row("gated", "s", "p1", 10., .9), _row("gated", "s", "p2", 20., .9), _row("reorder_point", "s", "p1", 12., .9), _row("reorder_point", "s", "p2", 19., .9)]
    S.BASELINES = ("reorder_point", "periodic:1", "base_stock", "order_up_to")
    pairs = S.paired(rows, reps=100)
    md = S.markdown("x", S.policy_table(rows), pairs, S.failures(rows), {"commit": "c", "runs": 4, "complete": 4, "failed": 0})
    assert "| final | observed | stable | reorder_point | 2 |" in md
