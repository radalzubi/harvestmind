"""The incumbent: what the operator would have ordered without us.

It is a first-class object because every safe-selection question is
relative to it. Two sources:

  CONFIGURED  the operator states their rule (order-up-to cover in weeks
              and a review cadence, per SKU or globally), or hands over an
              explicit schedule for the horizon.
  INFERRED    estimated from their own PO history: for each SKU, the
              implied order-up-to level is the median of (order quantity +
              inventory position at the PO date) over past POs, and the
              review cadence the median gap between POs. This is a
              statistical description of their behaviour, NOT their policy,
              and every output that uses it says INFERRED.
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field

from domain.uom import round_to_pack


@dataclass
class IncumbentPolicy:
    source: str                              # "configured" | "inferred" | "schedule"
    cover_weeks: dict = field(default_factory=dict)      # product -> order-up-to cover (periods of mean demand)
    review_periods: dict = field(default_factory=dict)   # product -> cadence in periods
    schedule: dict | None = None             # explicit (supplier, product, t) -> qty
    n_pos_used: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    @property
    def label(self) -> str:
        return {"configured": "client policy (configured)", "inferred": "client policy (INFERRED from PO history)",
                "schedule": "client schedule (supplied)"}[self.source]

    def build_schedule(self, fi) -> dict:
        """Open-loop schedule for the fold, in whole lots. ``fi`` is a
        FoldInputs
        the rule replaces expected usage and tops up to the
        cover level at each review point, exactly as the operator's rule
        would, using only the operator's own parameters."""
        if self.schedule is not None:
            return {k: float(v) for k, v in self.schedule.items() if v and v > 0}
        out = {}
        for j in fi.products:
            s_ = fi.supplier_of[j]
            mu = st.mean(fi.train_demand[j]) if fi.train_demand[j] else 0.0
            f = max(st.mean(fi.train_fill[s_]) if fi.train_fill.get(s_) else 1.0, 0.3)
            cover = float(self.cover_weeks.get(j, self.cover_weeks.get("*", fi.lead_of[s_] + 1)))
            review = int(self.review_periods.get(j, self.review_periods.get("*", 1)) or 1)
            pos = fi.opening.get(j, 0.0) + sum(q for (jj, t), q in fi.pipeline.items() if jj == j)
            for t in range(fi.horizon):
                mu_t = mu * float(fi.promo_multiplier.get((j, t), 1.0))
                pos -= mu_t
                if t % review == 0:
                    target = mu * cover
                    q = max(target - pos, 0.0) / f
                    q = round_to_pack(q, fi.policy.pack_spec_for(j))
                    if q > 0:
                        out[(s_, j, t)] = q
                        pos += q * f
        return out


def infer_incumbent(po_history: list, mean_demand: dict, pack_specs: dict | None = None,
                    min_pos: int = 4) -> IncumbentPolicy:
    """
    po_history: list of dicts {sku, period (int), qty, inventory_position_before}
                where inventory_position_before may be None (then the cover
                is estimated from qty alone, less reliably).
    """
    by_sku: dict = {}
    for r in po_history:
        by_sku.setdefault(r["sku"], []).append(r)
    cover, review, n_used, notes = {}, {}, {}, []
    for j, rows in by_sku.items():
        rows = sorted(rows, key=lambda r: r["period"])
        mu = float(mean_demand.get(j, 0.0))
        if len(rows) < min_pos or mu <= 0:
            notes.append(f"{j}: {len(rows)} POs, too few to infer a rule; default cover used")
            continue
        levels = []
        for r in rows:
            pos = r.get("inventory_position_before")
            if pos is None:
                levels.append(r["qty"] / mu + 1.0)       # qty alone: assume ordered at ~1 period of stock
            else:
                levels.append((r["qty"] + pos) / mu)
        cover[j] = max(float(st.median(levels)), 0.5)
        gaps = [b["period"] - a["period"] for a, b in zip(rows, rows[1:]) if b["period"] > a["period"]]
        review[j] = int(max(1, round(st.median(gaps)))) if gaps else 1
        n_used[j] = len(rows)
        if any(r.get("inventory_position_before") is None for r in rows):
            notes.append(f"{j}: inventory position at PO date unknown; cover inferred from quantity alone")
    return IncumbentPolicy(source="inferred", cover_weeks=cover, review_periods=review,
                           n_pos_used=n_used, notes=notes)


def configured_incumbent(cover_weeks: float | dict, review_periods: int | dict = 1) -> IncumbentPolicy:
    cw = cover_weeks if isinstance(cover_weeks, dict) else {"*": float(cover_weeks)}
    rp = review_periods if isinstance(review_periods, dict) else {"*": int(review_periods)}
    return IncumbentPolicy(source="configured", cover_weeks=cw, review_periods=rp)
