"""Scope 3 carbon accounting — transport emissions per delivery.

Walmart's Project Gigaton, Sysco's supplier scorecards, and US Foods'
sustainability reporting all cascade carbon-reporting requirements down
to the supplier (i.e., to a hub or aggregator). Hubs that can't produce
a per-delivery footprint lose contracts.

This module computes Scope 3 (transport) emissions from
``fact_deliveries.transport_miles`` and ``truck_class``, using the EPA
SmartWay default emission factors (kg CO2e per ton-mile).

Source: EPA SmartWay Performance Tables (2024 baseline). The factors
below are the program's mid-range "average" carrier values for each
truck class — they are *defaults*, not partner-specific. Partners with
their own SmartWay registration can supply a calibrated factor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb
import pandas as pd


# kg CO2e per ton-mile by truck class — EPA SmartWay 2024 averages.
EMISSION_FACTORS_KG_PER_TON_MILE: dict[str, float] = {
    "class_8_truckload":       0.130,   # Long-haul OTR
    "class_8_ltl":             0.165,   # Less-than-truckload
    "class_6_to_7_box":        0.215,   # Regional / city distribution
    "class_4_to_5_box":        0.310,   # Local box truck
    "refrigerated_truckload":  0.180,   # Reefer LTL adds ~25%
    "refrigerated_ltl":        0.225,
    "default":                 0.200,   # Conservative midpoint when unknown
}

# Convert kg CO2e per ton-mile → kg CO2e per kg-mile. 1 ton (US) = 907.185 kg.
_TON_TO_KG = 907.185


def emission_factor(truck_class: str | None) -> float:
    """Return kg CO2e per kg-mile for a given truck class."""
    if not truck_class:
        return EMISSION_FACTORS_KG_PER_TON_MILE["default"] / _TON_TO_KG
    factor = EMISSION_FACTORS_KG_PER_TON_MILE.get(
        truck_class.strip().lower().replace(" ", "_"),
        EMISSION_FACTORS_KG_PER_TON_MILE["default"],
    )
    return factor / _TON_TO_KG


def estimate_co2e_kg(qty_kg: float, miles: float, truck_class: str | None = None) -> float:
    """Single-row Scope 3 emissions estimate."""
    if qty_kg is None or miles is None or qty_kg <= 0 or miles <= 0:
        return 0.0
    return float(qty_kg) * float(miles) * emission_factor(truck_class)


def per_delivery_emissions(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Compute Scope 3 (transport) emissions per delivery.

    Uses the cached ``estimated_co2e_kg`` column when populated; otherwise
    computes on-the-fly from miles + truck_class. Falls back to default
    factor if both are missing.
    """
    df = conn.execute("""
        SELECT
            d.delivery_id,
            d.delivery_date,
            d.supplier_id,
            d.product_id,
            d.qty_received_kg,
            d.transport_miles,
            d.truck_class,
            d.fuel_type,
            d.estimated_co2e_kg
        FROM fact_deliveries d
        ORDER BY d.delivery_date DESC
    """).df()
    if df.empty:
        return df

    def _row_co2(r):
        cached = r.get("estimated_co2e_kg")
        if cached is not None and pd.notna(cached) and float(cached) > 0:
            return float(cached)
        miles = r.get("transport_miles")
        if miles is None or pd.isna(miles):
            return None
        return estimate_co2e_kg(
            qty_kg=float(r.get("qty_received_kg") or 0),
            miles=float(miles),
            truck_class=r.get("truck_class"),
        )

    df["computed_co2e_kg"] = df.apply(_row_co2, axis=1)
    return df


def carbon_summary(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Top-level Scope 3 summary suitable for a dashboard tile.

    Returns:
      total_co2e_kg              total trailing-12-month transport emissions
      total_co2e_t               same in metric tons
      kg_co2_per_kg_received     emissions intensity (kg CO2 per kg of produce)
      coverage_pct               fraction of deliveries with miles+truck_class set
      n_deliveries               total deliveries in period
      n_with_data                deliveries with usable miles
    """
    df = per_delivery_emissions(conn)
    if df.empty:
        return {
            "total_co2e_kg": 0.0, "total_co2e_t": 0.0,
            "kg_co2_per_kg_received": 0.0,
            "coverage_pct": 0.0,
            "n_deliveries": 0, "n_with_data": 0,
        }

    df_year = df[
        pd.to_datetime(df["delivery_date"]) >= (pd.Timestamp.now() - pd.Timedelta(days=365))
    ]
    n_deliveries = int(len(df_year))
    with_data = df_year[df_year["computed_co2e_kg"].notna()]
    n_with_data = int(len(with_data))

    total_co2e_kg = float(with_data["computed_co2e_kg"].sum())
    total_received = float(with_data["qty_received_kg"].fillna(0).sum())
    intensity = (total_co2e_kg / total_received) if total_received > 0 else 0.0
    coverage = (n_with_data / n_deliveries) if n_deliveries else 0.0

    return {
        "total_co2e_kg": round(total_co2e_kg, 1),
        "total_co2e_t":  round(total_co2e_kg / 1000.0, 2),
        "kg_co2_per_kg_received": round(intensity, 5),
        "coverage_pct": round(coverage, 4),
        "n_deliveries": n_deliveries,
        "n_with_data": n_with_data,
    }


def backfill_estimated_co2e(conn) -> int:
    """One-shot job: populate fact_deliveries.estimated_co2e_kg for any
    rows where transport_miles is set but the cached value is missing.

    Returns the number of rows updated.
    """
    miles_rows = conn.execute("""
        SELECT delivery_id, qty_received_kg, transport_miles, truck_class
        FROM fact_deliveries
        WHERE transport_miles IS NOT NULL
          AND (estimated_co2e_kg IS NULL OR estimated_co2e_kg = 0)
    """).fetchall()

    updates = 0
    for delivery_id, qty, miles, truck_class in miles_rows:
        co2 = estimate_co2e_kg(
            qty_kg=float(qty or 0),
            miles=float(miles or 0),
            truck_class=truck_class,
        )
        if co2 <= 0:
            continue
        conn.execute(
            "UPDATE fact_deliveries SET estimated_co2e_kg = ? WHERE delivery_id = ?",
            [round(co2, 4), delivery_id],
        )
        updates += 1
    return updates
