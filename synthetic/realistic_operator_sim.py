"""Realistic mid-size produce operator simulation.

Generates ~26 weeks of operations for a regional food hub / distributor at a
realistic scale, grounded in published benchmarks, then runs the live
HarvestMind engine on it and prints a business-owner readout.

IMPORTANT — this is a MODELED simulation, not a real operator's books. The
numbers are computed correctly by the real engine, but the inputs are
synthetic, calibrated to industry benchmarks:

  - Produce shrink/waste at distributor level: ~6-8% of throughput (USDA ERS
    loss-adjusted food availability; Wallace Center hub studies)
  - Fill rate for spreadsheet-run hubs: ~86-90% (vs 96-98% with full ERP/WMS)
  - Gross margin: ~18%
  - Category-level shelf life, cost, and sell prices from typical wholesale ranges

The point is to show value AT REAL SCALE. Validate against a real operator
before quoting any of these figures externally.

Run:  python3 synthetic/realistic_operator_sim.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SEED = 42
WEEKS = 26
AS_OF = date(2026, 5, 31)           # end of the data window
START = AS_OF - timedelta(weeks=WEEKS)
PERIOD_DAYS = WEEKS * 7
ANNUALIZE = 365.0 / PERIOD_DAYS

# Target scale
TARGET_ANNUAL_REVENUE = 8_000_000.0  # $8M/yr regional hub

# (name, category, shelf_life_days, cost_per_kg, sell_per_kg)
PRODUCTS = [
    ("Romaine Lettuce", "Leafy Greens", 6, 2.10, 3.40),
    ("Spinach", "Leafy Greens", 5, 2.60, 4.20),
    ("Kale", "Leafy Greens", 7, 2.20, 3.60),
    ("Mixed Greens", "Leafy Greens", 5, 3.00, 4.80),
    ("Arugula", "Leafy Greens", 5, 3.40, 5.40),
    ("Tomatoes", "Vine", 9, 1.40, 2.60),
    ("Cucumbers", "Vine", 11, 0.95, 1.90),
    ("Bell Peppers", "Vine", 12, 1.70, 3.10),
    ("Zucchini", "Vine", 8, 1.10, 2.10),
    ("Strawberries", "Berries", 4, 5.20, 9.00),
    ("Blueberries", "Berries", 6, 6.40, 11.50),
    ("Raspberries", "Berries", 3, 8.00, 14.00),
    ("Carrots", "Root Vegetables", 45, 0.70, 1.40),
    ("Potatoes", "Root Vegetables", 90, 0.55, 1.10),
    ("Onions", "Root Vegetables", 60, 0.65, 1.30),
    ("Beets", "Root Vegetables", 40, 0.90, 1.80),
    ("Broccoli", "Brassica", 12, 1.50, 2.80),
    ("Cauliflower", "Brassica", 14, 1.60, 3.00),
    ("Cabbage", "Brassica", 25, 0.70, 1.50),
    ("Brussels Sprouts", "Brassica", 18, 2.10, 3.80),
    ("Basil", "Herbs", 5, 7.00, 13.00),
    ("Cilantro", "Herbs", 6, 6.00, 11.00),
    ("Parsley", "Herbs", 7, 5.50, 10.00),
    ("Sweet Corn", "Vine", 6, 1.20, 2.40),
    ("Green Beans", "Vine", 8, 1.80, 3.30),
    ("Apples", "Fruit", 60, 1.30, 2.50),
    ("Mushrooms", "Vegetables", 7, 3.20, 5.80),
    ("Asparagus", "Vegetables", 5, 4.50, 8.00),
]

CATEGORY_WASTE_WEIGHT = {  # relative propensity to spoil
    "Berries": 3.0, "Herbs": 2.6, "Leafy Greens": 2.2, "Vegetables": 1.8,
    "Vine": 1.2, "Brassica": 0.9, "Fruit": 0.6, "Root Vegetables": 0.3,
}


def build_dataset(conn: duckdb.DuckDBPyConnection) -> None:
    rng = np.random.default_rng(SEED)

    # ── Products ───────────────────────────────────────────────────────────
    prod_rows, prod_meta = [], {}
    for i, (name, cat, shelf, cost, sell) in enumerate(PRODUCTS):
        pid = f"P{i+1:03d}"
        prod_meta[name] = dict(pid=pid, cat=cat, shelf=shelf, cost=cost, sell=sell)
        prod_rows.append((pid, name, cat, "kg", shelf, cat in ("Leafy Greens", "Berries", "Herbs")))
    conn.executemany(
        "INSERT INTO stg_products (product_id, product_name, category, unit, default_shelf_life_days, traceability_required) VALUES (?,?,?,?,?,?)",
        prod_rows)

    # ── Suppliers with realistic true fill-rate distribution ───────────────
    n_suppliers = 25
    sup = []
    for s in range(n_suppliers):
        if s < 17:      # reliable majority
            true_fill = rng.uniform(0.92, 0.985)
        elif s < 22:    # mediocre
            true_fill = rng.uniform(0.82, 0.90)
        else:           # problematic few
            true_fill = rng.uniform(0.62, 0.80)
        # volatility: some reliable-mean suppliers are swingy
        vol = rng.uniform(0.02, 0.06) if s < 20 else rng.uniform(0.10, 0.20)
        sup.append(dict(sid=f"S{s+1:03d}", name=f"Supplier {s+1:02d}",
                        fill=true_fill, vol=vol))
    # assign each product to 1-3 suppliers
    prod_names = [p[0] for p in PRODUCTS]
    prod_suppliers = {n: list(rng.choice(n_suppliers, size=rng.integers(1, 4), replace=False)) for n in prod_names}

    # ── Demand profile per product (weekly kg), calibrated later ───────────
    base_weekly = {n: rng.uniform(150, 1200) for n in prod_names}

    # ── Buyer orders (drives revenue + shortage) ───────────────────────────
    buyers = [(f"B{b+1:03d}", nm) for b, nm in enumerate([
        "Indianapolis Public Schools", "Eskenazi Health", "Purdue Dining",
        "Riley Children's Hospital", "Bloomington Schools", "IU Health",
        "Sodexo Midwest", "Fort Wayne Schools", "Parkview Health",
        "Ivy Tech Dining", "Community Hospital", "Lafayette Schools",
        "St. Vincent Foodservice", "Notre Dame Dining", "Goshen Schools"])]

    # Per-buyer priority: a few key accounts get filled first (near-full),
    # others absorb more of the shortfall. Concentrates buyer risk realistically.
    buyer_priority = {}
    for i, (bid, _) in enumerate(buyers):
        if i < 9:       # priority accounts
            buyer_priority[bid] = rng.uniform(1.05, 1.15)
        elif i < 12:    # standard
            buyer_priority[bid] = rng.uniform(0.95, 1.02)
        else:           # routinely shorted
            buyer_priority[bid] = rng.uniform(0.78, 0.90)

    order_rows = []
    oid = 0
    # weekly system supply adequacy (creates correlated shortage periods)
    weekly_adequacy = np.clip(rng.normal(0.93, 0.05, WEEKS), 0.78, 1.0)
    for w in range(WEEKS):
        d = START + timedelta(weeks=w)
        adequacy = weekly_adequacy[w]
        for bid, bname in buyers:
            n_items = rng.integers(10, 20)
            chosen = rng.choice(prod_names, size=n_items, replace=False)
            for pname in chosen:
                meta = prod_meta[pname]
                requested = max(1.0, base_weekly[pname] / len(buyers) * rng.uniform(0.5, 1.6))
                # fulfillment depends on supply adequacy, product's worst supplier,
                # and the buyer's priority with the operator
                worst = min(sup[i]["fill"] for i in prod_suppliers[pname])
                fulfill_rate = np.clip(
                    adequacy * (0.6 + 0.4 * worst) * buyer_priority[bid] + rng.normal(0, 0.04),
                    0.4, 1.0)
                fulfilled = round(requested * fulfill_rate, 1)
                substituted = round(max(0.0, (requested - fulfilled) * rng.uniform(0, 0.3)), 1)
                oid += 1
                order_rows.append((f"O{oid:05d}", bid, bname, meta["pid"], pname,
                                   d.isoformat(), (d + timedelta(days=3)).isoformat(),
                                   round(requested, 1), fulfilled, substituted,
                                   meta["sell"], "A"))

    orders_df = pd.DataFrame(order_rows, columns=[
        "order_id", "buyer_id", "buyer_name", "product_id", "product_name",
        "order_date", "delivery_date", "requested_quantity", "fulfilled_quantity",
        "substituted_quantity", "sales_price", "required_quality_grade"])

    # calibrate to target revenue
    realized_rev_period = float((orders_df["fulfilled_quantity"] * orders_df["sales_price"]).sum())
    scale = (TARGET_ANNUAL_REVENUE / ANNUALIZE) / realized_rev_period
    for c in ["requested_quantity", "fulfilled_quantity", "substituted_quantity"]:
        orders_df[c] = (orders_df[c] * scale).round(1)
    conn.register("orders_df", orders_df)
    cols = ",".join(orders_df.columns)
    conn.execute(f"INSERT INTO stg_buyer_orders ({cols}) SELECT {cols} FROM orders_df")

    # ── Supplier deliveries (weekly per supplier-product) ──────────────────
    deliv_rows = []
    did = 0
    for w in range(WEEKS):
        d = START + timedelta(weeks=w)
        for pname in prod_names:
            meta = prod_meta[pname]
            weekly_need = base_weekly[pname] * scale
            for si in prod_suppliers[pname]:
                s = sup[si]
                ordered = round(weekly_need / len(prod_suppliers[pname]) * rng.uniform(0.8, 1.2), 1)
                realized_fill = float(np.clip(rng.normal(s["fill"], s["vol"]), 0.0, 1.0))
                delivered = round(ordered * realized_fill, 1)
                accepted = round(delivered * rng.uniform(0.96, 1.0), 1)  # small reject for quality
                rejected = round(delivered - accepted, 1)
                did += 1
                deliv_rows.append((f"D{did:05d}", s["sid"], s["name"], meta["pid"], pname,
                                   d.isoformat(), ordered, delivered, accepted, rejected,
                                   round(meta["cost"] * rng.uniform(0.95, 1.08), 3), "A",
                                   f"LOT-{did:05d}"))
    deliv_df = pd.DataFrame(deliv_rows, columns=[
        "delivery_id", "supplier_id", "supplier_name", "product_id", "product_name",
        "delivery_date", "ordered_quantity", "delivered_quantity", "accepted_quantity",
        "rejected_quantity", "unit_cost", "quality_grade", "lot_id"])
    conn.register("deliv_df", deliv_df)
    cols = ",".join(deliv_df.columns)
    conn.execute(f"INSERT INTO stg_supplier_deliveries ({cols}) SELECT {cols} FROM deliv_df")

    # ── Inventory lots (current snapshot at AS_OF) ─────────────────────────
    lot_rows = []
    lid = 0
    for pname in prod_names:
        meta = prod_meta[pname]
        on_hand_total = base_weekly[pname] * scale * rng.uniform(0.5, 1.2)
        n_lots = int(rng.integers(2, 5))
        for _ in range(n_lots):
            lid += 1
            qty = round(on_hand_total / n_lots, 1)
            # expiry spread: most fresh, ~12% near-expiry, ~4% expired
            r = rng.random()
            if r < 0.04:        # expired
                exp = AS_OF - timedelta(days=int(rng.integers(1, 4)))
            elif r < 0.16:      # near-expiry
                exp = AS_OF + timedelta(days=int(rng.integers(0, 4)))
            else:
                exp = AS_OF + timedelta(days=int(rng.integers(5, meta["shelf"] + 5)))
            si = prod_suppliers[pname][0]
            committed = round(qty * rng.uniform(0.0, 0.4), 1)
            # occasionally drop lot_id / supplier to model traceability gaps (~8%)
            lot_id = None if rng.random() < 0.05 else f"INV-{lid:05d}"
            supid = None if rng.random() < 0.05 else sup[si]["sid"]
            lot_rows.append((lot_id, meta["pid"], pname, supid, qty, "kg",
                             (AS_OF - timedelta(days=int(rng.integers(1, 10)))).isoformat(),
                             exp.isoformat(), "DC-1", "A", committed))
    lots_df = pd.DataFrame(lot_rows, columns=[
        "lot_id", "product_id", "product_name", "supplier_id", "quantity_on_hand",
        "unit", "arrival_date", "expiration_date", "warehouse_location",
        "quality_grade", "committed_quantity"])
    conn.register("lots_df", lots_df)
    cols = ",".join(lots_df.columns)
    conn.execute(f"INSERT INTO stg_inventory_lots ({cols}) SELECT {cols} FROM lots_df")

    # ── Waste adjustments (calibrated to ~7% of throughput by cost) ────────
    total_cogs_period = float((deliv_df["accepted_quantity"] * deliv_df["unit_cost"]).sum())
    target_waste_usd = 0.07 * total_cogs_period
    waste_rows = []
    aid = 0
    weights = np.array([CATEGORY_WASTE_WEIGHT[prod_meta[n]["cat"]] for n in prod_names], float)
    weights /= weights.sum()
    accumulated = 0.0
    reasons = ["Spoilage", "Overripe", "Temperature abuse", "Wilting", "Mold", "Bruising", "Expired"]
    while accumulated < target_waste_usd:
        pname = rng.choice(prod_names, p=weights)
        meta = prod_meta[pname]
        qty = round(float(rng.uniform(5, 80)), 1)
        val = round(qty * meta["cost"], 2)
        aid += 1
        d = START + timedelta(days=int(rng.integers(0, PERIOD_DAYS)))
        # ~15% of rows leave estimated_value_lost null (exercise cost fallback)
        est = None if rng.random() < 0.15 else val
        waste_rows.append((f"A{aid:05d}", d.isoformat(), meta["pid"], pname,
                           None, qty, rng.choice(reasons), est))
        accumulated += val
    waste_df = pd.DataFrame(waste_rows, columns=[
        "adjustment_id", "date", "product_id", "product_name", "lot_id",
        "quantity_lost", "reason", "estimated_value_lost"])
    conn.register("waste_df", waste_df)
    cols = ",".join(waste_df.columns)
    conn.execute(f"INSERT INTO stg_waste_adjustments ({cols}) SELECT {cols} FROM waste_df")


def main() -> None:
    from dashboard.lib.diagnostic_metrics import (
        waste_loss_usd, shortage_loss_usd, supplier_reliability_scores,
        buyer_fulfillment_rates, traceability_coverage, atp_by_product,
    )
    from backtesting.policy_comparison import compare_policies

    conn = duckdb.connect(":memory:")
    mig = (ROOT / "db" / "migrations" / "010_diagnostic_staging.sql").read_text()
    for stmt in mig.split(";"):
        if stmt.strip():
            try:
                conn.execute(stmt)
            except Exception:
                pass
    build_dataset(conn)

    # Scale / scope
    rev = float(conn.execute(
        "SELECT SUM(fulfilled_quantity*sales_price) FROM stg_buyer_orders").fetchone()[0])
    cogs = float(conn.execute(
        "SELECT SUM(accepted_quantity*unit_cost) FROM stg_supplier_deliveries").fetchone()[0])
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
              ["stg_products", "stg_supplier_deliveries", "stg_inventory_lots",
               "stg_buyer_orders", "stg_waste_adjustments"]}

    waste = waste_loss_usd(conn, days=400)
    short = shortage_loss_usd(conn, days=400)
    sup = supplier_reliability_scores(conn)
    buy = buyer_fulfillment_rates(conn)
    trace = traceability_coverage(conn)
    atp = atp_by_product(conn, as_of_date=AS_OF)
    bt = compare_policies(conn, as_of_date=AS_OF, lead_time_days=3)

    MARGIN = 0.18
    waste_yr = waste["total_usd"] * ANNUALIZE          # cash lost (cost basis)
    short_rev_yr = short["total_usd"] * ANNUALIZE       # missed-order REVENUE at risk
    short_margin_yr = short_rev_yr * MARGIN             # profit actually lost on misses
    rev_yr = rev * ANNUALIZE
    fill = sum(b['fulfillment_rate'] for b in buy['buyers']) / len(buy['buyers'])

    # Economic loss = cash waste + lost margin on missed orders (NOT full revenue)
    economic_loss_yr = waste_yr + short_margin_yr
    rec_low = economic_loss_yr * 0.15
    rec_high = economic_loss_yr * 0.30

    def m(x): return f"${x:,.0f}"

    print("=" * 72)
    print("  HARVESTMIND — SIMULATED VALUE READOUT  (MODELED, not validated)")
    print("=" * 72)
    print(f"  Operator: regional produce hub, ~{m(rev_yr)}/yr revenue (simulated)")
    print(f"  Scope: {counts['stg_products']} products, "
          f"{conn.execute('SELECT COUNT(DISTINCT supplier_id) FROM stg_supplier_deliveries').fetchone()[0]} suppliers, "
          f"{counts['stg_buyer_orders']:,} order lines over {PERIOD_DAYS} days (annualized x{ANNUALIZE:.2f})")
    print()
    print("  WHAT IT'S COSTING YOU (annualized)")
    print("  " + "-" * 64)
    print(f"  Spoilage / waste  ....... {m(waste_yr)}/yr   real cash, {waste_yr/(cogs*ANNUALIZE)*100:.1f}% of cost of goods")
    print(f"  Missed orders  .......... {m(short_rev_yr)}/yr   revenue at risk (fill rate {fill*100:.0f}%)")
    print(f"     -> lost profit on those misses, at {MARGIN*100:.0f}% margin:  ~{m(short_margin_yr)}/yr")
    print("  ---------------------------------------------------------------")
    print(f"  Economic loss (cash waste + lost margin):  ~{m(economic_loss_yr)}/yr")
    print()
    print("  WHERE IT'S CONCENTRATED (what you'd act on)")
    print("  " + "-" * 64)
    print(f"  {sup['n_risky']} of {len(sup['suppliers'])} suppliers under 80% fill rate")
    print(f"  {buy['n_risky']} of {len(buy['buyers'])} buyers under 90% fulfillment")
    print(f"  {atp['n_risky']} of {len(atp['products'])} products with near-expiry / availability risk")
    print(f"  FSMA-204 traceability {trace['completeness_pct']*100:.1f}% complete "
          f"({trace['total_lots']-trace['complete_lots']} lots with record gaps)")
    print()
    print("  WHAT YOU COULD RECOVER  (15-30% of economic loss, USDA SR-77 band)")
    print("  " + "-" * 64)
    print(f"  Conservative (15%):  {m(rec_low)}/yr")
    print(f"  Upper (30%):         {m(rec_high)}/yr")
    print()
    print("  RETURN ON THE SOFTWARE")
    print("  " + "-" * 64)
    print(f"  vs a $7,500 one-time diagnostic:  {rec_low/7500:.0f}x - {rec_high/7500:.0f}x")
    print(f"  vs $24,000/yr ongoing software:   {rec_low/24000:.1f}x - {rec_high/24000:.1f}x")
    print("=" * 72)
    print("  HONESTY NOTES")
    print("  - SYNTHETIC data calibrated to benchmarks (7% shrink USDA ERS, ~88%")
    print("    hub fill rate, 18% margin). NOT a real operator's books.")
    print("  - 'Missed orders' is revenue at risk; the recoverable figure counts")
    print("    only the lost MARGIN on it, not full revenue.")
    print(f"  - The engine's own backtest of the model upgrade attributes only "
          f"{m(bt['total_estimated_avoided_usd']*ANNUALIZE)}/yr")
    print("    here, because in synthetic data the losses are not causally tied to")
    print("    the commitment decisions. On a REAL operator's history that figure")
    print("    becomes meaningful. Validate before quoting any of this externally.")
    print("=" * 72)


if __name__ == "__main__":
    main()
