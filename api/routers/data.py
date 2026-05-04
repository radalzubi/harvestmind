"""Data API router: query master data and operational facts."""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query

from api.dependencies import get_conn

router = APIRouter(prefix="/data", tags=["data"])


def _records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-serializable records, coercing arrays and replacing NaN with None."""
    if df.empty:
        return []
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].apply(
                lambda v: list(v) if isinstance(v, (np.ndarray, list)) else v
            )
    rows = out.to_dict("records")

    # Final pass: replace any scalar NaN/NaT with None for JSON safety
    def _safe(v):
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        if isinstance(v, (list, dict, str, int, bool)):
            return v
        # pandas Timestamp/NaT and other scalars
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        return v

    return [{k: _safe(v) for k, v in row.items()} for row in rows]


@router.get("/suppliers")
def list_suppliers(conn=Depends(get_conn)):
    df = conn.execute("SELECT * FROM dim_suppliers ORDER BY supplier_name").df()
    return _records(df)


@router.get("/products")
def list_products(is_ftl: bool | None = None, conn=Depends(get_conn)):
    if is_ftl is None:
        df = conn.execute("SELECT * FROM dim_products ORDER BY crop_name").df()
    else:
        df = conn.execute(
            "SELECT * FROM dim_products WHERE is_ftl_item = ? ORDER BY crop_name",
            [bool(is_ftl)],
        ).df()
    return _records(df)


@router.get("/deliveries/recent")
def recent_deliveries(weeks: int = Query(4, ge=1, le=52), conn=Depends(get_conn)):
    df = conn.execute(
        "SELECT d.*, p.crop_name, s.supplier_name "
        "FROM fact_deliveries d "
        "JOIN dim_products p ON d.product_id = p.product_id "
        "JOIN dim_suppliers s ON d.supplier_id = s.supplier_id "
        "WHERE d.delivery_date >= CURRENT_DATE - INTERVAL (? * 7) DAYS "
        "ORDER BY d.delivery_date DESC LIMIT 500",
        [weeks],
    ).df()
    return _records(df)


@router.get("/orders/weekly-demand")
def weekly_demand(weeks: int = Query(13, ge=1, le=104), conn=Depends(get_conn)):
    df = conn.execute(
        "SELECT o.week_start, ol.product_id, SUM(ol.qty_ordered_kg) AS demand_kg, "
        "SUM(ol.qty_delivered_kg) AS delivered_kg, "
        "SUM(CASE WHEN ol.lost_sale_flag THEN 1 ELSE 0 END) AS lost_sales "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id "
        "WHERE o.week_start >= CURRENT_DATE - INTERVAL (? * 7) DAYS "
        "GROUP BY 1, 2 ORDER BY 1, 2",
        [weeks],
    ).df()
    return _records(df)


@router.get("/fsma/lots")
def list_lots(product_id: str | None = None, conn=Depends(get_conn)):
    if product_id is None:
        df = conn.execute(
            "SELECT l.*, p.crop_name FROM fact_lots l "
            "JOIN dim_products p ON l.product_id = p.product_id "
            "ORDER BY l.created_at DESC LIMIT 200"
        ).df()
    else:
        df = conn.execute(
            "SELECT l.*, p.crop_name FROM fact_lots l "
            "JOIN dim_products p ON l.product_id = p.product_id "
            "WHERE l.product_id = ? "
            "ORDER BY l.created_at DESC LIMIT 200",
            [product_id],
        ).df()
    return _records(df)


@router.get("/fsma/report")
def fsma_report(tlc: str | None = None, conn=Depends(get_conn)):
    """Return FDA-ready 24-hour spreadsheet data."""
    if tlc is None:
        df = conn.execute("SELECT * FROM v_fsma_204_report LIMIT 1000").df()
    else:
        df = conn.execute(
            "SELECT * FROM v_fsma_204_report WHERE traceability_lot_code = ? LIMIT 1000",
            [tlc],
        ).df()
    return _records(df)
