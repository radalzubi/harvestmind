"""Data API router: query master data and operational facts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_conn

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/suppliers")
def list_suppliers(conn=Depends(get_conn)):
    df = conn.execute("SELECT * FROM dim_suppliers ORDER BY supplier_name").df()
    conn.close()
    return df.to_dict("records")


@router.get("/products")
def list_products(is_ftl: bool | None = None, conn=Depends(get_conn)):
    q = "SELECT * FROM dim_products"
    if is_ftl is not None:
        q += f" WHERE is_ftl_item = {str(is_ftl).upper()}"
    q += " ORDER BY crop_name"
    df = conn.execute(q).df()
    conn.close()
    return df.to_dict("records")


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
    conn.close()
    return df.to_dict("records")


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
    conn.close()
    return df.to_dict("records")


@router.get("/fsma/lots")
def list_lots(product_id: str | None = None, conn=Depends(get_conn)):
    q = "SELECT l.*, p.crop_name FROM fact_lots l JOIN dim_products p ON l.product_id = p.product_id"
    if product_id:
        q += f" WHERE l.product_id = '{product_id}'"
    q += " ORDER BY l.created_at DESC LIMIT 200"
    df = conn.execute(q).df()
    conn.close()
    return df.to_dict("records")


@router.get("/fsma/report")
def fsma_report(tlc: str | None = None, conn=Depends(get_conn)):
    """Return FDA-ready 24-hour spreadsheet data."""
    q = 'SELECT * FROM v_fsma_204_report'
    if tlc:
        q += f" WHERE traceability_lot_code = '{tlc}'"
    q += " LIMIT 1000"
    df = conn.execute(q).df()
    conn.close()
    return df.to_dict("records")
