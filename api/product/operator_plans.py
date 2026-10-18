"""Operator-plan capture for shadow comparison (HARDENING V1, H3b).

An ACTUAL_OPERATOR_PLAN is the operator's own intended purchasing decisions for a planning origin,
captured independently of ZAAD and before ZAAD's recommendation is exposed. Nothing in this module
infers a plan from history, from a reconstructed rule, from a Request's incumbent orders or from a
ZAAD proposal; the operator (or their export) states it.

The snapshot is append-only: every capture writes a new version with a content hash of the canonical
line set; a correction is a new version that supersedes the previous one, and the previous one keeps its
rows. A repeated capture of identical content returns the existing version instead of a duplicate, so a
retried request cannot change the baseline.

Plan lines are mapped to Request sources with the H3a comparator's business key (sku, supplier and,
in a network request, destination). A line without a usable identity is INCOMPLETE and is never guessed.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from zaad.full import comparator

PROVENANCES = ("OPERATOR_SUBMITTED", "OPERATOR_UPLOADED", "OPERATOR_CONFIRMED_DRAFT")
TABLES = ("zaad_operator_plans", "zaad_operator_plan_lines", "zaad_shadow_comparisons")


class PlanRefused(Exception):
    """The capture cannot be recorded as stated; the message is operator-facing."""


def _has_table(conn: Any, name: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {name} LIMIT 0")  # noqa: S608  # nosec B608 - names are the literals in TABLES
        return True
    except Exception:  # noqa: BLE001 - absent
        return False


def ensure_tables(conn: Any) -> None:
    """Create the H3b tables on a vault that predates migration 031 (the product's own tables only)."""
    if all(_has_table(conn, t) for t in TABLES):
        return
    from api.product.drafts import statements
    sql = (Path(__file__).resolve().parents[2] / "db" / "migrations" / "031_operator_plans.sql").read_text()
    for text in statements(sql):
        if not text.upper().startswith("CREATE TABLE IF NOT EXISTS ZAAD_"):
            continue
        conn.execute(text)
    missing = [t for t in TABLES if not _has_table(conn, t)]
    if missing:
        raise PlanRefused("This workspace is not set up for operator-plan capture yet: " + ", ".join(missing)
                          + " could not be created. Run the database migrations for this operator (scripts/setup_db.py).")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_utc_naive(value: Any) -> datetime:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    return stamp.to_pydatetime()


def canonical_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The line set in its canonical form: validated, normalised, sorted by business key. Physical order
    never changes the hash."""
    out = []
    for i, raw in enumerate(lines):
        sku = _text(raw.get("sku"))
        if not sku:
            raise PlanRefused(f"line {i + 1}: a SKU is required")
        try:
            qty = float(raw.get("quantity"))  # type: ignore[arg-type]  # a missing quantity is caught below as a refusal
        except (TypeError, ValueError):
            raise PlanRefused(f"line {i + 1}: the quantity must be a number") from None
        if not (qty >= 0) or qty != qty:
            raise PlanRefused(f"line {i + 1}: the quantity must be zero or positive")
        period = int(raw.get("period") or 0)
        if period < 0:
            raise PlanRefused(f"line {i + 1}: the period cannot be negative")
        out.append({"sku": sku, "supplier_id": _text(raw.get("supplier_id")), "destination_id": _text(raw.get("destination_id")),
                    "quantity": qty, "period": period, "line_reference": _text(raw.get("line_reference"))})
    if not out:
        raise PlanRefused("a plan needs at least one line (an explicit 'order nothing' is a line with quantity 0)")
    out.sort(key=lambda r: (r["sku"], r["supplier_id"] or "", r["destination_id"] or "", r["period"], r["line_reference"] or "", r["quantity"]))
    return out


def content_hash(lines: list[dict[str, Any]], as_of: datetime) -> str:
    body = json.dumps({"as_of": _as_utc_naive(as_of).isoformat(), "lines": canonical_lines(lines)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def plan_key(operator: str, as_of: datetime) -> str:
    return f"{operator}|{_as_utc_naive(as_of).isoformat()}"


def capture_plan(conn: Any, operator: str, *, as_of: datetime, lines: list[dict[str, Any]], provenance: str,
                 captured_by: str | None, source_reference: str | None = None, note: str | None = None,
                 supersedes: str | None = None) -> dict[str, Any]:
    """Record an operator plan as a new immutable version. Identical content for the same origin returns
    the existing version (idempotent); different content supersedes the latest version of the family."""
    ensure_tables(conn)
    if provenance not in PROVENANCES:
        raise PlanRefused(f"provenance must be one of {', '.join(PROVENANCES)}; {provenance!r} is not an independently established origin")
    canon = canonical_lines(lines)
    digest = content_hash(canon, as_of)
    key = plan_key(operator, as_of)
    origin = _as_utc_naive(as_of)
    existing = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? AND content_hash = ? ORDER BY version DESC LIMIT 1",
                     [operator, key, digest])
    if existing:
        return {**read_plan(conn, operator, existing[0]["plan_id"]), "created": False}
    latest = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? ORDER BY version DESC LIMIT 1", [operator, key])
    if supersedes and (not latest or latest[0]["plan_id"] != supersedes):
        raise PlanRefused("the plan version you are correcting is not the latest captured version for this origin; reload and correct the current one")
    version = (int(latest[0]["version"]) + 1) if latest else 1
    plan_id = f"plan_{uuid.uuid4().hex[:16]}"
    stamp = _now()
    conn.execute("INSERT INTO zaad_operator_plans (plan_id, operator_id, plan_key, version, as_of, captured_at, captured_by, provenance, source_reference, "
                 "content_hash, line_count, status, supersedes_plan_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CAPTURED', ?, ?, ?)",
                 [plan_id, operator, key, version, origin, stamp, captured_by, provenance, source_reference, digest, len(canon),
                  latest[0]["plan_id"] if latest else None, note, stamp])
    for n, line in enumerate(canon):
        conn.execute("INSERT INTO zaad_operator_plan_lines (plan_id, operator_id, line_no, sku, supplier_id, destination_id, quantity, period, line_reference) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [plan_id, operator, n, line["sku"], line["supplier_id"], line["destination_id"], line["quantity"], line["period"], line["line_reference"]])
    if latest:
        # status is the only field that ever changes on an earlier version, and it only moves forward
        conn.execute("UPDATE zaad_operator_plans SET status = 'SUPERSEDED' WHERE plan_id = ? AND operator_id = ?", [latest[0]["plan_id"], operator])
    return {**read_plan(conn, operator, plan_id), "created": True}


def _rows(conn: Any, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = conn.execute(sql, params)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def read_plan(conn: Any, operator: str, plan_id: str) -> dict[str, Any]:
    ensure_tables(conn)
    heads = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE plan_id = ? AND operator_id = ?", [plan_id, operator])
    if not heads:
        raise KeyError(plan_id)
    head = heads[0]
    lines = _rows(conn, "SELECT line_no, sku, supplier_id, destination_id, quantity, period, line_reference FROM zaad_operator_plan_lines "
                        "WHERE plan_id = ? AND operator_id = ? ORDER BY line_no", [plan_id, operator])
    # the stored lines must still hash to the recorded digest: a tampered or truncated snapshot is refused as evidence
    recomputed = content_hash(lines, head["as_of"])
    return {**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in head.items()}, "lines": lines,
            "integrity": "VERIFIED" if recomputed == head["content_hash"] else "HASH_MISMATCH"}


def list_plans(conn: Any, operator: str, *, as_of: datetime | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_tables(conn)
    if as_of is not None:
        rows = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? ORDER BY version DESC LIMIT ?", [operator, plan_key(operator, as_of), limit])
    else:
        rows = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE operator_id = ? ORDER BY created_at DESC, version DESC LIMIT ?", [operator, limit])
    return [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in rows]


# ── mapping a plan onto a Request ─────────────────────────────────────────────
def map_plan_to_request(plan: dict[str, Any], req: Any) -> dict[str, Any]:
    """Each plan line mapped to exactly one request source by business key, or left INCOMPLETE.

    Returns the purchases by (source, period) for the identified lines, the recorded quantity per source and
    period, the per-line fidelity and the coverage the comparator needs."""
    sources = list(req.sources)
    network = len({s.destination for s in sources}) > 1
    origin = pd.Timestamp(req.as_of)
    origin = origin.tz_convert(None) if origin.tzinfo is not None else origin
    frame = pd.DataFrame([{"po_id": f"line-{ln['line_no']}", "po_date": origin + pd.Timedelta(days=int(ln["period"]) * req.period_days),
                           "supplier_id": ln.get("supplier_id"), "sku": ln["sku"], "qty_ordered": float(ln["quantity"]), "unit_cost": None,
                           "destination_id": ln.get("destination_id")} for ln in plan["lines"]])
    actions = comparator.map_historical_actions(frame, sources, origin=origin, period_days=req.period_days, reviews=req.horizon, network=network)
    purchases: dict[tuple[str, int], float] = {}
    for ln in actions.lines:
        if ln.source is not None and ln.quantity > 0 and 0 <= ln.period < req.horizon:
            purchases[ln.source, ln.period] = purchases.get((ln.source, ln.period), 0.0) + ln.quantity
    coverage = actions.coverage(req.horizon)
    return {"purchases": purchases, "lines": [ln.as_dict() for ln in actions.lines], "coverage": coverage,
            "out_of_scope_lines": actions.out_of_scope,
            "identity_fidelity": comparator.EXACT if (coverage["lines_observed"] and coverage["lines_incomplete"] == 0) else
                                 (comparator.INCOMPLETE if coverage["lines_observed"] else comparator.NOT_AVAILABLE)}


def shadow_evidence(plan: dict[str, Any], mapping: dict[str, Any], *, req: Any, exposed_at: datetime, latest_version: int) -> dict[str, Any]:
    """What the comparator needs to decide whether this plan may serve as the ACTUAL_OPERATOR_PLAN for the request."""
    plan_as_of = _as_utc_naive(plan["as_of"])
    req_as_of = _as_utc_naive(req.as_of)
    return {"plan_id": plan["plan_id"], "version": int(plan["version"]), "latest_version": int(latest_version), "status": plan["status"],
            "provenance": plan["provenance"], "content_hash": plan["content_hash"], "integrity": plan.get("integrity"),
            "captured_at": _as_utc_naive(plan["captured_at"]), "exposed_at": _as_utc_naive(exposed_at),
            "plan_as_of": plan_as_of, "request_as_of": req_as_of, "same_origin": plan_as_of == req_as_of,
            "identity_fidelity": mapping["identity_fidelity"], "coverage": mapping["coverage"], "line_count": len(plan["lines"])}


# ── shadow comparison records ─────────────────────────────────────────────────
def store_comparison(conn: Any, operator: str, *, plan: dict[str, Any], as_of: datetime, request_hash: str | None, recommendation_source: str,
                     exposed_at: datetime, status: str, result: dict[str, Any] | None, note: str | None = None) -> str:
    ensure_tables(conn)
    identity = f"shadow_{uuid.uuid4().hex[:16]}"
    conn.execute("INSERT INTO zaad_shadow_comparisons (comparison_id, operator_id, plan_id, plan_version, plan_hash, as_of, request_hash, recommendation_source, "
                 "exposed_at, status, result_json, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 [identity, operator, plan["plan_id"], int(plan["version"]), plan["content_hash"], _as_utc_naive(as_of), request_hash, recommendation_source,
                  _as_utc_naive(exposed_at), status, json.dumps(result, default=str) if result is not None else None, note, _now()])
    return identity


def read_comparison(conn: Any, operator: str, comparison_id: str) -> dict[str, Any]:
    ensure_tables(conn)
    rows = _rows(conn, "SELECT * FROM zaad_shadow_comparisons WHERE comparison_id = ? AND operator_id = ?", [comparison_id, operator])
    if not rows:
        raise KeyError(comparison_id)
    row = rows[0]
    out = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items() if k != "result_json"}
    out["result"] = json.loads(row["result_json"]) if row.get("result_json") else None
    return out


def first_exposure(conn: Any, operator: str, plan_id: str) -> datetime | None:
    """The earliest moment a recommendation was compared against this plan family's origin: later captures
    for the same origin are 'after exposure' and cannot be the baseline of that comparison."""
    ensure_tables(conn)
    rows = _rows(conn, "SELECT MIN(c.exposed_at) AS first FROM zaad_shadow_comparisons c JOIN zaad_operator_plans p ON p.plan_id = c.plan_id "
                       "WHERE c.operator_id = ? AND p.plan_key = (SELECT plan_key FROM zaad_operator_plans WHERE plan_id = ? AND operator_id = ?)",
                 [operator, plan_id, operator])
    value = rows[0]["first"] if rows else None
    return None if value is None or (isinstance(value, float) and value != value) else _as_utc_naive(value)
