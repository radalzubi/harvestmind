"""Pilot data completeness: which conclusions the uploaded data can support.

Scores the FMCG staging tables an operator has uploaded against the
fields the safe selector, the economics and the supply model need, and
says explicitly which conclusions weaken when a field is absent. This is
what stands between "we have a plan" and "we have a plan we can defend".
"""

from __future__ import annotations

from dataclasses import dataclass, field

REQUIRED = {
    "stg_fmcg_skus": ["sku", "supplier_id", "unit_cost", "units_per_case"],
    "stg_fmcg_orders": ["sku", "order_date", "qty_ordered"],
    "stg_fmcg_purchase_orders": ["po_id", "po_date", "supplier_id", "sku", "qty_ordered"],
    "stg_fmcg_receipts": ["po_id", "receipt_date", "qty_received"],
    "stg_fmcg_inventory": ["sku", "snapshot_date", "on_hand"],
}
PREFERRED = {
    "stg_fmcg_skus": ["unit_price", "contribution_margin", "moq_units", "supplier_capacity_per_week",
                      "service_class", "manufacturer", "shelf_life_days"],
    "stg_fmcg_orders": ["qty_shipped", "customer_id", "requested_delivery_date", "channel"],
    "stg_fmcg_purchase_orders": ["expected_delivery_date", "unit_cost"],
    "stg_fmcg_receipts": ["qty_rejected", "sku"],
    "stg_fmcg_inventory": ["in_transit", "location_id"],
    "stg_fmcg_promotions": ["sku", "week_start", "uplift"],
    "stg_fmcg_suppliers": ["route", "manufacturer", "capacity_per_week", "lead_time_promised_weeks"],
    "stg_fmcg_economics": ["key", "value", "provenance"],
}
# Which conclusion each preferred field protects.
WEAKENS = {
    ("stg_fmcg_skus", "contribution_margin"): "shortage cost is UNKNOWN; the plan cannot price lost sales and must stay anchored to the incumbent",
    ("stg_fmcg_skus", "unit_price"): "margin cannot be derived; same consequence as a missing contribution margin",
    ("stg_fmcg_skus", "supplier_capacity_per_week"): "capacity is INFERRED from historical PO peaks, so capacity-bound recommendations are advisory",
    ("stg_fmcg_skus", "service_class"): "one service target for every SKU; segmentation is off",
    ("stg_fmcg_orders", "qty_shipped"): "historical shortfalls are invisible; incumbent service cannot be measured, only estimated",
    ("stg_fmcg_orders", "customer_id"): "line and order fill by customer cannot be measured",
    ("stg_fmcg_purchase_orders", "expected_delivery_date"): "on-time performance cannot be measured; lead is receipt minus PO date only",
    ("stg_fmcg_receipts", "qty_rejected"): "quality rejections are counted as fill",
    ("stg_fmcg_inventory", "in_transit"): "pipeline at plan time is estimated from open POs",
    ("stg_fmcg_promotions", "uplift"): "promotions are treated as demand surprises rather than planned inputs",
    ("stg_fmcg_suppliers", "route"): "shared-route disruption cannot be modelled; supplier failures are treated as independent",
    ("stg_fmcg_suppliers", "capacity_per_week"): "supplier-level capacity is INFERRED",
    ("stg_fmcg_economics", "key"): "carrying cost and penalties are ASSUMED from public benchmarks; the policy ranking is sensitive to them",
}
MIN_HISTORY_WEEKS = 26


@dataclass
class ReadinessReport:
    score: float
    required_missing: list = field(default_factory=list)
    preferred_missing: list = field(default_factory=list)
    weakened_conclusions: list = field(default_factory=list)
    history_weeks: int = 0
    row_counts: dict = field(default_factory=dict)
    verdict: str = ""

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def assess(conn) -> ReadinessReport:
    def cols(t):
        try:
            return {r[1] for r in conn.execute(f"PRAGMA table_info('{t}')").fetchall()}  # nosec B608 - constant table
        except Exception:  # noqa: BLE001
            return set()

    def count(t):
        try:
            return int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])  # nosec B608 - constant table
        except Exception:  # noqa: BLE001
            return 0

    def populated(t, c):
        try:
            return int(conn.execute(f"SELECT COUNT(*) FROM {t} WHERE {c} IS NOT NULL").fetchone()[0]) > 0  # nosec B608 - constants
        except Exception:  # noqa: BLE001
            return False

    req_missing, pref_missing, weakened, counts = [], [], [], {}
    for t, fields_ in REQUIRED.items():
        counts[t] = count(t)
        have = cols(t)
        if counts[t] == 0:
            req_missing.append(f"{t}: no rows")
            continue
        for c in fields_:
            if c not in have or not populated(t, c):
                req_missing.append(f"{t}.{c}")
    for t, fields_ in PREFERRED.items():
        counts.setdefault(t, count(t))
        have = cols(t)
        for c in fields_:
            if counts[t] == 0 or c not in have or not populated(t, c):
                pref_missing.append(f"{t}.{c}")
                w = WEAKENS.get((t, c))
                if w and w not in weakened:
                    weakened.append(w)
    weeks = 0
    try:
        row = conn.execute("SELECT MIN(order_date), MAX(order_date) FROM stg_fmcg_orders").fetchone()
        if row and row[0] and row[1]:
            weeks = int((row[1] - row[0]).days // 7)
    except Exception:  # noqa: BLE001
        pass
    total_pref = sum(len(v) for v in PREFERRED.values())
    score = (0.0 if req_missing else 0.6) + 0.4 * (1 - len(pref_missing) / max(total_pref, 1))
    if weeks < MIN_HISTORY_WEEKS:
        weakened.append(f"only {weeks} weeks of order history; the safe selector needs {MIN_HISTORY_WEEKS} to run multiple folds and will defer to the incumbent")
    verdict = ("NOT_READY: required fields missing" if req_missing else
               "READY_WITH_CAVEATS" if pref_missing or weeks < MIN_HISTORY_WEEKS else "READY")
    return ReadinessReport(score=round(score, 3), required_missing=req_missing, preferred_missing=pref_missing,
                           weakened_conclusions=weakened, history_weeks=weeks, row_counts=counts, verdict=verdict)
