"""FSMA-204 traceability API endpoints.

GET endpoints are read-only (use get_readonly_conn).
POST endpoints (create lot, record CTE) are append-only.
All SQL uses parameterised queries — never f-strings on user input.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator

from api.dependencies import get_conn, get_readonly_conn
from dashboard.lib.fsma_metrics import (
    fsma_coverage_score,
    ftl_product_list,
    fsma_lot_chain,
    generate_fda_report_csv,
    recent_cte_events,
)

router = APIRouter(prefix="/fsma", tags=["fsma-204"])


VALID_CTE_TYPES = {
    "harvesting", "cooling", "initial_packing",
    "shipping", "receiving", "transformation",
}


# ── Read endpoints ───────────────────────────────────────────────────────────

@router.get("/coverage")
def get_coverage(conn=Depends(get_readonly_conn)):
    """Return FSMA-204 traceability coverage score."""
    return fsma_coverage_score(conn)


@router.get("/ftl-products")
def get_ftl_products(conn=Depends(get_readonly_conn)):
    """Return per-FTL-product coverage breakdown."""
    df = ftl_product_list(conn)
    return df.to_dict(orient="records")


@router.get("/report")
def get_report(
    tlc: str | None = Query(default=None, max_length=128),
    fmt: str = Query(default="csv", alias="format", pattern="^(csv|json)$"),
    conn=Depends(get_readonly_conn),
):
    """FDA-style sortable report. Default last 30 days; tlc filters chain."""
    if fmt == "csv":
        body = generate_fda_report_csv(conn, tlc=tlc)
        # Empty = header line only (or completely empty). No data rows → 204.
        non_header_lines = [ln for ln in body.splitlines()[1:] if ln.strip()]
        if not non_header_lines:
            return Response(status_code=204)
        return Response(
            content=body,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=fsma_report.csv"},
        )

    # JSON
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
    return df.to_dict(orient="records")


@router.get("/report/chain")
def get_report_chain(
    tlc: str = Query(..., max_length=128),
    conn=Depends(get_readonly_conn),
):
    """Recursive lot-chain walk for a TLC."""
    df = fsma_lot_chain(conn, tlc)
    return df.to_dict(orient="records")


@router.get("/lots")
def list_lots(
    product_id: str | None = Query(default=None, max_length=64),
    supplier_id: str | None = Query(default=None, max_length=64),
    start_date: str | None = Query(default=None, max_length=10),
    end_date: str | None = Query(default=None, max_length=10),
    conn=Depends(get_readonly_conn),
):
    """List lots, capped at 500 rows. Parameterised filtering."""
    where: list[str] = []
    params: list[Any] = []

    if product_id is not None:
        where.append("product_id = ?")
        params.append(product_id)
    if supplier_id is not None:
        where.append("supplier_id = ?")
        params.append(supplier_id)
    if start_date is not None:
        where.append("harvest_date >= ?")
        params.append(start_date)
    if end_date is not None:
        where.append("harvest_date <= ?")
        params.append(end_date)

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = (  # nosec B608 - columns constant, filters parameterised
        f"""
        SELECT lot_id, traceability_lot_code, tlc_source_reference, product_id,
               quantity_kg, unit_of_measure, harvest_date, pack_date,
               supplier_id, gtin_14, sscc, lot_status
        FROM fact_lots
        {where_clause}
        ORDER BY harvest_date DESC NULLS LAST
        LIMIT 500
    """)  # nosec B608 - columns constant, filters parameterised
    df = conn.execute(sql, params).df()
    return df.to_dict(orient="records")


@router.get("/recent-ctes")
def get_recent_ctes(
    limit: int = Query(default=20, ge=1, le=200),
    conn=Depends(get_readonly_conn),
):
    df = recent_cte_events(conn, limit=limit)
    return df.to_dict(orient="records")


# ── Write endpoints ──────────────────────────────────────────────────────────

class LotCreate(BaseModel):
    traceability_lot_code: str = Field(..., max_length=128)
    product_id: str = Field(..., max_length=64)
    quantity_kg: float = Field(..., gt=0)
    supplier_id: str | None = Field(default=None, max_length=64)
    harvest_date: str | None = Field(default=None, max_length=10)
    pack_date: str | None = Field(default=None, max_length=10)
    tlc_source_reference: str = Field(..., max_length=255)


@router.post("/lots/create", status_code=status.HTTP_201_CREATED)
def create_lot(payload: LotCreate, conn=Depends(get_conn)):
    """Create a lot. Returns 409 on duplicate TLC."""
    existing = conn.execute(
        "SELECT lot_id FROM fact_lots WHERE traceability_lot_code = ?",
        [payload.traceability_lot_code],
    ).fetchone()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Lot with TLC {payload.traceability_lot_code!r} already exists",
        )

    lot_id = f"LOT-{uuid4().hex[:12].upper()}"
    conn.execute(
        """
        INSERT INTO fact_lots
            (lot_id, traceability_lot_code, tlc_source_reference, product_id,
             quantity_kg, supplier_id, harvest_date, pack_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            lot_id,
            payload.traceability_lot_code,
            payload.tlc_source_reference,
            payload.product_id,
            payload.quantity_kg,
            payload.supplier_id,
            payload.harvest_date,
            payload.pack_date,
        ],
    )
    return {"lot_id": lot_id, "traceability_lot_code": payload.traceability_lot_code}


class CTECreate(BaseModel):
    lot_id: str = Field(..., max_length=64)
    cte_type: str
    event_timestamp: datetime
    location_description: str = Field(..., max_length=255)
    business_name: str = Field(..., max_length=255)
    quantity_kg: float | None = Field(default=None, ge=0)
    point_of_contact: str | None = Field(default=None, max_length=128)
    phone_or_email: str | None = Field(default=None, max_length=128)
    referenced_tlc_codes: list[str] | None = None
    new_tlc_code: str | None = Field(default=None, max_length=128)
    recorded_by: str | None = Field(default=None, max_length=128)

    @field_validator("cte_type")
    @classmethod
    def _valid_cte_type(cls, v: str) -> str:
        if v not in VALID_CTE_TYPES:
            raise ValueError(
                f"cte_type must be one of {sorted(VALID_CTE_TYPES)}; got {v!r}"
            )
        return v


@router.post("/cte/record", status_code=status.HTTP_201_CREATED)
def record_cte(payload: CTECreate, conn=Depends(get_conn)):
    """Record a Critical Tracking Event. Returns 404 if lot_id unknown."""
    lot = conn.execute(
        "SELECT traceability_lot_code FROM fact_lots WHERE lot_id = ?",
        [payload.lot_id],
    ).fetchone()
    if not lot:
        raise HTTPException(
            status_code=404,
            detail=f"lot_id {payload.lot_id!r} not found",
        )

    cte_id = f"CTE-{uuid4().hex[:12].upper()}"
    conn.execute(
        """
        INSERT INTO fact_cte_events
            (cte_id, lot_id, traceability_lot_code, cte_type, event_timestamp,
             location_description, business_name, point_of_contact, phone_or_email,
             quantity_kg, referenced_tlc_codes, new_tlc_code, recorded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            cte_id,
            payload.lot_id,
            lot[0],
            payload.cte_type,
            payload.event_timestamp,
            payload.location_description,
            payload.business_name,
            payload.point_of_contact,
            payload.phone_or_email,
            payload.quantity_kg,
            payload.referenced_tlc_codes,
            payload.new_tlc_code,
            payload.recorded_by,
        ],
    )
    return {"cte_id": cte_id, "lot_id": payload.lot_id}
