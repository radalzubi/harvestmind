"""FMCG distributor simulator producing coherent ERP-like histories.

CLASSIFICATION: SYNTHETIC CALIBRATED. Every record is generated. The
shape parameters trace to public evidence (named inline); no distributor's
books were used. Do not present output as operator data.

WHAT "COHERENT" MEANS HERE. A supplier receipt is not drawn independently
of the purchase order it fulfils; it is that PO's quantity times a fill
draw, landing at the PO date plus a lead-time draw, both from the SAME
supplier state. A stockout is not a random flag; it is what happens when
cumulative demand exceeds on-hand plus arrivals. Lost sales, backorders,
emergency buys and inventory snapshots are all consequences of the same
physical state machine, so the cross-variable relationships a real ERP
shows (long lead -> low stock -> stockout -> emergency PO) are present
because they were caused, not because they were sampled.

The replenishment policy driving the history is a deliberately ordinary
periodic order-up-to, so the history looks like a competent human ran it.
That is what a pilot's uploaded data will look like, and it is the
baseline any optimizer must beat.

ARCHETYPES (section 12 of the readiness spec):
  A stable        predictable demand, reliable suppliers
  B volatile      promotion-heavy, demand spikes
  C constrained   variable fill, long lead times
  D importer      long lead, container MOQ, pallet ordering
  E mixed         fast + medium + slow/dead stock portfolio
  F disruption    a supplier or logistics shock mid-history
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from domain.uom import PackSpec, Unit

# ── calibration anchors (public) ────────────────────────────────────────────
# Gross margin 12-22% import distribution; carrying 1.5-2.5%/month; US
# merchant wholesalers I/S ratio mean 1.264 (38 days) over 414 months of
# Census MWTS; OTIF norms 90-98% (Walmart: 98% collect, 90% on-time prepaid,
# 95% in-full); ABC 20/30/50 SKU share carrying 80/15/5 of volume.
GROSS_MARGIN = (0.12, 0.22)
CARRY_PER_WEEK = 0.02 / 4.33
TARGET_COVER_WEEKS = 38 / 7.0


@dataclass
class ArchetypeSpec:
    name: str
    n_skus: int = 60
    n_suppliers: int = 8
    n_customers: int = 25
    weeks: int = 156
    demand_cv: float = 0.20
    promo_weeks_per_year: int = 4
    promo_uplift: float = 1.8
    seasonal_amp: float = 0.10
    fill_mean: float = 0.96
    fill_sd: float = 0.03
    lead_mean_weeks: float = 2.0
    lead_cv: float = 0.25
    order_multiple: Unit = Unit.CASE
    moq_cases: int = 0
    dead_stock_share: float = 0.0
    disruption_week: int | None = None
    disruption_len: int = 0
    disruption_fill_mult: float = 1.0
    disruption_lead_mult: float = 1.0
    disrupted_supplier_share: float = 0.0
    service_target: float = 0.97
    # Progressive episode: list of (week, fill_mult, lead_mult) breakpoints,
    # linearly interpolated, applied to the disrupted suppliers. Lets a
    # test build deterioration -> trough -> recovery, a false alarm (one
    # week), or a demand-only shock (profile empty, demand_shock set).
    disruption_profile: list = field(default_factory=list)
    disrupted_suppliers: tuple = ()          # explicit supplier ids; overrides the share draw
    demand_shock: tuple | None = None        # (week, len, multiplier) demand-side shock


ARCHETYPES: dict[str, ArchetypeSpec] = {
    "A_stable": ArchetypeSpec("A_stable", demand_cv=0.12, fill_mean=0.98, fill_sd=0.015,
                              lead_cv=0.10, promo_weeks_per_year=2),
    "B_volatile_retail": ArchetypeSpec("B_volatile_retail", demand_cv=0.45,
                                       promo_weeks_per_year=12, promo_uplift=2.4,
                                       seasonal_amp=0.25),
    "C_constrained_supplier": ArchetypeSpec("C_constrained_supplier", fill_mean=0.86,
                                            fill_sd=0.08, lead_mean_weeks=4.0, lead_cv=0.45),
    "D_importer": ArchetypeSpec("D_importer", lead_mean_weeks=8.0, lead_cv=0.30,
                                order_multiple=Unit.PALLET, moq_cases=40, fill_mean=0.93,
                                fill_sd=0.05),
    "E_mixed_portfolio": ArchetypeSpec("E_mixed_portfolio", n_skus=150, dead_stock_share=0.25,
                                       demand_cv=0.30),
    "F_disruption": ArchetypeSpec("F_disruption", disruption_week=90, disruption_len=10,
                                  disruption_fill_mult=0.55, disruption_lead_mult=2.2,
                                  disrupted_supplier_share=0.5),
}


@dataclass
class FMCGHistory:
    """ERP-shaped tables. All quantities in EACHES (base unit)."""

    archetype: str
    seed: int
    skus: pd.DataFrame
    suppliers: pd.DataFrame
    customers: pd.DataFrame
    customer_orders: pd.DataFrame
    order_lines: pd.DataFrame
    purchase_orders: pd.DataFrame
    receipts: pd.DataFrame
    inventory_snapshots: pd.DataFrame
    stockouts: pd.DataFrame
    promotions: pd.DataFrame
    pack_specs: dict = field(default_factory=dict)
    classification: str = "SYNTHETIC CALIBRATED"

    def tables(self) -> dict[str, pd.DataFrame]:
        return {k: getattr(self, k) for k in (
            "skus", "suppliers", "customers", "customer_orders", "order_lines",
            "purchase_orders", "receipts", "inventory_snapshots", "stockouts",
            "promotions")}


def _abc(i: int, n: int) -> str:
    return "A" if i < 0.2 * n else "B" if i < 0.5 * n else "C"


def build_history(archetype: str = "A_stable", seed: int = 0,
                  spec: ArchetypeSpec | None = None) -> FMCGHistory:
    sp = spec or ARCHETYPES[archetype]
    rng = np.random.default_rng(seed)
    start = date(2023, 1, 2)
    weeks = [start + timedelta(weeks=w) for w in range(sp.weeks)]

    # ── master data ──────────────────────────────────────────────────────
    suppliers = pd.DataFrame([{
        "supplier_id": f"SUP-{k+1:03d}", "supplier_name": f"Supplier {k+1}",
        "base_fill": float(np.clip(rng.normal(sp.fill_mean, sp.fill_sd), 0.5, 1.0)),
        "lead_mean_weeks": float(max(0.5, rng.normal(sp.lead_mean_weeks, sp.lead_mean_weeks * 0.15))),
        "lead_cv": sp.lead_cv,
        "disrupted": (f"SUP-{k+1:03d}" in sp.disrupted_suppliers) if sp.disrupted_suppliers
                     else bool(rng.random() < sp.disrupted_supplier_share),
    } for k in range(sp.n_suppliers)])

    skus, pack_specs = [], {}
    for i in range(sp.n_skus):
        klass = _abc(i, sp.n_skus)
        cost = float(np.round(rng.uniform(0.6, 12.0), 2))
        gm = float(rng.uniform(*GROSS_MARGIN))
        upc = int(rng.choice([6, 12, 24]))
        spec_ = PackSpec(units_per_case=upc, cases_per_layer=10, layers_per_pallet=5,
                         order_multiple=sp.order_multiple,
                         moq_units=float(sp.moq_cases * upc))
        pack_specs[f"SKU-{i+1:04d}"] = spec_
        weekly = {"A": rng.uniform(600, 2400), "B": rng.uniform(120, 600),
                  "C": rng.uniform(5, 120)}[klass]
        dead = klass == "C" and rng.random() < sp.dead_stock_share
        skus.append({
            "sku": f"SKU-{i+1:04d}", "abc": klass, "category": f"cat_{i % 6}",
            "supplier_id": suppliers.iloc[i % sp.n_suppliers]["supplier_id"],
            "unit_cost": cost, "unit_price": round(cost / (1 - gm), 3),
            "units_per_case": upc, "cases_per_pallet": 50,
            "moq_units": spec_.moq_units, "base_weekly_units": float(weekly),
            "dead_stock": dead, "service_target": sp.service_target,
            "shelf_life_days": int(rng.choice([180, 365, 540, 730])),
        })
    skus = pd.DataFrame(skus)
    customers = pd.DataFrame([{
        "customer_id": f"CUS-{c+1:03d}",
        "channel": str(rng.choice(["modern_trade", "traditional", "horeca"], p=[0.3, 0.55, 0.15])),
        "tier": int(rng.choice([1, 2, 3], p=[0.2, 0.5, 0.3])),
        "share": float(rng.gamma(2.0, 1.0)),
    } for c in range(sp.n_customers)])
    customers["share"] /= customers["share"].sum()

    # ── promotions and seasonality ───────────────────────────────────────
    promo_weeks = set(rng.choice(sp.weeks, size=min(sp.weeks, sp.promo_weeks_per_year * (sp.weeks // 52 + 1)),
                                 replace=False).tolist())
    promos = []
    promo_sku: dict[int, set] = {}
    for w in promo_weeks:
        chosen = rng.choice(skus.index, size=max(1, sp.n_skus // 8), replace=False)
        for i in chosen:
            promo_sku.setdefault(w, set()).add(skus.loc[i, "sku"])
            promos.append({"week_start": weeks[w], "sku": skus.loc[i, "sku"],
                           "uplift": sp.promo_uplift})
    season = 1.0 + sp.seasonal_amp * np.sin(2 * np.pi * np.arange(sp.weeks) / 52.0)

    # ── supplier state per week (disruption is a state, not a flag) ──────
    def _profile_mult(w):
        """(fill_mult, lead_mult) from the progressive profile at week w."""
        pts = sorted(sp.disruption_profile)
        if not pts or w < pts[0][0] or w > pts[-1][0]:
            return 1.0, 1.0
        for (w0, f0, l0), (w1, f1, l1) in zip(pts, pts[1:]):
            if w0 <= w <= w1:
                a = 0.0 if w1 == w0 else (w - w0) / (w1 - w0)
                return f0 + (f1 - f0) * a, l0 + (l1 - l0) * a
        return pts[-1][1], pts[-1][2]

    def supplier_state(sid_row, w):
        if sp.disruption_profile:
            fm, lm = _profile_mult(w)
            hit = sid_row["disrupted"] and fm < 0.999
            fill = sid_row["base_fill"] * (fm if sid_row["disrupted"] else 1.0)
            lead = sid_row["lead_mean_weeks"] * (lm if sid_row["disrupted"] else 1.0)
            return float(np.clip(fill, 0.0, 1.0)), float(lead), bool(hit)
        hit = (sp.disruption_week is not None and sid_row["disrupted"]
               and sp.disruption_week <= w < sp.disruption_week + sp.disruption_len)
        fill = sid_row["base_fill"] * (sp.disruption_fill_mult if hit else 1.0)
        lead = sid_row["lead_mean_weeks"] * (sp.disruption_lead_mult if hit else 1.0)
        return float(np.clip(fill, 0.0, 1.0)), float(lead), hit

    # ── the state machine ────────────────────────────────────────────────
    on_hand = {r.sku: r.base_weekly_units * TARGET_COVER_WEEKS for r in skus.itertuples()}
    in_transit: dict[int, list[tuple[str, float, str]]] = {}   # arrival week -> [(sku, qty, po_id)]
    orders, lines, pos, receipts, snaps, stockouts = [], [], [], [], [], []
    po_seq = 0
    sup_map = suppliers.set_index("supplier_id")

    for w, wk in enumerate(weeks):
        # arrivals
        for sku, qty, po_id in in_transit.pop(w, []):
            on_hand[sku] += qty
            receipts.append({"receipt_date": wk, "po_id": po_id, "sku": sku,
                             "qty_received": round(qty, 0)})
        # demand and fulfilment, customer by customer
        for r in skus.itertuples():
            if r.dead_stock and w > 20:
                dem_total = 0.0
            else:
                mult = season[w] * (sp.promo_uplift if r.sku in promo_sku.get(w, set()) else 1.0)
                if sp.demand_shock and sp.demand_shock[0] <= w < sp.demand_shock[0] + sp.demand_shock[1]:
                    mult *= float(sp.demand_shock[2])
                dem_total = max(0.0, rng.normal(r.base_weekly_units * mult,
                                                r.base_weekly_units * mult * sp.demand_cv))
            if r.abc == "C" and rng.random() < 0.35:
                dem_total = 0.0
            served_total = ordered_total = 0.0
            for c in customers.itertuples():
                q = dem_total * c.share
                if q < 1:
                    continue
                q = float(round(q))
                served = min(q, on_hand[r.sku])
                on_hand[r.sku] -= served
                served_total += served
                ordered_total += q
                oid = f"ORD-{w:04d}-{c.customer_id[-3:]}"
                lines.append({"order_id": oid, "sku": r.sku, "qty_ordered": q,
                              "qty_shipped": served, "qty_short": q - served})
            # A stockout is a shortfall against what customers ORDERED, which
            # is what an ERP records; demand that never became an order line
            # (sub-unit allocations) is not a stockout.
            if ordered_total > 0 and served_total < ordered_total - 1e-9:
                stockouts.append({"week_start": wk, "sku": r.sku,
                                  "units_short": round(ordered_total - served_total, 0)})
            # replenishment: periodic order-up-to with fill gross-up
            srow = sup_map.loc[r.supplier_id]
            fill, lead, _ = supplier_state(srow, w)
            cover = lead + 1.0
            target = r.base_weekly_units * cover * (1 + 1.64 * sp.demand_cv * np.sqrt(cover) / cover)
            pipeline = sum(q for lst in in_transit.values() for (s_, q, _) in lst if s_ == r.sku)
            gap = target - on_hand[r.sku] - pipeline
            if gap > 0:
                raw = gap / max(fill, 0.3)
                spec_ = pack_specs[r.sku]
                lots = int(np.ceil(raw / spec_.lot_units))
                qty = lots * spec_.lot_units
                if spec_.moq_units and qty < spec_.moq_units:
                    qty = spec_.moq_units
                po_seq += 1
                po_id = f"PO-{po_seq:06d}"
                lt = max(1, int(round(rng.lognormal(np.log(lead), srow["lead_cv"]))))
                delivered = qty * float(np.clip(rng.normal(fill, 0.04), 0.0, 1.0))
                pos.append({"po_id": po_id, "po_date": wk, "sku": r.sku,
                            "supplier_id": r.supplier_id, "qty_ordered": qty,
                            "lots": lots, "unit_cost": r.unit_cost,
                            "expected_lead_weeks": round(lead, 2)})
                in_transit.setdefault(w + lt, []).append((r.sku, delivered, po_id))
            snaps.append({"week_start": wk, "sku": r.sku, "on_hand": round(on_hand[r.sku], 0),
                          "in_transit": round(pipeline, 0)})
        for c in customers.itertuples():
            orders.append({"order_id": f"ORD-{w:04d}-{c.customer_id[-3:]}",
                           "customer_id": c.customer_id, "order_date": wk,
                           "requested_delivery_date": wk + timedelta(days=int(rng.integers(1, 5)))})

    receipts_df = pd.DataFrame(receipts)
    pos_df = pd.DataFrame(pos)
    return FMCGHistory(
        archetype=sp.name, seed=seed, skus=skus, suppliers=suppliers,
        customers=customers, customer_orders=pd.DataFrame(orders),
        order_lines=pd.DataFrame(lines), purchase_orders=pos_df,
        receipts=receipts_df, inventory_snapshots=pd.DataFrame(snaps),
        stockouts=pd.DataFrame(stockouts), promotions=pd.DataFrame(promos),
        pack_specs=pack_specs)


def closing_inventory_rows(snapshots: pd.DataFrame) -> pd.DataFrame:
    """The simulator's weekly stock rows as truthful `stg_fmcg_inventory` rows (HARDENING V1, H2).

    `build_history` appends each SKU's `on_hand` AFTER the week's arrivals, fulfilment and replenishment
    decision and labels the row with the week start. The state it holds is therefore the one that closes
    the week: `snapshot_date` = week start + 6 days (the Sunday), `snapshot_basis` = END_OF_DAY, and
    `snapshot_at` = the next Monday 00:00 (the instant the next decision opens on). SYNTHETIC: this is a
    property of the simulator and is declared here so no loader has to guess it."""
    rows = snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]].copy()
    rows["snapshot_date"] = pd.to_datetime(rows["snapshot_date"]) + pd.Timedelta(days=6)
    rows["snapshot_basis"] = "END_OF_DAY"
    rows["snapshot_at"] = rows["snapshot_date"] + pd.Timedelta(days=1)
    return rows


def coherence_report(h: FMCGHistory) -> dict:
    """Cross-table identities a real ERP would satisfy. Used by tests."""
    rec = h.receipts.groupby("po_id")["qty_received"].sum() if len(h.receipts) else pd.Series(dtype=float)
    pos = h.purchase_orders.set_index("po_id")["qty_ordered"]
    joined = pos.to_frame("ordered").join(rec.to_frame("received"), how="left").fillna({"received": 0.0})
    over = joined[joined["received"] > joined["ordered"] + 1e-6]
    fill = float(joined["received"].sum() / joined["ordered"].sum()) if joined["ordered"].sum() else 1.0
    ol = h.order_lines
    unit_fill = float(ol["qty_shipped"].sum() / ol["qty_ordered"].sum()) if len(ol) else 1.0
    return {
        "receipts_never_exceed_po": int(len(over)) == 0,
        "realised_supplier_fill": round(fill, 4),
        "unit_fill_rate": round(unit_fill, 4),
        "stockout_weeks": int(len(h.stockouts)),
        "orders_shipped_le_ordered": bool((ol["qty_shipped"] <= ol["qty_ordered"] + 1e-9).all()),
        "no_negative_stock": bool((h.inventory_snapshots["on_hand"] >= -1e-6).all()),
        "po_lots_whole": bool((h.purchase_orders["lots"] == h.purchase_orders["lots"].round()).all()),
    }
