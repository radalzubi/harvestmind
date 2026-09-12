"""P5 vault adapter (migration 020): the operator's declared customer orders, service classes and
promising policy -> `AtpSpec`. Absent tables or no rows -> None (the frozen request)."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


def _present(value) -> bool:
    return value is not None and not (isinstance(value, float) and pd.isna(value))


def _table(conn, name: str, operator_id: str) -> pd.DataFrame | None:
    try:
        return conn.execute(f"SELECT * FROM {name} WHERE operator_id = ?", [operator_id]).df()  # noqa: S608  # nosec B608 - table names are code literals
    except Exception:  # noqa: BLE001  table absent (pre-020 vault): nothing to attach
        return None


def atp_block(conn, operator_id: str) -> dict[str, Any] | None:
    orders = _table(conn, "stg_atp_customer_orders", operator_id)
    if orders is None or orders.empty:
        return None
    classes = _table(conn, "stg_atp_service_classes", operator_id)
    policy = _table(conn, "stg_atp_policy", operator_id)
    class_rows = []
    for r in (classes.to_dict("records") if classes is not None else []):
        row = {"id": r["class_id"]}
        for k in ("provenance", "reference", "contractual_service_floor", "shortage_penalty_per_unit", "late_penalty_per_unit_period", "refusal_cost_per_unit", "lost_margin_per_unit", "strategic", "tier"):
            if _present(r.get(k)):
                row[k] = r[k]
        class_rows.append(row)
    by_order: dict[str, dict[str, Any]] = {}
    for r in orders.to_dict("records"):
        o = by_order.setdefault(r["order_id"], {"id": r["order_id"], "customer": r["customer_id"], "service_class": r["service_class"], "lines": []})
        for k in ("order_period", "partial_fulfillment_allowed", "backorder_allowed", "max_backorder_periods", "substitution_allowed", "late_semantics", "priority_provenance"):
            if _present(r.get(k)):
                o[k] = r[k]
        line = {"id": r["line_id"], "sku": r["sku"], "quantity": r["quantity"], "requested_period": int(r["requested_period"]) if _present(r.get("requested_period")) else 0}
        if _present(r.get("minimum_ship_quantity")):
            line["minimum_ship_quantity"] = r["minimum_ship_quantity"]
        if _present(r.get("unit_margin")):
            line["unit_margin"] = r["unit_margin"]
        if _present(r.get("ship_from")):
            line["ship_from"] = tuple(json.loads(r["ship_from"]))
        o["lines"].append(line)
    block: dict[str, Any] = {"enabled": True, "orders": list(by_order.values()), "service_classes": class_rows}
    if policy is not None and not policy.empty:
        p = policy.to_dict("records")[-1]
        for k in ("incumbent_policy", "fairness", "include_inbound", "inbound_confidence", "promise_horizon", "cross_location", "provenance"):
            if _present(p.get(k)):
                block[k] = p[k]
        if _present(p.get("manual_sequence")):
            block["manual_sequence"] = tuple(json.loads(p["manual_sequence"]))
    return block
