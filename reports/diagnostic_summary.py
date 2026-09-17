"""Enrich the diagnostic summary with the evidence the report needs.

The diagnostic job (`api/routers/jobs.py`) already computes everything the
customer-facing report talks about: the readiness assessment, the inferred
incumbent, the state estimate per SKU and supplier, the lane outlooks and
the safe-selection evidence. Until now only a thin slice of it reached the
summary, which is why the report could show a candidate that "cleared the
gate" next to "incumbent retained" and nothing in between.

`enrich(summary, ...)` copies the missing evidence into the summary under
NEW keys. It is additive: every key the old summary had keeps its shape.
Nothing here is computed by the optimizer or changes what it decided; a
value that cannot be derived from the objects is simply absent (never
zero, never a guess). Every function is defensive: the diagnostic must
never fail because a report field could not be filled.
"""
from __future__ import annotations

import logging
import math
import statistics as st
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("harvestmind.diagnostic_summary")

SUMMARY_VERSION = "2026.09.2"
# PO lines without a matching receipt are counted as still open only inside
# this window; older unmatched lines are more likely cancelled or unrecorded.
OPEN_PO_WINDOW_WEEKS = 8


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r(x: Any, nd: int = 4) -> float | None:
    v = _f(x)
    return None if v is None else round(v, nd)


def readiness_detail(ready: Any) -> dict:
    """The full readiness assessment, not just the verdict."""
    out: dict = {}
    for k in ("verdict", "score", "history_weeks", "required_missing", "preferred_missing",
              "weakened_conclusions", "row_counts"):
        v = getattr(ready, k, None)
        if v is not None:
            out[k] = list(v) if isinstance(v, (list, tuple)) else (dict(v) if isinstance(v, dict) else v)
    return out


def incumbent_detail(fi: Any) -> dict | None:
    inc = getattr(fi, "incumbent", None)
    if inc is None:
        return None
    return {"source": getattr(inc, "source", None),
            "cover_weeks": {str(k): _r(v, 2) for k, v in (getattr(inc, "cover_weeks", {}) or {}).items()},
            "review_periods": {str(k): int(v) for k, v in (getattr(inc, "review_periods", {}) or {}).items()},
            "n_pos_used": {str(k): int(v) for k, v in (getattr(inc, "n_pos_used", {}) or {}).items()},
            "notes": list(getattr(inc, "notes", []) or [])}


def sku_profiles(fi: Any, est: Any, unknown_margin: set | None = None) -> dict:
    """Per-SKU evidence: demand level and variability, zero share, cover,
    supplier, value share and the estimator's regime reading."""
    out: dict = {}
    products = list(getattr(fi, "products", []) or [])
    if not products:
        return out
    values: dict = {}
    for j in products:
        d = [float(x) for x in (fi.train_demand.get(j) or [])]
        values[j] = (st.mean(d) if d else 0.0) * float(fi.unit_cost.get(j, 0.0) or 0.0)
    total_value = sum(values.values()) or 0.0
    sku_states = getattr(est, "sku", {}) or {}
    for j in products:
        d = [float(x) for x in (fi.train_demand.get(j) or [])]
        n = len(d)
        mu: float | None = st.mean(d) if d else None
        cv = (st.pstdev(d) / mu) if (n > 1 and mu) else None
        zero = (sum(1 for x in d if x <= 0) / n) if n else None
        s = sku_states.get(j)
        feats = getattr(s, "features", {}) if s is not None else {}
        prof = {"supplier": fi.supplier_of.get(j), "periods": n,
                "mean_weekly_demand": _r(mu, 2), "demand_cv": _r(cv, 3), "zero_share": _r(zero, 3),
                "unit_cost": _r(fi.unit_cost.get(j), 4),
                "value_share": _r(values[j] / total_value, 4) if total_value > 0 else None,
                "cover_periods": _r(feats.get("cover_periods"), 2),
                "opening_on_hand": _r(fi.opening.get(j), 2) if getattr(fi, "opening", None) else None,
                "demand_shift_sd": _r(feats.get("demand_shift_sd"), 2),
                "demand_shift_age": feats.get("demand_shift_age"),
                "margin_known": j not in (unknown_margin or set())}
        if s is not None:
            prof.update({"dominant": s.dominant, "stress": _r(s.stress, 3), "reasons": list(s.reasons[:3])})
        out[str(j)] = prof
    return out


def supplier_profiles(fi: Any, est: Any, sku_prof: dict) -> dict:
    """Per-supplier evidence: receipts observed, fill level and trend, lead
    mean and spread, share of value, SKUs, lane, regime reading."""
    out: dict = {}
    sups = sorted(set((getattr(fi, "supplier_of", {}) or {}).values()))
    sup_states = getattr(est, "supplier", {}) or {}
    events = getattr(fi, "supply_events", {}) or {}
    for s_ in sups:
        ev = events.get(s_, {}) or {}
        keys = sorted(k for k in ev if k < 0)
        fills = [float(ev[k][0]) for k in keys]
        leads = [float(ev[k][1]) for k in keys]
        skus = [j for j, sup in fi.supplier_of.items() if sup == s_]
        value_share = sum((sku_prof.get(j, {}).get("value_share") or 0.0) for j in skus)
        prof: dict = {"n_receipts": len(fills), "n_skus": len(skus), "skus": [str(j) for j in skus][:40],
                      "value_share": _r(value_share, 4), "lane": (getattr(fi, "route_of", {}) or {}).get(s_),
                      "lead_weeks_assumed": fi.lead_of.get(s_) if getattr(fi, "lead_of", None) else None}
        if fills:
            prof.update({"fill_mean": _r(st.mean(fills), 3), "fill_min": _r(min(fills), 3),
                         "short_receipts": int(sum(1 for f in fills if f < 0.95)),
                         "fill_recent": _r(st.mean(fills[-4:]), 3)})
        if leads:
            prof.update({"lead_mean_weeks": _r(st.mean(leads), 2), "lead_max_weeks": _r(max(leads), 2),
                         "lead_sd_weeks": _r(st.pstdev(leads), 2) if len(leads) > 1 else 0.0,
                         "lead_recent_weeks": _r(st.mean(leads[-4:]), 2)})
        if not fills and fi.train_fill.get(s_):
            prof["fill_assumed"] = _r(st.mean(fi.train_fill[s_]), 3)
        s = sup_states.get(s_)
        if s is not None:
            prof.update({"dominant": s.dominant, "stress": _r(s.stress, 3), "reasons": list(s.reasons[:3]),
                         "fill_shift": _r((s.features or {}).get("fill_shift"), 3),
                         "lead_ratio": _r((s.features or {}).get("lead_ratio"), 2),
                         "change_point": bool((s.change_points or {}).get("cusum") or (s.change_points or {}).get("page_hinkley"))})
        out[str(s_)] = prof
    return out


def candidate_evidence(decision: Any) -> dict:
    """Everything the safe selector recorded per candidate, including the
    nested held-out re-check, so the report can explain a retained incumbent."""
    out: dict = {}
    for name, ev in (getattr(decision, "evidence", {}) or {}).items():
        stats = dict(getattr(ev, "stats", {}) or {})
        if not stats:
            continue
        svc = list(getattr(ev, "service_diff", []) or [])
        inv = list(getattr(ev, "inventory_diff", []) or [])
        out[str(name)] = {
            "mean": _r(stats.get("mean")), "lower_bound": _r(stats.get("lower_bound")),
            "worst": _r(stats.get("worst")), "best": _r(stats.get("best")), "win_rate": _r(stats.get("win_rate")),
            "downside_regret": _r(stats.get("downside_regret")),
            "n_folds": int(getattr(ev, "n_folds", 0) or 0), "passed": bool(getattr(ev, "passed", False)),
            "gates": {k: bool(v) for k, v in (getattr(ev, "gates", {}) or {}).items()},
            "fold_deltas": [_r(x) for x in (getattr(ev, "deltas_rel", []) or [])],
            "service_diff_min": _r(min(svc)) if svc else None,
            "service_diff_mean": _r(st.mean(svc)) if svc else None,
            "inventory_diff_mean": _r(st.mean(inv)) if inv else None,
            "solves_usable": int(getattr(ev, "solves_usable", 0) or 0), "fallbacks": int(getattr(ev, "fallbacks", 0) or 0),
            "holdout_mean": _r(getattr(ev, "holdout_delta_rel", None)),
            "holdout_lower_bound": _r((getattr(ev, "holdout_stats", {}) or {}).get("lower_bound")),
            "holdout_worst": _r((getattr(ev, "holdout_stats", {}) or {}).get("worst")),
            "holdout_gates": {k: bool(v) for k, v in (getattr(ev, "holdout_gates", {}) or {}).items()},
            "holdout_fold_deltas": None,
        }
    return out


def gate_config(decision: Any) -> dict:
    cfg = dict(getattr(decision, "gates_config", {}) or {})
    keep = ("n_folds", "n_holdout_folds", "holdout", "min_history", "min_rel_improvement", "service_tolerance",
            "max_regret_share", "confidence", "n_scen", "prefer_simpler_within")
    out = {k: cfg[k] for k in keep if k in cfg}
    meta = getattr(decision, "meta", {}) or {}
    if meta.get("posture"):
        p = meta["posture"]
        out["posture"] = {k: p.get(k) for k in ("mode", "min_rel_improvement", "confidence") if k in p}
    return out


def lane_exposure(fi: Any, sku_prof: dict, sup_prof: dict, conn: Any) -> dict:
    """What of the operator's own business rides on each lane: suppliers,
    SKUs, share of value, and PO lines without a receipt inside the recent
    window (labelled as an estimate of open orders)."""
    out: dict = {}
    route_of = getattr(fi, "route_of", {}) or {}
    if not route_of:
        return out
    open_by_sup: dict = {}
    try:
        latest = conn.execute("SELECT MAX(po_date) FROM stg_fmcg_purchase_orders").fetchone()
        cutoff = None
        if latest and latest[0] is not None:
            from datetime import timedelta
            cutoff = latest[0] - timedelta(weeks=OPEN_PO_WINDOW_WEEKS)
        if cutoff is not None:
            has_cost = any(r[1] == "unit_cost" for r in conn.execute("PRAGMA table_info('stg_fmcg_purchase_orders')").fetchall())
            cost_expr = "COALESCE(p.unit_cost, s.unit_cost)" if has_cost else "s.unit_cost"
            rows = conn.execute(
                f"SELECT p.supplier_id, COUNT(*) AS lines, SUM(p.qty_ordered) AS units, COUNT(DISTINCT p.sku) AS skus, "  # noqa: S608  # nosec B608 - constant columns
                f"SUM(p.qty_ordered * {cost_expr}) AS value_at_cost "
                "FROM stg_fmcg_purchase_orders p LEFT JOIN stg_fmcg_receipts r ON r.po_id = p.po_id "
                "LEFT JOIN stg_fmcg_skus s ON s.sku = p.sku "
                "WHERE r.po_id IS NULL AND p.po_date >= ? GROUP BY p.supplier_id", [cutoff]).fetchall()
            for sup, lines, units, skus, value in rows:
                open_by_sup[str(sup)] = {"lines": int(lines or 0), "units": _r(units, 0), "skus": int(skus or 0), "value_at_cost": _r(value, 2)}
    except Exception as exc:  # noqa: BLE001  the table shape may not allow the join
        log.info("open PO estimate unavailable: %s", type(exc).__name__)
        open_by_sup = {}
    for lane in sorted(set(str(r).lower() for r in route_of.values())):
        sups = [s for s, r in route_of.items() if str(r).lower() == lane]
        skus = [j for j, s in fi.supplier_of.items() if s in sups]
        value = sum((sku_prof.get(j, {}).get("value_share") or 0.0) for j in skus)
        entry: dict = {"suppliers": [str(s) for s in sups], "n_skus": len(skus), "skus": [str(j) for j in skus][:40],
                       "value_share": _r(value, 4)}
        if open_by_sup:
            agg: dict = {"lines": 0, "units": 0.0, "skus": 0, "value_at_cost": 0.0}
            seen = False
            for s in sups:
                o = open_by_sup.get(str(s))
                if o:
                    seen = True
                    agg["lines"] += o["lines"]
                    agg["units"] += o["units"] or 0.0
                    agg["skus"] += o["skus"]
                    agg["value_at_cost"] = (agg["value_at_cost"] + o["value_at_cost"]) if (o.get("value_at_cost") is not None and agg["value_at_cost"] is not None) else None
            basis = f"PO lines without a matching receipt in the last {OPEN_PO_WINDOW_WEEKS} weeks of history"
            entry["open_po_estimate"] = {**agg, "basis": basis} if seen else {"lines": 0, "units": 0.0, "skus": 0, "value_at_cost": None, "basis": f"no PO line without a receipt in the last {OPEN_PO_WINDOW_WEEKS} weeks of history"}
        out[lane] = entry
    return out


def lane_detail(est: Any) -> dict:
    """The outlook with its named contributions, missing and stale feeds."""
    out: dict = {}
    for r, o in (getattr(est, "outlooks", {}) or {}).items():
        out[str(r).lower()] = {"risk": _r(o.risk), "quality": _r(o.quality),
                               "contributions": {k: _r(v, 3) for k, v in (o.contributions or {}).items()},
                               "missing": list(o.missing or []), "stale": list(o.stale or []),
                               "reasons": list(o.reasons or [])[:6]}
    return out


def history_range(conn: Any) -> dict:
    out: dict = {}
    try:
        row = conn.execute("SELECT MIN(order_date), MAX(order_date), COUNT(*) FROM stg_fmcg_orders").fetchone()
        if row and row[0] and row[1]:
            out = {"orders_from": str(row[0])[:10], "orders_to": str(row[1])[:10], "order_lines": int(row[2] or 0)}
        row = conn.execute("SELECT MIN(po_date), MAX(po_date), COUNT(*) FROM stg_fmcg_purchase_orders").fetchone()
        if row and row[0] and row[1]:
            out.update({"pos_from": str(row[0])[:10], "pos_to": str(row[1])[:10], "po_lines": int(row[2] or 0)})
        row = conn.execute("SELECT COUNT(*) FROM stg_fmcg_receipts").fetchone()
        if row:
            out["receipt_lines"] = int(row[0] or 0)
    except Exception as exc:  # noqa: BLE001
        log.info("history range unavailable: %s", type(exc).__name__)
    return out


def currency_declared(conn: Any) -> str | None:
    try:
        row = conn.execute("SELECT value FROM stg_fmcg_economics WHERE key = 'currency' LIMIT 1").fetchone()
        return str(row[0]).strip().upper() if row and row[0] else None
    except Exception:  # noqa: BLE001
        return None


def enrich(summary: dict, *, ready: Any = None, fi: Any = None, est: Any = None, decision: Any = None,
           report: dict | None = None, conn: Any = None) -> dict:
    """Add the report evidence to a commercial diagnostic summary in place and return it."""
    try:
        summary["summary_version"] = SUMMARY_VERSION
        summary["generated_at"] = datetime.now(timezone.utc).isoformat()
        if ready is not None:
            summary["readiness_detail"] = readiness_detail(ready)
        if fi is not None:
            summary["incumbent_detail"] = incumbent_detail(fi)
            unknown = set(str(x) for x in ((report or {}).get("unknown_margin_skus") or []))
            sku_prof = sku_profiles(fi, est, unknown)
            summary["sku_profile"] = sku_prof
            sup_prof = supplier_profiles(fi, est, sku_prof)
            summary["supplier_profile"] = sup_prof
            if conn is not None:
                summary["lane_exposure"] = lane_exposure(fi, sku_prof, sup_prof, conn)
            summary["service_level_target"] = _r(getattr(getattr(fi, "policy", None), "service_level", None), 3)
        if est is not None:
            summary["lane_detail"] = lane_detail(est)
            port = getattr(est, "portfolio", None)
            if port is not None:
                summary["state"] = {**(summary.get("state") or {}), "data_quality": _r(port.data_quality, 3),
                                    "components": {k: _r(v, 3) for k, v in (port.components or {}).items()}}
        if decision is not None:
            summary["candidate_evidence"] = candidate_evidence(decision)
            summary["gate_config"] = gate_config(decision)
            summary["decision_meta"] = {k: v for k, v in (getattr(decision, "meta", {}) or {}).items()
                                        if k in ("selection_basis", "status")}
        if report:
            summary["carrying_cost"] = report.get("carrying_cost")
            summary["carrying_cost_sensitivity"] = report.get("carrying_cost_sensitivity")
            summary["unknown_margin_skus"] = list(report.get("unknown_margin_skus") or [])[:50]
            summary["unknown_margin_count"] = len(report.get("unknown_margin_skus") or [])
            summary["supply_history_events"] = report.get("supply_history_events")
        if conn is not None:
            summary["history_range"] = history_range(conn)
            summary["currency"] = currency_declared(conn)
    except Exception as exc:  # noqa: BLE001  the diagnostic result stands even if a report field is missing
        log.exception("summary enrichment incomplete")
        summary.setdefault("warnings", []).append(f"report evidence incomplete ({type(exc).__name__}); "
                                                  "the core result is unaffected")
    return summary
