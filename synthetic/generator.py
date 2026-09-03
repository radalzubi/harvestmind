"""Synthetic dataset generator for HarvestMind.

Produces ~2 years of weekly data (104 weeks) for the Indiana pilot market:
- Demand orders (fact_orders + fact_order_lines)
- Supplier purchase orders (fact_purchase_orders)
- Deliveries with rejection rates (fact_deliveries)
- Yield observations (fact_yield_obs)
- Weather observations (fact_weather_obs)
- Market spot prices (fact_market_prices)
- Waste events (fact_waste_events)
- FSMA-204 lots and CTE events (fact_lots, fact_cte_events)

All data written directly to DuckDB via the db layer.
"""

from __future__ import annotations

import hashlib
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

from synthetic.archetypes import (
    BUYER_ARCHETYPES,
    PRODUCT_ARCHETYPES,
    SUPPLIER_PRODUCT_MAP,
    SUPPLIER_RELIABILITY,
)
from synthetic.seasonality import enso_yield_adjustment, seasonal_index

_RNG_SEED = int(os.getenv("SYNTHETIC_SEED", "42"))


def _sid(prefix: str, *parts: str) -> str:
    """Deterministic stable ID from a prefix + content hash."""
    h = hashlib.md5("|".join(parts).encode(), usedforsecurity=False).hexdigest()[:12]
    return f"{prefix}-{h}"


def _iso_week_start(d: date) -> date:
    """Return Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _enso_sequence(n_weeks: int, rng: np.random.Generator) -> list[str]:
    """Pseudo-realistic ENSO phase sequence: each phase lasts 26-78 weeks."""
    phases = []
    phase_pool = ["neutral", "el_nino", "la_nina"]
    weights = [0.50, 0.25, 0.25]
    while len(phases) < n_weeks:
        phase = rng.choice(phase_pool, p=weights)
        duration = int(rng.integers(26, 79))
        phases.extend([phase] * duration)
    return phases[:n_weeks]


class SyntheticGenerator:
    def __init__(
        self,
        start_date: date | None = None,
        n_weeks: int = 104,
        seed: int = _RNG_SEED,
        end_near_today: bool = True,
    ) -> None:
        if start_date is None and end_near_today:
            # Anchor end of dataset close to today so "last N days" queries hit data
            today_monday = _iso_week_start(date.today())
            start_date = today_monday - timedelta(weeks=n_weeks - 1)
        self.start = _iso_week_start(start_date or date(2023, 6, 5))
        self.n_weeks = n_weeks
        self.rng = np.random.default_rng(seed)
        self.weeks: list[date] = [
            self.start + timedelta(weeks=w) for w in range(n_weeks)
        ]
        self.enso = _enso_sequence(n_weeks, self.rng)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate_all(self, conn) -> dict[str, int]:
        """Generate all tables and insert into DuckDB connection. Returns row counts."""
        counts: dict[str, int] = {}

        orders_df, lines_df = self._build_orders()
        counts["fact_orders"] = self._insert(conn, "fact_orders", orders_df)
        counts["fact_order_lines"] = self._insert(conn, "fact_order_lines", lines_df)

        po_df = self._build_purchase_orders(lines_df)
        counts["fact_purchase_orders"] = self._insert(conn, "fact_purchase_orders", po_df)

        deliveries_df = self._build_deliveries(po_df)
        counts["fact_deliveries"] = self._insert(conn, "fact_deliveries", deliveries_df)

        yield_df = self._build_yield_obs()
        counts["fact_yield_obs"] = self._insert(conn, "fact_yield_obs", yield_df)

        weather_df = self._build_weather()
        counts["fact_weather_obs"] = self._insert(conn, "fact_weather_obs", weather_df)

        price_df = self._build_market_prices()
        counts["fact_market_prices"] = self._insert(conn, "fact_market_prices", price_df)

        waste_df = self._build_waste_events(deliveries_df)
        counts["fact_waste_events"] = self._insert(conn, "fact_waste_events", waste_df)

        lots_df, cte_df = self._build_fsma(deliveries_df)
        counts["fact_lots"] = self._insert(conn, "fact_lots", lots_df)
        counts["fact_cte_events"] = self._insert(conn, "fact_cte_events", cte_df)

        return counts

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def _build_orders(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        orders, lines = [], []
        for week in self.weeks:
            iso_week = week.isocalendar()[1]
            # NOTE: ENSO modulation could feed demand here too; today only
            # yields are ENSO-adjusted (see _build_yield_obs / seasonality.py).

            for buyer_id, b in BUYER_ARCHETYPES.items():
                # Determine if buyer orders this week
                if self.rng.random() > b.order_frequency:
                    continue

                order_id = _sid("ORD", buyer_id, str(week))
                orders.append({
                    "order_id": order_id,
                    "buyer_id": buyer_id,
                    "order_date": week,
                    "week_start": week,
                    "status": "confirmed",
                    "notes": None,
                })

                for prod_id in b.preferred_product_ids:
                    arch = PRODUCT_ARCHETYPES[prod_id]
                    si = seasonal_index(arch.seasonality, iso_week)
                    mean_kg = arch.base_demand_kg * b.volume_multiplier * si
                    std_kg = mean_kg * arch.cv

                    # Intermittent demand: zero-inflation
                    if arch.intermittent and self.rng.random() > 0.55:
                        continue

                    qty = max(0.0, float(self.rng.normal(mean_kg, std_kg)))
                    qty = round(qty / 5) * 5  # round to 5 kg

                    if qty <= 0:
                        continue

                    # Determine if fulfilled (lost sale if not)
                    fulfilled = self.rng.random() < b.reliability
                    qty_del = round(qty * self.rng.uniform(0.9, 1.0) / 5) * 5 if fulfilled else 0.0

                    lines.append({
                        "line_id": _sid("LIN", order_id, prod_id),
                        "order_id": order_id,
                        "product_id": prod_id,
                        "qty_ordered_kg": qty,
                        "qty_delivered_kg": qty_del if fulfilled else None,
                        "price_per_kg": round(arch.price_per_kg * self.rng.uniform(0.95, 1.05), 4),
                        "grade": "A",
                        "lost_sale_flag": not fulfilled,
                        "lost_sale_reason": "stockout" if not fulfilled else None,
                        "delivery_date": week + timedelta(days=2),
                    })

        return pd.DataFrame(orders), pd.DataFrame(lines)

    # ------------------------------------------------------------------
    # Purchase orders
    # ------------------------------------------------------------------

    def _build_purchase_orders(self, lines_df: pd.DataFrame) -> pd.DataFrame:
        if lines_df.empty:
            return pd.DataFrame()

        # Derive week_start from delivery_date (delivery is order week + 2 days → back to Monday)
        tmp = lines_df.copy()
        delivery_dates = pd.to_datetime(tmp["delivery_date"])
        tmp["week_start"] = delivery_dates - pd.to_timedelta(
            delivery_dates.dt.weekday + 2, unit="D"
        )

        # Aggregate demand by week × product
        agg = (
            tmp.groupby(["week_start", "product_id"])["qty_ordered_kg"]
            .sum()
            .reset_index()
        )

        rows = []
        for _, row in agg.iterrows():
            prod_id = row["product_id"]
            week = row["week_start"]
            total_demand = row["qty_ordered_kg"]

            # Find eligible suppliers for this product
            eligible = [s for s, prods in SUPPLIER_PRODUCT_MAP.items() if prod_id in prods]
            if not eligible:
                continue

            # Split demand across suppliers proportionally (with noise)
            weights = self.rng.dirichlet(np.ones(len(eligible)) * 3)
            for sup_id, w in zip(eligible, weights):
                qty = round(total_demand * w * self.rng.uniform(1.05, 1.20) / 5) * 5
                if qty <= 0:
                    continue

                arch = PRODUCT_ARCHETYPES[prod_id]
                is_spot = self.rng.random() < 0.08
                contract_price = arch.price_per_kg * self.rng.uniform(0.90, 0.98)
                spot_prem = arch.spot_premium_pct / 100 if is_spot else 0.0
                price = contract_price * (1 + spot_prem)

                rows.append({
                    "po_id": _sid("PO", sup_id, prod_id, str(week)),
                    "supplier_id": sup_id,
                    "product_id": prod_id,
                    "po_date": week - timedelta(days=7),
                    "week_start": week,
                    "qty_committed_kg": float(qty),
                    "qty_received_kg": None,
                    "price_per_kg": round(price, 4),
                    "is_spot_purchase": is_spot,
                    "spot_premium_pct": round(spot_prem * 100, 2) if is_spot else None,
                    "contract_id": None,
                    "delivery_window_start": week,
                    "delivery_window_end": week + timedelta(days=4),
                    "grade_spec": "A",
                    "status": "open",
                    "notes": "spot buy — emergency" if is_spot else None,
                })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Deliveries
    # ------------------------------------------------------------------

    def _build_deliveries(self, po_df: pd.DataFrame) -> pd.DataFrame:
        if po_df.empty:
            return pd.DataFrame()

        rows = []
        for _, po in po_df.iterrows():
            rel = SUPPLIER_RELIABILITY.get(po["supplier_id"], 0.90)
            # Actual quantity: slight over/under relative to commitment
            qty_recv = round(
                max(0.0, float(po["qty_committed_kg"]) * self.rng.uniform(rel - 0.12, 1.05)) / 5
            ) * 5
            rejection_rate = max(0.0, self.rng.normal(0.04, 0.03))
            qty_rej = round(qty_recv * rejection_rate / 5) * 5
            rejection_reason = (
                self.rng.choice(["quality", "over_ripe", "size", "contamination", "late"])
                if qty_rej > 0 else None
            )
            rows.append({
                "delivery_id": _sid("DEL", po["po_id"]),
                "po_id": po["po_id"],
                "supplier_id": po["supplier_id"],
                "product_id": po["product_id"],
                "delivery_date": po["delivery_window_start"],
                "qty_received_kg": float(qty_recv),
                "qty_rejected_kg": float(qty_rej),
                "rejection_reason": rejection_reason,
                "grade_received": "A",
                "lot_id": None,
                "temp_on_arrival_c": float(self.rng.normal(4.0, 1.2)),
                "transit_hrs": float(self.rng.uniform(0.5, 3.0)),
                "driver_id": None,
                "vehicle_id": None,
            })

        df = pd.DataFrame(rows)
        # Update POs with received qty (just for the dataframe; DB handles it separately)
        return df

    # ------------------------------------------------------------------
    # Yield observations
    # ------------------------------------------------------------------

    def _build_yield_obs(self) -> pd.DataFrame:
        rows = []
        for week_idx, week in enumerate(self.weeks):
            enso = self.enso[week_idx]
            iso_week = week.isocalendar()[1]

            for sup_id, prod_ids in SUPPLIER_PRODUCT_MAP.items():
                for prod_id in prod_ids:
                    arch = PRODUCT_ARCHETYPES[prod_id]
                    si = seasonal_index(arch.seasonality, iso_week)
                    if si < 0.3:  # out-of-season: no harvest
                        continue

                    # Determine crop category for ENSO adjustment
                    cat = "other"
                    if "leafy" in arch.crop_name.lower() or "spinach" in arch.crop_name.lower() or "kale" in arch.crop_name.lower():
                        cat = "leafy_green"
                    elif "tomato" in arch.crop_name.lower():
                        cat = "tomato"
                    elif "pepper" in arch.crop_name.lower():
                        cat = "pepper"
                    elif "squash" in arch.crop_name.lower() or "zucchini" in arch.crop_name.lower():
                        cat = "squash"
                    elif "berry" in arch.crop_name.lower() or "strawberry" in arch.crop_name.lower():
                        cat = "berry"
                    elif "onion" in arch.crop_name.lower():
                        cat = "allium"

                    enso_adj = enso_yield_adjustment(enso, cat)
                    base_yield_kgha = 8000.0 * si * enso_adj
                    realized = max(0.0, float(self.rng.normal(base_yield_kgha, base_yield_kgha * arch.yield_cv)))
                    planned_ha = self.rng.uniform(3.0, 15.0)

                    rows.append({
                        "yield_id": _sid("YLD", sup_id, prod_id, str(week)),
                        "supplier_id": sup_id,
                        "product_id": prod_id,
                        "harvest_week": week,
                        "planned_ha": round(planned_ha, 2),
                        "realized_yield_kg_per_ha": round(realized, 1),
                        "total_kg_harvested": round(realized * planned_ha, 0),
                        "grade_a_pct": round(self.rng.uniform(72.0, 94.0), 1),
                        "reject_pct": round(self.rng.uniform(1.0, 8.0), 1),
                        "enso_phase": enso,
                        "drought_cat": self.rng.choice(["None","D0","D1","D2"], p=[0.55,0.25,0.15,0.05]),
                        "weather_note": None,
                    })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Weather (one row per week, central Indiana)
    # ------------------------------------------------------------------

    def _build_weather(self) -> pd.DataFrame:
        rows = []
        for week_idx, week in enumerate(self.weeks):
            enso = self.enso[week_idx]
            month = week.month
            # Seasonal temperature (°C)
            tbase = {1:-4,2:-2,3:5,4:12,5:18,6:24,7:27,8:26,9:20,10:13,11:5,12:-2}.get(month, 10)
            tmax = tbase + float(self.rng.normal(4.0, 3.0))
            tmin = tbase - float(self.rng.normal(5.0, 2.5))
            tavg = (tmax + tmin) / 2.0
            precip = max(0.0, float(self.rng.exponential(20.0)))
            rows.append({
                "obs_id": _sid("WX", str(week), "IN"),
                "obs_date": week,
                "location_id": "LOC-HUB-01",
                "county_fips": "18057",
                "station_id": "GHCND:USW00093819",
                "source": "synthetic",
                "tmax_c": round(tmax, 2),
                "tmin_c": round(tmin, 2),
                "tavg_c": round(tavg, 2),
                "precip_mm": round(precip, 1),
                "heat_stress_flag": tmax > 32.0,
                "drought_monitor_cat": self.rng.choice(["None","D0","D1"], p=[0.70,0.20,0.10]),
                "enso_oni_index": {"el_nino": 1.2, "la_nina": -1.1, "neutral": 0.1}.get(enso, 0.0),
                "gdd_base10": max(0.0, round(tavg - 10.0, 2)),
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Market prices (weekly USDA-AMS style)
    # ------------------------------------------------------------------

    def _build_market_prices(self) -> pd.DataFrame:
        rows = []
        for week in self.weeks:
            for prod_id, arch in PRODUCT_ARCHETYPES.items():
                low = arch.price_per_kg * self.rng.uniform(0.80, 0.95)
                high = arch.price_per_kg * self.rng.uniform(1.05, 1.30)
                avg = (low + high) / 2.0
                rows.append({
                    "price_id": _sid("PRC", prod_id, str(week)),
                    "source": "synthetic_ams",
                    "report_date": week,
                    "market_name": "Indianapolis Terminal Market",
                    "product_id": prod_id,
                    "commodity_code": None,
                    "grade": "A",
                    "unit": "kg",
                    "low_price": round(low, 4),
                    "high_price": round(high, 4),
                    "avg_price": round(avg, 4),
                    "volume_units": round(self.rng.uniform(500, 5000), 0),
                    "currency": "USD",
                })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Waste events
    # ------------------------------------------------------------------

    def _build_waste_events(self, deliveries_df: pd.DataFrame) -> pd.DataFrame:
        if deliveries_df.empty:
            return pd.DataFrame()
        rows = []
        for _, d in deliveries_df.iterrows():
            if self.rng.random() > 0.12:  # ~12% of deliveries generate a waste event
                continue
            qty_recv = float(d["qty_received_kg"]) - float(d.get("qty_rejected_kg", 0))
            waste_pct = self.rng.uniform(0.02, 0.15)
            qty_wasted = max(1.0, round(qty_recv * waste_pct / 5) * 5)
            arch = PRODUCT_ARCHETYPES.get(d["product_id"])
            unit_val = arch.price_per_kg if arch else 1.5
            rows.append({
                "waste_id": _sid("WST", d["delivery_id"]),
                "event_date": d["delivery_date"],
                "location_id": "LOC-HUB-01",
                "product_id": d["product_id"],
                "lot_id": None,
                "qty_wasted_kg": float(qty_wasted),
                "waste_stage": self.rng.choice(
                    ["pre_sale","quality","cold_chain","shrink"],
                    p=[0.30, 0.40, 0.20, 0.10],
                ),
                "reason_code": self.rng.choice(
                    ["shelf_life","quality_reject","cold_chain_failure","demand_miss"],
                    p=[0.35, 0.35, 0.15, 0.15],
                ),
                "estimated_value_usd": round(qty_wasted * unit_val, 2),
                "salvage_recovered": 0.0,
                "notes": None,
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # FSMA-204 lots and CTE events
    # ------------------------------------------------------------------

    def _build_fsma(self, deliveries_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        if deliveries_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        lots, ctes = [], []
        for _, d in deliveries_df.iterrows():
            prod_id = d["product_id"]
            arch = PRODUCT_ARCHETYPES.get(prod_id)
            if not arch:
                continue
            # Only FTL items need FSMA tracking (is_ftl_item flagged in seed data)
            ftl_products = {"PRD-001","PRD-002","PRD-003","PRD-007","PRD-009"}
            if prod_id not in ftl_products:
                continue

            tlc = f"TLC-{d['supplier_id']}-{prod_id}-{d['delivery_date'].strftime('%Y%m%d')}"
            lot_id = _sid("LOT", tlc)

            lots.append({
                "lot_id": lot_id,
                "traceability_lot_code": tlc,
                "tlc_source_reference": f"{d['supplier_id']} | GLN:0000000000000",
                "product_id": prod_id,
                "quantity_kg": float(d["qty_received_kg"]),
                "unit_of_measure": "kg",
                "harvest_date": d["delivery_date"] - timedelta(days=int(self.rng.integers(1, 5))),
                "pack_date": d["delivery_date"] - timedelta(days=1),
                "best_by_date": d["delivery_date"] + timedelta(days=arch.shelf_life_days - 2),
                "supplier_id": d["supplier_id"],
                "origin_location_id": f"LOC-FAR-0{list(SUPPLIER_PRODUCT_MAP.keys()).index(d['supplier_id']) + 1}",
                "gtin_14": None,
                "sscc": None,
                "parent_lot_id": None,
                "lot_status": "active",
            })

            delivery_ts = pd.Timestamp(d["delivery_date"])
            # Harvesting CTE
            ctes.append({
                "cte_id": _sid("CTE", "harvesting", lot_id),
                "lot_id": lot_id,
                "traceability_lot_code": tlc,
                "cte_type": "harvesting",
                "event_timestamp": delivery_ts - timedelta(days=3),
                "location_id": None,
                "location_description": f"Farm: {d['supplier_id']}",
                "business_name": d["supplier_id"],
                "point_of_contact": "Farm Manager",
                "phone_or_email": None,
                "quantity_kg": float(d["qty_received_kg"]),
                "referenced_tlc_codes": None,
                "new_tlc_code": None,
                "additional_kdes": None,
                "recorded_by": "synthetic",
            })
            # Receiving CTE at hub
            ctes.append({
                "cte_id": _sid("CTE", "receiving", lot_id),
                "lot_id": lot_id,
                "traceability_lot_code": tlc,
                "cte_type": "receiving",
                "event_timestamp": delivery_ts,
                "location_id": "LOC-HUB-01",
                "location_description": "Hoosier Harvest Hub, Greenfield IN",
                "business_name": "Hoosier Harvest Market",
                "point_of_contact": "Receiving Manager",
                "phone_or_email": None,
                "quantity_kg": float(d["qty_received_kg"]) - float(d.get("qty_rejected_kg", 0)),
                "referenced_tlc_codes": None,
                "new_tlc_code": None,
                "additional_kdes": None,
                "recorded_by": "synthetic",
            })

        return pd.DataFrame(lots), pd.DataFrame(ctes)

    # ------------------------------------------------------------------
    # DuckDB insert helper
    # ------------------------------------------------------------------

    @staticmethod
    def _insert(conn, table: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        cols = ", ".join(df.columns)
        placeholders = ", ".join(f"df.{c}" for c in df.columns)
        try:
            conn.execute(f"INSERT OR IGNORE INTO {table} ({cols}) SELECT {placeholders} FROM df")
        except Exception:
            # Fallback: use INSERT INTO with explicit column list (no OR IGNORE)
            conn.execute(f"INSERT INTO {table} ({cols}) SELECT {placeholders} FROM df")
        return len(df)
