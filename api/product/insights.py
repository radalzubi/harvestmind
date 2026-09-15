"""Insights: the operator's own records aggregated on the server, and the latest completed plan read
back — never a new solve.

Two sources, kept apart on every surface:

  **OPERATIONAL DATA** — customer orders and what was shipped, inventory snapshots, purchase orders
  and receipts, transfers, declared sources and rights. Every number here is a sum, a count or a
  ratio over rows the operator uploaded, and every payload says which rows, over which dates, with
  which filters, and what the denominator is.

  **THE LATEST COMPLETED PLAN** — the most recent DONE workspace plan in the job store, read as it
  was written. Its actions, its ledger and its phase blocks are reported verbatim; nothing is
  recomputed, and Insights never starts a solve to have something to draw. If the workspace's
  data changed after the plan finished, that is said.

The registers a number can belong to are kept distinct and never summed into one "savings":
MODELED_DIFFERENCE (the plan's ledger), BACKTESTED_OPPORTUNITY (not wired), APPROVED_EXPECTED_
DIFFERENCE (an approved proposal's evaluation), OBSERVED_AFTER_ACTION (an outcome recorded after a
placed action; not attributed) and REALIZED_VALUE (an outcome with a stated comparator).

What the vault cannot answer is returned as null with a reason — UNKNOWN, NOT MEASURED, NOT
APPLICABLE, NO DATA, BLOCKED BY DATA, NOT IN PLAN — and never as zero. Zero is a count of rows.

Bounded: every series is capped by bucket count, every breakdown by `TOP`, and nothing returns a
raw row set. Tenant-scoped by construction: `conn` is the caller's own vault, and the plan lookup
is filtered by the caller's operator id.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from api.product.catalog import _columns, _demand_cte, _one, _open_po_cte, _rows, _stock_cte, has_table, site_column_usable
from api.product.diagnostics import SHORT_FILL_TOLERANCE, THIN_SAMPLE, _matched_cte

Bucket = Literal["day", "week", "month"]
BUCKETS: tuple[str, ...] = ("day", "week", "month")
#: Series are bounded: a month bucket over two years is 24 points; a day bucket is capped here.
MAX_POINTS = 400
TOP = 10
NULL_REASONS = ("UNKNOWN", "NOT_MEASURED", "NOT_APPLICABLE", "NO_DATA", "BLOCKED_BY_DATA", "NOT_IN_PLAN")
VALUE_REGISTERS = ("MODELED_DIFFERENCE", "BACKTESTED_OPPORTUNITY", "APPROVED_EXPECTED_DIFFERENCE",
                   "OBSERVED_AFTER_ACTION", "REALIZED_VALUE")
AMENDMENT_VERBS = ("KEEP", "DEFER", "EXPEDITE", "REDUCE", "CANCEL", "SPLIT")
STAGING_TABLES = ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_inventory", "stg_fmcg_purchase_orders", "stg_fmcg_receipts",
                  "stg_fmcg_suppliers", "stg_fmcg_locations", "stg_fmcg_lanes", "stg_fmcg_transfers", "stg_fmcg_sources")


class InsightsRefused(ValueError):
    """A request outside what this module serves (a bad bucket, a malformed date, an overlong id)."""


@dataclass(frozen=True)
class Scope:
    """The filters every Insights read accepts. Values bind; names are code literals."""
    start: date | None = None
    end: date | None = None
    bucket: str = "week"
    sku: str | None = None
    category: str | None = None
    brand: str | None = None
    customer: str | None = None
    location: str | None = None
    supplier: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"date_range": {"start": self.start.isoformat() if self.start else None, "end": self.end.isoformat() if self.end else None},
                "bucket": self.bucket,
                "filters": {k: v for k, v in (("sku", self.sku), ("category", self.category), ("brand", self.brand),
                                              ("customer", self.customer), ("location", self.location), ("supplier", self.supplier)) if v}}


def _ident(value: str | None, what: str) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if len(text) > 120 or any(ch in text for ch in "\x00\n\r"):
        raise InsightsRefused(f"{what} is not a valid identifier.")
    return text


def _date(value: str | None, what: str) -> date | None:
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise InsightsRefused(f"{what} must be a date (YYYY-MM-DD).") from exc


def scope_from(bucket: str = "week", start: str | None = None, end: str | None = None, sku: str | None = None,
               category: str | None = None, brand: str | None = None, customer: str | None = None,
               location: str | None = None, supplier: str | None = None) -> Scope:
    if bucket not in BUCKETS:
        raise InsightsRefused(f"bucket is one of {', '.join(BUCKETS)}.")
    s, e = _date(start, "start"), _date(end, "end")
    if s and e and e < s:
        raise InsightsRefused("end is before start.")
    return Scope(start=s, end=e, bucket=bucket, sku=_ident(sku, "sku"), category=_ident(category, "category"),
                 brand=_ident(brand, "brand"), customer=_ident(customer, "customer"), location=_ident(location, "location"),
                 supplier=_ident(supplier, "supplier"))


def _trunc(bucket: str, column: str) -> str:
    return f"date_trunc('{bucket}', CAST({column} AS DATE))"   # bucket is validated against BUCKETS


def _plain(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and value != value:   # NaN
        return None
    return value


def _clean(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: _plain(v) for k, v in r.items()} for r in rows]


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out else out


def _null(reason: str, why: str) -> dict[str, Any]:
    assert reason in NULL_REASONS
    return {"value": None, "reason": reason, "why": why}


def _last_updated(conn: Any) -> str | None:
    stamps: list[Any] = []
    for table in STAGING_TABLES:
        if not has_table(conn, table):
            continue
        cols = _columns(conn, table)
        col = "_uploaded_at" if "_uploaded_at" in cols else ("imported_at" if "imported_at" in cols else None)
        if col:
            stamps.append(_one(conn, f"SELECT max({col}) FROM {table}"))  # noqa: S608  # nosec B608 - literals
    stamps = [s for s in stamps if s is not None]
    return max(stamps).isoformat() if stamps else None


def provenance(conn: Any, scope: Scope, *, source: list[str], metric: str, numerator: str, denominator: str,
               coverage: dict[str, Any] | None = None, plan: dict[str, Any] | None = None, note: str | None = None) -> dict[str, Any]:
    """The "Data & scope" block every chart carries."""
    return {"source_data": source, "metric": metric, "numerator": numerator, "denominator": denominator,
            **scope.as_dict(), "coverage": coverage or {}, "last_updated": _last_updated(conn),
            "plan": ({k: plan.get(k) for k in ("job_id", "finished_at", "as_of", "information_hash", "stale", "stale_reason")} if plan else None),
            "note": note}


# ── SKU-side filters (category / brand / sku / supplier) join the master; the row-side filters bind ──

def _sku_filter(scope: Scope, alias: str = "m") -> tuple[str, list[Any]]:
    clauses, params = [], []
    if scope.sku:
        clauses.append(f"{alias}.sku = ?")
        params.append(scope.sku)
    if scope.category:
        clauses.append(f"{alias}.category = ?")
        params.append(scope.category)
    if scope.brand:
        clauses.append(f"{alias}.brand = ?")
        params.append(scope.brand)
    if scope.supplier:
        clauses.append(f"{alias}.supplier_id = ?")
        params.append(scope.supplier)
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _range(scope: Scope, column: str) -> tuple[str, list[Any]]:
    clauses, params = [], []
    if scope.start:
        clauses.append(f"{column} >= ?")
        params.append(scope.start)
    if scope.end:
        clauses.append(f"{column} <= ?")
        params.append(scope.end)
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _master_cte(conn: Any) -> str:
    cols = _columns(conn, "stg_fmcg_skus") if has_table(conn, "stg_fmcg_skus") else set()
    brand = "any_value(brand)" if "brand" in cols else "NULL"
    return f"""master AS (SELECT sku, any_value(category) AS category, {brand} AS brand, any_value(supplier_id) AS supplier_id,
                            any_value(unit_cost) AS unit_cost, any_value(unit_price) AS unit_price, any_value(sku_name) AS sku_name
                     FROM stg_fmcg_skus GROUP BY sku)""" if cols else \
        "master AS (SELECT NULL AS sku, NULL AS category, NULL AS brand, NULL AS supplier_id, NULL AS unit_cost, NULL AS unit_price, NULL AS sku_name WHERE FALSE)"


# ── the latest completed plan ──────────────────────────────────────────────────

def latest_plan(conn: Any, operator: str) -> dict[str, Any] | None:
    """The most recent DONE workspace plan this operator owns, with its report and request, or None.

    Read from the job store; never computed. `stale` says whether any staging table was written
    after the plan finished, which is the honest answer to "does this plan describe my data?"."""
    path = os.getenv("ZAAD_JOB_STORE")
    if not path:
        return None
    from zaad.full.jobs import JobStore
    store = JobStore(Path(path))
    for job in store.list(operator, limit=50, purpose="WORKSPACE_PLAN"):
        if job["status"] != "DONE":
            continue
        full = store.get(job["id"], operator)
        report = full.get("report") or {}
        try:
            request = json.loads(store.request_json(job["id"]))
        except Exception:  # noqa: BLE001 - a request that cannot be parsed leaves the plan without its scope map
            request = {}
        finished = full.get("finished_at")
        updated = _last_updated(conn)
        stale = bool(finished and updated and updated > finished)
        return {"job_id": job["id"], "finished_at": finished, "as_of": report.get("as_of"),
                "information_hash": report.get("information_hash"), "status": report.get("status"),
                "stale": stale,
                "stale_reason": ("Workspace data changed after this plan finished." if stale else None),
                "report": report, "request": request,
                "scope_skus": [s.get("id") for s in (request.get("skus") or [])]}
    return None


def plan_summary(plan: dict[str, Any] | None) -> dict[str, Any]:
    if plan is None:
        return {"available": False, "reason": "NOT_IN_PLAN", "why": "No completed plan exists for this workspace yet. Run one from Home; Insights never starts a solve on its own."}
    return {"available": True, "job_id": plan["job_id"], "finished_at": plan["finished_at"], "as_of": plan["as_of"],
            "status": plan["status"], "information_hash": plan["information_hash"], "stale": plan["stale"],
            "stale_reason": plan["stale_reason"], "products": len(plan["scope_skus"]), "scope_skus": plan["scope_skus"][:50]}


def _source_to_sku(plan: dict[str, Any]) -> dict[str, str]:
    return {s.get("id"): s.get("sku") for s in (plan.get("request", {}).get("sources") or []) if s.get("id")}


def _po_to_sku(plan: dict[str, Any]) -> dict[str, str]:
    source_sku = _source_to_sku(plan)
    return {p.get("id"): source_sku.get(p.get("source"), "") for p in (plan.get("request", {}).get("pipeline") or []) if p.get("id")}


def decisions_of_plan(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Every decision the plan carries, flat: open-order verdicts, purchases, transfers. Verbatim."""
    if plan is None:
        return []
    report, out = plan["report"], []
    source_sku, po_sku = _source_to_sku(plan), _po_to_sku(plan)
    for order in ((report.get("commitments") or {}).get("orders") or []):
        out.append({"kind": "open_po", "id": f"po:{order.get('po')}", "target": order.get("po"), "sku": po_sku.get(order.get("po")),
                    "verb": str(order.get("recommended_action") or "KEEP").upper(),
                    "quantity": _num(order.get("quantity_affected")), "period": order.get("recommended_arrival_period")})
    for action in (report.get("actions") or []):
        kind = str(action.get("action") or "")
        if kind == "purchase":
            out.append({"kind": "purchase", "id": f"purchase:{action.get('source')}:{action.get('period')}", "target": action.get("source"),
                        "sku": source_sku.get(action.get("source")), "verb": "BUY", "quantity": _num(action.get("quantity")), "period": action.get("period")})
        elif kind == "transfer":
            out.append({"kind": "transfer", "id": f"transfer:{action.get('transfer')}:{action.get('period')}", "target": action.get("transfer"),
                        "sku": None, "verb": "MOVE", "quantity": _num(action.get("quantity")), "period": action.get("period")})
    return out


# ── demand ─────────────────────────────────────────────────────────────────────

def _has_rows(conn: Any, table: str) -> bool:
    """A table that exists but holds no rows is NO DATA, the same as one that was never uploaded."""
    return has_table(conn, table) and bool(_one(conn, f"SELECT count(*) FROM {table}"))  # noqa: S608  # nosec B608 - literals


def demand(conn: Any, scope: Scope, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """OBSERVED CUSTOMER ORDERS by bucket, with what was shipped where that is recorded."""
    if not _has_rows(conn, "stg_fmcg_orders"):
        return {"series": [], "available": False, "reason": "NO_DATA", "why": "No customer orders have been uploaded.",
                "provenance": provenance(conn, scope, source=["stg_fmcg_orders"], metric="observed customer orders", numerator="—", denominator="—")}
    shipped_col = "qty_shipped" in _columns(conn, "stg_fmcg_orders")
    site_ok = site_column_usable(conn, "stg_fmcg_orders", "location_id")
    sf, sp = _sku_filter(scope)
    rf, rp = _range(scope, "o.order_date")
    extra, ep = "", []
    if scope.customer:
        extra += " AND o.customer_id = ?"
        ep.append(scope.customer)
    if scope.location:
        if not site_ok:
            return {"series": [], "available": False, "reason": "BLOCKED_BY_DATA",
                    "why": "Customer orders carry no site, so demand by site is not a number the vault holds.",
                    "provenance": provenance(conn, scope, source=["stg_fmcg_orders"], metric="observed customer orders", numerator="—", denominator="—")}
        extra += " AND CAST(o.location_id AS VARCHAR) = ?"
        ep.append(scope.location)
    shipped = "sum(o.qty_shipped) AS shipped, sum(CASE WHEN o.qty_shipped IS NOT NULL THEN o.qty_ordered END) AS ordered_measured, count(*) FILTER (WHERE o.qty_shipped IS NULL) AS lines_unmeasured" if shipped_col \
        else "NULL AS shipped, NULL AS ordered_measured, count(*) AS lines_unmeasured"
    base = f"""WITH {_master_cte(conn)}
               SELECT {{select}} FROM stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku
               WHERE o.qty_ordered IS NOT NULL{sf}{rf}{extra} {{group}}"""  # nosec B608 - code literals; values bind
    params = [*sp, *rp, *ep]
    series = _rows(conn, base.format(select=f"{_trunc(scope.bucket, 'o.order_date')} AS period, sum(o.qty_ordered) AS ordered, {shipped}, "
                                            "count(*) AS lines, count(DISTINCT o.customer_id) AS customers, count(DISTINCT o.sku) AS products",
                                     group="GROUP BY 1 ORDER BY 1"), params)
    truncated = len(series) > MAX_POINTS
    series = series[-MAX_POINTS:]
    for r in series:
        r["unfulfilled"] = (r["ordered_measured"] - r["shipped"]) if (shipped_col and r.get("shipped") is not None and r.get("ordered_measured") is not None) else None
    top: dict[str, dict[str, Any]] = {}
    for name, key in (("skus", "o.sku"), ("customers", "o.customer_id"), ("categories", "m.category"), ("brands", "m.brand"),
                      ("locations", "o.location_id" if site_ok else None)):
        if key is None:
            top[name] = {"rows": [], "reason": "BLOCKED_BY_DATA", "why": "Customer orders carry no site."}
            continue
        rows = _rows(conn, base.format(select=f"{key} AS id, sum(o.qty_ordered) AS ordered, {shipped}, count(*) AS lines",
                                       group=f"GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT {TOP}"), params)
        for r in rows:
            r["unfulfilled"] = (r["ordered_measured"] - r["shipped"]) if (shipped_col and r.get("shipped") is not None and r.get("ordered_measured") is not None) else None
        top[name] = {"rows": _clean(rows)}
    totals = _rows(conn, base.format(select=f"sum(o.qty_ordered) AS ordered, {shipped}, count(*) AS lines, count(DISTINCT o.customer_id) AS customers, "
                                            "count(DISTINCT o.sku) AS products, min(o.order_date) AS first_order, max(o.order_date) AS last_order", group=""), params)[0]
    # concentration: share of the largest customer and of the largest five, over the range
    by_customer = _rows(conn, base.format(select="o.customer_id AS id, sum(o.qty_ordered) AS ordered", group="GROUP BY 1 ORDER BY 2 DESC"), params)
    total_units = float(totals.get("ordered") or 0.)
    shares = [float(r["ordered"] or 0.) / total_units for r in by_customer] if total_units > 0 else []
    concentration = {"customers": len(by_customer), "top_1_share": shares[0] if shares else None,
                     "top_5_share": sum(shares[:5]) if shares else None, "hhi": sum(s * s for s in shares) if shares else None,
                     "basis": "share of units ordered over the selected range; HHI is the sum of squared shares (1 = one customer)"}
    # period over period: the last two COMPLETE buckets. The newest bucket is partial when the data's
    # last order falls before the bucket's end, and a partial period against a whole one is not a change.
    pop = None
    partial_last = False
    if series:
        last_order = totals.get("last_order")
        last_period = series[-1]["period"]
        if last_order is not None and last_period is not None:
            bucket_end = _one(conn, f"SELECT {_trunc(scope.bucket, '?')} + INTERVAL 1 {scope.bucket} - INTERVAL 1 DAY", [last_period])
            partial_last = bool(bucket_end is not None and last_order < (bucket_end.date() if hasattr(bucket_end, "date") else bucket_end))
    complete = series[:-1] if (partial_last and len(series) >= 3) else series
    if len(complete) >= 2:
        last, prev = complete[-1], complete[-2]
        pop = {"period": _plain(last["period"]), "previous": _plain(prev["period"]), "ordered": last["ordered"], "previous_ordered": prev["ordered"],
               "change": (last["ordered"] - prev["ordered"]) if last["ordered"] is not None and prev["ordered"] is not None else None,
               "change_share": ((last["ordered"] - prev["ordered"]) / prev["ordered"]) if prev.get("ordered") else None,
               "basis": "the last two complete periods" + ("; the newest period is partial and is left out" if partial_last else "")}
    fulfilment = ("MEASURED" if shipped_col and (totals.get("lines_unmeasured") or 0) < (totals.get("lines") or 0) else
                  "NOT_MEASURED")
    return {"available": True, "label": "OBSERVED CUSTOMER ORDERS", "fulfilment": fulfilment,
            "fulfilment_note": ("Ordered, shipped and the recorded shortfall between them; a line without a shipped quantity is counted as unmeasured, never as fulfilled or lost."
                                if fulfilment == "MEASURED" else "The upload carries no shipped quantity, so fulfilment and shortfall are not measured. Nothing is inferred about lost demand."),
            "series": _clean(series), "truncated": truncated, "partial_last_period": partial_last,
            "totals": _clean([totals])[0], "top": top, "concentration": concentration,
            "period_over_period": pop,
            "provenance": provenance(conn, scope, source=["stg_fmcg_orders", "stg_fmcg_skus"], metric="units ordered by customers per period (observed orders, not demand)",
                                     numerator="sum(qty_ordered) of order lines in the period", denominator="every order line in the period after filters",
                                     coverage={"lines": totals.get("lines"), "lines_without_shipped_quantity": totals.get("lines_unmeasured"),
                                               "first_order": _plain(totals.get("first_order")), "last_order": _plain(totals.get("last_order"))},
                                     plan=plan)}


def demand_period(conn: Any, scope: Scope, period: date, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """One bucket opened: who and what drove it, what changed against the bucket before, what stock
    and inbound sit behind the products involved, and which decisions in the latest plan touch them."""
    if not _has_rows(conn, "stg_fmcg_orders"):
        return {"available": False, "reason": "NO_DATA", "why": "No customer orders have been uploaded."}
    shipped_col = "qty_shipped" in _columns(conn, "stg_fmcg_orders")
    site_ok = site_column_usable(conn, "stg_fmcg_orders", "location_id")
    sf, sp = _sku_filter(scope)
    extra, ep = "", []
    if scope.customer:
        extra += " AND o.customer_id = ?"
        ep.append(scope.customer)
    if scope.location and site_ok:
        extra += " AND CAST(o.location_id AS VARCHAR) = ?"
        ep.append(scope.location)
    bucket = _trunc(scope.bucket, "o.order_date")
    shipped = "sum(o.qty_shipped) AS shipped" if shipped_col else "NULL AS shipped"
    base = f"""WITH {_master_cte(conn)}
               SELECT {{select}} FROM stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku
               WHERE o.qty_ordered IS NOT NULL AND {bucket} = {_trunc(scope.bucket, '?')}{sf}{extra} {{group}}"""  # nosec B608 - literals; values bind
    params = [period, *sp, *ep]

    def top_by(key: str) -> list[dict[str, Any]]:
        return _clean(_rows(conn, base.format(select=f"{key} AS id, sum(o.qty_ordered) AS ordered, {shipped}, count(*) AS lines, count(DISTINCT o.customer_id) AS customers",
                                              group=f"GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT {TOP}"), params))

    skus, customers = top_by("o.sku"), top_by("o.customer_id")
    locations = top_by("o.location_id") if site_ok else []
    # change against the previous bucket, by product
    prev_sql = f"""WITH {_master_cte(conn)},
        cur AS (SELECT o.sku, sum(o.qty_ordered) AS q FROM stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku
                WHERE {bucket} = {_trunc(scope.bucket, '?')}{sf}{extra} GROUP BY 1),
        prev AS (SELECT o.sku, sum(o.qty_ordered) AS q FROM stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku
                 WHERE {bucket} = {_trunc(scope.bucket, '?')} - INTERVAL 1 {scope.bucket}{sf}{extra} GROUP BY 1)
        SELECT coalesce(cur.sku, prev.sku) AS sku, cur.q AS ordered, prev.q AS previous, coalesce(cur.q, 0) - coalesce(prev.q, 0) AS change
        FROM cur FULL OUTER JOIN prev ON prev.sku = cur.sku ORDER BY change {{dir}} LIMIT {TOP}"""  # nosec B608 - literals; values bind
    pparams = [period, *sp, *ep, period, *sp, *ep]
    increases = _clean(_rows(conn, prev_sql.format(dir="DESC"), pparams))
    declines = _clean(_rows(conn, prev_sql.format(dir="ASC"), pparams))
    involved = [r["id"] for r in skus]
    stock_rows: list[dict[str, Any]] = []
    po_rows: list[dict[str, Any]] = []
    if involved:
        placeholders = ", ".join("?" for _ in involved)
        stock_rows = _clean(_rows(conn, f"""WITH {_stock_cte(conn)}, {_demand_cte(conn)}
            SELECT st.sku, st.on_hand, st.in_transit, st.sites, d.weekly_demand,
                   CASE WHEN d.weekly_demand > 0 THEN st.on_hand / d.weekly_demand END AS weeks_of_cover
            FROM stock st LEFT JOIN demand d ON d.sku = st.sku WHERE st.sku IN ({placeholders}) ORDER BY st.on_hand DESC""", involved))  # nosec B608 - literals; values bind
        if has_table(conn, "stg_fmcg_purchase_orders"):
            po_rows = _clean(_rows(conn, f"""WITH {_open_po_cte(conn)}
                SELECT po_id, sku, supplier_id, po_date, eta, open_units FROM po_state
                WHERE open_units > 0 AND sku IN ({placeholders}) ORDER BY eta NULLS LAST, po_id LIMIT {TOP * 2}""", involved))  # nosec B608 - literals; values bind
    related = [d for d in decisions_of_plan(plan) if d.get("sku") in set(involved)] if plan else []
    return {"available": True, "period": period.isoformat(), "bucket": scope.bucket,
            "top_skus": skus, "top_customers": customers, "top_locations": locations,
            "largest_increases": [r for r in increases if (r.get("change") or 0) > 0],
            "largest_declines": [r for r in declines if (r.get("change") or 0) < 0],
            "affected_inventory": stock_rows, "open_purchase_orders": po_rows, "related_decisions": related,
            "links": {"inventory": {"sku": involved[:1]}, "orders": {"po": [r["po_id"] for r in po_rows[:1]]},
                      "data": {"dataset": "customer_orders"}, "decisions": [d["id"] for d in related[:5]]},
            "provenance": provenance(conn, scope, source=["stg_fmcg_orders", "stg_fmcg_skus", "stg_fmcg_inventory", "stg_fmcg_purchase_orders"],
                                     metric="units ordered in one period, by product, customer and site; change against the previous period",
                                     numerator="sum(qty_ordered) in the period", denominator="every order line in the period after filters", plan=plan)}


# ── inventory ──────────────────────────────────────────────────────────────────

def inventory(conn: Any, scope: Scope, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inventory over time from the uploaded snapshots — never reconstructed."""
    if not _has_rows(conn, "stg_fmcg_inventory"):
        return {"available": False, "reason": "NO_DATA", "why": "No inventory snapshots have been uploaded.",
                "provenance": provenance(conn, scope, source=["stg_fmcg_inventory"], metric="units on hand", numerator="—", denominator="—")}
    sf, sp = _sku_filter(scope)
    rf, rp = _range(scope, "i.snapshot_date")
    site, site_p = "", []
    if scope.location:
        site = " AND CAST(i.location_id AS VARCHAR) = ?"
        site_p.append(scope.location)
    # one row per (snapshot, sku, site): the latest import wins, as the planning adapter reads it
    snap = f"""WITH {_master_cte(conn)},
        snaps AS (SELECT i.snapshot_date, i.sku, i.location_id, i.on_hand, coalesce(i.in_transit, 0) AS in_transit, m.category, m.unit_cost
                  FROM (SELECT *, row_number() OVER (PARTITION BY snapshot_date, sku, location_id ORDER BY imported_at DESC) AS rn FROM stg_fmcg_inventory) i
                  LEFT JOIN master m ON m.sku = i.sku WHERE i.rn = 1{sf}{rf}{site}),
        latest_in_bucket AS (SELECT {_trunc(scope.bucket, 'snapshot_date')} AS period, max(snapshot_date) AS snapshot_date FROM snaps GROUP BY 1)"""  # nosec B608 - literals; values bind
    params = [*sp, *rp, *site_p]
    series = _rows(conn, snap + """
        SELECT l.period, l.snapshot_date, sum(s.on_hand) AS units, sum(s.on_hand * s.unit_cost) AS value,
               count(*) FILTER (WHERE s.unit_cost IS NULL) AS rows_without_cost, sum(s.in_transit) AS in_transit,
               count(DISTINCT s.sku) AS products, count(DISTINCT s.location_id) AS sites
        FROM latest_in_bucket l JOIN snaps s ON s.snapshot_date = l.snapshot_date GROUP BY 1, 2 ORDER BY 1""", params)
    truncated = len(series) > MAX_POINTS
    series = series[-MAX_POINTS:]
    by_site_series = _rows(conn, snap + f"""
        SELECT l.period, CAST(s.location_id AS VARCHAR) AS location_id, sum(s.on_hand) AS units, sum(s.on_hand * s.unit_cost) AS value
        FROM latest_in_bucket l JOIN snaps s ON s.snapshot_date = l.snapshot_date GROUP BY 1, 2 ORDER BY 1, 2 LIMIT {MAX_POINTS * 12}""", params)  # nosec B608 - literal cap
    latest_date = _one(conn, snap + " SELECT max(snapshot_date) FROM snaps", params)
    by_site = _rows(conn, snap + """
        SELECT CAST(s.location_id AS VARCHAR) AS id, sum(s.on_hand) AS units, sum(s.on_hand * s.unit_cost) AS value, count(DISTINCT s.sku) AS products
        FROM snaps s WHERE s.snapshot_date = (SELECT max(snapshot_date) FROM snaps) GROUP BY 1 ORDER BY 2 DESC""", params)
    by_category = _rows(conn, snap + f"""
        SELECT s.category AS id, sum(s.on_hand) AS units, sum(s.on_hand * s.unit_cost) AS value, count(DISTINCT s.sku) AS products
        FROM snaps s WHERE s.snapshot_date = (SELECT max(snapshot_date) FROM snaps) GROUP BY 1 ORDER BY 2 DESC LIMIT {TOP}""", params)  # nosec B608 - literal cap
    # cover and inbound against the current position (catalog's own rules, so Inventory agrees)
    cover_rows = _rows(conn, f"""WITH {_master_cte(conn)}, {_stock_cte(conn, scope.location)}, {_demand_cte(conn, 12, scope.location)}, {_open_po_cte(conn, scope.location)}
        SELECT sum(st.on_hand) AS on_hand, sum(d.weekly_demand) AS weekly_demand, sum(op.inbound_units) AS inbound_units,
               count(*) FILTER (WHERE d.weekly_demand IS NULL) AS products_without_demand, count(*) AS products
        FROM stock st LEFT JOIN master m ON m.sku = st.sku LEFT JOIN demand d ON d.sku = st.sku LEFT JOIN open_po op ON op.sku = st.sku
        WHERE TRUE{sf}""", [*([scope.location] * (1 + (1 if site_column_usable(conn, 'stg_fmcg_orders', 'location_id') else 0) + (1 if site_column_usable(conn, 'stg_fmcg_purchase_orders', 'destination_id') else 0)) if scope.location else []), *sp])  # nosec B608 - literals; values bind
    cover = cover_rows[0] if cover_rows else {}
    weekly = _num(cover.get("weekly_demand"))
    on_hand = _num(cover.get("on_hand"))
    weeks_of_cover = (on_hand / weekly) if (weekly and on_hand is not None) else None
    return {"available": True, "series": _clean(series), "by_site_series": _clean(by_site_series), "truncated": truncated,
            "latest_snapshot": _plain(latest_date), "by_site": _clean(by_site), "by_category": _clean(by_category),
            "position": {"on_hand": on_hand, "inbound_units": _num(cover.get("inbound_units")), "weekly_demand": weekly,
                         "weeks_of_cover": weeks_of_cover, "products": cover.get("products"),
                         "products_without_demand": cover.get("products_without_demand"),
                         "cover_basis": "units on hand at the latest snapshot divided by average weekly units ordered over the last 12 weeks (the Inventory page's rule)",
                         "cover_reason": None if weeks_of_cover is not None else ("NOT_MEASURED" if weekly is None else "NO_DATA")},
            "provenance": provenance(conn, scope, source=["stg_fmcg_inventory", "stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders"],
                                     metric="units on hand at the latest snapshot in each period; value = units × unit cost from the SKU master",
                                     numerator="sum(on_hand) over the snapshot rows", denominator="every product and site in the snapshot after filters",
                                     coverage={"rows_without_cost": sum((r.get("rows_without_cost") or 0) for r in series[-1:]) if series else None,
                                               "snapshots": len(series)}, plan=plan)}


# ── supply ─────────────────────────────────────────────────────────────────────

def supply(conn: Any, scope: Scope, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Open orders by expected arrival, receipts by period, aging, and where supply comes from and goes."""
    if not _has_rows(conn, "stg_fmcg_purchase_orders"):
        return {"available": False, "reason": "NO_DATA", "why": "No purchase orders have been uploaded.",
                "provenance": provenance(conn, scope, source=["stg_fmcg_purchase_orders"], metric="open purchase-order units", numerator="—", denominator="—")}
    sf, sp = _sku_filter(scope)
    dest_ok = site_column_usable(conn, "stg_fmcg_purchase_orders", "destination_id")
    open_cte = _open_po_cte(conn, scope.location if dest_ok else None)
    site_params = [scope.location] if (scope.location and dest_ok) else []
    today = scope.end or date.today()
    base = f"""WITH {_master_cte(conn)}, {open_cte}
               SELECT {{select}} FROM po_state p LEFT JOIN master m ON m.sku = p.sku WHERE TRUE{sf} {{extra}} {{group}}"""  # nosec B608 - literals; values bind
    open_by_eta = _rows(conn, base.format(select=f"CASE WHEN p.eta IS NULL THEN NULL ELSE {_trunc(scope.bucket, 'p.eta')} END AS period, sum(p.open_units) AS units, count(DISTINCT p.po_id) AS orders",
                                          extra="AND p.open_units > 0", group="GROUP BY 1 ORDER BY 1 NULLS LAST"), [*site_params, *sp])
    open_by_eta = open_by_eta[:MAX_POINTS]
    no_eta = next((r for r in open_by_eta if r["period"] is None), None)
    aging = _rows(conn, base.format(select="""CASE WHEN date_diff('day', p.po_date, CAST(? AS DATE)) <= 14 THEN '0-2 weeks'
                                                  WHEN date_diff('day', p.po_date, CAST(? AS DATE)) <= 28 THEN '2-4 weeks'
                                                  WHEN date_diff('day', p.po_date, CAST(? AS DATE)) <= 56 THEN '4-8 weeks' ELSE 'over 8 weeks' END AS age,
                                              sum(p.open_units) AS units, count(DISTINCT p.po_id) AS orders""",
                                    extra="AND p.open_units > 0", group="GROUP BY 1 ORDER BY min(date_diff('day', p.po_date, CAST(? AS DATE)))"),
                  # positional binds follow the SQL text: the site CTE, the three CASE dates, the SKU-side filters, the ORDER BY date
                  [*site_params, today, today, today, *sp, today])
    late_open = _rows(conn, base.format(select="count(DISTINCT p.po_id) AS orders, sum(p.open_units) AS units, count(DISTINCT p.po_id) FILTER (WHERE p.eta IS NULL) AS orders_without_eta",
                                        extra="AND p.open_units > 0 AND (p.eta IS NULL OR p.eta < CAST(? AS DATE))", group=""), [*site_params, *sp, today])[0]
    by_supplier = _rows(conn, base.format(select="p.supplier_id AS id, sum(p.open_units) AS open_units, count(DISTINCT p.po_id) FILTER (WHERE p.open_units > 0) AS open_orders, sum(p.open_units * m.unit_cost) AS open_value",
                                          extra="", group=f"GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT {TOP}"), [*site_params, *sp])
    by_destination: Any
    if dest_ok:
        by_destination = _rows(conn, f"""WITH {_master_cte(conn)}, {_open_po_cte(conn)}
            SELECT CAST(d.destination_id AS VARCHAR) AS id, sum(p.open_units) AS open_units, count(DISTINCT p.po_id) FILTER (WHERE p.open_units > 0) AS open_orders
            FROM po_state p JOIN (SELECT po_id, sku, any_value(destination_id) AS destination_id FROM stg_fmcg_purchase_orders GROUP BY 1, 2) d
              ON d.po_id = p.po_id AND d.sku = p.sku LEFT JOIN master m ON m.sku = p.sku WHERE TRUE{sf} GROUP BY 1 ORDER BY 2 DESC LIMIT {TOP}""", sp)  # nosec B608 - literals; values bind
    else:
        by_destination = {"rows": [], "reason": "BLOCKED_BY_DATA", "why": "Purchase orders carry no destination site."}
    received: list[dict[str, Any]] = []
    if has_table(conn, "stg_fmcg_receipts"):
        rf, rp = _range(scope, "r.receipt_date")
        received = _rows(conn, f"""WITH {_master_cte(conn)}
            SELECT {_trunc(scope.bucket, 'r.receipt_date')} AS period, sum(r.qty_received) AS units, count(DISTINCT r.po_id) AS orders,
                   sum(coalesce(r.qty_rejected, 0)) AS rejected
            FROM stg_fmcg_receipts r LEFT JOIN (SELECT po_id, any_value(sku) AS sku FROM stg_fmcg_purchase_orders GROUP BY 1) h ON h.po_id = r.po_id
            LEFT JOIN master m ON m.sku = coalesce(r.sku, h.sku) WHERE TRUE{sf}{rf} GROUP BY 1 ORDER BY 1""", [*sp, *rp])[-MAX_POINTS:]  # nosec B608 - literals; values bind
    totals = _rows(conn, base.format(select="sum(p.open_units) AS open_units, count(DISTINCT p.po_id) FILTER (WHERE p.open_units > 0) AS open_orders, "
                                            "sum(p.open_units * m.unit_cost) AS open_value, count(*) FILTER (WHERE p.open_units > 0 AND m.unit_cost IS NULL) AS open_lines_without_cost",
                                     extra="", group=""), [*site_params, *sp])[0]
    return {"available": True, "as_of": today.isoformat(), "open_by_expected_arrival": _clean([r for r in open_by_eta if r["period"] is not None]),
            "open_without_expected_date": _clean([no_eta])[0] if no_eta else {"units": 0, "orders": 0},
            "received": _clean(received), "aging": _clean(aging), "late_open": _clean([late_open])[0],
            "by_supplier": _clean(by_supplier), "by_destination": _clean(by_destination) if isinstance(by_destination, list) else by_destination,
            "totals": _clean([totals])[0],
            "provenance": provenance(conn, scope, source=["stg_fmcg_purchase_orders", "stg_fmcg_receipts", "stg_fmcg_skus"],
                                     metric="units still owed on open purchase orders (open until the first receipt — the Purchase Orders page's rule) and units received per period",
                                     numerator="sum(open units) / sum(qty_received)", denominator="every purchase-order line after filters",
                                     coverage={"open_orders_without_expected_date": late_open.get("orders_without_eta")}, plan=plan)}


# ── suppliers ──────────────────────────────────────────────────────────────────

def suppliers(conn: Any, scope: Scope, operator: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Per supplier: fill, lead time, lateness — each with its denominator — plus exposure, share, rights, alternatives."""
    if not (_has_rows(conn, "stg_fmcg_purchase_orders") and _has_rows(conn, "stg_fmcg_receipts")):
        return {"available": False, "reason": "NO_DATA", "why": "Supplier performance needs purchase orders and receipts.",
                "provenance": provenance(conn, scope, source=["stg_fmcg_purchase_orders", "stg_fmcg_receipts"], metric="fill rate", numerator="—", denominator="—")}
    rf, rp = _range(scope, "x.po_date")
    where, params = " WHERE TRUE" + rf, [*rp]
    if scope.supplier:
        where += " AND x.supplier_id = ?"
        params.append(scope.supplier)
    if scope.sku:
        where += " AND x.first_sku = ? AND x.lines = 1"
        params.append(scope.sku)
    metrics_sql = f"""WITH {_matched_cte()}, x AS (SELECT * FROM matched)
        SELECT x.supplier_id, count(*) AS matched_orders, sum(x.ordered) AS units_ordered, sum(x.received) AS units_received,
               CASE WHEN sum(x.ordered) > 0 THEN sum(x.received) / sum(x.ordered) END AS fill_rate,
               avg(CASE WHEN x.fill < {SHORT_FILL_TOLERANCE} THEN 1.0 ELSE 0.0 END) AS short_fill_rate,
               count(*) FILTER (WHERE x.fill < {SHORT_FILL_TOLERANCE}) AS short_fills,
               quantile_cont(x.observed_lead_days, 0.5) AS p50_lead_days, quantile_cont(x.observed_lead_days, 0.9) AS p90_lead_days,
               count(*) FILTER (WHERE x.promised IS NOT NULL) AS orders_with_promise,
               count(*) FILTER (WHERE x.late_days IS NOT NULL AND x.late_days > 0) AS late_orders,
               CASE WHEN count(*) FILTER (WHERE x.promised IS NOT NULL) > 0
                    THEN count(*) FILTER (WHERE x.late_days > 0) * 1.0 / count(*) FILTER (WHERE x.promised IS NOT NULL) END AS late_rate,
               avg(CASE WHEN x.late_days > 0 THEN x.late_days END) AS mean_late_days
        FROM x{where} GROUP BY 1 ORDER BY units_ordered DESC NULLS LAST LIMIT 50"""  # nosec B608 - literals; values bind
    rows = _rows(conn, metrics_sql, params)
    for r in rows:
        r["lateness"] = (_null("NOT_MEASURED", f"None of the {int(r['matched_orders'])} matched orders carries a promised date.")
                         if not r.get("orders_with_promise") else
                         {"value": r["late_rate"], "numerator": r["late_orders"], "denominator": r["orders_with_promise"],
                          "thin": (r["orders_with_promise"] or 0) < THIN_SAMPLE,
                          "coverage": (r["orders_with_promise"] / r["matched_orders"]) if r.get("matched_orders") else None})
        r["fill"] = {"value": r["fill_rate"], "numerator": r["units_received"], "denominator": r["units_ordered"], "orders": r["matched_orders"],
                     "thin": (r["matched_orders"] or 0) < THIN_SAMPLE}
    trend = _rows(conn, f"""WITH {_matched_cte()}, x AS (SELECT * FROM matched)
        SELECT x.supplier_id, {_trunc('month', 'x.po_date')} AS period, count(*) AS matched_orders,
               CASE WHEN sum(x.ordered) > 0 THEN sum(x.received) / sum(x.ordered) END AS fill_rate,
               quantile_cont(x.observed_lead_days, 0.5) AS p50_lead_days,
               count(*) FILTER (WHERE x.promised IS NOT NULL) AS orders_with_promise,
               count(*) FILTER (WHERE x.late_days > 0) AS late_orders,
               count(*) FILTER (WHERE x.fill < {SHORT_FILL_TOLERANCE}) AS short_fills
        FROM x{where} GROUP BY 1, 2 ORDER BY 1, 2""", params)[-MAX_POINTS * 6:]  # nosec B608 - literals; values bind
    for r in trend:
        r["late_rate"] = (r["late_orders"] / r["orders_with_promise"]) if r.get("orders_with_promise") else None
        r["late_reason"] = None if r.get("orders_with_promise") else "NOT_MEASURED"
    exposure = _rows(conn, f"""WITH {_master_cte(conn)}, {_open_po_cte(conn)}
        SELECT p.supplier_id AS id, sum(p.open_units) AS open_units, sum(p.open_units * m.unit_cost) AS open_value,
               count(DISTINCT p.po_id) FILTER (WHERE p.open_units > 0) AS open_orders
        FROM po_state p LEFT JOIN master m ON m.sku = p.sku GROUP BY 1""")  # nosec B608 - literals
    share_rows = _rows(conn, f"""SELECT supplier_id AS id, sum(qty_ordered) AS units, sum(qty_ordered * coalesce(unit_cost, 0)) AS value
                                 FROM stg_fmcg_purchase_orders x WHERE TRUE{rf} GROUP BY 1""", rp)  # nosec B608 - literals; values bind
    total_units = sum(float(r["units"] or 0) for r in share_rows)
    share = {r["id"]: (float(r["units"] or 0) / total_units if total_units else None) for r in share_rows}
    rights: dict[str, int] = {}
    if has_table(conn, "stg_po_commitments"):
        for r in _rows(conn, """SELECT h.supplier_id AS id, count(DISTINCT c.po_id) AS n FROM stg_po_commitments c
                                JOIN (SELECT po_id, any_value(supplier_id) AS supplier_id FROM stg_fmcg_purchase_orders GROUP BY 1) h ON h.po_id = c.po_id
                                WHERE c.operator_id = ? GROUP BY 1""", [operator]):
            rights[r["id"]] = int(r["n"])
    alternatives: dict[str, int] = {}
    alternative_for: dict[str, int] = {}
    if has_table(conn, "stg_fmcg_sources"):
        for r in _rows(conn, """SELECT s.supplier_id AS alt, m.supplier_id AS incumbent, count(DISTINCT s.sku) AS n
                                FROM stg_fmcg_sources s JOIN (SELECT sku, any_value(supplier_id) AS supplier_id FROM stg_fmcg_skus GROUP BY 1) m ON m.sku = s.sku
                                WHERE coalesce(s.approved, TRUE) AND s.supplier_id <> m.supplier_id GROUP BY 1, 2"""):
            alternatives[r["incumbent"]] = alternatives.get(r["incumbent"], 0) + int(r["n"])
            alternative_for[r["alt"]] = alternative_for.get(r["alt"], 0) + int(r["n"])
    ex = {r["id"]: r for r in exposure}
    for r in rows:
        sid = r["supplier_id"]
        r["exposure"] = _clean([ex.get(sid) or {"open_units": 0, "open_value": None, "open_orders": 0}])[0]
        r["share_of_units_ordered"] = share.get(sid)
        r["amendment_rights_on_open_orders"] = rights.get(sid, 0)
        r["products_with_declared_alternative"] = alternatives.get(sid, 0)
        r["alternative_for_products"] = alternative_for.get(sid, 0)
    sourcing = None
    if plan and plan["report"].get("sourcing"):
        sourcing = {"present": True, "note": "The latest plan carries a sourcing block (P3); the recommended split is on Decisions."}
    return {"available": True, "suppliers": _clean(rows), "trend": _clean(trend), "share_basis": "share of units ordered on purchase orders in the range",
            "short_fill_tolerance": SHORT_FILL_TOLERANCE, "thin_sample": THIN_SAMPLE, "sourcing": sourcing,
            "provenance": provenance(conn, scope, source=["stg_fmcg_purchase_orders", "stg_fmcg_receipts", "stg_po_commitments", "stg_fmcg_sources"],
                                     metric="fill rate = units received / units ordered on matched orders; lateness = orders received after the promised date / orders that carry a promised date",
                                     numerator="stated per row", denominator="stated per row; an order without a promised date is outside the lateness denominator, never counted on time",
                                     plan=plan)}


# ── service and customers ──────────────────────────────────────────────────────

def service(conn: Any, scope: Scope, operator: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ordered, shipped, unfulfilled and service level by customer and by declared service class; the
    latest plan's allocation block where it exists."""
    if not _has_rows(conn, "stg_fmcg_orders"):
        return {"available": False, "reason": "NO_DATA", "why": "No customer orders have been uploaded."}
    shipped_col = "qty_shipped" in _columns(conn, "stg_fmcg_orders")
    sf, sp = _sku_filter(scope)
    rf, rp = _range(scope, "o.order_date")
    extra, ep = "", []
    if scope.customer:
        extra += " AND o.customer_id = ?"
        ep.append(scope.customer)
    if scope.location and site_column_usable(conn, "stg_fmcg_orders", "location_id"):
        extra += " AND CAST(o.location_id AS VARCHAR) = ?"
        ep.append(scope.location)
    shipped = ("sum(o.qty_shipped) AS shipped, sum(CASE WHEN o.qty_shipped IS NOT NULL THEN o.qty_ordered END) AS ordered_measured, "
               "count(*) FILTER (WHERE o.qty_shipped IS NOT NULL AND o.qty_shipped < o.qty_ordered) AS lines_short, "
               "count(*) FILTER (WHERE o.qty_shipped IS NULL) AS lines_unmeasured") if shipped_col else \
        "NULL AS shipped, NULL AS ordered_measured, NULL AS lines_short, count(*) AS lines_unmeasured"
    classes: dict[str, str] = {}
    if has_table(conn, "stg_atp_customer_orders"):
        for r in _rows(conn, "SELECT customer_id, any_value(service_class) AS c FROM stg_atp_customer_orders WHERE operator_id = ? GROUP BY 1", [operator]):
            classes[r["customer_id"]] = r["c"]
    by_customer = _rows(conn, f"""WITH {_master_cte(conn)}
        SELECT o.customer_id AS id, sum(o.qty_ordered) AS ordered, {shipped}, count(*) AS lines
        FROM stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku WHERE o.qty_ordered IS NOT NULL{sf}{rf}{extra}
        GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT 50""", [*sp, *rp, *ep])  # nosec B608 - literals; values bind
    for r in by_customer:
        measured = shipped_col and r.get("ordered_measured")
        r["unfulfilled"] = (r["ordered_measured"] - r["shipped"]) if measured else None
        r["service_level"] = ({"value": r["shipped"] / r["ordered_measured"], "numerator": r["shipped"], "denominator": r["ordered_measured"],
                               "basis": "units shipped / units ordered on lines that record a shipped quantity"}
                              if measured else _null("NOT_MEASURED", "No line for this customer records a shipped quantity."))
        r["service_class"] = classes.get(r["id"]) or None
        r["service_class_reason"] = None if classes.get(r["id"]) else "NOT_APPLICABLE"
    by_class: dict[str, dict[str, Any]] = {}
    for r in by_customer:
        key = r["service_class"] or "not declared"
        agg = by_class.setdefault(key, {"id": key, "customers": 0, "ordered": 0., "shipped": 0., "ordered_measured": 0.})
        agg["customers"] += 1
        agg["ordered"] += float(r["ordered"] or 0)
        if r.get("shipped") is not None:
            agg["shipped"] += float(r["shipped"])
            agg["ordered_measured"] += float(r["ordered_measured"] or 0)
    for agg in by_class.values():
        agg["service_level"] = (agg["shipped"] / agg["ordered_measured"]) if agg["ordered_measured"] else None
    series = _rows(conn, f"""WITH {_master_cte(conn)}
        SELECT {_trunc(scope.bucket, 'o.order_date')} AS period, sum(o.qty_ordered) AS ordered, {shipped}, count(*) AS lines
        FROM stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku WHERE o.qty_ordered IS NOT NULL{sf}{rf}{extra}
        GROUP BY 1 ORDER BY 1""", [*sp, *rp, *ep])[-MAX_POINTS:]  # nosec B608 - literals; values bind
    for r in series:
        measured = shipped_col and r.get("ordered_measured")
        r["unfulfilled"] = (r["ordered_measured"] - r["shipped"]) if measured else None
        r["service_level"] = (r["shipped"] / r["ordered_measured"]) if measured else None
    declared_classes = _clean(_rows(conn, "SELECT class_id, contractual_service_floor, strategic, tier, provenance FROM stg_atp_service_classes WHERE operator_id = ? ORDER BY 1",
                                    [operator])) if has_table(conn, "stg_atp_service_classes") else []
    atp: dict[str, Any]
    if plan and plan["report"].get("atp"):
        block = plan["report"]["atp"]
        orders = block.get("orders") if isinstance(block, dict) else None
        atp = {"present": True, "note": "Read from the latest plan's allocation block (P5); nothing recomputed.",
               "summary": {k: block.get(k) for k in ("status", "policy", "verdict", "promised_units", "unpromised_units", "orders_promised", "orders_short") if isinstance(block, dict) and k in block},
               "orders": (orders or [])[:TOP * 2] if isinstance(orders, list) else []}
    else:
        atp = {"present": False, "reason": "NOT_IN_PLAN",
               "why": ("The latest plan carries no allocation block; declare service classes and open customer orders and ask for allocation to see it."
                       if plan else "No completed plan exists yet.")}
    return {"available": True, "fulfilment": "MEASURED" if shipped_col else "NOT_MEASURED", "series": _clean(series),
            "by_customer": _clean(by_customer), "by_service_class": _clean(list(by_class.values())), "declared_service_classes": declared_classes,
            "atp": atp, "risk_scores": _null("NOT_APPLICABLE", "ZAAD does not score customers. Exposure is the recorded shortfall and the declared class."),
            "provenance": provenance(conn, scope, source=["stg_fmcg_orders", "stg_atp_customer_orders", "stg_atp_service_classes"],
                                     metric="service level = units shipped / units ordered, on lines that record a shipped quantity",
                                     numerator="sum(qty_shipped)", denominator="sum(qty_ordered) where qty_shipped is recorded; unmeasured lines are counted and excluded",
                                     plan=plan)}


# ── decisions and value ────────────────────────────────────────────────────────

def decisions(conn: Any, operator: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """What the latest plan recommends, by verb, and what people did with it: responses, proposals,
    external actions, outcomes. Counts of rows; the plan is read verbatim."""
    flat = decisions_of_plan(plan)
    by_verb = {verb: sum(1 for d in flat if d["kind"] == "open_po" and d["verb"] == verb) for verb in AMENDMENT_VERBS}
    other = {"BUY": sum(1 for d in flat if d["kind"] == "purchase"), "MOVE": sum(1 for d in flat if d["kind"] == "transfer")}
    responses: list[dict[str, Any]] = []
    drafts_by_state: list[dict[str, Any]] = []
    drafts_by_origin: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    outcomes = {"recorded": 0, "with_comparator": 0, "drafts_with_outcomes": 0}
    if has_table(conn, "zaad_decision_responses"):
        responses = _rows(conn, "SELECT status, count(*) AS n, count(*) FILTER (WHERE job_id = ?) AS for_latest_plan FROM zaad_decision_responses WHERE operator_id = ? GROUP BY 1 ORDER BY 1",
                          [plan["job_id"] if plan else "", operator])
    if has_table(conn, "zaad_draft_orders"):
        drafts_by_state = _rows(conn, "SELECT state, count(*) AS n FROM zaad_draft_orders WHERE operator_id = ? GROUP BY 1 ORDER BY 1", [operator])
        drafts_by_origin = _rows(conn, "SELECT origin, coalesce(amendment_action, '') AS amendment_action, count(*) AS n FROM zaad_draft_orders WHERE operator_id = ? GROUP BY 1, 2 ORDER BY 1, 2", [operator])
        external = _rows(conn, "SELECT external_status, count(*) AS n FROM zaad_draft_orders WHERE operator_id = ? AND external_status IS NOT NULL GROUP BY 1 ORDER BY 1", [operator])
    if has_table(conn, "zaad_outcomes"):
        row = _rows(conn, "SELECT count(*) AS recorded, count(*) FILTER (WHERE comparator_value IS NOT NULL AND comparator_basis IS NOT NULL) AS with_comparator, "
                          "count(DISTINCT draft_id) AS drafts_with_outcomes FROM zaad_outcomes WHERE operator_id = ?", [operator])[0]
        outcomes = {k: int(row[k] or 0) for k in outcomes}
    recent = flat[:TOP * 2]
    return {"plan": plan_summary(plan), "recommended": {"open_po_by_verb": by_verb, "other": other, "total": len(flat)},
            "responses": _clean(responses), "proposals_by_state": _clean(drafts_by_state), "proposals_by_origin": _clean(drafts_by_origin),
            "external_status": _clean(external), "outcomes": outcomes, "decisions": recent,
            "registers": {"recommended": "the latest plan's verdicts, read verbatim", "approved": "proposals in APPROVED or EXPORTED",
                          "rejected": "proposals in REJECTED and responses in REJECTED", "overridden": "responses in OVERRIDDEN",
                          "externally_executed": "proposals with a human-recorded external status", "outcome_available": "proposals with at least one recorded outcome"},
            "provenance": provenance(conn, Scope(), source=["job store (latest DONE workspace plan)", "zaad_decision_responses", "zaad_draft_orders", "zaad_outcomes"],
                                     metric="counts of decisions, responses, proposals, external statuses and outcomes", numerator="count(rows)", denominator="all rows of this workspace", plan=plan)}


def _ledger_total(costs: dict[str, Any] | None) -> float | None:
    return _num((costs or {}).get("TOTAL"))


def value(conn: Any, operator: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Five registers, each its own number with its own basis. Never one 'savings'."""
    registers: dict[str, Any] = {}
    currency = None
    if plan:
        econ = plan["report"].get("economics") or {}
        currency = (plan.get("request") or {}).get("currency")
        inc, sel = _ledger_total(econ.get("incumbent_costs")), _ledger_total(econ.get("selected_costs"))
        registers["MODELED_DIFFERENCE"] = {
            "available": inc is not None and sel is not None, "currency": currency,
            "incumbent_total": inc, "selected_total": sel, "difference": (inc - sel) if (inc is not None and sel is not None) else None,
            "ledger": [{"component": k, "incumbent": _num((econ.get("incumbent_costs") or {}).get(k)), "selected": _num((econ.get("selected_costs") or {}).get(k))}
                       for k in (econ.get("selected_costs") or {}) if k != "TOTAL"],
            "basis": "The engine's own ledger for the latest plan: the cost it projects for your current policy minus the cost of what it recommends, over the same products and information. A modelled difference, not a saving.",
            "plan": {k: plan.get(k) for k in ("job_id", "as_of", "finished_at", "stale")}}
    else:
        registers["MODELED_DIFFERENCE"] = {"available": False, "reason": "NOT_IN_PLAN", "why": "No completed plan exists yet."}
    registers["BACKTESTED_OPPORTUNITY"] = {"available": False, "reason": "NOT_MEASURED", "why": "No held-out replay of your history is wired into this product."}
    approved: list[dict[str, Any]] = []
    if has_table(conn, "zaad_draft_orders") and has_table(conn, "zaad_evaluations") and os.getenv("ZAAD_JOB_STORE"):
        from api.product import evaluation as evaluation_module
        from zaad.full.jobs import JobStore
        store = JobStore(Path(os.environ["ZAAD_JOB_STORE"]))
        rows = _rows(conn, """SELECT d.draft_id, d.reference, d.state, d.approved_evaluation_id, d.currency, d.origin, d.amendment_action,
                                     e.baseline_job_id, e.proposal_job_id, e.scope_skus, e.amendment_json, e.note
                              FROM zaad_draft_orders d JOIN zaad_evaluations e ON e.evaluation_id = d.approved_evaluation_id AND e.operator_id = d.operator_id
                              WHERE d.operator_id = ? AND d.state IN ('APPROVED', 'EXPORTED') ORDER BY d.updated_at DESC LIMIT 25""", [operator])
        for r in rows:
            try:
                base = store.get(r["baseline_job_id"], operator).get("report") if r.get("baseline_job_id") else None
                prop = store.get(r["proposal_job_id"], operator).get("report") if r.get("proposal_job_id") else None
            except KeyError:
                base = prop = None
            if not base or not prop:
                approved.append({"draft_id": r["draft_id"], "reference": r["reference"], "available": False, "reason": "UNKNOWN", "why": "The evaluation's runs are no longer in the job store."})
                continue
            draft = {"origin": r["origin"], "amendment_action": r["amendment_action"], "currency": r["currency"]}
            comparison = evaluation_module.compare(base, prop, draft=draft, scope=json.loads(r["scope_skus"] or "[]"), currency=str(r["currency"] or currency or "USD"),
                                                    amendment_terms=json.loads(r["amendment_json"]) if r.get("amendment_json") else None)
            total = next((row for row in comparison.get("ledger", []) if row.get("component") == "TOTAL"), None)
            approved.append({"draft_id": r["draft_id"], "reference": r["reference"], "state": r["state"], "available": total is not None,
                             "currency": comparison.get("currency"),
                             "proposal_vs_current": _num(total.get("proposal_vs_current")) if total else None,
                             "zaad_vs_current": _num(total.get("zaad_vs_current")) if total else None,
                             "contract_net_difference": _num((comparison.get("contract_terms") or {}).get("net_difference"))})
    registers["APPROVED_EXPECTED_DIFFERENCE"] = {
        "available": bool(approved), "reason": None if approved else "NO_DATA", "why": None if approved else "No approved proposal carries an evaluation.",
        "proposals": approved,
        "basis": "For each approved proposal, its evaluation's modelled difference between the workspace with the proposal and without it, at approval time. Expected, not observed."}
    observed_rows: list[dict[str, Any]] = []
    realized_rows: list[dict[str, Any]] = []
    if has_table(conn, "zaad_outcomes"):
        observed_rows = _rows(conn, "SELECT metric, unit, count(*) AS n, sum(value) AS total, min(observed_at) AS first_observed, max(observed_at) AS last_observed "
                                    "FROM zaad_outcomes WHERE operator_id = ? GROUP BY 1, 2 ORDER BY 1", [operator])
        realized_rows = _rows(conn, "SELECT draft_id, metric, unit, value, comparator_value, comparator_basis, observed_at, "
                                    "CASE WHEN value IS NOT NULL THEN comparator_value - value END AS difference "
                                    "FROM zaad_outcomes WHERE operator_id = ? AND comparator_value IS NOT NULL AND comparator_basis IS NOT NULL "
                                    "ORDER BY observed_at DESC NULLS LAST LIMIT 50", [operator])
    registers["OBSERVED_AFTER_ACTION"] = {"available": bool(observed_rows), "reason": None if observed_rows else "NO_DATA",
                                          "why": None if observed_rows else "No outcome has been recorded after an action yet.",
                                          "by_metric": _clean(observed_rows),
                                          "basis": "Values recorded after an approved action was placed. Observed after action; not attributed to ZAAD."}
    registers["REALIZED_VALUE"] = {"available": bool(realized_rows), "reason": None if realized_rows else "NO_DATA",
                                   "why": None if realized_rows else "No outcome carries a stated comparator, so nothing is realized value yet.",
                                   "rows": _clean(realized_rows),
                                   "basis": "An observed outcome against a comparator whose basis is stated on the row (what it is and where it comes from). Only these rows may be called realized."}
    return {"registers": registers, "order": list(VALUE_REGISTERS), "currency": currency,
            "never_combined": "These five registers are different kinds of statement and are never added into one number.",
            "provenance": provenance(conn, Scope(), source=["job store (plan ledgers, evaluation runs)", "zaad_draft_orders", "zaad_evaluations", "zaad_outcomes"],
                                     metric="five value registers, each read from its own record", numerator="stated per register", denominator="stated per register", plan=plan)}


# ── engine connectivity ────────────────────────────────────────────────────────

def connectivity(conn: Any, operator: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every released engine family: where it comes from, where it shows, or that it is not visualized."""
    report = (plan or {}).get("report") or {}
    declared_sources = bool(has_table(conn, "stg_fmcg_sources") and _one(conn, "SELECT count(*) FROM stg_fmcg_sources"))
    declared_rights = bool(has_table(conn, "stg_po_commitments") and _one(conn, "SELECT count(*) FROM stg_po_commitments WHERE operator_id = ?", [operator]))
    declared_atp = bool(has_table(conn, "stg_atp_customer_orders") and _one(conn, "SELECT count(*) FROM stg_atp_customer_orders WHERE operator_id = ?", [operator]))
    declared_sites = bool(has_table(conn, "stg_fmcg_locations") and (_one(conn, "SELECT count(*) FROM stg_fmcg_locations") or 0) > 1)
    declared_recourse = bool(has_table(conn, "stg_recourse_spec") and _one(conn, "SELECT count(*) FROM stg_recourse_spec"))
    sector = bool(has_table(conn, "stg_fmcg_skus") and "sector" in _columns(conn, "stg_fmcg_skus") and _one(conn, "SELECT count(*) FROM stg_fmcg_skus WHERE sector IS NOT NULL"))

    def status(in_plan: bool, declared: bool, visual: bool) -> str:
        if not plan:
            return "NO_PLAN"
        if in_plan and visual:
            return "VISUALIZED"
        if in_plan:
            return "IN_PLAN_NOT_VISUALIZED"
        return "NOT_IN_PLAN" if declared else "NOT_DECLARED"

    rows = [
        {"family": "P0", "name": "Protection and recovery", "backend_source": "report.protection, report.status, report.reasons", "api": "/api/zaad/network/jobs/{id}; /api/zaad/insights/decisions",
         "visualization": "Decisions & Value (plan status, verdict); Decisions page", "drilldown": "Decision detail", "in_plan": bool(report), "declared": True,
         "status": status(bool(report), True, True)},
        {"family": "P1", "name": "Purchasing economics", "backend_source": "report.economics (incumbent_costs, selected_costs, working capital)", "api": "/api/zaad/insights/value",
         "visualization": "Decisions & Value — MODELED_DIFFERENCE ledger", "drilldown": "Decision detail economics", "in_plan": bool(report.get("economics")), "declared": True,
         "status": status(bool(report.get("economics")), True, True)},
        {"family": "P2", "name": "Multi-echelon network", "backend_source": "report.network, report.actions (transfer), request.locations / transfers", "api": "/api/zaad/insights/inventory?location=; /api/zaad/workspace/locations",
         "visualization": "Inventory by site and the site series; Network page", "drilldown": "Inventory filtered by site; transfer decisions", "in_plan": bool(report.get("network")), "declared": declared_sites,
         "status": status(bool(report.get("network")), declared_sites, True)},
        {"family": "Sector physics", "name": "Produce / meat-seafood physics", "backend_source": "stg_fmcg_skus sector columns; report.limitations", "api": "/api/zaad/workspace/sector",
         "visualization": "Perishability tab (only when a sector is declared); Diagnostics", "drilldown": "Diagnostics sector table", "in_plan": sector, "declared": sector,
         "status": ("VISUALIZED" if sector else "NOT_DECLARED")},
        {"family": "P3", "name": "Sourcing portfolio", "backend_source": "report.sourcing; stg_fmcg_sources", "api": "/api/zaad/insights/suppliers (alternatives, share)",
         "visualization": "Supply & Suppliers — declared alternatives and share; recommended split on Decisions", "drilldown": "Supplier page", "in_plan": bool(report.get("sourcing")), "declared": declared_sources,
         "status": status(bool(report.get("sourcing")), declared_sources, True)},
        {"family": "P4", "name": "Adaptive recourse", "backend_source": "report.recourse; stg_recourse_spec", "api": "/api/zaad/network/jobs/{id}",
         "visualization": "Not visualized in Insights: the value of adaptation is reported in the plan's recourse block only", "drilldown": "—", "in_plan": bool(report.get("recourse")), "declared": declared_recourse,
         "status": status(bool(report.get("recourse")), declared_recourse, False)},
        {"family": "P5", "name": "ATP / customer allocation", "backend_source": "report.atp; stg_atp_customer_orders, stg_atp_service_classes", "api": "/api/zaad/insights/service",
         "visualization": "Service & Customers — allocation block and declared classes", "drilldown": "Customer rows", "in_plan": bool(report.get("atp")), "declared": declared_atp,
         "status": status(bool(report.get("atp")), declared_atp, True)},
        {"family": "P4B", "name": "Open PO / commitment intervention", "backend_source": "report.commitments.orders; stg_po_commitments, stg_po_options", "api": "/api/zaad/insights/decisions",
         "visualization": "Decisions & Value — verdicts by verb (KEEP / DEFER / EXPEDITE / REDUCE / CANCEL / SPLIT)", "drilldown": "Decision detail; Purchase Orders", "in_plan": bool(report.get("commitments")), "declared": declared_rights,
         "status": status(bool(report.get("commitments")), declared_rights, True)},
    ]
    return {"plan": plan_summary(plan), "families": rows,
            "note": "A family is VISUALIZED when the latest plan carries its block and an Insights surface draws it; NOT_IN_PLAN when the data is declared but the plan did not include it; NOT_DECLARED when the workspace declares nothing for it. Nothing here is computed from the engine; it reads what the plan wrote."}


# ── overview ───────────────────────────────────────────────────────────────────

def overview(conn: Any, scope: Scope, operator: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """The headline of every tab, on one page, from the same functions the tabs use."""
    twelve = Scope(start=(scope.end or date.today()) - timedelta(weeks=12), end=scope.end, bucket="week",
                   sku=scope.sku, category=scope.category, brand=scope.brand, customer=scope.customer, location=scope.location, supplier=scope.supplier)
    d = demand(conn, twelve, plan)
    inv = inventory(conn, Scope(bucket="month", sku=scope.sku, category=scope.category, brand=scope.brand, location=scope.location, supplier=scope.supplier), plan)
    sup = supply(conn, Scope(bucket="week", end=scope.end, sku=scope.sku, category=scope.category, brand=scope.brand, location=scope.location, supplier=scope.supplier), plan)
    dec = decisions(conn, operator, plan)
    return {"plan": plan_summary(plan), "data_last_updated": _last_updated(conn),
            "demand": {"available": d.get("available", False), "label": d.get("label"), "series": d.get("series", []), "fulfilment": d.get("fulfilment"),
                       "totals": d.get("totals"), "period_over_period": d.get("period_over_period"), "concentration": d.get("concentration")},
            "inventory": {"available": inv.get("available", False), "position": inv.get("position"), "by_site": inv.get("by_site", []),
                          "series": (inv.get("series") or [])[-12:], "latest_snapshot": inv.get("latest_snapshot")},
            "supply": {"available": sup.get("available", False), "totals": sup.get("totals"), "late_open": sup.get("late_open"),
                       "open_without_expected_date": sup.get("open_without_expected_date"), "by_supplier": (sup.get("by_supplier") or [])[:5]},
            "decisions": {"recommended": dec.get("recommended"), "responses": dec.get("responses"), "proposals_by_state": dec.get("proposals_by_state"),
                          "external_status": dec.get("external_status"), "outcomes": dec.get("outcomes")},
            "scope": scope.as_dict()}
