"""The diagnostic report builder: deterministic, evidence-grounded,
customer-readable, honest about what the data cannot support.

Fixture `diagnostic_ntdco_old_summary.json` is shape-faithful to the job
summary the production diagnostic persisted before the summary was
enriched, with the values the owner quoted from the confusing report
(READY_WITH_CAVEATS; order_up_to +15.4% / lower bound +13.9% / cleared the
gate, yet the incumbent retained; SKU-0137 CV 2.04 zero-share 77%; aqaba
64%). It is not a copy of customer data."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from reports.diagnostic_findings import NOT_AVAILABLE, build_report, num, pct, weeks
from reports.diagnostic_pdf import render_pdf

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "diagnostic_ntdco_old_summary.json"


@pytest.fixture
def old_summary():
    return json.loads(FIX.read_text())


def _enriched(base: dict) -> dict:
    """The same case in the enriched shape the job now produces."""
    s = copy.deepcopy(base)
    s["summary_version"] = "2026.09.2"
    s["readiness_detail"] = {"verdict": "READY_WITH_CAVEATS", "score": 0.771, "history_weeks": 52,
                             "required_missing": [], "preferred_missing": ["stg_fmcg_skus.contribution_margin", "stg_fmcg_inventory.in_transit",
                                                                          "stg_fmcg_skus.supplier_capacity_per_week", "stg_fmcg_economics.key"],
                             "weakened_conclusions": ["shortage cost is UNKNOWN; the plan cannot price lost sales and must stay anchored to the incumbent",
                                                      "pipeline at plan time is estimated from open POs"],
                             "row_counts": {"stg_fmcg_orders": 41000, "stg_fmcg_purchase_orders": 2210, "stg_fmcg_receipts": 2100, "stg_fmcg_inventory": 180}}
    s["incumbent_detail"] = {"source": "inferred", "cover_weeks": {"SKU-0137": 3.1, "SKU-0012": 2.4, "SKU-0090": 2.0, "SKU-0001": 2.2},
                             "review_periods": {"SKU-0137": 2, "SKU-0012": 1, "SKU-0090": 1, "SKU-0001": 1}, "n_pos_used": {"SKU-0137": 9, "SKU-0012": 30, "SKU-0090": 20, "SKU-0001": 40},
                             "notes": [f"SKU-{i:04d}: inventory position at PO date unknown; cover inferred from quantity alone" for i in range(1, 41)] + ["SKU-0044: 3 POs, too few to infer a rule; default cover used"]}
    s["sku_profile"] = {
        "SKU-0001": {"supplier": "SUP-01", "periods": 52, "mean_weekly_demand": 1200.0, "demand_cv": 0.31, "zero_share": 0.0, "unit_cost": 4.2, "value_share": 0.42, "cover_periods": 0.6, "demand_shift_sd": 0.3, "demand_shift_age": None, "margin_known": True},
        "SKU-0137": {"supplier": "SUP-02", "periods": 52, "mean_weekly_demand": 14.0, "demand_cv": 2.04, "zero_share": 0.77, "unit_cost": 55.0, "value_share": 0.064, "cover_periods": 4.0, "demand_shift_sd": 0.1, "demand_shift_age": None, "margin_known": True},
        "SKU-0090": {"supplier": "SUP-02", "periods": 52, "mean_weekly_demand": 60.0, "demand_cv": 1.15, "zero_share": 0.41, "unit_cost": 9.0, "value_share": 0.045, "cover_periods": 1.8, "demand_shift_sd": 2.6, "demand_shift_age": 5, "margin_known": False},
        "SKU-0012": {"supplier": "SUP-01", "periods": 52, "mean_weekly_demand": 300.0, "demand_cv": 0.4, "zero_share": 0.02, "unit_cost": 3.0, "value_share": 0.075, "cover_periods": 2.5, "demand_shift_sd": 0.0, "demand_shift_age": None, "margin_known": True},
    }
    s["supplier_profile"] = {
        "SUP-01": {"n_receipts": 30, "n_skus": 120, "skus": ["SKU-0001", "SKU-0012"], "value_share": 0.61, "lane": "aqaba", "lead_weeks_assumed": 3, "fill_mean": 0.97, "fill_min": 0.8, "short_receipts": 3, "fill_recent": 0.96, "lead_mean_weeks": 3.1, "lead_max_weeks": 5.0, "lead_sd_weeks": 0.7, "lead_recent_weeks": 3.2, "dominant": "NORMAL", "stress": 0.2, "reasons": [], "fill_shift": -0.01, "lead_ratio": 1.03, "change_point": False},
        "SUP-02": {"n_receipts": 12, "n_skus": 40, "skus": ["SKU-0137", "SKU-0090"], "value_share": 0.3, "lane": "aqaba", "lead_weeks_assumed": 4, "fill_mean": 0.9, "fill_min": 0.6, "short_receipts": 5, "fill_recent": 0.78, "lead_mean_weeks": 4.0, "lead_max_weeks": 9.0, "lead_sd_weeks": 2.3, "lead_recent_weeks": 5.6, "dominant": "TIGHT", "stress": 0.6, "reasons": ["lead time 1.4x its long-run mean"], "fill_shift": -0.12, "lead_ratio": 1.4, "change_point": True},
        "SUP-05": {"n_receipts": 3, "n_skus": 20, "skus": [], "value_share": 0.09, "lane": None, "lead_weeks_assumed": 2, "fill_assumed": 0.95},
    }
    s["candidate_evidence"] = {
        "order_up_to": {"mean": 0.154, "lower_bound": 0.139, "worst": 0.121, "best": 0.19, "win_rate": 1.0, "downside_regret": 0.0, "n_folds": 4, "passed": True,
                        "gates": {"enough_folds": True, "lower_bound_exceeds_threshold": True, "service_non_inferior": True, "downside_within_budget": True, "no_fallbacks": True},
                        "fold_deltas": [0.121, 0.16, 0.19, 0.145], "service_diff_min": -0.004, "service_diff_mean": 0.001, "inventory_diff_mean": -120.0, "solves_usable": 4, "fallbacks": 0,
                        "holdout_mean": 0.012, "holdout_lower_bound": -0.03, "holdout_worst": -0.02,
                        "holdout_gates": {"complete": True, "no_fallbacks": True, "lower_bound_exceeds_threshold": False, "service_non_inferior": True, "downside_within_budget": True}},
        "stochastic_sp": {"mean": 0.033, "lower_bound": -0.012, "worst": -0.05, "best": 0.1, "win_rate": 0.5, "downside_regret": 0.05, "n_folds": 4, "passed": False,
                          "gates": {"enough_folds": True, "lower_bound_exceeds_threshold": False, "service_non_inferior": True, "downside_within_budget": True, "no_fallbacks": True},
                          "fold_deltas": [-0.05, 0.1, 0.02, 0.06], "service_diff_min": -0.002, "service_diff_mean": 0.0, "inventory_diff_mean": 0.0, "solves_usable": 4, "fallbacks": 0,
                          "holdout_mean": None, "holdout_lower_bound": None, "holdout_worst": None, "holdout_gates": {}},
    }
    s["gate_config"] = {"n_folds": 4, "n_holdout_folds": 2, "holdout": 4, "min_history": 26, "min_rel_improvement": 0.03, "service_tolerance": 0.01,
                        "max_regret_share": 0.1, "confidence": 0.8, "n_scen": 20, "prefer_simpler_within": 0.01}
    s["lane_detail"] = {"aqaba": {"risk": 0.64, "quality": 0.42, "contributions": {"chokepoint:bab_el_mandeb": 1.95, "gscpi": 0.97, "fuel_index": 0.43},
                                  "missing": ["port:AQABA", "freight_index_yoy"], "stale": [], "reasons": s["lanes"]["aqaba"]["reasons"]}}
    s["lane_exposure"] = {"aqaba": {"suppliers": ["SUP-01", "SUP-02"], "n_skus": 160, "skus": ["SKU-0001", "SKU-0137"], "value_share": 0.91,
                                    "open_po_estimate": {"lines": 14, "units": 42000.0, "skus": 11, "basis": "PO lines without a matching receipt in the last 8 weeks of history"}}}
    s["carrying_cost"] = {"cost_of_capital": 0.0019, "storage_handling": 0.0015, "insurance": 0.0002, "shrink_obsolescence": 0.001, "total_per_week": 0.0046}
    s["carrying_cost_sensitivity"] = [{"multiplier": 0.5, "per_period_rate": 0.0023, "annual_rate": 0.12}, {"multiplier": 1.0, "per_period_rate": 0.0046, "annual_rate": 0.24}, {"multiplier": 2.0, "per_period_rate": 0.0092, "annual_rate": 0.48}]
    s["unknown_margin_skus"] = ["SKU-0090"] + [f"SKU-{i:04d}" for i in range(200, 222)]
    s["unknown_margin_count"] = 23
    s["history_range"] = {"orders_from": "2025-08-04", "orders_to": "2026-08-02", "order_lines": 41000, "pos_from": "2025-08-04", "pos_to": "2026-07-30", "po_lines": 2210, "receipt_lines": 2100}
    s["currency"] = None
    return s


def _all_text(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False)


def _customer_copy(report: dict) -> dict:
    """The report minus the appendix and the fields marked internal (ids and
    keys the UI uses for links, never rendered as prose)."""
    body = copy.deepcopy({k: v for k, v in report.items() if k != "appendix"})
    for f in body["findings"]:
        f.pop("id", None)
    body["policy_comparison"].pop("internal", None)
    body["policy_comparison"].pop("candidate", None)
    for ln in body["lanes"]:
        ln.pop("internal", None)
    for k in ("internal_verdict", "missing_fields", "required_missing"):
        body["readiness"].pop(k, None)
    body["ordering_today"].pop("internal_label", None)
    for li in body["readiness"]["limitations"]:
        li.pop("internal", None)
    return body


# ── the confusing case ───────────────────────────────────────────────────────
def test_incumbent_retained_despite_strong_candidate_is_explained_old_shape(old_summary):
    r = build_report(old_summary, job_id="job_x", company="NTDCO", generated_at="2026-09-17T00:00:00+00:00")
    pc = r["policy_comparison"]
    assert pc["outcome"] == "keep_current_after_holdout" and pc["candidate"] == "order_up_to"
    text = " ".join(pc["explanation"])
    assert "15.4% less" in text and "+13.9%" in text
    assert "cleared ZAAD's selection rule" in text
    assert "2 unseen historical validation periods" in text and "+1.2%" in text
    assert "Your current purchasing policy was retained" in text
    assert "can clear the selection threshold and still not be selected" in text
    assert r["conclusion"]["kind"] == "keep_current"
    assert "did not hold up on unseen periods" in r["conclusion"]["headline"]
    # the internal enum never reaches customer-facing copy outside the appendix and the internal fields
    body = json.dumps(_customer_copy(r))
    assert "READY_WITH_CAVEATS" not in body and "incumbent" not in body.lower()
    assert r["readiness"]["label"] == "GOOD ENOUGH TO ANALYZE — WITH LIMITATIONS"
    assert r["appendix"]["run"]["internal_readiness_verdict"] == "READY_WITH_CAVEATS"


def test_incumbent_retained_despite_strong_candidate_enriched_shape(old_summary):
    s = _enriched(old_summary)
    r = build_report(s, job_id="job_y", company="NTDCO", generated_at="2026-09-17T00:00:00+00:00")
    pc = r["policy_comparison"]
    assert pc["outcome"] == "keep_current_after_holdout"
    text = " ".join(pc["explanation"])
    assert "exceed 3.0%" in text and "80% confidence" in " ".join(x["difference"] for x in pc["rows"])
    assert "lower bound of -3.0%" in text
    assert pc["fold_chart"]["selection"] == [0.121, 0.16, 0.19, 0.145] and pc["fold_chart"]["holdout_mean"] == 0.012
    rows = {x["metric"]: x for x in pc["rows"]}
    assert rows["Operating cost on the same history"]["candidate"] == "15.4% lower"
    assert rows["Worst historical period"]["candidate"] == "+12.1%"
    assert rows["Periods where the candidate cost less"]["candidate"] == "100% of periods"
    assert rows["Service (fill rate) difference"]["candidate"] == "-0.4 pts in the worst period"
    assert rows["Inventory held"]["candidate"] == NOT_AVAILABLE
    top = r["executive_summary"]["findings"][0]
    assert top["id"] == "policy-holdout" and "only +1.2%" in top["line"]


# ── data findings ────────────────────────────────────────────────────────────
def test_missing_inventory_at_po_date(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    f = next(x for x in r["findings"] if x["id"] == "data-inventory-at-po")
    assert f["observation"].startswith("For 40 product(s)") and f["confidence"] == "High"
    assert "inventory snapshots" in f["recommendation"]
    assert any("stock-on-hand at order date" in a["text"] or "inventory snapshots" in a["text"] for a in r["actions"]["next"])
    # the old shape kept only five notes, so it says "at least"
    r_old = build_report(old_summary, job_id="j", company="C")
    f_old = next(x for x in r_old["findings"] if x["id"] == "data-inventory-at-po")
    assert f_old["observation"].startswith("For at least 4 product(s)")


def test_intermittent_demand_sku_is_translated(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    f = next(x for x in r["findings"] if x["id"] == "demand-intermittent-SKU-0137")
    assert f["headline"] == "SKU-0137 — highly intermittent demand"
    assert "Demand was zero in 77% of the 52 observed weeks" in f["observation"]
    assert "should not automatically be managed with the same replenishment logic" in f["business_implication"]
    ev = {e["label"]: e["value"] for e in f["evidence"]}
    assert ev["Demand variability (coefficient of variation)"] == "2.04"     # a CV is never shown as a percentage
    assert ev["Weeks with zero demand"] == "77%"
    assert f["related"] == [{"kind": "sku", "id": "SKU-0137", "label": "SKU-0137"}]
    assert f["materiality"] == 0.064 and f["driver_tag"] == "OBSERVED"
    # ranked by value share among demand findings: SKU-0137 (6.4%) before SKU-0090 (4.5%)
    ids = [x["id"] for x in r["findings"] if x["id"].startswith("demand-intermittent-")]
    assert ids.index("demand-intermittent-SKU-0137") < ids.index("demand-intermittent-SKU-0090")


def test_lane_risk_has_meaning_evidence_exposure_and_response(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    ln = r["lanes"][0]
    assert ln["lane"] == "aqaba" and ln["attention"] == "ELEVATED" and ln["score"] == "64%"
    assert "not a probability calibrated on your own shipments" in ln["score_meaning"]
    assert ln["evidence_strength"] == "moderate" and "42% of the lane's indicator feeds" in ln["evidence_note"]
    assert "Bab el-Mandeb transits at 61% of their trailing norm" in ln["external"]
    assert any("2 supplier(s): SUP-01, SUP-02" in x for x in ln["exposure"])
    assert any("91.0% of demand value" in x for x in ln["exposure"])
    assert any("14 purchase-order line(s) without a receipt" in x and "42,000 units" in x for x in ln["exposure"])
    assert any("no currency declared" in x for x in ln["exposure"])
    assert "does not infer an alternative route" in ln["response"] and "rerout" not in ln["response"].lower()
    assert any("Aqaba" in m["text"] for m in r["actions"]["monitor"])


def test_no_external_lane_evidence_is_unavailable_not_normal(old_summary):
    s = _enriched(old_summary)
    s["lanes"] = {"haifa": {"risk": 0.1, "quality": 0.0, "reasons": ["no leading indicators available for this lane; outlook UNAVAILABLE"], "missing": ["port:HAIFA"]}}
    s["lane_detail"] = {}
    s["lane_exposure"] = {}
    r = build_report(s, job_id="j", company="C")
    ln = r["lanes"][0]
    assert ln["attention"] == "UNAVAILABLE" and ln["evidence_strength"] == "none"
    assert "widened its uncertainty rather than assuming normal conditions" in ln["response"]
    assert not any("Haifa" in m["text"] for m in r["actions"]["monitor"])


def test_missing_supplier_capacity_and_public_carrying_cost(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    ids = {f["id"]: f for f in r["findings"]}
    assert "data-capacity" in ids and "1.25 ×" in ids["data-capacity"]["observation"]
    assert "data-carrying" in ids and "24% of inventory value per year" in ids["data-carrying"]["observation"]
    assert any(a["input"] == "holding rate per period" and a["provenance"] == "public_benchmark" for a in r["appendix"]["assumptions"])
    assert [x["annual_rate"] for x in r["appendix"]["carrying_cost_sensitivity"]] == [0.12, 0.24, 0.48]
    s = _enriched(old_summary)
    s["provenance"]["holding_rate_per_period"] = "operator"
    s["provenance"]["supplier_capacity"] = "operator"
    r2 = build_report(s, job_id="j", company="C")
    assert "data-capacity" not in {f["id"] for f in r2["findings"]} and "data-carrying" not in {f["id"] for f in r2["findings"]}


def test_supplier_findings_from_receipts(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    ids = {f["id"]: f for f in r["findings"]}
    assert "supplier-fill-decline-SUP-02" in ids and "78%" in ids["supplier-fill-decline-SUP-02"]["observation"]
    assert ids["supplier-fill-decline-SUP-02"]["confidence"] == "High"      # 12 receipts
    assert "supplier-lead-drift-SUP-02" in ids and "1.4×" in ids["supplier-lead-drift-SUP-02"]["observation"]
    assert "supplier-concentration-SUP-01" in ids and "61%" in ids["supplier-concentration-SUP-01"]["headline"]
    assert "supplier-few-receipts" in ids and "SUP-05" in ids["supplier-few-receipts"]["observation"]
    rows = {x["supplier"]: x for x in r["suppliers"]["rows"]}
    assert rows["SUP-02"]["reading"] == "fill falling, lead lengthening" and rows["SUP-01"]["reading"] == "steady"
    assert rows["SUP-05"]["reading"] == "too few receipts to judge" and rows["SUP-05"]["fill"].startswith("assumed")


def test_thin_cover_uses_open_orders_link(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    f = next(x for x in r["findings"] if x["id"] == "inventory-thin-cover")
    assert "1 product(s) had under one week of cover" in f["headline"]
    assert {"kind": "po", "id": "open", "label": "Purchase orders"} in f["related"]


# ── degenerate results ───────────────────────────────────────────────────────
def test_no_plan_no_policy_result():
    s = {"sector": "commercial", "readiness": {"verdict": "READY_WITH_CAVEATS", "score": 0.7, "missing": []},
         "incumbent": "client policy (INFERRED from PO history)", "incumbent_notes": [], "history_periods": 20, "products": 5, "suppliers": 1,
         "decision": "incumbent", "reason": "insufficient history (20 < 26 periods); no candidate can be evidenced, incumbent retained",
         "improvement": None, "candidates": {}, "state": {"mode": "normal", "dominant": "NORMAL", "p_disruptive": 0.1, "stress": 0.1, "reasons": []},
         "lanes": {}, "signal_sources": {}, "priors_in_use": {}, "provenance": {}, "warnings": []}
    r = build_report(s, job_id="j", company="C")
    assert r["policy_comparison"]["available"] is False and r["policy_comparison"]["outcome"] == "not_run"
    assert "insufficient history (20 < 26 periods)" in r["policy_comparison"]["explanation"][0]
    assert r["conclusion"]["kind"] == "not_run" and r["readiness"]["confidence"] == "Low"
    assert r["actions"]["now"][0]["text"] == "Keep your current purchasing policy."
    assert render_pdf(r)[:4] == b"%PDF"


def test_genuinely_insufficient_data():
    s = {"sector": "commercial", "readiness": {"verdict": "NOT_READY: required fields missing", "score": 0.0, "missing": ["stg_fmcg_receipts: no rows"]},
         "readiness_detail": {"verdict": "NOT_READY: required fields missing", "required_missing": ["stg_fmcg_receipts: no rows"], "history_weeks": 10},
         "decision": None, "reason": None, "candidates": {}, "warnings": []}
    r = build_report(s, job_id="j", company="C")
    assert r["readiness"]["level"] == "not_ready" and r["readiness"]["label"] == "NOT ENOUGH DATA TO ANALYZE"
    assert r["conclusion"]["kind"] == "insufficient_data"
    assert r["readiness"]["required_missing"] == ["stg_fmcg_receipts: no rows"]
    assert render_pdf(r)[:4] == b"%PDF"


def test_null_is_never_shown_as_zero(old_summary):
    s = _enriched(old_summary)
    s["sku_profile"]["SKU-0137"]["value_share"] = None
    s["supplier_profile"]["SUP-02"]["lead_sd_weeks"] = None
    s["candidate_evidence"]["order_up_to"]["worst"] = None
    s["candidate_evidence"]["order_up_to"]["service_diff_min"] = None
    r = build_report(s, job_id="j", company="C")
    f = next(x for x in r["findings"] if x["id"] == "demand-intermittent-SKU-0137")
    assert {e["label"]: e["value"] for e in f["evidence"]}["Share of demand value"] == NOT_AVAILABLE and f["materiality"] is None
    rows = {x["metric"]: x for x in r["policy_comparison"]["rows"]}
    assert "Worst historical period" not in rows
    assert rows["Service (fill rate) difference"]["candidate"] == NOT_AVAILABLE
    assert "0.0%" not in rows["Service (fill rate) difference"]["candidate"]
    sup = {x["supplier"]: x for x in r["suppliers"]["rows"]}["SUP-02"]
    assert sup["lead_spread"] == NOT_AVAILABLE
    assert pct(None) == NOT_AVAILABLE and num(None) == NOT_AVAILABLE and weeks(None) == NOT_AVAILABLE


def test_no_fabricated_roi_or_savings(old_summary):
    for s in (old_summary, _enriched(old_summary)):
        r = build_report(s, job_id="j", company="C")
        text = _all_text({k: v for k, v in r.items() if k != "appendix"})
        assert "$" not in text and "ROI" not in text and "stockout reduction" not in text.lower()
        assert re.search(r"\bsav(e|ing|ings)\b", text, re.I) is None
        assert "working capital" not in text.lower() or "not reported separately" in text.lower()


def test_identifiers_are_only_those_in_the_summary(old_summary):
    s = _enriched(old_summary)
    r = build_report(s, job_id="j", company="NTDCO")
    text = _all_text(r)
    known = set(s["sku_profile"]) | set(s["supplier_profile"]) | set(s["unknown_margin_skus"]) | {n.split(":")[0] for n in s["incumbent_detail"]["notes"]}
    for ident in set(re.findall(r"\b(?:SKU|SUP)-\d{2,4}\b", text)):
        assert ident in known, ident


def test_deterministic_wording(old_summary):
    s = _enriched(old_summary)
    a = build_report(s, job_id="j", company="C", generated_at="2026-09-17T00:00:00+00:00")
    b = build_report(copy.deepcopy(s), job_id="j", company="C", generated_at="2026-09-17T00:00:00+00:00")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_formatting_and_rounding():
    assert pct(0.064) == "6.4%" and pct(0.064, signed=True) == "+6.4%" and pct(-0.0123) == "-1.2%"
    assert pct(0.8, nd=0) == "80%" and pct(0.0) == "0.0%"
    assert num(1234567) == "1,234,567" and num(42000.0) == "42,000" and num(3.14159, 2) == "3.14"
    assert weeks(3.0) == "3 weeks" and weeks(1.0) == "1 week" and weeks(2.75) == "2.8 weeks" and weeks(2.75, 0) == "3 weeks"
    assert pct(float("nan")) == NOT_AVAILABLE and num("x") == NOT_AVAILABLE


def test_no_raw_floats_or_enums_in_customer_copy(old_summary):
    r = build_report(_enriched(old_summary), job_id="j", company="C")
    text = _all_text(_customer_copy(r))
    assert "the your" not in text and "anchored to your current policy" in text
    assert not re.search(r"\d\.\d{4,}", text), re.search(r"\S*\d\.\d{4,}\S*", text).group(0)
    for enum in ("READY_WITH_CAVEATS", "order_up_to", "stochastic_sp", "held-out fold", "zero-share", "incumbent"):
        assert enum not in text, enum


def test_provenance_and_run_identity(old_summary):
    r = build_report(_enriched(old_summary), job_id="job_abc", company="C", generated_at="2026-09-17T10:00:00+00:00")
    run = r["appendix"]["run"]
    assert run["run_id"] == "job_abc" and run["generated_at"] == "2026-09-17T10:00:00+00:00"
    assert run["report_version"] == r["version"] and run["summary_version"] == "2026.09.2"
    assert run["history_range"]["orders_from"] == "2025-08-04"
    inputs = {a["input"]: a["provenance"] for a in r["appendix"]["assumptions"]}
    assert inputs["shortage cost per unit"] == "unknown" and inputs["supplier fill"] == "measured"
    assert "lead-time variability, supplier SUP-05" in inputs
    cands = {c["candidate"]: c for c in r["appendix"]["candidates"]}
    assert cands["order_up_to"]["inner_gates"] == "cleared" and "did not hold" in cands["order_up_to"]["holdout"]
    assert cands["stochastic_sp"]["holdout"] == "not re-tested (did not win selection)"
    assert any("winner's curse" in m for m in r["appendix"]["methodology"])
    assert r["readiness"]["confidence_rule"] in " ".join(r["appendix"]["methodology"])


def test_candidate_adopted_case(old_summary):
    s = _enriched(old_summary)
    s["decision"] = "order_up_to"
    s["reason"] = "order_up_to clears the gate: conservative lower bound +13.9% of incumbent cost over 4 folds, service non-inferior, downside within budget, confirmed on held-out folds"
    s["candidate_evidence"]["order_up_to"]["holdout_mean"] = 0.11
    s["candidate_evidence"]["order_up_to"]["holdout_lower_bound"] = 0.06
    s["candidate_evidence"]["order_up_to"]["holdout_gates"] = {k: True for k in s["candidate_evidence"]["order_up_to"]["holdout_gates"]}
    r = build_report(s, job_id="j", company="C")
    assert r["policy_comparison"]["outcome"] == "adopt_candidate" and r["conclusion"]["kind"] == "adopt_candidate"
    assert r["actions"]["now"][0]["link"]["kind"] == "decision"
    assert any(f["id"] == "policy-adopt" for f in r["findings"])
    top = r["executive_summary"]["findings"][0]
    assert top["id"] == "policy-adopt" and "held its advantage on the unseen validation periods (+11.0%)" in top["line"]


def test_produce_sector_report_renders():
    s = {"sector": "produce", "readiness": {"verdict": "READY", "score": 1.0, "missing": []},
         "benchmark": {"status": "ok", "gate_passed": False, "verdict": "baseline retained: stochastic plan not better on rolling origins", "weeks_available": 30, "weeks_required": 26,
                       "summary": {"waste_share": 0.04}},
         "decision": "baseline retained", "reason": "baseline retained", "warnings": []}
    r = build_report(s, job_id="j", company="Green Hub")
    assert r["sector"] == "produce" and r["conclusion"]["kind"] == "keep_current"
    assert render_pdf(r)[:4] == b"%PDF"


def test_pdf_renders_both_shapes_within_page_budget(old_summary):
    for s in (old_summary, _enriched(old_summary)):
        r = build_report(s, job_id="job_ntdco", company="NTDCO", generated_at="2026-09-17T00:00:00+00:00")
        pdf = render_pdf(r)
        assert pdf[:4] == b"%PDF"
        pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
        assert 3 <= pages <= 8, pages
