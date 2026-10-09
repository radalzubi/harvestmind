"""Diagnostic report V3: the parts that keep two different questions apart.

    POLICY BENCHMARK     "Would a simpler fixed replenishment rule have been more robust than yours?"
    ZAAD DECISION REPLAY "What would ZAAD itself have decided at each historical date, and how did
                          those decisions perform?"

Everything here is deterministic and reads the job summary only: the benchmark from
`summary["candidate_evidence"]` (the safe selector) and the replay from `summary["optimizer_replay"]`
(`zaad/full/historical.py`). No model API. A metric the replay did not measure is absent or marked
"Not available", never zero; no saving is projected.

Also here: the single canonical provenance ledger every section reads from (OPERATOR / MEASURED /
INFERRED / PUBLIC_BENCHMARK / ASSUMED / UNKNOWN), the automated consistency checks over it, and the
computed intersections behind the management-level findings.
"""
from __future__ import annotations

import json

from zaad.full import comparator
import math
from typing import Any

NOT_AVAILABLE = "Not available from current data"
CANONICAL = ("OPERATOR", "MEASURED", "INFERRED", "PUBLIC_BENCHMARK", "ASSUMED", "UNKNOWN")

# the diagnostic (domain.economics.Provenance) and the frozen engine (zaad.full.workspace) each have
# their own vocabulary; both map onto the six canonical labels
_DIAG = {"operator": "OPERATOR", "measured": "MEASURED", "public_benchmark": "PUBLIC_BENCHMARK", "assumed": "ASSUMED", "unknown": "UNKNOWN"}
_ENGINE = {"CUSTOMER_PROVIDED": "OPERATOR", "INFERRED_FROM_HISTORY": "MEASURED", "CONFIGURED_ASSUMPTION": "ASSUMED",
           "NOT_AVAILABLE": "UNKNOWN", "DERIVED_FROM_OPERATOR_HISTORY": "INFERRED"}
# an input the diagnostic labels "measured" but derives indirectly (a peak times 1.25 is a construction, not
# a measurement) is INFERRED in the canonical ledger
_INDIRECT = {"supplier_capacity", "incumbent_rule"}

PLAIN = {"OPERATOR": "supplied by you", "MEASURED": "measured from your transactions", "INFERRED": "inferred from your history",
         "PUBLIC_BENCHMARK": "a public benchmark", "ASSUMED": "a stated assumption", "UNKNOWN": "unknown (the decision does not depend on it)"}


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def pct(x: Any, signed: bool = False, nd: int = 1) -> str:
    v = _f(x)
    if v is None:
        return NOT_AVAILABLE
    s = f"{v * 100:.{nd}f}%"
    return (f"+{s}" if v > 0 else s) if signed else s


def num(x: Any, nd: int = 0) -> str:
    v = _f(x)
    return NOT_AVAILABLE if v is None else f"{v:,.{nd}f}"


def money(x: Any, currency: str | None) -> str:
    """An amount in the declared currency, or the bare figure when none is declared (the section then
    carries one note saying so)."""
    v = _f(x)
    if v is None:
        return NOT_AVAILABLE
    return f"{v:,.0f} {currency}" if currency else f"{v:,.0f}"


def canonical(value: Any, key: str = "") -> str:
    """Map either vocabulary onto the canonical six; unknown strings stay UNKNOWN."""
    if value is None:
        return "UNKNOWN"
    v = str(value)
    if v.upper() in CANONICAL:
        out = v.upper()
    elif v in _ENGINE:
        out = _ENGINE[v]
    elif v.lower() in _DIAG:
        out = _DIAG[v.lower()]
    else:
        return "UNKNOWN"
    if key in _INDIRECT and out == "MEASURED":
        out = "INFERRED"
    return out


# ── provenance ledger ────────────────────────────────────────────────────────
def provenance_ledger(summary: dict) -> list[dict]:
    """One row per decisive input, one canonical label each, with the note that explains the label and,
    where the diagnostic and the replay engine treat an input differently, both treatments."""
    prov = summary.get("provenance") or {}
    replay = summary.get("optimizer_replay") or {}
    eprov = ((replay.get("build") or {}).get("provenance") or {})
    unknown_margin = summary.get("unknown_margin_count")
    rows: list[dict] = []

    def add(input_: str, label: str, basis: str, note: str | None = None, replay_label: str | None = None, replay_note: str | None = None) -> None:
        rows.append({"input": input_, "provenance": label, "plain": PLAIN.get(label, label), "basis": basis, "note": note,
                     "replay_provenance": replay_label, "replay_note": replay_note})

    add("Unit cost", canonical(prov.get("unit_cost"), "unit_cost"), "product list")
    sc = canonical(prov.get("shortage_cost_per_unit"), "shortage_cost_per_unit")
    margin_note = (f"{num(unknown_margin)} product(s) have no price or margin: the policy benchmark anchors them to your current rule and does not price their lost sales"
                   if unknown_margin else None)
    replay_margin = None
    replay_margin_note = None
    if replay.get("status") in ("complete", "partial"):
        replay_margin = "ASSUMED" if unknown_margin else "OPERATOR"
        replay_margin_note = ("the replay's engine values a lost sale at a stated margin over unit cost (30%) where no price is given, so it does price those lost sales — the two engines treat this input differently on purpose and both treatments are shown"
                              if unknown_margin else "the replay values lost sales at your selling price over unit cost")
    add("Shortage cost (margin on a lost sale)", sc, "unit price or contribution margin per product", margin_note, replay_margin, replay_margin_note)
    add("Supplier fill", canonical(prov.get("supplier_fill"), "supplier_fill"), "receipts against purchase orders")
    add("Lead time", canonical(prov.get("lead_time"), "lead_time"), "first receipt date minus order date")
    cap = canonical(prov.get("supplier_capacity"), "supplier_capacity")
    cap_note = "1.25 × the largest weekly quantity you ever ordered from the supplier (2 × mean demand where no orders exist)" if cap in ("INFERRED", "ASSUMED") else None
    replay_cap = None
    caps = [canonical(v) for k, v in eprov.items() if k.endswith(".capacity")]
    if caps:
        replay_cap = "OPERATOR" if all(c == "OPERATOR" for c in caps) else ("INFERRED" if any(c == "MEASURED" or c == "INFERRED" for c in caps) else "UNKNOWN")
        if replay_cap == "INFERRED":
            replay_cap = "INFERRED"
    add("Supplier capacity", cap, "supplier list or product list; else purchase-order peaks", cap_note, replay_cap,
        "the replay's engine reads the same supplier list; without it, 1.25 × the weekly purchase-order peak, else unbounded" if replay_cap and replay_cap != "OPERATOR" else None)
    add("Opening inventory", canonical(prov.get("opening_inventory"), "opening_inventory"), "latest stock count before the plan date")
    hold = canonical(prov.get("holding_rate_per_period"), "holding_rate_per_period")
    add("Carrying cost", hold, "economics inputs", "24% of inventory value per year (capital 10%, storage 8%, insurance 1%, shrink 5%)" if hold == "PUBLIC_BENCHMARK" else None,
        canonical(eprov.get("location.main.holding_per_value_period")) if eprov else None,
        "the replay's engine uses the same public storage and capital benchmarks when none are declared" if eprov and canonical(eprov.get("location.main.holding_per_value_period")) != "OPERATOR" else None)
    inc = summary.get("incumbent_detail") or {}
    src = inc.get("source") or ("inferred" if "INFERRED" in str(summary.get("incumbent") or "") else None)
    add("Your purchasing rule", "INFERRED" if src == "inferred" else "OPERATOR" if src in ("configured", "schedule") else "UNKNOWN",
        "purchase-order history (cover level and cadence)" if src == "inferred" else "your configuration",
        None, canonical((replay.get("scope") or {}).get("rule_provenance"), "incumbent_rule") if replay.get("scope") else None,
        f"the replay's engine reconstructs the cadence as `{(replay.get('scope') or {}).get('incumbent_rule')}`" if replay.get("scope") else None)
    add("Customer demand", "MEASURED", "customer orders as placed", "recorded shortfalls do not reduce it")
    return rows


def consistency_checks(report: dict) -> list[dict]:
    """Automated checks that no section contradicts the ledger. Each check names what it compared."""
    ledger = {r["input"]: r for r in report.get("provenance_ledger") or []}
    checks: list[dict] = []
    findings = {f["id"]: f for f in report.get("findings") or []}
    lim_text = " ".join(li.get("effect", "") for li in (report.get("readiness") or {}).get("limitations") or []).lower()

    cap = ledger.get("Supplier capacity")
    if cap:
        f = findings.get("data-capacity")
        ok = True
        detail = f"ledger: {cap['provenance']}"
        if cap["provenance"] in ("INFERRED", "ASSUMED"):
            ok = f is not None and "inferred" in f["headline"].lower()
            detail += "; finding says inferred" if ok else "; finding missing or worded differently"
        else:
            ok = f is None
            detail += "; no 'inferred capacity' finding" if ok else "; a finding calls it inferred"
        checks.append({"check": "supplier capacity is described the same way everywhere", "pass": ok, "detail": detail})
    sc = ledger.get("Shortage cost (margin on a lost sale)")
    if sc:
        f = findings.get("data-margin")
        if sc["provenance"] == "UNKNOWN":
            ok = f is not None and "no price or margin" in f["headline"]
            detail = "ledger UNKNOWN; finding present" if ok else "ledger UNKNOWN but no margin finding"
        else:
            ok = f is None
            detail = "ledger known; no margin finding" if ok else "ledger known but a margin finding exists"
        if sc.get("replay_provenance") and sc["replay_provenance"] != sc["provenance"]:
            ok = ok and bool(sc.get("replay_note"))
            detail += f"; the replay treats it as {sc['replay_provenance']} and the ledger explains why" if sc.get("replay_note") else "; the replay treats it differently WITHOUT explanation"
        checks.append({"check": "shortage cost: the diagnostic and the replay engine agree or the difference is explained", "pass": ok, "detail": detail})
    hold = ledger.get("Carrying cost")
    if hold:
        f = findings.get("data-carrying")
        ok = (hold["provenance"] == "PUBLIC_BENCHMARK") == (f is not None)
        checks.append({"check": "carrying cost benchmark is stated wherever it applies", "pass": ok, "detail": f"ledger {hold['provenance']}; finding {'present' if f else 'absent'}"})
    if "inferred" in lim_text and cap and cap["provenance"] == "OPERATOR":
        checks.append({"check": "readiness limitations do not call a supplied capacity inferred", "pass": False, "detail": "limitations mention inferred capacity while the ledger says OPERATOR"})
    else:
        checks.append({"check": "readiness limitations agree with the ledger", "pass": True, "detail": "no contradiction found"})
    pb = report.get("policy_benchmark") or {}
    text = " ".join(pb.get("explanation") or []).lower()
    checks.append({"check": "the policy benchmark never describes itself as ZAAD's optimizer", "pass": "optimizer" not in text and "zaad's own" not in text,
                   "detail": "benchmark explanation scanned for 'optimizer'"})
    rp = report.get("optimizer_replay") or {}
    checks.append({"check": "the replay section is separate from the benchmark", "pass": bool(rp) and rp.get("question") != pb.get("question"),
                   "detail": "distinct questions on the two sections"})
    return checks


# ── the policy benchmark framing ─────────────────────────────────────────────
BENCHMARK_QUESTION = "Would a simpler fixed replenishment rule have historically been more robust than your own?"
BENCHMARK_EXPLAINER = ("This tests whether a fixed purchasing rule (for example a fixed order-up-to cover level) appears robust enough to replace "
                       "your reconstructed rule. Candidates are chosen on selection periods and then re-tested on later unseen periods. "
                       "A candidate that wins the selection periods and fails the unseen ones is a rule that did not generalise. "
                       "This section says nothing about ZAAD's adaptive optimizer, which is replayed separately below.")


def frame_benchmark(policy: dict) -> dict:
    """The V2 policy comparison with V3 framing: renamed, its question stated, its wording about fixed rules."""
    out = dict(policy)
    out["title"] = "Simple policy benchmark"
    out["question"] = BENCHMARK_QUESTION
    out["explainer"] = BENCHMARK_EXPLAINER
    out["candidate_kind"] = "a fixed replenishment rule"
    oc = policy.get("outcome")
    label = str(policy.get("candidate_label") or "policy")
    article = ("an " if label[:1].lower() in "aeiou" else "a ") + label[:1].lower() + label[1:]
    if oc == "keep_current_after_holdout":
        out["statement"] = (f"{article[:1].upper()}{article[1:]} performed strongly on the periods used to select it, but the improvement "
                            "did not persist on later unseen periods. ZAAD therefore does not recommend replacing your existing purchasing rule with that fixed policy.")
    elif oc == "adopt_candidate":
        out["statement"] = (f"{article[:1].upper()}{article[1:]} beat {policy.get('reference_label') or 'the reconstructed rule'} on the selection periods and held on the unseen "
                            "periods. It is a defensible fixed rule; whether ZAAD's adaptive decisions do better is a separate question, answered below.")
    elif oc == "keep_current":
        out["statement"] = f"No fixed replenishment rule cleared the conservative selection rule against {policy.get('reference_label') or 'the reconstructed rule'}. It stands as the fixed-rule baseline."
    elif oc == "not_run":
        out["statement"] = "The fixed-rule benchmark could not run in full on this history."
    else:
        out["statement"] = out.get("explanation", [""])[0] if out.get("explanation") else ""
    return out


# ── the replay section ───────────────────────────────────────────────────────
REPLAY_QUESTION = "What would ZAAD itself have decided at each historical decision date, and how would those decisions have performed?"
REPLAY_EXPLAINER = ("ZAAD optimizes each decision with the information available at that moment. Historical replay re-runs the production "
                    "optimizer at every weekly decision date on the state its own earlier decisions produced, then settles what followed under "
                    "the realised or simulated environment. It evaluates how those decisions would have performed; it does not imply ZAAD could "
                    "know the future, and a decision that was right given what was known can still lose on one particular realisation.")


_PROVENANCE_WORDS = {"INFERRED_FROM_HISTORY": "reconstructed from purchase-order history", "CUSTOMER_PROVIDED": "operator-declared",
                     "CONFIGURED_ASSUMPTION": "configured assumption", "NOT_AVAILABLE": "not available"}


def _customer_safe_comparison(comparison: dict) -> dict:
    """The replay's comparator contract with engine provenance codes rendered as words (the report never leaks enums)."""
    if not comparison:
        return {}
    out = json.loads(json.dumps(comparison))
    for holder in (out.get("decision_reference") or {}, ((out.get("legs") or {}).get("rule") or {})):
        if holder.get("provenance") in _PROVENANCE_WORDS:
            holder["provenance"] = _PROVENANCE_WORDS[holder["provenance"]]
    return out


def replay_section(summary: dict) -> dict:
    r = summary.get("optimizer_replay") or {}
    currency = (r.get("scope") or {}).get("currency") if summary.get("currency") else None
    out: dict = {"title": "ZAAD historical decision replay", "question": REPLAY_QUESTION, "explainer": REPLAY_EXPLAINER,
                 "available": r.get("status") in ("complete", "partial"), "status": r.get("status") or "unavailable"}
    if not out["available"]:
        out["statement"] = ("ZAAD's decision replay could not be completed on this history: " + str(r.get("reason") or "not run") + ". "
                            "The policy benchmark above is not a substitute for it; no optimizer result is reported.")
        out["reason"] = r.get("reason")
        return out
    scope, cov, legs = r.get("scope") or {}, r.get("coverage") or {}, r.get("legs") or {}
    # H3a: the comparator the replay actually used, and what it allows the report to say. An older replay result
    # without the section never established exactness, so its historical-action leg is not called "actual".
    comparison = _customer_safe_comparison(r.get("comparison") or {})
    out["comparison"] = comparison or {"mode": comparator.HISTORICAL_COMPARISON_MODE, "readiness": comparator.CONDITIONAL, "claim_class": comparator.MODEL_COMPARISON,
                                       "comparator": {"type": comparator.ACTUAL_HISTORICAL_ACTION, "fidelity": comparator.NOT_AVAILABLE},
                                       "permissions": {k: k in ("can_recommend", "can_compare") for k in comparator.PERMISSION_KEYS},
                                       "caveats": ["this replay result predates comparator provenance; exactness of the historical-action comparator was not established"]}
    exact_claim = bool((out["comparison"].get("permissions") or {}).get("can_claim_historical_counterfactual_difference"))
    action_label = comparator.actual_action_label(out["comparison"])
    out["comparator_label"] = action_label
    out["reference_label"] = ((out["comparison"].get("decision_reference") or {}).get("label")) or comparator.policy_label(scope.get("rule_provenance"))
    out["claim_class"] = out["comparison"].get("claim_class")
    d_actual, d_rule = (r.get("differences") or {}).get("zaad_vs_actual") or {}, (r.get("differences") or {}).get("zaad_vs_rule") or {}
    a, z, ru = legs.get("actual") or {}, legs.get("zaad") or {}, legs.get("rule") or {}
    conf = r.get("confidence") or {}
    prov = r.get("settlement_provenance") or {}
    W, planned = cov.get("reviews_completed") or 0, cov.get("reviews_planned") or 0
    share = _f(scope.get("demand_value_share"))
    window = d_actual.get("window") or {}
    rel = _f(window.get("relative"))
    if rel is None and _f(a.get("realized_cost")) is not None and _f(z.get("realized_cost")) is not None and abs(float(a["realized_cost"])) > 1e-9:
        rel = (float(a["realized_cost"]) - float(z["realized_cost"])) / abs(float(a["realized_cost"]))
    # statement
    coverage_txt = f"{num(W)} historical decision dates" + (f" ({num(W)} of {num(planned)} planned; stopped at the time budget)" if r.get("status") == "partial" else "")
    scope_txt = f"{num(scope.get('sku_count'))} of your {num(scope.get('skus_in_workspace'))} products" + (f", carrying {pct(share, nd=0)} of demand value" if share is not None else "")
    if rel is not None and a:
        direction = "less" if rel > 0 else "more"
        worst = _f(d_actual.get("worst"))
        worst_txt = f" and the worst single period {money(-worst, currency)} against" if (worst is not None and worst < 0) else ""
        fidelity = (out["comparison"].get("comparator") or {}).get("fidelity")
        qualifier = ("" if exact_claim else
                     f" This is a modelled comparison, not a claim against the operator: the historical-action comparator is {str(fidelity or 'not established').lower()}"
                     + (" (recorded orders were adjusted to the declared physical envelope before settlement)" if fidelity == comparator.TRANSFORMED else
                        " (some recorded lines could not be identified to a source)" if fidelity == comparator.INCOMPLETE else "") + ".")
        stmt = (f"In this historical counterfactual replay, re-run at {coverage_txt} on {scope_txt}, ZAAD's modelled path cost {pct(abs(rel))} {direction} than "
                f"the path of {action_label} over the evaluated window, with {pct(_f(d_actual.get('share_improved')), nd=0)} of periods better{worst_txt}. "
                f"ZAAD's path is counterfactual and settles on measured, inferred, simulated or assumed supplier behaviour; nothing here is a realized benefit. "
                f"Replay confidence: {str(conf.get('level', '')).lower()}.{qualifier}")
    else:
        stmt = f"Re-run at {coverage_txt} on {scope_txt}; the window total could not be compared."
    out["statement"] = stmt
    out["currency"] = currency
    out["currency_note"] = None if currency else "Amounts are in your cost units as uploaded; no currency is declared in the economics inputs."
    out["scope"] = {"skus": scope.get("skus"), "sku_count": scope.get("sku_count"), "skus_in_workspace": scope.get("skus_in_workspace"),
                    "demand_value_share": share, "origin": scope.get("origin"), "horizon_weeks": scope.get("horizon"), "rule": scope.get("incumbent_rule"),
                    "text": f"{scope_txt}; weekly decision dates from {scope.get('origin')}; the optimizer plans {num(scope.get('horizon'))} weeks ahead at each date"}
    sel = scope.get("selection") or {}
    scov = sel.get("coverage") or {}
    if sel.get("rule") == "window_value":
        sel_text = (f"STUDY SELECTION: the {num(scope.get('sku_count'))} products carrying the most demand value over the whole replay window "
                    f"({(sel.get('window') or {}).get('start')} to {(sel.get('window') or {}).get('end')}), one intermittent-demand product included where one exists; "
                    f"this choice reads the window's demand only to decide which products are studied and never enters a decision request. "
                    f"Coverage: {pct(_f(scov.get('window_demand_value_share')), nd=0)} of window demand value, {pct(_f(scov.get('d0_demand_value_share')), nd=0)} of demand value at the first decision date, "
                    f"{pct(_f(scov.get('purchase_order_line_share')), nd=0)} of the purchase-order lines placed in the window")
    elif sel.get("rule") == "d0_value":
        sel_text = f"the top products by demand value at the first decision date (a fixed rule, not a choice of dates); coverage {pct(share, nd=0)} of demand value"
    else:
        sel_text = "the top products by demand value at the first decision date (a fixed rule, not a choice of dates)"
    out["coverage"] = {"completed": W, "planned": planned, "partial": r.get("status") == "partial", "dates": cov.get("dates"),
                       "text": coverage_txt, "selection_rule": sel_text + "; every weekly decision date in the window in order",
                       "selection": {"rule": sel.get("rule"), "information": sel.get("information"), "coverage": scov, "strata": sel.get("strata"), "swapped": sel.get("swapped")}}
    # summary table: only measured legs and metrics
    rows: list[dict] = []

    def row(metric: str, key: str, fmt, note: str | None = None, lower_is_better: bool = True) -> None:
        av, zv = a.get(key), z.get(key)
        fa, fz = _f(av), _f(zv)
        diff = (fz - fa) if (fa is not None and fz is not None) else None
        rows.append({"metric": metric, "actual": fmt(av), "rule": fmt(ru.get(key)) if ru else NOT_AVAILABLE, "zaad": fmt(zv),
                     "difference": (("−" if diff < 0 else "+") + fmt(abs(diff)).replace("+", "")) if diff is not None else NOT_AVAILABLE,
                     "better": (None if diff is None or abs(diff) < 1e-9 else ((diff < 0) == lower_is_better)), "note": note})
    row("Total modelled cost over the window", "realized_cost", lambda v: money(v, currency), "purchase + carrying + financing + shortage, stock valued at the window's ends")
    row("Cost including the value of stock left at the end", "continuation_cost", lambda v: money(v, currency), "residual stock valued as future avoided purchases")
    row("Service (share of demand served)", "service", lambda v: pct(v), "unit fill inside the window", lower_is_better=False)
    row("Unmet demand (units)", "unmet_units", lambda v: num(v))
    row("Periods below the service target", "breaches", lambda v: num(v))
    row("Average stock on hand (units)", "avg_inventory_units", lambda v: num(v), "lower is not always better; read with service")
    row("Units purchased", "units_purchased", lambda v: num(v), None, lower_is_better=False)
    row("Orders placed", "orders_placed", lambda v: num(v), None, lower_is_better=False)
    comps_a, comps_z = a.get("components") or {}, z.get("components") or {}
    for label, key in (("Purchase cost", "PURCHASE"), ("Carrying cost", "CARRYING"), ("Shortage cost (lost margin)", "SHORTAGE"), ("Financing", "FINANCING")):
        av, zv = _f(comps_a.get(key)), _f(comps_z.get(key))
        if av is None or zv is None:
            continue
        diff = zv - av
        rows.append({"metric": label, "actual": money(av, currency), "rule": money((ru.get("components") or {}).get(key), currency) if ru else NOT_AVAILABLE,
                     "zaad": money(zv, currency), "difference": ("−" if diff < 0 else "+") + money(abs(diff), currency), "better": None if abs(diff) < 1e-9 else diff < 0, "note": None})
    out["table"] = rows
    out["not_measured"] = ["Waste / expiry: no lot expiry recorded in the upload; the settlement's disposal line stayed zero.",
                           "Expedites, supplier switches, cancelled or amended orders: the workspace declares one source per product and keep-only open orders, so the optimizer had no switch, expedite or amendment to choose.",
                           "Working capital: the financing and carrying lines above are the ledger's; no separate working-capital figure is projected."]
    # decisions changed
    decs = r.get("decisions") or []
    changed = [d for d in decs if d.get("zaad_action") in ("order", "more", "less") or (d.get("zaad_action") == "no order" and (d.get("actual_qty") or 0) > 0)]
    zr = r.get("zaad_reviews") or []
    retained = sum(1 for e in zr if str(e.get("status")) == "RETAIN_INCUMBENT")
    identical_to_rule = bool(decs) and all(abs((d.get("zaad_qty") or 0.0) - (d.get("rule_qty") or 0.0)) < 1e-6 for d in decs)
    out["decisions_summary"] = {"rows": len(decs), "changed": len(changed), "retained_rule_reviews": retained, "identical_to_rule": identical_to_rule,
                                "zaad_ordered_where_you_did_not": sum(1 for d in decs if d.get("zaad_action") == "order"),
                                "zaad_ordered_less": sum(1 for d in decs if d.get("zaad_action") == "less"),
                                "zaad_ordered_more": sum(1 for d in decs if d.get("zaad_action") == "more"),
                                "zaad_did_not_order_where_you_did": sum(1 for d in decs if d.get("zaad_action") == "no order" and (d.get("actual_qty") or 0) > 0),
                                "abstained_reviews": sum(1 for e in (r.get("zaad_reviews") or []) if e.get("fallback_to_rule")),
                                "units_difference": sum((d.get("quantity_difference") or 0.0) for d in decs)}
    out["retention_note"] = (f"At every one of the {num(W)} decision dates the optimizer retained your reconstructed rule (no candidate cleared its own gates), so ZAAD's orders are the "
                             f"rule's orders and the ZAAD column equals the rule column. The comparison against {action_label} then measures the rule as ZAAD would have applied it, not a different plan."
                             if identical_to_rule and retained == W and W > 0 else
                             (f"The optimizer retained your reconstructed rule on {num(retained)} of the {num(W)} decision dates and recommended its own plan on the others."
                              if retained else None))
    # decision-change rate against the reconstructed rule (§16), the planner's own materiality
    ch = r.get("decision_changes") or {}
    if ch.get("available"):
        ro, ln, mg = ch.get("review_outcomes") or {}, ch.get("lines") or {}, ch.get("magnitude") or {}
        n_changed = ch.get("changed_lines") or 0
        out["decision_changes"] = {
            **{k: v for k, v in ch.items() if k != "per_review"},
            "text": (f"On {num(ro.get('retained_rule'))} of the {num(W)} decision dates the optimizer retained your reconstructed rule, on {num(ro.get('own_plan'))} it recommended its own plan, "
                     f"and on {num(ro.get('abstained_or_fallback'))} it abstained and the rule stood. Across {num(ch.get('lines_total'))} product-weeks ZAAD's order matched the rule's on "
                     f"{num(ln.get('same'))}; it ordered more on {num(ln.get('more'))}, less on {num(ln.get('less'))}, placed an order the rule did not on {num(ln.get('new'))} "
                     f"and dropped one the rule placed on {num(ln.get('dropped'))}. {num(ch.get('material_lines'))} of the {num(n_changed)} changed lines were material by the planner's own "
                     f"standard ({ch.get('materiality_rule')}); {num((ch.get('timing') or {}).get('deferred_one_week'))} were a one-week deferral and "
                     f"{num((ch.get('timing') or {}).get('advanced_one_week'))} a one-week advance. Units added {num(mg.get('units_added'))}, removed {num(mg.get('units_removed'))} "
                     f"(value {money(mg.get('value_added'), currency)} / {money(mg.get('value_removed'), currency)}). Source changes: {ch.get('source_changes')}. Open-order changes: {ch.get('open_order_changes')}.")
                    if n_changed else
                    (f"On every one of the {num(W)} decision dates ZAAD's executed orders matched the reconstructed rule's line for line: the optimizer retained the rule on "
                     f"{num(ro.get('retained_rule'))} dates and abstained on {num(ro.get('abstained_or_fallback'))}. No value is claimed from a plan that was never different.")}
    else:
        out["decision_changes"] = {"available": False, "text": "Decision-change accounting is not available: " + str(ch.get("reason") or "the rule leg did not complete")}
    ev = r.get("evidence_basis") or {}
    if ev.get("by_leg"):
        def basis_txt(leg: str) -> str:
            sh = ((ev["by_leg"].get(leg) or {}).get("shares") or {})
            return ", ".join(f"{pct(sh.get(k), nd=0)} {k.lower()}" for k in ("MEASURED", "INFERRED", "SIMULATED", "ASSUMED"))
        out["evidence_basis"] = {**ev, "text": (f"Settlement basis of each leg's delivered units — {action_label}: {basis_txt('actual')}; {out['reference_label']}: {basis_txt('rule')}; "
                                                f"ZAAD: {basis_txt('zaad')}. Demand is measured throughout; cost and service of a leg both rest on its delivered units, so an inferred share "
                                                "is an inferred share of both. Nothing inferred or simulated is an observed outcome.")}
    rc = r.get("rule_conformance") or {}
    if rc.get("changed_lines"):
        out["rule_conformance_note"] = (f"The reconstructed rule's projected orders were scaled to the declared shared supplier capacity on {num(rc.get('changed_lines'))} line(s) "
                                        "(the rule orders every product of a supplier in the same week, which your own staggered orders never did); the scaled plan is the rule leg and the incumbent ZAAD was compared against.")
    # per period
    series, dates = d_actual.get("series") or [], cov.get("dates") or []
    negatives = [(dates[i] if i < len(dates) else str(i), v) for i, v in enumerate(series) if v < -1e-9]
    worst_i = min(range(len(series)), key=lambda i: series[i]) if series else None
    out["periods"] = {"series": series, "dates": dates, "currency": currency, "improved": _f(d_actual.get("share_improved")), "worse": _f(d_actual.get("share_worse")),
                      "mean": _f(d_actual.get("mean")), "median": _f(d_actual.get("median")), "worst": _f(d_actual.get("worst")), "best": _f(d_actual.get("best")),
                      "sd": _f(d_actual.get("sd")), "ci80": d_actual.get("ci80_mean"), "n_negative": len(negatives),
                      "worst_date": dates[worst_i] if worst_i is not None and worst_i < len(dates) else None,
                      "text": (f"ZAAD's modelled path cost less than the path of {action_label} in {pct(_f(d_actual.get('share_improved')), nd=0)} of the {num(W)} periods and more in "
                               f"{pct(_f(d_actual.get('share_worse')), nd=0)}. The average per-period difference was {money(d_actual.get('mean'), currency)} in ZAAD's favour"
                               if (_f(d_actual.get('mean')) or 0) > 0 else
                               f"ZAAD's modelled path cost less than the path of {action_label} in {pct(_f(d_actual.get('share_improved')), nd=0)} of the {num(W)} periods and more in "
                               f"{pct(_f(d_actual.get('share_worse')), nd=0)}. The average per-period difference was {money(abs(_f(d_actual.get('mean')) or 0), currency)} against ZAAD")
                              + (f"; the worst period ({dates[worst_i]}) cost {money(abs(series[worst_i]), currency)} more under ZAAD." if worst_i is not None and series[worst_i] < 0 and worst_i < len(dates) else ".")
                              + (" A losing period is not a failed decision: it is the cost of a decision that was right given what was known at the time and wrong for that one realisation." if negatives else "")
                              + (f" 80% interval on the mean per-period difference: {money(d_actual['ci80_mean'][0], currency)} to {money(d_actual['ci80_mean'][1], currency)}." if d_actual.get("ci80_mean") else " Too few periods for a defensible interval on the mean.")}
    # vs the reconstructed rule
    if d_rule and d_rule.get("periods"):
        wr = d_rule.get("window") or {}
        rr = _f(wr.get("relative"))
        if identical_to_rule:
            txt = "ZAAD's orders were identical to your reconstructed rule's at every decision date, so there is no difference against the rule to report."
        else:
            txt = f"Against your reconstructed rule replayed on the same snapshots, ZAAD cost {pct(abs(rr or 0))} {'less' if (rr or 0) > 0 else 'more'} over the window ({pct(_f(d_rule.get('share_improved')), nd=0)} of periods better)."
        out["vs_rule"] = {"relative": rr, "improved": _f(d_rule.get("share_improved")), "identical": identical_to_rule, "text": txt}
    # regimes
    reg = (r.get("regimes") or {}).get("by_planner_state") or {}
    out["regimes"] = [{"state": k, "periods": v["periods"], "mean": _f(v["mean"]), "improved": _f(v["share_improved"]),
                       "text": f"{k.title()} reviews ({num(v['periods'])}): ZAAD better in {pct(_f(v['share_improved']), nd=0)} of periods, average {money(abs(v['mean']), currency)} {'in ZAAD’s favour' if v['mean'] > 0 else 'against'}"}
                      for k, v in sorted(reg.items(), key=lambda kv: -kv[1]["periods"])]
    out["regime_note"] = ("Split by the planner's own review state; only groups with three or more periods are shown." if out["regimes"] else
                          "Too few periods per planner state to split performance by regime.")
    oreg = (r.get("regimes") or {}).get("by_operating_regime") or {}
    defs = (r.get("regimes") or {}).get("definitions") or {}
    out["operating_regimes"] = [{"regime": k, "periods": v["periods"], "mean": _f(v["mean"]), "improved": _f(v["share_improved"]), "definition": defs.get(k),
                                 "text": f"{k.replace('_', ' ').capitalize()} weeks ({num(v['periods'])}): ZAAD better in {pct(_f(v['share_improved']), nd=0)} of periods, average {money(abs(v['mean']), currency)} {'in ZAAD’s favour' if v['mean'] > 0 else 'against'}"}
                                for k, v in sorted(oreg.items(), key=lambda kv: -kv[1]["periods"])]
    out["operating_regime_note"] = ("Weeks labelled from each decision snapshot only (supplier deterioration, intermittent demand, constrained inventory, stable); a week can carry several labels. "
                                    "Analysis only: nothing here was used by the optimizer." if out["operating_regimes"] else "Too few weeks per operating regime to split performance.")
    # settlement provenance
    shares = prov.get("shares_by_zaad_order") or {}
    out["settlement"] = {"shares": shares, "orders": prov.get("zaad_orders"), "rules": prov.get("rules"),
                         "text": (f"Of ZAAD's {num(prov.get('zaad_orders'))} replayed orders, {pct(shares.get('MEASURED'), nd=0)} settled on the supplier's observed delivery for the same order, "
                                  f"{pct(shares.get('INFERRED'), nd=0)} on observed supplier behaviour applied to a different quantity or a nearby week, "
                                  f"{pct(shares.get('SIMULATED'), nd=0)} on a seeded draw from the supplier's own record, and {pct(shares.get('ASSUMED'), nd=0)} on assumed behaviour. "
                                  "Customer demand is measured throughout; nothing after a decision date reached the optimizer."),
                         "open_orders": prov.get("open_po"), "actual_conformance": r.get("actual_conformance")}
    att = r.get("attestation") or {}
    out["lookahead"] = {"clean": all(v.get("all_clean") for v in att.values()) if att else None,
                        "snapshots": sum(v.get("snapshots", 0) for v in att.values()),
                        "text": "Every planning snapshot was checked: demand history ends before the decision date, no receipt is observed after it, no open order was placed after it, and every dated row is known at or before it."
                                + (" All checks passed." if att and all(v.get("all_clean") for v in att.values()) else " A check failed; see the appendix.")}
    out["confidence"] = {"level": conf.get("level"), "reasons": conf.get("reasons") or [], "dimensions": conf.get("dimensions") or {}, "rule": conf.get("rule")}
    perf = r.get("performance") or {}
    out["performance"] = perf
    out["engine"] = r.get("engine")
    eng = r.get("engine") or {}
    certs = eng.get("certificates") or {}
    out["engine_text"] = (f"Formulation: {eng.get('formulation_note') or 'the released formulation'}."
                          + (f" Tie certificates: {num(certs.get('certified'))} of {num(certs.get('attempted'))} attempted solves certified, {num(certs.get('fallbacks'))} solved on the released formulation instead; "
                             f"certificate time {num(certs.get('certificate_seconds'))} s." if certs else ""))
    out["decisions"] = decs
    out["limits"] = [
        "Prices, the product set, calendars and economics are frozen at the first decision date (assumed constant over the window).",
        "Supplier capacity and lead times enter as the request declares them at each date; a supplier's response to an order it never received is inferred or simulated and labelled.",
        "The replay plans the main location's stock, like the production purchase plan; branch stock is not netted." if (scope.get("inventory_locations") or 1) > 1 else "Single-location workspace: the whole stock count is the opening state.",
        "Per-product economics are not attributed: the ledger is settled for the replayed products together; per-product service and stock are.",
    ]
    return out


def replay_headline(rep: dict) -> str:
    if not rep.get("available"):
        return "ZAAD's own decision replay is not available on this history (see the replay section)"
    return rep.get("statement", "")


# ── computed intersections ───────────────────────────────────────────────────
def synthesis_findings(summary: dict, lanes: list[dict]) -> list[dict]:
    """Management-level findings computed from the joins of product, supplier and lane evidence. Each carries
    the computed share of demand value; nothing is emitted for an empty intersection."""
    sku = summary.get("sku_profile") or {}
    sup = summary.get("supplier_profile") or {}
    inc = (summary.get("incumbent_detail") or {}).get("cover_weeks") or {}
    exposure = summary.get("lane_exposure") or {}
    elevated = {ln["lane"] for ln in lanes if ln.get("attention") == "ELEVATED"}
    out: list[dict] = []
    if not sku or not sup:
        return out

    def deteriorated(sid: str) -> bool:
        sp = sup.get(sid) or {}
        fs, lr = _f(sp.get("fill_shift")), _f(sp.get("lead_ratio"))
        return (fs is not None and fs < -0.06) or (lr is not None and lr > 1.3)

    def lead_weeks(sid: str) -> float | None:
        sp = sup.get(sid) or {}
        return _f(sp.get("lead_mean_weeks")) or _f(sp.get("lead_weeks_assumed"))

    below_lead = []
    for k, v in sku.items():
        sid = str(v.get("supplier"))
        lw, cov = lead_weeks(sid), _f(inc.get(k))
        if lw is not None and cov is not None and cov < lw:
            below_lead.append(k)
    share = lambda ks: sum((_f(sku[k].get("value_share")) or 0.0) for k in ks)  # noqa: E731

    a = [k for k in below_lead if deteriorated(str(sku[k].get("supplier")))]
    if a:
        out.append({"id": "synth-cover-below-lead-and-deterioration", "category": "synthesis", "severity": "high" if share(a) >= 0.15 else "medium",
                    "headline": f"{pct(share(a), nd=0)} of demand value sits in products ordered to less cover than their lead time whose supplier has recently deteriorated",
                    "observation": f"{num(len(a))} product(s) are ordered to a cover below their supplier's lead time, and that supplier's fill has fallen or its lead time has lengthened recently.",
                    "business_implication": "These are the products where a shortage is most likely next: the cover cannot absorb a late or short receipt, and the supplier is currently delivering late or short.",
                    "possible_driver": "A cover rule tuned to the supplier's historical lead time meeting a supplier that no longer keeps it", "driver_tag": "LIKELY DRIVER",
                    "recommendation": "Review the protection on these products first; plan their next orders to the recent lead time.",
                    "confidence": "Moderate", "confidence_basis": "cover inferred from order quantities; supplier drift measured from receipts", "materiality": share(a),
                    "evidence": [{"label": "Products", "value": ", ".join(sorted(a)[:6]) + (" …" if len(a) > 6 else "")}, {"label": "Share of demand value", "value": pct(share(a))}],
                    "related": [{"kind": "sku", "id": k, "label": k} for k in sorted(a, key=lambda k: -(_f(sku[k].get("value_share")) or 0))[:5]], "summary_line": None})
        b = [k for k in a if str((sup.get(str(sku[k].get("supplier"))) or {}).get("lane") or "").lower() in elevated]
        if b:
            out.append({"id": "synth-cover-below-lead-deterioration-lane", "category": "synthesis", "severity": "high",
                        "headline": f"{pct(share(b), nd=0)} of demand value combines thin cover, a deteriorating supplier and an elevated lane",
                        "observation": f"{num(len(b))} of those product(s) are also supplied through a lane currently at elevated attention.",
                        "business_implication": "Three independent risks stack on the same products; a lane delay would land on stock that is already thin and a supplier already short.",
                        "possible_driver": None, "driver_tag": "OBSERVED", "recommendation": "Bring the next commitment on these products forward rather than larger, and confirm the supplier's shipping dates.",
                        "confidence": "Moderate", "confidence_basis": "lane score from public indicators; the rest from your records", "materiality": share(b),
                        "evidence": [{"label": "Products", "value": ", ".join(sorted(b)[:6])}, {"label": "Share of demand value", "value": pct(share(b))}],
                        "related": [{"kind": "sku", "id": k, "label": k} for k in sorted(b)[:5]] + [{"kind": "po", "id": "open", "label": "Purchase orders"}], "summary_line": None})
    inter = [k for k, v in sku.items() if (_f(v.get("zero_share")) or 0) >= 0.35 and ((_f((sup.get(str(v.get("supplier"))) or {}).get("fill_mean")) or 1.0) < 0.9 or deteriorated(str(v.get("supplier"))))]
    if inter:
        out.append({"id": "synth-intermittent-unreliable", "category": "synthesis", "severity": "medium",
                    "headline": f"{num(len(inter))} intermittent-demand product(s) depend on a supplier that fills short or late",
                    "observation": "Demand for these products is zero in at least 35% of weeks, and their supplier's fill is below 90% or has recently deteriorated.",
                    "business_implication": "Lumpy demand plus unreliable supply is the combination that produces both dead stock and missed orders on the same product.",
                    "possible_driver": None, "driver_tag": "OBSERVED", "recommendation": "Decide a deliberate stocking rule for each (make-to-order, a fixed minimum, or a second source).",
                    "confidence": "Moderate", "confidence_basis": "demand history and receipts", "materiality": share(inter),
                    "evidence": [{"label": "Products", "value": ", ".join(sorted(inter)[:6])}, {"label": "Share of demand value", "value": pct(share(inter))}],
                    "related": [{"kind": "sku", "id": k, "label": k} for k in sorted(inter)[:5]], "summary_line": None})
    for lane in sorted(elevated):
        ex = exposure.get(lane) or {}
        o = ex.get("open_po_estimate") or {}
        if (o.get("lines") or 0) > 0:
            out.append({"id": f"synth-open-po-lane-{lane}", "category": "synthesis", "severity": "medium",
                        "headline": f"{num(o.get('lines'))} open purchase-order line(s) ride on {lane.replace('_', ' ').title()}, a lane at elevated attention",
                        "observation": f"{num(o.get('units'))} units across {num(o.get('skus'))} product(s) have no receipt yet on this lane ({o.get('basis')}).",
                        "business_implication": "If the lane slips, these are the receipts that slip with it.",
                        "possible_driver": None, "driver_tag": "OBSERVED", "recommendation": "Confirm shipping status on these orders and check cover on their products.",
                        "confidence": "Moderate", "confidence_basis": "open orders estimated from purchase orders without a matching receipt", "materiality": _f(ex.get("value_share")),
                        "evidence": [{"label": "Lines", "value": num(o.get("lines"))}, {"label": "Units", "value": num(o.get("units"))}],
                        "related": [{"kind": "po", "id": "open", "label": "Purchase orders"}], "summary_line": None})
    for sid, sp in sup.items():
        vs = _f(sp.get("value_share")) or 0.0
        if vs >= 0.35 and deteriorated(sid):
            out.append({"id": f"synth-concentration-decline-{sid}", "category": "synthesis", "severity": "high",
                        "headline": f"{sid} carries {pct(vs, nd=0)} of your demand value and has recently deteriorated",
                        "observation": f"Recent fill {pct(_f(sp.get('fill_recent')), nd=0)} against long-run {pct(_f(sp.get('fill_mean')), nd=0)}; lead time {sp.get('lead_ratio')}× its long-run mean.",
                        "business_implication": "Concentration and deterioration together: most of your business is exposed to one supplier at the moment its reliability fell.",
                        "possible_driver": None, "driver_tag": "OBSERVED", "recommendation": "Know which of its products have a second source; agree confirmed quantities and dates for the next orders.",
                        "confidence": "High" if (sp.get("n_receipts") or 0) >= 8 else "Moderate", "confidence_basis": f"{num(sp.get('n_receipts'))} receipts", "materiality": vs,
                        "evidence": [{"label": "Share of demand value", "value": pct(vs)}, {"label": "Products supplied", "value": num(sp.get("n_skus"))}],
                        "related": [{"kind": "supplier", "id": sid, "label": sid}], "summary_line": None})
    return out
