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
import math
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from zaad.full import comparator

PROVENANCES = ("OPERATOR_SUBMITTED", "OPERATOR_UPLOADED", "OPERATOR_CONFIRMED_DRAFT")
TABLES = ("zaad_operator_plans", "zaad_operator_plan_lines", "zaad_shadow_comparisons")
EXPOSURE_TABLES = ("zaad_recommendation_exposures", "zaad_exposure_coverage")
#: exposure bases a comparison may stand on as VERIFIED: a finished job in a complete job history, a row of the
#: recommendation ledger under verified coverage, or an earlier comparison that was itself verified
VERIFIED_EXPOSURE_BASES = ("JOB_FINISHED", "RECOMMENDATION_LEDGER", "PRIOR_COMPARISON")
# test hook: called after the version decision and before the insert, so a test can hold two corrections at the
# same point and prove that the database constraint, not the read, decides the race
def _no_hook() -> None:
    return None


_before_insert: Callable[[], None] = _no_hook


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


def ensure_exposure_tables(conn: Any) -> None:
    """Create the exposure ledger on a vault that predates migration 032, and open its coverage.

    Migration 032 normally runs when the vault is created or first opened under this schema and writes the coverage
    row then (the registry then stamps a vault it has just created, see `stamp_vault_creation`). A vault that reaches
    this code without it (migration on open disabled) gets the tables here and a coverage row stamped NOW with source
    LAZY: recording starts at this instant, and such a vault is treated as upgraded (never verified)."""
    if not all(_has_table(conn, t) for t in EXPOSURE_TABLES):
        from api.product.drafts import statements
        sql = (Path(__file__).resolve().parents[2] / "db" / "migrations" / "032_recommendation_exposures.sql").read_text()
        for text in statements(sql):
            if text.upper().startswith("CREATE TABLE IF NOT EXISTS ZAAD_") or text.upper().startswith("ALTER TABLE ZAAD_EXPOSURE_COVERAGE ADD COLUMN IF NOT EXISTS"):
                conn.execute(text)
        missing = [t for t in EXPOSURE_TABLES if not _has_table(conn, t)]
        if missing:
            raise PlanRefused("This workspace is not set up for recommendation exposure recording yet: " + ", ".join(missing)
                              + " could not be created. Run the database migrations for this operator (scripts/setup_db.py).")
    if not _rows(conn, "SELECT 1 FROM zaad_exposure_coverage LIMIT 1", []):
        conn.execute("INSERT INTO zaad_exposure_coverage (coverage_since_ms, source) VALUES (?, 'LAZY')",
                     [int(datetime.now(timezone.utc).timestamp() * 1000)])


def stamp_vault_creation(conn: Any, vault_path: str | None) -> None:
    """Called by the registry on a vault it has JUST created, after the migrations ran and before the operator exists
    for any route: the vault's whole life is under exposure recording. The stamp names the vault file so a copy of the
    file served from elsewhere is recognised as not this vault. It is written once; a replayed migration keeps it
    (the migration's insert happens only when no row exists) and nothing ever downgrades a CREATED row."""
    ensure_exposure_tables(conn)
    conn.execute("UPDATE zaad_exposure_coverage SET source = 'CREATED', bound_vault_path = ?, coverage_since_ms = ? "
                 "WHERE source IN ('MIGRATION', 'LAZY')",
                 [_text(vault_path), int(datetime.now(timezone.utc).timestamp() * 1000)])


def record_exposure(conn: Any, operator: str, *, as_of: datetime, route: str, request_hash: str | None = None,
                    reference: str | None = None) -> datetime:
    """Record that ZAAD's recommendation for `as_of` became accessible to `operator` through `route`, and return the
    instant recorded (server clock, UTC). Append-only: a repeat adds a row and the earliest row stays the first
    exposure. The caller records BEFORE it sends the recommendation, so nothing is accessible unrecorded; a failure
    here must withhold the recommendation."""
    ensure_exposure_tables(conn)
    stamp = _now()
    conn.execute("INSERT INTO zaad_recommendation_exposures (exposure_id, operator_id, as_of, route, request_hash, reference, exposed_at, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [f"exp_{uuid.uuid4().hex[:16]}", operator, _as_utc_naive(as_of), route, _text(request_hash), _text(reference), stamp, stamp])
    return stamp.replace(tzinfo=timezone.utc)


def ledger_exposure(conn: Any, operator: str, as_of: datetime) -> dict[str, Any]:
    """The earliest recorded exposure of a recommendation for (`operator`, `as_of`) in the vault's ledger, with the route
    that made it accessible and how many rows the origin has. Other operators' rows are never read."""
    ensure_exposure_tables(conn)
    rows = _rows(conn, "SELECT exposed_at, route, exposure_id FROM zaad_recommendation_exposures WHERE operator_id = ? AND as_of = ? "
                       "ORDER BY exposed_at, created_at, exposure_id LIMIT 1", [operator, _as_utc_naive(as_of)])
    count = _rows(conn, "SELECT count(*) AS n FROM zaad_recommendation_exposures WHERE operator_id = ? AND as_of = ?",
                  [operator, _as_utc_naive(as_of)])[0]["n"]
    if not rows:
        return {"earliest": None, "route": None, "exposure_id": None, "count": int(count)}
    row = rows[0]
    return {"earliest": _as_utc_naive(row["exposed_at"]).replace(tzinfo=timezone.utc), "route": row["route"], "exposure_id": row["exposure_id"], "count": int(count)}


def coverage(conn: Any) -> dict[str, Any]:
    """When this vault began recording exposures and what its history can vouch for.

    `provenance` is NEW for a vault the registry created under this schema and served from the file it was created as
    (its whole life is recorded), UPGRADED for a vault that existed before recording began (its coverage row came from
    the migration's replay on open, or lazily), and RESTORED for a CREATED vault served from another file than the one
    it was created as (a copy, a restore, another environment: what happened to it elsewhere is unknown). The file
    binding is checked when the connection knows its file (the product's vault connections do; a bare connection does
    not, and then only the stamp decides). Nothing about the vault's data is used: an upgraded vault may have served a
    recommendation for ANY origin before recording, because the contract route takes the origin from the caller."""
    ensure_exposure_tables(conn)
    row = _rows(conn, "SELECT coverage_since_ms, source, bound_vault_path, legacy_engines_seen_ms FROM zaad_exposure_coverage "
                      "ORDER BY coverage_since_ms LIMIT 1", [])[0]
    since = datetime.fromtimestamp(int(row["coverage_since_ms"]) / 1000.0, tz=timezone.utc)
    legacy_seen = (datetime.fromtimestamp(int(row["legacy_engines_seen_ms"]) / 1000.0, tz=timezone.utc)
                   if row.get("legacy_engines_seen_ms") is not None else None)
    served_from = getattr(conn, "_key", None)
    bound = _text(row.get("bound_vault_path"))
    if row["source"] != "CREATED":
        provenance = "UPGRADED"
    elif bound is not None and served_from is not None and str(served_from) != bound:
        provenance = "RESTORED"
    else:
        provenance = "NEW"
    return {"since": since, "source": row["source"], "provenance": provenance, "bound_vault_path": bound,
            "served_from": str(served_from) if served_from is not None else None, "legacy_engines_seen_at": legacy_seen}


def note_legacy_engines(conn: Any) -> None:
    """Record, once and for good, that a superseded planning engine (whose recommendations are not recorded here) was
    reachable on the service that serves this vault. From then on no exposure history of this vault is complete: an
    unrecorded recommendation may have been served at any time after this instant, for any origin."""
    ensure_exposure_tables(conn)
    conn.execute("UPDATE zaad_exposure_coverage SET legacy_engines_seen_ms = ? WHERE legacy_engines_seen_ms IS NULL",
                 [int(datetime.now(timezone.utc).timestamp() * 1000)])


def coverage_verifies(cov: dict[str, Any], *, as_of: datetime, captured_at: datetime) -> str | None:
    """None when the ledger can vouch for every recommendation route for this plan; otherwise why it cannot.

    `as_of` plays no part: no planning origin is ever excluded from an unverified history on the strength of the
    vault's data, because a recommendation for any origin could have been requested before recording began."""
    captured = _as_utc_naive(captured_at).replace(tzinfo=timezone.utc)
    if cov["provenance"] == "UPGRADED":
        return (f"this workspace existed before recommendation exposures were recorded (recording began {cov['since'].isoformat()}, "
                f"source {cov['source']}); a recommendation served before then, for any planning origin, is in no record and cannot be excluded")
    if cov["provenance"] == "RESTORED":
        return (f"this workspace's exposure ledger was created for vault file {cov['bound_vault_path']} but is served from {cov['served_from']}; "
                "what was served to its operator elsewhere is in no record here, so its history cannot be established")
    if captured < cov["since"]:
        return (f"the plan was captured at {captured.isoformat()}, before this workspace began recording recommendation exposures "
                f"({cov['since'].isoformat()}); a recommendation between the capture and that instant is not recorded")
    if cov.get("legacy_engines_seen_at") is not None:
        return (f"superseded planning engines (ZAAD_LEGACY_PLANNERS), whose recommendations are not recorded as exposures, were reachable on this "
                f"service at {cov['legacy_engines_seen_at'].isoformat()}; an unrecorded recommendation since then cannot be excluded")
    return None


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
        if not math.isfinite(qty) or qty < 0:
            raise PlanRefused(f"line {i + 1}: the quantity must be a finite number, zero or positive")
        try:
            period = int(raw.get("period") or 0)
        except (TypeError, ValueError):
            raise PlanRefused(f"line {i + 1}: the period must be a whole number") from None
        if period < 0 or period > 52:
            raise PlanRefused(f"line {i + 1}: the period must be between 0 and 52")
        out.append({"sku": sku, "supplier_id": _text(raw.get("supplier_id")), "destination_id": _text(raw.get("destination_id")),
                    "quantity": qty, "period": period, "line_reference": _text(raw.get("line_reference"))})
    if not out:
        raise PlanRefused("a plan needs at least one line (an explicit 'order nothing' is a line with quantity 0)")
    out.sort(key=lambda r: (r["sku"], r["supplier_id"] or "", r["destination_id"] or "", r["period"], r["line_reference"] or "", r["quantity"]))
    # two lines with one business key and no distinguishing reference are either a duplicate submission or two
    # real lines; the plan cannot say which, so it is refused rather than summed or deduplicated
    seen: set[tuple] = set()
    for r in out:
        key = (r["sku"], r["supplier_id"], r["destination_id"], r["period"], r["line_reference"])
        if key in seen:
            raise PlanRefused(f"lines repeat the same SKU, supplier, destination and period ({r['sku']}, {r['supplier_id']}, period {r['period']}); "
                              "merge them or give each a line_reference")
        seen.add(key)
    return out


def content_hash(lines: list[dict[str, Any]], as_of: datetime) -> str:
    body = json.dumps({"as_of": _as_utc_naive(as_of).isoformat(), "lines": canonical_lines(lines)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def plan_key(operator: str, as_of: datetime) -> str:
    return f"{operator}|{_as_utc_naive(as_of).isoformat()}"


def capture_plan(conn: Any, operator: str, *, as_of: datetime, lines: list[dict[str, Any]], provenance: str,
                 captured_by: str | None, source_reference: str | None = None, note: str | None = None,
                 supersedes: str | None = None) -> dict[str, Any]:
    """Record an operator plan as a new immutable version.

    - the first capture for an origin needs no `supersedes`;
    - identical content for the same origin returns the existing version (a retry adds nothing);
    - different content must name the latest version in `supersedes`; a missing, stale or wrong id is refused;
    - two corrections of the same version cannot both land: the new version is written inside a transaction and
      the UNIQUE (operator, origin, version) constraint rejects the second writer, whatever it read first;
    - earlier versions and their lines are never updated: a version's status is derived from whether a later
      version exists."""
    ensure_tables(conn)
    if provenance not in PROVENANCES:
        raise PlanRefused(f"provenance must be one of {', '.join(PROVENANCES)}; {provenance!r} is not an independently established origin")
    canon = canonical_lines(lines)
    digest = content_hash(canon, as_of)
    key = plan_key(operator, as_of)
    origin = _as_utc_naive(as_of)
    existing = _rows(conn, "SELECT plan_id FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? AND content_hash = ? ORDER BY version DESC LIMIT 1",
                     [operator, key, digest])
    if existing:
        return {**read_plan(conn, operator, existing[0]["plan_id"]), "created": False}
    latest = _rows(conn, "SELECT plan_id, version FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? ORDER BY version DESC LIMIT 1", [operator, key])
    if latest and not supersedes:
        raise PlanRefused(f"a plan is already captured for this origin (version {latest[0]['version']}, {latest[0]['plan_id']}); a correction must name it in "
                          "`supersedes` so the version being replaced is explicit")
    if latest and latest[0]["plan_id"] != supersedes:
        raise PlanRefused(f"`supersedes` names {supersedes}, but the latest captured version for this origin is {latest[0]['plan_id']} "
                          f"(version {latest[0]['version']}); reload and correct the current one")
    if not latest and supersedes:
        raise PlanRefused("nothing is captured for this origin yet, so there is no version to supersede")
    version = (int(latest[0]["version"]) + 1) if latest else 1
    plan_id = f"plan_{uuid.uuid4().hex[:16]}"
    stamp = _now()
    _before_insert()
    conn.begin()
    try:
        conn.execute("INSERT INTO zaad_operator_plans (plan_id, operator_id, plan_key, version, as_of, captured_at, captured_by, provenance, source_reference, "
                     "content_hash, line_count, supersedes_plan_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [plan_id, operator, key, version, origin, stamp, captured_by, provenance, source_reference, digest, len(canon),
                      latest[0]["plan_id"] if latest else None, note, stamp])
        for n, line in enumerate(canon):
            _insert_line(conn, plan_id, operator, n, line)
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001 - the engine already aborted the transaction on the conflict; nothing of ours was written
            pass
        text = str(exc)
        if type(exc).__name__ in ("ConstraintException", "TransactionException") or "Duplicate key" in text or "Constraint Error" in text or "conflict" in text.lower():
            # another correction of the same version, or the same content, landed first: nothing of this one remains
            retry = _rows(conn, "SELECT plan_id FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? AND content_hash = ?", [operator, key, digest])
            if retry:
                return {**read_plan(conn, operator, retry[0]["plan_id"]), "created": False}
            raise PlanRefused("another correction of this plan version was recorded first; reload and correct the current version") from exc
        raise
    return {**read_plan(conn, operator, plan_id), "created": True}


def _insert_line(conn: Any, plan_id: str, operator: str, n: int, line: dict[str, Any]) -> None:
    conn.execute("INSERT INTO zaad_operator_plan_lines (plan_id, operator_id, line_no, sku, supplier_id, destination_id, quantity, period, line_reference) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 [plan_id, operator, n, line["sku"], line["supplier_id"], line["destination_id"], line["quantity"], line["period"], line["line_reference"]])


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
    try:
        recomputed = content_hash(lines, head["as_of"])
    except PlanRefused:
        recomputed = "INVALID"
    latest = _rows(conn, "SELECT MAX(version) AS v FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ?", [operator, head["plan_key"]])[0]["v"]
    return {**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in head.items()}, "lines": lines,
            "status": "CAPTURED" if int(latest) == int(head["version"]) else "SUPERSEDED", "latest_version": int(latest),
            "integrity": "VERIFIED" if (recomputed == head["content_hash"] and len(lines) == int(head["line_count"])) else "HASH_MISMATCH"}


def list_plans(conn: Any, operator: str, *, as_of: datetime | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_tables(conn)
    if as_of is not None:
        rows = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ? ORDER BY version DESC LIMIT ?", [operator, plan_key(operator, as_of), limit])
    else:
        rows = _rows(conn, "SELECT * FROM zaad_operator_plans WHERE operator_id = ? ORDER BY created_at DESC, version DESC LIMIT ?", [operator, limit])
    out = []
    latest_by_key: dict[str, int] = {}
    for r in rows:
        if r["plan_key"] not in latest_by_key:
            latest_by_key[r["plan_key"]] = int(_rows(conn, "SELECT MAX(version) AS v FROM zaad_operator_plans WHERE operator_id = ? AND plan_key = ?", [operator, r["plan_key"]])[0]["v"])
        out.append({**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()},
                    "status": "CAPTURED" if int(r["version"]) == latest_by_key[r["plan_key"]] else "SUPERSEDED", "latest_version": latest_by_key[r["plan_key"]]})
    return out


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
    beyond = [ln for ln in actions.lines if ln.period >= req.horizon]
    coverage["lines_beyond_horizon"] = len(beyond)
    return {"purchases": purchases, "lines": [ln.as_dict() for ln in actions.lines], "coverage": coverage,
            "out_of_scope_lines": actions.out_of_scope, "lines_beyond_horizon": len(beyond),
            "identity_fidelity": comparator.EXACT if (coverage["lines_observed"] and coverage["lines_incomplete"] == 0) else
                                 (comparator.INCOMPLETE if coverage["lines_observed"] else comparator.NOT_AVAILABLE)}


def shadow_evidence(plan: dict[str, Any], mapping: dict[str, Any], *, req: Any, exposed_at: datetime, latest_version: int,
                    exposure_basis: str = "UNVERIFIED", exposure_note: str | None = None) -> dict[str, Any]:
    """What the comparator needs to decide whether this plan may serve as the ACTUAL_OPERATOR_PLAN for the request.

    `exposed_at` is the earliest instant ZAAD's recommendation for this origin is KNOWN to have been accessible
    (a finished planning job, a row of the recommendation ledger, or an earlier stored comparison); `exposure_basis`
    says what established it: JOB_FINISHED, RECOMMENDATION_LEDGER, PRIOR_COMPARISON, or UNVERIFIED when the history
    behind it is not established as complete (`exposure_note` says why). Client-supplied times never set it."""
    plan_as_of = _as_utc_naive(plan["as_of"])
    req_as_of = _as_utc_naive(req.as_of)
    return {"plan_id": plan["plan_id"], "version": int(plan["version"]), "latest_version": int(latest_version), "status": plan["status"],
            "provenance": plan["provenance"], "content_hash": plan["content_hash"], "integrity": plan.get("integrity"),
            "captured_at": _as_utc_naive(plan["captured_at"]), "exposed_at": _as_utc_naive(exposed_at), "exposure_basis": exposure_basis,
            "exposure_note": exposure_note,
            "plan_as_of": plan_as_of, "request_as_of": req_as_of, "same_origin": plan_as_of == req_as_of,
            "identity_fidelity": mapping["identity_fidelity"], "coverage": mapping["coverage"], "line_count": len(plan["lines"]),
            "lines_beyond_horizon": mapping.get("lines_beyond_horizon", 0)}


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


class PriorExposure:
    """What this plan family's stored comparisons already recorded about the first exposure of a recommendation
    for its origin. `earliest` is the earliest exposure any comparison recorded, whatever established it: a later
    comparison can never move the exposure after it. `verified` is the earliest exposure a comparison established
    from a complete job history (basis JOB_FINISHED, or PRIOR_COMPARISON rooted in one); None when no comparison
    did. Only `verified` can stand as a pre-exposure basis: a synchronous run's own clock recorded by an earlier
    comparison is an exposure, not a verification, and must not become one by being repeated."""
    __slots__ = ("earliest", "verified", "verified_job")

    def __init__(self, earliest: datetime, verified: datetime | None, verified_job: datetime | None = None):
        self.earliest, self.verified, self.verified_job = earliest, verified, verified_job


def first_exposure(conn: Any, operator: str, plan_id: str) -> PriorExposure | None:
    """The earliest recorded exposure of a recommendation for this plan family's origin across every stored
    comparison (whatever version they used), with the earliest VERIFIED one: a repeated comparison never resets
    either, and a capture after the earliest is not an independent baseline for this origin."""
    ensure_tables(conn)
    rows = _rows(conn, "SELECT c.exposed_at, c.result_json FROM zaad_shadow_comparisons c JOIN zaad_operator_plans p ON p.plan_id = c.plan_id "
                       "WHERE c.operator_id = ? AND p.plan_key = (SELECT plan_key FROM zaad_operator_plans WHERE plan_id = ? AND operator_id = ?)",
                 [operator, plan_id, operator])
    earliest: datetime | None = None
    verified: datetime | None = None
    verified_job: datetime | None = None          # verified exposures rooted in a finished job: the job scan must still find them
    for row in rows:
        value = row.get("exposed_at")
        if value is None or (isinstance(value, float) and value != value):
            continue
        when = _as_utc_naive(value)
        earliest = when if earliest is None or when < earliest else earliest
        try:
            basis = (json.loads(row["result_json"]) if row.get("result_json") else {}).get("evidence", {}).get("exposure_basis")
        except (ValueError, AttributeError):
            basis = None                     # a comparison whose stored result cannot be read verifies nothing
        if basis in VERIFIED_EXPOSURE_BASES:
            verified = when if verified is None or when < verified else verified
        if basis == "JOB_FINISHED":
            verified_job = when if verified_job is None or when < verified_job else verified_job
    return None if earliest is None else PriorExposure(earliest, verified, verified_job)
