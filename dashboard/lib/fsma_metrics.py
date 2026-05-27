"""FSMA-204 traceability metrics.

Pure DuckDB functions. No Streamlit / FastAPI imports — these are reused by
both the dashboard and the API router.

Reference: 21 CFR Part 1, Subpart S (Food Safety Modernization Act, Section 204).
Compliance date: July 20, 2028 (FDA extended Nov 2025).
Major retailers (Walmart, Sysco, US Foods) demand compliance now.
"""

from __future__ import annotations

import csv
import io
from typing import Any

import duckdb
import pandas as pd


# ── Coverage score ───────────────────────────────────────────────────────────

def fsma_coverage_score(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Compute FSMA-204 traceability coverage.

    coverage_pct = (FTL delivery kg with at least one lot record)
                   ÷ (total FTL delivery kg)

    Status thresholds:
      Full     >= 0.95
      Partial  0.50 .. 0.95
      Minimal  > 0 .. 0.50
      None     == 0
    """
    # Total FTL-product delivery volume (across all time).
    total_row = conn.execute(
        """
        SELECT COALESCE(SUM(d.qty_received_kg - COALESCE(d.qty_rejected_kg, 0)), 0.0)
        FROM fact_deliveries d
        JOIN dim_products p ON d.product_id = p.product_id
        WHERE p.is_ftl_item = TRUE
        """
    ).fetchone()
    total_ftl_kg = float(total_row[0]) if total_row else 0.0

    # FTL deliveries with a corresponding lot record.
    covered_row = conn.execute(
        """
        SELECT COALESCE(SUM(d.qty_received_kg - COALESCE(d.qty_rejected_kg, 0)), 0.0)
        FROM fact_deliveries d
        JOIN dim_products p ON d.product_id = p.product_id
        WHERE p.is_ftl_item = TRUE
          AND EXISTS (
              SELECT 1 FROM fact_lots l
              WHERE l.product_id = d.product_id
                AND COALESCE(l.supplier_id, '') = COALESCE(d.supplier_id, '')
          )
        """
    ).fetchone()
    covered_kg = float(covered_row[0]) if covered_row else 0.0

    coverage_pct = (covered_kg / total_ftl_kg) if total_ftl_kg > 0 else 0.0

    products_total_df = conn.execute(
        "SELECT product_id, crop_name FROM dim_products WHERE is_ftl_item = TRUE"
    ).df()
    n_ftl_products_total = int(len(products_total_df))

    products_covered_df = conn.execute(
        """
        SELECT DISTINCT p.product_id, p.crop_name
        FROM dim_products p
        JOIN fact_lots l ON l.product_id = p.product_id
        WHERE p.is_ftl_item = TRUE
        """
    ).df()
    products_covered = sorted(products_covered_df["crop_name"].tolist())
    products_missing = sorted(
        set(products_total_df["crop_name"].tolist()) - set(products_covered)
    )

    if coverage_pct >= 0.95:
        status = "Full"
    elif coverage_pct >= 0.50:
        status = "Partial"
    elif coverage_pct > 0:
        status = "Minimal"
    else:
        status = "None"

    return {
        "coverage_pct": round(coverage_pct, 4),
        "covered_kg": round(covered_kg, 1),
        "total_ftl_kg": round(total_ftl_kg, 1),
        "missing_kg": round(max(0.0, total_ftl_kg - covered_kg), 1),
        "n_ftl_products_covered": int(len(products_covered)),
        "n_ftl_products_total": n_ftl_products_total,
        "products_missing": products_missing,
        "products_covered": products_covered,
        "status": status,
    }


# ── Per-product coverage breakdown ───────────────────────────────────────────

def ftl_product_list(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Per-FTL-product coverage table.

    Columns: product_id, crop_name, crop_category, received_kg, covered_kg,
             coverage_pct, status.
    """
    return conn.execute(
        """
        SELECT
            p.product_id,
            p.crop_name,
            p.crop_category,
            COALESCE(d.received_kg, 0.0)  AS received_kg,
            COALESCE(c.covered_kg, 0.0)   AS covered_kg,
            CASE WHEN COALESCE(d.received_kg, 0) > 0
                 THEN COALESCE(c.covered_kg, 0) / d.received_kg
                 ELSE 0
            END AS coverage_pct
        FROM dim_products p
        LEFT JOIN (
            SELECT product_id,
                   SUM(qty_received_kg - COALESCE(qty_rejected_kg, 0)) AS received_kg
            FROM fact_deliveries
            GROUP BY product_id
        ) d ON p.product_id = d.product_id
        LEFT JOIN (
            SELECT d2.product_id,
                   SUM(d2.qty_received_kg - COALESCE(d2.qty_rejected_kg, 0)) AS covered_kg
            FROM fact_deliveries d2
            WHERE EXISTS (
                SELECT 1 FROM fact_lots l
                WHERE l.product_id = d2.product_id
                  AND COALESCE(l.supplier_id, '') = COALESCE(d2.supplier_id, '')
            )
            GROUP BY d2.product_id
        ) c ON p.product_id = c.product_id
        WHERE p.is_ftl_item = TRUE
        ORDER BY received_kg DESC
        """
    ).df().assign(
        status=lambda x: x["coverage_pct"].apply(
            lambda v: "Full" if v >= 0.95 else "Partial" if v >= 0.5 else "Minimal" if v > 0 else "None"
        )
    )


# ── FDA report ───────────────────────────────────────────────────────────────

def generate_fda_report_csv(
    conn: duckdb.DuckDBPyConnection,
    tlc: str | None = None,
) -> str:
    """Return a CSV string sorted by event_timestamp.

    tlc=None       → all CTEs from the last 30 days.
    tlc=<code>     → only CTEs matching the lot chain (parameterised query).
    """
    if tlc is None:
        df = conn.execute(
            """
            SELECT * FROM v_fsma_204_report
            WHERE event_timestamp >= CURRENT_TIMESTAMP - INTERVAL 30 DAY
            ORDER BY event_timestamp
            """
        ).df()
    else:
        df = conn.execute(
            """
            SELECT * FROM v_fsma_204_report
            WHERE traceability_lot_code = ?
            ORDER BY event_timestamp
            """,
            [tlc],
        ).df()

    buf = io.StringIO()
    df.to_csv(buf, index=False, quoting=csv.QUOTE_MINIMAL)
    return buf.getvalue()


# ── Lot chain (recursive references) ─────────────────────────────────────────

_MAX_CHAIN_DEPTH = 10


def fsma_lot_chain(conn: duckdb.DuckDBPyConnection, tlc: str) -> pd.DataFrame:
    """Walk the TLC chain via referenced_tlc_codes (max depth 10).

    Returns CTEs across the entire upstream chain, sorted by event_timestamp.
    """
    visited: set[str] = set()
    frontier = [tlc]
    rows: list[pd.DataFrame] = []
    depth = 0
    while frontier and depth < _MAX_CHAIN_DEPTH:
        depth += 1
        current = [t for t in frontier if t and t not in visited]
        visited.update(current)
        if not current:
            break

        placeholders = ", ".join(["?"] * len(current))
        df = conn.execute(
            f"SELECT * FROM v_fsma_204_report "
            f"WHERE traceability_lot_code IN ({placeholders}) "
            f"ORDER BY event_timestamp",
            current,
        ).df()
        if df.empty:
            break
        rows.append(df)

        # Collect next-level upstream references. Pandas may return the
        # array column as numpy.ndarray, list, scalar, or NA depending on
        # the row contents — normalize all of them.
        import numpy as np
        next_frontier: set[str] = set()
        for _, r in df.iterrows():
            refs = r.get("referenced_tlc_codes")
            if refs is None:
                continue
            if isinstance(refs, (list, tuple)):
                iterable = list(refs)
            elif isinstance(refs, np.ndarray):
                iterable = refs.tolist()
            else:
                # Scalar — could be NaN/NA or a single TLC string
                try:
                    if pd.isna(refs):
                        continue
                except (TypeError, ValueError):
                    pass
                iterable = [refs]
            for code in iterable:
                if isinstance(code, str) and code and code not in visited:
                    next_frontier.add(code)
        frontier = list(next_frontier)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values("event_timestamp")


# ── Recent CTE listing for the dashboard ─────────────────────────────────────

def recall_forward_trace(conn: duckdb.DuckDBPyConnection, tlc: str) -> dict:
    """Forward recall trace: given a TLC, identify every business that received
    product from this lot or a downstream transformation of it.

    Returns:
      tlc:                  input TLC
      affected_lots:        list of TLCs in the downstream chain
      receiving_businesses: list of distinct business_names that received
                             any of those lots (these are the recall
                             notification targets)
      n_shipping_events:    total shipping CTEs in the chain
      total_quantity_kg:    total kg moved out under the affected lots

    The walk follows new_tlc_code (output of transformation events) so a
    lettuce lot transformed into a salad mix continues to trace forward.
    """
    visited: set[str] = set()
    frontier: list[str] = [tlc]
    affected: set[str] = set()
    businesses: set[str] = set()
    n_shipping = 0
    total_kg = 0.0

    while frontier:
        current = [t for t in frontier if t and t not in visited]
        visited.update(current)
        if not current:
            break

        placeholders = ", ".join(["?"] * len(current))
        sql = (
            "SELECT traceability_lot_code, cte_type, business_name, "
            "quantity_kg, new_tlc_code "
            "FROM v_fsma_204_report "
            f"WHERE traceability_lot_code IN ({placeholders})"
        )
        rows = conn.execute(sql, current).fetchall()
        # Only mark as affected the TLCs that actually have CTE rows.
        affected.update(r[0] for r in rows)

        next_frontier: set[str] = set()
        for tlc_code, cte_type, biz, qty, new_tlc in rows:
            if cte_type in ("shipping", "receiving") and biz:
                businesses.add(biz)
            if cte_type == "shipping":
                n_shipping += 1
                if qty:
                    total_kg += float(qty)
            if new_tlc and new_tlc not in visited:
                next_frontier.add(new_tlc)
        frontier = list(next_frontier)

    return {
        "tlc": tlc,
        "affected_lots": sorted(affected),
        "receiving_businesses": sorted(businesses),
        "n_shipping_events": n_shipping,
        "total_quantity_kg": round(total_kg, 2),
    }


def recent_cte_events(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> pd.DataFrame:
    """Return the N most recent CTEs (joined with product description)."""
    if limit <= 0 or limit > 1000:
        limit = 20
    return conn.execute(
        f"""
        SELECT * FROM v_fsma_204_report
        ORDER BY event_timestamp DESC
        LIMIT {int(limit)}
        """
    ).df()
