"""Deterministic signals: detection without fabrication.

A signal is a comparison the registry already defines, computed by the same engine, with a stated
window and threshold. V1 ships two detectors the curated questions need:

  * supplier deterioration — late rate and fill rate, recent half of the window against the
    earlier half, per supplier, with the sample size; a direction, never a cause;
  * cover exposure — products below or above stated cover thresholds at the latest snapshot.

Nothing here decides anything; a signal offers to open the analysis behind it.
"""
from __future__ import annotations

from typing import Any

from api.analytics import query
from api.analytics.contracts import AnalyticsQuerySpec
from api.product.governance import Actor

MIN_PERIODS = 4
MIN_ORDERS = 6


def _v(cell: Any) -> float | None:
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def supplier_deterioration(conn: Any, operator: str, actor: Actor | None, *, months: int = 12) -> dict[str, Any]:
    spec = AnalyticsQuerySpec.model_validate({"measures": [{"metric_id": "supplier_late_rate"}, {"metric_id": "supplier_fill_rate"}, {"metric_id": "matched_orders"}],
                                              "dimensions": [{"dimension_id": "supplier"}], "time": {"grain": "month", "range": {"last": months, "unit": "month"}}, "purpose": "signal"})
    result = query.run(conn, operator, actor, spec)
    cols = [c["id"] for c in result["columns"]]
    i_sup, i_date = cols.index("supplier"), cols.index("date")
    i_late, i_fill, i_n = cols.index("supplier_late_rate"), cols.index("supplier_fill_rate"), cols.index("matched_orders")
    series: dict[str, list[tuple[str, float | None, float | None, float]]] = {}
    if not result.get("empty"):
        for row in result["rows"]:
            sup = row[i_sup]
            if isinstance(sup, dict) or sup is None:
                continue
            series.setdefault(str(sup), []).append((str(row[i_date])[:10], _v(row[i_late]), _v(row[i_fill]), float(_v(row[i_n]) or 0)))
    signals: list[dict[str, Any]] = []
    unmeasured: list[str] = []
    for sup, points in series.items():
        points.sort()
        orders = sum(p[3] for p in points)
        late_points = [(d, v) for d, v, _, _ in points if v is not None]
        fill_points = [(d, v) for d, _, v, _ in points if v is not None]
        if not late_points and orders >= MIN_ORDERS:
            unmeasured.append(sup)
        if len(points) < MIN_PERIODS or orders < MIN_ORDERS:
            continue

        def halves(pts: list[tuple[str, float]]) -> tuple[float | None, float | None]:
            if len(pts) < MIN_PERIODS:
                return None, None
            h = len(pts) // 2
            return sum(v for _, v in pts[:h]) / h, sum(v for _, v in pts[h:]) / (len(pts) - h)

        late_e, late_r = halves(late_points)
        fill_e, fill_r = halves(fill_points)
        late_delta = (late_r - late_e) if (late_e is not None and late_r is not None) else None
        fill_delta = (fill_r - fill_e) if (fill_e is not None and fill_r is not None) else None
        worse = (late_delta is not None and late_delta > 0.05) or (fill_delta is not None and fill_delta < -0.03)
        signals.append({"supplier": sup, "periods": len(points), "matched_orders": orders, "late_rate_earlier": late_e, "late_rate_recent": late_r, "late_rate_change": late_delta,
                        "fill_rate_earlier": fill_e, "fill_rate_recent": fill_r, "fill_rate_change": fill_delta, "worsening": worse,
                        "basis": "recent half of the window against the earlier half; a direction over months, not a cause",
                        "lateness": None if late_points else "NOT_MEASURED"})
    signals.sort(key=lambda s: (-(s["late_rate_change"] or 0) - (-(s["fill_rate_change"] or 0)), s["supplier"]))
    return {"kind": "supplier_deterioration", "window_months": months, "signals": signals, "lateness_unmeasured": unmeasured,
            "thresholds": {"late_rate_change": 0.05, "fill_rate_change": -0.03, "min_periods": MIN_PERIODS, "min_orders": MIN_ORDERS},
            "provenance": result["provenance"], "dataset_version": result["dataset_version"], "query_id": result["query_id"]}


def cover_exposure(conn: Any, operator: str, actor: Actor | None, *, under_weeks: float = 2.0, over_weeks: float = 12.0, limit: int = 50) -> dict[str, Any]:
    spec = AnalyticsQuerySpec.model_validate({"measures": [{"metric_id": "weeks_of_cover"}, {"metric_id": "inventory_units"}], "dimensions": [{"dimension_id": "sku"}], "limit": 400, "purpose": "signal"})
    result = query.run(conn, operator, actor, spec)
    cols = [c["id"] for c in result["columns"]]
    i_sku, i_cover, i_units = cols.index("sku"), cols.index("weeks_of_cover"), cols.index("inventory_units")
    under: list[dict[str, Any]] = []
    over: list[dict[str, Any]] = []
    unknown = 0
    if not result.get("empty"):
        for row in result["rows"]:
            cover = _v(row[i_cover])
            if cover is None:
                unknown += 1
                continue
            entry = {"sku": row[i_sku], "weeks_of_cover": cover, "units": _v(row[i_units])}
            if cover < under_weeks:
                under.append(entry)
            elif cover > over_weeks:
                over.append(entry)
    under.sort(key=lambda e: e["weeks_of_cover"])
    over.sort(key=lambda e: -e["weeks_of_cover"])
    return {"kind": "cover_exposure", "under": under[:limit], "over": over[:limit], "unknown": unknown,
            "thresholds": {"under_weeks": under_weeks, "over_weeks": over_weeks}, "truncated": result["bounds"]["truncated"],
            "provenance": result["provenance"], "dataset_version": result["dataset_version"], "query_id": result["query_id"]}
