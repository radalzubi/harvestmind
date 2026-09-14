"""Supplier and sector diagnostics, measured from the operator's own purchase and receipt history.

This module is the answer to a question a distributor asks every week — *why is this supplier
late?* — and the discipline it keeps is the reason it can be trusted:

  **OBSERVED FACT** — a count or a quantile over matched orders. "Arrived late on 31% of 58
  matched orders" is a fact about rows that exist.

  **ASSOCIATION** — where the lateness concentrates. "Nine of the eleven late arrivals were on
  two products" is an association, and it is labelled as one. It is not a cause.

  **SUPPORTED DRIVER** — only when event timestamps prove where the time went. The canonical
  upload carries an order date, a promised date and a receipt date, and nothing between them, so
  this release produces no supported drivers at all. That is stated, not hidden.

  **UNKNOWN** — everything else, named together with the fields that would settle it.

Everything is computed from `stg_fmcg_purchase_orders` and `stg_fmcg_receipts`. The legacy
HarvestMind produce tables (`stg_supplier_deliveries` and friends) are a different data family with
different row counts and different semantics; mixing them once produced a number nobody could
reconcile, so this module never reads them.
"""
from __future__ import annotations

from typing import Any

from api.product.catalog import _one, _rows, has_table

#: Below this share of the ordered quantity arriving, a delivery counts as short. A percent or two
#: is rounding on a case-packed order; four points is a shortfall an operator would notice. The
#: Network Twin's supplier colouring uses the same threshold, so one supplier never looks short in
#: one surface and fine in the other.
SHORT_FILL_TOLERANCE = 0.96

#: A quantile over fewer matched orders than this is arithmetic, not evidence; it is returned with
#: its sample size so the interface can say so rather than printing a confident-looking number.
THIN_SAMPLE = 6


def _count(value: Any) -> str:
    """A count inside a sentence, grouped the way the rest of the interface groups numbers.

    These statements are prose the backend writes, so the thousands separator has to be written
    with them — "1865 matched orders" next to a tile reading "1,865" is the same number twice in
    two styles.
    """
    return f"{int(value or 0):,}"


def _matched_cte() -> str:
    """Orders that have at least one receipt, with the three dates the vault actually carries."""
    return """
    po_head AS (
      SELECT po_id, any_value(supplier_id) AS supplier_id, min(po_date) AS po_date,
             min(expected_delivery_date) AS promised, sum(qty_ordered) AS ordered,
             count(DISTINCT sku) AS lines, any_value(sku) AS first_sku
      FROM stg_fmcg_purchase_orders GROUP BY po_id),
    recv AS (
      SELECT po_id, min(receipt_date) AS first_receipt, sum(qty_received) AS received,
             sum(coalesce(qty_rejected, 0)) AS rejected
      FROM stg_fmcg_receipts GROUP BY po_id),
    matched AS (
      SELECT h.po_id, h.supplier_id, h.po_date, h.promised, h.ordered, h.lines, h.first_sku,
             r.first_receipt, r.received, r.rejected,
             date_diff('day', h.po_date, r.first_receipt) AS observed_lead_days,
             CASE WHEN h.promised IS NOT NULL THEN date_diff('day', h.po_date, h.promised) END AS promised_lead_days,
             CASE WHEN h.promised IS NOT NULL THEN date_diff('day', h.promised, r.first_receipt) END AS late_days,
             CASE WHEN h.ordered > 0 THEN r.received / h.ordered END AS fill
      FROM po_head h JOIN recv r ON r.po_id = h.po_id)
    """


def _supplier_metrics_sql(where: str = "") -> str:
    return f"""
    WITH {_matched_cte()}
    SELECT supplier_id,
           count(*) AS matched_orders,
           sum(ordered) AS units_ordered,
           sum(received) AS units_received,
           CASE WHEN sum(ordered) > 0 THEN sum(received) / sum(ordered) END AS fill_rate,
           avg(CASE WHEN fill < {SHORT_FILL_TOLERANCE} THEN 1.0 ELSE 0.0 END) AS short_fill_rate,
           avg(observed_lead_days) AS mean_lead_days,
           quantile_cont(observed_lead_days, 0.5) AS p50_lead_days,
           quantile_cont(observed_lead_days, 0.9) AS p90_lead_days,
           stddev_samp(observed_lead_days) AS lead_sd_days,
           avg(promised_lead_days) AS promised_lead_days,
           count(*) FILTER (WHERE promised IS NOT NULL) AS orders_with_promise,
           avg(CASE WHEN late_days IS NOT NULL AND late_days > 0 THEN 1.0
                    WHEN late_days IS NOT NULL THEN 0.0 END) AS late_rate,
           avg(CASE WHEN late_days > 0 THEN late_days END) AS mean_late_days,
           stddev_samp(fill) AS fill_sd,
           min(po_date) AS first_order, max(first_receipt) AS last_receipt
    FROM matched {where} GROUP BY supplier_id
    """  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind


SUPPLIER_SORTS = {
    "supplier_id": "supplier_id", "name": "name", "matched_orders": "matched_orders",
    "fill_rate": "fill_rate", "short_fill_rate": "short_fill_rate", "late_rate": "late_rate",
    "mean_late_days": "mean_late_days", "p90_lead_days": "p90_lead_days",
    "lead_sd_days": "lead_sd_days", "open_orders": "open_orders", "late_open_orders": "late_open_orders",
    "skus": "skus", "fill_sd": "fill_sd",
}


class DiagnosticsRefused(ValueError):
    """A name in the request is not one this module serves."""


def supplier_page(
    conn: Any,
    *,
    search: str | None = None,
    sort: str = "late_rate",
    direction: str = "desc",
    limit: int = 50,
    offset: int = 0,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Every supplier with what the receipt history measures about it.

    A supplier with no matched orders is still listed — it is part of the business — with its
    measured fields null, so nobody concludes from a short table that a supplier is missing.
    """
    if not has_table(conn, "stg_fmcg_purchase_orders"):
        return {"rows": [], "total": 0, "served": False,
                "note": "No purchase order history has been uploaded, so no supplier can be measured yet."}
    if sort not in SUPPLIER_SORTS:
        raise DiagnosticsRefused(f"Cannot sort suppliers on {sort!r}")
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    direction_sql = "DESC" if str(direction).lower() == "desc" else "ASC"
    measured = _supplier_metrics_sql() if has_table(conn, "stg_fmcg_receipts") else \
        "SELECT NULL AS supplier_id, NULL AS matched_orders, NULL AS fill_rate, NULL AS short_fill_rate, " \
        "NULL AS late_rate, NULL AS mean_late_days, NULL AS p50_lead_days, NULL AS p90_lead_days, " \
        "NULL AS lead_sd_days, NULL AS promised_lead_days, NULL AS fill_sd, NULL AS mean_lead_days, " \
        "NULL AS units_ordered, NULL AS units_received, NULL AS orders_with_promise, " \
        "NULL AS first_order, NULL AS last_receipt WHERE FALSE"

    master = ("SELECT supplier_id, any_value(supplier_name) AS name, any_value(origin_iso3) AS origin, "
              "any_value(route) AS route, any_value(risk_group) AS risk_group "
              "FROM stg_fmcg_suppliers GROUP BY supplier_id") if has_table(conn, "stg_fmcg_suppliers") else \
             ("SELECT DISTINCT supplier_id, CAST(NULL AS VARCHAR) AS name, CAST(NULL AS VARCHAR) AS origin, "
              "CAST(NULL AS VARCHAR) AS route, CAST(NULL AS VARCHAR) AS risk_group "
              "FROM stg_fmcg_purchase_orders WHERE supplier_id IS NOT NULL")

    open_sql = """
    open_state AS (
      SELECT h.supplier_id, h.po_id, h.promised,
             CASE WHEN r.first_receipt IS NULL THEN h.ordered ELSE 0 END AS open_units
      FROM (SELECT po_id, any_value(supplier_id) AS supplier_id, min(expected_delivery_date) AS promised,
                   sum(qty_ordered) AS ordered FROM stg_fmcg_purchase_orders GROUP BY po_id) h
      LEFT JOIN (SELECT po_id, min(receipt_date) AS first_receipt FROM stg_fmcg_receipts GROUP BY po_id) r
             ON r.po_id = h.po_id),
    opens AS (
      SELECT supplier_id, count(*) FILTER (WHERE open_units > 0) AS open_orders,
             count(*) FILTER (WHERE open_units > 0 AND promised IS NOT NULL AND promised < CAST(? AS DATE)) AS late_open_orders,
             sum(greatest(open_units, 0)) AS open_units
      FROM open_state GROUP BY supplier_id)
    """ if has_table(conn, "stg_fmcg_receipts") else """
    opens AS (
      SELECT any_value(supplier_id) AS supplier_id, count(DISTINCT po_id) AS open_orders,
             CAST(NULL AS BIGINT) AS late_open_orders, sum(qty_ordered) AS open_units
      FROM stg_fmcg_purchase_orders GROUP BY supplier_id)
    """
    open_params: list[Any] = [as_of] if has_table(conn, "stg_fmcg_receipts") else []

    skus_sql = ("supplied AS (SELECT supplier_id, count(DISTINCT sku) AS skus FROM stg_fmcg_skus "
                "WHERE supplier_id IS NOT NULL GROUP BY supplier_id)"
                if has_table(conn, "stg_fmcg_skus") else
                "supplied AS (SELECT NULL AS supplier_id, NULL AS skus WHERE FALSE)")

    where: list[str] = []
    params: list[Any] = []
    if search and search.strip():
        needle = f"%{search.strip()}%"
        where.append("(CAST(m.supplier_id AS VARCHAR) ILIKE ? OR CAST(m.name AS VARCHAR) ILIKE ?)")
        params.extend([needle, needle])
    clause = f" WHERE {' AND '.join(where)}" if where else ""

    body = f"""
    WITH master AS ({master}), measured AS ({measured}), {open_sql}, {skus_sql}
    SELECT m.supplier_id, m.name, m.origin, m.route, m.risk_group,
           d.matched_orders, d.fill_rate, d.short_fill_rate, d.late_rate, d.mean_late_days,
           d.p50_lead_days, d.p90_lead_days, d.lead_sd_days, d.promised_lead_days, d.fill_sd,
           d.mean_lead_days, d.orders_with_promise, d.last_receipt,
           o.open_orders, o.late_open_orders, o.open_units, s.skus
    FROM master m
    LEFT JOIN measured d ON d.supplier_id = m.supplier_id
    LEFT JOIN opens o ON o.supplier_id = m.supplier_id
    LEFT JOIN supplied s ON s.supplier_id = m.supplier_id{clause}
    """  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    all_params = [*open_params, *params]
    rows = _rows(conn, f"SELECT * FROM ({body}) ORDER BY {SUPPLIER_SORTS[sort]} {direction_sql} NULLS LAST LIMIT ? OFFSET ?",  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
                 [*all_params, limit, offset])
    total = int(_one(conn, f"SELECT count(*) FROM ({body})", all_params) or 0)  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    return {"rows": rows, "total": total, "limit": limit, "offset": offset, "sort": sort,
            "direction": direction_sql.lower(), "served": True,
            "short_fill_tolerance": SHORT_FILL_TOLERANCE, "thin_sample": THIN_SAMPLE}


def supplier_detail(conn: Any, supplier_id: str, *, as_of: str | None = None) -> dict[str, Any]:
    """One supplier: what is measured, where lateness concentrates, and what cannot be determined."""
    page = supplier_page(conn, search=None, limit=200, as_of=as_of)
    row = next((r for r in page["rows"] if str(r.get("supplier_id")) == supplier_id), None)
    if row is None and not has_table(conn, "stg_fmcg_suppliers"):
        raise KeyError(supplier_id)
    if row is None:
        found = _rows(conn, "SELECT supplier_id FROM stg_fmcg_suppliers WHERE supplier_id = ? LIMIT 1", [supplier_id])
        if not found:
            raise KeyError(supplier_id)
        row = {"supplier_id": supplier_id}

    master = _rows(conn, "SELECT * FROM stg_fmcg_suppliers WHERE supplier_id = ? LIMIT 1",
                   [supplier_id]) if has_table(conn, "stg_fmcg_suppliers") else []

    deliveries: list[dict[str, Any]] = []
    by_sku: list[dict[str, Any]] = []
    by_month: list[dict[str, Any]] = []
    if has_table(conn, "stg_fmcg_receipts") and has_table(conn, "stg_fmcg_purchase_orders"):
        deliveries = _rows(conn, f"""
            WITH {_matched_cte()}
            SELECT po_id, po_date, promised, first_receipt, ordered, received, rejected,
                   observed_lead_days, promised_lead_days, late_days, fill, first_sku, lines
            FROM matched WHERE supplier_id = ? ORDER BY first_receipt DESC LIMIT 200""", [supplier_id])  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
        by_sku = _rows(conn, f"""
            WITH {_matched_cte()}
            SELECT first_sku AS sku, count(*) AS orders,
                   count(*) FILTER (WHERE late_days > 0) AS late_orders,
                   avg(CASE WHEN late_days > 0 THEN late_days END) AS mean_late_days,
                   CASE WHEN sum(ordered) > 0 THEN sum(received) / sum(ordered) END AS fill_rate
            FROM matched WHERE supplier_id = ? AND lines = 1
            GROUP BY first_sku ORDER BY late_orders DESC, orders DESC LIMIT 20""", [supplier_id])  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
        by_month = _rows(conn, f"""
            WITH {_matched_cte()}
            SELECT date_trunc('month', po_date) AS month, count(*) AS orders,
                   count(*) FILTER (WHERE late_days > 0) AS late_orders,
                   avg(observed_lead_days) AS mean_lead_days
            FROM matched WHERE supplier_id = ?
            GROUP BY 1 ORDER BY 1 DESC LIMIT 24""", [supplier_id])  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind

    trend = _trend(conn, supplier_id)
    skus = _rows(conn, """
        SELECT sku, sku_name, category FROM (
          SELECT sku, sku_name, category, row_number() OVER (PARTITION BY sku ORDER BY imported_at DESC) rn
          FROM stg_fmcg_skus WHERE supplier_id = ?) WHERE rn = 1 ORDER BY sku LIMIT 500
        """, [supplier_id]) if has_table(conn, "stg_fmcg_skus") else []

    alternatives = _alternatives(conn, supplier_id)
    exposure = _exposure(conn, supplier_id)

    return {
        "supplier_id": supplier_id,
        "master": master[0] if master else None,
        "measured": row,
        "deliveries": deliveries,
        "by_product": by_sku,
        "by_month": by_month,
        "trend": trend,
        "skus": skus,
        "alternatives": alternatives,
        "exposure": exposure,
        "lateness": lateness_account(row, by_sku, by_month, conn),
        "short_fill_tolerance": SHORT_FILL_TOLERANCE,
        "thin_sample": THIN_SAMPLE,
    }


def _trend(conn: Any, supplier_id: str) -> dict[str, Any] | None:
    """Recent half against earlier half of this supplier's matched orders. A direction, not a forecast."""
    if not (has_table(conn, "stg_fmcg_receipts") and has_table(conn, "stg_fmcg_purchase_orders")):
        return None
    rows = _rows(conn, f"""
        WITH {_matched_cte()},
        ranked AS (SELECT *, row_number() OVER (ORDER BY first_receipt DESC) AS rn,
                          count(*) OVER () AS n
                   FROM matched WHERE supplier_id = ?)
        SELECT CASE WHEN rn <= n / 2 THEN 'recent' ELSE 'earlier' END AS half,
               count(*) AS orders, avg(observed_lead_days) AS mean_lead_days,
               avg(CASE WHEN late_days IS NOT NULL AND late_days > 0 THEN 1.0
                        WHEN late_days IS NOT NULL THEN 0.0 END) AS late_rate,
               CASE WHEN sum(ordered) > 0 THEN sum(received) / sum(ordered) END AS fill_rate
        FROM ranked GROUP BY 1""", [supplier_id])  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    if len(rows) < 2:
        return None
    recent = next((r for r in rows if r["half"] == "recent"), None)
    earlier = next((r for r in rows if r["half"] == "earlier"), None)
    if not recent or not earlier or (recent["orders"] or 0) < 3 or (earlier["orders"] or 0) < 3:
        return None
    return {"recent": recent, "earlier": earlier}


def _alternatives(conn: Any, supplier_id: str) -> dict[str, Any]:
    """Declared alternative sources for the products this supplier ships. Declared, never inferred."""
    if not has_table(conn, "stg_fmcg_sources"):
        return {"declared": False, "rows": [],
                "note": "No alternative sources have been declared for this workspace."}
    rows = _rows(conn, """
        SELECT s.* FROM stg_fmcg_sources s
        WHERE s.sku IN (SELECT DISTINCT sku FROM stg_fmcg_sources WHERE supplier_id = ?
                        UNION SELECT DISTINCT sku FROM stg_fmcg_skus WHERE supplier_id = ?)
          AND s.supplier_id <> ?
        ORDER BY s.sku, s.supplier_id LIMIT 500""", [supplier_id, supplier_id, supplier_id])
    return {"declared": bool(rows), "rows": rows,
            "note": None if rows else
            "No alternative supplier has been declared for the products this supplier ships."}


def _exposure(conn: Any, supplier_id: str) -> dict[str, Any]:
    """What depends on this supplier: products, stock value on hand, open units."""
    out: dict[str, Any] = {"skus": None, "on_hand_value": None, "open_units": None}
    if has_table(conn, "stg_fmcg_skus"):
        out["skus"] = _one(conn, "SELECT count(DISTINCT sku) FROM stg_fmcg_skus WHERE supplier_id = ?", [supplier_id])
        if has_table(conn, "stg_fmcg_inventory"):
            out["on_hand_value"] = _one(conn, """
                WITH latest AS (
                  SELECT sku, sum(on_hand) AS on_hand FROM (
                    SELECT sku, location_id, on_hand,
                           row_number() OVER (PARTITION BY sku, location_id ORDER BY imported_at DESC) rn
                    FROM stg_fmcg_inventory
                    WHERE snapshot_date = (SELECT max(snapshot_date) FROM stg_fmcg_inventory))
                  WHERE rn = 1 GROUP BY sku),
                m AS (SELECT sku, any_value(unit_cost) AS unit_cost, any_value(supplier_id) AS supplier_id
                      FROM stg_fmcg_skus GROUP BY sku)
                SELECT sum(l.on_hand * m.unit_cost) FROM latest l JOIN m ON m.sku = l.sku
                WHERE m.supplier_id = ?""", [supplier_id])
    if has_table(conn, "stg_fmcg_purchase_orders"):
        received = ("LEFT JOIN (SELECT po_id, min(receipt_date) AS first_receipt FROM stg_fmcg_receipts "
                    "GROUP BY po_id) r ON r.po_id = h.po_id" if has_table(conn, "stg_fmcg_receipts")
                    else "LEFT JOIN (SELECT NULL AS po_id, NULL AS first_receipt WHERE FALSE) r ON FALSE")
        out["open_units"] = _one(conn, f"""
            SELECT sum(CASE WHEN r.first_receipt IS NULL THEN h.ordered ELSE 0 END)
            FROM (SELECT po_id, any_value(supplier_id) AS supplier_id, sum(qty_ordered) AS ordered
                  FROM stg_fmcg_purchase_orders GROUP BY po_id) h {received}
            WHERE h.supplier_id = ?""", [supplier_id])  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    return out


def lateness_account(
    measured: dict[str, Any], by_sku: list[dict[str, Any]], by_month: list[dict[str, Any]], conn: Any,
) -> dict[str, Any]:
    """"Why is this supplier late?", answered in four separated registers.

    The separation is the product. An operator reading this must be able to tell, sentence by
    sentence, which statements are counts of rows that exist and which are patterns that suggest
    but do not establish anything. Nothing here is allowed to read as a cause.
    """
    observed: list[dict[str, Any]] = []
    associations: list[dict[str, Any]] = []
    n = measured.get("matched_orders") or 0
    late_rate = measured.get("late_rate")
    with_promise = measured.get("orders_with_promise") or 0

    if n:
        if late_rate is not None and with_promise:
            observed.append({
                "statement": f"Arrived after the promised date on {late_rate * 100:.0f}% of "
                             f"{_count(with_promise)} order{'' if with_promise == 1 else 's'} that carried a promised date.",
                "sample": int(with_promise), "thin": with_promise < THIN_SAMPLE})
        elif not with_promise:
            observed.append({
                "statement": f"None of the {_count(n)} matched orders carries a promised delivery date, "
                             "so lateness cannot be measured — only how long delivery actually took.",
                "sample": int(n), "thin": False})
        if measured.get("mean_late_days") is not None:
            observed.append({
                "statement": f"When late, arrived {measured['mean_late_days']:.0f} day"
                             f"{'' if round(measured['mean_late_days']) == 1 else 's'} after the promised date on average.",
                "sample": int(with_promise), "thin": with_promise < THIN_SAMPLE})
        if measured.get("p50_lead_days") is not None and measured.get("p90_lead_days") is not None:
            observed.append({
                "statement": f"Half of deliveries took {measured['p50_lead_days']:.0f} days or less; "
                             f"one in ten took {measured['p90_lead_days']:.0f} days or more.",
                "sample": int(n), "thin": n < THIN_SAMPLE})
        if measured.get("fill_rate") is not None:
            observed.append({
                "statement": f"{measured['fill_rate'] * 100:.1f}% of the quantity ordered has arrived.",
                "sample": int(n), "thin": n < THIN_SAMPLE})
        if measured.get("short_fill_rate"):
            observed.append({
                "statement": f"{measured['short_fill_rate'] * 100:.0f}% of orders arrived short of the "
                             f"quantity ordered by more than {(1 - SHORT_FILL_TOLERANCE) * 100:.0f}%.",
                "sample": int(n), "thin": n < THIN_SAMPLE})

    late_total = sum((r.get("late_orders") or 0) for r in by_sku)
    if late_total >= 3:
        top = [r for r in by_sku if (r.get("late_orders") or 0) > 0][:3]
        share = sum((r.get("late_orders") or 0) for r in top) / late_total
        if share >= 0.6 and len(by_sku) > len(top):
            names = ", ".join(str(r["sku"]) for r in top)
            associations.append({
                "statement": f"{_count(sum((r.get('late_orders') or 0) for r in top))} of {_count(late_total)} "
                             f"late arrivals were on {names}.",
                "note": "This is where lateness concentrates. It does not establish that these products cause it."})
    months_late = [r for r in by_month if (r.get("late_orders") or 0) > 0]
    if len(by_month) >= 6 and months_late:
        worst = max(months_late, key=lambda r: (r.get("late_orders") or 0))
        if (worst.get("late_orders") or 0) >= 2 and (worst.get("late_orders") or 0) / max(1, late_total) >= 0.4:
            associations.append({
                "statement": f"Late arrivals cluster in {str(worst['month'])[:7]}.",
                "note": "A period, not a reason. Seasonality, a single disruption and a coincidence look identical here."})

    # What the upload physically cannot answer. Listing the fields is the useful part: it tells an
    # operator exactly what to add if they want the decomposition.
    missing = ["supplier dispatch or ready-to-ship date", "departure from origin",
               "arrival at the entry port", "customs clearance", "inland departure and delivery"]
    unknown = {
        "statement": "ZAAD can measure the delay but cannot say where it happened. The upload carries "
                     "the date you ordered, the date you were promised and the date you received — "
                     "and nothing in between.",
        "missing_fields": missing,
        "available_fields": ["order date", "promised delivery date", "receipt date", "quantity ordered",
                             "quantity received", "quantity rejected"],
    }
    return {"observed": observed, "associations": associations, "drivers": [], "unknown": unknown,
            "driver_note": "No delivery-event timestamps are uploaded, so no stage of the journey can be "
                           "shown to carry the delay."}


# ── sector diagnostics (physics the workspace declares) ───────────────────────

SECTOR_SORTS = {
    "sku": "sku", "supply_uncertainty": "fill_sd", "lead_uncertainty": "lead_sd_days",
    "remaining_life_receipt": "remaining_life_at_receipt_days", "shelf_life_days": "shelf_life_days",
    "on_hand": "on_hand", "days_to_expiry": "days_to_expiry", "demand_variability": "demand_cv",
}


def sector_page(
    conn: Any, *, sector: str | None = None, sort: str = "supply_uncertainty",
    direction: str = "desc", limit: int = 50, offset: int = 0,
) -> dict[str, Any]:
    """Per-product physical uncertainty for a produce or meat/seafood workspace.

    Everything here is either a declared physics column (migration 017) or a dispersion measured
    from the operator's own history. Waste and spoilage are not part of the canonical upload, so
    they are absent rather than approximated from stock movements.
    """
    if not has_table(conn, "stg_fmcg_skus"):
        return {"rows": [], "total": 0, "served": False, "note": "No product master has been uploaded yet."}
    if sort not in SECTOR_SORTS:
        raise DiagnosticsRefused(f"Cannot sort sector diagnostics on {sort!r}")
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    direction_sql = "DESC" if str(direction).lower() == "desc" else "ASC"

    cols = {row[1] for row in conn.execute("PRAGMA table_info('stg_fmcg_skus')").fetchall()}
    declared = 0
    if "sector" in cols:
        got = conn.execute('SELECT count(*) FROM stg_fmcg_skus WHERE "sector" IS NOT NULL').fetchone()
        declared = int(got[0]) if got else 0
    if not declared:
        return {"rows": [], "total": 0, "served": False,
                "note": "No product in this workspace declares a sector, so there is no sector physics to show. "
                        "Declare a sector on the product master and these measures appear."}

    if has_table(conn, "stg_fmcg_receipts") and has_table(conn, "stg_fmcg_purchase_orders"):
        supply = f"""
        supply AS (
          WITH {_matched_cte()}
          SELECT first_sku AS sku, count(*) AS deliveries, avg(fill) AS fill_mean,
                 stddev_samp(fill) AS fill_sd, avg(observed_lead_days) AS lead_mean_days,
                 stddev_samp(observed_lead_days) AS lead_sd_days
          FROM matched WHERE lines = 1 GROUP BY first_sku)
        """  # nosec B608 - code literals only
    else:
        supply = """
        supply AS (SELECT NULL AS sku, NULL AS deliveries, NULL AS fill_mean, NULL AS fill_sd,
                          NULL AS lead_mean_days, NULL AS lead_sd_days WHERE FALSE)
        """
    life = """
    life AS (
      SELECT sku, min(date_diff('day', snapshot_date, expiry_date)) AS days_to_expiry,
             sum(on_hand) AS on_hand
      FROM stg_fmcg_inventory
      WHERE snapshot_date = (SELECT max(snapshot_date) FROM stg_fmcg_inventory)
      GROUP BY sku)
    """ if (has_table(conn, "stg_fmcg_inventory")
            and "expiry_date" in {r[1] for r in conn.execute("PRAGMA table_info('stg_fmcg_inventory')").fetchall()}) else """
    life AS (SELECT NULL AS sku, NULL AS days_to_expiry, NULL AS on_hand WHERE FALSE)
    """
    demand = """
    demandvar AS (
      SELECT sku, stddev_samp(weekly) / nullif(avg(weekly), 0) AS demand_cv FROM (
        SELECT sku, date_trunc('week', order_date) AS w, sum(qty_ordered) AS weekly
        FROM stg_fmcg_orders
        WHERE order_date > (SELECT max(order_date) FROM stg_fmcg_orders) - INTERVAL 364 DAY
        GROUP BY 1, 2) GROUP BY sku)
    """ if has_table(conn, "stg_fmcg_orders") else "demandvar AS (SELECT NULL AS sku, NULL AS demand_cv WHERE FALSE)"

    def col(name: str, fallback: str = "NULL") -> str:
        return f'm."{name}"' if name in cols else fallback

    where = ' WHERE m."sector" = ?' if sector else ""
    params: list[Any] = [sector] if sector else []
    body = f"""
    WITH {supply}, {life}, {demand},
    base AS (
      SELECT m."sku" AS sku, {col('sku_name', 'CAST(NULL AS VARCHAR)')} AS sku_name,
             {col('sector', 'CAST(NULL AS VARCHAR)')} AS sector,
             {col('storage_state', 'CAST(NULL AS VARCHAR)')} AS storage_state,
             {col('shelf_life_days')} AS shelf_life_days,
             {col('age_at_receipt_days')} AS age_at_receipt_days,
             {col('min_remaining_life_sale_days')} AS min_remaining_life_sale_days,
             CASE WHEN {col('shelf_life_days')} IS NOT NULL AND {col('age_at_receipt_days')} IS NOT NULL
                  THEN {col('shelf_life_days')} - {col('age_at_receipt_days')} END AS remaining_life_at_receipt_days,
             s.deliveries, s.fill_mean, s.fill_sd, s.lead_mean_days, s.lead_sd_days,
             l.days_to_expiry, l.on_hand, d.demand_cv
      FROM (SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY "sku" ORDER BY imported_at DESC) rn
                           FROM stg_fmcg_skus) WHERE rn = 1) m
      LEFT JOIN supply s ON s.sku = m."sku"
      LEFT JOIN life l ON l.sku = m."sku"
      LEFT JOIN demandvar d ON d.sku = m."sku"{where})
    SELECT * FROM base
    """  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    rows = _rows(conn, f"SELECT * FROM ({body}) ORDER BY {SECTOR_SORTS[sort]} {direction_sql} NULLS LAST LIMIT ? OFFSET ?",  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
                 [*params, limit, offset])
    for row in rows:
        row.pop("rn", None)
    total = int(_one(conn, f"SELECT count(*) FROM ({body})", params) or 0)  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    sectors = _rows(conn, 'SELECT DISTINCT "sector" AS s FROM stg_fmcg_skus WHERE "sector" IS NOT NULL ORDER BY 1')
    return {"rows": rows, "total": total, "limit": limit, "offset": offset, "sort": sort,
            "direction": direction_sql.lower(), "served": True,
            "sectors": [str(r["s"]) for r in sectors],
            "absent": ["Waste and spoilage events are not part of this upload, so waste exposure is not measured.",
                       "Cold-chain excursions are not uploaded; the storage state a product declares is shown instead."]}


def corridor_lateness(conn: Any) -> dict[str, Any]:
    """Late arrivals grouped by the route each supplier declares. An association across suppliers."""
    if not (has_table(conn, "stg_fmcg_suppliers") and has_table(conn, "stg_fmcg_receipts")
            and has_table(conn, "stg_fmcg_purchase_orders")):
        return {"served": False, "rows": [],
                "note": "Routes are grouped from the supplier master and measured from receipts; both are needed."}
    if "route" not in {r[1] for r in conn.execute("PRAGMA table_info('stg_fmcg_suppliers')").fetchall()}:
        return {"served": False, "rows": [], "note": "No supplier declares a route in this workspace."}
    rows = _rows(conn, f"""
        WITH {_matched_cte()},
        sup AS (SELECT supplier_id, any_value(route) AS route FROM stg_fmcg_suppliers GROUP BY supplier_id)
        SELECT coalesce(sup.route, 'not declared') AS route,
               count(*) AS orders, count(DISTINCT matched.supplier_id) AS suppliers,
               count(*) FILTER (WHERE late_days > 0) AS late_orders,
               avg(CASE WHEN late_days > 0 THEN late_days END) AS mean_late_days,
               avg(observed_lead_days) AS mean_lead_days
        FROM matched LEFT JOIN sup ON sup.supplier_id = matched.supplier_id
        GROUP BY 1 ORDER BY late_orders DESC""")  # nosec B608 - code literals plus allowlisted names (SUPPLIER_SORTS / SECTOR_SORTS); values bind
    return {"served": True, "rows": rows,
            "note": "Grouped by the route each supplier declares. A route that arrives late more often is "
                    "where delay concentrates, not a demonstration that the route causes it."}
