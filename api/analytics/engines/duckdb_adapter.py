"""The DuckDB adapter: renders a `PhysicalPlan` against the operator's own vault.

The only module in the analytics package that writes SQL. Every fragment is a code literal; every
request value binds as a parameter; every fact is projected once into a filtered `base` relation
(dimension values and the raw columns the measures need) and everything else — grouping, top-N,
ranking, the latest snapshot per period — reads `base`. The fragments reuse the released modules'
own rules so that a number in Explore is the number Inventory, Purchase orders, Diagnostics and
Insights already show:

  * the product master is one row per SKU (latest import), as `insights._master_cte` reads it;
  * an order is open until its first receipt (`catalog._open_po_cte`);
  * supplier measures are taken on matched orders (`diagnostics._matched_cte`);
  * a period's stock is the latest snapshot in the period, never a sum of snapshots;
  * weeks of cover is on hand ÷ (units ordered in the trailing 12 weeks ÷ 12) (`catalog._demand_cte`).

A dimension the vault cannot carry (orders without a site, a master without a brand column) is
reported as blocked with its reason; the engine never substitutes a default member.
"""
from __future__ import annotations

import threading
import time
from datetime import date, timedelta
from typing import Any

import duckdb

from api.analytics.contracts import AnalyticsRefused
from api.analytics.engines.base import EngineResult, PhysicalPlan, PlanDimension, PlanFilter
from api.analytics.semantic import COVER_WEEKS, DIMENSIONS, SHORT_FILL_TOLERANCE, MetricContract
from api.product import queries
from api.product.catalog import _columns, _one, _rows, has_table, site_column_usable
from api.product.diagnostics import _matched_cte

OTHERS = "(others)"
_RAW_CAP = 20_000   # rows the engine will group before a query is declared too wide


def _trunc(grain: str, column: str) -> str:
    assert grain in ("day", "week", "month", "quarter", "year"), grain
    return f"date_trunc('{grain}', CAST({column} AS DATE))"


def _master_cte(conn: Any) -> str:
    cols = _columns(conn, "stg_fmcg_skus") if has_table(conn, "stg_fmcg_skus") else set()
    if not cols:
        return ("master AS (SELECT NULL AS sku, NULL AS sku_name, NULL AS category, NULL AS sub_category, NULL AS brand, NULL AS abc_class, "
                "NULL AS sector, NULL AS supplier_id, NULL AS unit_cost WHERE FALSE)")

    def col(name: str) -> str:
        return f"any_value({name})" if name in cols else "CAST(NULL AS VARCHAR)"

    return (f"master AS (SELECT sku, {col('sku_name')} AS sku_name, {col('category')} AS category, {col('sub_category')} AS sub_category, "  # nosec B608 - code literals; values bind
            f"{col('brand')} AS brand, {col('abc_class')} AS abc_class, {col('sector')} AS sector, {col('supplier_id')} AS supplier_id, "
            f"{'any_value(unit_cost)' if 'unit_cost' in cols else 'CAST(NULL AS DOUBLE)'} AS unit_cost FROM stg_fmcg_skus GROUP BY sku)")


def _supplier_cte(conn: Any) -> str:
    if not has_table(conn, "stg_fmcg_suppliers"):
        return "sup AS (SELECT NULL AS supplier_id, NULL AS supplier_name, NULL AS origin_iso3, NULL AS route WHERE FALSE)"
    cols = _columns(conn, "stg_fmcg_suppliers")

    def col(name: str) -> str:
        return f"any_value({name})" if name in cols else "CAST(NULL AS VARCHAR)"

    return (f"sup AS (SELECT supplier_id, {col('supplier_name')} AS supplier_name, {col('origin_iso3')} AS origin_iso3, {col('route')} AS route "  # nosec B608 - code literals; values bind
            "FROM stg_fmcg_suppliers WHERE supplier_id IS NOT NULL GROUP BY supplier_id)")


def _has_rows(conn: Any, table: str) -> bool:
    return has_table(conn, table) and bool(_one(conn, f"SELECT count(*) FROM {table}"))  # noqa: S608  # nosec B608 - literal table names


class _Fact:
    """How one fact is projected: its CTEs, the FROM clause, the dimension expressions, the raw
    columns and the aggregate expressions per metric. Built per connection so optional columns
    are checked against the vault, never assumed."""

    def __init__(self, conn: Any, plan: PhysicalPlan, operator: str):
        self.conn, self.plan, self.operator = conn, plan, operator
        self.ctes: list[str] = []
        self.from_sql = ""
        self.where: list[str] = []
        self.params: list[Any] = []
        self.dims: dict[str, str | None] = {}   # dimension id → expression over the fact aliases (None = not carried)
        self.blocked: dict[str, tuple[str, str]] = {}
        self.anchor_expr: str = ""
        self.raw: dict[str, str] = {}
        self.agg: dict[str, Any] = {}
        self.available = True
        self.empty_reason: tuple[str, str] | None = None
        self.snapshot = False                   # latest-snapshot semantics
        self.cutoff_expr = ""
        getattr(self, f"_{plan.fact}")()

    # ── facts ──

    def _customer_order_line(self) -> None:
        conn = self.conn
        if not _has_rows(conn, "stg_fmcg_orders"):
            self.available, self.empty_reason = False, ("NO_DATA", "No customer orders have been uploaded.")
            return
        cols = _columns(conn, "stg_fmcg_orders")
        self.ctes.append(_master_cte(conn))
        self.from_sql = "stg_fmcg_orders o LEFT JOIN master m ON m.sku = o.sku"
        self.where.append("o.qty_ordered IS NOT NULL")
        self.dims = {"sku": "o.sku", "product": "coalesce(m.sku_name, o.sku)", "category": "m.category", "sub_category": "m.sub_category",
                     "brand": "m.brand", "abc_class": "m.abc_class", "sector": "m.sector", "supplier": "m.supplier_id",
                     "customer": "o.customer_id", "channel": "o.channel" if "channel" in cols else None}
        if site_column_usable(conn, "stg_fmcg_orders", "location_id"):
            self.dims["location"] = "CAST(o.location_id AS VARCHAR)"
        else:
            self.blocked["location"] = ("BLOCKED_BY_DATA", "Customer orders carry no site, so nothing here can be broken down or filtered by site.")
        anchors = {"order_date": "o.order_date", "requested_delivery_date": "o.requested_delivery_date"}
        self.anchor_expr = anchors.get(self.plan.anchor) or "o.order_date"
        self.cutoff_expr = "max(o.order_date)"
        shipped = "qty_shipped" in cols
        self.raw = {"ordered": "o.qty_ordered", "shipped": "o.qty_shipped" if shipped else "CAST(NULL AS DOUBLE)",
                    "measured": "CASE WHEN o.qty_shipped IS NOT NULL THEN o.qty_ordered END" if shipped else "CAST(NULL AS DOUBLE)",
                    "customer_id": "o.customer_id"}
        self.agg = {
            "ordered_units": ("sum(ordered)", None), "customer_order_units": ("sum(ordered)", None), "ordered_lines": ("count(*)", None),
            "customers_ordering": ("count(DISTINCT customer_id)", None),
            "shipped_units": ("sum(shipped)", ("count(*) FILTER (WHERE shipped IS NOT NULL)", "count(*)")),
            "unfulfilled_units": ("sum(CASE WHEN shipped IS NOT NULL THEN ordered - shipped END)", ("count(*) FILTER (WHERE shipped IS NOT NULL)", "count(*)")),
            "fill_rate": (("sum(shipped)", "sum(measured)"), ("count(*) FILTER (WHERE shipped IS NOT NULL)", "count(*)")),
            "customer_fill_rate": (("sum(shipped)", "sum(measured)"), ("count(*) FILTER (WHERE shipped IS NOT NULL)", "count(*)")),
        }

    def _inventory_snapshot(self) -> None:
        conn = self.conn
        if not _has_rows(conn, "stg_fmcg_inventory"):
            self.available, self.empty_reason = False, ("NO_DATA", "No inventory snapshots have been uploaded.")
            return
        self.snapshot = True
        self.ctes.append(_master_cte(conn))
        self.ctes.append("snaps AS (SELECT i.snapshot_date, i.sku, i.location_id, i.on_hand, coalesce(i.in_transit, 0) AS in_transit "
                         "FROM (SELECT *, row_number() OVER (PARTITION BY snapshot_date, sku, location_id ORDER BY imported_at DESC) AS rn FROM stg_fmcg_inventory) i "
                         "WHERE i.rn = 1)")
        self.from_sql = "snaps i LEFT JOIN master m ON m.sku = i.sku"
        self.dims = {"sku": "i.sku", "product": "coalesce(m.sku_name, i.sku)", "category": "m.category", "sub_category": "m.sub_category", "brand": "m.brand",
                     "abc_class": "m.abc_class", "sector": "m.sector", "supplier": "m.supplier_id", "location": "CAST(i.location_id AS VARCHAR)"}
        self.anchor_expr = "i.snapshot_date"
        self.cutoff_expr = "max(i.snapshot_date)"
        self.raw = {"snapshot_date": "i.snapshot_date", "on_hand": "i.on_hand", "in_transit": "i.in_transit", "unit_cost": "m.unit_cost", "sku_key": "i.sku",
                    "location_key": "CAST(i.location_id AS VARCHAR)"}
        self.agg = {
            "inventory_units": ("sum(on_hand)", None), "in_transit_units": ("sum(in_transit)", None),
            "inventory_value": ("sum(on_hand * unit_cost)", ("count(*) FILTER (WHERE unit_cost IS NOT NULL)", "count(*)")),
            "weeks_of_cover": "COVER",
        }

    def _purchase_order_line(self) -> None:
        conn = self.conn
        if not _has_rows(conn, "stg_fmcg_purchase_orders"):
            self.available, self.empty_reason = False, ("NO_DATA", "No purchase orders have been uploaded.")
            return
        receipts = has_table(conn, "stg_fmcg_receipts")
        dest_ok = site_column_usable(conn, "stg_fmcg_purchase_orders", "destination_id")
        self.ctes.append(_master_cte(conn))
        self.ctes.append(_supplier_cte(conn))
        recv = ("recv_line AS (SELECT po_id, sku, sum(qty_received) AS q, min(receipt_date) AS first_receipt FROM stg_fmcg_receipts WHERE sku IS NOT NULL GROUP BY 1, 2), "
                "recv_po AS (SELECT po_id, sum(qty_received) AS q, min(receipt_date) AS first_receipt FROM stg_fmcg_receipts GROUP BY 1)") if receipts else \
               ("recv_line AS (SELECT NULL AS po_id, NULL AS sku, NULL AS q, NULL AS first_receipt WHERE FALSE), "
                "recv_po AS (SELECT NULL AS po_id, NULL AS q, NULL AS first_receipt WHERE FALSE)")
        dest = "any_value(CAST(destination_id AS VARCHAR))" if dest_ok else "CAST(NULL AS VARCHAR)"
        self.ctes.append(recv)
        self.ctes.append(f"po_line AS (SELECT po_id, sku, sum(qty_ordered) AS ordered, min(po_date) AS po_date, min(expected_delivery_date) AS eta, "  # nosec B608 - code literals; values bind
                         f"any_value(supplier_id) AS supplier_id, {dest} AS destination_id, count(*) OVER (PARTITION BY po_id) AS lines_on_po "
                         "FROM stg_fmcg_purchase_orders GROUP BY po_id, sku)")
        self.ctes.append("po_state AS (SELECT l.po_id, l.sku, l.ordered, l.po_date, l.eta, l.supplier_id, l.destination_id, "
                         "coalesce(rl.q, CASE WHEN l.lines_on_po = 1 THEN rp.q END) AS received, coalesce(rl.first_receipt, rp.first_receipt) AS first_receipt, "
                         "CASE WHEN coalesce(rl.first_receipt, rp.first_receipt) IS NULL THEN l.ordered ELSE 0 END AS open_units "
                         "FROM po_line l LEFT JOIN recv_line rl ON rl.po_id = l.po_id AND rl.sku = l.sku LEFT JOIN recv_po rp ON rp.po_id = l.po_id)")
        self.from_sql = "po_state p LEFT JOIN master m ON m.sku = p.sku LEFT JOIN sup s ON s.supplier_id = p.supplier_id"
        self.dims = {"sku": "p.sku", "product": "coalesce(m.sku_name, p.sku)", "category": "m.category", "sub_category": "m.sub_category", "brand": "m.brand",
                     "abc_class": "m.abc_class", "sector": "m.sector", "supplier": "p.supplier_id", "origin": "s.origin_iso3", "route": "s.route",
                     "po_status": "CASE WHEN p.first_receipt IS NOT NULL THEN 'received' WHEN p.eta IS NOT NULL AND p.eta < CURRENT_DATE THEN 'late' ELSE 'open' END"}
        if dest_ok:
            self.dims["destination"] = "p.destination_id"
        else:
            self.blocked["destination"] = ("BLOCKED_BY_DATA", "Purchase orders carry no destination site.")
        self.anchor_expr = {"po_date": "p.po_date", "eta": "p.eta"}.get(self.plan.anchor) or "p.po_date"
        self.cutoff_expr = "max(p.po_date)"
        self.raw = {"open_units": "p.open_units", "ordered": "p.ordered", "unit_cost": "m.unit_cost", "po_id": "p.po_id"}
        self.agg = {
            "open_po_units": ("sum(open_units)", None), "po_ordered_units": ("sum(ordered)", None),
            "open_po_value": ("sum(open_units * unit_cost)", ("count(*) FILTER (WHERE open_units > 0 AND unit_cost IS NOT NULL)", "count(*) FILTER (WHERE open_units > 0)")),
            "open_po_count": ("count(DISTINCT po_id) FILTER (WHERE open_units > 0)", None),
        }

    def _matched_purchase_order(self) -> None:
        conn = self.conn
        if not (_has_rows(conn, "stg_fmcg_purchase_orders") and _has_rows(conn, "stg_fmcg_receipts")):
            self.available, self.empty_reason = False, ("NO_DATA", "Supplier performance needs purchase orders and receipts.")
            return
        self.ctes.append(_matched_cte().strip().rstrip(",").strip())
        self.ctes.append(_master_cte(conn))
        self.ctes.append(_supplier_cte(conn))
        # an equi-join only: `AND x.lines = 1` inside the ON clause made DuckDB nest-loop the master
        # (3 s at 50k products); the single-line rule is applied in the projections instead (21 ms)
        self.from_sql = "matched x LEFT JOIN master m ON m.sku = x.first_sku LEFT JOIN sup s ON s.supplier_id = x.supplier_id"
        self.dims = {"supplier": "x.supplier_id", "origin": "s.origin_iso3", "route": "s.route", "sku": "CASE WHEN x.lines = 1 THEN x.first_sku END",
                     "product": "CASE WHEN x.lines = 1 THEN coalesce(m.sku_name, x.first_sku) END", "category": "CASE WHEN x.lines = 1 THEN m.category END",
                     "brand": "CASE WHEN x.lines = 1 THEN m.brand END", "sector": "CASE WHEN x.lines = 1 THEN m.sector END"}
        self.anchor_expr = {"po_date": "x.po_date", "first_receipt": "x.first_receipt"}.get(self.plan.anchor) or "x.po_date"
        self.cutoff_expr = "max(x.first_receipt)"
        self.raw = {"ordered": "x.ordered", "received": "x.received", "fill": "x.fill", "promised": "x.promised", "late_days": "x.late_days",
                    "lead_days": "x.observed_lead_days"}
        tol = float(SHORT_FILL_TOLERANCE)
        self.agg = {
            "matched_orders": ("count(*)", None),
            "supplier_fill_rate": (("sum(received)", "sum(ordered)"), ("count(*)", "count(*)")),
            "short_fill_rate": ((f"count(*) FILTER (WHERE fill < {tol})", "count(*)"), ("count(*)", "count(*)")),
            "short_fill_units": ("sum(CASE WHEN received < ordered THEN ordered - received END)", None),
            "supplier_late_rate": (("count(*) FILTER (WHERE late_days > 0)", "count(*) FILTER (WHERE promised IS NOT NULL)"),
                                   ("count(*) FILTER (WHERE promised IS NOT NULL)", "count(*)")),
            "lead_time_p50": ("quantile_cont(lead_days, 0.5)", None), "lead_time_p90": ("quantile_cont(lead_days, 0.9)", None),
            "lead_time": ("avg(lead_days)", None),
            "lead_time_variability": ("quantile_cont(lead_days, 0.9) - quantile_cont(lead_days, 0.5)", None),
            "mean_late_days": ("avg(CASE WHEN late_days > 0 THEN late_days END)", ("count(*) FILTER (WHERE late_days > 0)", "count(*) FILTER (WHERE promised IS NOT NULL)")),
        }

    def _receipt(self) -> None:
        conn = self.conn
        if not _has_rows(conn, "stg_fmcg_receipts"):
            self.available, self.empty_reason = False, ("NO_DATA", "No receipts have been uploaded.")
            return
        self.ctes.append(_master_cte(conn))
        head = ("head AS (SELECT po_id, any_value(supplier_id) AS supplier_id, any_value(sku) AS sku FROM stg_fmcg_purchase_orders GROUP BY po_id)"
                if has_table(conn, "stg_fmcg_purchase_orders") else "head AS (SELECT NULL AS po_id, NULL AS supplier_id, NULL AS sku WHERE FALSE)")
        self.ctes.append(head)
        self.from_sql = "stg_fmcg_receipts r LEFT JOIN head h ON h.po_id = r.po_id LEFT JOIN master m ON m.sku = coalesce(r.sku, h.sku)"
        self.dims = {"sku": "coalesce(r.sku, h.sku)", "product": "coalesce(m.sku_name, r.sku, h.sku)", "category": "m.category", "brand": "m.brand", "supplier": "h.supplier_id"}
        self.anchor_expr = "r.receipt_date"
        self.cutoff_expr = "max(r.receipt_date)"
        self.raw = {"received": "r.qty_received"}
        self.agg = {"received_units": ("sum(received)", None)}

    def _decision_response(self) -> None:
        conn = self.conn
        if not has_table(conn, "zaad_decision_responses"):
            self.available, self.empty_reason = False, ("NO_DATA", "No decision has been responded to yet.")
            return
        self.from_sql = "zaad_decision_responses z"
        self.where.append("z.operator_id = ?")
        self.params.append(self.operator)
        self.dims = {"decision_status": "z.status"}
        self.anchor_expr = "z.created_at"
        self.cutoff_expr = "max(z.created_at)"
        self.raw = {"status": "z.status"}
        self.agg = {"decision_response_count": ("count(*)", None),
                    "override_rate": (("count(*) FILTER (WHERE status = 'OVERRIDDEN')", "count(*)"), ("count(*)", "count(*)"))}

    def _proposal(self) -> None:
        conn = self.conn
        if not has_table(conn, "zaad_draft_orders"):
            self.available, self.empty_reason = False, ("NO_DATA", "No proposal exists yet.")
            return
        self.from_sql = "zaad_draft_orders z"
        self.where.append("z.operator_id = ?")
        self.params.append(self.operator)
        self.dims = {"proposal_state": "z.state", "supplier": "z.supplier_id"}
        self.anchor_expr = "z.updated_at"
        self.cutoff_expr = "max(z.updated_at)"
        self.raw = {"state": "z.state"}
        self.agg = {"proposal_count": ("count(*)", None)}

    def _outcome(self) -> None:
        conn = self.conn
        if not has_table(conn, "zaad_outcomes"):
            self.available, self.empty_reason = False, ("NO_DATA", "No outcome has been recorded yet.")
            return
        self.from_sql = "zaad_outcomes z"
        self.where.append("z.operator_id = ?")
        self.params.append(self.operator)
        self.dims = {"outcome_metric": "z.metric",
                     "value_register": "CASE WHEN z.comparator_value IS NOT NULL AND z.comparator_basis IS NOT NULL THEN 'REALIZED_VALUE' ELSE 'OBSERVED_AFTER_ACTION' END"}
        self.anchor_expr = "z.observed_at"
        self.cutoff_expr = "max(z.observed_at)"
        self.raw = {"value": "z.value", "comparator": "z.comparator_value", "basis": "z.comparator_basis"}
        self.agg = {"observed_after_action": ("sum(value)", None),
                    "realized_value": ("sum(CASE WHEN comparator IS NOT NULL AND basis IS NOT NULL THEN comparator - value END)",
                                       ("count(*) FILTER (WHERE comparator IS NOT NULL AND basis IS NOT NULL)", "count(*)"))}

    # ── rendering ──

    def dimension_expr(self, d: PlanDimension) -> str | None:
        if d.kind == "time":
            return f"CAST({_trunc(d.level or 'week', self.anchor_expr)} AS DATE)"
        expr = self.dims.get(d.id)
        if expr is None and d.id not in self.blocked:
            self.blocked[d.id] = ("BLOCKED_BY_DATA", f"{DIMENSIONS[d.id].label['en']} is not a column this workspace's upload carries.")
        return expr

    def filter_sql(self, f: PlanFilter) -> tuple[str, list[Any]] | None:
        expr = self.dims.get(f.dimension_id)
        if expr is None:
            self.blocked[f.dimension_id] = self.blocked.get(f.dimension_id, ("BLOCKED_BY_DATA", f"{DIMENSIONS[f.dimension_id].label['en']} cannot be filtered on in this workspace."))
            return None
        text = f"CAST({expr} AS VARCHAR)"
        if f.op == "in":
            return f"{text} IN ({', '.join('?' for _ in f.values)})", list(f.values)
        if f.op == "eq":
            return f"{text} = ?", [f.values[0]]
        if f.op == "ne":
            return f"({text} IS NULL OR {text} <> ?)", [f.values[0]]
        if f.op == "contains":
            return f"{text} ILIKE ? ESCAPE '{queries.LIKE_ESCAPE}'", [queries.like_contains(f.values[0])]
        if f.op == "gte":
            return f"{text} >= ?", [f.values[0]]
        if f.op == "lte":
            return f"{text} <= ?", [f.values[0]]
        if f.op == "between":
            return f"{text} BETWEEN ? AND ?", [f.values[0], f.values[1]]
        if f.op == "is_null":
            return f"{expr} IS NULL", []
        if f.op == "not_null":
            return f"{expr} IS NOT NULL", []
        raise AnalyticsRefused("spec_invalid", f"unknown filter op {f.op!r}")


class DuckDBAdapter:
    name = "duckdb"

    def __init__(self, conn: Any, operator: str):
        self.conn = conn
        self.operator = operator

    # ── members ──

    def members(self, dimension_id: str, *, search: str | None = None, limit: int = 200) -> list[str]:
        d = DIMENSIONS[dimension_id]
        fixed = {"po_status": ["open", "late", "received"], "decision_verb": ["KEEP", "DEFER", "EXPEDITE", "REDUCE", "CANCEL", "SPLIT", "BUY", "MOVE"],
                 "decision_status": ["REVIEWED", "ACCEPTED", "OVERRIDDEN", "REJECTED"],
                 "proposal_state": ["DRAFT", "READY_FOR_REVIEW", "APPROVED", "REJECTED", "EXPORTED", "SUPERSEDED"],
                 "value_register": ["OBSERVED_AFTER_ACTION", "REALIZED_VALUE"]}
        if dimension_id in fixed:
            values = fixed[dimension_id]
            return [v for v in values if not search or search.lower() in v.lower()][:limit]
        if dimension_id == "outcome_metric":
            if not has_table(self.conn, "zaad_outcomes"):
                return []
            return [str(r["metric"]) for r in _rows(self.conn, "SELECT DISTINCT metric FROM zaad_outcomes WHERE operator_id = ? ORDER BY 1 LIMIT ?", [self.operator, limit])]
        if not d.members:
            return []
        dataset, column = d.members
        try:
            values = queries.distinct_values(self.conn, dataset, column, limit=min(max(limit, 1), 200))
        except queries.QueryRefused:
            return []
        if search:
            needle = search.lower()
            values = [v for v in values if needle in str(v).lower()]
        return [str(v) for v in values][:limit]

    # ── execution ──

    def execute(self, plan: PhysicalPlan) -> EngineResult:
        if plan.fact_source == "plan":
            return _aggregate_supplied(plan)
        started = time.perf_counter()
        fact = _Fact(self.conn, plan, self.operator)
        if not fact.available:
            reason, why = fact.empty_reason or ("NO_DATA", "Nothing to read.")
            return EngineResult(rows=[], blocked={"__fact__": (reason, why)}, coverage={}, executed_ms=0.0)

        # dimensions and filters over the fact
        select_dims: list[tuple[str, str]] = []          # (id, expr)
        for d in plan.dimensions:
            expr = fact.dimension_expr(d)
            if expr is not None:
                select_dims.append((d.id, expr))
        where = list(fact.where)
        params = list(fact.params)
        for f in plan.filters:
            rendered = fact.filter_sql(f)
            if rendered is None:
                # a filter on a blocked dimension narrows to nothing rather than to everything
                return EngineResult(rows=[], blocked=dict(fact.blocked), coverage={}, executed_ms=0.0)
            sql, p = rendered
            where.append(sql)
            params.extend(p)

        # the range, absolute or relative to the fact's last date
        cutoff = None
        if fact.cutoff_expr:
            fact_where = (" WHERE " + " AND ".join(fact.where)) if fact.where else ""
            cutoff_sql = (f"WITH {', '.join(fact.ctes)} " if fact.ctes else "") + f"SELECT {fact.cutoff_expr} FROM {fact.from_sql}{fact_where}"  # nosec B608 - code literals; values bind
            cutoff = self._run_scalar(cutoff_sql, list(fact.params), plan.timeout_s)
            if hasattr(cutoff, "date"):
                cutoff = cutoff.date() if not isinstance(cutoff, date) else cutoff
        start, end = plan.range_start, plan.range_end
        if start and fact.anchor_expr:
            where.append(f"CAST({fact.anchor_expr} AS DATE) >= ?")
            params.append(start)
        if end and fact.anchor_expr:
            where.append(f"CAST({fact.anchor_expr} AS DATE) <= ?")
            params.append(end)

        raw_cols = ", ".join(f"{expr} AS {name}" for name, expr in fact.raw.items())
        dim_cols = ", ".join(f"{expr} AS d_{name}" for name, expr in select_dims)
        projection = ", ".join(x for x in (dim_cols, raw_cols) if x)
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        base = f"base AS (SELECT {projection} FROM {fact.from_sql}{where_sql})"  # nosec B608 - code literals; values bind
        ctes = [*fact.ctes, base]

        dim_ids = [name for name, _ in select_dims]
        time_dim = next((d for d in plan.dimensions if d.kind == "time"), None)
        group_cols = [f"d_{name}" for name in dim_ids]

        # measures
        measure_sql: list[str] = []
        coverage_sql: list[str] = []
        extra_ctes: list[str] = []
        for m in plan.metrics:
            spec = fact.agg.get(m.metric_id)
            if spec is None:
                raise AnalyticsRefused("engine_unavailable", f"{m.display_name['en']} has no fragment on {fact.plan.fact} in this engine.")
            if spec == "COVER":
                continue
            expr, cov = spec
            if isinstance(expr, tuple):
                num, den = expr
                measure_sql.append(f"{num} AS {m.metric_id}__num")
                measure_sql.append(f"{den} AS {m.metric_id}__den")
            else:
                measure_sql.append(f"{expr} AS {m.metric_id}")
            if cov:
                coverage_sql.append(f"{cov[0]} AS {m.metric_id}__cov_num")
                coverage_sql.append(f"{cov[1]} AS {m.metric_id}__cov_den")
            measure_sql.append(f"count(*) AS {m.metric_id}__n")

        source = "base"
        if fact.snapshot:
            # the latest snapshot per period (or overall): stock is a level, never a sum over dates
            if time_dim is not None:
                extra_ctes.append("latest AS (SELECT d_date AS period, max(snapshot_date) AS snapshot_date FROM base GROUP BY 1)")
                extra_ctes.append("current AS (SELECT b.* FROM base b JOIN latest l ON l.period = b.d_date AND l.snapshot_date = b.snapshot_date)")
            else:
                extra_ctes.append("current AS (SELECT b.* FROM base b WHERE b.snapshot_date = (SELECT max(snapshot_date) FROM base))")
            source = "current"
            if any(m.metric_id == "weeks_of_cover" for m in plan.metrics):
                by_site = "location" in dim_ids or any(f.dimension_id == "location" for f in plan.filters)
                site_ok = site_column_usable(self.conn, "stg_fmcg_orders", "location_id")
                if has_table(self.conn, "stg_fmcg_orders"):
                    site_col = ", CAST(location_id AS VARCHAR) AS location_key" if (by_site and site_ok) else ""
                    group = "GROUP BY sku, location_id" if (by_site and site_ok) else "GROUP BY sku"
                    extra_ctes.append(f"demand AS (SELECT sku{site_col}, sum(qty_ordered) / {COVER_WEEKS}.0 AS weekly_demand FROM stg_fmcg_orders "  # nosec B608 - code literals; values bind
                                      f"WHERE order_date > (SELECT max(order_date) FROM stg_fmcg_orders) - INTERVAL {COVER_WEEKS * 7} DAY {group})")
                else:
                    extra_ctes.append("demand AS (SELECT NULL AS sku, NULL AS weekly_demand WHERE FALSE)")
                join = "d.sku = c.sku_key AND d.location_key = c.location_key" if (by_site and site_ok) else "d.sku = c.sku_key"
                gcols = ", ".join(group_cols)
                # one stock row per product (and per site only when the query is by site), so a
                # product's weekly demand is counted once, never once per site it is stocked at
                keys = "c.sku_key, c.location_key" if (by_site and site_ok) else "c.sku_key"
                extra_ctes.append(f"stock_sku AS (SELECT {gcols + ', ' if gcols else ''}{keys}, sum(c.on_hand) AS on_hand FROM current c "  # nosec B608 - code literals; values bind
                                  f"GROUP BY {gcols + ', ' if gcols else ''}{keys})")
                extra_ctes.append(f"cover AS (SELECT {gcols + ', ' if gcols else ''}sum(c.on_hand) AS weeks_of_cover__num, sum(d.weekly_demand) AS weeks_of_cover__den, "  # nosec B608 - code literals; values bind
                                  f"count(*) FILTER (WHERE d.weekly_demand IS NOT NULL) AS weeks_of_cover__cov_num, count(*) AS weeks_of_cover__cov_den, count(*) AS weeks_of_cover__n "
                                  f"FROM stock_sku c LEFT JOIN demand d ON {join}{' GROUP BY ' + gcols if gcols else ''})")

        # top-N: rank members of one dimension by one measure, computed from the same base
        topn = plan.top_n
        rank_where = ""
        if topn:
            by = topn.get("by") or plan.metrics[0].metric_id
            by_spec: Any = fact.agg.get(by)
            rank_expr: str
            if by_spec == "COVER" or by_spec is None:
                rank_expr = "sum(on_hand)"
            elif isinstance(by_spec[0], tuple):
                rank_expr = f"CASE WHEN {by_spec[0][1]} > 0 THEN {by_spec[0][0]} / {by_spec[0][1]} END"
            else:
                rank_expr = by_spec[0]
            col = f"d_{topn['dimension_id']}"
            extra_ctes.append(f"ranked AS (SELECT {col} AS member FROM {source} GROUP BY 1 ORDER BY {rank_expr} DESC NULLS LAST LIMIT {int(topn['n'])})")  # nosec B608 - code literals; values bind
            if topn.get("others"):
                folded = ", ".join(f"CASE WHEN {c} IN (SELECT member FROM ranked) THEN {c} ELSE '{OTHERS}' END AS {c}" if c == col else c for c in group_cols)  # nosec B608 - code literals; values bind
                extra_ctes.append(f"folded AS (SELECT {folded}{', ' if group_cols else ''}* EXCLUDE ({', '.join(group_cols)}) FROM {source})" if group_cols else f"folded AS (SELECT * FROM {source})")  # nosec B608 - code literals; values bind
                source = "folded"
            else:
                rank_where = f" WHERE {col} IN (SELECT member FROM ranked)"  # nosec B608 - code literals; values bind

        select_parts = [*group_cols, *measure_sql, *coverage_sql]
        group_sql = f" GROUP BY {', '.join(group_cols)}" if group_cols else ""
        order_sql = self._order_sql(plan, dim_ids, group_cols)
        has_cover = fact.snapshot and any(m.metric_id == "weeks_of_cover" for m in plan.metrics)
        cover_cols = ["weeks_of_cover__num", "weeks_of_cover__den", "weeks_of_cover__cov_num", "weeks_of_cover__cov_den", "weeks_of_cover__n"]
        inner = f"SELECT {', '.join(select_parts) if select_parts else 'count(*) AS __rows'} FROM {source}{rank_where}{group_sql}"  # nosec B608 - code literals; values bind
        if has_cover:
            if group_cols:
                on = " AND ".join(f"g.{c} IS NOT DISTINCT FROM v.{c}" for c in group_cols)
                main = f"SELECT g.*, {', '.join('v.' + c for c in cover_cols)} FROM ({inner}) g LEFT JOIN cover v ON {on}{order_sql} LIMIT {int(plan.limit) + 1}"  # nosec B608 - code literals; values bind
            else:
                main = f"SELECT g.*, {', '.join('v.' + c for c in cover_cols)} FROM ({inner}) g CROSS JOIN cover v LIMIT {int(plan.limit) + 1}"  # nosec B608 - code literals; values bind
        else:
            main = f"{inner}{order_sql} LIMIT {int(plan.limit) + 1}"

        statement = f"WITH {', '.join([*ctes, *extra_ctes])} {main}"
        rows = self._run_rows(statement, params, plan.timeout_s)
        truncated = len(rows) > plan.limit
        rows = rows[: plan.limit]
        if not group_cols and rows and all((rows[0].get(f"{m.metric_id}__n") or 0) == 0 for m in plan.metrics):
            rows = []       # an aggregate over no rows: NO_DATA, never a row of nulls
        for r in rows:
            r.pop("__rows", None)
            for name in dim_ids:
                r[name] = _plain(r.pop(f"d_{name}", None))
            for k, v in list(r.items()):
                r[k] = _plain(v)

        # whole-result coverage, one aggregate over the same base (with top-N applied)
        coverage: dict[str, dict[str, float | None]] = {}
        cov_parts = [*measure_sql, *coverage_sql]
        if has_cover:
            cov_parts.extend(f"(SELECT sum({c}) FROM cover) AS {c}" for c in cover_cols)  # nosec B608 - code literals; values bind
        if cov_parts:
            cov_stmt = f"WITH {', '.join([*ctes, *extra_ctes])} SELECT {', '.join(cov_parts)} FROM {source}{rank_where}"  # nosec B608 - code literals; values bind
            total = self._run_rows(cov_stmt, params, plan.timeout_s)
            whole = total[0] if total else {}
            for m in plan.metrics:
                coverage[m.metric_id] = {"numerator": _num(whole.get(f"{m.metric_id}__cov_num")), "denominator": _num(whole.get(f"{m.metric_id}__cov_den")),
                                         "n": _num(whole.get(f"{m.metric_id}__n")),
                                         "value_num": _num(whole.get(f"{m.metric_id}__num")), "value_den": _num(whole.get(f"{m.metric_id}__den")),
                                         "value": _num(whole.get(m.metric_id))}

        comparison_rows = None
        if plan.comparison_lag and time_dim is not None and plan.grain:
            comparison_rows = self._comparison(plan, ctes, extra_ctes, select_parts, source, rank_where, group_sql, order_sql, params, fact, start, end)

        return EngineResult(rows=rows, blocked=dict(fact.blocked), coverage=coverage, executed_ms=(time.perf_counter() - started) * 1000.0,
                            truncated=truncated, statement=statement, data_cutoff=cutoff.isoformat() if isinstance(cutoff, date) else (str(cutoff) if cutoff else None),
                            comparison_rows=comparison_rows)

    def _comparison(self, plan, ctes, extra_ctes, select_parts, source, rank_where, group_sql, order_sql, params, fact, start, end):
        """The same aggregation over the range shifted back by `lag` grains; the assembler aligns periods."""
        lag = int(plan.comparison_lag or 1)
        if not (start or end):
            # unbounded range: the comparison is the same series shifted, which the assembler derives itself
            return []
        shifted_where_params = list(params)
        # replace the last two (or one) range parameters with the shifted dates
        shift = _shift(plan.grain, lag)
        idx = len(shifted_where_params) - 1
        if end:
            shifted_where_params[idx] = shift(date.fromisoformat(end)).isoformat()
            idx -= 1
        if start:
            shifted_where_params[idx] = shift(date.fromisoformat(start)).isoformat()
        statement = f"WITH {', '.join([*ctes, *extra_ctes])} SELECT {', '.join(select_parts)} FROM {source}{rank_where}{group_sql}{order_sql} LIMIT {int(plan.limit) + 1}"  # nosec B608 - code literals; values bind
        rows = self._run_rows(statement, shifted_where_params, plan.timeout_s)
        for r in rows:
            for k in list(r):
                if k.startswith("d_"):
                    r[k[2:]] = _plain(r.pop(k))
                else:
                    r[k] = _plain(r[k])
        return rows[: plan.limit]

    @staticmethod
    def _order_sql(plan: PhysicalPlan, dim_ids: list[str], group_cols: list[str]) -> str:
        if plan.sort:
            parts = []
            for field_name, direction in plan.sort:
                d = "DESC" if direction == "desc" else "ASC"
                if field_name in dim_ids:
                    parts.append(f"d_{field_name} {d} NULLS LAST")
                else:
                    spec = next((m for m in plan.metrics if m.metric_id == field_name), None)
                    if spec is None:
                        continue
                    if spec.aggregation_rule in ("ratio_of_sums", "ratio_of_counts"):
                        parts.append(f"(CASE WHEN {field_name}__den > 0 THEN {field_name}__num / {field_name}__den END) {d} NULLS LAST")
                    elif spec.metric_id == "weeks_of_cover":
                        continue
                    else:
                        parts.append(f"{field_name} {d} NULLS LAST")
            return (" ORDER BY " + ", ".join(parts)) if parts else ""
        if "date" in dim_ids:
            others = [c for c in group_cols if c != "d_date"]
            return " ORDER BY d_date ASC" + ("".join(f", {c} ASC NULLS LAST" for c in others) if others else "")
        first = plan.metrics[0]
        if first.metric_id == "weeks_of_cover":
            return (" ORDER BY " + ", ".join(f"{c} ASC NULLS LAST" for c in group_cols)) if group_cols else ""
        if first.aggregation_rule in ("ratio_of_sums", "ratio_of_counts"):
            return f" ORDER BY (CASE WHEN {first.metric_id}__den > 0 THEN {first.metric_id}__num / {first.metric_id}__den END) DESC NULLS LAST"
        return f" ORDER BY {first.metric_id} DESC NULLS LAST"

    # ── execution with a statement timeout ──

    def _run_rows(self, sql: str, params: list[Any], timeout_s: float) -> list[dict[str, Any]]:
        return self._timed(lambda: _rows(self.conn, sql, params), timeout_s)

    def _run_scalar(self, sql: str, params: list[Any], timeout_s: float) -> Any:
        return self._timed(lambda: _one(self.conn, sql, params), timeout_s)

    def _timed(self, fn, timeout_s: float):
        interrupt = getattr(self.conn, "interrupt", None)
        timer = threading.Timer(max(0.5, float(timeout_s)), interrupt) if callable(interrupt) else None
        if timer:
            timer.daemon = True
            timer.start()
        try:
            return fn()
        except duckdb.InterruptException as exc:
            raise AnalyticsRefused("query_timeout", f"The query did not finish inside {timeout_s:.0f} s. Narrow the range or the dimensions, or use top-N.") from exc
        except duckdb.Error as exc:
            text = str(exc)
            if "INTERRUPT" in text.upper():
                raise AnalyticsRefused("query_timeout", f"The query did not finish inside {timeout_s:.0f} s.") from exc
            raise AnalyticsRefused("engine_unavailable", "The analytics engine could not run this query.", {"engine": type(exc).__name__}) from exc
        finally:
            if timer:
                timer.cancel()


def _shift(grain: str, lag: int):
    def go(d: date) -> date:
        if grain == "day":
            return d - timedelta(days=lag)
        if grain == "week":
            return d - timedelta(weeks=lag)
        if grain == "month":
            m = d.month - lag
            y = d.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            return d.replace(year=y, month=m, day=min(d.day, 28))
        if grain == "quarter":
            m = d.month - 3 * lag
            y = d.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            return d.replace(year=y, month=m, day=min(d.day, 28))
        return d.replace(year=d.year - lag)
    return go


def _aggregate_supplied(plan: PhysicalPlan) -> EngineResult:
    """Plan-snapshot facts: rows are supplied by the planner and grouped here. Nothing is recomputed."""
    started = time.perf_counter()
    rows = list(plan.supplied_rows)
    dims = [d.id for d in plan.dimensions]
    for f in plan.filters:
        values = set(f.values)
        if f.op == "in":
            rows = [r for r in rows if str(r.get(f.dimension_id)) in values]
        elif f.op == "eq":
            rows = [r for r in rows if str(r.get(f.dimension_id)) == f.values[0]]
        elif f.op == "ne":
            rows = [r for r in rows if str(r.get(f.dimension_id)) != f.values[0]]
        elif f.op == "contains":
            rows = [r for r in rows if f.values[0].lower() in str(r.get(f.dimension_id) or "").lower()]
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(tuple(r.get(d) for d in dims), []).append(r)
    out: list[dict[str, Any]] = []
    coverage: dict[str, dict[str, float | None]] = {}
    for key, members in groups.items():
        row: dict[str, Any] = {d: k for d, k in zip(dims, key)}
        for m in plan.metrics:
            row[m.metric_id] = _supplied_measure(m, members)
            row[f"{m.metric_id}__n"] = len(members)
        out.append(row)
    for m in plan.metrics:
        coverage[m.metric_id] = {"numerator": None, "denominator": None, "n": float(len(rows)), "value_num": None, "value_den": None,
                                 "value": _supplied_measure(m, rows) if rows else None}
    if plan.top_n and out:
        by = plan.top_n.get("by") or plan.metrics[0].metric_id
        out.sort(key=lambda r: (r.get(by) is None, -(r.get(by) or 0)))
        out = out[: int(plan.top_n["n"])]
    elif out and plan.metrics:
        first = plan.metrics[0].metric_id
        out.sort(key=lambda r: (r.get(first) is None, -(r.get(first) or 0)))
    truncated = len(out) > plan.limit
    return EngineResult(rows=out[: plan.limit], blocked={} if plan.supplied_rows or plan.parameters.get("plan_present") else {"__fact__": ("NOT_IN_PLAN", "No completed plan exists for this workspace yet.")},
                        coverage=coverage, executed_ms=(time.perf_counter() - started) * 1000.0, truncated=truncated, statement="(plan snapshot rows, grouped in memory)",
                        data_cutoff=plan.parameters.get("plan_as_of"))


def _supplied_measure(m: MetricContract, rows: list[dict[str, Any]]) -> float | None:
    if m.metric_id == "decision_count":
        return float(len(rows))
    if m.metric_id == "recommendation_count":
        return float(sum(1 for r in rows if str(r.get("decision_verb") or "KEEP").upper() != "KEEP"))
    if m.aggregation_rule == "snapshot":
        values = [float(r["value"]) for r in rows if r.get("register") == m.register and r.get("value") is not None]
        return sum(values) if values else None
    return None


def _plain(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and value != value:
        return None
    return value


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out else out
