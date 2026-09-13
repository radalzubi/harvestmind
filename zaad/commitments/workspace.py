"""P4B V1 vault adapter (migration 022): declared PO commitment terms (`stg_po_commitments`) and amendment
options (`stg_po_options`) attached to the open orders the workspace builds. Absent tables or no rows attach
nothing (KEEP-only, the released request). A declared row for an unknown open order, a declared keep row,
or a malformed value is refused: flexibility is never manufactured."""
from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd

from zaad.commitments.contracts import INTERACTIVE_LIMITS
from zaad.full.contracts import PO_STAGES

# Release audit (C / K): the explicit boundary between vault text and the contract's vocabularies. Case and
# surrounding whitespace are normalised (a vault writes "Ordered"); every other value is refused with an
# operator-facing `commitments:` message, never mapped to a neighbour.
ACTIONS = ("cancel", "expedite", "de_expedite", "reschedule")
PROVENANCES = ("CONTRACT", "OPERATOR_DECLARED", "CONFIGURED_ASSUMPTION")


def normalize_stage(value: Any, where: str) -> str:
    stage = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if stage not in PO_STAGES:
        raise ValueError(f"commitments: {where} declares stage '{value}' outside the vocabulary {list(PO_STAGES)}")
    return stage


def normalize_action(value: Any, where: str) -> str:
    action = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if action == "keep":
        raise ValueError(f"commitments: {where} declares keep; the keep option is built from the order itself")
    if action not in ACTIONS:
        raise ValueError(f"commitments: {where} declares action '{value}' outside {list(ACTIONS)} (a route / mode change is not a commitment option)")
    return action


def normalize_provenance(value: Any, where: str) -> str:
    provenance = str(value).strip().upper().replace(" ", "_").replace("-", "_")
    if provenance not in PROVENANCES:
        raise ValueError(f"commitments: {where} declares provenance '{value}' outside {list(PROVENANCES)}")
    return provenance


def number(value: Any, name: str, where: str, *, upper: float | None = None) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"commitments: {where} declares {name} '{value}'; a number is required") from exc
    if not math.isfinite(v) or v < 0 or (upper is not None and v > upper):
        raise ValueError(f"commitments: {where} declares {name} {value}; a finite number in [0, {upper if upper is not None else 'inf'}) is required")
    return v


def _present(value: Any) -> bool:
    try:
        return value is not None and not bool(pd.isna(value))
    except (TypeError, ValueError):
        return value is not None


def _table(conn: Any, name: str, operator_id: str) -> pd.DataFrame | None:
    try:
        return conn.execute(f"SELECT * FROM {name} WHERE operator_id = ?", [operator_id]).df()  # noqa: S608  # nosec B608 - table names are code literals
    except Exception:  # noqa: BLE001 - table absent (pre-022 vault): nothing to attach
        return None


def commitment_declarations(conn: Any, operator_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]] | None:
    """(PO-level terms by po_id, option rows by po_id) or None when nothing is declared."""
    options = _table(conn, "stg_po_options", operator_id)
    terms = _table(conn, "stg_po_commitments", operator_id)
    if (options is None or options.empty) and (terms is None or terms.empty):
        return None
    by_po: dict[str, list[dict[str, Any]]] = {}
    for r in (options.to_dict("records") if options is not None else []):
        row: dict[str, Any] = {"po_id": str(r["po_id"]), "id": str(r["option_id"]), "action": r["action"], "due_offset_periods": r.get("due_offset_periods"),
                               "fee_per_unit": r.get("fee_per_unit"), "credit_per_unit": r.get("credit_per_unit"), "remaining_invoice_per_unit": r.get("remaining_invoice_per_unit"),
                               "payment_offset_periods": r.get("payment_offset_periods"), "max_quantity": r.get("max_quantity"), "deadline": r.get("deadline"),
                               "allowed_stages": r.get("allowed_stages"), "contract_reference": r.get("contract_reference"), "provenance": r.get("provenance")}
        by_po.setdefault(row["po_id"], []).append(row)
    po_terms: dict[str, dict[str, Any]] = {}
    for r in (terms.to_dict("records") if terms is not None else []):
        po_terms[str(r["po_id"])] = {k: r.get(k) for k in ("stage", "allow_split_amendments", "minimum_remaining_quantity", "prepaid_per_remaining_unit", "deposit_refundable_fraction", "cancellation_status")}
    return po_terms, by_po


def attach(pipeline_rows: list[dict[str, Any]], declarations, *, as_of, period_days: int) -> dict[str, Any]:
    """Merge declared terms and options into the workspace's pipeline rows (in place). Returns the build report entry."""
    po_terms, by_po = declarations
    known = {row["id"] for row in pipeline_rows}
    unknown = sorted((set(by_po) | set(po_terms)) - known)
    if unknown:
        raise ValueError(f"commitments: declared options for open orders the workspace does not carry: {unknown}")
    attached = 0
    total_non_keep = sum(len(v) for v in by_po.values())
    if total_non_keep > INTERACTIVE_LIMITS["non_keep_options"]:
        raise ValueError(f"commitments: {total_non_keep} amendment options declared, over the limit {INTERACTIVE_LIMITS['non_keep_options']}")
    for row in pipeline_rows:
        terms = po_terms.get(row["id"], {})
        where = f"order {row['id']}"
        if _present(terms.get("stage")):
            row["stage"] = normalize_stage(terms["stage"], where)
        if _present(terms.get("cancellation_status")):
            row["cancellation_status"] = str(terms["cancellation_status"])
        if _present(terms.get("allow_split_amendments")):
            row["allow_split_amendments"] = bool(terms["allow_split_amendments"])
        for k in ("minimum_remaining_quantity", "prepaid_per_remaining_unit"):
            if _present(terms.get(k)):
                row[k] = number(terms[k], k, where)
        if _present(terms.get("deposit_refundable_fraction")):
            row["deposit_refundable_fraction"] = number(terms["deposit_refundable_fraction"], "deposit_refundable_fraction", where, upper=1.)
        declared = by_po.get(row["id"], [])
        if len(declared) + len(row["options"]) > INTERACTIVE_LIMITS["options_per_order"]:
            raise ValueError(f"commitments: {where} declares {len(declared)} amendment options, over the limit {INTERACTIVE_LIMITS['options_per_order'] - 1}")
        if len({o["id"] for o in declared}) != len(declared) or any(o["id"] in {x["id"] for x in row["options"]} for o in declared):
            raise ValueError(f"commitments: {where} declares the same option id more than once")
        keep = next(o for o in row["options"] if o["action"] == "keep")
        for opt in declared:
            where_o = f"option {opt['id']} of order {row['id']}"
            opt["action"] = normalize_action(opt["action"], where_o)
            for k in ("fee_per_unit", "credit_per_unit", "remaining_invoice_per_unit", "max_quantity"):
                if _present(opt.get(k)):
                    opt[k] = number(opt[k], k, where_o)
            due = int(opt["due_offset_periods"]) if _present(opt.get("due_offset_periods")) else keep["due_in"]
            deadline = pd.Timestamp(opt["deadline"]).to_pydatetime() if _present(opt.get("deadline")) else None
            if deadline is None:
                raise ValueError(f"commitments: option {opt['id']} declares no deadline (an amendment right needs its window)")
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=as_of.tzinfo)
            raw_stages = json.loads(opt["allowed_stages"]) if _present(opt.get("allowed_stages")) and isinstance(opt["allowed_stages"], str) else (list(opt["allowed_stages"]) if _present(opt.get("allowed_stages")) else [row["stage"]])
            stages = [normalize_stage(x, where_o) for x in raw_stages]
            row["options"].append({"known_at": keep["known_at"], "id": opt["id"], "action": opt["action"], "due_in": max(0, due),
                                   "fee_per_unit": float(opt["fee_per_unit"]) if _present(opt.get("fee_per_unit")) else 0.,
                                   "credit_per_unit": float(opt["credit_per_unit"]) if _present(opt.get("credit_per_unit")) else 0.,
                                   "remaining_invoice_per_unit": float(opt["remaining_invoice_per_unit"]) if _present(opt.get("remaining_invoice_per_unit")) else (0. if opt["action"] == "cancel" else keep["remaining_invoice_per_unit"]),
                                   "payment_due_in": int(opt["payment_offset_periods"]) if _present(opt.get("payment_offset_periods")) else max(0, due) + max(0, keep["payment_due_in"] - keep["due_in"]),
                                   "max_quantity": float(opt["max_quantity"]) if _present(opt.get("max_quantity")) else float(keep["max_quantity"]),
                                   "deadline": deadline, "allowed_stages": stages,
                                   "contract_reference": str(opt["contract_reference"]) if _present(opt.get("contract_reference")) else "",
                                   "provenance": normalize_provenance(opt["provenance"], where_o) if _present(opt.get("provenance")) else "CONTRACT"})
            attached += 1
    return {"orders_with_terms": len(po_terms), "options_attached": attached}
