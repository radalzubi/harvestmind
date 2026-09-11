"""Sourcing portfolio from the operator's vault (migration 018) into the frozen request.

Every value comes from a declared row or column; an absent table, absent columns or NULL cells attach
nothing, and the adapter then builds the frozen single-source request. Nothing is inferred: a supplier
becomes a source option only through a `stg_fmcg_sources` row, shared risk only through a declared
`risk_group`, and shares, switching costs and the incumbent mix only through their own columns."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


PROVENANCE_VALUES = ("OPERATOR_DECLARED", "DERIVED_FROM_OPERATOR_HISTORY", "PHYSICAL_DEPENDENCY", "PUBLIC_PRIOR", "FALLBACK")
KINDS = ("MANUFACTURER", "PLANT", "PACKAGING", "PORT", "ROUTE", "CARRIER", "3PL", "UPSTREAM_FACILITY", "OTHER")


def _num(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def _flag(value: Any, default: bool) -> bool:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "t", "yes", "y")
    return bool(value)


def source_table(conn: Any) -> pd.DataFrame | None:
    """The declared source options, or None when the vault predates migration 018."""
    try:
        return conn.execute("SELECT * FROM stg_fmcg_sources").df()
    except Exception:
        return None


def alternate_rows(table: pd.DataFrame | None, planned: list[str], primary: dict[str, str]) -> list[dict[str, Any]]:
    """Declared source rows for planned SKUs beyond the primary supplier, normalised."""
    if table is None or not len(table):
        return []
    out = []
    for row in table.itertuples():
        sku, sid = str(row.sku), str(row.supplier_id)
        if sku not in planned or primary.get(sku) == sid:
            continue
        prov = _text(getattr(row, "provenance", None))
        out.append({"sku": sku, "supplier": sid, "approved": _flag(getattr(row, "approved", None), True),
                    "compliance": (_text(getattr(row, "compliance", None)) or "cleared").lower(),
                    "unit_cost": _num(getattr(row, "unit_cost", None)), "freight_per_unit": _num(getattr(row, "freight_per_unit", None)),
                    "handling_per_unit": _num(getattr(row, "handling_per_unit", None)), "fixed_po_cost": _num(getattr(row, "fixed_po_cost", None)),
                    "moq_units": _num(getattr(row, "moq_units", None)), "units_per_case": _num(getattr(row, "units_per_case", None)),
                    "capacity_per_week": _num(getattr(row, "capacity_per_week", None)), "lead_time_promised_weeks": _num(getattr(row, "lead_time_promised_weeks", None)),
                    "age_at_receipt_days": _num(getattr(row, "age_at_receipt_days", None)),
                    "minimum_share": _num(getattr(row, "minimum_share", None)), "maximum_share": _num(getattr(row, "maximum_share", None)),
                    "committed_units": _num(getattr(row, "committed_units", None)), "incumbent_share": _num(getattr(row, "incumbent_share", None)),
                    "switching_cost": _num(getattr(row, "switching_cost", None)),
                    "provenance": prov.upper() if prov and prov.upper() in PROVENANCE_VALUES else "OPERATOR_DECLARED"})
    return out


def primary_rows(table: pd.DataFrame | None, planned: list[str], primary: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Declared share / incumbent / switching values for the primary supplier's own row, per SKU."""
    if table is None or not len(table):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in table.itertuples():
        sku, sid = str(row.sku), str(row.supplier_id)
        if sku in planned and primary.get(sku) == sid:
            prov = _text(getattr(row, "provenance", None))
            out[sku] = {"minimum_share": _num(getattr(row, "minimum_share", None)), "maximum_share": _num(getattr(row, "maximum_share", None)),
                        "committed_units": _num(getattr(row, "committed_units", None)), "incumbent_share": _num(getattr(row, "incumbent_share", None)),
                        "switching_cost": _num(getattr(row, "switching_cost", None)),
                        "provenance": prov.upper() if prov and prov.upper() in PROVENANCE_VALUES else "OPERATOR_DECLARED"}
    return out


def sourcing_block(source_rows: list[dict[str, Any]], declared: dict[str, dict[str, Any]], suppliers: pd.DataFrame | None,
                   location: str, provenance: dict[str, str], warnings: list[str]) -> dict[str, Any] | None:
    """The `sourcing` block from the declared per-source values (`declared[source id]`) and the supplier
    master's risk-group and switching columns. Returns None when nothing is declared (the request stays
    frozen), so activation is explicit."""
    shares, incumbent, switching = [], [], []
    for src in source_rows:
        d = declared.get(src["id"])
        if not d:
            continue
        prov = d.get("provenance", "OPERATOR_DECLARED")
        lo, hi, committed = d.get("minimum_share"), d.get("maximum_share"), d.get("committed_units")
        if lo is not None or hi is not None or committed is not None:
            shares.append({"sku": src["sku"], "destination": src["destination"], "source": src["id"], "minimum_share": float(lo or 0.),
                           "maximum_share": float(hi if hi is not None else 1.), "committed_units": float(committed or 0.), "provenance": prov})
        if d.get("incumbent_share") is not None and d["incumbent_share"] > 0:
            incumbent.append({"sku": src["sku"], "destination": src["destination"], "source": src["id"], "share": float(d["incumbent_share"]), "provenance": prov})
        if d.get("switching_cost") is not None and d["switching_cost"] > 0:
            switching.append({"source": src["id"], "cost": float(d["switching_cost"]), "kind": "SWITCHING", "provenance": prov})
    groups: list[dict[str, Any]] = []
    if suppliers is not None and len(suppliers):
        cols = set(suppliers.columns)
        if "risk_group" in cols:
            by_group: dict[str, list[str]] = {}
            meta: dict[str, tuple[str, str]] = {}
            for row in suppliers.drop_duplicates("supplier_id", keep="last").itertuples():
                gid = _text(getattr(row, "risk_group", None))
                if not gid:
                    continue
                by_group.setdefault(gid, []).append(str(row.supplier_id))
                kind = (_text(getattr(row, "risk_group_kind", None)) or "OTHER").upper() if "risk_group_kind" in cols else "OTHER"
                prov_g = (_text(getattr(row, "risk_group_provenance", None)) or "OPERATOR_DECLARED").upper() if "risk_group_provenance" in cols else "OPERATOR_DECLARED"
                meta[gid] = (kind if kind in KINDS else "OTHER", prov_g if prov_g in PROVENANCE_VALUES else "OPERATOR_DECLARED")
            for gid, members in by_group.items():
                ids = [s["id"] for s in source_rows if s["supplier"] in members]
                if len(ids) < 2:
                    continue
                kind, prov_g = meta[gid]
                groups.append({"id": gid, "kind": kind, "members": ids, "correlation": 1., "provenance": prov_g,
                               "evidence": f"suppliers {sorted(set(members))} declare risk group {gid}"})
                provenance[f"sourcing.risk_group.{gid}"] = prov_g
        if "switching_cost" in cols:
            declared_switch = {s["source"] for s in switching}
            for row in suppliers.drop_duplicates("supplier_id", keep="last").itertuples():
                cost = _num(getattr(row, "switching_cost", None))
                if cost is None or cost <= 0:
                    continue
                for src in source_rows:
                    if src["supplier"] == str(row.supplier_id) and src["id"] not in declared_switch:
                        switching.append({"source": src["id"], "cost": float(cost), "kind": "SWITCHING", "provenance": "OPERATOR_DECLARED"})
    if not (shares or incumbent or switching or groups):
        return None
    provenance.setdefault("sourcing", "CUSTOMER_PROVIDED")
    return {"risk_groups": groups, "share_constraints": shares, "switching_costs": switching, "incumbent_shares": incumbent}
