"""Diagnostic report V3: the policy benchmark and ZAAD's decision replay are two separate questions, the
executive summary states both, the ledger has one canonical provenance per input, and the replay section
reports negative periods, coverage and what is measured versus simulated without inventing anything."""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_diagnostic_findings import _customer_copy, _enriched  # noqa: E402

from zaad.full import comparator
from reports.diagnostic_findings import build_report  # noqa: E402
from reports.diagnostic_pdf import render_pdf  # noqa: E402
from reports.diagnostic_v3 import canonical, consistency_checks, provenance_ledger  # noqa: E402

FIX = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def base():
    return _enriched(json.loads((FIX / "diagnostic_ntdco_old_summary.json").read_text()))


def _replay(status="complete", **over) -> dict:
    """A replay result in the shape zaad/full/historical.py returns (values synthetic)."""
    dates = [f"2026-0{5 + i // 4}-{(i % 4) * 7 + 4:02d}" for i in range(8)]
    series = [1200.0, -800.0, 2500.0, 900.0, -150.0, 700.0, 1300.0, 400.0]
    rows = []
    for t in range(8):
        for sku, sup in (("SKU-0001", "SUP-01"), ("SKU-0012", "SUP-01")):
            actual = 500.0 if t % 2 == 0 else 0.0
            zaad = 420.0 if t % 2 == 0 else (200.0 if t == 3 else 0.0)
            rows.append({"review": t, "date": dates[t], "sku": sku, "supplier": sup, "location": "main", "actual_qty": actual, "rule_qty": 480.0 if t % 2 == 0 else 0.0,
                         "zaad_qty": zaad, "quantity_difference": zaad - actual, "zaad_action": "less" if actual and zaad else ("order" if zaad else "no order"),
                         "zaad_status": "PENDING_REVIEW" if t != 5 else "RETAIN_INCUMBENT", "zaad_policy": "joint_recovery", "fallback_to_rule": t == 6,
                         "timing": "same week" if actual and zaad else ("1 week later than the operator's nearest order" if zaad else None),
                         "settlement": ("INFERRED" if zaad and actual else ("SIMULATED" if zaad else None)), "settlement_cell": "MEASURED" if actual else "SIMULATED",
                         "outcome": {"actual": {"served": 90.0, "demand": 100.0, "end_stock": 300.0}, "rule": {"served": 88.0, "demand": 100.0, "end_stock": 280.0}, "zaad": {"served": 95.0, "demand": 100.0, "end_stock": 250.0}},
                         "economic_outcome": "portfolio level (the ledger is not attributed per SKU)"})
    out = {"version": "2026.09.3", "status": status,
           "engine": {"optimizer": "zaad.full.planner.plan (production path, unchanged)", "loop": "zaad.full.replay.replay(rolling=True)", "settlement": "zaad.full.settlement.settle", "request": "zaad.full.workspace.build_request(as_of=decision date)"},
           "scope": {"skus": ["SKU-0001", "SKU-0012"], "sku_count": 2, "skus_in_workspace": 180, "demand_value_share": 0.495, "origin": "2026-05-04", "horizon": 12, "period_days": 7,
                     "reviews_planned": 8, "incumbent_rule": "periodic:2", "rule_provenance": "INFERRED_FROM_HISTORY", "history_weeks_before_origin": 40, "currency": "JOD", "inventory_locations": 1},
           "coverage": {"reviews_completed": 8, "reviews_planned": 8, "stopped_by_budget": False, "budget_s": 1200.0, "dates": dates},
           "legs": {"actual": {"status": "COMPLETE", "reviews": 8, "realized_cost": 100000.0, "continuation_cost": 90000.0, "components": {"PURCHASE": 70000.0, "CARRYING": 3000.0, "SHORTAGE": 20000.0, "FINANCING": 500.0}, "service": 0.90, "unmet_units": 800.0, "breaches": 2, "avg_inventory_units": 3000.0, "terminal_on_hand": 2000.0, "terminal_in_transit": 500.0, "units_purchased": 4000.0, "orders_placed": 8},
                    "rule": {"status": "COMPLETE", "reviews": 8, "realized_cost": 99000.0, "continuation_cost": 89500.0, "components": {"PURCHASE": 69000.0, "CARRYING": 3100.0, "SHORTAGE": 20500.0, "FINANCING": 500.0}, "service": 0.89, "unmet_units": 900.0, "breaches": 2, "avg_inventory_units": 3100.0, "terminal_on_hand": 2100.0, "terminal_in_transit": 500.0, "units_purchased": 3840.0, "orders_placed": 8},
                    "zaad": {"status": "COMPLETE", "reviews": 8, "realized_cost": 93950.0, "continuation_cost": 86000.0, "components": {"PURCHASE": 66000.0, "CARRYING": 2500.0, "SHORTAGE": 19000.0, "FINANCING": 450.0}, "service": 0.93, "unmet_units": 600.0, "breaches": 1, "avg_inventory_units": 2600.0, "terminal_on_hand": 1800.0, "terminal_in_transit": 700.0, "units_purchased": 3560.0, "orders_placed": 9}},
           "per_review": {}, "differences": {"zaad_vs_actual": {"periods": 8, "mean": 756.25, "median": 800.0, "worst": -800.0, "best": 2500.0, "share_improved": 0.75, "share_worse": 0.25, "sd": 950.0, "ci80_mean": (300.0, 1200.0),
                                                                  "window": {"base": 100000.0, "candidate": 93950.0, "difference": 6050.0, "relative": 0.061, "continuation_difference": 4000.0}, "series": series},
                                              "zaad_vs_rule": {"periods": 8, "mean": 600.0, "median": 500.0, "worst": -700.0, "best": 2000.0, "share_improved": 0.625, "share_worse": 0.375, "sd": 900.0, "ci80_mean": None,
                                                               "window": {"base": 99000.0, "candidate": 93950.0, "difference": 5050.0, "relative": 0.051, "continuation_difference": 3500.0}, "series": [s - 100 for s in series]},
                                              "rule_vs_actual": None},
           "decisions": rows, "zaad_reviews": [{"review": t, "as_of": dates[t], "status": "PENDING_REVIEW" if t != 5 else "RETAIN_INCUMBENT", "selected_policy": "joint_recovery", "fallback_to_rule": t == 6, "solve_seconds": 20.0 + t, "orchestration": {"state": "PROTECT" if t < 5 else "LEAN"}, "history_periods": 40 + t} for t in range(8)],
           "settlement_provenance": {"zaad_orders": 9, "shares_by_zaad_order": {"MEASURED": 0.0, "INFERRED": 0.89, "SIMULATED": 0.11, "ASSUMED": 0.0}, "cell_shares": {"MEASURED": 0.5, "INFERRED": 0.4, "SIMULATED": 0.1, "ASSUMED": 0.0}, "open_po": {}, "demand": "MEASURED",
                                     "rules": {"MEASURED": "m", "INFERRED": "i", "SIMULATED": "s", "ASSUMED": "a"}},
           "attestation": {"actual": {"snapshots": 8, "all_clean": True, "per_review": []}, "rule": {"snapshots": 8, "all_clean": True, "per_review": []}, "zaad": {"snapshots": 8, "all_clean": True, "per_review": []}},
           "regimes": {"by_planner_state": {"PROTECT": {"periods": 5, "mean": 750.0, "share_improved": 0.8}, "LEAN": {"periods": 3, "mean": 766.0, "share_improved": 0.67}}},
           "build": {"provenance": {"location.main.holding_per_value_period": "CONFIGURED_ASSUMPTION", "resource.SUP-01.capacity": "INFERRED_FROM_HISTORY", "incumbent_rule": "INFERRED_FROM_HISTORY"}, "fits": {"SUP-01": {"sample_size": 30}}, "warnings": [], "leakage_guard": {}},
           "performance": {"decision_points": 8, "optimizer_solves": 8, "skus": 2, "sources": 2, "solve_seconds_mean": 23.5, "solve_seconds_max": 27.0, "total_seconds": 210.0, "peak_rss_mb": 400.0},
           "actual_conformance": {"changed_orders": 0, "rows": [], "note": "n"},
           # H3a: the replay states what its historical-action comparator is (exact here: every recorded line identified and untransformed)
           "comparison": comparator.historical_comparison({"lines_observed": 8, "lines_exact": 8, "lines_incomplete": 0, "lines_unmapped": 0, "exact_quantity_share": 1.0,
                                                           "exact_value_share": 1.0, "value_share_basis": "recorded unit cost on every line", "incomplete_reasons": []},
                                                          transformed_groups=0, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=8),
           "confidence": {"level": "Moderate", "dimensions": {"counterfactual_settlement": "high", "supplier_observations": "high", "demand_history": "moderate", "opening_inventory": "high", "economics": "moderate", "capacity": "moderate", "coverage": "high"},
                          "reasons": ["40 weeks of demand history before the first decision date", "economic inputs assumed: location.main.holding per value period", "supplier capacity inferred or unbounded for 1 supplier(s)"], "rule": "the level is the weakest of ..."}}
    out.update(over)
    return out


def _text(d) -> str:
    return json.dumps(d, ensure_ascii=False)


# ── separation of the two questions ─────────────────────────────────────────
def test_benchmark_is_never_described_as_the_optimizer(base):
    base["optimizer_replay"] = _replay()
    r = build_report(base, job_id="j", company="C")
    pb = r["policy_benchmark"]
    assert pb["title"] == "Simple policy benchmark" and "fixed" in pb["question"].lower()
    text = " ".join(pb["explanation"] + [pb["statement"], pb["explainer"]]).lower()
    assert "optimizer" not in text.replace("adaptive optimizer, which is replayed separately", "")
    assert "fixed order-up-to rule" in pb["statement"].lower()
    assert "did not persist on later unseen periods" in pb["statement"]
    assert "policy_comparison" not in r
    # the benchmark candidates never carry an optimizer label
    assert not any("optimis" in c["label"].lower() or "optimiz" in c["label"].lower() for c in r["appendix"]["candidates"])


def test_executive_summary_states_both_and_headline_uses_fixed_rule_language(base):
    base["optimizer_replay"] = _replay()
    r = build_report(base, job_id="j", company="C")
    ex = r["executive_summary"]
    assert ex["benchmark"]["label"] == "SIMPLE POLICY BENCHMARK" and ex["replay"]["label"] == "ZAAD DECISION REPLAY"
    stmt = ex["replay"]["statement"]
    # H3a: an exact historical-action comparator permits a historical counterfactual difference, stated as such
    assert ex["replay"]["available"] is True and "historical counterfactual replay" in stmt and "ZAAD's modelled path cost 6.1% less than the path of the recorded historical orders" in stmt
    assert "would have" not in stmt and "your actual orders" not in stmt and "realized" in stmt
    rp = r["optimizer_replay"]
    assert rp["claim_class"] == "HISTORICAL_COUNTERFACTUAL_COMPARISON" and rp["comparison"]["permissions"]["can_claim_historical_counterfactual_difference"] is True
    assert rp["comparison"]["permissions"]["can_claim_realized_value"] is False and rp["comparison"]["decision_reference"]["provenance"] == "reconstructed from purchase-order history"
    assert "fixed alternative" in r["conclusion"]["headline"] and "optimizer" not in r["conclusion"]["headline"].lower()
    assert r["conclusion"]["replay_headline"] == ex["replay"]["statement"]
    assert ex["confidence"]["replay_level"] == "Moderate"
    ids = [f["id"] for f in r["findings"]]
    assert ids.index("policy-holdout") < ids.index("replay-result")


def test_negative_optimizer_periods_are_explained_not_hidden(base):
    base["optimizer_replay"] = _replay()
    r = build_report(base, job_id="j", company="C")
    per = r["optimizer_replay"]["periods"]
    assert per["n_negative"] == 2 and per["worst"] == -800.0 and per["worst_date"] == per["dates"][1]
    assert "more in 25%" in per["text"] and "worst period" in per["text"] and "A losing period is not a failed decision" in per["text"]
    assert "80% interval" in per["text"]
    # a window where ZAAD loses is stated as such, with no softening
    worse = _replay()
    worse["legs"]["zaad"]["realized_cost"] = 104000.0
    worse["differences"]["zaad_vs_actual"]["window"] = {"base": 100000.0, "candidate": 104000.0, "difference": -4000.0, "relative": -0.04, "continuation_difference": -3000.0}
    base["optimizer_replay"] = worse
    r2 = build_report(base, job_id="j", company="C")
    assert "cost 4.0% more than the path of the recorded historical orders" in r2["executive_summary"]["replay"]["statement"]
    cost_row = next(x for x in r2["optimizer_replay"]["table"] if x["metric"].startswith("Total modelled cost"))
    assert cost_row["better"] is False and cost_row["difference"].startswith("+4,000")


def test_replay_unavailable_never_substitutes_the_benchmark(base):
    base["optimizer_replay"] = {"status": "unavailable", "reason": "not enough history for a rolling replay: 20 weeks of orders, 16 are needed before the first decision date and 12 after the last one"}
    r = build_report(base, job_id="j", company="C")
    rp = r["optimizer_replay"]
    assert rp["available"] is False and "could not be completed" in rp["statement"] and "not a substitute" in rp["statement"]
    assert r["executive_summary"]["replay"]["available"] is False
    assert "table" not in rp and "periods" not in rp
    f = next(x for x in r["findings"] if x["id"] == "replay-unavailable")
    assert "No optimizer performance figure is reported" in f["business_implication"]
    assert render_pdf(r)[:4] == b"%PDF"


def test_replay_absent_from_old_summary(base):
    r = build_report(base, job_id="j", company="C")
    assert r["optimizer_replay"]["available"] is False and r["executive_summary"]["replay"]["available"] is False


# ── the replay section content ───────────────────────────────────────────────
def test_replay_table_only_measured_metrics_and_marks_direction(base):
    base["optimizer_replay"] = _replay()
    base["currency"] = "JOD"
    r = build_report(base, job_id="j", company="C")
    rp = r["optimizer_replay"]
    rows = {x["metric"]: x for x in rp["table"]}
    assert rows["Total modelled cost over the window"]["actual"] == "100,000 JOD" and rows["Total modelled cost over the window"]["zaad"] == "93,950 JOD"
    assert rows["Total modelled cost over the window"]["difference"] == "−6,050 JOD" and rows["Total modelled cost over the window"]["better"] is True
    assert rows["Service (share of demand served)"]["better"] is True and rows["Service (share of demand served)"]["difference"] == "+3.0%"
    assert rows["Average stock on hand (units)"]["note"].startswith("lower is not always better")
    assert rows["Units purchased"]["better"] is None or rows["Units purchased"]["better"] is False
    assert any("Waste / expiry" in n for n in rp["not_measured"]) and any("Working capital" in n for n in rp["not_measured"])
    assert rp["currency"] == "JOD" and rp["currency_note"] is None
    # no currency declared -> bare figures and one note
    base["currency"] = None
    r2 = build_report(base, job_id="j", company="C")
    assert r2["optimizer_replay"]["currency"] is None and "no currency is declared" in r2["optimizer_replay"]["currency_note"]
    assert next(x for x in r2["optimizer_replay"]["table"] if x["metric"].startswith("Total")) ["actual"] == "100,000"


def test_settlement_provenance_confidence_coverage_and_attestation(base):
    base["optimizer_replay"] = _replay()
    r = build_report(base, job_id="j", company="C")
    rp = r["optimizer_replay"]
    assert "89% on observed supplier behaviour applied to a different quantity" in rp["settlement"]["text"]
    assert "11% on a seeded draw" in rp["settlement"]["text"] and "nothing after a decision date reached the optimizer" in rp["settlement"]["text"]
    assert rp["confidence"]["level"] == "Moderate" and len(rp["confidence"]["reasons"]) == 3
    assert rp["coverage"]["completed"] == 8 and rp["coverage"]["partial"] is False and "fixed rule, not a choice of dates" in rp["coverage"]["selection_rule"]
    assert rp["lookahead"]["clean"] is True and "All checks passed" in rp["lookahead"]["text"]
    assert rp["scope"]["demand_value_share"] == 0.495 and "2 of your 180 products" in rp["scope"]["text"]
    assert [g["state"] for g in rp["regimes"]] == ["PROTECT", "LEAN"]
    assert rp["decisions_summary"]["abstained_reviews"] == 1 and rp["decisions_summary"]["retained_rule_reviews"] == 1
    assert rp["retention_note"].startswith("The optimizer retained your reconstructed rule on 1 of the 8")


def test_partial_replay_reports_coverage_honestly(base):
    rp = _replay(status="partial")
    rp["coverage"] = {"reviews_completed": 5, "reviews_planned": 26, "stopped_by_budget": True, "budget_s": 1200.0, "dates": rp["coverage"]["dates"][:5]}
    rp["confidence"]["level"] = "Low"
    rp["confidence"]["reasons"].append("5 of 26 planned decision dates completed within the time budget")
    base["optimizer_replay"] = rp
    r = build_report(base, job_id="j", company="C")
    assert "5 of 26 planned; stopped at the time budget" in r["optimizer_replay"]["coverage"]["text"]
    assert "5 of 26 planned" in r["executive_summary"]["replay"]["statement"]
    assert r["optimizer_replay"]["coverage"]["partial"] is True


def test_identical_to_rule_is_stated(base):
    rp = _replay()
    for d in rp["decisions"]:
        d["zaad_qty"] = d["rule_qty"]
    for e in rp["zaad_reviews"]:
        e["status"] = "RETAIN_INCUMBENT"
    base["optimizer_replay"] = rp
    r = build_report(base, job_id="j", company="C")
    assert r["optimizer_replay"]["decisions_summary"]["identical_to_rule"] is True
    assert "ZAAD column equals the rule column" in r["optimizer_replay"]["retention_note"]
    assert r["optimizer_replay"]["vs_rule"]["identical"] is True


def test_full_window_summary_equals_decision_level_results(base):
    """The section's counts are sums over the decision rows it exposes; nothing is stated that the rows do not carry."""
    rp = _replay()
    base["optimizer_replay"] = rp
    r = build_report(base, job_id="j", company="C")
    ds, rows = r["optimizer_replay"]["decisions_summary"], r["optimizer_replay"]["decisions"]
    assert ds["rows"] == len(rows) == 16
    assert ds["zaad_ordered_where_you_did_not"] == sum(1 for d in rows if d["zaad_action"] == "order")
    assert ds["zaad_ordered_less"] == sum(1 for d in rows if d["zaad_action"] == "less")
    assert abs(ds["units_difference"] - sum(d["quantity_difference"] for d in rows)) < 1e-6
    assert r["optimizer_replay"]["periods"]["series"] == rp["differences"]["zaad_vs_actual"]["series"]


# ── ledger and consistency ───────────────────────────────────────────────────
def test_canonical_mapping():
    assert canonical("operator") == "OPERATOR" and canonical("CUSTOMER_PROVIDED") == "OPERATOR"
    assert canonical("measured") == "MEASURED" and canonical("INFERRED_FROM_HISTORY") == "MEASURED"
    assert canonical("measured", "supplier_capacity") == "INFERRED" and canonical("INFERRED_FROM_HISTORY", "incumbent_rule") == "INFERRED"
    assert canonical("public_benchmark") == "PUBLIC_BENCHMARK" and canonical("CONFIGURED_ASSUMPTION") == "ASSUMED"
    assert canonical("unknown") == "UNKNOWN" and canonical("NOT_AVAILABLE") == "UNKNOWN" and canonical(None) == "UNKNOWN" and canonical("weird") == "UNKNOWN"


def test_provenance_ledger_one_label_per_input_and_explained_engine_differences(base):
    base["optimizer_replay"] = _replay()
    ledger = {row["input"]: row for row in provenance_ledger(base)}
    assert ledger["Supplier capacity"]["provenance"] == "INFERRED" and "1.25" in ledger["Supplier capacity"]["note"]
    assert ledger["Shortage cost (margin on a lost sale)"]["provenance"] == "UNKNOWN"
    assert ledger["Shortage cost (margin on a lost sale)"]["replay_provenance"] == "ASSUMED" and "30%" in ledger["Shortage cost (margin on a lost sale)"]["replay_note"]
    assert ledger["Carrying cost"]["provenance"] == "PUBLIC_BENCHMARK" and ledger["Your purchasing rule"]["replay_provenance"] == "INFERRED"
    assert all(row["provenance"] in ("OPERATOR", "MEASURED", "INFERRED", "PUBLIC_BENCHMARK", "ASSUMED", "UNKNOWN") for row in ledger.values())
    r = build_report(base, job_id="j", company="C")
    assert all(c["pass"] for c in r["consistency_checks"]), r["consistency_checks"]
    assert r["provenance_ledger"] == r["appendix"]["provenance_ledger"]


def test_consistency_check_fails_on_a_contradiction(base):
    base["optimizer_replay"] = _replay()
    r = build_report(base, job_id="j", company="C")
    broken = copy.deepcopy(r)
    broken["provenance_ledger"] = [dict(x, provenance="OPERATOR", note=None) if x["input"] == "Supplier capacity" else x for x in broken["provenance_ledger"]]
    checks = {c["check"]: c for c in consistency_checks(broken)}
    assert checks["supplier capacity is described the same way everywhere"]["pass"] is False
    broken2 = copy.deepcopy(r)
    broken2["policy_benchmark"]["explanation"] = ["ZAAD's optimizer failed on unseen history"]
    checks2 = {c["check"]: c for c in consistency_checks(broken2)}
    assert checks2["the policy benchmark never describes itself as ZAAD's optimizer"]["pass"] is False


# ── synthesis ────────────────────────────────────────────────────────────────
def test_synthesis_findings_are_computed_intersections(base):
    r = build_report(base, job_id="j", company="C")
    ids = {f["id"]: f for f in r["findings"]}
    # SKU-0001 and SKU-0012 sit on SUP-01 (steady): not in the deterioration set; SKU-0137 / SKU-0090 on SUP-02 (fill falling, lead 1.4x)
    # cover below lead: SKU-0137 cover 3.1 vs SUP-02 lead 4.0; SKU-0090 cover 2.0 vs 4.0  -> both, deteriorated supplier -> share 0.064 + 0.045
    f = ids["synth-cover-below-lead-and-deterioration"]
    assert f["headline"].startswith("11% of demand value") and f["materiality"] == pytest.approx(0.109)
    assert {x["id"] for x in f["related"]} == {"SKU-0137", "SKU-0090"}
    g = ids["synth-cover-below-lead-deterioration-lane"]   # both on aqaba, elevated
    assert g["severity"] == "high" and g["materiality"] == pytest.approx(0.109)
    assert "synth-intermittent-unreliable" in ids and {x["id"] for x in ids["synth-intermittent-unreliable"]["related"]} == {"SKU-0137", "SKU-0090"}
    assert "synth-open-po-lane-aqaba" in ids and "14 open purchase-order line(s)" in ids["synth-open-po-lane-aqaba"]["headline"]
    assert "synth-concentration-decline-SUP-01" not in ids   # SUP-01 is 61% but steady
    # no intersection -> no finding
    base2 = copy.deepcopy(base)
    for sp in base2["supplier_profile"].values():
        sp["fill_shift"], sp["lead_ratio"], sp["fill_mean"] = 0.0, 1.0, 0.98
    r2 = build_report(base2, job_id="j", company="C")
    assert not any(f["id"].startswith("synth-cover") or f["id"] == "synth-intermittent-unreliable" for f in r2["findings"])


# ── honesty guards on the whole V3 report ────────────────────────────────────
def test_no_fabricated_savings_null_never_zero_and_no_enum_leakage(base):
    base["optimizer_replay"] = _replay()
    r = build_report(base, job_id="j", company="C")
    body = _text(_customer_copy({k: v for k, v in r.items() if k not in ("provenance_ledger", "consistency_checks")}))
    assert "$" not in body and "ROI" not in body and re.search(r"\bsav(e|ing|ings)\b", body, re.I) is None
    assert "guarantee" not in body.lower() and "will save" not in body.lower()
    rp = r["optimizer_replay"]
    assert all(x["actual"] != "0" for x in rp["table"] if x["metric"] == "Waste / expiry")
    for enum in ("RETAIN_INCUMBENT", "PENDING_REVIEW", "gated", "INFERRED_FROM_HISTORY", "CONFIGURED_ASSUMPTION"):
        assert enum not in json.dumps({k: v for k, v in rp.items() if k not in ("decisions", "engine", "performance")}), enum


def test_deterministic_and_pdf_within_budget(base):
    base["optimizer_replay"] = _replay()
    a = build_report(base, job_id="j", company="C", generated_at="2026-09-18T00:00:00+00:00")
    b = build_report(copy.deepcopy(base), job_id="j", company="C", generated_at="2026-09-18T00:00:00+00:00")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    pdf = render_pdf(a)
    assert pdf[:4] == b"%PDF"
    pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    assert 4 <= pages <= 12, pages


# ── H3a: the comparator contract gates the replay's wording ──────────────────
def test_transformed_or_incomplete_historical_actions_are_never_called_actual_orders(base):
    transformed = _replay()
    transformed["comparison"] = comparator.historical_comparison(
        {"lines_observed": 8, "lines_exact": 8, "lines_incomplete": 0, "lines_unmapped": 0, "exact_quantity_share": 1.0, "exact_value_share": 1.0,
         "value_share_basis": "recorded unit cost on every line", "incomplete_reasons": []},
        transformed_groups=3, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=8)
    base["optimizer_replay"] = transformed
    r = build_report(base, job_id="j", company="C")
    rp, stmt = r["optimizer_replay"], r["executive_summary"]["replay"]["statement"]
    assert rp["claim_class"] == "MODEL_COMPARISON" and rp["comparison"]["comparator"]["fidelity"] == "TRANSFORMED"
    assert rp["comparison"]["permissions"]["can_claim_historical_counterfactual_difference"] is False and rp["comparison"]["permissions"]["can_claim_against_operator"] is False
    assert "a model-adjusted version of the recorded historical orders" in stmt and "not a claim against the operator" in stmt
    assert "the path of a model-adjusted version of the recorded historical orders over" in stmt and "than the path of the recorded historical orders" not in stmt
    assert "your actual orders" not in json.dumps(rp)
    incomplete = _replay()
    incomplete["comparison"] = comparator.historical_comparison(
        {"lines_observed": 8, "lines_exact": 6, "lines_incomplete": 2, "lines_unmapped": 1, "exact_quantity_share": 0.8, "exact_value_share": None,
         "value_share_basis": "unit cost missing on some lines: no value share", "incomplete_reasons": ["the record carries no supplier identity"]},
        transformed_groups=0, settlement_shares=None, rule_provenance="CUSTOMER_PROVIDED", reviews_completed=8)
    base["optimizer_replay"] = incomplete
    r = build_report(base, job_id="j", company="C")
    rp = r["optimizer_replay"]
    assert rp["comparison"]["comparator"]["fidelity"] == "INCOMPLETE" and "could not be identified" in r["executive_summary"]["replay"]["statement"]
    assert rp["reference_label"] == "the operator-declared rule" and rp["comparison"]["decision_reference"]["provenance"] == "operator-declared"
    # a replay result from before the contract never established exactness: it is not called "actual" either
    legacy = _replay()
    legacy.pop("comparison")
    base["optimizer_replay"] = legacy
    r = build_report(base, job_id="j", company="C")
    rp = r["optimizer_replay"]
    assert rp["comparison"]["comparator"]["fidelity"] == "NOT_AVAILABLE" and rp["comparison"]["permissions"]["can_claim_historical_counterfactual_difference"] is False
    assert "comparator fidelity not established" in r["executive_summary"]["replay"]["statement"] and "your actual orders" not in json.dumps(rp)
    assert "INFERRED_FROM_HISTORY" not in json.dumps({k: v for k, v in rp.items() if k not in ("decisions", "engine", "performance")})


# ── final pass, defect 3: no operator attribution the comparator contract does not support ──
def _comparison(fidelity_kind: str, rule_provenance: str = "INFERRED_FROM_HISTORY"):
    cov = {"lines_observed": 8, "lines_exact": 8 if fidelity_kind != "INCOMPLETE" else 6, "lines_incomplete": 0 if fidelity_kind != "INCOMPLETE" else 2,
           "lines_unmapped": 0 if fidelity_kind != "INCOMPLETE" else 1, "exact_quantity_share": 1.0, "exact_value_share": 1.0, "value_share_basis": "x",
           "incomplete_reasons": [] if fidelity_kind != "INCOMPLETE" else ["the record carries no supplier identity"]}
    return comparator.historical_comparison(cov, transformed_groups=1 if fidelity_kind == "TRANSFORMED" else 0, settlement_shares=None,
                                            rule_provenance=rule_provenance, reviews_completed=8)


@pytest.mark.parametrize("kind", ["EXACT", "TRANSFORMED", "INCOMPLETE", "LEGACY"])
def test_report_attribution_follows_the_comparator_contract(base, kind):
    rep = _replay()
    if kind == "LEGACY":
        rep.pop("comparison")
    else:
        rep["comparison"] = _comparison(kind)
    base["optimizer_replay"] = rep
    r = build_report(base, job_id="j", company="C")
    rp = r["optimizer_replay"]
    caption = rp["periods"]["caption"]
    assert "your orders" not in caption and "− ZAAD" in caption
    if kind == "EXACT":
        assert caption.startswith("Cost difference per decision date: the recorded historical orders − ZAAD")
    elif kind == "TRANSFORMED":
        assert "a model-adjusted version of the recorded historical orders − ZAAD" in caption
    elif kind == "INCOMPLETE":
        assert "could be identified" in caption
    else:
        assert "comparator fidelity not established" in caption
    text = json.dumps({k: v for k, v in rp.items() if k not in ("decisions", "engine", "performance")})
    assert "your orders" not in text and "your actual orders" not in text and "you / ZAAD" not in text
    pb = r["policy_benchmark"]
    assert "than your own" not in pb["question"] and "your existing purchasing rule" not in (pb.get("statement") or "")
    assert "the reconstructed historical rule" in pb["question"]
    assert "your own staggered orders" not in json.dumps(rp)


def test_benchmark_names_the_rule_by_its_provenance(base):
    base["optimizer_replay"] = _replay()
    inferred = build_report(base, job_id="j", company="C")["policy_benchmark"]
    assert inferred["reference_label"] == "the reconstructed historical rule" and "the reconstructed historical rule" in inferred["question"]
    assert "your existing" not in (inferred.get("statement") or "") and "your own" not in inferred["question"]
    declared = dict(base)
    declared["incumbent_detail"] = {**(base.get("incumbent_detail") or {}), "source": "configured"}
    pb = build_report(declared, job_id="j", company="C")["policy_benchmark"]
    assert pb["reference_label"] == "your operator-declared purchasing rule" and "your operator-declared purchasing rule" in pb["question"]
    if pb.get("outcome") == "keep_current_after_holdout":
        assert "replacing your operator-declared purchasing rule" in pb["statement"]


def test_decision_summary_wording_follows_action_fidelity(base):
    rep = _replay()
    rep["comparison"] = _comparison("INCOMPLETE")
    base_row = dict(rep["decisions"][0])
    # A: a 100-unit recorded order of the SKU could not be attributed to a source; ZAAD ordered 20 from A
    unattributed = {**base_row, "sku": "SKU-0001", "supplier": "SUP-A", "actual_qty": 0.0, "actual_observed_qty": 0.0, "actual_evaluated_qty": 0.0, "zaad_qty": 20.0,
                    "actual_identity_fidelity": "INCOMPLETE", "actual_evaluation_fidelity": None, "actual_fidelity": "INCOMPLETE",
                    "actual_unidentified_lines": 1, "actual_unidentified_qty": 100.0, "zaad_action": "order", "zaad_vs_recorded": None,
                    "comparison_basis": "unidentified", "zaad_action_label": "ordered 20; a recorded order of this SKU (100) could not be attributed to a source",
                    "quantity_difference": 20.0, "timing": None}
    # B: a recorded 103 was evaluated as 96; ZAAD ordered 100
    transformed = {**base_row, "sku": "SKU-0012", "supplier": "SUP-01", "actual_qty": 96.0, "actual_observed_qty": 103.0, "actual_evaluated_qty": 96.0, "zaad_qty": 100.0,
                   "actual_identity_fidelity": "EXACT", "actual_evaluation_fidelity": "TRANSFORMED", "actual_fidelity": "TRANSFORMED",
                   "actual_unidentified_lines": 0, "actual_unidentified_qty": 0.0, "zaad_action": "more", "zaad_vs_recorded": "less",
                   "comparison_basis": "model-evaluated", "zaad_action_label": "more than the model-evaluated quantity (96), less than the recorded order (103)",
                   "quantity_difference": 4.0, "timing": "same week"}
    rep["decisions"] = [unattributed, transformed]
    base["optimizer_replay"] = rep
    r = build_report(base, job_id="j", company="C")
    ds = r["optimizer_replay"]["decisions_summary"]
    assert ds["unattributed_recorded_rows"] == 1 and ds["zaad_ordered_where_identified_recorded_had_none"] == 0
    assert ds["zaad_less_than_recorded"] == 1 and ds["zaad_more_than_recorded"] == 0 and ds["rows_compared_on_model_evaluated_quantity"] == 1
    text = ds["text"]
    assert "ZAAD ordered where no identified recorded order existed on 0" in text
    assert "less than the recorded order on 1" in text and "more than the recorded order on 0" in text
    assert "1 product-week" in text and "could not be attributed to a source" in text and "no comparison is made" in text
    assert "where you did not" not in text and "less than you" not in text and "placed no order" not in text
    # the per-row label keeps both quantities apart
    row = next(d for d in r["optimizer_replay"]["decisions"] if d["sku"] == "SKU-0012")
    assert row["zaad_action_label"].startswith("more than the model-evaluated quantity (96), less than the recorded order (103)")
