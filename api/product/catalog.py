"""Operational projections over the operator's own vault: inventory, products, orders, search.

Why these exist at all: the canonical planning contract is *compact by design*. It carries the
bounded selection of products a solve covers and nothing else — no descriptions, no brands, no
receipt history, no site-level stock breakdown. A distributor with 10,000 products needs to find
one of them in a second, and the planning contract is the wrong instrument for that.

So this module answers the operational questions directly from the staging tables, server-side and
paged. Three rules hold everywhere in it:

  * **Arithmetic only.** On-hand times unit cost is inventory value. On-hand divided by average
    weekly demand is weeks of cover. Neither is a judgement, and neither pretends to be an
    optimizer output. Anything the engine decides (protect, buy, defer, allocate) is read from the
    report, never recomputed here.
  * **A missing number stays missing.** No column is defaulted to zero to make a table look full.
    `None` travels to the interface, which says "Not available".
  * **Nothing is attributed that cannot be.** A receipt that does not name a product can only be
    matched to an order line when the order has one line; otherwise the received quantity is
    reported as unattributed rather than spread across lines.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_ROWS = 200
DEFAULT_ROWS = 50
#: A selection of products the caller names (for example "only what the last plan covered").
MAX_SKU_FILTER = 400

INVENTORY_SORTS = {
    "sku": '"sku"', "sku_name": '"sku_name"', "brand": '"brand"', "category": '"category"',
    "supplier_id": '"supplier_id"', "on_hand": "on_hand", "inbound_units": "inbound_units",
    "inventory_value": "inventory_value", "weekly_demand": "weekly_demand",
    "cover_weeks": "cover_weeks", "unit_cost": '"unit_cost"', "open_pos": "open_pos",
    "shelf_life_days": '"shelf_life_days"',
}

COVER_BUCKETS = {
    "out": "on_hand IS NOT NULL AND on_hand <= 0",
    "under2": "cover_weeks IS NOT NULL AND cover_weeks < 2",
    "under4": "cover_weeks IS NOT NULL AND cover_weeks < 4",
    "over12": "cover_weeks IS NOT NULL AND cover_weeks > 12",
    "unknown": "cover_weeks IS NULL",
}


class CatalogRefused(ValueError):
    """A name in the request is not one this module serves."""


def has_table(conn: Any, table: str) -> bool:
    try:
        conn.execute(f'SELECT 1 FROM "{table}" LIMIT 0')  # noqa: S608 - literal call sites only
        return True
    except Exception:  # noqa: BLE001 - a vault without this upload
        return False


def _columns(conn: Any, table: str) -> set[str]:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}
    except Exception:  # noqa: BLE001
        return set()


def _rows(conn: Any, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    cursor = conn.execute(sql, params or [])
    names = [c[0] for c in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _one(conn: Any, sql: str, params: list[Any] | None = None) -> Any:
    got = conn.execute(sql, params or []).fetchone()
    return got[0] if got else None


def _optional(conn: Any, table: str, column: str, fallback: str = "NULL") -> str:
    """`column` when the vault has it, else a literal, so a pre-migration vault still answers."""
    return f'"{column}"' if column in _columns(conn, table) else fallback


# ── shared SQL fragments ──────────────────────────────────────────────────────
#
# Every fragment below is a code literal. Nothing from a request is ever interpolated into one:
# request values travel as bound parameters, and request *names* are looked up in the dictionaries
# above before they are used.

def _stock_cte(conn: Any) -> str:
    """Latest uploaded stock snapshot, matching what the planning adapter reads.

    The adapter takes the most recent snapshot date the vault holds and uses the rows on it. Using
    the same rule here means the stock a person sees in Inventory is the stock the optimizer
    planned with, rather than a second, slightly different number.
    """
    if not has_table(conn, "stg_fmcg_inventory"):
        return "stock AS (SELECT NULL AS sku, NULL AS on_hand, NULL AS in_transit, NULL AS sites WHERE FALSE)"
    return """
    snap_day AS (SELECT max(snapshot_date) AS d FROM stg_fmcg_inventory),
    stock AS (
      SELECT sku,
             sum(on_hand) AS on_hand,
             sum(coalesce(in_transit, 0)) AS in_transit,
             count(DISTINCT location_id) AS sites
      FROM (SELECT sku, location_id, on_hand, in_transit,
                   row_number() OVER (PARTITION BY sku, location_id ORDER BY imported_at DESC) AS rn
            FROM stg_fmcg_inventory WHERE snapshot_date = (SELECT d FROM snap_day))
      WHERE rn = 1 GROUP BY sku)
    """


def _open_po_cte(conn: Any) -> str:
    """Units still owed on open purchase orders, per product.

    **An order is open until its first receipt is recorded.** That is the planning adapter's own
    rule — `zaad/full/workspace.py` drops an order the moment a receipt lands before the plan date,
    and carries the rest as pipeline — and this module follows it exactly so that the inbound units
    a person reads in Inventory are the inbound units the optimizer planned with. A short delivery
    therefore closes the order at the quantity that arrived; it does not leave a permanent sliver
    open on every order a supplier ever under-shipped.

    A receipt is matched to an order line by (po_id, sku) when the receipt names a product. When it
    does not, it can only be attributed if the order has a single line — otherwise the line's
    received quantity is unknown and it is reported as unattributed rather than guessed.
    """
    if not has_table(conn, "stg_fmcg_purchase_orders"):
        return "open_po AS (SELECT NULL AS sku, NULL AS inbound_units, NULL AS open_pos WHERE FALSE)"
    receipts = has_table(conn, "stg_fmcg_receipts")
    recv = """
    recv_line AS (SELECT po_id, sku, sum(qty_received) AS q, min(receipt_date) AS first_receipt
                  FROM stg_fmcg_receipts WHERE sku IS NOT NULL GROUP BY 1, 2),
    recv_po   AS (SELECT po_id, sum(qty_received) AS q, min(receipt_date) AS first_receipt
                  FROM stg_fmcg_receipts GROUP BY 1),
    """ if receipts else """
    recv_line AS (SELECT NULL AS po_id, NULL AS sku, NULL AS q, NULL AS first_receipt WHERE FALSE),
    recv_po   AS (SELECT NULL AS po_id, NULL AS q, NULL AS first_receipt WHERE FALSE),
    """
    return recv + """
    po_line AS (
      SELECT po_id, sku, sum(qty_ordered) AS ordered, min(po_date) AS po_date,
             min(expected_delivery_date) AS eta, any_value(supplier_id) AS supplier_id,
             count(*) OVER (PARTITION BY po_id) AS lines_on_po
      FROM stg_fmcg_purchase_orders GROUP BY po_id, sku),
    po_state AS (
      SELECT l.po_id, l.sku, l.ordered, l.po_date, l.eta, l.supplier_id,
             coalesce(rl.q, CASE WHEN l.lines_on_po = 1 THEN rp.q END) AS received,
             coalesce(rl.first_receipt, rp.first_receipt) AS first_receipt,
             (rl.q IS NULL AND l.lines_on_po > 1 AND rp.q IS NOT NULL) AS received_unattributed,
             CASE WHEN coalesce(rl.first_receipt, rp.first_receipt) IS NULL THEN l.ordered ELSE 0 END AS open_units
      FROM po_line l
      LEFT JOIN recv_line rl ON rl.po_id = l.po_id AND rl.sku = l.sku
      LEFT JOIN recv_po rp ON rp.po_id = l.po_id),
    open_po AS (
      SELECT sku, sum(open_units) AS inbound_units,
             count(*) FILTER (WHERE open_units > 0) AS open_pos
      FROM po_state GROUP BY sku)
    """


def _demand_cte(conn: Any, weeks: int = 12) -> str:
    """Average weekly customer demand over the most recent `weeks` weeks of order history."""
    if not has_table(conn, "stg_fmcg_orders"):
        return "demand AS (SELECT NULL AS sku, NULL AS weekly_demand WHERE FALSE)"
    return f"""
    demand AS (
      SELECT sku, sum(qty_ordered) / {weeks}.0 AS weekly_demand
      FROM stg_fmcg_orders
      WHERE order_date > (SELECT max(order_date) FROM stg_fmcg_orders) - INTERVAL {weeks * 7} DAY
      GROUP BY sku)
    """


@dataclass(frozen=True)
class InventoryPage:
    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    sort: str
    direction: str
    snapshot_date: str | None
    demand_weeks: int
    served: bool
    note: str | None = None


def inventory_page(
    conn: Any,
    *,
    search: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    supplier_id: str | None = None,
    abc_class: str | None = None,
    cover: str | None = None,
    skus: list[str] | None = None,
    sort: str = "sku",
    direction: str = "asc",
    limit: int = DEFAULT_ROWS,
    offset: int = 0,
) -> InventoryPage:
    """One page of the product catalogue with its stock position. Server-side, always bounded."""
    if not has_table(conn, "stg_fmcg_skus"):
        return InventoryPage([], 0, limit, offset, sort, direction, None, 12, served=False,
                             note="No product master has been uploaded yet.")
    if sort not in INVENTORY_SORTS:
        raise CatalogRefused(f"Cannot sort inventory on {sort!r}")
    if cover is not None and cover not in COVER_BUCKETS:
        raise CatalogRefused(f"Unknown cover filter {cover!r}")
    limit = max(1, min(int(limit), MAX_ROWS))
    offset = max(0, int(offset))
    direction_sql = "DESC" if str(direction).lower() == "desc" else "ASC"

    sku_cols = _columns(conn, "stg_fmcg_skus")
    brand_col = _optional(conn, "stg_fmcg_skus", "brand", "CAST(NULL AS VARCHAR)")
    sub_col = _optional(conn, "stg_fmcg_skus", "sub_category", "CAST(NULL AS VARCHAR)")
    supplier_name = (
        "(SELECT any_value(s.supplier_name) FROM stg_fmcg_suppliers s WHERE s.supplier_id = m.supplier_id)"
        if has_table(conn, "stg_fmcg_suppliers") and "supplier_name" in _columns(conn, "stg_fmcg_suppliers")
        else "CAST(NULL AS VARCHAR)")

    where: list[str] = []
    params: list[Any] = []
    if search and search.strip():
        needle = f"%{search.strip()}%"
        targets = ['CAST(m."sku" AS VARCHAR)']
        if "sku_name" in sku_cols:
            targets.append('CAST(m."sku_name" AS VARCHAR)')
        if "brand" in sku_cols:
            targets.append('CAST(m."brand" AS VARCHAR)')
        if "category" in sku_cols:
            targets.append('CAST(m."category" AS VARCHAR)')
        where.append("(" + " OR ".join(f"{t} ILIKE ?" for t in targets) + ")")
        params.extend([needle] * len(targets))
    for column, value in (("category", category), ("brand", brand), ("supplier_id", supplier_id),
                          ("abc_class", abc_class)):
        if value is None:
            continue
        if column not in sku_cols:
            raise CatalogRefused(f"The product master does not declare {column!r}")
        where.append(f'CAST(m."{column}" AS VARCHAR) = ?')
        params.append(value)
    if skus:
        chosen = [s for s in skus if s][:MAX_SKU_FILTER]
        if not chosen:
            chosen = ["\x00"]
        where.append(f'm."sku" IN ({", ".join("?" for _ in chosen)})')
        params.extend(chosen)
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    having = f" WHERE {COVER_BUCKETS[cover]}" if cover else ""

    body = f"""
    WITH {_stock_cte(conn)}, {_open_po_cte(conn)}, {_demand_cte(conn)},
    base AS (
      SELECT m."sku" AS sku,
             {_optional(conn, 'stg_fmcg_skus', 'sku_name', 'CAST(NULL AS VARCHAR)')} AS sku_name,
             {brand_col} AS brand,
             {_optional(conn, 'stg_fmcg_skus', 'category', 'CAST(NULL AS VARCHAR)')} AS category,
             {sub_col} AS sub_category,
             {_optional(conn, 'stg_fmcg_skus', 'supplier_id', 'CAST(NULL AS VARCHAR)')} AS supplier_id,
             {supplier_name} AS supplier_name,
             {_optional(conn, 'stg_fmcg_skus', 'unit_cost')} AS unit_cost,
             {_optional(conn, 'stg_fmcg_skus', 'unit_price')} AS unit_price,
             {_optional(conn, 'stg_fmcg_skus', 'units_per_case')} AS units_per_case,
             {_optional(conn, 'stg_fmcg_skus', 'moq_units')} AS moq_units,
             {_optional(conn, 'stg_fmcg_skus', 'shelf_life_days')} AS shelf_life_days,
             {_optional(conn, 'stg_fmcg_skus', 'abc_class', 'CAST(NULL AS VARCHAR)')} AS abc_class,
             st.on_hand AS on_hand, st.in_transit AS in_transit, st.sites AS sites,
             po.inbound_units AS inbound_units, po.open_pos AS open_pos,
             d.weekly_demand AS weekly_demand
      FROM (SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY "sku" ORDER BY imported_at DESC) AS _rn
                           FROM stg_fmcg_skus) WHERE _rn = 1) m
      LEFT JOIN stock st ON st.sku = m."sku"
      LEFT JOIN open_po po ON po.sku = m."sku"
      LEFT JOIN demand d ON d.sku = m."sku"
      {clause}),
    shaped AS (
      SELECT *,
             CASE WHEN unit_cost IS NOT NULL AND on_hand IS NOT NULL THEN on_hand * unit_cost END AS inventory_value,
             CASE WHEN weekly_demand IS NOT NULL AND weekly_demand > 0 AND on_hand IS NOT NULL
                  THEN on_hand / weekly_demand END AS cover_weeks
      FROM base)
    SELECT * FROM shaped{having}
    """
    sql = f'{body} ORDER BY {INVENTORY_SORTS[sort]} {direction_sql} NULLS LAST LIMIT ? OFFSET ?'
    rows = _rows(conn, sql, [*params, limit, offset])
    total = int(_one(conn, f"WITH counted AS ({body}) SELECT count(*) FROM counted", params) or 0)
    day = _one(conn, "SELECT max(snapshot_date) FROM stg_fmcg_inventory") if has_table(conn, "stg_fmcg_inventory") else None
    for row in rows:
        row.pop("_rn", None)
    return InventoryPage(rows, total, limit, offset, sort, direction_sql.lower(),
                         str(day) if day else None, 12, served=True)


def sku_detail(conn: Any, sku: str) -> dict[str, Any]:
    """Everything the vault holds about one product, for the detail panel."""
    if not has_table(conn, "stg_fmcg_skus"):
        raise CatalogRefused("No product master has been uploaded yet.")
    master = _rows(conn, 'SELECT * FROM stg_fmcg_skus WHERE "sku" = ? ORDER BY imported_at DESC LIMIT 1', [sku])
    if not master:
        raise KeyError(sku)
    page = inventory_page(conn, skus=[sku], limit=1)
    overview = page.rows[0] if page.rows else {"sku": sku}

    stock_by_site: list[dict[str, Any]] = []
    if has_table(conn, "stg_fmcg_inventory"):
        stock_by_site = _rows(conn, """
            SELECT location_id, on_hand, in_transit, snapshot_date FROM (
              SELECT location_id, on_hand, in_transit, snapshot_date,
                     row_number() OVER (PARTITION BY location_id ORDER BY snapshot_date DESC, imported_at DESC) AS rn
              FROM stg_fmcg_inventory WHERE sku = ?)
            WHERE rn = 1 ORDER BY location_id""", [sku])

    orders: list[dict[str, Any]] = []
    if has_table(conn, "stg_fmcg_purchase_orders"):
        receipts_join = ("LEFT JOIN (SELECT po_id, sum(qty_received) q, min(receipt_date) first_receipt "
                         "FROM stg_fmcg_receipts GROUP BY 1) r ON r.po_id = p.po_id"
                         if has_table(conn, "stg_fmcg_receipts") else
                         "LEFT JOIN (SELECT NULL po_id, NULL q, NULL first_receipt WHERE FALSE) r ON FALSE")
        orders = _rows(conn, f"""
            SELECT p.po_id, p.po_date, p.supplier_id, p.qty_ordered, p.unit_cost,
                   p.expected_delivery_date, r.q AS qty_received, r.first_receipt
            FROM stg_fmcg_purchase_orders p {receipts_join}
            WHERE p.sku = ? ORDER BY p.po_date DESC LIMIT 100""", [sku])

    demand: list[dict[str, Any]] = []
    shortfalls = None
    if has_table(conn, "stg_fmcg_orders"):
        demand = _rows(conn, """
            SELECT date_trunc('week', order_date) AS week,
                   sum(qty_ordered) AS ordered, sum(coalesce(qty_shipped, qty_ordered)) AS shipped
            FROM stg_fmcg_orders WHERE sku = ?
              AND order_date > (SELECT max(order_date) FROM stg_fmcg_orders) - INTERVAL 182 DAY
            GROUP BY 1 ORDER BY 1""", [sku])
        shortfalls = _one(conn, """
            SELECT count(*) FROM stg_fmcg_orders
            WHERE sku = ? AND qty_shipped IS NOT NULL AND qty_shipped < qty_ordered""", [sku])

    sources: list[dict[str, Any]] = []
    if has_table(conn, "stg_fmcg_sources"):
        sources = _rows(conn, "SELECT * FROM stg_fmcg_sources WHERE sku = ? ORDER BY supplier_id", [sku])

    missing: list[str] = []
    if not stock_by_site:
        missing.append("No stock snapshot has been uploaded for this product.")
    if not orders:
        missing.append("No purchase order history has been uploaded for this product.")
    if not demand:
        missing.append("No customer order history has been uploaded for this product.")
    if not sources:
        missing.append("No alternative source has been declared for this product.")

    return {
        "sku": sku,
        "master": master[0],
        "overview": overview,
        "stock_by_site": stock_by_site,
        "purchase_orders": orders,
        "demand_by_week": demand,
        "short_shipped_lines": shortfalls,
        "declared_sources": sources,
        "missing": missing,
        "provenance": "OPERATOR_UPLOADED",
    }


# ── purchase orders as the operator's system has them ─────────────────────────

PO_SORTS = {
    "po_id": "po_id", "po_date": "po_date", "supplier_id": "supplier_id",
    "expected_delivery_date": "eta", "ordered_units": "ordered_units",
    "open_units": "open_units", "value": "value", "lines": "lines",
}


def purchase_order_page(
    conn: Any,
    *,
    search: str | None = None,
    supplier_id: str | None = None,
    state: str | None = None,
    sort: str = "po_date",
    direction: str = "desc",
    limit: int = DEFAULT_ROWS,
    offset: int = 0,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Imported purchase orders, one row per order, with what is still owed on it.

    `state` is arithmetic, not a judgement: **open** means units are still owed, **received** means
    none are, **late** means units are still owed and the expected date has passed.
    """
    if not has_table(conn, "stg_fmcg_purchase_orders"):
        return {"rows": [], "total": 0, "limit": limit, "offset": offset, "served": False,
                "note": "No purchase orders have been uploaded yet."}
    if sort not in PO_SORTS:
        raise CatalogRefused(f"Cannot sort purchase orders on {sort!r}")
    if state not in (None, "open", "late", "received"):
        raise CatalogRefused(f"Unknown order state {state!r}")
    limit = max(1, min(int(limit), MAX_ROWS))
    offset = max(0, int(offset))
    direction_sql = "DESC" if str(direction).lower() == "desc" else "ASC"

    where: list[str] = []
    params: list[Any] = []
    if search and search.strip():
        needle = f"%{search.strip()}%"
        where.append('(CAST(po_id AS VARCHAR) ILIKE ? OR CAST(supplier_id AS VARCHAR) ILIKE ? OR CAST(sku AS VARCHAR) ILIKE ?)')
        params.extend([needle, needle, needle])
    if supplier_id:
        where.append("CAST(supplier_id AS VARCHAR) = ?")
        params.append(supplier_id)
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    state_clause = {
        None: "", "open": " WHERE open_units > 0",
        "received": " WHERE open_units <= 0",
        "late": " WHERE open_units > 0 AND eta IS NOT NULL AND eta < CAST(? AS DATE)",
    }[state]

    body = f"""
    WITH {_open_po_cte(conn)},
    filtered AS (SELECT * FROM stg_fmcg_purchase_orders{clause}),
    heads AS (
      SELECT po_id, min(po_date) AS po_date, any_value(supplier_id) AS supplier_id,
             min(expected_delivery_date) AS eta, count(*) AS lines,
             sum(qty_ordered) AS ordered_units,
             sum(qty_ordered * coalesce(unit_cost, 0)) AS value,
             bool_or(unit_cost IS NULL) AS value_incomplete
      FROM filtered GROUP BY po_id),
    owed AS (
      SELECT po_id, sum(open_units) AS open_units, min(first_receipt) AS first_receipt,
             sum(coalesce(received, 0)) AS received_units,
             bool_or(received_unattributed) AS received_unattributed
      FROM po_state GROUP BY po_id)
    SELECT h.*, coalesce(o.open_units, h.ordered_units) AS open_units,
           o.first_receipt, o.received_units,
           coalesce(o.received_unattributed, FALSE) AS received_unattributed
    FROM heads h LEFT JOIN owed o ON o.po_id = h.po_id
    """
    shaped = f"SELECT * FROM ({body}){state_clause}"
    state_params = [as_of] if state == "late" else []
    rows = _rows(conn, f"{shaped} ORDER BY {PO_SORTS[sort]} {direction_sql} NULLS LAST LIMIT ? OFFSET ?",
                 [*params, *state_params, limit, offset])
    total = int(_one(conn, f"SELECT count(*) FROM ({shaped})", [*params, *state_params]) or 0)
    return {"rows": rows, "total": total, "limit": limit, "offset": offset,
            "sort": sort, "direction": direction_sql.lower(), "served": True}


def purchase_order_detail(conn: Any, po_id: str) -> dict[str, Any]:
    """One imported order: its lines, its receipts and any amendment right declared against it."""
    if not has_table(conn, "stg_fmcg_purchase_orders"):
        raise CatalogRefused("No purchase orders have been uploaded yet.")
    lines = _rows(conn, "SELECT * FROM stg_fmcg_purchase_orders WHERE po_id = ? ORDER BY sku", [po_id])
    if not lines:
        raise KeyError(po_id)
    receipts = _rows(conn, "SELECT * FROM stg_fmcg_receipts WHERE po_id = ? ORDER BY receipt_date",
                     [po_id]) if has_table(conn, "stg_fmcg_receipts") else []
    options = _rows(conn, "SELECT * FROM stg_po_options WHERE po_id = ? ORDER BY option_id",
                    [po_id]) if has_table(conn, "stg_po_options") else []
    terms = _rows(conn, "SELECT * FROM stg_po_commitments WHERE po_id = ? LIMIT 1",
                  [po_id]) if has_table(conn, "stg_po_commitments") else []
    supplier = None
    supplier_id = lines[0].get("supplier_id")
    if supplier_id and has_table(conn, "stg_fmcg_suppliers"):
        found = _rows(conn, "SELECT * FROM stg_fmcg_suppliers WHERE supplier_id = ? LIMIT 1", [supplier_id])
        supplier = found[0] if found else None
    return {
        "po_id": po_id, "lines": lines, "receipts": receipts,
        "declared_options": options, "declared_terms": terms[0] if terms else None,
        "supplier": supplier,
        "amendment_rights_declared": bool(options),
        "provenance": "OPERATOR_UPLOADED",
    }


# ── the operating snapshot Home shows ─────────────────────────────────────────

def summary(conn: Any, *, as_of: str | None = None) -> dict[str, Any]:
    """Counts and totals a person recognises. Every one is a count or a sum, nothing derived."""
    out: dict[str, Any] = {"provenance": "OPERATOR_UPLOADED"}
    out["products"] = _one(conn, "SELECT count(DISTINCT sku) FROM stg_fmcg_skus") if has_table(conn, "stg_fmcg_skus") else None
    out["suppliers"] = _one(conn, "SELECT count(DISTINCT supplier_id) FROM stg_fmcg_suppliers") if has_table(conn, "stg_fmcg_suppliers") else None
    out["locations"] = _one(conn, "SELECT count(DISTINCT location_id) FROM stg_fmcg_locations") if has_table(conn, "stg_fmcg_locations") else None
    out["customers"] = _one(conn, "SELECT count(DISTINCT customer_id) FROM stg_fmcg_orders") if has_table(conn, "stg_fmcg_orders") else None

    if has_table(conn, "stg_fmcg_inventory"):
        snapshot = _one(conn, "SELECT max(snapshot_date) FROM stg_fmcg_inventory")
        out["snapshot_date"] = str(snapshot) if snapshot else None
        stock = _rows(conn, f"WITH {_stock_cte(conn)} SELECT sum(on_hand) AS units FROM stock")
        out["on_hand_units"] = stock[0]["units"] if stock else None
        value = _rows(conn, f"""
            WITH {_stock_cte(conn)}
            SELECT sum(st.on_hand * m.unit_cost) AS v,
                   count(*) FILTER (WHERE m.unit_cost IS NULL) AS unpriced
            FROM stock st LEFT JOIN (SELECT sku, any_value(unit_cost) AS unit_cost
                                     FROM stg_fmcg_skus GROUP BY sku) m ON m.sku = st.sku""")
        out["inventory_value"] = value[0]["v"] if value else None
        out["products_without_cost"] = value[0]["unpriced"] if value else None
    else:
        out["snapshot_date"] = None
        out["on_hand_units"] = None
        out["inventory_value"] = None

    if has_table(conn, "stg_fmcg_purchase_orders"):
        open_rows = _rows(conn, f"""
            WITH {_open_po_cte(conn)}
            SELECT count(DISTINCT po_id) FILTER (WHERE open_units > 0) AS open_orders,
                   sum(open_units) AS inbound_units
            FROM po_state""")
        out["open_purchase_orders"] = open_rows[0]["open_orders"] if open_rows else None
        out["inbound_units"] = open_rows[0]["inbound_units"] if open_rows else None
        if as_of:
            late = _rows(conn, f"""
                WITH {_open_po_cte(conn)}
                SELECT count(DISTINCT po_id) AS late FROM po_state
                WHERE open_units > 0 AND eta IS NOT NULL AND eta < CAST(? AS DATE)""", [as_of])
            out["late_purchase_orders"] = late[0]["late"] if late else None
    else:
        out["open_purchase_orders"] = None
        out["inbound_units"] = None

    if has_table(conn, "zaad_draft_orders"):
        out["proposals_awaiting_review"] = _one(
            conn, "SELECT count(*) FROM zaad_draft_orders WHERE state = 'READY_FOR_REVIEW'")
        out["proposals_open"] = _one(
            conn, "SELECT count(*) FROM zaad_draft_orders WHERE state IN ('DRAFT', 'READY_FOR_REVIEW')")
    return out


# ── search across everything a person might type ──────────────────────────────

def search_everything(conn: Any, q: str, limit: int = 8) -> list[dict[str, Any]]:
    """Server-side search. Every branch is bounded, so this stays fast at catalogue scale."""
    needle = q.strip()
    if not needle:
        return []
    like = f"%{needle}%"
    out: list[dict[str, Any]] = []
    if has_table(conn, "stg_fmcg_skus"):
        name = _optional(conn, "stg_fmcg_skus", "sku_name", "CAST(NULL AS VARCHAR)")
        brand = _optional(conn, "stg_fmcg_skus", "brand", "CAST(NULL AS VARCHAR)")
        for row in _rows(conn, f"""
                SELECT DISTINCT "sku" AS id, {name} AS label, {brand} AS detail FROM stg_fmcg_skus
                WHERE CAST("sku" AS VARCHAR) ILIKE ? OR CAST({name} AS VARCHAR) ILIKE ?
                ORDER BY id LIMIT ?""", [like, like, limit]):
            out.append({"kind": "product", "id": row["id"], "label": row["label"] or row["id"],
                        "detail": row["detail"], "href": f"/inventory?sku={row['id']}"})
    if has_table(conn, "stg_fmcg_suppliers"):
        for row in _rows(conn, """
                SELECT DISTINCT supplier_id AS id, supplier_name AS label, origin_iso3 AS detail
                FROM stg_fmcg_suppliers
                WHERE CAST(supplier_id AS VARCHAR) ILIKE ? OR CAST(supplier_name AS VARCHAR) ILIKE ?
                ORDER BY id LIMIT ?""", [like, like, limit]):
            out.append({"kind": "supplier", "id": row["id"], "label": row["label"] or row["id"],
                        "detail": row["detail"], "href": f"/diagnostics/supplier/{row['id']}"})
    if has_table(conn, "stg_fmcg_purchase_orders"):
        for row in _rows(conn, """
                SELECT DISTINCT po_id AS id, any_value(supplier_id) AS detail
                FROM stg_fmcg_purchase_orders WHERE CAST(po_id AS VARCHAR) ILIKE ?
                GROUP BY po_id ORDER BY id LIMIT ?""", [like, limit]):
            out.append({"kind": "order", "id": row["id"], "label": row["id"],
                        "detail": row["detail"], "href": f"/orders?po={row['id']}"})
    if has_table(conn, "stg_fmcg_orders"):
        for row in _rows(conn, """
                SELECT DISTINCT customer_id AS id FROM stg_fmcg_orders
                WHERE CAST(customer_id AS VARCHAR) ILIKE ? ORDER BY id LIMIT ?""", [like, limit]):
            out.append({"kind": "customer", "id": row["id"], "label": row["id"],
                        "detail": None, "href": f"/data?dataset=customer_orders&q={row['id']}"})
    return out
