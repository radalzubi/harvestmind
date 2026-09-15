"""Proposed purchase orders: one object, one lifecycle, four ways in.

A proposal can start from a ZAAD recommendation, from the operator's own current ordering policy,
from a buyer typing it, from a spreadsheet they upload, or as an amendment to an order that already
exists in their system. All five produce **the same row** in `zaad_draft_orders` and the same
editor — the only difference is the `origin` field and, for an amendment, the order it points at.
There is deliberately no second code path: a product that stores "ZAAD orders" differently from
"my orders" drifts within a month.

Three rules the lifecycle enforces:

  * **Imported data is never edited.** Changing an order that came from the operator's system
    creates a proposal *against* it. `stg_fmcg_purchase_orders` is read-only to this module.
  * **An approved or exported revision is immutable.** Changing one produces a new revision that
    records what it supersedes; the old row stays exactly as it was approved.
  * **Nothing is transmitted.** Approve and export are the end of the loop in this release. No
    supplier and no ERP is contacted anywhere in this file.

Validation warns; it does not forbid. A quantity below a declared minimum, a quantity that is not a
whole number of cases, an order above a supplier's declared weekly capacity, **a product that is not
in the master yet** — each is something a buyer may have a reason for, and each is a warning shown
before they approve. Only what makes the document meaningless is refused: a line with no product, a
non-positive quantity, a receipt date before the order date, a number that is not a number, and a
number so large it is a typo rather than an order (`MAX_LINE_VALUE`).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal

from api.product import queries
from api.product.catalog import _one, _rows, has_table

ORIGINS = ("ZAAD_RECOMMENDATION", "CURRENT_POLICY", "MANUAL", "UPLOADED_PROPOSAL", "IMPORTED_AMENDMENT")
STATES = ("DRAFT", "READY_FOR_REVIEW", "APPROVED", "REJECTED", "EXPORTED", "SUPERSEDED")
#: The P4B V1 vocabulary, exactly. The product never invents a seventh thing to do to an order.
AMENDMENT_ACTIONS = ("KEEP", "DEFER", "EXPEDITE", "REDUCE", "CANCEL", "SPLIT")

EDITABLE = ("DRAFT",)
DELETABLE = ("DRAFT",)
#: A file that looks like a purchase order leaves only for a decided one. Exporting a draft would
#: put an unapproved document into someone's ERP with nothing on it saying so.
EXPORTABLE = ("APPROVED", "EXPORTED")
#: An approved or exported revision is history. Editing one makes a new revision instead.
IMMUTABLE = ("APPROVED", "EXPORTED", "REJECTED", "SUPERSEDED")

MAX_LINES = 500
MAX_NOTE = 2000
#: An identifier — a supplier code, a product code, a site, an order number — is a short string in
#: every system this product exports to. A 300,000-character supplier id was stored and rendered on
#: Home before this bound existed; nothing legitimate is that long.
MAX_IDENTIFIER = 200
#: A quantity or a price larger than this is a typo or a paste accident, not an order. A trillion
#: units of anything is not a number an importer means, and it reaches the optimizer as one — where
#: it is either nonsense or a solver failure, neither of which says what went wrong. Refused here,
#: in words, where the person who typed it is looking.
MAX_LINE_VALUE = 1_000_000_000.0


class DraftRefused(ValueError):
    """The document cannot be stored as asked. The message is written for the person reading it."""


class EvaluationStale(DraftRefused):
    """An approval was asked for over a comparison that no longer describes the proposal.

    Not refused for ever: the caller may acknowledge it and approve anyway, and the acknowledgement
    is written into the record. Refused silently is what §93 of the brief forbids.
    """


@dataclass(frozen=True)
class Line:
    sku: str
    quantity: float
    unit_price: float | None = None
    units_per_case: float | None = None
    requested_receipt_date: str | None = None
    notes: str | None = None


def _said(state: str) -> str:
    """A state named the way a sentence needs it: "an approved proposal", not "a approved"."""
    words = str(state).lower().replace("_", " ")
    return f"{'an' if words[:1] in 'aeiou' else 'a'} {words}"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _identity() -> str:
    return f"draft_{uuid.uuid4().hex[:16]}"


def _as_date(value: Any, field: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError as exc:
        raise DraftRefused(f"{field} is not a date ZAAD can read: {value!r}. Use YYYY-MM-DD.") from exc


def _number(value: Any, field: str, *, allow_none: bool = True) -> float | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise DraftRefused(f"{field} is required.")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise DraftRefused(f"{field} is not a number: {value!r}.") from exc
    if out != out or out in (float("inf"), float("-inf")):
        raise DraftRefused(f"{field} is not a finite number.")
    return out


def _identifier(value: Any, field: str) -> str | None:
    """A bounded identifier, or None when absent."""
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > MAX_IDENTIFIER:
        raise DraftRefused(f"{field} is {len(text):,} characters long; an identifier is at most {MAX_IDENTIFIER}. "
                           "Check that the right value was pasted.")
    return text


def checkpoint(conn: Any) -> bool:
    """Write the WAL into the database file now.

    Schema changes must never wait in the write-ahead log. The vault's connection is held open for
    the life of the process (see `infrastructure/db_manager.py`), so nothing checkpoints on close
    the way a per-request connection used to — and a DuckDB file whose WAL holds an `ALTER TABLE`
    on one of these tables **cannot be opened** after a hard stop: replay fails with an internal
    error. Reproduced in the V1 audit with one `ADD COLUMN`, and held by
    `test_a_vault_survives_a_hard_stop_right_after_ensure_tables`. A checkpoint fails when another
    connection has a transaction open; that is reported, not raised, because the DDL itself is
    committed and the next quiet moment checkpoints it.
    """
    try:
        conn.execute("CHECKPOINT")
        return True
    except Exception:  # noqa: BLE001 - another transaction is open; the anchor checkpoints when idle
        return False


#: Tables `ensure_tables` is responsible for. If one of these is missing afterwards, the vault is
#: not usable for proposed orders and the caller must be told, not handed a catalogue error.
PRODUCT_TABLES = ("zaad_draft_orders", "zaad_draft_lines", "zaad_draft_events",
                  "zaad_export_profiles", "zaad_export_log", "zaad_evaluations")


def statements(sql: str) -> list[str]:
    """Split a migration file into statements.

    `sql.split(";")` is wrong here and was: migration 023 carries `COMMENT ON ... IS '...;...'`
    strings and `--` comments that contain semicolons, so a naive split cuts statements in half and
    every half fails to parse. That failure used to be swallowed, which left a vault with one of the
    six tables and a 500 on the first visit to Purchase orders. This walks the text instead, so a
    semicolon inside a quoted string or a line comment does not end a statement.
    """
    out: list[str] = []
    buf: list[str] = []
    quote = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            buf.append(ch)
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":  # '' is an escaped quote, not the end
                    buf.append(sql[i + 1])
                    i += 2
                    continue
                quote = False
            i += 1
            continue
        if ch == "'":
            quote = True
            buf.append(ch)
        elif sql.startswith("--", i):
            end = sql.find("\n", i)
            i = len(sql) if end == -1 else end
            continue
        elif ch == ";":
            text = "".join(buf).strip()
            if text:
                out.append(text)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def ensure_tables(conn: Any) -> None:
    """Create the product's own tables if this vault predates migration 023.

    Vaults are created per operator and migrated by `scripts/setup_db.py`; a workspace opened before
    this release would otherwise meet a missing table on its first visit to Purchase Orders. Only
    the product's own tables are created here — never a staging table, and never a column on one.
    """
    from pathlib import Path
    migrations = Path(__file__).resolve().parents[2] / "db" / "migrations"
    ran_ddl = False
    if not (has_table(conn, "zaad_draft_orders") and has_table(conn, "zaad_export_profiles")):
        sql = (migrations / "023_operating_product.sql").read_text()
        for text in statements(sql):
            if text.upper().startswith("ALTER TABLE STG_"):
                continue  # staging columns belong to the migration runner, not to a page load
            try:
                conn.execute(text)
                ran_ddl = True
            except Exception:  # noqa: BLE001 - already present, or a COMMENT the engine declines
                continue
        missing = [name for name in PRODUCT_TABLES if not has_table(conn, name)]
        if missing:
            raise DraftRefused(
                "This workspace is not set up for proposed orders yet — "
                + ", ".join(missing)
                + " could not be created. Run the database migrations for this operator "
                  "(scripts/setup_db.py) and open the page again.")
    # The V2 columns (migration 024) on a vault migrated to 023 by an earlier release. One PRAGMA
    # per call; the ALTERs are `IF NOT EXISTS` and touch only the product's own tables.
    present = {row[1] for row in conn.execute("PRAGMA table_info('zaad_evaluations')").fetchall()}
    if "draft_hash" not in present:
        for text in statements((migrations / "024_operating_product_v2.sql").read_text()):
            if not text.upper().startswith("ALTER TABLE ZAAD_"):
                continue
            try:
                conn.execute(text)
                ran_ddl = True
            except Exception:  # noqa: BLE001 - already present
                continue
    if ran_ddl:
        checkpoint(conn)


# ── reading ───────────────────────────────────────────────────────────────────

DRAFT_SORTS = {"updated_at": "updated_at", "created_at": "created_at", "state": "state",
               "supplier_id": "supplier_id", "units": "units", "value": "value", "reference": "reference"}


def list_drafts(
    conn: Any, operator: str, *, state: str | None = None, origin: str | None = None,
    supplier_id: str | None = None, search: str | None = None, source_po_id: str | None = None,
    sort: str = "updated_at", direction: str = "desc", limit: int = 50, offset: int = 0,
) -> dict[str, Any]:
    ensure_tables(conn)
    if sort not in DRAFT_SORTS:
        raise DraftRefused(f"Cannot sort proposals on {sort!r}")
    if state and state not in STATES:
        raise DraftRefused(f"Unknown state {state!r}")
    if origin and origin not in ORIGINS:
        raise DraftRefused(f"Unknown origin {origin!r}")
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    direction_sql = "DESC" if str(direction).lower() == "desc" else "ASC"

    where = ["d.operator_id = ?"]
    params: list[Any] = [operator]
    if state:
        where.append("d.state = ?")
        params.append(state)
    if origin:
        where.append("d.origin = ?")
        params.append(origin)
    if supplier_id:
        where.append("d.supplier_id = ?")
        params.append(supplier_id)
    if source_po_id:
        where.append("d.source_po_id = ?")
        params.append(source_po_id)
    if search and search.strip():
        needle = queries.like_contains(search.strip())
        esc = queries.LIKE_ESCAPE
        where.append(f"(CAST(d.draft_id AS VARCHAR) ILIKE ? ESCAPE '{esc}' "
                     f"OR CAST(d.reference AS VARCHAR) ILIKE ? ESCAPE '{esc}' "
                     f"OR CAST(d.supplier_id AS VARCHAR) ILIKE ? ESCAPE '{esc}' "
                     f"OR CAST(d.source_po_id AS VARCHAR) ILIKE ? ESCAPE '{esc}')")
        params.extend([needle] * 4)
    clause = " WHERE " + " AND ".join(where)

    body = f"""
    SELECT d.*, coalesce(l.lines, 0) AS lines, l.units, l.value, l.value_incomplete
    FROM zaad_draft_orders d
    LEFT JOIN (SELECT draft_id, count(*) AS lines, sum(quantity) AS units,
                      sum(quantity * coalesce(unit_price, 0)) AS value,
                      bool_or(unit_price IS NULL) AS value_incomplete
               FROM zaad_draft_lines WHERE operator_id = ? GROUP BY draft_id) l
           ON l.draft_id = d.draft_id{clause}
    """  # nosec B608 - code literals plus allowlisted names (DRAFT_SORTS); values bind
    rows = _rows(conn, f"SELECT * FROM ({body}) ORDER BY {DRAFT_SORTS[sort]} {direction_sql} NULLS LAST LIMIT ? OFFSET ?",  # nosec B608 - code literals plus allowlisted names (DRAFT_SORTS); values bind
                 [operator, *params, limit, offset])
    total = int(_one(conn, f"SELECT count(*) FROM ({body})", [operator, *params]) or 0)  # nosec B608 - code literals plus allowlisted names (DRAFT_SORTS); values bind
    return {"rows": rows, "total": total, "limit": limit, "offset": offset,
            "sort": sort, "direction": direction_sql.lower()}


def read_draft(conn: Any, operator: str, draft_id: str) -> dict[str, Any]:
    """One proposal with its lines and its history. A draft of another workspace is simply absent."""
    ensure_tables(conn)
    head = _rows(conn, "SELECT * FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?",
                 [draft_id, operator])
    if not head:
        raise KeyError(draft_id)
    lines = _rows(conn, "SELECT * FROM zaad_draft_lines WHERE draft_id = ? AND operator_id = ? ORDER BY line_no",
                  [draft_id, operator])
    events = _rows(conn, "SELECT * FROM zaad_draft_events WHERE draft_id = ? AND operator_id = ? ORDER BY happened_at",
                   [draft_id, operator])
    exports = _rows(conn, "SELECT * FROM zaad_export_log WHERE draft_id = ? AND operator_id = ? ORDER BY happened_at DESC",
                    [draft_id, operator])
    evaluations = _rows(conn, "SELECT * FROM zaad_evaluations WHERE draft_id = ? AND operator_id = ? ORDER BY created_at DESC",
                        [draft_id, operator])
    row = head[0]
    draft = {
        **row,
        "lines": lines,
        "events": events,
        "exports": exports,
        "evaluations": evaluations,
        "editable": row["state"] in EDITABLE,
        "deletable": row["state"] in DELETABLE,
        "exportable": row["state"] in EXPORTABLE,
        "executable": False,
        "transmitted": False,
        "warnings": validate(conn, row, lines),
    }
    newest = evaluations[0] if evaluations else None
    stale, why = evaluation_freshness(conn, operator, draft, newest)
    draft["evaluation_stale"] = stale
    draft["evaluation_stale_reason"] = why
    return draft


# ── validation ────────────────────────────────────────────────────────────────

def validate(conn: Any, head: dict[str, Any], lines: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Things a buyer should see before approving. Warnings, never prohibitions."""
    out: list[dict[str, str]] = []
    if not lines:
        out.append({"level": "warn", "message": "This proposal has no lines yet."})
    seen: dict[str, int] = {}
    for line in lines:
        sku = str(line.get("sku"))
        seen[sku] = seen.get(sku, 0) + 1
    for sku, count in seen.items():
        if count > 1:
            out.append({"level": "warn", "message": f"{sku} appears on {count} lines. Most systems expect one line per product."})

    if not has_table(conn, "stg_fmcg_skus"):
        return out
    master = {str(r["sku"]): r for r in _rows(
        conn, f"""SELECT sku, any_value(units_per_case) AS units_per_case, any_value(moq_units) AS moq_units,
                         any_value(supplier_id) AS supplier_id, any_value(unit_cost) AS unit_cost
                  FROM stg_fmcg_skus WHERE sku IN ({', '.join('?' for _ in lines) or 'NULL'}) GROUP BY sku""",  # nosec B608 - code literals plus allowlisted names (DRAFT_SORTS); values bind
        [str(x.get("sku")) for x in lines]) } if lines else {}
    for line in lines:
        sku = str(line.get("sku"))
        info = master.get(sku)
        quantity = float(line.get("quantity") or 0)
        if info is None:
            out.append({"level": "warn", "message": f"{sku} is not in your product master."})
            continue
        pack = line.get("units_per_case") or info.get("units_per_case")
        if pack and float(pack) > 0 and quantity % float(pack) != 0:
            whole = int(quantity // float(pack))
            out.append({"level": "warn", "message":
                        f"{sku}: {quantity:,.0f} units is not a whole number of cases of {float(pack):,.0f}. "
                        f"{whole * float(pack):,.0f} or {(whole + 1) * float(pack):,.0f} would be."})
        moq = info.get("moq_units")
        if moq and quantity < float(moq):
            out.append({"level": "warn", "message":
                        f"{sku}: {quantity:,.0f} units is below the minimum order quantity of {float(moq):,.0f} in your product master."})
        if head.get("supplier_id") and info.get("supplier_id") and str(info["supplier_id"]) != str(head["supplier_id"]):
            out.append({"level": "warn", "message":
                        f"{sku} is normally bought from {info['supplier_id']}, not {head['supplier_id']}."})

    supplier_id = head.get("supplier_id")
    if supplier_id and has_table(conn, "stg_fmcg_suppliers"):
        capacity = _one(conn, "SELECT any_value(capacity_per_week) FROM stg_fmcg_suppliers WHERE supplier_id = ?",
                        [supplier_id])
        units = sum(float(x.get("quantity") or 0) for x in lines)
        if capacity and units > float(capacity):
            out.append({"level": "warn", "message":
                        f"{units:,.0f} units is more than {supplier_id}'s declared weekly capacity of {float(capacity):,.0f}."})
    return out


# ── writing ───────────────────────────────────────────────────────────────────

def _check_lines(operator: str, draft_id: str, lines: list[dict[str, Any]]) -> list[list[Any]]:
    """Every line read and checked, none written. A refused line refuses the whole document."""
    if len(lines) > MAX_LINES:
        raise DraftRefused(f"A proposal carries at most {MAX_LINES} lines; this one has {len(lines)}.")
    checked: list[list[Any]] = []
    for index, raw in enumerate(lines, start=1):
        sku = _identifier(raw.get("sku"), f"Line {index} product code") or ""
        if not sku:
            raise DraftRefused(f"Line {index} has no product.")
        quantity = _number(raw.get("quantity"), f"Line {index} quantity", allow_none=False)
        assert quantity is not None
        if quantity <= 0:
            raise DraftRefused(f"Line {index}: a quantity must be more than zero. To remove a line, delete it.")
        price = _number(raw.get("unit_price"), f"Line {index} unit price")
        pack = _number(raw.get("units_per_case"), f"Line {index} units per case")
        for name, value in (("quantity", quantity), ("unit price", price), ("units per case", pack)):
            if value is not None and abs(value) > MAX_LINE_VALUE:
                raise DraftRefused(
                    f"Line {index}: {value:,.0f} is not a {name} ZAAD will store. "
                    f"The most it takes is {MAX_LINE_VALUE:,.0f}. Check for a typo or an extra zero.")
        checked.append([draft_id, operator, index, sku, quantity, price, pack,
                        _as_date(raw.get("requested_receipt_date"), f"Line {index} requested receipt date"),
                        (str(raw.get("notes"))[:MAX_NOTE] if raw.get("notes") else None)])
    return checked


def _store_lines(conn: Any, operator: str, draft_id: str, checked: list[list[Any]]) -> None:
    conn.execute("DELETE FROM zaad_draft_lines WHERE draft_id = ? AND operator_id = ?", [draft_id, operator])
    for row in checked:
        conn.execute(
            "INSERT INTO zaad_draft_lines (draft_id, operator_id, line_no, sku, quantity, unit_price, "
            "units_per_case, requested_receipt_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)


def _write_lines(conn: Any, operator: str, draft_id: str, lines: list[dict[str, Any]]) -> None:
    """Replace a proposal's lines.

    Every line is read and checked **before** the first row is removed. An earlier version deleted
    first and validated as it inserted, so one bad quantity in an edit left the proposal with no
    lines at all — a refused edit must change nothing.
    """
    _store_lines(conn, operator, draft_id, _check_lines(operator, draft_id, lines))


class _transaction:
    """BEGIN … COMMIT around a multi-statement write, rolled back on any error.

    A connection that is already inside a transaction (a caller's, or a test's) is left to that
    caller: the block then does nothing on enter and nothing on exit.
    """

    def __init__(self, conn: Any):
        self.conn = conn
        self.owned = False

    def __enter__(self):
        try:
            self.conn.begin()
            self.owned = True
        except Exception:  # noqa: BLE001 - already in a transaction, or a connection without one
            self.owned = False
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self.owned:
            return False
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        except Exception:  # noqa: BLE001 - nothing more to do than let the original error through
            pass
        return False


def record_event(conn: Any, operator: str, draft_id: str, event: str, revision: int | None, actor: str | None,
                 detail: str | None = None) -> None:
    """One row in the draft's history. Append-only: nothing in the product deletes an event."""
    _event(conn, operator, draft_id, event, revision, actor, detail)


def _event(conn: Any, operator: str, draft_id: str, event: str, revision: int | None, actor: str | None,
           detail: str | None = None) -> None:
    conn.execute(
        "INSERT INTO zaad_draft_events (draft_id, operator_id, happened_at, actor, event, revision, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", [draft_id, operator, _now(), actor, event, revision, detail])


def create_draft(conn: Any, operator: str, body: dict[str, Any], *, actor: str | None = None) -> str:
    """Store a new proposal. Every origin lands here."""
    ensure_tables(conn)
    origin = str(body.get("origin") or "MANUAL").upper()
    if origin not in ORIGINS:
        raise DraftRefused(f"Unknown origin {origin!r}. One of {', '.join(ORIGINS)}.")
    action = body.get("amendment_action")
    if action is not None:
        action = str(action).upper()
        if action not in AMENDMENT_ACTIONS:
            raise DraftRefused(f"{action!r} is not something ZAAD can do to an order. "
                               f"One of {', '.join(AMENDMENT_ACTIONS)}.")
    if origin == "IMPORTED_AMENDMENT":
        if not body.get("source_po_id"):
            raise DraftRefused("An amendment must say which order it changes.")
        if action is None:
            raise DraftRefused("An amendment must say what it does to the order.")
    ordered = _as_date(body.get("requested_order_date"), "Order date")
    receipt = _as_date(body.get("requested_receipt_date"), "Requested receipt date")
    if ordered and receipt and receipt < ordered:
        raise DraftRefused("The requested receipt date is before the order date.")

    draft_id = _identity()
    # Everything is checked before anything is written, and the writes are one transaction. The
    # head row used to be inserted first and the lines validated afterwards, so a refused line
    # left an empty proposal behind — four of them appeared on Home in the V1 audit.
    head = [
        draft_id, operator, origin, int(body.get("revision") or 1),
        (str(body.get("reference"))[:120] if body.get("reference") else None),
        _identifier(body.get("supplier_id"), "Supplier code"),
        _identifier(body.get("destination_id"), "Deliver to"),
        (str(body.get("currency") or "")[:3].upper() or None),
        ordered, receipt,
        (str(body.get("notes"))[:MAX_NOTE] if body.get("notes") else None),
        _identifier(body.get("source_decision_id"), "Source decision"),
        _identifier(body.get("source_po_id"), "The order this amends"),
        action, actor, _now(), _now(),
        _identifier(body.get("supersedes"), "The revision this replaces")]
    checked = _check_lines(operator, draft_id, list(body.get("lines") or []))
    with _transaction(conn):
        conn.execute("""
            INSERT INTO zaad_draft_orders
            (draft_id, operator_id, origin, state, revision, reference, supplier_id, destination_id, currency,
             requested_order_date, requested_receipt_date, notes, source_decision_id, source_po_id,
             amendment_action, created_by, created_at, updated_at, supersedes)
            VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", head)
        _store_lines(conn, operator, draft_id, checked)
        _event(conn, operator, draft_id, "created", 1, actor, f"origin {origin}")
    return draft_id


def update_draft(conn: Any, operator: str, draft_id: str, body: dict[str, Any], *,
                 actor: str | None = None) -> dict[str, Any]:
    """Edit a draft in place. Refused once a revision has been approved, rejected or exported."""
    ensure_tables(conn)
    current = _rows(conn, "SELECT * FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?",
                    [draft_id, operator])
    if not current:
        raise KeyError(draft_id)
    row = current[0]
    if row["state"] == "READY_FOR_REVIEW":
        raise DraftRefused("This proposal is with a reviewer. Return it to draft before changing it.")
    if row["state"] in IMMUTABLE:
        raise DraftRefused(f"{_said(row['state']).capitalize()} proposal is a record of what was decided "
                           "and does not change. Create the next revision instead.")

    fields: list[str] = []
    params: list[Any] = []
    for column, label in (("reference", "Your reference"), ("supplier_id", "Supplier code"),
                          ("destination_id", "Deliver to"), ("currency", "Currency"), ("notes", "Notes")):
        if column in body:
            value = body[column]
            fields.append(f"{column} = ?")
            if column == "notes":
                params.append(None if value in (None, "") else str(value)[:MAX_NOTE])
            elif column == "reference":
                params.append(None if value in (None, "") else str(value)[:120])
            elif column == "currency":
                params.append(None if value in (None, "") else str(value)[:3].upper())
            else:
                params.append(_identifier(value, label))
    if "requested_order_date" in body:
        fields.append("requested_order_date = ?")
        params.append(_as_date(body["requested_order_date"], "Order date"))
    if "requested_receipt_date" in body:
        fields.append("requested_receipt_date = ?")
        params.append(_as_date(body["requested_receipt_date"], "Requested receipt date"))
    if "amendment_action" in body and body["amendment_action"] is not None:
        action = str(body["amendment_action"]).upper()
        if action not in AMENDMENT_ACTIONS:
            raise DraftRefused(f"{action!r} is not something ZAAD can do to an order.")
        fields.append("amendment_action = ?")
        params.append(action)
    fields.append("updated_at = ?")
    params.append(_now())
    # nosec B608 - every column name above is a literal in this function
    conn.execute(f"UPDATE zaad_draft_orders SET {', '.join(fields)} WHERE draft_id = ? AND operator_id = ?",  # noqa: S608  # nosec B608 - code literals plus allowlisted names (DRAFT_SORTS); values bind
                 [*params, draft_id, operator])
    if "lines" in body:
        _write_lines(conn, operator, draft_id, list(body["lines"] or []))
    _event(conn, operator, draft_id, "edited", int(row["revision"] or 1), actor)
    return read_draft(conn, operator, draft_id)


def latest_evaluation(conn: Any, operator: str, draft_id: str) -> dict[str, Any] | None:
    rows = _rows(conn, "SELECT * FROM zaad_evaluations WHERE draft_id = ? AND operator_id = ? "
                       "ORDER BY created_at DESC LIMIT 1", [draft_id, operator])
    return rows[0] if rows else None


def evaluation_freshness(conn: Any, operator: str, draft: dict[str, Any], record: dict[str, Any] | None
                         ) -> tuple[bool, str | None]:
    """(stale, reason) for the newest evaluation of a draft, decided deterministically.

    A record carrying `draft_hash` is compared with the hash of what the draft holds now, and its
    `workspace_version` with the workspace's now. A record written before those existed falls back
    to the one thing the timestamp rule can tell truthfully: whether an *edit* — not an approval,
    a rejection or an export — happened after it.
    """
    from api.product.evaluation import content_hash, workspace_version

    if record is None:
        return False, None
    if record.get("draft_hash"):
        if record["draft_hash"] != content_hash(draft):
            return True, ("This proposal was changed after it was evaluated, so the comparison describes "
                          "the order as it was, not as it is now. Evaluate it again to compare what you have.")
        if record.get("workspace_version") and record["workspace_version"] != workspace_version(conn):
            return True, ("Your workspace data was replaced or added to after this evaluation ran, so the "
                          "comparison was built from data ZAAD no longer holds. Evaluate it again.")
        return False, None
    evaluated_at = record.get("created_at")
    edited_after = _rows(conn, "SELECT 1 FROM zaad_draft_events WHERE draft_id = ? AND operator_id = ? "
                               "AND event = 'edited' AND happened_at > ? LIMIT 1",
                         [draft["draft_id"], operator, evaluated_at]) if evaluated_at else []
    if edited_after:
        return True, ("This proposal was changed after it was evaluated, so the comparison describes "
                      "the order as it was, not as it is now. Evaluate it again to compare what you have.")
    return False, None


def delete_draft(conn: Any, operator: str, draft_id: str, *, actor: str | None = None) -> None:
    """Remove a draft. Only a draft: an approved or exported revision is history."""
    ensure_tables(conn)
    current = _rows(conn, "SELECT state FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?",
                    [draft_id, operator])
    if not current:
        raise KeyError(draft_id)
    if current[0]["state"] not in DELETABLE:
        raise DraftRefused(f"{_said(current[0]['state']).capitalize()} proposal is part of the record "
                           "and cannot be deleted.")
    conn.execute("DELETE FROM zaad_draft_lines WHERE draft_id = ? AND operator_id = ?", [draft_id, operator])
    conn.execute("DELETE FROM zaad_draft_events WHERE draft_id = ? AND operator_id = ?", [draft_id, operator])
    conn.execute("DELETE FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?", [draft_id, operator])


TRANSITIONS: dict[str, tuple[str, ...]] = {
    "submit": ("DRAFT",),
    "reopen": ("READY_FOR_REVIEW", "REJECTED"),
    "approve": ("DRAFT", "READY_FOR_REVIEW"),
    "reject": ("DRAFT", "READY_FOR_REVIEW"),
}
TO_STATE = {"submit": "READY_FOR_REVIEW", "reopen": "DRAFT", "approve": "APPROVED", "reject": "REJECTED"}


def transition(conn: Any, operator: str, draft_id: str, action: str, *, actor: str | None = None,
               reason: str | None = None, acknowledge_stale: bool = False) -> dict[str, Any]:
    """Move a proposal through its lifecycle. Approval is recorded with who, why, and against what.

    An approval names the evaluation it was made against and whether that evaluation was current.
    Approving over a stale comparison is refused unless the approver acknowledges it — and the
    acknowledgement is part of the record, so a reviewer later can see the approver knew.
    """
    ensure_tables(conn)
    if action not in TRANSITIONS:
        raise DraftRefused(f"Unknown action {action!r}")
    current = _rows(conn, "SELECT * FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?",
                    [draft_id, operator])
    if not current:
        raise KeyError(draft_id)
    row = current[0]
    if row["state"] not in TRANSITIONS[action]:
        raise DraftRefused(f"{_said(row['state']).capitalize()} proposal cannot be "
                           f"{ {'submit': 'sent for review', 'reopen': 'returned to draft', 'approve': 'approved', 'reject': 'rejected'}[action] }.")
    if action in ("approve", "reject") and not (reason or "").strip():
        raise DraftRefused("Record why. An approval without a reason is not a decision anyone can review later.")

    evaluation_state: str | None = None
    evaluation_ref: str | None = None
    if action == "approve":
        draft = read_draft(conn, operator, draft_id)
        record = latest_evaluation(conn, operator, draft_id)
        if record is None:
            evaluation_state = "none"
        else:
            evaluation_ref = str(record["evaluation_id"])
            stale, _why = evaluation_freshness(conn, operator, draft, record)
            if stale and not acknowledge_stale:
                raise EvaluationStale(
                    "The comparison on this proposal is out of date — it describes the order as it was "
                    "when it was evaluated, not as it is now. Evaluate it again, or approve it knowing that "
                    "and say so.")
            evaluation_state = "stale_acknowledged" if stale else "current"

    state = TO_STATE[action]
    stamp = _now()
    conn.execute(
        "UPDATE zaad_draft_orders SET state = ?, updated_at = ?, approved_by = ?, approved_at = ?, "
        "decision_reason = ?, approved_evaluation_id = ?, approval_evaluation_state = ? "
        "WHERE draft_id = ? AND operator_id = ?",
        [state, stamp, actor if action in ("approve", "reject") else row.get("approved_by"),
         stamp if action in ("approve", "reject") else row.get("approved_at"),
         (reason or "").strip()[:MAX_NOTE] or row.get("decision_reason"),
         evaluation_ref if action == "approve" else row.get("approved_evaluation_id"),
         evaluation_state if action == "approve" else row.get("approval_evaluation_state"),
         draft_id, operator])
    detail = (reason or "").strip()[:MAX_NOTE] or None
    if action == "approve":
        against = {"none": "without an evaluation", "current": f"against evaluation {evaluation_ref} (current)",
                   "stale_acknowledged": f"against evaluation {evaluation_ref} (out of date — acknowledged)"}[evaluation_state or "none"]
        detail = f"{detail} — {against}" if detail else against
    _event(conn, operator, draft_id, {"submit": "submitted", "reopen": "reopened",
                                      "approve": "approved", "reject": "rejected"}[action],
           int(row["revision"] or 1), actor, detail)
    return read_draft(conn, operator, draft_id)


def revise(conn: Any, operator: str, draft_id: str, *, actor: str | None = None) -> str:
    """The next revision of a proposal that is already part of the record.

    The old row is left exactly as it was decided and marked superseded; the new one starts as a
    draft, carries the same lines, and records what it replaces.
    """
    ensure_tables(conn)
    current = _rows(conn, "SELECT * FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?",
                    [draft_id, operator])
    if not current:
        raise KeyError(draft_id)
    row = current[0]
    if row["state"] == "SUPERSEDED":
        raise DraftRefused("This revision has already been replaced.")
    lines = _rows(conn, "SELECT * FROM zaad_draft_lines WHERE draft_id = ? AND operator_id = ? ORDER BY line_no",
                  [draft_id, operator])
    new_id = create_draft(conn, operator, {
        "origin": row["origin"], "revision": int(row["revision"] or 1) + 1, "reference": row.get("reference"),
        "supplier_id": row.get("supplier_id"), "destination_id": row.get("destination_id"),
        "currency": row.get("currency"), "requested_order_date": row.get("requested_order_date"),
        "requested_receipt_date": row.get("requested_receipt_date"), "notes": row.get("notes"),
        "source_decision_id": row.get("source_decision_id"), "source_po_id": row.get("source_po_id"),
        "amendment_action": row.get("amendment_action"), "supersedes": draft_id,
        "lines": [{k: line.get(k) for k in ("sku", "quantity", "unit_price", "units_per_case",
                                            "requested_receipt_date", "notes")} for line in lines],
    }, actor=actor)
    conn.execute("UPDATE zaad_draft_orders SET state = 'SUPERSEDED', superseded_by = ?, updated_at = ? "
                 "WHERE draft_id = ? AND operator_id = ?", [new_id, _now(), draft_id, operator])
    _event(conn, operator, draft_id, "superseded", int(row["revision"] or 1), actor, f"replaced by {new_id}")
    return new_id


# ── the four ways in ──────────────────────────────────────────────────────────

def from_recommendation(
    conn: Any, operator: str, *, supplier_id: str | None, destination_id: str | None,
    lines: list[dict[str, Any]], decision_id: str | None, currency: str | None,
    requested_receipt_date: str | None = None, actor: str | None = None, notes: str | None = None,
) -> str:
    """A proposal from what ZAAD recommended. The quantities come from the report, unchanged."""
    return create_draft(conn, operator, {
        "origin": "ZAAD_RECOMMENDATION", "supplier_id": supplier_id, "destination_id": destination_id,
        "currency": currency, "source_decision_id": decision_id, "lines": lines,
        "requested_order_date": _now().date().isoformat(), "requested_receipt_date": requested_receipt_date,
        "notes": notes or "Created from a ZAAD recommendation. Quantities are the report's; edit before approving.",
    }, actor=actor)


def from_amendment(
    conn: Any, operator: str, *, source_po_id: str, action: str, lines: list[dict[str, Any]],
    supplier_id: str | None, decision_id: str | None = None, requested_receipt_date: str | None = None,
    actor: str | None = None, notes: str | None = None,
) -> str:
    """A proposed change to an order that already exists in the operator's system.

    The imported rows are not touched. This proposal points at them and says what should change.
    """
    return create_draft(conn, operator, {
        "origin": "IMPORTED_AMENDMENT", "source_po_id": source_po_id, "amendment_action": action.upper(),
        "supplier_id": supplier_id, "lines": lines, "source_decision_id": decision_id,
        "requested_order_date": _now().date().isoformat(), "requested_receipt_date": requested_receipt_date,
        "notes": notes,
    }, actor=actor)


# ── export profiles ───────────────────────────────────────────────────────────

def list_profiles(conn: Any, operator: str) -> list[dict[str, Any]]:
    ensure_tables(conn)
    rows = _rows(conn, "SELECT * FROM zaad_export_profiles WHERE operator_id = ? ORDER BY name", [operator])
    for row in rows:
        row["columns"] = json.loads(row["columns"]) if row.get("columns") else []
    return rows


def save_profile(conn: Any, operator: str, body: dict[str, Any], *, profile_id: str | None = None) -> str:
    """Store a company's own import format. The field vocabulary is checked before it is saved."""
    from api.product.exporting import EXPORT_FIELDS, FORMATS

    ensure_tables(conn)
    name = str(body.get("name") or "").strip()
    if not name:
        raise DraftRefused("Give the format a name, so a buyer can pick it later.")
    fmt = str(body.get("format") or "csv").lower()
    if fmt not in FORMATS:
        raise DraftRefused(f"{fmt!r} is not a format ZAAD writes. One of {', '.join(FORMATS)}.")
    columns = list(body.get("columns") or [])
    if not columns:
        raise DraftRefused("A format needs at least one column.")
    if len(columns) > 80:
        raise DraftRefused("A format carries at most 80 columns.")
    cleaned: list[dict[str, Any]] = []
    for index, column in enumerate(columns, start=1):
        header = str(column.get("header") or "").strip()
        if not header:
            raise DraftRefused(f"Column {index} has no heading.")
        field = column.get("field")
        constant = column.get("constant")
        if field:
            if field not in EXPORT_FIELDS:
                raise DraftRefused(f"Column {index} ({header}) maps to {field!r}, which ZAAD does not hold. "
                                   f"Choose one of: {', '.join(sorted(EXPORT_FIELDS))}.")
        elif constant is None:
            raise DraftRefused(f"Column {index} ({header}) needs either a ZAAD field or a fixed value.")
        cleaned.append({"header": header[:120], "field": field,
                        "constant": (str(constant)[:200] if constant is not None else None)})
    identity = profile_id or f"profile_{uuid.uuid4().hex[:12]}"
    existing = _rows(conn, "SELECT profile_id FROM zaad_export_profiles WHERE profile_id = ? AND operator_id = ?",
                     [identity, operator]) if profile_id else []
    if profile_id and not existing:
        raise KeyError(profile_id)   # an update names a format this workspace holds; it does not invent one
    values = [name[:120], fmt, (str(body.get("sheet_name") or "Purchase Order")[:60]),
              (str(body.get("delimiter") or ",")[:1]), str(body.get("date_format") or "iso"),
              str(body.get("number_format") or "plain"),
              (str(body.get("filename_template") or "{reference}_{supplier}_{date}")[:160]),
              (str(body["supplier_id"]) if body.get("supplier_id") else None),
              json.dumps(cleaned), _now()]
    if existing:
        conn.execute("UPDATE zaad_export_profiles SET name = ?, format = ?, sheet_name = ?, delimiter = ?, "
                     "date_format = ?, number_format = ?, filename_template = ?, supplier_id = ?, columns = ?, "
                     "updated_at = ? WHERE profile_id = ? AND operator_id = ?", [*values, identity, operator])
    else:
        conn.execute("INSERT INTO zaad_export_profiles (profile_id, operator_id, name, format, sheet_name, "
                     "delimiter, date_format, number_format, filename_template, supplier_id, columns, "
                     "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [identity, operator, *values[:-1], _now(), values[-1]])
    return identity


def delete_profile(conn: Any, operator: str, profile_id: str) -> None:
    ensure_tables(conn)
    found = _rows(conn, "SELECT profile_id FROM zaad_export_profiles WHERE profile_id = ? AND operator_id = ?",
                  [profile_id, operator])
    if not found:
        raise KeyError(profile_id)
    conn.execute("DELETE FROM zaad_export_profiles WHERE profile_id = ? AND operator_id = ?",
                 [profile_id, operator])


def record_export(conn: Any, operator: str, draft_id: str, *, revision: int | None, profile_id: str | None,
                  profile_name: str, fmt: str, filename: str, actor: str | None) -> None:
    """Exporting is not transmitting. It is recorded so the workspace knows a file left the building."""
    ensure_tables(conn)
    conn.execute("INSERT INTO zaad_export_log (export_id, operator_id, draft_id, revision, profile_id, "
                 "profile_name, format, filename, actor, happened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 [f"export_{uuid.uuid4().hex[:12]}", operator, draft_id, revision, profile_id,
                  profile_name, fmt, filename, actor, _now()])
    state = _rows(conn, "SELECT state, revision FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?",
                  [draft_id, operator])
    if state and state[0]["state"] == "APPROVED":
        conn.execute("UPDATE zaad_draft_orders SET state = 'EXPORTED', updated_at = ? "
                     "WHERE draft_id = ? AND operator_id = ?", [_now(), draft_id, operator])
    _event(conn, operator, draft_id, "exported", revision, actor, f"{profile_name} ({fmt})")


StateName = Literal["DRAFT", "READY_FOR_REVIEW", "APPROVED", "REJECTED", "EXPORTED", "SUPERSEDED"]
