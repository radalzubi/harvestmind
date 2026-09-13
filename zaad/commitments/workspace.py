"""P4B V1 vault adapter (migration 022): declared PO commitment terms (`stg_po_commitments`) and amendment
options (`stg_po_options`) attached to the open orders the workspace builds. Absent tables or no rows attach
nothing (KEEP-only, the released request). A declared row for an unknown open order, a declared keep row,
or a malformed value is refused: flexibility is never manufactured."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


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
    for row in pipeline_rows:
        terms = po_terms.get(row["id"], {})
        for k in ("stage", "cancellation_status"):
            if _present(terms.get(k)):
                row[k] = str(terms[k])
        for k in ("allow_split_amendments",):
            if _present(terms.get(k)):
                row[k] = bool(terms[k])
        for k in ("minimum_remaining_quantity", "prepaid_per_remaining_unit", "deposit_refundable_fraction"):
            if _present(terms.get(k)):
                row[k] = float(terms[k])
        keep = next(o for o in row["options"] if o["action"] == "keep")
        for opt in by_po.get(row["id"], []):
            if opt["action"] == "keep":
                raise ValueError(f"commitments: option {opt['id']} declares keep for order {row['id']}; the keep option is built from the order itself")
            due = int(opt["due_offset_periods"]) if _present(opt.get("due_offset_periods")) else keep["due_in"]
            deadline = pd.Timestamp(opt["deadline"]).to_pydatetime() if _present(opt.get("deadline")) else None
            if deadline is None:
                raise ValueError(f"commitments: option {opt['id']} declares no deadline (an amendment right needs its window)")
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=as_of.tzinfo)
            stages = json.loads(opt["allowed_stages"]) if _present(opt.get("allowed_stages")) and isinstance(opt["allowed_stages"], str) else (list(opt["allowed_stages"]) if _present(opt.get("allowed_stages")) else [row["stage"]])
            row["options"].append({"known_at": keep["known_at"], "id": opt["id"], "action": opt["action"], "due_in": max(0, due),
                                   "fee_per_unit": float(opt["fee_per_unit"]) if _present(opt.get("fee_per_unit")) else 0.,
                                   "credit_per_unit": float(opt["credit_per_unit"]) if _present(opt.get("credit_per_unit")) else 0.,
                                   "remaining_invoice_per_unit": float(opt["remaining_invoice_per_unit"]) if _present(opt.get("remaining_invoice_per_unit")) else (0. if opt["action"] == "cancel" else keep["remaining_invoice_per_unit"]),
                                   "payment_due_in": int(opt["payment_offset_periods"]) if _present(opt.get("payment_offset_periods")) else max(0, due) + max(0, keep["payment_due_in"] - keep["due_in"]),
                                   "max_quantity": float(opt["max_quantity"]) if _present(opt.get("max_quantity")) else float(keep["max_quantity"]),
                                   "deadline": deadline, "allowed_stages": stages,
                                   "contract_reference": str(opt["contract_reference"]) if _present(opt.get("contract_reference")) else "",
                                   "provenance": str(opt["provenance"]) if _present(opt.get("provenance")) else "CONTRACT"})
            attached += 1
    return {"orders_with_terms": len(po_terms), "options_attached": attached}
