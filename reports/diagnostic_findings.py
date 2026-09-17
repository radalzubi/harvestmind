"""The diagnostic report as structured findings: what we found, why it
matters, what appears to cause it, what ZAAD recommends, how confident.

`build_report(summary, ...)` turns the diagnostic job summary into a
report model that the PDF (`reports/diagnostic_pdf.py`) and the in-app
result view both render, so they cannot tell different stories.

Rules of this module
  * Deterministic. The same summary always yields the same report (only
    `generated_at` is passed in). No model API is involved anywhere.
  * Evidence-grounded. Every finding carries the numbers it rests on, and
    every number comes from the summary. Nothing is estimated here that
    the diagnostic did not measure; a metric the data cannot support is
    reported as "Not available from current data" with the field that
    would make it possible. Zero is never shown for an unknown.
  * No fabricated benefit. There is no savings, ROI, stockout-reduction or
    working-capital figure anywhere. Cost changes are the backtest's own
    relative measurements on the operator's history, labelled as such.
  * Customer-readable. Internal labels (READY_WITH_CAVEATS, incumbent,
    folds, CV, zero-share, gate) are translated in the body; the exact
    terms live in the methodology appendix.
  * Old summaries render. A job persisted before the summary was enriched
    lacks `candidate_evidence`; the held-out explanation then falls back to
    the selector's reason string.
"""
from __future__ import annotations

import math
import re
import statistics as st
from typing import Any

REPORT_VERSION = "2026.09.2"
NOT_AVAILABLE = "Not available from current data"

CANDIDATE_LABEL = {
    "order_up_to": "an order-up-to (cover level) policy",
    "deterministic_sp": "a deterministic optimisation policy",
    "stochastic_sp": "a scenario-based optimisation policy",
    "anchored_sp": "an anchored scenario-based policy",
    "adaptive_sp": "an adaptive scenario-based policy",
    "service_target": "a service-target policy",
    "dro": "a distributionally robust policy",
}
CANDIDATE_SHORT = {
    "order_up_to": "Order-up-to policy", "deterministic_sp": "Deterministic optimiser",
    "stochastic_sp": "Scenario optimiser", "anchored_sp": "Anchored scenario optimiser",
    "adaptive_sp": "Adaptive scenario optimiser", "service_target": "Service-target policy", "dro": "Robust optimiser",
}
CURRENT_LABEL = "Your current purchasing policy"

FIELD_LABEL = {
    "stg_fmcg_skus.contribution_margin": "contribution margin per product",
    "stg_fmcg_skus.unit_price": "selling price per product",
    "stg_fmcg_skus.supplier_capacity_per_week": "supplier capacity per product",
    "stg_fmcg_skus.service_class": "service class per product",
    "stg_fmcg_skus.moq_units": "minimum order quantity",
    "stg_fmcg_skus.manufacturer": "manufacturer per product",
    "stg_fmcg_skus.shelf_life_days": "shelf life per product",
    "stg_fmcg_orders.qty_shipped": "quantity shipped on customer orders",
    "stg_fmcg_orders.customer_id": "customer on each order",
    "stg_fmcg_orders.requested_delivery_date": "requested delivery date",
    "stg_fmcg_orders.channel": "sales channel",
    "stg_fmcg_purchase_orders.expected_delivery_date": "expected delivery date on purchase orders",
    "stg_fmcg_purchase_orders.unit_cost": "unit cost on purchase orders",
    "stg_fmcg_receipts.qty_rejected": "rejected quantity on receipts",
    "stg_fmcg_receipts.sku": "product on each receipt line",
    "stg_fmcg_inventory.in_transit": "in-transit quantity in stock counts",
    "stg_fmcg_inventory.location_id": "location in stock counts",
    "stg_fmcg_promotions.sku": "promotion calendar",
    "stg_fmcg_promotions.week_start": "promotion calendar",
    "stg_fmcg_promotions.uplift": "promotion uplift",
    "stg_fmcg_suppliers.route": "shipping route per supplier",
    "stg_fmcg_suppliers.manufacturer": "manufacturer per supplier",
    "stg_fmcg_suppliers.capacity_per_week": "supplier capacity",
    "stg_fmcg_suppliers.lead_time_promised_weeks": "promised lead time per supplier",
    "stg_fmcg_economics.key": "carrying-cost and penalty inputs",
    "stg_fmcg_economics.value": "carrying-cost and penalty inputs",
    "stg_fmcg_economics.provenance": "carrying-cost and penalty inputs",
}


# ── formatting ───────────────────────────────────────────────────────────────
def pct(x: Any, signed: bool = False, nd: int = 1) -> str:
    """A ratio in [−1, 1] shown as a percentage. Never applied to a non-ratio."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NOT_AVAILABLE
    if not math.isfinite(v):
        return NOT_AVAILABLE
    s = f"{v * 100:.{nd}f}%"
    return (f"+{s}" if v > 0 else s) if signed else s


def num(x: Any, nd: int = 0) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NOT_AVAILABLE
    if not math.isfinite(v):
        return NOT_AVAILABLE
    return f"{v:,.{nd}f}"


def weeks(x: Any, nd: int = 1) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return NOT_AVAILABLE
    if not math.isfinite(v):
        return NOT_AVAILABLE
    s = f"{v:.{nd}f}".rstrip("0").rstrip(".")
    return f"{s} week" + ("" if s == "1" else "s")


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _field_label(f: str) -> str:
    return FIELD_LABEL.get(f, f.replace("stg_fmcg_", "").replace("_", " "))


# ── readiness ────────────────────────────────────────────────────────────────
def readiness_section(summary: dict) -> dict:
    r = summary.get("readiness") or {}
    d = summary.get("readiness_detail") or {}
    verdict = str(r.get("verdict") or d.get("verdict") or "")
    weeks_hist = d.get("history_weeks")
    periods = summary.get("history_periods")
    n_weeks = _f(weeks_hist) if weeks_hist is not None else _f(periods)
    products = summary.get("products")
    suppliers = summary.get("suppliers")
    required_missing = list(d.get("required_missing") or r.get("missing") or [])
    preferred_missing = list(d.get("preferred_missing") or [])
    weakened = list(d.get("weakened_conclusions") or [])
    unknown_margin = summary.get("unknown_margin_count")
    if unknown_margin is None:
        unknown_margin = _unknown_margin_from_warnings(summary)
    n_products = _f(products) or 0.0

    if verdict.startswith("NOT_READY") or (verdict == "" and required_missing):
        level, label = "not_ready", "NOT ENOUGH DATA TO ANALYZE"
    elif verdict == "READY":
        level, label = "ready", "GOOD ENOUGH TO ANALYZE"
    elif verdict == "READY_WITH_CAVEATS":
        level, label = "ready_with_limits", "GOOD ENOUGH TO ANALYZE — WITH LIMITATIONS"
    elif verdict:
        level, label = "ready_with_limits", "ANALYZED — WITH LIMITATIONS"
    else:
        level, label = "unknown", "DATA READINESS NOT ASSESSED"

    # Explicit, deterministic confidence rule. Stated in the appendix verbatim.
    margin_share = (float(unknown_margin) / n_products) if (unknown_margin is not None and n_products) else 0.0
    if level == "not_ready" or (n_weeks is not None and n_weeks < 26):
        confidence, rule = "Low", "required data missing or fewer than 26 weeks of history"
    elif level == "ready" and (n_weeks or 0) >= 52 and margin_share == 0.0:
        confidence, rule = "High", "no required or preferred field missing, at least 52 weeks of history, margin known for every product"
    elif (n_weeks or 0) >= 26 and margin_share < 0.5:
        confidence, rule = "Moderate", "at least 26 weeks of history; some preferred fields missing or margin unknown for under half the products"
    else:
        confidence, rule = "Low", "margin unknown for half or more of the products"

    limitations: list[dict] = []
    seen: set = set()
    field_by_effect: dict = {}
    for f in preferred_missing:
        # the readiness module already phrases the consequence; pair it with the field
        field_by_effect.setdefault(_field_label(f), f)
    for w in weakened:
        if w in seen:
            continue
        seen.add(w)
        limitations.append({"effect": _humanise_weakened(w), "internal": w})
    if not limitations:
        # a summary persisted before the readiness detail existed: the run's warnings carry the same facts
        for w in (summary.get("warnings") or []):
            eff = _limitation_from_warning(str(w))
            if eff and eff not in seen:
                seen.add(eff)
                limitations.append({"effect": eff, "internal": str(w)})
    facts = [{"label": "History analysed", "value": f"{int(n_weeks)} weeks" if n_weeks is not None else NOT_AVAILABLE},
             {"label": "Products with order history", "value": num(products) if products is not None else NOT_AVAILABLE},
             {"label": "Suppliers", "value": num(suppliers) if suppliers is not None else NOT_AVAILABLE}]
    hr = summary.get("history_range") or {}
    if hr.get("orders_from"):
        facts.append({"label": "Order history window", "value": f"{hr['orders_from']} to {hr.get('orders_to', '')}"})
    if hr.get("po_lines") is not None:
        facts.append({"label": "Purchase order lines", "value": num(hr["po_lines"])})
    if hr.get("receipt_lines") is not None:
        facts.append({"label": "Receipt lines", "value": num(hr["receipt_lines"])})
    rc = d.get("row_counts") or {}
    loc = "location" if "stg_fmcg_inventory.location_id" not in preferred_missing and rc.get("stg_fmcg_inventory") else None
    if loc is None and rc.get("stg_fmcg_inventory"):
        facts.append({"label": "Locations", "value": "single location assumed (no location field in stock counts)"})
    missing_fields = [{"field": _field_label(f), "internal": f} for f in preferred_missing]
    return {"label": label, "level": level, "confidence": confidence, "confidence_rule": rule,
            "internal_verdict": verdict or None, "facts": facts, "limitations": limitations,
            "missing_fields": missing_fields, "required_missing": required_missing,
            "history_weeks": int(n_weeks) if n_weeks is not None else None,
            "products": products, "suppliers": suppliers, "unknown_margin_count": unknown_margin,
            "statement": _readiness_statement(level, confidence, n_weeks, limitations)}


_MARGIN_RE = re.compile(r"(\d+) SKU\(s\) have no contribution margin or price")


def _unknown_margin_from_warnings(summary: dict) -> int | None:
    for w in (summary.get("warnings") or []):
        m = _MARGIN_RE.search(str(w))
        if m:
            return int(m.group(1))
    return None


def _limitation_from_warning(w: str) -> str | None:
    m = _MARGIN_RE.search(w)
    if m:
        return f"{m.group(1)} product(s) have no price or margin, so their shortage cost is unknown and they stay anchored to your current policy"
    if w.startswith("supplier capacity not supplied"):
        return "Supplier capacity is inferred from historical order peaks, so capacity-bound recommendations are advisory"
    if w.startswith("carrying cost not supplied"):
        return "Carrying cost is a public benchmark (24% per year); the policy ranking is sensitive to it"
    if w.startswith("no inventory snapshot"):
        return "No stock count was supplied, so opening stock is unknown"
    if w.startswith("no PO/receipt history"):
        return "No purchase-order and receipt history, so supplier fill and lead time are assumed"
    return None


def _humanise_weakened(w: str) -> str:
    t = w
    t = t.replace("incumbent", "your current policy")
    t = t.replace("UNKNOWN", "unknown").replace("INFERRED", "inferred").replace("ASSUMED", "assumed")
    t = t.replace("the safe selector needs", "the policy comparison needs").replace("run multiple folds", "test several historical periods")
    t = t.replace("will defer to your current policy", "keeps your current policy")
    return t[0].upper() + t[1:] if t else t


def _readiness_statement(level: str, confidence: str, n_weeks: float | None, limitations: list) -> str:
    if level == "not_ready":
        return "The uploaded history is missing required fields, so the purchasing diagnostic could not run in full."
    base = "Your historical data is sufficient for a meaningful purchasing diagnostic"
    if limitations:
        first = limitations[0]["effect"].rstrip(".")
        first = first[0].lower() + first[1:]
        return f"{base}, although {first}. Overall confidence: {confidence.lower()}."
    return f"{base}. Overall confidence: {confidence.lower()}."


# ── how you order today ──────────────────────────────────────────────────────
def ordering_section(summary: dict) -> dict:
    inc = summary.get("incumbent_detail") or {}
    label = str(summary.get("incumbent") or "")
    notes = list(summary.get("incumbent_notes") or inc.get("notes") or [])
    sku_prof = summary.get("sku_profile") or {}
    sup_prof = summary.get("supplier_profile") or {}
    items: list[dict] = []
    if inc.get("source") == "inferred" or "INFERRED" in label:
        n_used = inc.get("n_pos_used") or {}
        items.append({"label": "Policy read from your history", "tag": "OBSERVED",
                      "value": f"ZAAD reconstructed your ordering from {num(sum(n_used.values()))} purchase orders across {num(len(n_used))} products"
                      if n_used else "ZAAD reconstructed your ordering from your purchase-order history",
                      "note": "The reconstruction is a cover-level rule: at each review you order up to a target number of weeks of demand."})
    elif inc.get("source") == "configured" or "configured" in label:
        items.append({"label": "Policy", "tag": "OBSERVED", "value": "Your configured purchasing rule was used as the baseline", "note": None})
    elif inc.get("source") == "schedule":
        items.append({"label": "Policy", "tag": "OBSERVED", "value": "Your supplied order schedule was used as the baseline", "note": None})
    covers = [v for v in (inc.get("cover_weeks") or {}).values() if _f(v) is not None]
    if covers:
        q = sorted(covers)
        med = st.median(q)
        p25, p75 = q[max(0, int(len(q) * 0.25) - 1)] if len(q) > 3 else q[0], q[min(len(q) - 1, int(len(q) * 0.75))]
        items.append({"label": "Typical cover ordered", "tag": "OBSERVED",
                      "value": f"about {weeks(med)} of demand at each review (middle half of products: {weeks(p25)} to {weeks(p75)})",
                      "note": "Cover inferred from order quantities alone for products without stock-on-hand at order date; treat as approximate."
                      if any("inventory position at PO date unknown" in n for n in notes) else None})
    reviews = [v for v in (inc.get("review_periods") or {}).values() if _f(v) is not None]
    if reviews:
        med_r = st.median(reviews)
        items.append({"label": "Order frequency", "tag": "OBSERVED",
                      "value": f"orders placed about every {weeks(med_r, 0)} for a typical product", "note": None})
    too_few = [n for n in notes if "too few to infer" in n]
    if too_few or any("too few" in n for n in (inc.get("notes") or [])):
        n_tf = sum(1 for n in (inc.get("notes") or notes) if "too few to infer" in n)
        if n_tf:
            items.append({"label": "Products with too few orders to read a rule", "tag": "OBSERVED",
                          "value": f"{num(n_tf)} product(s) had fewer than 4 purchase orders; a default cover level stood in", "note": None})
    if sup_prof:
        shares = sorted(((v.get("value_share") or 0.0), k) for k, v in sup_prof.items())
        top_share, top = shares[-1]
        items.append({"label": "Supplier concentration", "tag": "OBSERVED",
                      "value": f"your largest supplier ({top}) carries {pct(top_share)} of demand value; {num(len(sup_prof))} suppliers in total",
                      "note": "Concentration is measured on demand value (mean weekly demand × unit cost), not on spend."})
    if sku_prof:
        vals = sorted(((v.get("value_share") or 0.0) for v in sku_prof.values()), reverse=True)
        n = len(vals)
        top20 = sum(vals[:max(1, int(math.ceil(n * 0.2)))])
        items.append({"label": "Product concentration", "tag": "OBSERVED",
                      "value": f"the top 20% of products carry {pct(top20)} of demand value ({num(n)} products)", "note": None})
        thin = [(k, v) for k, v in sku_prof.items() if _f(v.get("cover_periods")) is not None and float(v["cover_periods"]) < 1.0
                and (v.get("mean_weekly_demand") or 0) > 0]
        if thin:
            items.append({"label": "Products under one week of cover at the plan date", "tag": "OBSERVED",
                          "value": f"{num(len(thin))} product(s)", "note": "Cover = stock on hand plus in transit, divided by recent weekly demand."})
        lead_thin = []
        for k, v in sku_prof.items():
            sp = sup_prof.get(str(v.get("supplier")), {})
            lead = _f(sp.get("lead_mean_weeks")) or _f(sp.get("lead_weeks_assumed"))
            cov = _f((inc.get("cover_weeks") or {}).get(k))
            if lead is not None and cov is not None and cov < lead:
                lead_thin.append(k)
        if lead_thin:
            items.append({"label": "Products ordered to less cover than their supplier's lead time", "tag": "LIKELY DRIVER",
                          "value": f"{num(len(lead_thin))} product(s)",
                          "note": "When the cover ordered is shorter than the lead time, stock runs out before the next receipt unless demand falls. This is a likely driver of shortages, not a measured one: shipped quantities on customer orders would confirm it."})
    summary_text = ("ZAAD read your purchasing behaviour from your own purchase orders and receipts; the items below are "
                    "observations, not judgements. Where a cause is suggested it is labelled as a likely driver.")
    return {"summary": summary_text, "items": items, "internal_label": label or None}


# ── policy comparison ────────────────────────────────────────────────────────
_HOLDOUT_RE = re.compile(r"(?P<name>\w+) won the selection folds but did not beat the incumbent on (?P<n>\d+) held-out fold\(s\) \(mean (?P<mean>[-+\d.eE]+|None)\)")


def _leading_candidate(summary: dict) -> tuple[str | None, dict]:
    ce = summary.get("candidate_evidence") or {}
    cands = summary.get("candidates") or {}
    decision = str(summary.get("decision") or "")
    if decision and decision != "incumbent" and (decision in ce or decision in cands):
        return decision, (ce.get(decision) or cands.get(decision) or {})
    pool = ce or cands
    if not pool:
        return None, {}
    best = max(pool.items(), key=lambda kv: (bool(kv[1].get("passed")), _f(kv[1].get("lower_bound")) or -9.0))
    return best[0], best[1]


def policy_section(summary: dict) -> dict:
    decision = str(summary.get("decision") or "")
    reason = str(summary.get("reason") or "")
    gates = summary.get("gate_config") or {}
    threshold = _f(gates.get("min_rel_improvement"))
    conf = _f(gates.get("confidence"))
    name, ev = _leading_candidate(summary)
    out: dict = {"available": bool(name), "current_label": CURRENT_LABEL, "candidate": name,
                 "candidate_label": CANDIDATE_SHORT.get(name or "", name or ""), "rows": [], "explanation": [],
                 "outcome": None, "fold_chart": None, "internal": {"decision": decision or None, "reason": reason or None,
                                                                   "gates": gates}}
    if not name:
        if "insufficient history" in reason:
            out["outcome"] = "not_run"
            out["explanation"] = [f"The comparison did not run: {reason.split(';')[0].strip()}. ZAAD keeps your current policy until at least 26 weeks of history are available."]
        elif "admits no candidate" in reason or "no candidate" in reason.lower():
            out["outcome"] = "not_run"
            out["explanation"] = ["No alternative policy was tested against your history in this run, so your current policy stands."]
        else:
            out["outcome"] = "not_run"
            out["explanation"] = ["No alternative policy was evidenced against your current policy; keeping it is a valid result."]
        return out

    mean, lb, worst, wr, nf = _f(ev.get("mean")), _f(ev.get("lower_bound")), _f(ev.get("worst")), _f(ev.get("win_rate")), ev.get("n_folds")
    svc_min, svc_mean = _f(ev.get("service_diff_min")), _f(ev.get("service_diff_mean"))
    hold_mean, hold_lb, hold_gates = _f(ev.get("holdout_mean")), _f(ev.get("holdout_lower_bound")), ev.get("holdout_gates") or {}
    held_n = None
    if hold_mean is None and reason:
        m = _HOLDOUT_RE.search(reason)
        if m and m.group("name") == name:
            held_n = int(m.group("n"))
            hold_mean = _f(m.group("mean"))
            hold_gates = hold_gates or {"lower_bound_exceeds_threshold": False}
    if held_n is None:
        held_n = gates.get("n_holdout_folds")

    rows = [
        {"metric": "Operating cost on the same history", "current": "baseline",
         "candidate": _rel_cost(mean),
         "difference": f"{pct(mean, signed=True)} on average across {num(nf)} historical periods" if nf else pct(mean, signed=True),
         "note": "Positive means the candidate would have cost less than your policy on the same history. Cost = holding + shortage + purchase, as the backtest prices them."},
        {"metric": "Conservative estimate of that cost change", "current": "—", "candidate": pct(lb, signed=True),
         "difference": f"at least {pct(lb, signed=True)} with {pct(conf, nd=0)} confidence" if conf else pct(lb, signed=True),
         "note": "A statistical lower bound: the improvement ZAAD is confident the history supports, not the average."},
        *([{"metric": "Worst historical period", "current": "—", "candidate": pct(worst, signed=True),
            "difference": "the least favourable period for the candidate", "note": None}] if worst is not None else []),
        *([{"metric": "Periods where the candidate cost less", "current": "—",
            "candidate": f"{pct(wr, nd=0)} of periods", "difference": "", "note": None}] if wr is not None else []),
        {"metric": "Service (fill rate) difference", "current": "baseline",
         "candidate": (f"{svc_min * 100:+.1f} pts in the worst period" if svc_min is not None else NOT_AVAILABLE),
         "difference": (f"{svc_mean * 100:+.1f} pts on average" if svc_mean is not None else "shipped quantities on customer orders would allow this to be measured"),
         "note": "Fill rate is the share of demand served from stock in the backtest."},
        {"metric": "Inventory held", "current": "—", "candidate": NOT_AVAILABLE,
         "difference": "the backtest retains only the cost and service outcome per period; inventory-at-order-date history would allow a like-for-like inventory comparison", "note": None},
        {"metric": "Working capital, holding cost, waste", "current": "—", "candidate": NOT_AVAILABLE,
         "difference": "not reported separately: the cost line above already prices holding and shortage; no currency value is shown because none is declared", "note": None},
    ]
    out["rows"] = rows

    thr_txt = pct(threshold) if threshold is not None else "the configured threshold"
    passed_inner = bool(ev.get("passed"))
    cand_txt = CANDIDATE_LABEL.get(name, name)
    para: list[str] = []
    periods_txt = f"{num(nf)} historical periods" if nf else "rolling historical periods"
    para.append(f"ZAAD replayed {cand_txt} through {periods_txt} that it had not seen when choosing its orders, and compared its cost with what your own policy did on the same periods. "
                f"On average it cost {pct(abs(mean) if mean is not None else None)} {'less' if (mean or 0) > 0 else 'more'} than your policy; the conservative estimate (lower bound) was {pct(lb, signed=True)}.")
    if passed_inner:
        para.append(f"That cleared ZAAD's selection rule: the lower bound had to exceed {thr_txt}, service could not fall by more than "
                    f"{pct(_f(gates.get('service_tolerance')), nd=0) if gates.get('service_tolerance') is not None else 'the tolerance'}, and no single period could lose more than "
                    f"{pct(_f(gates.get('max_regret_share')), nd=0) if gates.get('max_regret_share') is not None else 'the budget'} against your policy. \"Cleared the gate\" means exactly this and nothing more.")
    else:
        failed = [k for k, v in (ev.get("gates") or {}).items() if not v]
        para.append("It did not clear ZAAD's selection rule" + (f" ({', '.join(_gate_label(k) for k in failed)})" if failed else "") + ", so your current policy stands.")
    if decision == "incumbent" and passed_inner:
        out["outcome"] = "keep_current_after_holdout"
        hold_txt = f"there it averaged {pct(hold_mean, signed=True)}" if hold_mean is not None else "there its advantage did not hold"
        if hold_lb is not None:
            hold_txt += f" with a lower bound of {pct(hold_lb, signed=True)}"
        para.append(f"ZAAD then re-tested the candidate on {num(held_n) if held_n else 'additional'} unseen historical validation periods that played no part in choosing it; {hold_txt}. "
                    f"Because the advantage was not consistent across those unseen periods, ZAAD did not recommend replacing your policy on an unstable result. "
                    f"Your current purchasing policy was retained. This is the reason a candidate can clear the selection threshold and still not be selected.")
        para.append("What would change this: more history (each additional quarter adds validation periods), and stock-on-hand at order date, which sharpens the reconstruction of your own policy that the candidate is measured against.")
    elif decision == name:
        out["outcome"] = "adopt_candidate"
        para.append(f"The candidate was then re-tested on unseen historical validation periods and held its advantage there as well. ZAAD therefore recommends {cand_txt} for the next order cycle, with your current policy kept as the fallback.")
    elif decision == "incumbent":
        out["outcome"] = "keep_current"
        para.append("Your current purchasing policy was retained.")
    else:
        out["outcome"] = "other"
        para.append(reason)
    out["explanation"] = para
    fd = [x for x in (ev.get("fold_deltas") or []) if _f(x) is not None]
    if fd:
        out["fold_chart"] = {"selection": [float(x) for x in fd], "holdout_mean": hold_mean, "threshold": threshold,
                             "title": f"Cost change vs your policy per historical period ({CANDIDATE_SHORT.get(name, name)})"}
    out["internal"].update({"candidate_evidence": {**ev, "holdout_mean": hold_mean if hold_mean is not None else ev.get("holdout_mean")},
                            "inner_passed": passed_inner, "holdout_gates": hold_gates})
    return out


def _rel_cost(mean: float | None) -> str:
    if mean is None:
        return NOT_AVAILABLE
    if abs(mean) < 0.0005:
        return "no measurable change"
    return f"{pct(abs(mean))} {'lower' if mean > 0 else 'higher'}"


def _gate_label(k: str) -> str:
    return {"enough_folds": "not enough usable historical periods", "lower_bound_exceeds_threshold": "the conservative estimate did not exceed the threshold",
            "service_non_inferior": "service fell by more than the tolerance", "downside_within_budget": "one period lost more than the risk budget",
            "no_fallbacks": "some solves needed a fallback", "complete": "incomplete on the validation periods"}.get(k, k.replace("_", " "))


# ── findings ─────────────────────────────────────────────────────────────────
def _finding(id_: str, category: str, headline: str, severity: str, observation: str, implication: str,
             recommendation: str, confidence: str, confidence_basis: str, *, materiality: float | None = None,
             driver: str | None = None, driver_tag: str = "UNKNOWN", evidence: list | None = None,
             related: list | None = None, summary_line: str | None = None) -> dict:
    return {"id": id_, "category": category, "headline": headline, "severity": severity, "materiality": materiality,
            "observation": observation, "business_implication": implication, "possible_driver": driver,
            "driver_tag": driver_tag, "recommendation": recommendation, "confidence": confidence,
            "confidence_basis": confidence_basis, "evidence": evidence or [], "related": related or [],
            "summary_line": summary_line}


_STATE_DEMAND_RE = re.compile(r"^(?P<id>[\w.\-/]+): demand CV (?P<cv>[\d.]+), zero-share (?P<z>\d+)%")
_STATE_LEAD_RE = re.compile(r"^(?P<id>[\w.\-/]+): lead time (?P<r>[\d.]+)x its long-run mean")


def _profiles_from_state_reasons(summary: dict) -> dict:
    """Old summaries carry the estimator's top reasons only; read the SKU
    demand facts out of them so the finding still appears (value share
    unknown, confidence moderate, period count unknown)."""
    out: dict = {}
    for r in ((summary.get("state") or {}).get("reasons") or []):
        m = _STATE_DEMAND_RE.match(str(r))
        if m:
            out[m.group("id")] = {"zero_share": int(m.group("z")) / 100.0, "demand_cv": float(m.group("cv")),
                                  "periods": int(summary.get("history_periods") or 0) or 12, "value_share": None, "supplier": None}
    return out


def _lead_drift_from_state_reasons(summary: dict) -> list:
    out = []
    for r in ((summary.get("state") or {}).get("reasons") or []):
        m = _STATE_LEAD_RE.match(str(r))
        if m:
            out.append((m.group("id"), float(m.group("r"))))
    return out


def _sev_rank(s: str) -> int:
    return {"high": 3, "medium": 2, "low": 1, "info": 0}.get(s, 0)


def findings_section(summary: dict, policy: dict, readiness: dict) -> list[dict]:
    out: list[dict] = []
    sku_prof = summary.get("sku_profile") or {}
    sup_prof = summary.get("supplier_profile") or {}
    prov = summary.get("provenance") or {}

    # policy
    name = str(policy.get("candidate") or "")
    if policy.get("outcome") == "keep_current_after_holdout":
        ev = (policy.get("internal") or {}).get("candidate_evidence") or {}
        out.append(_finding("policy-holdout", "policy", "An alternative policy looked better on average but was not consistent",
                            "medium", policy["explanation"][0] if policy.get("explanation") else "",
                            "Changing a purchasing policy on an unstable result risks paying for a change that does not hold. ZAAD kept your current policy.",
                            "Keep your current policy for now; re-run the diagnostic when another quarter of history is available, and supply stock-on-hand at order date.",
                            "High", "measured on your own history with held-out validation periods",
                            materiality=1.0, driver="Advantage on the selection periods that did not repeat on unseen validation periods", driver_tag="OBSERVED",
                            evidence=[{"label": "Average cost change (selection periods)", "value": pct(_f(ev.get("mean")), signed=True)},
                                      {"label": "Conservative estimate", "value": pct(_f(ev.get("lower_bound")), signed=True)},
                                      {"label": "Unseen validation periods", "value": pct(_f(ev.get("holdout_mean")), signed=True) if ev.get("holdout_mean") is not None else "did not hold"}],
                            related=[{"kind": "decision", "id": "decisions", "label": "Decisions"}],
                            summary_line=f"{CANDIDATE_SHORT.get(name, name)} cost {pct(abs(_f(ev.get('mean')) or 0))} less on average on the selection periods (conservative estimate {pct(_f(ev.get('lower_bound')), signed=True)}) but "
                                         + (f"only {pct(_f(ev.get('holdout_mean')), signed=True)}" if ev.get("holdout_mean") is not None else "did not hold") + " on the unseen validation periods, so your policy was kept."))
    elif policy.get("outcome") == "adopt_candidate":
        ev = (policy.get("internal") or {}).get("candidate_evidence") or {}
        out.append(_finding("policy-adopt", "policy", f"{CANDIDATE_SHORT.get(name, name)} outperformed your policy consistently on your history", "high",
                            policy["explanation"][0] if policy.get("explanation") else "",
                            "The advantage held on unseen validation periods, which is the standard ZAAD requires before recommending a change.",
                            "Adopt it for the next order cycle with your current policy as fallback; review the first cycle's orders line by line in ZAAD before release.",
                            "High", "measured on your own history with held-out validation periods", materiality=1.0,
                            driver_tag="OBSERVED", evidence=[{"label": "Average cost change", "value": pct(_f(ev.get("mean")), signed=True)},
                                                             {"label": "Conservative estimate", "value": pct(_f(ev.get("lower_bound")), signed=True)}],
                            related=[{"kind": "decision", "id": "decisions", "label": "Run a decision"}]))
    elif policy.get("outcome") == "keep_current" and name:
        out.append(_finding("policy-keep", "policy", "No tested alternative beat your current policy with enough margin", "info",
                            policy["explanation"][0] if policy.get("explanation") else "",
                            "Your current policy is the defensible choice on the evidence available; this is a valid outcome, not a failure.",
                            "Keep your current policy; the data actions below raise the chance a future comparison is decisive either way.",
                            "High", "measured on your own history", materiality=0.9, driver_tag="OBSERVED"))

    # data findings
    inc_detail_notes = (summary.get("incumbent_detail") or {}).get("notes")
    inc_notes = list(summary.get("incumbent_notes") or [])
    exact = inc_detail_notes is not None
    note_pool: list = list(inc_detail_notes or []) if exact else inc_notes
    n_nopos = sum(1 for n in note_pool if "inventory position at PO date unknown" in str(n))
    if n_nopos:
        count_txt = f"For {num(n_nopos)} product(s)" if exact else f"For at least {num(n_nopos)} product(s) (this run kept only its first notes)"
        out.append(_finding("data-inventory-at-po", "data", "Your ordering rule was reconstructed without stock on hand at order date", "medium",
                            f"{count_txt} the stock position at the moment each purchase order was placed is not in the data, so the cover level you order to was inferred from order quantities alone.",
                            "The baseline ZAAD compares every alternative against is less precise, which lowers confidence in the policy comparison for those products.",
                            "Supply inventory snapshots at (or just before) each purchase-order date, or weekly stock counts covering the history.",
                            "High", "a property of the uploaded data", materiality=0.8, driver_tag="OBSERVED",
                            evidence=[{"label": "Products affected", "value": num(n_nopos)}], related=[{"kind": "screen", "id": "upload", "label": "Upload"}]))
    um = summary.get("unknown_margin_count")
    if um is None:
        um = _unknown_margin_from_warnings(summary)
    if um:
        out.append(_finding("data-margin", "data", f"{num(um)} product(s) have no price or margin, so their shortage cost is unknown", "medium",
                            "Without a margin ZAAD cannot price a lost sale for these products.", "They are anchored to your current policy and excluded from any recommendation to change.",
                            "Add unit price or contribution margin to the product list.", "High", "a property of the uploaded data", materiality=0.6, driver_tag="OBSERVED",
                            evidence=[{"label": "Products", "value": ", ".join((summary.get("unknown_margin_skus") or [])[:6]) + (" …" if um > 6 else "")}],
                            related=[{"kind": "sku", "id": s, "label": s} for s in (summary.get("unknown_margin_skus") or [])[:5]]))
    if str(prov.get("holding_rate_per_period", "")).upper().startswith("PUBLIC"):
        out.append(_finding("data-carrying", "data", "Carrying cost is a public benchmark, not your figure", "low",
                            "No carrying-cost inputs were supplied, so ZAAD used a public benchmark of 24% of inventory value per year (cost of capital 10%, storage and handling 8%, insurance 1%, shrink and obsolescence 5%).",
                            "The ranking of policies is sensitive to this figure; a lower true carrying cost favours holding more stock.",
                            "Provide your cost of capital, storage and handling, insurance and shrink rates (economics inputs).", "High", "a stated assumption",
                            materiality=0.5, driver_tag="OBSERVED", related=[{"kind": "screen", "id": "upload", "label": "Upload"}]))
    if str(prov.get("supplier_capacity", "")).upper() in ("MEASURED", "ASSUMED"):
        out.append(_finding("data-capacity", "data", "Supplier capacity was inferred from your past order peaks", "low",
                            "No supplier capacity was supplied, so ZAAD took 1.25 × the largest weekly quantity you ever ordered as each product's capacity (2 × mean demand where no orders exist).",
                            "Recommendations that rest on capacity limits are advisory until capacity is confirmed.",
                            "Confirm weekly capacity with your main suppliers and record it in the supplier list.", "High", "a stated assumption",
                            materiality=0.4, driver_tag="OBSERVED"))
    if (readiness.get("history_weeks") or 0) < 52 and readiness.get("history_weeks") is not None:
        out.append(_finding("data-history", "data", f"{readiness['history_weeks']} weeks of history: fewer validation periods than ideal", "low",
                            "The comparison used the available history; a full year adds seasonal periods and more unseen validation periods.",
                            "Conclusions about seasonal products are weaker.", "Upload the remaining history when available.", "High", "a property of the uploaded data",
                            materiality=0.3, driver_tag="OBSERVED"))

    # demand findings per SKU, ranked by value share
    inter = []
    shifted = []
    if not sku_prof:
        sku_prof = _profiles_from_state_reasons(summary)
    for k, v in sku_prof.items():
        z, cv = _f(v.get("zero_share")), _f(v.get("demand_cv"))
        n = int(v.get("periods") or 0)
        if n < 12:
            continue
        if (z is not None and z >= 0.35) or (cv is not None and cv > 0.45 and z is not None and z >= 0.2):
            inter.append((_f(v.get("value_share")) or 0.0, k, v))
        sd, age = _f(v.get("demand_shift_sd")), v.get("demand_shift_age")
        if sd is not None and abs(sd) > 2.0 and age is not None and age <= 12:
            shifted.append((_f(v.get("value_share")) or 0.0, k, v))
    inter.sort(reverse=True)
    for share, k, v in inter[:5]:
        z, cv, n = _f(v.get("zero_share")), _f(v.get("demand_cv")), int(v.get("periods") or 0)
        conf = "High" if n >= 26 else "Moderate"
        share_known = v.get("value_share") is not None
        out.append(_finding(f"demand-intermittent-{k}", "demand", f"{k} — highly intermittent demand", "medium" if (share >= 0.01 or not share_known) else "low",
                            f"Demand was zero in {pct(z, nd=0)} of the {n} observed weeks" + (" and varied materially when it did occur." if (cv or 0) > 1.0 else "."),
                            "A product like this should not automatically be managed with the same replenishment logic as stable, high-frequency items: a cover rule tuned to average demand either holds stock through long quiet spells or misses the occasional large order.",
                            "Review this product individually: decide whether it is make-to-order, held for a specific customer, or stocked at a deliberate minimum.",
                            conf, f"{n} weeks of demand observed", materiality=share if share_known else None, driver="Demand arrives in occasional lumps rather than a steady flow", driver_tag="OBSERVED",
                            evidence=[{"label": "Weeks with zero demand", "value": pct(z, nd=0)}, {"label": "Demand variability (coefficient of variation)", "value": f"{cv:.2f}" if cv is not None else NOT_AVAILABLE},
                                      {"label": "Share of demand value", "value": pct(share) if share_known else NOT_AVAILABLE}, {"label": "Supplier", "value": str(v.get("supplier") or NOT_AVAILABLE)}],
                            related=[{"kind": "sku", "id": k, "label": k}]))
    if len(inter) > 5:
        rest = inter[5:]
        out.append(_finding("demand-intermittent-rest", "demand", f"{num(len(rest))} further product(s) show intermittent demand", "low",
                            f"Together they carry {pct(sum(s for s, _, _ in rest))} of demand value.", "Individually small; as a group they decide how much slow stock you hold.",
                            "Set a deliberate stocking rule for slow products (minimum, make-to-order, or none).", "Moderate", "per-product demand history",
                            materiality=sum(s for s, _, _ in rest), driver_tag="OBSERVED", related=[{"kind": "sku", "id": k, "label": k} for _, k, _ in rest[:8]]))
    shifted.sort(reverse=True)
    for share, k, v in shifted[:3]:
        sd = _f(v.get("demand_shift_sd")) or 0.0
        out.append(_finding(f"demand-shift-{k}", "demand", f"{k} — demand level changed recently", "medium" if share >= 0.01 else "low",
                            f"Recent weekly demand sits {abs(sd):.1f} standard deviations {'above' if sd > 0 else 'below'} its longer-run level, with the change about {v.get('demand_shift_age')} week(s) old.",
                            "A cover rule based on the older level " + ("under-orders" if sd > 0 else "over-orders") + " until it catches up; the backtest periods largely predate the change.",
                            "Check whether the change is a known cause (a new customer, a lost listing, a promotion) and adjust the cover for this product deliberately.",
                            "Moderate", "change-point detection on weekly demand", materiality=share, driver="Cause not in the data", driver_tag="UNKNOWN",
                            evidence=[{"label": "Shift", "value": f"{sd:+.1f} sd"}, {"label": "Age", "value": f"{v.get('demand_shift_age')} weeks"}, {"label": "Share of demand value", "value": pct(share)}],
                            related=[{"kind": "sku", "id": k, "label": k}]))

    # inventory: thin cover on material products
    thin = [((_f(v.get("value_share")) or 0.0), k, v) for k, v in sku_prof.items()
            if _f(v.get("cover_periods")) is not None and float(v["cover_periods"]) < 1.0 and (v.get("mean_weekly_demand") or 0) > 0]
    thin.sort(reverse=True)
    if thin:
        top = thin[:5]
        out.append(_finding("inventory-thin-cover", "inventory", f"{num(len(thin))} product(s) had under one week of cover at the plan date", "medium" if sum(s for s, _, _ in thin) >= 0.05 else "low",
                            "Stock on hand plus in transit divided by recent weekly demand was below 1.0 for these products at the last stock count.",
                            "Any supplier slip on these products becomes a shortage within the week.",
                            "Check open orders for these products and whether the next receipt lands before stock runs out.",
                            "Moderate", "latest stock count and recent demand; in-transit quantities are " + ("included" if "stg_fmcg_inventory.in_transit" not in [m.get("internal") for m in readiness.get("missing_fields", [])] else "estimated from open orders"),
                            materiality=sum(s for s, _, _ in thin), driver_tag="OBSERVED",
                            evidence=[{"label": k, "value": f"{float(v['cover_periods']):.1f} weeks of cover"} for _, k, v in top],
                            related=[{"kind": "sku", "id": k, "label": k} for _, k, _ in top] + [{"kind": "po", "id": "open", "label": "Purchase orders"}]))

    # supplier findings
    if not sup_prof:
        for sid, ratio in _lead_drift_from_state_reasons(summary):
            out.append(_finding(f"supplier-lead-drift-{sid}", "supplier", f"{sid} — lead times are lengthening", "medium",
                                f"Recent receipts from this supplier arrived {ratio:.1f}× later than its longer-run average lead time.",
                                "Orders placed to the old lead time arrive late; cover set for the old lead time runs out first on this supplier's products.",
                                "Plan the next orders on this supplier to the recent lead time, not the historical one.",
                                "Moderate", "state estimate from receipts; receipt counts not retained in this run", driver="Cause not in the data", driver_tag="UNKNOWN",
                                evidence=[{"label": "Recent vs long-run lead time", "value": f"{ratio:.1f}×"}], related=[{"kind": "supplier", "id": sid, "label": sid}]))
    for sid, sp in sorted(sup_prof.items(), key=lambda kv: -(_f(kv[1].get("value_share")) or 0.0)):
        n = int(sp.get("n_receipts") or 0)
        share = _f(sp.get("value_share")) or 0.0
        if n < 4:
            continue
        conf = "High" if n >= 8 else "Moderate"
        basis = f"{n} receipts observed"
        fill_shift, fill_mean, fill_recent = _f(sp.get("fill_shift")), _f(sp.get("fill_mean")), _f(sp.get("fill_recent"))
        lead_ratio, lead_sd, lead_mean = _f(sp.get("lead_ratio")), _f(sp.get("lead_sd_weeks")), _f(sp.get("lead_mean_weeks"))
        rel = [{"kind": "supplier", "id": sid, "label": sid}]
        if fill_shift is not None and fill_shift < -0.06:
            out.append(_finding(f"supplier-fill-decline-{sid}", "supplier", f"{sid} — fill rate has fallen recently", "high" if share >= 0.2 else "medium",
                                f"The last four receipts filled {pct(fill_recent, nd=0)} of the ordered quantity against a longer-run {pct(fill_mean, nd=0)} ({fill_shift * 100:+.0f} points).",
                                f"This supplier carries {pct(share)} of your demand value; short receipts turn directly into thinner cover on those products.",
                                "Raise it with the supplier and, until it recovers, review the protection (safety cover) on the products most dependent on it.",
                                conf, basis, materiality=share, driver="Cause not in the data (supplier capacity, allocation, or transport)", driver_tag="UNKNOWN",
                                evidence=[{"label": "Recent fill", "value": pct(fill_recent, nd=0)}, {"label": "Long-run fill", "value": pct(fill_mean, nd=0)}, {"label": "Products supplied", "value": num(sp.get("n_skus"))}], related=rel))
        elif fill_mean is not None and fill_mean < 0.90:
            out.append(_finding(f"supplier-fill-low-{sid}", "supplier", f"{sid} — consistently short receipts", "medium" if share >= 0.1 else "low",
                                f"Across {n} receipts this supplier delivered {pct(fill_mean, nd=0)} of the ordered quantity on average; {num(sp.get('short_receipts'))} receipt(s) were below 95%.",
                                "Your current ordering already absorbs this (it orders more than it expects to receive), but every product on this supplier carries the cost of that over-ordering.",
                                "Agree confirmed quantities before shipment, or split the most exposed products across a second source where one exists.",
                                conf, basis, materiality=share, driver_tag="OBSERVED",
                                evidence=[{"label": "Average fill", "value": pct(fill_mean, nd=0)}, {"label": "Lowest fill", "value": pct(_f(sp.get("fill_min")), nd=0)}], related=rel))
        if lead_ratio is not None and lead_ratio > 1.3:
            out.append(_finding(f"supplier-lead-drift-{sid}", "supplier", f"{sid} — lead times are lengthening", "high" if share >= 0.2 else "medium",
                                f"Recent receipts arrived after {weeks(_f(sp.get('lead_recent_weeks')))} on average, {lead_ratio:.1f}× the longer-run {weeks(lead_mean)}.",
                                "Orders placed to the old lead time arrive late; cover set for the old lead time runs out first on this supplier's products.",
                                "Plan the next orders on this supplier to the recent lead time, not the historical one, and check the lane's conditions below.",
                                conf, basis, materiality=share, driver="Cause not in the data; the lane signals may explain part of it", driver_tag="UNKNOWN",
                                evidence=[{"label": "Recent lead time", "value": weeks(_f(sp.get("lead_recent_weeks")))}, {"label": "Long-run lead time", "value": weeks(lead_mean)}, {"label": "Longest observed", "value": weeks(_f(sp.get("lead_max_weeks")))}], related=rel))
        elif lead_sd is not None and lead_mean and lead_sd / lead_mean > 0.5 and n >= 6:
            out.append(_finding(f"supplier-lead-variable-{sid}", "supplier", f"{sid} — lead times vary widely", "medium" if share >= 0.1 else "low",
                                f"Lead times averaged {weeks(lead_mean)} but spread by ±{weeks(lead_sd)} (longest {weeks(_f(sp.get('lead_max_weeks')))}).",
                                "Variability, more than the average, is what safety cover has to absorb on this supplier's products.",
                                "Review the safety protection on the products most dependent on this supplier rather than raising cover across the board.",
                                conf, basis, materiality=share, driver_tag="OBSERVED",
                                evidence=[{"label": "Average lead time", "value": weeks(lead_mean)}, {"label": "Spread (sd)", "value": weeks(lead_sd)}, {"label": "Products supplied", "value": num(sp.get("n_skus"))}], related=rel))
        if share >= 0.5:
            out.append(_finding(f"supplier-concentration-{sid}", "supplier", f"{sid} carries {pct(share, nd=0)} of your demand value", "medium",
                                f"{num(sp.get('n_skus'))} of your products are sourced from this single supplier.",
                                "A disruption at this supplier or on its lane reaches most of your business at once.",
                                "Know which of its products have a second source, and which do not.", "High", "product master", materiality=share, driver_tag="OBSERVED", related=rel))
    few = [sid for sid, sp in sup_prof.items() if int(sp.get("n_receipts") or 0) < 4]
    if few and sup_prof:
        out.append(_finding("supplier-few-receipts", "supplier", f"{num(len(few))} supplier(s) have too few receipts to judge", "info",
                            "Fewer than four receipts were recorded for " + ", ".join(few[:6]) + (" …" if len(few) > 6 else "") + ".",
                            "ZAAD used assumed fill and lead-time behaviour for them (labelled in the appendix).",
                            "Nothing to do unless these suppliers matter more than the receipt count suggests; then upload their receipt history.",
                            "High", "receipt count", materiality=0.0, driver_tag="OBSERVED", related=[{"kind": "supplier", "id": s, "label": s} for s in few[:5]]))

    out.sort(key=lambda f: (0 if f["category"] == "policy" else 1, -_sev_rank(f["severity"]), -(f.get("materiality") or 0.0), f["id"]))
    return out


# ── suppliers table ──────────────────────────────────────────────────────────
def supplier_section(summary: dict) -> dict:
    sup_prof = summary.get("supplier_profile") or {}
    if not sup_prof:
        return {"available": False, "rows": [], "note": "Supplier-level behaviour needs purchase orders and receipts with a supplier on each line."}
    rows = []
    for sid, sp in sorted(sup_prof.items(), key=lambda kv: -(_f(kv[1].get("value_share")) or 0.0)):
        n = int(sp.get("n_receipts") or 0)
        rows.append({"supplier": sid, "share_of_value": pct(_f(sp.get("value_share"))), "products": num(sp.get("n_skus")),
                     "receipts": num(n),
                     "fill": pct(_f(sp.get("fill_mean")), nd=0) if sp.get("fill_mean") is not None else ("assumed " + pct(_f(sp.get("fill_assumed")), nd=0) if sp.get("fill_assumed") is not None else NOT_AVAILABLE),
                     "lead_time": weeks(_f(sp.get("lead_mean_weeks"))) if sp.get("lead_mean_weeks") is not None else (f"assumed {weeks(_f(sp.get('lead_weeks_assumed')))}" if sp.get("lead_weeks_assumed") is not None else NOT_AVAILABLE),
                     "lead_spread": ("±" + weeks(_f(sp.get("lead_sd_weeks")))) if n > 1 and sp.get("lead_sd_weeks") is not None else NOT_AVAILABLE,
                     "lane": sp.get("lane") or "not declared",
                     "reading": _supplier_reading(sp, n), "evidence": "strong" if n >= 8 else "moderate" if n >= 4 else "weak"})
    return {"available": True, "rows": rows,
            "note": "Fill = quantity received ÷ quantity ordered. Lead time = first receipt date − order date. Share of value is mean weekly demand × unit cost."}


def _supplier_reading(sp: dict, n: int) -> str:
    if n < 4:
        return "too few receipts to judge"
    parts = []
    fs = _f(sp.get("fill_shift"))
    if fs is not None and fs < -0.06:
        parts.append("fill falling")
    elif (_f(sp.get("fill_mean")) or 1.0) < 0.9:
        parts.append("chronically short")
    lr = _f(sp.get("lead_ratio"))
    if lr is not None and lr > 1.3:
        parts.append("lead lengthening")
    if not parts:
        return "steady"
    return ", ".join(parts)


# ── lanes ────────────────────────────────────────────────────────────────────
LANE_SCORE_MEANING = ("ZAAD's estimate that supply on this lane deteriorates over the coming weeks. It combines public "
                      "indicators with fixed weights: ship transits through the lane's chokepoints, port throughput, news "
                      "coverage of conflict on the route, the global supply-chain pressure index, and fuel and freight "
                      "indices. It is not a probability calibrated on your own shipments, and it is only as strong as the "
                      "share of those feeds that were available and fresh.")


def lanes_section(summary: dict) -> list[dict]:
    lanes = summary.get("lanes") or {}
    detail = summary.get("lane_detail") or {}
    exposure = summary.get("lane_exposure") or {}
    out = []
    for lane, v in lanes.items():
        key = str(lane).lower()
        risk, quality = _f(v.get("risk")), _f(v.get("quality"))
        d = detail.get(key) or {}
        ex = exposure.get(key) or {}
        missing = list(d.get("missing") or v.get("missing") or [])
        reasons = list(d.get("reasons") or v.get("reasons") or [])
        if quality is None or quality <= 0 or risk is None:
            attention, strength = "UNAVAILABLE", "none"
        else:
            attention = "ELEVATED" if risk >= 0.5 else "WATCH" if risk >= 0.25 else "NORMAL"
            strength = "strong" if quality >= 0.6 else "moderate" if quality >= 0.3 else "weak"
        external = [r for r in reasons if "UNAVAILABLE" not in r]
        external = [_humanise_lane_reason(r) for r in external]
        exp_lines = []
        if ex:
            exp_lines.append(f"{num(len(ex.get('suppliers') or []))} supplier(s): {', '.join(ex.get('suppliers') or [])}")
            if (ex.get("n_skus") or 0) > 0:
                exp_lines.append(f"{num(ex.get('n_skus'))} product(s), {pct(_f(ex.get('value_share')))} of demand value")
            else:
                exp_lines.append("No product with order history is sourced through this lane")
            o = ex.get("open_po_estimate")
            if o:
                if (o.get("lines") or 0) > 0:
                    line = f"{num(o.get('lines'))} purchase-order line(s) without a receipt yet ({num(o.get('units'))} units, {num(o.get('skus'))} products) — {o.get('basis')}"
                    cur = summary.get("currency")
                    if cur and _f(o.get("value_at_cost")) is not None:
                        line += f"; value at unit cost {num(o.get('value_at_cost'))} {cur}"
                    elif not cur:
                        line += "; value not shown (no currency declared in the economics inputs)"
                    exp_lines.append(line)
                else:
                    exp_lines.append("No purchase-order line without a receipt in the last 8 weeks of history")
            else:
                exp_lines.append("Open orders: not available (purchase orders and receipts could not be matched)")
        else:
            exp_lines.append("Exposure not available: no shipping route declared per supplier in the supplier list.")
        if attention == "UNAVAILABLE":
            response = "No public indicator covered this lane; ZAAD widened its uncertainty rather than assuming normal conditions. Declare the route per supplier to attach evidence."
        elif attention == "ELEVATED":
            response = "Review the purchase orders due through this lane in the next weeks; for exposed products with thin cover, consider committing the next order earlier rather than larger. ZAAD does not infer an alternative route unless one is declared."
        elif attention == "WATCH":
            response = "Monitor. No change to orders is indicated by the lane alone; watch receipts on this lane for lead-time slippage."
        else:
            response = "No action indicated."
        out.append({"lane": key, "label": key.replace("_", " ").title(), "attention": attention, "score": pct(risk, nd=0) if risk is not None else NOT_AVAILABLE,
                    "score_meaning": LANE_SCORE_MEANING, "evidence_strength": strength,
                    "evidence_note": (f"{pct(quality, nd=0)} of the lane's indicator feeds were available" + (f"; missing: {', '.join(missing)}" if missing else "")) if quality is not None else "no feeds",
                    "external": external or ["No indicator on this lane is outside its normal range."], "exposure": exp_lines, "response": response,
                    "internal": {"risk": risk, "quality": quality, "contributions": d.get("contributions"), "stale": d.get("stale")}})
    order = {"ELEVATED": 0, "WATCH": 1, "NORMAL": 2, "UNAVAILABLE": 3}
    out.sort(key=lambda x: (order.get(str(x["attention"]), 9), str(x["lane"])))
    return out


def _humanise_lane_reason(r: str) -> str:
    t = r.replace("gscpi elevated", "global supply-chain pressure index elevated").replace("fuel_index elevated", "fuel price index elevated")
    t = t.replace("freight_index_yoy elevated", "freight rate index elevated").replace("bab_el_mandeb", "Bab el-Mandeb").replace("_", " ")
    return t[0].upper() + t[1:]


# ── actions ──────────────────────────────────────────────────────────────────
def actions_section(policy: dict, findings: list[dict], lanes: list[dict], suppliers: dict) -> dict:
    now: list[dict] = []
    nxt: list[dict] = []
    mon: list[dict] = []
    oc = policy.get("outcome")
    if oc in ("keep_current", "keep_current_after_holdout", "not_run"):
        now.append({"text": "Keep your current purchasing policy.", "link": None})
    elif oc == "adopt_candidate":
        now.append({"text": f"Adopt {policy.get('candidate_label')} for the next order cycle, keeping your current policy as fallback; review the first cycle's orders in ZAAD before release.",
                    "link": {"kind": "decision", "id": "decisions", "label": "Run a decision"}})
    inter = [f for f in findings if f["category"] == "demand" and f["id"].startswith("demand-intermittent-") and f["id"] != "demand-intermittent-rest"]
    if inter:
        ids = [f["related"][0]["id"] for f in inter[:3] if f.get("related")]
        now.append({"text": f"Review the {len(ids)} most material intermittent-demand product(s) individually: {', '.join(ids)}.",
                    "link": {"kind": "sku", "id": ids[0], "label": "View SKU"} if ids else None})
    decl = [f["related"][0]["id"] for f in findings if f["category"] == "supplier" and f["severity"] in ("high", "medium") and f["id"].startswith("supplier-fill-decline") and f.get("related")]
    if decl:
        now.append({"text": f"Raise the recent fill-rate decline with {_join(decl)}; until it recovers, review the protection (safety cover) on the products most dependent on {'them' if len(decl) > 1 else 'it'}.",
                    "link": {"kind": "supplier", "id": decl[0], "label": "View supplier"}})
    drift = [f["related"][0]["id"] for f in findings if f["category"] == "supplier" and f["severity"] in ("high", "medium") and f["id"].startswith("supplier-lead-drift") and f.get("related")]
    if drift:
        now.append({"text": f"Plan the next orders on {_join(drift)} to the recent lead time, not the historical one.",
                    "link": {"kind": "supplier", "id": drift[0], "label": "View supplier"}})
    thin = next((f for f in findings if f["id"] == "inventory-thin-cover"), None)
    if thin:
        now.append({"text": thin["recommendation"], "link": {"kind": "po", "id": "open", "label": "View purchase orders"}})
    for f in findings:
        if f["category"] == "data":
            nxt.append({"text": f["recommendation"], "link": {"kind": "screen", "id": "upload", "label": "Upload"} if f["id"] in ("data-inventory-at-po", "data-margin", "data-carrying", "data-history") else None})
    if not any(f["id"] == "data-capacity" for f in findings) and suppliers.get("available"):
        pass
    for level in ("ELEVATED", "WATCH"):
        names = [ln["label"] for ln in lanes if ln["attention"] == level]
        if names:
            mon.append({"text": f"Purchase orders due through {_join(names)} (lane attention: {level.lower()}).", "link": {"kind": "po", "id": "open", "label": "View purchase orders"}})
    if suppliers.get("available"):
        judged = [r for r in suppliers["rows"] if r["evidence"] != "weak"]
        if judged:
            mon.append({"text": "Supplier fill rate and lead-time drift on each receipt for " + ", ".join(r["supplier"] for r in judged[:4]) + ".", "link": {"kind": "supplier", "id": judged[0]["supplier"], "label": "View supplier"}})
    if thin:
        mon.append({"text": "Cover on the products under one week of stock until their next receipt lands.", "link": {"kind": "screen", "id": "inventory", "label": "Inventory"}})
    if not mon:
        mon.append({"text": "Re-run the diagnostic after the next quarter of history.", "link": None})
    return {"now": now[:5], "next": nxt[:5], "monitor": mon[:5]}


def _join(ids: list) -> str:
    ids = [str(x) for x in ids]
    if len(ids) <= 1:
        return ids[0] if ids else ""
    if len(ids) <= 4:
        return ", ".join(ids[:-1]) + " and " + ids[-1]
    return ", ".join(ids[:3]) + f" and {len(ids) - 3} more"


# ── appendix ─────────────────────────────────────────────────────────────────
def appendix_section(summary: dict, policy: dict, readiness: dict, job_id: str, generated_at: str | None) -> dict:
    gates = summary.get("gate_config") or {}
    prov = summary.get("provenance") or {}
    priors = summary.get("priors_in_use") or {}
    cc = summary.get("carrying_cost") or {}
    ce = summary.get("candidate_evidence") or summary.get("candidates") or {}
    cand_rows = []
    for k, v in ce.items():
        cand_rows.append({"candidate": k, "label": CANDIDATE_SHORT.get(k, k), "mean": pct(_f(v.get("mean")), signed=True),
                          "lower_bound": pct(_f(v.get("lower_bound")), signed=True), "worst": pct(_f(v.get("worst")), signed=True) if v.get("worst") is not None else "—",
                          "folds": num(v.get("n_folds")) if v.get("n_folds") is not None else "—",
                          "inner_gates": "cleared" if v.get("passed") else "not cleared",
                          "holdout": (pct(_f(v.get("holdout_mean")), signed=True) + (" (held)" if v.get("holdout_gates") and all((v.get("holdout_gates") or {}).values()) else " (did not hold)"))
                          if v.get("holdout_mean") is not None else "not re-tested (did not win selection)"})
    methodology = [
        "Selection folds: rolling historical periods inside your history; each fold's orders see only what came before it, and its outcome is settled on the demand, supplier fills and lead times actually recorded after it.",
        f"Candidates and your current policy are settled on the same periods with the same rules; the cost change is (your cost − candidate cost) ÷ your cost per period, averaged over {num(gates.get('n_folds')) if gates.get('n_folds') else 'the'} folds.",
        f"Conservative estimate: a one-sided block-bootstrap lower bound at {pct(_f(gates.get('confidence')), nd=0) if gates.get('confidence') is not None else 'the configured'} confidence.",
        f"Selection rule (\"gate\"): lower bound > {pct(_f(gates.get('min_rel_improvement'))) if gates.get('min_rel_improvement') is not None else 'threshold'}; service not more than {pct(_f(gates.get('service_tolerance')), nd=0) if gates.get('service_tolerance') is not None else 'tolerance'} below yours in any fold; worst-fold loss within {pct(_f(gates.get('max_regret_share')), nd=0) if gates.get('max_regret_share') is not None else 'budget'}; every fold usable without solver fallbacks. Ties go to the simpler policy; your policy is the simplest.",
        f"Held-out re-check (winner's curse): the winning candidate is re-evaluated on {num(gates.get('n_holdout_folds')) if gates.get('n_holdout_folds') else 'additional'} later periods it was not chosen on; it must clear the same rule there or your policy is retained.",
        f"Scenario count per fold: {num(gates.get('n_scen'))}." if gates.get("n_scen") else "Scenario count per fold: as configured.",
        "Lane score: logistic combination of public indicators with fixed (assumed, not fitted) weights; quality = share of feeds available, reduced for stale feeds.",
        "Demand variability: coefficient of variation of weekly demand; zero share: fraction of weeks with no demand; cover: (on hand + in transit) ÷ recent weekly demand.",
        f"Data confidence rule: {readiness.get('confidence_rule')}.",
    ]
    assumptions = []
    for k, v in prov.items():
        assumptions.append({"input": k.replace("_", " "), "provenance": str(v)})
    for s_, p in priors.items():
        assumptions.append({"input": f"lead-time variability, supplier {s_}", "provenance": f"{p.get('source')} ({p.get('provenance')}); {p.get('note')}"})
    if cc:
        assumptions.append({"input": "carrying cost per week", "provenance": ", ".join(f"{k}: {v}" for k, v in cc.items() if not isinstance(v, dict))[:300]})
    sens = summary.get("carrying_cost_sensitivity")
    run = {"run_id": job_id, "generated_at": generated_at, "summary_version": summary.get("summary_version"),
           "report_version": REPORT_VERSION, "sector": summary.get("sector"),
           "history_range": summary.get("history_range"), "signal_sources": summary.get("signal_sources"),
           "internal_readiness_verdict": readiness.get("internal_verdict"), "internal_decision": summary.get("decision"),
           "internal_reason": summary.get("reason")}
    return {"methodology": methodology, "assumptions": assumptions, "candidates": cand_rows, "gates": gates,
            "carrying_cost_sensitivity": sens if isinstance(sens, (list, dict)) else None,
            "warnings": list(summary.get("warnings") or []), "run": run,
            "glossary": [
                {"term": "Your current purchasing policy", "internal": "incumbent", "meaning": "the ordering rule reconstructed from your purchase orders (or configured)"},
                {"term": "Historical periods", "internal": "folds", "meaning": "rolling windows of your history used to test a policy"},
                {"term": "Unseen validation periods", "internal": "held-out folds", "meaning": "later periods a candidate was not chosen on, used to confirm it"},
                {"term": "Conservative estimate", "internal": "lower bound", "meaning": "one-sided bootstrap confidence bound on the mean cost change"},
                {"term": "Selection rule", "internal": "gate", "meaning": "the set of thresholds a candidate must clear"},
                {"term": "Demand variability", "internal": "CV", "meaning": "standard deviation ÷ mean of weekly demand"},
                {"term": "Weeks with zero demand", "internal": "zero-share / intermittency", "meaning": "fraction of weeks with no demand"},
                {"term": "Data readiness", "internal": readiness.get("internal_verdict") or "READY / READY_WITH_CAVEATS / NOT_READY", "meaning": "whether required and preferred fields are present"},
            ]}


# ── executive summary and conclusion ─────────────────────────────────────────
def conclusion(summary: dict, policy: dict, readiness: dict) -> dict:
    oc = policy.get("outcome")
    if readiness.get("level") == "not_ready":
        return {"kind": "insufficient_data", "headline": "Not enough data for a purchasing diagnostic yet",
                "body": "Required fields are missing from the upload; see Data readiness for what to add."}
    if oc == "adopt_candidate":
        return {"kind": "adopt_candidate", "headline": f"{policy.get('candidate_label')} outperformed your current policy consistently on your history",
                "body": policy["explanation"][-1] if policy.get("explanation") else ""}
    if oc == "keep_current_after_holdout":
        return {"kind": "keep_current", "headline": "Keep your current purchasing policy: an alternative looked better on average but did not hold up on unseen periods",
                "body": "ZAAD found an alternative replenishment policy with stronger average historical performance, but its advantage was not consistent across the unseen validation periods. ZAAD therefore does not recommend replacing your current policy yet."}
    if oc == "keep_current":
        return {"kind": "keep_current", "headline": "Keep your current purchasing policy: no tested alternative beat it with enough margin",
                "body": "On your own history, no alternative cleared ZAAD's conservative selection rule. That is a valid result: your current policy is the defensible choice on the evidence available."}
    if oc == "not_run":
        return {"kind": "not_run", "headline": "Your current purchasing policy stands; the policy comparison could not run in full",
                "body": policy["explanation"][0] if policy.get("explanation") else ""}
    return {"kind": "other", "headline": "Diagnostic completed", "body": str(summary.get("reason") or "")}


def build_report(summary: dict, *, job_id: str, company: str, generated_at: str | None = None) -> dict:
    sector = str(summary.get("sector") or "")
    if sector and sector != "commercial":
        return _produce_report(summary, job_id=job_id, company=company, generated_at=generated_at)
    readiness = readiness_section(summary)
    ordering = ordering_section(summary)
    policy = policy_section(summary)
    findings = findings_section(summary, policy, readiness)
    suppliers = supplier_section(summary)
    lanes = lanes_section(summary)
    actions = actions_section(policy, findings, lanes, suppliers)
    appendix = appendix_section(summary, policy, readiness, job_id, generated_at)
    concl = conclusion(summary, policy, readiness)
    top = [f for f in findings if f["severity"] != "info"][:5]
    if len(top) < 3:
        top = findings[:5]
    exec_actions = (actions["now"] + actions["next"])[:4]
    return {"version": REPORT_VERSION, "run_id": job_id, "company": company, "generated_at": generated_at, "sector": "commercial",
            "conclusion": concl,
            "executive_summary": {"findings": [{"id": f["id"], "headline": f["headline"], "line": _one_line(f), "severity": f["severity"], "confidence": f["confidence"]} for f in top],
                                  "actions": [a["text"] for a in exec_actions],
                                  "confidence": {"level": readiness["confidence"], "statement": readiness["statement"]}},
            "readiness": readiness, "ordering_today": ordering, "policy_comparison": policy, "findings": findings,
            "suppliers": suppliers, "lanes": lanes, "actions": actions, "appendix": appendix}


def _one_line(f: dict) -> str:
    if f.get("summary_line"):
        return str(f["summary_line"])
    o = f.get("observation") or ""
    return o if len(o) <= 220 else o[:217].rsplit(" ", 1)[0] + "…"


def _produce_report(summary: dict, *, job_id: str, company: str, generated_at: str | None) -> dict:
    b = summary.get("benchmark") or {}
    r = summary.get("readiness") or {}
    gate = bool(b.get("gate_passed"))
    weeks_av, weeks_req = b.get("weeks_available"), b.get("weeks_required")
    level = "not_ready" if str(r.get("verdict") or "").startswith("NOT_READY") else "ready_with_limits"
    readiness = {"label": "NOT ENOUGH DATA TO ANALYZE" if level == "not_ready" else "ANALYZED — WITH LIMITATIONS", "level": level,
                 "confidence": "Moderate" if gate else "Low", "confidence_rule": "produce benchmark: moderate when the rolling-origin gate passed, low otherwise",
                 "internal_verdict": r.get("verdict"), "facts": [{"label": "Weeks available", "value": f"{num(weeks_av)} of {num(weeks_req)} required" if weeks_av is not None else NOT_AVAILABLE}],
                 "limitations": [], "missing_fields": [], "required_missing": list(r.get("missing") or []), "history_weeks": weeks_av, "products": None, "suppliers": None,
                 "unknown_margin_count": None, "statement": "Produce diagnostics use the rolling-origin benchmark; see the appendix for its verdict."}
    concl = {"kind": "adopt_candidate" if gate else "keep_current", "headline": "The stochastic two-sided plan beat the baseline on your history" if gate else "Keep the baseline: the stochastic plan did not clear the benchmark gate on your history",
             "body": str(b.get("verdict") or summary.get("reason") or "")}
    policy = {"available": bool(b), "current_label": "Your baseline", "candidate": "stochastic two-sided plan" if b else None, "candidate_label": "Stochastic two-sided plan",
              "rows": [{"metric": k.replace("_", " "), "current": "—", "candidate": str(v), "difference": "", "note": None} for k, v in (b.get("summary") or {}).items()] if isinstance(b.get("summary"), dict) else [],
              "explanation": [str(b.get("verdict") or "")], "outcome": "adopt_candidate" if gate else "keep_current", "fold_chart": None, "internal": {"benchmark": b}}
    actions = {"now": [{"text": "Adopt the stochastic plan for the next cycle with the baseline as fallback." if gate else "Keep the baseline plan.", "link": None}],
               "next": [{"text": "Upload the remaining history to reach the required weeks." if (weeks_av is not None and weeks_req is not None and weeks_av < weeks_req) else "Re-run after the next month of history.", "link": None}],
               "monitor": [{"text": "Waste and short-life lots.", "link": None}]}
    return {"version": REPORT_VERSION, "run_id": job_id, "company": company, "generated_at": generated_at, "sector": summary.get("sector"),
            "conclusion": concl, "executive_summary": {"findings": [], "actions": [a["text"] for a in actions["now"] + actions["next"]], "confidence": {"level": readiness["confidence"], "statement": readiness["statement"]}},
            "readiness": readiness, "ordering_today": {"summary": "Not applicable to the produce benchmark.", "items": [], "internal_label": None},
            "policy_comparison": policy, "findings": [], "suppliers": {"available": False, "rows": [], "note": "Not part of the produce benchmark."}, "lanes": [],
            "actions": actions, "appendix": {"methodology": ["Rolling-origin benchmark on the uploaded produce history."], "assumptions": [], "candidates": [], "gates": {},
                                             "carrying_cost_sensitivity": None, "warnings": list(summary.get("warnings") or []),
                                             "run": {"run_id": job_id, "generated_at": generated_at, "report_version": REPORT_VERSION, "sector": summary.get("sector"),
                                                     "internal_readiness_verdict": r.get("verdict"), "internal_decision": summary.get("decision"), "internal_reason": summary.get("reason")},
                                             "glossary": []}}
