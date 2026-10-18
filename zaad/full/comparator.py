"""Comparator provenance and claim gating (HARDENING V1, H3a).

ZAAD may recommend a decision without a real comparator. It may NOT say "better than current", "savings",
"what you would have done" or "your current plan" unless the evidence establishes the comparator that
statement needs. Two things that look alike are kept apart:

    DECISION REFERENCE   what the optimizer uses internally to decide whether to move (its incumbent: a
                         reconstructed rule, an operator-declared rule or order set, or a system proxy)
    EVIDENCE COMPARATOR  what ZAAD may compare itself against in front of the operator

A reconstructed reorder-point rule is a perfectly good decision reference. It is not "the buyer's plan".

COMPARATOR TYPES
    ACTUAL_HISTORICAL_ACTION   an action actually observed in the operator's records (a PO really placed),
                               with enough identity to establish it: sku, supplier, destination where
                               material, timing, quantity. An altered copy is not one.
    ACTUAL_OPERATOR_PLAN       a prospective operator plan captured independently BEFORE ZAAD's
                               recommendation or execution. RESERVED FOR H3b: nothing in this module
                               fabricates one from history, a rule, a baseline or a ZAAD proposal.
    RECONSTRUCTED_POLICY       a rule inferred from history or projected from a declared rule; a decision
                               reference and engineering baseline, never "your current policy".
    SYSTEM_BASELINE            a generic engineering benchmark (base-stock proxy, reorder point, ...).
    NONE                       no evidence comparator.

FIDELITY
    EXACT          observed and preserved without any decision-changing transformation
    DECLARED       supplied explicitly by the operator, but not an observed executed action
    RECONSTRUCTED  inferred from history
    TRANSFORMED    began from an observed action but a material field was changed before evaluation
    INCOMPLETE     a material identity / action dimension is missing (e.g. the source could not be mapped)
    NOT_AVAILABLE

MODES, CLAIM CLASSES, READINESS: see the constants below. The permissions a comparison grants are explicit
booleans; nothing downstream infers them from copy. Realized value stays with the Operating Product V2
outcome contract (`api.routers.zaad_history.realized_value`) and is not broadened here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

# ── vocabulary ───────────────────────────────────────────────────────────────
ACTUAL_HISTORICAL_ACTION = "ACTUAL_HISTORICAL_ACTION"
ACTUAL_OPERATOR_PLAN = "ACTUAL_OPERATOR_PLAN"                   # reserved for H3b
RECONSTRUCTED_POLICY = "RECONSTRUCTED_POLICY"
SYSTEM_BASELINE = "SYSTEM_BASELINE"
INCUMBENT_ORDER_SET = "INCUMBENT_ORDER_SET"                     # dated incumbent orders in a Request whose origin is not established
NONE = "NONE"
COMPARATOR_TYPES = (ACTUAL_HISTORICAL_ACTION, ACTUAL_OPERATOR_PLAN, RECONSTRUCTED_POLICY, SYSTEM_BASELINE, INCUMBENT_ORDER_SET, NONE)
ORIGIN_NOT_ESTABLISHED = "ORIGIN_NOT_ESTABLISHED"

EXACT, DECLARED, RECONSTRUCTED, TRANSFORMED, INCOMPLETE, NOT_AVAILABLE = "EXACT", "DECLARED", "RECONSTRUCTED", "TRANSFORMED", "INCOMPLETE", "NOT_AVAILABLE"
FIDELITIES = (EXACT, DECLARED, RECONSTRUCTED, TRANSFORMED, INCOMPLETE, NOT_AVAILABLE)
NO_IDENTIFIED_ACTION = "NO_IDENTIFIED_ACTION"                   # a decision row with no recorded action of its SKU in the period: not a fidelity, an absence

PLAN_MODE, HISTORICAL_COMPARISON_MODE, SHADOW_COMPARISON_MODE = "PLAN_MODE", "HISTORICAL_COMPARISON_MODE", "SHADOW_COMPARISON_MODE"

PLAN_ONLY = "PLAN_ONLY"
MODEL_COMPARISON = "MODEL_COMPARISON"
HISTORICAL_COUNTERFACTUAL_COMPARISON = "HISTORICAL_COUNTERFACTUAL_COMPARISON"
SHADOW_COMPARISON = "SHADOW_COMPARISON"                         # reserved for H3b
REALIZED_VALUE = "REALIZED_VALUE"                               # Operating Product V2 outcome contract only
CLAIM_CLASSES = (PLAN_ONLY, MODEL_COMPARISON, HISTORICAL_COUNTERFACTUAL_COMPARISON, SHADOW_COMPARISON, REALIZED_VALUE)

READY, CONDITIONAL, NOT_READY_FOR_THIS_DECISION, CANNOT_COMPARE = "READY", "CONDITIONAL", "NOT_READY_FOR_THIS_DECISION", "CANNOT_COMPARE"

OPERATOR_PLAN_PROVENANCES = ("OPERATOR_SUBMITTED", "OPERATOR_UPLOADED", "OPERATOR_CONFIRMED_DRAFT")   # H3b capture origins
PERMISSION_KEYS = ("can_recommend", "can_compare", "can_claim_against_operator", "can_claim_historical_counterfactual_difference",
                   "can_claim_shadow_difference", "can_claim_realized_value")

# wording the contract allows for each decision-reference / comparator kind
LABELS = {
    "rule_inferred": "the reconstructed historical rule",
    "rule_declared": "the operator-declared rule",
    "orders_unestablished": "the incumbent order set in the request (origin not established; not a captured operator plan)",
    "orders_declared": "the operator-declared incumbent orders (a declared order set, not a captured operator plan)",
    "system_proxy": "the system base-stock baseline",
    "action_exact": "the recorded historical orders",
    "action_transformed": "a model-adjusted version of the recorded historical orders",
    "action_incomplete": "the recorded historical orders that could be identified (some lines could not be mapped to a source)",
    "zaad": "ZAAD's counterfactual decisions",
    "operator_plan_exact": "your captured purchasing plan",
    "operator_plan_incomplete": "your captured purchasing plan (some lines could not be identified to a source)",
    "operator_plan_transformed": "a model-adjusted version of your captured purchasing plan",
}


def _permissions(**on: bool) -> dict[str, bool]:
    return {k: bool(on.get(k, False)) for k in PERMISSION_KEYS}


# ── decision reference (what the planner compares against internally) ───────
def rule_fidelity(rule_provenance: str | None) -> str:
    """The fidelity of an incumbent rule from the workspace build's `incumbent_rule.provenance`."""
    if rule_provenance == "CUSTOMER_PROVIDED":
        return DECLARED
    return RECONSTRUCTED


def policy_label(rule_provenance: str | None) -> str:
    """How a rule may be named: declared by the operator, or reconstructed. Never 'your current policy'."""
    return LABELS["rule_declared"] if rule_provenance == "CUSTOMER_PROVIDED" else LABELS["rule_inferred"]


def decision_reference(req: Any, *, rule_provenance: str | None = None, incumbent_orders_source: str | None = None) -> dict[str, Any]:
    """The planner's incumbent, described by what it is. `rule_provenance` is the workspace build's
    `incumbent_rule.provenance` when the caller has the build; the Request itself does not carry it.

    A bare `Request.incumbent_orders` collection proves nothing about who wrote it: the replay engine
    builds incumbent orders from a rule and carries schedules forward, so without `incumbent_orders_source`
    (a defensible, independently established origin the caller supplies; H3b's plan capture will be one)
    the set has ORIGIN_NOT_ESTABLISHED and NOT_AVAILABLE fidelity. The legacy engine field
    `evidence_label = OPERATOR-SHADOW` is not such a source."""
    if getattr(req, "incumbent_orders", ()):
        if incumbent_orders_source:
            return {"type": INCUMBENT_ORDER_SET, "kind": "DECLARED_INCUMBENT_ORDERS", "fidelity": DECLARED, "provenance": incumbent_orders_source,
                    "label": LABELS["orders_declared"],
                    "description": "a dated set of incumbent orders with an operator-declared origin; still not a plan captured prospectively, so not an ACTUAL_OPERATOR_PLAN"}
        return {"type": INCUMBENT_ORDER_SET, "kind": "INCUMBENT_ORDER_SET", "fidelity": NOT_AVAILABLE, "provenance": ORIGIN_NOT_ESTABLISHED,
                "label": LABELS["orders_unestablished"],
                "description": "a dated set of incumbent orders carried in the request; the planner is compared against it, but nothing establishes "
                               "whether an operator wrote it or the engine projected it, so no operator provenance is attached"}
    rule = getattr(req, "incumbent_rule", None)
    if rule:
        fidelity = rule_fidelity(rule_provenance)
        known = rule_provenance is not None
        return {"type": RECONSTRUCTED_POLICY, "kind": "INCUMBENT_RULE", "rule": rule, "fidelity": fidelity,
                "provenance": rule_provenance if known else "RULE_IN_REQUEST",
                "provenance_note": None if known else ("the Request carries the rule, not its origin; the workspace build report records "
                                                        "whether it was inferred from history or declared (incumbent_rule.provenance). "
                                                        "Until that says CUSTOMER_PROVIDED the rule is treated as reconstructed"),
                "label": policy_label(rule_provenance),
                "description": f"the projection of the {'operator-declared' if fidelity == DECLARED else 'reconstructed'} rule `{rule}` from this snapshot"}
    return {"type": SYSTEM_BASELINE, "kind": "PROJECTED_BASE_STOCK_PROXY", "fidelity": NOT_AVAILABLE, "provenance": "planner",
            "label": LABELS["system_proxy"], "description": "the planner's own projected base-stock proxy; an engineering benchmark, not operator behaviour"}


# ── PLAN_MODE: a live recommendation with no captured operator plan ──────────
def plan_comparison(req: Any, *, status: str | None, selected_policy: str | None, rule_provenance: str | None = None,
                    actual_operator_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """The comparison contract of a live plan. Without an ACTUAL_OPERATOR_PLAN the mode is PLAN_MODE: a
    recommendation and, where a decision reference exists, a MODEL_COMPARISON against it; never a claim
    against the operator. An absent comparator is not a planning failure. With captured operator-plan
    evidence (H3b, see `shadow_comparison`) the shadow contract is returned instead."""
    if actual_operator_plan is not None:
        return shadow_comparison(actual_operator_plan, status=status, selected_policy=selected_policy, rule_provenance=rule_provenance)
    ref = decision_reference(req, rule_provenance=rule_provenance)
    usable = status not in (None, "ABSTAIN")
    retained = status == "RETAIN_INCUMBENT"
    comparator = {"type": ref["type"], "fidelity": ref["fidelity"], "provenance": ref["provenance"], "label": ref["label"],
                  "observed": False, "transformed": False}
    if not usable:
        permissions = _permissions(can_recommend=False, can_compare=False)
        readiness, claim = CANNOT_COMPARE, PLAN_ONLY
        comparator = {"type": NONE, "fidelity": NOT_AVAILABLE, "provenance": None, "label": None, "observed": False, "transformed": False}
    else:
        permissions = _permissions(can_recommend=True, can_compare=True)
        readiness, claim = READY, MODEL_COMPARISON
    caveats = ["no operator plan was captured for this decision: the comparison is against the planner's decision reference under the shared model",
               "modelled differences against a reconstructed or declared rule are not a benefit realized by the operator"]
    if ref.get("provenance_note"):
        caveats.append(ref["provenance_note"])
    meaning = ("ZAAD retained its decision reference" if retained else "ZAAD recommends a change from its decision reference" if status == "PENDING_REVIEW"
               else "the planner abstained: no usable decision reference" if status == "ABSTAIN" else f"planner status {status}")
    return {"mode": PLAN_MODE, "readiness": readiness, "comparator": comparator, "decision_reference": ref, "claim_class": claim,
            "permissions": permissions, "coverage": None, "caveats": caveats, "meaning": meaning,
            "planner_status": status, "selected_policy": selected_policy,
            "shadow": shadow_readiness(None),
            "claims_not_permitted": ["a reduction versus your current plan", "better than what you would have done", "an improvement versus your actual plan",
                                     "you would have spent X", "a benefit versus your current policy"]}


def shadow_readiness(evidence: dict[str, Any] | None) -> dict[str, Any]:
    """Whether a captured operator plan may serve as the ACTUAL_OPERATOR_PLAN of one decision (H3b).

    `evidence` is `api.product.operator_plans.shadow_evidence(...)`: the plan's provenance, versions, hash
    integrity, capture and exposure instants, planning origin and line identity coverage. The plan is never
    inferred from a reconstructed rule, historical POs, the incumbent projection, a ZAAD recommendation, a
    system baseline or a proposal made from ZAAD output: only a declared provenance in PROVENANCES counts.

    READY        captured before ZAAD's recommendation was exposed, latest version, hash verified, same
                 origin, every line identified exactly
    CONDITIONAL  as READY but some lines could not be identified to a source (no exact claim) or the
                 captured version was later superseded (the comparison stands for the version it used)
    NOT_READY_FOR_THIS_DECISION  no plan, captured at or after exposure, a different planning origin, an
                 unestablished provenance, or a snapshot whose hash no longer matches"""
    if evidence is None:
        return {"mode": SHADOW_COMPARISON_MODE, "readiness": NOT_READY_FOR_THIS_DECISION, "claim_class": None, "fidelity": NOT_AVAILABLE,
                "requires": ACTUAL_OPERATOR_PLAN, "permissions": _permissions(can_recommend=True),
                "reasons": ["no ACTUAL_OPERATOR_PLAN was captured for this decision"]}
    reasons: list[str] = []
    blockers: list[str] = []
    if evidence.get("provenance") not in OPERATOR_PLAN_PROVENANCES:
        blockers.append(f"provenance {evidence.get('provenance')!r} is not an independently established operator origin")
    if evidence.get("integrity") not in (None, "VERIFIED"):
        blockers.append("the stored snapshot does not hash to its recorded content hash")
    if not evidence.get("same_origin", False):
        blockers.append("the plan was captured for a different planning origin than this decision")
    captured, exposed = evidence.get("captured_at"), evidence.get("exposed_at")
    if captured is not None and exposed is not None and not (captured < exposed):
        blockers.append("the plan was captured at or after ZAAD's recommendation was exposed; it cannot be the independent baseline of that decision")
    if evidence.get("line_count", 0) == 0:
        blockers.append("the plan has no lines")
    identity = evidence.get("identity_fidelity")
    if evidence.get("version") != evidence.get("latest_version"):
        reasons.append(f"a later version (v{evidence.get('latest_version')}) supersedes the one compared (v{evidence.get('version')}); the comparison stands for v{evidence.get('version')}")
    if identity == INCOMPLETE:
        cov = evidence.get("coverage") or {}
        reasons.append(f"{cov.get('lines_incomplete')} of {cov.get('lines_observed')} plan lines could not be identified to one request source; "
                       "those lines are not evaluated and no exact claim is made")
    if blockers:
        readiness, fidelity = NOT_READY_FOR_THIS_DECISION, NOT_AVAILABLE
    elif reasons:
        readiness, fidelity = CONDITIONAL, (INCOMPLETE if identity == INCOMPLETE else EXACT)
    else:
        readiness, fidelity = READY, EXACT
    return {"mode": SHADOW_COMPARISON_MODE, "readiness": readiness, "fidelity": fidelity, "requires": ACTUAL_OPERATOR_PLAN,
            "claim_class": SHADOW_COMPARISON if readiness != NOT_READY_FOR_THIS_DECISION else None,
            "permissions": _permissions(can_recommend=True, can_compare=readiness != NOT_READY_FOR_THIS_DECISION,
                                        can_claim_shadow_difference=readiness == READY),
            "reasons": blockers + reasons}



def shadow_comparison(evidence: dict[str, Any], *, status: str | None = None, selected_policy: str | None = None,
                      rule_provenance: str | None = None, transformed: bool = False) -> dict[str, Any]:
    """The comparison contract of a shadow comparison: ZAAD's recommendation against a captured operator plan.
    The difference is modelled on simulated worlds; it is never realized value. `transformed` says whether
    the plan the settlement scored differs from the recorded plan (a line dropped as unidentified counts as a
    transformation of the whole-plan comparison, recorded through readiness as INCOMPLETE)."""
    ready = shadow_readiness(evidence)
    fidelity = ready["fidelity"]
    if fidelity == EXACT and transformed:
        fidelity = TRANSFORMED
        ready = {**ready, "fidelity": TRANSFORMED, "readiness": CONDITIONAL if ready["readiness"] == READY else ready["readiness"],
                 "permissions": {**ready["permissions"], "can_claim_shadow_difference": False},
                 "reasons": ready["reasons"] + ["the settlement could not score the plan exactly as recorded (quantities were adjusted); no exact claim is made"]}
    label = {EXACT: LABELS["operator_plan_exact"], INCOMPLETE: LABELS["operator_plan_incomplete"], TRANSFORMED: LABELS["operator_plan_transformed"]}.get(fidelity)
    comparator = {"type": ACTUAL_OPERATOR_PLAN if ready["readiness"] != NOT_READY_FOR_THIS_DECISION else NONE, "fidelity": fidelity,
                  "provenance": evidence.get("provenance"), "plan_id": evidence.get("plan_id"), "version": evidence.get("version"),
                  "content_hash": evidence.get("content_hash"), "label": label, "observed": False, "transformed": fidelity == TRANSFORMED}
    caveats = ["shadow comparison: both plans are settled on simulated scenario worlds under the same assumptions; the difference is modelled, not a realized outcome",
               "no realized value is claimed; realized value needs observed outcomes under the Operating Product V2 outcome contract"] + list(ready["reasons"])
    return {"mode": SHADOW_COMPARISON_MODE, "readiness": ready["readiness"], "comparator": comparator,
            "decision_reference": {"type": RECONSTRUCTED_POLICY, "fidelity": rule_fidelity(rule_provenance), "provenance": rule_provenance, "label": policy_label(rule_provenance),
                                   "note": "ZAAD's own decision reference, unchanged by the shadow comparison; the recommendation was produced without the operator plan"},
            "claim_class": ready["claim_class"] or PLAN_ONLY, "permissions": ready["permissions"], "coverage": evidence.get("coverage"),
            "caveats": caveats, "planner_status": status, "selected_policy": selected_policy,
            "claims_not_permitted": ["a realized benefit", "would have spent", "operator savings"]}


# ── historical actions: observed records mapped to request sources ───────────
def _text(value: Any) -> str:
    return "" if value is None or (isinstance(value, float) and value != value) else str(value).strip()


@dataclass
class ActionLine:
    po_id: str
    po_date: Any
    sku: str
    supplier: str | None
    destination: str | None
    quantity: float
    unit_cost: float | None
    period: int
    source: str | None = None
    fidelity: str = INCOMPLETE
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"po_id": self.po_id, "po_date": str(self.po_date)[:10], "sku": self.sku, "supplier": self.supplier, "destination": self.destination,
                "quantity": self.quantity, "unit_cost": self.unit_cost, "period": self.period, "source": self.source, "fidelity": self.fidelity, "reason": self.reason}


@dataclass
class HistoricalActions:
    lines: list[ActionLine] = field(default_factory=list)
    by_review: dict[int, dict[str, float]] = field(default_factory=dict)
    out_of_scope: int = 0          # recorded lines for SKUs the request does not plan: not comparator lines, counted for the record

    def coverage(self, reviews: int | None = None) -> dict[str, Any]:
        lines = [ln for ln in self.lines if reviews is None or 0 <= ln.period < reviews]
        exact = [ln for ln in lines if ln.fidelity == EXACT]
        incomplete = [ln for ln in lines if ln.fidelity == INCOMPLETE]
        qty = sum(ln.quantity for ln in lines)
        value_lines = [ln for ln in lines if ln.unit_cost is not None]
        value = sum(ln.quantity * ln.unit_cost for ln in value_lines if ln.unit_cost is not None)
        exact_value = sum(ln.quantity * ln.unit_cost for ln in exact if ln.unit_cost is not None)
        return {"lines_observed": len(lines), "lines_exact": len(exact), "lines_incomplete": len(incomplete),
                "lines_unmapped": sum(1 for ln in incomplete if ln.source is None),
                "exact_quantity_share": (sum(ln.quantity for ln in exact) / qty) if qty > 0 else None,
                "exact_value_share": (exact_value / value) if value > 0 and len(value_lines) == len(lines) else None,
                "value_share_basis": "recorded unit cost on every line" if lines and len(value_lines) == len(lines) else "unit cost missing on some lines: no value share",
                "incomplete_reasons": sorted({ln.reason for ln in incomplete if ln.reason}),
                "lines_out_of_scope": self.out_of_scope,
                "scope_note": "lines for SKUs outside the replay scope are not comparator lines; the comparison covers the planned SKUs only"}


def map_historical_actions(pos: pd.DataFrame, sources: list[Any], *, origin: pd.Timestamp, period_days: int, reviews: int,
                           network: bool = False) -> HistoricalActions:
    """Map observed purchase-order lines to request sources by exact business key: (sku, supplier) and, in a
    network request, destination. Never by cheapest, primary, first or physical row order. A line whose
    supplier is missing, or whose (sku, supplier[, destination]) matches no source or several, is INCOMPLETE;
    if its SKU has exactly one source it is still evaluated through that source (the quantity is the
    operator's), but it cannot support an exact actual-action claim."""
    by_key: dict[tuple[str, str, str | None], list[Any]] = {}
    by_sku: dict[str, list[Any]] = {}
    for s in sources:
        by_sku.setdefault(str(s.sku), []).append(s)
        key = (str(s.sku), _text(s.supplier).upper(), _text(getattr(s, "destination", None)).upper() if network else None)
        by_key.setdefault(key, []).append(s)
    out = HistoricalActions(by_review={t: {} for t in range(reviews)})
    if not len(pos):
        return out
    frame = pos.copy()
    frame["po_date"] = pd.to_datetime(frame["po_date"])
    frame["period"] = ((frame["po_date"] - origin).dt.days // period_days).astype(int)
    frame = frame.assign(_po_key=frame["po_id"].astype(str)).sort_values(["po_date", "_po_key"], kind="stable")      # H1c: a canonical order, not row order
    for row in frame.itertuples():
        sku, supplier = _text(row.sku), _text(getattr(row, "supplier_id", None))
        destination = _text(getattr(row, "destination_id", None))
        quantity = float(row.qty_ordered or 0.)
        unit_cost = getattr(row, "unit_cost", None)
        unit_cost = None if unit_cost is None or pd.isna(unit_cost) else float(unit_cost)
        line = ActionLine(po_id=str(row.po_id), po_date=row.po_date, sku=sku, supplier=supplier or None, destination=destination or None,
                          quantity=quantity, unit_cost=unit_cost, period=int(row.period))
        candidates = by_sku.get(sku, [])
        if not candidates:
            out.out_of_scope += 1                   # the SKU is not in the request: outside the comparison scope, not an incomplete comparator
            continue
        if not supplier:
            line.reason = "the record carries no supplier identity"
            line.source = candidates[0].id if len(candidates) == 1 else None
            if len(candidates) > 1:
                line.reason += f"; the SKU has {len(candidates)} sources and none can be chosen"
        else:
            key = (sku, supplier.upper(), destination.upper() if (network and destination) else (None if not network else None))
            matches = by_key.get(key, [])
            if network and not destination:
                matches = [s for s in candidates if _text(s.supplier).upper() == supplier.upper()]
                if len(matches) > 1:
                    line.reason = "the record carries no destination and the supplier delivers to several locations"
                    matches = []
            if len(matches) == 1:
                line.source, line.fidelity = matches[0].id, EXACT
            elif len(matches) > 1:
                line.reason = f"{len(matches)} sources share the business key ({sku}, {supplier})"
            else:
                line.reason = line.reason or f"no source of {sku} is supplied by {supplier} (the request sources it from {', '.join(sorted({_text(s.supplier) for s in candidates}))})"
                line.source = None
        if quantity > 0 and line.source is not None and 0 <= line.period < reviews:
            out.by_review[line.period][line.source] = out.by_review[line.period].get(line.source, 0.) + quantity
        out.lines.append(line)
    return out


# ── historical comparison contract ───────────────────────────────────────────
def historical_comparison(coverage: dict[str, Any], *, transformed_groups: int, settlement_shares: dict[str, Any] | None,
                          rule_provenance: str | None, reviews_completed: int) -> dict[str, Any]:
    """What a historical replay may claim. The operator's action is observed; ZAAD's alternate history is
    counterfactual and settles on measured / inferred / simulated / assumed supplier behaviour. An exact
    claim needs EVERY action line in the reported scope mapped exactly and left untransformed.

    `transformed_groups` counts source-review action groups (one source's recorded orders in one review
    period, settled together) that the conformance step changed. The settlement works on those groups, so
    no line-level count of transformed POs exists and none is invented; one changed group is enough to
    deny the exact whole-scope claim."""
    observed = int(coverage.get("lines_observed") or 0)
    incomplete = int(coverage.get("lines_incomplete") or 0)
    if observed == 0:
        fidelity, label = NOT_AVAILABLE, None
    elif incomplete:
        fidelity, label = INCOMPLETE, LABELS["action_incomplete"]
    elif transformed_groups:
        fidelity, label = TRANSFORMED, LABELS["action_transformed"]
    else:
        fidelity, label = EXACT, LABELS["action_exact"]
    exact_ok = fidelity == EXACT and reviews_completed > 0
    comparator = {"type": ACTUAL_HISTORICAL_ACTION if observed else NONE, "fidelity": fidelity, "provenance": "stg_fmcg_purchase_orders (recorded purchase orders)",
                  "label": label, "observed": observed > 0, "transformed": transformed_groups > 0}
    if exact_ok:
        readiness, claim = READY, HISTORICAL_COUNTERFACTUAL_COMPARISON
        permissions = _permissions(can_recommend=True, can_compare=True, can_claim_historical_counterfactual_difference=True)
    elif observed:
        readiness, claim = CONDITIONAL, MODEL_COMPARISON
        permissions = _permissions(can_recommend=True, can_compare=True)
    else:
        readiness, claim = CANNOT_COMPARE, PLAN_ONLY
        permissions = _permissions(can_recommend=True)
    caveats = ["historical counterfactual comparison: the operator's action is observed, ZAAD's alternate history is not; nothing here is realized value",
               "ZAAD's leg settles on measured, inferred, simulated or assumed supplier behaviour (see settlement_provenance)"]
    if fidelity == TRANSFORMED:
        caveats.append(f"{transformed_groups} source-review action group(s) (one source's recorded orders in one review period) were rounded, capped or dropped "
                       "to fit the declared physical envelope before settlement; the scored path is a model-adjusted version of the recorded orders, so no claim is made against the operator")
    if fidelity == INCOMPLETE:
        caveats.append(f"{incomplete} of {observed} recorded line(s) could not be mapped exactly to a request source ({'; '.join(coverage.get('incomplete_reasons') or [])}); "
                       "the comparator does not cover the operator's actions exactly")
    return {"mode": HISTORICAL_COMPARISON_MODE, "readiness": readiness, "comparator": comparator,
            "decision_reference": {"type": RECONSTRUCTED_POLICY, "fidelity": rule_fidelity(rule_provenance), "provenance": rule_provenance, "label": policy_label(rule_provenance)},
            "claim_class": claim, "permissions": permissions,
            "coverage": {**coverage, "transformed_action_groups": transformed_groups,
                         "transformation_unit": "source-review action groups (one source's recorded orders in one review period, settled together); PO-line attribution is not available"},
            "caveats": caveats, "settlement_basis": settlement_shares,
            "legs": {"actual": {"comparator_type": comparator["type"], "fidelity": fidelity, "label": label},
                     "rule": {"comparator_type": RECONSTRUCTED_POLICY, "fidelity": rule_fidelity(rule_provenance), "provenance": rule_provenance, "label": policy_label(rule_provenance)},
                     "zaad": {"type": "COUNTERFACTUAL_DECISION", "label": LABELS["zaad"]}},
            "claims_not_permitted": [c for c in ("a realized benefit", "would have spent", "calling the comparator the operator's own orders" if fidelity != EXACT else None) if c]}


def actual_action_label(comparison: dict[str, Any] | None) -> str:
    """The name the report may give the historical-action leg; absent metadata (an older replay) is treated
    as not exact, because exactness was never established."""
    fidelity = ((comparison or {}).get("comparator") or {}).get("fidelity")
    if fidelity == EXACT:
        return LABELS["action_exact"]
    if fidelity == INCOMPLETE:
        return LABELS["action_incomplete"]
    return LABELS["action_transformed"] if fidelity == TRANSFORMED else "the recorded historical orders as the replay evaluated them (comparator fidelity not established)"
