"""Pool contribution pipeline — anonymized signals, consent-gated.

The pool is HarvestMind's compounding asset, and it is safe precisely
because of what it refuses to carry. Per signal:

  demand_patterns    category (never product), week-of-year, CV, trend,
                     mean NORMALIZED to 1.0 (never actual volume)
  yield_distributions category + operator-level region (never supplier),
                     fill-rate mean/std (ratios), n_deliveries
  waste_profiles     category, waste RATE (ratio), bucketed reason, season

Hard rules enforced here, before anything is written:
- consent checked first; non-consented operators are skipped and the
  skip is logged
- anonymization happens at extraction — raw rows never leave the vault
- k-anonymity floor: a signal built on fewer than K_ANONYMITY_FLOOR
  underlying rows is dropped (small samples can identify a business)
- operator_id is kept ON the signal for audit/withdrawal-accounting
  only; the PoolReader never exposes it
- contribute_session never raises — failures are logged and the upload
  flow continues

Storage: one parquet file per contribution under
pool/signals/<signal>/<contribution_id>.parquet — append-safe and
atomic (a partial write can't corrupt prior contributions); readers
treat the directory as the dataset.
"""

from __future__ import annotations

import re

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

from infrastructure.consent_manager import ConsentManager
from infrastructure.db_manager import DBManager
from infrastructure.operator_registry import OperatorRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POOL_ROOT = REPO_ROOT / "pool"

K_ANONYMITY_FLOOR = 10

# Names must never appear in any pool signal — checked by tests by
# scanning the written parquet payloads.
SIGNALS = ("demand_patterns", "yield_distributions", "waste_profiles")

_REASON_BUCKETS = {
    "over_commitment": ("over", "commit", "surplus", "unsold", "excess"),
    "supplier_quality": ("quality", "reject", "damage", "temperature",
                         "spoil", "grade"),
    "demand_miss": ("demand", "order", "cancel", "forecast", "missed"),
}


class ContributionResult(BaseModel):
    status: str                       # contributed | skipped | error
    operator_id: str
    contribution_id: str | None = None
    reason: str | None = None
    signals_written: dict[str, int] = {}
    signals_dropped_k_anonymity: int = 0


def _season(month: int) -> str:
    return f"Q{(month - 1) // 3 + 1}"


def _bucket_reason(raw: Any) -> str:
    text = str(raw or "").lower()
    for bucket, words in _REASON_BUCKETS.items():
        if any(w in text for w in words):
            return bucket
    return "over_commitment"



_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _assert_ident(name: str) -> str:
    """operator ids come from the registry, never from a request, but a
    schema name interpolated into SQL is validated regardless."""
    if not _IDENT_RE.match(str(name)):
        raise ValueError(f"invalid identifier {name!r}")
    return str(name)


class PoolContributor:
    def __init__(
        self,
        registry: OperatorRegistry | None = None,
        pool_root: str | Path | None = None,
    ) -> None:
        self.registry = registry or OperatorRegistry()
        self.pool_root = Path(pool_root) if pool_root else DEFAULT_POOL_ROOT

    # ── public entry ─────────────────────────────────────────────────────

    def contribute_session(self, operator_id: str) -> ContributionResult:
        """Extract + anonymize + write this operator's current signals.
        Triggered after every confirmed session. Never raises."""
        try:
            cm = ConsentManager(self.registry)
            if operator_id not in cm.get_consented_operators():
                self._log({"event": "skipped", "operator_id": operator_id,
                           "reason": "no consent (or not active)"})
                return ContributionResult(
                    status="skipped", operator_id=operator_id,
                    reason="operator has not consented to pool contribution")
            return self._contribute(operator_id)
        except Exception as e:  # noqa: BLE001  never break the upload flow
            self._log({"event": "error", "operator_id": operator_id,
                       "error": f"{type(e).__name__}: {e}"})
            return ContributionResult(status="error",
                                      operator_id=operator_id,
                                      reason=str(e))

    # ── extraction (reads the vault read-only, writes only signals) ─────

    def _contribute(self, operator_id: str) -> ContributionResult:
        record = self.registry.get_operator(operator_id)
        contribution_id = f"contrib_{secrets.token_hex(6)}"
        now = datetime.now(timezone.utc)

        dbm = DBManager(self.registry)
        conn = dbm.get_cross_operator_connection(
            [operator_id], purpose=f"pool contribution {contribution_id}")
        try:
            demand = self._demand_signals(conn, operator_id, record.region)
            yields = self._yield_signals(conn, operator_id, record.region)
            waste = self._waste_signals(conn, operator_id)
        finally:
            dbm.close_all()

        # Re-check consent immediately before any write. Consent is checked at
        # the start of contribute_session, but extraction reads the vault and
        # can take time; if the operator withdrew consent in that window we
        # must NOT write — pool signals are irreversible once written.
        if operator_id not in ConsentManager(self.registry).get_consented_operators():
            self._log({"event": "skipped", "operator_id": operator_id,
                       "reason": "consent withdrawn before write"})
            return ContributionResult(
                status="skipped", operator_id=operator_id,
                reason="consent withdrawn before write")

        dropped = sum(d.pop("_dropped", 0)
                      for d in (demand, yields, waste))
        written: dict[str, int] = {}
        for name, frame in (("demand_patterns", demand["df"]),
                            ("yield_distributions", yields["df"]),
                            ("waste_profiles", waste["df"])):
            if frame.empty:
                continue
            frame = frame.assign(
                operator_id=operator_id,
                contribution_id=contribution_id,
                contributed_at=now.isoformat(),
            )
            d = self.pool_root / "signals" / name
            d.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(d / f"{contribution_id}.parquet", index=False)
            written[name] = len(frame)

        self._log({"event": "contributed", "operator_id": operator_id,
                   "contribution_id": contribution_id,
                   "signal_counts": written,
                   "dropped_k_anonymity": dropped})
        self.registry.record_pool_contribution(operator_id)
        return ContributionResult(
            status="contributed", operator_id=operator_id,
            contribution_id=contribution_id, signals_written=written,
            signals_dropped_k_anonymity=dropped)

    def _demand_signals(self, conn, operator_id: str, region: str) -> dict:
        operator_id = _assert_ident(operator_id)
        q = (  # nosec B608 - operator_id validated by _assert_ident, not user input
            f"""
            SELECT COALESCE(p.category, 'uncategorized') AS category,
                   DATE_TRUNC('week', COALESCE(o.delivery_date, o.order_date)) AS week_start,
                   SUM(o.requested_quantity) AS demand
            FROM {operator_id}.stg_buyer_orders o
            LEFT JOIN {operator_id}.stg_products p
                   ON o.product_id = p.product_id
            WHERE o.requested_quantity IS NOT NULL
              AND COALESCE(o.delivery_date, o.order_date) IS NOT NULL
            GROUP BY 1, 2
        """)  # nosec B608 - operator_id validated by _assert_ident, not user input
        df = conn.execute(q).df()
        rows, dropped = [], 0
        if not df.empty:
            # The k-anonymity count MUST use the same filter as the signal
            # query above — otherwise NULL-quantity/date rows inflate the
            # count and a signal built on < K underlying rows can slip through.
            counts = conn.execute(  # nosec B608 - operator_id validated by _assert_ident, not user input
                f"""
                SELECT COALESCE(p.category, 'uncategorized') AS category,
                       COUNT(*) AS n
                FROM {operator_id}.stg_buyer_orders o
                LEFT JOIN {operator_id}.stg_products p
                       ON o.product_id = p.product_id
                WHERE o.requested_quantity IS NOT NULL
                  AND COALESCE(o.delivery_date, o.order_date) IS NOT NULL
                GROUP BY 1
            """).df().set_index("category")["n"].to_dict()  # nosec B608 - operator_id validated by _assert_ident, not user input
            for cat, g in df.groupby("category"):
                if counts.get(cat, 0) < K_ANONYMITY_FLOOR:
                    dropped += 1
                    continue
                vals = g["demand"].to_numpy(dtype=float)
                mean = float(vals.mean())
                if mean <= 0:
                    continue
                recent = float(vals[-4:].mean()) if len(vals) >= 8 else mean
                trend = ("increasing" if recent > mean * 1.10 else
                         "decreasing" if recent < mean * 0.90 else "stable")
                rows.append({
                    "category": str(cat).lower().replace(" ", "_"),
                    "week_of_year": int(datetime.now(timezone.utc)
                                        .isocalendar().week),
                    "demand_cv": round(float(vals.std(ddof=0)) / mean, 4),
                    "demand_mean_normalized": 1.0,   # never actual volume
                    "trend_direction": trend,
                    "n_weeks": int(len(vals)),
                })
        return {"df": pd.DataFrame(rows), "_dropped": dropped}

    def _yield_signals(self, conn, operator_id: str, region: str) -> dict:
        operator_id = _assert_ident(operator_id)
        q = (  # nosec B608 - operator_id validated by _assert_ident, not user input
            f"""
            SELECT COALESCE(p.category, 'uncategorized') AS category,
                   d.ordered_quantity AS ordered,
                   COALESCE(d.accepted_quantity, d.delivered_quantity) AS accepted
            FROM {operator_id}.stg_supplier_deliveries d
            LEFT JOIN {operator_id}.stg_products p
                   ON d.product_id = p.product_id
            WHERE d.ordered_quantity IS NOT NULL AND d.ordered_quantity > 0
        """)  # nosec B608 - operator_id validated by _assert_ident, not user input
        df = conn.execute(q).df()
        rows, dropped = [], 0
        if not df.empty:
            df["fill"] = (df["accepted"].fillna(0).astype(float)
                          / df["ordered"].astype(float)).clip(0, 1)
            for cat, g in df.groupby("category"):
                if len(g) < K_ANONYMITY_FLOOR:   # the k-anonymity floor
                    dropped += 1
                    continue
                rows.append({
                    "category": str(cat).lower().replace(" ", "_"),
                    "region": region,             # operator-level only
                    "season": _season(datetime.now(timezone.utc).month),
                    "fill_rate_mean": round(float(g["fill"].mean()), 4),
                    "fill_rate_std": round(float(g["fill"].std(ddof=0)), 4),
                    "n_deliveries": int(len(g)),
                })
        return {"df": pd.DataFrame(rows), "_dropped": dropped}

    def _waste_signals(self, conn, operator_id: str) -> dict:
        operator_id = _assert_ident(operator_id)
        q = (  # nosec B608 - operator_id validated by _assert_ident, not user input
            f"""
            SELECT COALESCE(p.category, 'uncategorized') AS category,
                   w.quantity_lost, w.reason
            FROM {operator_id}.stg_waste_adjustments w
            LEFT JOIN {operator_id}.stg_products p
                   ON w.product_id = p.product_id
            WHERE w.quantity_lost IS NOT NULL
        """)  # nosec B608 - operator_id validated by _assert_ident, not user input
        waste = conn.execute(q).df()
        delivered = conn.execute(  # nosec B608 - operator_id validated by _assert_ident, not user input
            f"""
            SELECT COALESCE(p.category, 'uncategorized') AS category,
                   SUM(COALESCE(d.accepted_quantity, d.delivered_quantity)) AS total
            FROM {operator_id}.stg_supplier_deliveries d
            LEFT JOIN {operator_id}.stg_products p
                   ON d.product_id = p.product_id
            GROUP BY 1
        """).df()  # nosec B608 - operator_id validated by _assert_ident, not user input
        totals = delivered.set_index("category")["total"].to_dict() \
            if not delivered.empty else {}
        rows, dropped = [], 0
        if not waste.empty:
            for cat, g in waste.groupby("category"):
                if len(g) < K_ANONYMITY_FLOOR:
                    dropped += 1
                    continue
                base = float(totals.get(cat) or 0.0)
                lost = float(g["quantity_lost"].sum())
                if base <= 0:
                    continue
                reasons = g["reason"].map(_bucket_reason)
                rows.append({
                    "category": str(cat).lower().replace(" ", "_"),
                    "waste_rate": round(min(lost / base, 1.0), 4),  # ratio
                    "primary_reason": reasons.mode().iloc[0]
                    if not reasons.empty else "over_commitment",
                    "season": _season(datetime.now(timezone.utc).month),
                    "n_events": int(len(g)),
                })
        return {"df": pd.DataFrame(rows), "_dropped": dropped}

    # ── audit log (operator_id + counts only, never content) ────────────

    def _log(self, entry: dict) -> None:
        d = self.pool_root / "contributions"
        d.mkdir(parents=True, exist_ok=True)
        entry = {"at": datetime.now(timezone.utc).isoformat(), **entry}
        with (d / "contribution_log.jsonl").open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
