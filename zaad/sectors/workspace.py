"""Sector physics from the operator's vault (migration 017 columns) into the frozen request.

Every value comes from a declared column; absent columns or NULL cells attach nothing (the request
stays legacy for that SKU / location / lane) and are reported as UNKNOWN in the provenance. Days are
converted to whole periods (rounded to the nearest period, never below the frozen meaning: a life of
less than half a period is 0)."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from zaad.sectors.contracts import SECTOR_MODES, STORAGE_STATES

PROVENANCE_VALUES = ("OPERATOR_OBSERVED", "OPERATOR_DECLARED", "DERIVED_FROM_OPERATOR_HISTORY", "PUBLIC_PRIOR", "FALLBACK")


def _num(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip().upper()
    return text or None


def periods(days: float | None, period_days: int) -> int | None:
    return None if days is None else max(0, int(round(days / period_days)))


def parse_states(value: Any) -> list[str]:
    """'CHILLED,FROZEN' -> ['CHILLED', 'FROZEN']; unknown tokens raise (a declared but invalid state is a data error)."""
    text = _text(value)
    if not text:
        return []
    states = [s.strip() for s in text.replace(";", ",").split(",") if s.strip()]
    bad = [s for s in states if s not in STORAGE_STATES]
    if bad:
        raise ValueError(f"unknown storage state(s) {bad}; expected {STORAGE_STATES}")
    return sorted(set(states))


def sku_physics_rows(master: pd.DataFrame, planned: list[str], period_days: int, provenance: dict[str, str],
                     warnings: list[str], default_sector: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Profiles for the planned SKUs from the SKU master's physics columns, and the request's default
    sector (the explicit `default_sector`, else the single sector the master declares, else None)."""
    rows: list[dict[str, Any]] = []
    sectors: set[str] = set()
    if master is None or not len(master):
        return rows, default_sector
    cols = set(master.columns)
    physics_cols = {"sector", "storage_state", "age_at_receipt_days", "min_remaining_life_receipt_days", "min_remaining_life_sale_days", "weight_per_unit"}
    if not (cols & physics_cols):
        provenance["sku.physics"] = "NOT_AVAILABLE"
        return rows, default_sector
    for row in master.itertuples():
        sku = str(row.sku)
        if sku not in planned:
            continue
        sector = _text(getattr(row, "sector", None)) if "sector" in cols else None
        if sector is not None and sector not in SECTOR_MODES:
            raise ValueError(f"SKU {sku}: unknown sector {sector!r}; expected one of {SECTOR_MODES}")
        prov_value = _text(getattr(row, "physics_provenance", None)) if "physics_provenance" in cols else None
        prov = prov_value if prov_value in PROVENANCE_VALUES else "OPERATOR_DECLARED"
        fields: dict[str, Any] = {}
        state = _text(getattr(row, "storage_state", None)) if "storage_state" in cols else None
        if state is not None:
            if state not in STORAGE_STATES:
                raise ValueError(f"SKU {sku}: unknown storage state {state!r}; expected one of {STORAGE_STATES}")
            fields["storage_state"] = state
        for column, field in (("age_at_receipt_days", "age_at_receipt_periods"), ("min_remaining_life_receipt_days", "minimum_remaining_life_at_receipt"),
                              ("min_remaining_life_sale_days", "minimum_remaining_life_at_sale")):
            value = periods(_num(getattr(row, column, None)) if column in cols else None, period_days)
            if value is not None:
                fields[field] = value
        weight = _num(getattr(row, "weight_per_unit", None)) if "weight_per_unit" in cols else None
        if weight is not None and weight > 0:
            fields["weight_per_unit"] = weight
        if sector is None and not fields:
            continue
        sectors.add(sector or default_sector or "COMMERCIAL")
        rows.append({"sku": sku, "sector": sector or default_sector or "COMMERCIAL", **fields, "provenance": {k: prov for k in fields}})
    if rows:
        provenance["sku.physics"] = "CUSTOMER_PROVIDED"
    mode = default_sector or (next(iter(sectors)) if len(sectors) == 1 else None)
    if len(sectors) > 1 and default_sector is None:
        warnings.append(f"SKU master declares several sectors {sorted(sectors)}; the request carries per-SKU profiles and no default sector")
    return rows, mode


def lot_expiry_periods(expiry_date: Any, origin: pd.Timestamp, period_days: int, default: int) -> tuple[int, str]:
    """A lot's remaining life in periods from its expiry date; the SKU's shelf life when absent."""
    if expiry_date is None:
        return default, "NOT_AVAILABLE"
    try:
        if pd.isna(expiry_date):
            return default, "NOT_AVAILABLE"
        remaining = (pd.Timestamp(expiry_date) - origin).days
    except (TypeError, ValueError):
        return default, "NOT_AVAILABLE"
    return max(0, min(default, int(remaining // period_days))), "CUSTOMER_PROVIDED"
