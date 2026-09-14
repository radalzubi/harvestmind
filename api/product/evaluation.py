"""Evaluating a proposed order: the workspace, plus the proposal, through the released engine.

The shape of the answer a buyer wants is three columns:

    YOUR CURRENT PLAN    |    WHAT ZAAD RECOMMENDS    |    YOUR PROPOSAL

and all three must come out of the same engine, over the same information set, or the comparison is
theatre. This module gets them like this:

  * **One baseline run** of the operator's workspace over the proposal's products. Its report
    carries both the incumbent projection (your current ordering policy, played forward) and the
    selected plan (what ZAAD recommends instead). That is columns one and two, from one run.
  * **One proposal run** of the *same* request with the proposal overlaid on the open-order
    pipeline — the order treated as if it had been placed. Its incumbent projection is column
    three: your current policy with this order in it.

Both runs go through `POST /api/zaad/network/jobs`, the released asynchronous path, because a solve
takes minutes. Both carry the same `as_of`, the same seed, the same scenario configuration and the
same products, so the difference between column one and column three is the proposal and nothing
else.

What this module does **not** do:

  * It does not compute an economic quantity. The comparison subtracts two numbers the engine
    itself reported under the same ledger key. Nothing is modelled here.
  * It does not price an amendment. A change to an existing order is worth what the contract says
    it is worth, and that lives in P4B — which prices only the options the operator has actually
    declared. An amendment with no declared right is reported as un-priceable, not estimated.
  * It does not touch the operator's uploaded data. The overlay exists for the length of one
    request object and is never written anywhere.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from zaad.full.contracts import Request

#: Products one evaluation covers. A solve is minutes long and grows fast with the product count;
#: a comparison nobody waits for is not a product feature. The number is always stated in the
#: answer, and a proposal that needs more products than this is refused rather than trimmed.
MAX_EVALUATION_SKUS = 25

#: The ledger lines shown side by side, in the order a buyer reads them.
LEDGER_ORDER = ("PURCHASE", "FREIGHT", "ORDERING", "RECEIVING", "CARRYING", "FINANCING",
                "SHORTAGE", "OTHER", "OPERATING_TOTAL", "INVENTORY_VALUE_CHANGE", "TOTAL")

LEDGER_LABEL = {
    "PURCHASE": "What you pay the supplier",
    "FREIGHT": "Getting it here",
    "ORDERING": "Placing the orders",
    "RECEIVING": "Receiving it",
    "CARRYING": "Holding the stock",
    "FINANCING": "The money tied up",
    "SHORTAGE": "Running short",
    "OTHER": "Everything else",
    "OPERATING_TOTAL": "Operating cost",
    "INVENTORY_VALUE_CHANGE": "Change in the value of stock held",
    "TOTAL": "Total modelled cost",
}


class EvaluationRefused(ValueError):
    """The proposal cannot be evaluated as it stands, with the reason a person should read."""


def evaluation_id() -> str:
    return f"eval_{uuid.uuid4().hex[:16]}"


def _source_for(request: Request, sku: str, supplier: str | None, destination: str | None) -> Any:
    """The approved source a proposal line would be bought through, or None."""
    candidates = [s for s in request.sources if s.sku == sku]
    if supplier:
        narrowed = [s for s in candidates if s.supplier == supplier]
        if narrowed:
            candidates = narrowed
        else:
            return None
    if destination:
        narrowed = [s for s in candidates if s.destination == destination]
        if narrowed:
            candidates = narrowed
    return candidates[0] if candidates else None


def overlay(request: Request, draft: dict[str, Any]) -> tuple[Request, list[str]]:
    """The workspace request with the proposal's lines added to the open-order pipeline.

    Treating a proposed order as an order already placed is the only honest way to ask what it
    does: it is what the operator is about to commit to. Every line is attached to an approved
    source the workspace already declares — a line ZAAD has no approved source for cannot be
    evaluated, and says so rather than inventing terms for it.
    """
    lines = list(draft.get("lines") or [])
    if not lines:
        raise EvaluationRefused("This proposal has no lines, so there is nothing to evaluate.")
    supplier = draft.get("supplier_id")
    destination = draft.get("destination_id")
    as_of = request.as_of
    known_at = as_of - timedelta(seconds=1)
    period_days = request.period_days
    notes: list[str] = []

    pipeline = [po.model_dump(mode="python") for po in request.pipeline]
    existing = {row["id"] for row in pipeline}
    for index, line in enumerate(lines, start=1):
        sku = str(line.get("sku"))
        source = _source_for(request, sku, str(supplier) if supplier else None,
                             str(destination) if destination else None)
        if source is None:
            raise EvaluationRefused(
                f"{sku} has no approved source from {supplier or 'any supplier'} in this workspace, so ZAAD "
                "cannot evaluate that line. Declare the source first (Data → Alternative sources), or change "
                "the supplier on this proposal.")
        quantity = float(line.get("quantity") or 0)
        if quantity <= 0:
            continue
        wanted = line.get("requested_receipt_date") or draft.get("requested_receipt_date")
        eta = _receipt_datetime(wanted, as_of) or (as_of + timedelta(days=int(source.lead_days)))
        if eta < as_of:
            eta = as_of
        due_in = max(0, int((eta - as_of).days // period_days))
        identity = f"proposal_{draft.get('draft_id', 'draft')}_{index}"
        if identity in existing:
            identity = f"{identity}_{uuid.uuid4().hex[:4]}"
        unit_price = line.get("unit_price")
        pipeline.append({
            "known_at": known_at, "id": identity, "source": source.id, "revision": 1,
            "ordered": quantity, "confirmed": 0., "shipped": 0., "received": 0., "rejected": 0.,
            "expected_accepted_remaining": quantity * float(source.fill_mean),
            "placed_at": as_of, "confirmed_at": None, "departed_at": None, "current_eta": eta,
            "stage": "placed", "carrier": "unknown", "cancellation_status": "none",
            "prepaid_per_remaining_unit": 0., "allow_split_amendments": False,
            "minimum_remaining_quantity": 0., "deposit_refundable_fraction": 0.,
            "options": [{
                "known_at": known_at, "id": f"keep_{identity}", "action": "keep", "due_in": due_in,
                "fee_per_unit": 0., "credit_per_unit": 0.,
                "remaining_invoice_per_unit": float(unit_price) if unit_price is not None else float(source.unit_price),
                "payment_due_in": due_in, "max_quantity": quantity,
                "deadline": as_of + timedelta(days=period_days * request.horizon),
                "allowed_stages": ["placed"], "contract_reference": str(draft.get("draft_id") or ""),
                "provenance": "OPERATOR_DECLARED",
            }],
        })
        if unit_price is None:
            notes.append(f"{sku}: no price is declared on this line, so the source's declared unit price "
                         f"({source.unit_price:,.2f}) was used.")

    payload = request.model_dump(mode="python")
    payload["pipeline"] = pipeline
    return Request.model_validate(payload), notes


def _receipt_datetime(value: Any, as_of: datetime) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value)[:19])
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def scope_for(draft: dict[str, Any], *, amendment_skus: set[str] | None = None) -> list[str]:
    """The products the two runs cover: the proposal's, and no others.

    Deliberately minimal. Every product in the scope multiplies the solve time, and the honest
    statement — "this comparison covered the products on this proposal" — is better than a larger
    scope nobody waits for. The limitation that follows from it is reported with the answer.
    """
    wanted = [str(line["sku"]) for line in (draft.get("lines") or []) if line.get("sku")]
    ordered = list(dict.fromkeys(wanted))
    extra = sorted((amendment_skus or set()) - set(ordered))
    if len(ordered) + len(extra) > MAX_EVALUATION_SKUS:
        if len(ordered) > MAX_EVALUATION_SKUS:
            raise EvaluationRefused(
                f"This proposal covers {len(ordered)} products. ZAAD evaluates up to {MAX_EVALUATION_SKUS} at a "
                "time, because each one adds solve time. Split it into smaller proposals to compare them.")
        return ordered
    return ordered + extra


# ── the comparison ────────────────────────────────────────────────────────────

def _costs(report: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not report:
        return {}
    economics = report.get("economics") or {}
    value = economics.get(key)
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and abs(out) != float("inf") else None


def compare(
    baseline: dict[str, Any] | None,
    proposal: dict[str, Any] | None,
    *,
    draft: dict[str, Any],
    scope: list[str],
    currency: str = "USD",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """Three columns of the engine's own ledger, and the difference between two of them.

    Nothing here models anything. Every cell is a number one of the two reports produced under a
    named ledger key, and every difference is a subtraction of two such numbers from runs that
    shared an information set. A key one report carries and the other does not is reported as
    unavailable rather than treated as zero.
    """
    current = _costs(baseline, "incumbent_costs")
    zaad = _costs(baseline, "selected_costs")
    yours = _costs(proposal, "incumbent_costs")

    rows: list[dict[str, Any]] = []
    for component in LEDGER_ORDER:
        cells = {"current": _number(current.get(component)), "zaad": _number(zaad.get(component)),
                 "proposal": _number(yours.get(component))}
        if all(v is None for v in cells.values()):
            continue
        rows.append({
            "component": component, "label": LEDGER_LABEL.get(component, component.replace("_", " ").title()),
            **cells,
            "proposal_vs_current": (cells["proposal"] - cells["current"]
                                    if cells["proposal"] is not None and cells["current"] is not None else None),
            "zaad_vs_current": (cells["zaad"] - cells["current"]
                                if cells["zaad"] is not None and cells["current"] is not None else None),
        })

    economics = (baseline or {}).get("economics") or {}
    proposal_economics = (proposal or {}).get("economics") or {}
    capital = {
        "current": _number(economics.get("incumbent_working_capital")),
        "zaad": _number(economics.get("selected_working_capital")),
        "proposal": _number(proposal_economics.get("incumbent_working_capital")),
    }

    service = _service_rows(baseline, proposal)

    # When the optimizer kept the operator's own plan, the middle column is the left column. Saying
    # so is the difference between an honest comparison and one that implies a recommendation the
    # engine never made.
    comparable = [row for row in rows if row["current"] is not None and row["zaad"] is not None]
    zaad_abstained = bool(comparable) and all(
        abs(row["zaad"] - row["current"]) < 0.005 for row in comparable)

    # The scope is the proposal's own products plus any product carrying a declared order-change
    # right, so the commitments layer can be declared on both runs. Calling all of them "the
    # products on this proposal" was wrong whenever the second group was not empty.
    own = {str(line["sku"]) for line in (draft.get("lines") or []) if line.get("sku")}
    carried = [sku for sku in scope if sku not in own]
    covered = (
        f"The comparison covers the {len(scope)} product{'' if len(scope) == 1 else 's'} on this proposal. "
        if not carried else
        f"The comparison covers {len(scope)} products: the {len(own)} "
        f"product{'' if len(own) == 1 else 's'} on this proposal, and {len(carried)} more that "
        f"{'carries' if len(carried) == 1 else 'carry'} a declared order-change right, so both runs "
        "price those rights the same way. "
    )
    limitations: list[str] = [
        covered
        + "Effects that reach other products — a supplier's weekly capacity shared with other orders, for "
        "example — are outside it.",
        "Your current plan and your proposal are both the projection of your declared ordering policy: "
        "one without this order, one with it. The difference between them is this order.",
    ]
    # Both runs are the same engine over the same information, so they report the same limitations
    # almost always. Saying each one twice is noise that teaches a reader to skip the list.
    shared: list[str] = []
    for report in (baseline, proposal):
        for limitation in (report or {}).get("limitations") or []:
            if limitation not in shared:
                shared.append(limitation)
    limitations.extend(f"From the engine: {limitation}" for limitation in shared)
    limitations.extend(notes or [])

    unavailable: list[str] = []
    if baseline is None:
        unavailable.append("The baseline run has not produced a plan yet.")
    if proposal is None:
        unavailable.append("The run with your proposal has not produced a plan yet.")
    if baseline and proposal and baseline.get("as_of") != proposal.get("as_of"):
        unavailable.append("The two runs do not share an as-of date, so they are not comparable. Run the "
                           "evaluation again.")

    return {
        "columns": [
            {"key": "current", "label": "Your current plan",
             "source": "The projection of your declared ordering policy, without this order."},
            {"key": "zaad", "label": "What ZAAD recommends",
             "source": "The plan the optimizer selected over the same products and the same information."},
            {"key": "proposal", "label": "Your proposal",
             "source": "The projection of your declared ordering policy, with this order placed."},
        ],
        "currency": currency,
        "ledger": rows,
        "working_capital": capital,
        "service": service,
        "scope": scope,
        "as_of": (baseline or {}).get("as_of"),
        "information_hash": (baseline or {}).get("information_hash"),
        "baseline_status": (baseline or {}).get("status"),
        "proposal_status": (proposal or {}).get("status"),
        "limitations": limitations,
        "unavailable": unavailable,
        "amendment": draft.get("origin") == "IMPORTED_AMENDMENT",
        "zaad_abstained": zaad_abstained,
        "executable": False,
    }


def _service_rows(baseline: dict[str, Any] | None, proposal: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Service by service, what each column projects. Keyed by the engine's own service ids."""
    def index(report: dict[str, Any] | None, key: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for row in (report or {}).get("network_service") or []:
            out[str(row.get("service"))] = row.get(key)
        return out

    requested: dict[str, Any] = {}
    location: dict[str, Any] = {}
    for report in (baseline, proposal):
        for row in (report or {}).get("network_service") or []:
            requested.setdefault(str(row.get("service")), row.get("requested"))
            location.setdefault(str(row.get("service")), row.get("location"))
    current = index(baseline, "incumbent_achieved")
    zaad = index(baseline, "selected_achieved")
    yours = index(proposal, "incumbent_achieved")
    rows: list[dict[str, Any]] = []
    for service in sorted(requested):
        rows.append({"service": service, "location": location.get(service),
                     "requested": _number(requested.get(service)),
                     "current": _number(current.get(service)), "zaad": _number(zaad.get(service)),
                     "proposal": _number(yours.get(service))})
    return rows


def amendment_view(report: dict[str, Any] | None, po_id: str) -> dict[str, Any]:
    """What the engine says about one open order, for a proposed amendment to it.

    An amendment is worth what the contract says it is worth. P4B prices exactly the options the
    operator declared and nothing else, so this reads the engine's commitment block rather than
    modelling the change. With no declared right, the honest answer is that it cannot be priced.
    """
    commitments = (report or {}).get("commitments") or {}
    orders = commitments.get("orders") or []
    order = next((o for o in orders if str(o.get("po")) == po_id), None)
    if order is None:
        return {
            "priced": False,
            "reason": "This order is not in the last plan, so ZAAD has not evaluated a change to it. "
                      "Run a plan that covers its product to see what the engine says.",
            "declared_options": [],
        }
    declared = [row.get("option") for row in order.get("contractual_basis") or []]
    return {
        "priced": bool(declared),
        "order": order,
        "recommended_action": order.get("recommended_action"),
        "declared_options": declared,
        "reading": commitments.get("reading"),
        "reason": None if declared else
        "No contractual right to change this order is declared, so ZAAD cannot price a change to it. "
        "Declare the amendment terms your contract gives you and it will.",
        "executable": False,
    }


def store_evaluation(conn: Any, operator: str, *, draft_id: str, revision: int | None,
                     baseline_job_id: str | None, proposal_job_id: str | None, as_of: str | None,
                     scope: list[str], status: str, note: str | None = None) -> str:
    from api.product.drafts import ensure_tables

    ensure_tables(conn)
    identity = evaluation_id()
    conn.execute(
        "INSERT INTO zaad_evaluations (evaluation_id, operator_id, draft_id, revision, baseline_job_id, "
        "proposal_job_id, as_of, scope_skus, status, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [identity, operator, draft_id, revision, baseline_job_id, proposal_job_id, as_of,
         json.dumps(scope), status, note, datetime.now(timezone.utc).replace(tzinfo=None)])
    conn.execute("UPDATE zaad_draft_orders SET evaluation_id = ?, updated_at = ? "
                 "WHERE draft_id = ? AND operator_id = ?",
                 [identity, datetime.now(timezone.utc).replace(tzinfo=None), draft_id, operator])
    return identity
