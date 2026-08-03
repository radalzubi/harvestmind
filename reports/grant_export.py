"""USDA grant-application metrics export.

Auto-generates the operational reporting block that USDA grant programs
(Local Food Promotion Program, Local Agriculture Market Program, SARE,
Indiana State Department of Agriculture) require with every application.

A typical hub manager spends 4–10 hours assembling these numbers by hand
across spreadsheets. We compute them straight from operational data.

Public API:
  generate_grant_metrics(conn) → dict of metric_name → value
  generate_grant_csv(conn, output_path)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class GrantMetric:
    name: str
    value: Any
    unit: str
    source: str   # human-readable provenance — "fact_orders trailing 12 mo"


def generate_grant_metrics(
    conn: duckdb.DuckDBPyConnection,
    partner_name: str = "Partner",
) -> list[GrantMetric]:
    """Compute the standard USDA-grant operational reporting block."""
    metrics: list[GrantMetric] = []

    # ── Volume + revenue ────────────────────────────────────────────────
    row = conn.execute("""
        SELECT
            COALESCE(SUM(ol.qty_ordered_kg * COALESCE(ol.price_per_kg, 0)), 0) AS revenue,
            COALESCE(SUM(ol.qty_ordered_kg), 0) AS kg_moved,
            COUNT(DISTINCT o.buyer_id) AS n_buyers,
            COUNT(DISTINCT o.order_id) AS n_orders
        FROM fact_orders o
        JOIN fact_order_lines ol ON o.order_id = ol.order_id
        WHERE o.week_start >= CURRENT_DATE - INTERVAL 12 MONTH
    """).fetchone()
    revenue, kg_moved, n_buyers, n_orders = row

    metrics.append(GrantMetric("annual_revenue_usd", round(float(revenue), 0), "USD",
                               "fact_orders × fact_order_lines (trailing 12 mo)"))
    metrics.append(GrantMetric("annual_volume_kg", round(float(kg_moved), 0), "kg",
                               "fact_order_lines (trailing 12 mo)"))
    metrics.append(GrantMetric("buyers_served", int(n_buyers), "count",
                               "distinct fact_orders.buyer_id (trailing 12 mo)"))
    metrics.append(GrantMetric("orders_fulfilled", int(n_orders), "count",
                               "distinct fact_orders (trailing 12 mo)"))

    # ── Local sourcing ──────────────────────────────────────────────────
    row = conn.execute("""
        SELECT
            COUNT(DISTINCT supplier_id) AS n_suppliers,
            COALESCE(SUM(qty_received_kg - COALESCE(qty_rejected_kg,0)), 0) AS sourced_kg
        FROM fact_deliveries
        WHERE delivery_date >= CURRENT_DATE - INTERVAL 12 MONTH
    """).fetchone()
    n_suppliers, sourced_kg = row
    metrics.append(GrantMetric("local_suppliers_engaged", int(n_suppliers), "count",
                               "distinct fact_deliveries.supplier_id (trailing 12 mo)"))
    metrics.append(GrantMetric("local_volume_sourced_kg", round(float(sourced_kg), 0), "kg",
                               "fact_deliveries net of rejection (trailing 12 mo)"))

    # ── Buyer types served (institutional / school / hospital / restaurant) ───
    row = conn.execute("""
        SELECT
            SUM(CASE WHEN b.buyer_type IN ('school','school_district') THEN 1 ELSE 0 END) AS schools,
            SUM(CASE WHEN b.buyer_type IN ('hospital','institution') THEN 1 ELSE 0 END) AS institutions,
            SUM(CASE WHEN b.buyer_type IN ('restaurant') THEN 1 ELSE 0 END) AS restaurants,
            SUM(CASE WHEN b.buyer_type IN ('foodbank') THEN 1 ELSE 0 END) AS foodbanks
        FROM dim_buyers b
    """).fetchone()
    schools, institutions, restaurants, foodbanks = (row or (0, 0, 0, 0))
    metrics.append(GrantMetric("schools_served", int(schools or 0), "count",
                               "dim_buyers.buyer_type IN (school, school_district)"))
    metrics.append(GrantMetric("institutions_served", int(institutions or 0), "count",
                               "dim_buyers.buyer_type IN (hospital, institution)"))
    metrics.append(GrantMetric("restaurants_served", int(restaurants or 0), "count",
                               "dim_buyers.buyer_type = restaurant"))
    metrics.append(GrantMetric("food_banks_served", int(foodbanks or 0), "count",
                               "dim_buyers.buyer_type = foodbank"))

    # ── Waste reduction (reportable for sustainability grants) ──────────
    waste_row = conn.execute("""
        SELECT
            COALESCE(SUM(qty_wasted_kg), 0) AS waste_kg,
            COALESCE(SUM(estimated_value_usd), 0) AS waste_value
        FROM fact_waste_events
        WHERE event_date >= CURRENT_DATE - INTERVAL 12 MONTH
    """).fetchone()
    metrics.append(GrantMetric("food_waste_kg", round(float(waste_row[0]), 0), "kg",
                               "fact_waste_events (trailing 12 mo)"))
    metrics.append(GrantMetric("food_waste_value_usd", round(float(waste_row[1]), 0), "USD",
                               "fact_waste_events.estimated_value_usd (trailing 12 mo)"))

    # ── FTL / FSMA-204 readiness flag (regulatory grants care about this) ──
    coverage_row = conn.execute("""
        SELECT
          ROUND(
            COALESCE(
              SUM(CASE WHEN p.is_ftl_item AND EXISTS (
                  SELECT 1 FROM fact_lots l
                  WHERE l.product_id = d.product_id
                    AND COALESCE(l.supplier_id,'') = COALESCE(d.supplier_id,'')
              ) THEN d.qty_received_kg - COALESCE(d.qty_rejected_kg,0)
                ELSE 0 END), 0)
            / NULLIF(SUM(CASE WHEN p.is_ftl_item
                              THEN d.qty_received_kg - COALESCE(d.qty_rejected_kg,0)
                              ELSE 0 END), 0)
          , 4) AS coverage_pct
        FROM fact_deliveries d
        JOIN dim_products p ON d.product_id = p.product_id
    """).fetchone()
    coverage = float(coverage_row[0] or 0) if coverage_row else 0.0
    metrics.append(GrantMetric("fsma_204_coverage_pct", round(coverage * 100, 1), "%",
                               "fact_deliveries × fact_lots match on (supplier, product)"))

    # ── Period meta ─────────────────────────────────────────────────────
    metrics.append(GrantMetric("partner_name", partner_name, "string", "input"))
    metrics.append(GrantMetric("report_date", date.today().isoformat(), "date", "auto"))

    return metrics


def _csv_safe(value: object) -> str:
    """Neutralize spreadsheet formula injection.

    A cell beginning with = + - @ (or a leading tab/CR) is interpreted as a
    formula by Excel/Sheets. Operator-supplied names/reasons flow into these
    exports, so prefix any such cell with an apostrophe to force text.
    """
    s = "" if value is None else str(value)
    if s[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def generate_grant_csv(
    conn: duckdb.DuckDBPyConnection,
    output_path: str | Path,
    partner_name: str = "Partner",
) -> Path:
    """Write the grant-application metrics block to a CSV."""
    out = Path(output_path).resolve()
    if out.suffix.lower() != ".csv":
        raise ValueError(f"output_path must end in .csv; got {out.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)

    metrics = generate_grant_metrics(conn, partner_name=partner_name)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "unit", "source"])
        for m in metrics:
            w.writerow([_csv_safe(m.name), _csv_safe(m.value),
                        _csv_safe(m.unit), _csv_safe(m.source)])
    return out
