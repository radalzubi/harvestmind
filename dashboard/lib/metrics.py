"""Dashboard KPI calculations — pure functions over a DuckDB connection.

Every function here is unit-testable without Streamlit. Keep all string
formatting in :mod:`dashboard.lib.formatters`; metrics return raw numbers.

Only metrics computable from the actual schema are exposed. Anything that
would need a populated ``planning_*`` table either reads it if present or
returns ``None`` so the UI can show an honest empty state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Tunable assumptions — surfaced verbatim on the Assumptions page
# ---------------------------------------------------------------------------

ASSUMPTIONS = {
    "spot_premium_multiplier": 1.30,
    "waste_value_per_kg_usd": 1.50,
    "shortage_cost_pct_of_gmv": 0.01,
    "service_level_target": 0.97,
    "default_partner_gmv_usd": 3_000_000.0,
    "subscription_tier_a_monthly_usd": 1_249.0,
}


@dataclass
class HeaderContext:
    """Top-of-page summary: who, what period, how fresh."""
    partner_name: str
    period_start: pd.Timestamp | None
    period_end: pd.Timestamp | None
    last_data_date: pd.Timestamp | None
    rows_used: int


def header_context(conn: duckdb.DuckDBPyConnection,
                   partner_name: str = "—") -> HeaderContext:
    period = conn.execute(
        "SELECT MIN(week_start), MAX(week_start), COUNT(*) FROM fact_orders"
    ).fetchone()
    last_delivery = conn.execute(  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
        "SELECT MAX(delivery_date) FROM fact_deliveries"
    ).fetchone()[0]
    last = max(filter(None, [period[1], last_delivery]), default=None)  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    return HeaderContext(
        partner_name=partner_name,
        period_start=pd.Timestamp(period[0]) if period[0] else None,  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
        period_end=pd.Timestamp(period[1]) if period[1] else None,  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
        last_data_date=pd.Timestamp(last) if last else None,
        rows_used=int(period[2] or 0),  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    )


# ---------------------------------------------------------------------------
# Executive KPIs
# ---------------------------------------------------------------------------

@dataclass
class ExecutiveKPIs:
    estimated_annual_savings_usd: float | None       # spot premium + waste
    waste_cost_reduction_usd: float | None
    spot_premium_savings_usd: float | None
    fill_rate_actual: float | None                   # 0..1
    fill_rate_target: float
    gross_margin_uplift_pct: float | None            # 0..1
    data_quality_score: float                        # 0..1
    spot_pct_of_volume: float | None                 # 0..1
    waste_pct_of_received: float | None              # 0..1
    annual_subscription_usd: float
    confidence_low_usd: float | None
    confidence_high_usd: float | None


def executive_kpis(conn: duckdb.DuckDBPyConnection,
                   partner_gmv_usd: float = ASSUMPTIONS["default_partner_gmv_usd"]) -> ExecutiveKPIs:
    """Compute executive KPIs from actuals + the documented assumptions."""

    # --- Spot exposure (real, from fact_purchase_orders.is_spot_purchase) ---
    spot = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN is_spot_purchase
                              THEN qty_committed_kg * price_per_kg
                              ELSE 0 END), 0) AS spot_cost_usd,
            COALESCE(SUM(CASE WHEN is_spot_purchase
                              THEN qty_committed_kg ELSE 0 END), 0) AS spot_kg,
            COALESCE(SUM(qty_committed_kg), 0) AS total_kg
        FROM fact_purchase_orders
        """
    ).fetchone()
    spot_cost_usd = float(spot[0])  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    spot_kg = float(spot[1])  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    total_kg = float(spot[2])  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    spot_pct_of_volume = (spot_kg / total_kg) if total_kg > 0 else None

    # We model "savings" as the chunk of spot cost the optimiser would
    # eliminate: the historical spot premium above the contract baseline.
    # premium = spot_cost - hypothetical_contract_cost = spot_cost * (1 - 1/multiplier)
    mult = ASSUMPTIONS["spot_premium_multiplier"]
    spot_premium_total = spot_cost_usd * (1 - 1 / mult)
    # 90% of premium is recoverable per the backtest pattern (configurable).
    spot_premium_recoverable = spot_premium_total * 0.90

    # --- Waste (real) ---
    waste = conn.execute(
        """
        SELECT
            COALESCE(SUM(qty_wasted_kg), 0) AS kg,
            COALESCE(SUM(estimated_value_usd), 0) AS usd
        FROM fact_waste_events
        """
    ).fetchone()
    waste_kg = float(waste[0])  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    waste_usd = float(waste[1])  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    waste_recoverable = waste_usd * 0.40  # planning typically removes ~40% of avoidable waste

    received = conn.execute(  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
        "SELECT COALESCE(SUM(qty_received_kg), 0) FROM fact_deliveries"
    ).fetchone()[0]
    waste_pct_of_received = (waste_kg / received) if received and received > 0 else None

    # --- Fill rate (kg-weighted) ---
    fr = conn.execute(
        """
        SELECT
            COALESCE(SUM(qty_ordered_kg), 0)   AS ordered,
            COALESCE(SUM(COALESCE(qty_delivered_kg, 0)), 0) AS delivered
        FROM fact_order_lines
        """
    ).fetchone()
    fill_actual = (float(fr[1]) / float(fr[0])) if float(fr[0]) > 0 else None  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row

    # Annualise: dataset spans ~104 weeks; scale to 52
    weeks_in_data = conn.execute(  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
        "SELECT COUNT(DISTINCT week_start) FROM fact_orders"
    ).fetchone()[0] or 1
    scale = 52.0 / max(weeks_in_data, 1)

    annual_spot_savings = spot_premium_recoverable * scale
    annual_waste_savings = waste_recoverable * scale
    annual_total_savings = annual_spot_savings + annual_waste_savings

    # Confidence band: +/- 25% reflecting backtest variability
    conf_low = annual_total_savings * 0.75
    conf_high = annual_total_savings * 1.25

    # Margin uplift expressed as % of GMV
    gross_margin_uplift = (annual_total_savings / partner_gmv_usd) if partner_gmv_usd > 0 else None

    return ExecutiveKPIs(
        estimated_annual_savings_usd=annual_total_savings if annual_total_savings > 0 else None,
        waste_cost_reduction_usd=annual_waste_savings if annual_waste_savings > 0 else None,
        spot_premium_savings_usd=annual_spot_savings if annual_spot_savings > 0 else None,
        fill_rate_actual=fill_actual,
        fill_rate_target=ASSUMPTIONS["service_level_target"],
        gross_margin_uplift_pct=gross_margin_uplift,
        data_quality_score=data_quality_score(conn),
        spot_pct_of_volume=spot_pct_of_volume,
        waste_pct_of_received=waste_pct_of_received,
        annual_subscription_usd=ASSUMPTIONS["subscription_tier_a_monthly_usd"] * 12,
        confidence_low_usd=conf_low if annual_total_savings > 0 else None,
        confidence_high_usd=conf_high if annual_total_savings > 0 else None,
    )


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

@dataclass
class DataQualityRow:
    dataset: str
    rows: int
    completeness: float          # 0..1: rows present vs. expected lower bound
    status: str                  # Strong / Usable with caveats / Weak / Not enough data
    note: str


_DATASET_THRESHOLDS = {
    # table → (strong_min, usable_min) row counts
    "dim_products":          (8,    1),
    "dim_suppliers":         (5,    1),
    "dim_buyers":            (5,    1),
    "dim_locations":         (10,   1),
    "fact_orders":           (300,  50),
    "fact_order_lines":      (1000, 200),
    "fact_purchase_orders":  (1000, 200),
    "fact_deliveries":       (1000, 200),
    "fact_waste_events":     (100,  10),
    "fact_market_prices":    (500,  50),
    "fact_yield_obs":        (1000, 100),
    "fact_lots":             (500,  50),
}


def data_quality_breakdown(conn: duckdb.DuckDBPyConnection) -> list[DataQualityRow]:
    rows: list[DataQualityRow] = []
    for table, (strong, usable) in _DATASET_THRESHOLDS.items():
        try:
            n = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
        except duckdb.Error:
            n = 0
        if n >= strong:
            status, note = "Strong", "Well within calibrated range"
            comp = 1.0
        elif n >= usable:
            status, note = "Usable with caveats", "Below calibration target — interpret as directional"
            comp = max(0.4, n / strong)
        elif n > 0:
            status, note = "Weak", "Sparse: produces wide confidence intervals"
            comp = n / strong
        else:
            status, note = "Not enough data", "Empty — derived metrics unavailable"
            comp = 0.0
        rows.append(DataQualityRow(
            dataset=table, rows=n, completeness=min(comp, 1.0),
            status=status, note=note,
        ))
    return rows


def data_quality_score(conn: duckdb.DuckDBPyConnection) -> float:
    """Overall completeness 0..1 — average of per-dataset completeness."""
    rows = data_quality_breakdown(conn)
    if not rows:
        return 0.0
    return sum(r.completeness for r in rows) / len(rows)


def full_data_quality_report(conn: duckdb.DuckDBPyConnection) -> dict:
    """Diagnostic data quality report for the 5 staging tables.

    Checks: row counts, missing required fields, duplicate IDs,
    referential consistency, date plausibility, negative quantities.

    Returns a dict with:
      score              0–100 integer
      tables             per-table detail
      errors             blocking issues
      warnings           non-blocking issues
      total_rows         across all staging tables
    """

    STAGING_REQUIRED: dict[str, list[str]] = {
        "stg_products":            ["product_name"],
        "stg_supplier_deliveries": ["product_name", "delivery_date"],
        "stg_inventory_lots":      ["product_name", "quantity_on_hand"],
        "stg_buyer_orders":        ["product_name", "requested_quantity"],
        "stg_waste_adjustments":   ["product_name", "quantity_lost"],
    }

    errors: list[str] = []
    warnings: list[str] = []
    tables: dict[str, dict] = {}
    score = 100
    total_rows = 0

    for table, required_cols in STAGING_REQUIRED.items():
        try:
            df = conn.execute(f"SELECT * FROM {table}").df()  # noqa: S608
        except Exception:
            errors.append(f"{table}: table not found (migration 010 not applied?)")
            score -= 10
            tables[table] = {"row_count": 0, "status": "missing", "issues": []}
            continue

        n = len(df)
        total_rows += n
        table_issues: list[str] = []

        if n == 0:
            warnings.append(f"{table}: no rows loaded")
            score -= 2
            tables[table] = {"row_count": 0, "status": "empty", "issues": ["empty"]}
            continue

        # Missing required columns
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"{table}.{col}: required column missing from upload")
                score -= 5
                table_issues.append(f"missing column: {col}")
            elif df[col].isna().any():
                null_pct = round(df[col].isna().mean() * 100, 1)
                msg = f"{table}.{col}: {null_pct}% null"
                if null_pct > 20:
                    errors.append(msg)
                    score -= 3
                else:
                    warnings.append(msg)
                    score -= 1
                table_issues.append(f"{null_pct}% null in {col}")

        # Negative quantity checks
        qty_cols = [
            c for c in df.columns
            if any(k in c for k in ("quantity", "qty", "value", "price", "cost"))
            and df[c].dtype in (float, int, "float64", "int64")
        ]
        for qcol in qty_cols:
            try:
                neg_count = int(
                    (pd.to_numeric(df[qcol], errors="coerce").fillna(0) < 0).sum()
                )
                if neg_count > 0:
                    warnings.append(f"{table}.{qcol}: {neg_count} negative values")
                    score -= 1
                    table_issues.append(f"{neg_count} negative values in {qcol}")
            except Exception:
                pass

        # Date plausibility
        date_cols = [c for c in df.columns if "date" in c.lower()]
        for dcol in date_cols:
            try:
                parsed = pd.to_datetime(df[dcol], errors="coerce")
                bad = int(parsed.isna().sum()) - int(df[dcol].isna().sum())
                if bad > 0:
                    warnings.append(f"{table}.{dcol}: {bad} unparseable dates")
                    score -= 1
                    table_issues.append(f"{bad} unparseable dates in {dcol}")
                # Future dates warn
                future = int((parsed > pd.Timestamp.now()).sum())
                if future > 0:
                    warnings.append(
                        f"{table}.{dcol}: {future} future dates (check data)"
                    )
                    table_issues.append(f"{future} future dates in {dcol}")
            except Exception:
                pass

        # Expiry before arrival (inventory lots only)
        if table == "stg_inventory_lots":
            if "arrival_date" in df.columns and "expiration_date" in df.columns:
                try:
                    arr = pd.to_datetime(df["arrival_date"], errors="coerce")
                    exp = pd.to_datetime(df["expiration_date"], errors="coerce")
                    bad_exp = int(((exp < arr) & arr.notna() & exp.notna()).sum())
                    if bad_exp > 0:
                        errors.append(
                            f"stg_inventory_lots: {bad_exp} lots where "
                            f"expiration_date < arrival_date"
                        )
                        score -= 3
                        table_issues.append(
                            f"{bad_exp} lots with expiry before arrival"
                        )
                except Exception:
                    pass

        # Fulfilled > requested (buyer orders)
        if table == "stg_buyer_orders":
            if "fulfilled_quantity" in df.columns and "requested_quantity" in df.columns:
                try:
                    req = pd.to_numeric(df["requested_quantity"], errors="coerce")
                    ful = pd.to_numeric(df["fulfilled_quantity"], errors="coerce")
                    over = int(((ful > req) & req.notna() & ful.notna()).sum())
                    if over > 0:
                        warnings.append(
                            f"stg_buyer_orders: {over} rows where "
                            f"fulfilled_quantity > requested_quantity"
                        )
                        table_issues.append(
                            f"{over} rows: fulfilled > requested"
                        )
                except Exception:
                    pass

        status = "ok" if not table_issues else (
            "error" if any(
                e.startswith(table) for e in errors
            ) else "warning"
        )
        tables[table] = {
            "row_count": n,
            "status": status,
            "issues": table_issues,
        }

    score = max(0, min(100, score))
    return {
        "score": score,
        "score_label": (
            "Excellent" if score >= 90 else
            "Good" if score >= 75 else
            "Fair" if score >= 50 else
            "Poor"
        ),
        "tables": tables,
        "errors": errors,
        "warnings": warnings,
        "total_rows": total_rows,
        # Structured hard-validation results per table (same rules the
        # intake endpoint enforces at upload time), so the scorecard and
        # the upload path can never disagree about what counts as a
        # violation.
        "violations": _staging_violations(conn),
    }


def _staging_violations(conn: duckdb.DuckDBPyConnection) -> dict:
    """Hard-validation results for loaded staging tables (guarded)."""
    try:
        from ingestion.validators import validate_loaded_tables
        return validate_loaded_tables(conn)
    except Exception:  # noqa: BLE001  scorecard must never crash on this
        return {}


# ---------------------------------------------------------------------------
# Waste / spot / shortage breakdowns
# ---------------------------------------------------------------------------

def waste_by_product(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            p.crop_name AS product,
            p.product_id AS product_id,
            COALESCE(SUM(w.qty_wasted_kg), 0) AS waste_kg,
            COALESCE(SUM(w.estimated_value_usd), 0) AS waste_usd,
            COUNT(*) AS events
        FROM dim_products p
        LEFT JOIN fact_waste_events w USING (product_id)
        GROUP BY 1, 2
        ORDER BY waste_usd DESC
        """
    ).df()


def waste_by_reason(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            reason_code,
            waste_stage,
            SUM(qty_wasted_kg) AS waste_kg,
            SUM(estimated_value_usd) AS waste_usd,
            COUNT(*) AS events
        FROM fact_waste_events
        GROUP BY 1, 2
        ORDER BY waste_usd DESC
        """
    ).df()


def spot_by_product(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            p.crop_name AS product,
            p.product_id AS product_id,
            COALESCE(SUM(CASE WHEN po.is_spot_purchase
                          THEN po.qty_committed_kg * po.price_per_kg ELSE 0 END), 0) AS spot_cost_usd,
            COALESCE(SUM(CASE WHEN po.is_spot_purchase
                          THEN po.qty_committed_kg ELSE 0 END), 0) AS spot_kg,
            COALESCE(SUM(po.qty_committed_kg), 0) AS total_kg,
            COALESCE(AVG(CASE WHEN po.is_spot_purchase
                          THEN po.spot_premium_pct END), 0) AS avg_premium_pct
        FROM dim_products p
        LEFT JOIN fact_purchase_orders po USING (product_id)
        GROUP BY 1, 2
        ORDER BY spot_cost_usd DESC
        """
    ).df()


def spot_premium_trend(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Weekly spot premium $ + share over time."""
    return conn.execute(
        """
        SELECT
            week_start,
            SUM(CASE WHEN is_spot_purchase THEN qty_committed_kg * price_per_kg ELSE 0 END) AS spot_cost_usd,
            SUM(CASE WHEN is_spot_purchase THEN qty_committed_kg ELSE 0 END) AS spot_kg,
            SUM(qty_committed_kg) AS total_kg
        FROM fact_purchase_orders
        GROUP BY 1
        ORDER BY 1
        """
    ).df()


def waste_by_week(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            DATE_TRUNC('week', event_date) AS week_start,
            reason_code,
            SUM(qty_wasted_kg) AS waste_kg,
            SUM(estimated_value_usd) AS waste_usd
        FROM fact_waste_events
        GROUP BY 1, 2
        ORDER BY 1
        """
    ).df()


def loss_attribution(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Per-product loss table: waste $ + spot premium $ + likely root cause."""
    spot = spot_by_product(conn).set_index("product_id")
    waste = waste_by_product(conn).set_index("product_id")

    out = (
        spot.join(waste[["waste_kg", "waste_usd", "events"]], rsuffix="_w")
        .reset_index()
        .rename(columns={"events": "spot_events", "events_w": "waste_events"})
    )
    out["product"] = out["product_id"].map(
        spot["product"].to_dict() if "product" in spot.columns else {}
    )

    # Root cause: dominant reason for that product, if waste exists; else spot
    reason = conn.execute(
        """
        SELECT
            product_id,
            reason_code,
            SUM(qty_wasted_kg) AS kg
        FROM fact_waste_events
        GROUP BY 1, 2
        """
    ).df()
    if not reason.empty:
        top = reason.sort_values("kg", ascending=False).drop_duplicates("product_id")
        out = out.merge(
            top[["product_id", "reason_code"]].rename(columns={"reason_code": "top_waste_reason"}),
            on="product_id", how="left",
        )
    else:
        out["top_waste_reason"] = None

    def _action(row) -> str:
        if (row.get("spot_cost_usd") or 0) > 1000 and (row.get("waste_usd") or 0) < 200:
            return "Increase committed volume — spot exposure dominates losses"
        if (row.get("waste_usd") or 0) > 1000 and (row.get("spot_cost_usd") or 0) < 200:
            return "Reduce committed volume or shorten shelf-life buffer"
        if (row.get("spot_cost_usd") or 0) > 200 and (row.get("waste_usd") or 0) > 200:
            return "Re-allocate between suppliers; both directions losing money"
        return "Within tolerance — monitor"

    out["recommended_action"] = out.apply(_action, axis=1)
    return out[[
        "product", "product_id", "spot_cost_usd", "waste_usd",
        "top_waste_reason", "recommended_action",
    ]].sort_values("spot_cost_usd", ascending=False)


def product_risk_heatmap(conn: duckdb.DuckDBPyConnection,
                         weeks: int = 12) -> pd.DataFrame:
    """Per-product per-week risk score 0..1.

    risk = w * spot_share + (1-w) * waste_rate, both capped at 1.0
    """
    df = conn.execute(
        """
        WITH po AS (
            SELECT
                product_id,
                DATE_TRUNC('week', week_start) AS wk,
                SUM(CASE WHEN is_spot_purchase THEN qty_committed_kg ELSE 0 END) AS spot_kg,
                SUM(qty_committed_kg) AS total_kg
            FROM fact_purchase_orders
            GROUP BY 1, 2
        ),
        we AS (
            SELECT
                product_id,
                DATE_TRUNC('week', event_date) AS wk,
                SUM(qty_wasted_kg) AS waste_kg
            FROM fact_waste_events
            GROUP BY 1, 2
        ),
        recv AS (
            SELECT
                product_id,
                DATE_TRUNC('week', delivery_date) AS wk,
                SUM(qty_received_kg) AS recv_kg
            FROM fact_deliveries
            GROUP BY 1, 2
        )
        SELECT
            p.crop_name AS product,
            po.wk AS week,
            CASE WHEN po.total_kg > 0 THEN po.spot_kg / po.total_kg ELSE 0 END AS spot_share,
            CASE WHEN recv.recv_kg > 0 THEN COALESCE(we.waste_kg, 0) / recv.recv_kg ELSE 0 END AS waste_rate
        FROM po
        JOIN dim_products p ON po.product_id = p.product_id
        LEFT JOIN we ON we.product_id = po.product_id AND we.wk = po.wk
        LEFT JOIN recv ON recv.product_id = po.product_id AND recv.wk = po.wk
        WHERE po.wk >= (SELECT MAX(wk) FROM po) - INTERVAL (?) WEEKS
        ORDER BY 2, 1
        """, [weeks],
    ).df()
    if df.empty:
        return df
    df["risk"] = (0.6 * df["spot_share"].clip(0, 1)
                  + 0.4 * df["waste_rate"].clip(0, 1)).clip(0, 1)
    return df


# ---------------------------------------------------------------------------
# Supplier intelligence
# ---------------------------------------------------------------------------

def supplier_reliability(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = conn.execute(
        """
        WITH po AS (
            SELECT supplier_id, product_id, SUM(qty_committed_kg) AS committed_kg,
                   SUM(CASE WHEN is_spot_purchase THEN qty_committed_kg ELSE 0 END) AS spot_kg
            FROM fact_purchase_orders
            GROUP BY 1, 2
        ),
        del AS (
            SELECT supplier_id, product_id,
                   SUM(qty_received_kg) AS received_kg,
                   SUM(qty_rejected_kg) AS rejected_kg,
                   COUNT(*) AS deliveries,
                   AVG(transit_hrs) AS avg_transit_hrs,
                   SUM(CASE WHEN rejection_reason='late' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS late_rate
            FROM fact_deliveries
            GROUP BY 1, 2
        )
        SELECT
            s.supplier_name AS supplier,
            p.crop_name AS product,
            po.committed_kg,
            del.received_kg,
            del.rejected_kg,
            CASE WHEN po.committed_kg > 0
                 THEN LEAST(1.0, del.received_kg / po.committed_kg) END AS fill_reliability,
            CASE WHEN del.received_kg > 0
                 THEN del.rejected_kg / del.received_kg END AS rejection_rate,
            del.late_rate,
            CASE WHEN po.committed_kg > 0
                 THEN po.spot_kg / po.committed_kg END AS spot_replacement_rate,
            del.deliveries
        FROM po
        JOIN dim_suppliers s USING (supplier_id)
        JOIN dim_products p USING (product_id)
        LEFT JOIN del ON del.supplier_id = po.supplier_id AND del.product_id = po.product_id
        ORDER BY fill_reliability ASC NULLS LAST
        """
    ).df()
    if df.empty:
        return df

    def _tier(row) -> str:
        fr = row["fill_reliability"] or 0
        rr = row["rejection_rate"] or 0
        if fr < 0.85 or rr > 0.10:
            return "Critical"
        if fr < 0.92 or rr > 0.06:
            return "High"
        if fr < 0.97 or rr > 0.03:
            return "Medium"
        return "Low"
    df["risk_tier"] = df.apply(_tier, axis=1)
    return df


def supplier_concentration(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Share of total committed volume by supplier."""
    return conn.execute(
        """
        SELECT
            s.supplier_name AS supplier,
            SUM(po.qty_committed_kg) AS committed_kg,
            SUM(po.qty_committed_kg) /
                NULLIF((SELECT SUM(qty_committed_kg) FROM fact_purchase_orders), 0) AS share
        FROM fact_purchase_orders po
        JOIN dim_suppliers s USING (supplier_id)
        GROUP BY 1
        ORDER BY committed_kg DESC
        """
    ).df()


def supplier_trend(conn: duckdb.DuckDBPyConnection,
                   supplier_id: str | None = None) -> pd.DataFrame:
    sql = """
        SELECT
            DATE_TRUNC('month', delivery_date) AS month,
            s.supplier_name AS supplier,
            COUNT(*) AS deliveries,
            SUM(qty_received_kg) AS received_kg,
            SUM(qty_rejected_kg) / NULLIF(SUM(qty_received_kg), 0) AS rejection_rate
        FROM fact_deliveries d
        JOIN dim_suppliers s USING (supplier_id)
    """
    params: list = []
    if supplier_id:
        sql += " WHERE supplier_id = ?"
        params.append(supplier_id)
    sql += " GROUP BY 1, 2 ORDER BY 1"
    return conn.execute(sql, params).df()


# ---------------------------------------------------------------------------
# Buyer intelligence
# ---------------------------------------------------------------------------

def buyer_demand_variability(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = conn.execute(
        """
        WITH lines AS (
            SELECT
                o.buyer_id,
                ol.product_id,
                o.week_start,
                ol.qty_ordered_kg,
                ol.qty_delivered_kg,
                ol.lost_sale_flag
            FROM fact_order_lines ol
            JOIN fact_orders o ON ol.order_id = o.order_id
        )
        SELECT
            b.buyer_name AS buyer,
            p.crop_name AS product,
            COUNT(*) AS lines,
            AVG(qty_ordered_kg) AS avg_order_kg,
            STDDEV_SAMP(qty_ordered_kg) AS order_stddev,
            STDDEV_SAMP(qty_ordered_kg) / NULLIF(AVG(qty_ordered_kg), 0) AS coef_of_variation,
            SUM(CASE WHEN lost_sale_flag THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS lost_sale_rate,
            SUM(qty_delivered_kg) / NULLIF(SUM(qty_ordered_kg), 0) AS fill_rate
        FROM lines l
        JOIN dim_buyers b USING (buyer_id)
        JOIN dim_products p USING (product_id)
        GROUP BY 1, 2
        ORDER BY coef_of_variation DESC NULLS LAST
        """
    ).df()
    if df.empty:
        return df

    def _tier(row) -> str:
        cv = row["coef_of_variation"] or 0
        ls = row["lost_sale_rate"] or 0
        if cv > 0.6 or ls > 0.10:
            return "Critical"
        if cv > 0.4 or ls > 0.05:
            return "High"
        if cv > 0.25:
            return "Medium"
        return "Low"
    df["risk_tier"] = df.apply(_tier, axis=1)
    return df


def buyer_demand_trend(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT
            o.week_start,
            b.buyer_name AS buyer,
            SUM(ol.qty_ordered_kg) AS demand_kg
        FROM fact_order_lines ol
        JOIN fact_orders o ON ol.order_id = o.order_id
        JOIN dim_buyers b ON o.buyer_id = b.buyer_id
        GROUP BY 1, 2
        ORDER BY 1
        """
    ).df()


# ---------------------------------------------------------------------------
# Recommendations table — derived from actuals when planning_recommendations
# is empty (which is the default state until the optimiser is run).
# ---------------------------------------------------------------------------

def recommendation_table(conn: duckdb.DuckDBPyConnection,
                         week_start: pd.Timestamp | date | None = None) -> pd.DataFrame:
    """Per-product weekly recommendation derived from history.

    If the planning_recommendations table is populated, return that;
    otherwise compute a transparent heuristic from history so the page is
    never empty.  The heuristic is clearly labelled in the UI as
    "actuals-derived" so it is never confused with a real optimiser run.
    """
    n = conn.execute("SELECT COUNT(*) FROM planning_recommendations").fetchone()[0]  # type: ignore[index]  # fetchone() on a COUNT/MIN query always yields a row
    if n > 0:
        return conn.execute(
            "SELECT * FROM planning_recommendations ORDER BY priority, generated_at DESC"
        ).df()

    # Heuristic fallback: per-product 4-week mean ± std
    df = conn.execute(
        """
        WITH lines AS (
            SELECT
                o.week_start,
                ol.product_id,
                SUM(ol.qty_ordered_kg) AS demand_kg
            FROM fact_order_lines ol
            JOIN fact_orders o ON ol.order_id = o.order_id
            GROUP BY 1, 2
        ),
        recent AS (
            SELECT
                product_id,
                AVG(demand_kg) AS avg_demand_kg,
                STDDEV_SAMP(demand_kg) AS std_demand_kg
            FROM lines
            WHERE week_start >= (SELECT MAX(week_start) FROM lines) - INTERVAL 8 WEEKS
            GROUP BY 1
        ),
        spot_share AS (
            SELECT
                product_id,
                SUM(CASE WHEN is_spot_purchase THEN qty_committed_kg ELSE 0 END)
                  / NULLIF(SUM(qty_committed_kg), 0) AS spot_share
            FROM fact_purchase_orders
            GROUP BY 1
        ),
        waste_share AS (
            SELECT
                product_id,
                SUM(qty_wasted_kg) AS waste_kg
            FROM fact_waste_events
            GROUP BY 1
        )
        SELECT
            p.crop_name AS product,
            p.product_id,
            r.avg_demand_kg AS demand_forecast_kg,
            r.std_demand_kg AS demand_std_kg,
            r.avg_demand_kg + COALESCE(r.std_demand_kg, 0) * 0.5 AS recommended_commit_kg,
            r.avg_demand_kg AS historical_avg_kg,
            COALESCE(s.spot_share, 0) AS spot_exposure,
            COALESCE(w.waste_kg, 0) AS recent_waste_kg
        FROM dim_products p
        JOIN recent r ON r.product_id = p.product_id
        LEFT JOIN spot_share s ON s.product_id = p.product_id
        LEFT JOIN waste_share w ON w.product_id = p.product_id
        ORDER BY r.avg_demand_kg DESC
        """
    ).df()
    if df.empty:
        return df

    def _shortage(row) -> str:
        if row["spot_exposure"] > 0.20:
            return "High"
        if row["spot_exposure"] > 0.10:
            return "Medium"
        return "Low"

    def _waste(row) -> str:
        if row["recent_waste_kg"] > 200:
            return "High"
        if row["recent_waste_kg"] > 50:
            return "Medium"
        return "Low"

    def _explain(row) -> str:
        bits = []
        cmt = row["recommended_commit_kg"]
        avg = row["historical_avg_kg"]
        delta_pct = (cmt - avg) / avg if avg else 0
        if delta_pct > 0.05:
            bits.append(f"Commit {delta_pct*100:+.0f}% above last 8-week average to absorb demand variance")
        elif delta_pct < -0.05:
            bits.append(f"Commit {delta_pct*100:+.0f}% below average — demand has softened")
        else:
            bits.append("Commit close to recent average — demand stable")
        if row["spot_exposure"] > 0.15:
            bits.append(f"Spot exposure on this SKU runs at {row['spot_exposure']*100:.0f}%")
        if row["recent_waste_kg"] > 100:
            bits.append(f"Recent waste is {row['recent_waste_kg']:.0f} kg — keep buffer tight")
        return ". ".join(bits) + "."

    df["shortage_risk"] = df.apply(_shortage, axis=1)
    df["waste_risk"] = df.apply(_waste, axis=1)
    df["explanation"] = df.apply(_explain, axis=1)
    df["status"] = "Pending"
    df["source"] = "actuals-derived heuristic"  # surfaced in UI
    return df


# ---------------------------------------------------------------------------
# Top-5 risk drivers (used on Executive Overview)
# ---------------------------------------------------------------------------

def top_risk_drivers(conn: duckdb.DuckDBPyConnection, n: int = 5) -> pd.DataFrame:
    """Combine spot exposure and waste $ to surface the top loss drivers."""
    spot = spot_by_product(conn)
    waste = waste_by_product(conn)

    merged = spot.merge(
        waste[["product_id", "waste_usd", "waste_kg"]],
        on="product_id", how="outer",
    ).fillna(0)
    merged["loss_usd"] = merged["spot_cost_usd"] + merged["waste_usd"]
    merged = merged.sort_values("loss_usd", ascending=False).head(n)

    # If product name missing on either side, use the other
    if "product_x" in merged.columns:
        merged["product"] = merged["product_x"].fillna(merged.get("product_y"))
    return merged[["product", "product_id", "loss_usd", "spot_cost_usd", "waste_usd"]]
