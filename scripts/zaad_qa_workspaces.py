#!/usr/bin/env python3
"""Deterministic synthetic workspaces for product QA. **Never** loaded into a live workspace.

Two shapes the released fixtures do not produce, both needed to test the operating product:

  ``corridor``  a multi-corridor importer: three declared shipping paths (Jordan/Aqaba,
                Saudi/Jeddah with inland movement, Iraq/Umm Qasr with inland movement), several
                supplier origins, two inventory destinations, promised delivery dates so lateness
                is measurable, uneven supplier reliability, declared alternative sources, and
                declared amendment rights on a few open orders. Pass ``--operator`` so those
                rights are keyed to the operator whose vault the file becomes: `stg_po_commitments`
                and `stg_po_options` are filtered by `operator_id`, and a mismatch reads back empty
                with nothing but a build warning to show for it.

  ``scale``     a catalogue of N products (10,000 and 50,000 are the sizes this release is tested
                at) with stock, a year of customer orders and a purchase-order history, to measure
                what the product's tables and queries actually do at that size.

Everything is generated from a seed, so two runs produce the same vault. Rows are unmistakably
synthetic: product codes are ``QA-…``, suppliers ``QA-SUP-…``, customers ``QA-CUST-…``.

Usage::

    python3 scripts/zaad_qa_workspaces.py corridor --db /tmp/zaad_qa_corridor.duckdb
    python3 scripts/zaad_qa_workspaces.py scale --skus 10000 --db /tmp/zaad_qa_10k.duckdb

The generated file is a DuckDB database. Point a development API at it with ``DUCKDB_PATH`` and an
unauthenticated dev environment, or attach it to a development operator's vault. It has no place in
a deployed environment, and nothing in ``api/`` calls this module.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: (route tag, origin ISO3, entry port label, ocean days, inland days) — the declared paths a
#: Jordanian importer actually uses. The route tag is what `stg_fmcg_suppliers.route` carries and
#: what the Network Twin draws; ZAAD does not choose between them (route optimisation is not
#: released), so this exists to exercise the diagnostics, not a router.
CORRIDORS = [
    ("aqaba", "DEU", "Aqaba", 26, 1),
    ("aqaba", "CHN", "Aqaba", 34, 1),
    ("jeddah", "SAU", "Jeddah", 9, 4),
    ("road_saudi", "ARE", "Jeddah", 12, 4),
    ("umm_qasr", "IRQ", "Umm Qasr", 18, 6),
    ("iraq_overland", "TUR", "Umm Qasr", 14, 6),
]

LOCATIONS = [("QA-DC-AMMAN", "central_dc"), ("QA-BR-IRBID", "branch"), ("QA-BR-AQABA", "branch")]

CATEGORIES = ["Beverages", "Household", "Personal care", "Ambient food", "Paper"]
BRANDS = ["Northwind", "Marisol", "Kaveh", "Tamra", "Solis", "Baraka"]


def _connect(path: Path):
    import duckdb
    from scripts.setup_db import setup_db

    if path.exists():
        path.unlink()
    conn = duckdb.connect(str(path))
    setup_db(conn)
    return conn


def _weeks(start: date, count: int):
    return [start + timedelta(days=7 * i) for i in range(count)]


def build_corridor(conn, seed: int = 11, as_of: date | None = None, operator: str = "QA_OPERATOR") -> dict:
    """A multi-corridor importer. Small enough to plan, rich enough to exercise every surface."""
    rng = random.Random(seed)
    # The fixture ends today by default, so a QA workspace behaves like a live one: a proposal
    # dated now sits inside the planning horizon rather than months after the data ends.
    today = as_of or date.today()
    history_start = today - timedelta(days=364)

    suppliers = []
    for index, (route, origin, port, ocean, inland) in enumerate(CORRIDORS, start=1):
        supplier_id = f"QA-SUP-{index:02d}"
        # Reliability is deliberately uneven: one supplier per corridor is materially worse, so the
        # diagnostics have something true to find.
        troubled = index % 3 == 0
        suppliers.append({
            "id": supplier_id, "route": route, "origin": origin, "port": port,
            "promised_days": ocean + inland,
            "late_bias": 9 if troubled else 1,
            "late_share": 0.42 if troubled else 0.08,
            "fill": 0.88 if troubled else 0.985,
            "capacity": 9000 if troubled else 20000,
        })
        conn.execute(
            "INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name, origin_iso3, route, "
            "capacity_per_week, lead_time_promised_weeks, risk_group, risk_group_kind) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [supplier_id, f"{port} line {index}", origin, route, suppliers[-1]["capacity"],
             round((ocean + inland) / 7, 1),
             f"port_{port.lower().replace(' ', '_')}" if index % 2 else None,
             "PORT" if index % 2 else None])

    for location_id, kind in LOCATIONS:
        conn.execute("INSERT INTO stg_fmcg_locations (location_id, kind, holding_annual, capacity_units) "
                     "VALUES (?, ?, ?, ?)", [location_id, kind, 0.12 if kind == "central_dc" else 0.16,
                                             400_000 if kind == "central_dc" else 90_000])
    for origin, destination, lead, cost in (
            ("QA-DC-AMMAN", "QA-BR-IRBID", 2, 0.11), ("QA-DC-AMMAN", "QA-BR-AQABA", 4, 0.19)):
        conn.execute("INSERT INTO stg_fmcg_lanes (lane_id, origin_id, destination_id, lead_days, "
                     "cost_per_unit, capacity_per_week, approved) VALUES (?, ?, ?, ?, ?, ?, TRUE)",
                     [f"{origin}->{destination}", origin, destination, lead, cost, 30_000])

    products = []
    for index in range(1, 37):
        supplier = suppliers[index % len(suppliers)]
        pack = rng.choice([12, 24, 6, 48])
        cost = round(rng.uniform(0.8, 14.0), 2)
        sku = f"QA-{index:04d}"
        products.append({"sku": sku, "supplier": supplier, "pack": pack, "cost": cost,
                         "weekly": rng.randint(120, 2600)})
        conn.execute(
            "INSERT INTO stg_fmcg_skus (sku, sku_name, brand, category, sub_category, supplier_id, "
            "unit_cost, unit_price, units_per_case, moq_units, shelf_life_days, abc_class) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [sku, f"{rng.choice(BRANDS)} {rng.choice(['1L', '500ml', '2kg', '750g', '12s', '24s'])} {index}",
             rng.choice(BRANDS), CATEGORIES[index % len(CATEGORIES)],
             f"{CATEGORIES[index % len(CATEGORIES)]} — line {index % 3 + 1}",
             supplier["id"], cost, round(cost * rng.uniform(1.18, 1.55), 2), pack,
             pack * rng.choice([10, 20, 40]), rng.choice([180, 365, 540, 730]),
             "A" if index % 4 == 0 else "B" if index % 3 else "C"])

    # Sector physics on part of the catalogue (migration 017), so the produce and meat/seafood
    # diagnostics have declared data rather than an empty state. Declared, never inferred.
    for index, product in enumerate(products):
        if index % 4 == 0:
            sector = "PRODUCE" if index % 8 == 0 else "MEAT_SEAFOOD"
            conn.execute(
                "UPDATE stg_fmcg_skus SET sector = ?, storage_state = ?, age_at_receipt_days = ?, "
                "min_remaining_life_receipt_days = ?, min_remaining_life_sale_days = ?, "
                "physics_provenance = 'OPERATOR_DECLARED' WHERE sku = ?",
                [sector, "CHILLED" if sector == "PRODUCE" else "FROZEN",
                 rng.randint(2, 9), rng.randint(10, 30), rng.randint(3, 12), product["sku"]])
        elif index % 4 == 1:
            conn.execute("UPDATE stg_fmcg_skus SET sector = 'COMMERCIAL', storage_state = 'AMBIENT' WHERE sku = ?",
                         [product["sku"]])

    # A second approved source for a third of the catalogue, on a different corridor, so the
    # alternative-supplier workflow has real declared data rather than an empty state.
    for product in products[::3]:
        alternative = next(s for s in suppliers if s["route"] != product["supplier"]["route"])
        conn.execute(
            "INSERT INTO stg_fmcg_sources (sku, supplier_id, approved, compliance, unit_cost, "
            "freight_per_unit, capacity_per_week, lead_time_promised_weeks, moq_units, units_per_case, "
            "incumbent_share, switching_cost, provenance) "
            "VALUES (?, ?, TRUE, 'cleared', ?, ?, ?, ?, ?, ?, 0.0, ?, 'OPERATOR_DECLARED')",
            [product["sku"], alternative["id"], round(product["cost"] * 1.07, 2), 0.04,
             alternative["capacity"] / 4, round(alternative["promised_days"] / 7, 1),
             product["pack"] * 10, product["pack"], round(product["cost"] * 40, 2)])

    # Customer order history: one year, three customers, weekly, with a seasonal shape.
    customers = ["QA-CUST-RETAIL", "QA-CUST-WHOLESALE", "QA-CUST-HORECA"]
    order_rows = 0
    for product in products:
        for week_index, week in enumerate(_weeks(history_start, 52)):
            season = 1 + 0.25 * math.sin(week_index / 8.0)
            for customer in customers:
                share = {"QA-CUST-RETAIL": 0.55, "QA-CUST-WHOLESALE": 0.3, "QA-CUST-HORECA": 0.15}[customer]
                ordered = max(0, int(product["weekly"] * share * season * rng.uniform(0.7, 1.3)))
                if not ordered:
                    continue
                shipped = ordered if rng.random() > 0.06 else int(ordered * rng.uniform(0.5, 0.95))
                location = LOCATIONS[week_index % len(LOCATIONS)][0]
                conn.execute(
                    "INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, "
                    "requested_delivery_date, sku, qty_ordered, qty_shipped, channel, location_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [f"QA-SO-{week_index:03d}-{product['sku']}-{customer[-4:]}", customer, week,
                     week + timedelta(days=3), product["sku"], ordered, shipped, "wholesale", location])
                order_rows += 1

    # Purchase orders with promised dates, matched receipts, and a tail of open orders. The promised
    # date is what makes lateness measurable at all; the released sample fixture has none.
    po_rows = receipts = open_orders = 0
    for product in products:
        supplier = product["supplier"]
        # The full year, fortnightly, so the most recent orders are still in flight and the
        # product has genuinely open orders to change rather than a closed archive.
        for index, week in enumerate(_weeks(history_start, 53)):
            if index % 2:
                continue
            po_id = f"QA-PO-{product['sku']}-{index:02d}"
            quantity = product["pack"] * rng.randint(20, 90)
            promised = week + timedelta(days=supplier["promised_days"])
            destination = LOCATIONS[0][0]
            conn.execute(
                "INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, "
                "unit_cost, expected_delivery_date, destination_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [po_id, week, supplier["id"], product["sku"], quantity, product["cost"], promised, destination])
            po_rows += 1
            arrives = promised + timedelta(days=(rng.randint(2, supplier["late_bias"] + 6)
                                                 if rng.random() < supplier["late_share"] else -rng.randint(0, 3)))
            if arrives >= today - timedelta(days=7):
                open_orders += 1
                continue
            received = int(quantity * min(1.0, rng.gauss(supplier["fill"], 0.05)))
            conn.execute(
                "INSERT INTO stg_fmcg_receipts (receipt_id, po_id, receipt_date, sku, qty_received, qty_rejected) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                [f"QA-RCPT-{po_id}", po_id, arrives, product["sku"], max(0, received)])
            receipts += 1

    # Declared amendment rights on a handful of open orders (P4B), so the change workflow has
    # something real to price. Rights are declared, never inferred — that is the whole point.
    # Strictly *before* the plan date: the planning adapter drops an order placed on or after the
    # origin, and a right declared on one it has dropped makes the whole workspace read refuse.
    open_ids = [row[0] for row in conn.execute(
        "SELECT DISTINCT po_id FROM stg_fmcg_purchase_orders WHERE po_id NOT IN "
        "(SELECT DISTINCT po_id FROM stg_fmcg_receipts) AND po_date < ? ORDER BY po_id LIMIT 4",
        [today]).fetchall()]
    for po_id in open_ids:
        # A 0.40 deposit per remaining unit, half of it refundable, so the 0.20 cancel credit below
        # is inside what P4B allows: a credit may never exceed prepaid x refundable fraction.
        conn.execute("INSERT INTO stg_po_commitments (operator_id, po_id, stage, allow_split_amendments, "
                     "minimum_remaining_quantity, prepaid_per_remaining_unit, deposit_refundable_fraction, "
                     "cancellation_status) VALUES (?, ?, 'ordered', TRUE, 0, 0.40, 0.5, 'none')",
                     [operator, po_id])
        conn.execute("INSERT INTO stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, "
                     "fee_per_unit, credit_per_unit, max_quantity, deadline, allowed_stages, "
                     "contract_reference, provenance) VALUES (?, ?, ?, 'reschedule', 6, 0.05, 0, 100000, ?, "
                     "'[\"ordered\"]', ?, 'CONTRACT')",
                     [operator, po_id, f"{po_id}-defer", today + timedelta(days=30), f"Contract {po_id}"])
        conn.execute("INSERT INTO stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, "
                     "fee_per_unit, credit_per_unit, max_quantity, deadline, allowed_stages, "
                     "contract_reference, provenance) VALUES (?, ?, ?, 'cancel', 0, 0.10, 0.20, 100000, ?, "
                     "'[\"ordered\"]', ?, 'CONTRACT')",
                     [operator, po_id, f"{po_id}-cancel", today + timedelta(days=14), f"Contract {po_id}"])

    # Stock, split across the three sites. A lot on a perishable product carries its own expiry.
    perishable = {row[0]: True for row in conn.execute(
        "SELECT sku FROM stg_fmcg_skus WHERE sector IN ('PRODUCE', 'MEAT_SEAFOOD')").fetchall()}
    stock_rows = 0
    for product in products:
        total = int(product["weekly"] * rng.uniform(1.2, 9.0))
        for share, (location_id, _kind) in zip((0.6, 0.25, 0.15), LOCATIONS):
            expiry = (today + timedelta(days=rng.randint(4, 120))) if perishable.get(product["sku"]) else None
            conn.execute(
                "INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand, in_transit, expiry_date) "
                "VALUES (?, ?, ?, ?, 0, ?)",
                [today - timedelta(days=1), product["sku"], location_id, int(total * share), expiry])
            stock_rows += 1

    return {"shape": "corridor", "seed": seed, "products": len(products), "suppliers": len(suppliers),
            "locations": len(LOCATIONS), "customer_order_rows": order_rows, "purchase_orders": po_rows,
            "receipts": receipts, "open_orders": open_orders, "stock_rows": stock_rows,
            "amendment_rights_on": len(open_ids), "classification": "SYNTHETIC QA FIXTURE"}


def build_scale(conn, skus: int = 10_000, seed: int = 23, as_of: date | None = None) -> dict:
    """A catalogue of `skus` products, for measuring what the product's tables do at that size.

    Deliberately shallow per product — the point is row counts, not richness — and written with
    generated SQL rather than a Python loop, because inserting a million rows one statement at a
    time measures Python, not DuckDB.
    """
    rng = random.Random(seed)
    today = as_of or date.today()
    suppliers = 120
    for index in range(1, suppliers + 1):
        route, origin, _port, ocean, inland = CORRIDORS[index % len(CORRIDORS)]
        conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name, origin_iso3, route, "
                     "capacity_per_week, lead_time_promised_weeks) VALUES (?, ?, ?, ?, ?, ?)",
                     [f"QA-SUP-{index:04d}", f"Supplier {index}", origin, route,
                      rng.randint(5_000, 40_000), round((ocean + inland) / 7, 1)])
    for location_id, kind in LOCATIONS:
        conn.execute("INSERT INTO stg_fmcg_locations (location_id, kind) VALUES (?, ?)", [location_id, kind])

    categories = ", ".join(f"'{c}'" for c in CATEGORIES)
    brands = ", ".join(f"'{b}'" for b in BRANDS)
    conn.execute(f"""
        INSERT INTO stg_fmcg_skus (sku, sku_name, brand, category, sub_category, supplier_id,
                                   unit_cost, unit_price, units_per_case, moq_units, shelf_life_days, abc_class)
        SELECT 'QA-' || lpad(CAST(i AS VARCHAR), 6, '0'),
               list_value({brands})[1 + (i % {len(BRANDS)})] || ' item ' || CAST(i AS VARCHAR),
               list_value({brands})[1 + (i % {len(BRANDS)})],
               list_value({categories})[1 + (i % {len(CATEGORIES)})],
               list_value({categories})[1 + (i % {len(CATEGORIES)})] || ' — line ' || CAST(1 + (i % 4) AS VARCHAR),
               'QA-SUP-' || lpad(CAST(1 + (i % {suppliers}) AS VARCHAR), 4, '0'),
               round(0.8 + (i % 1300) / 100.0, 2), round(1.4 + (i % 1300) / 80.0, 2),
               list_value(6, 12, 24, 48)[1 + (i % 4)], list_value(60, 120, 240)[1 + (i % 3)],
               list_value(180, 365, 540, 730)[1 + (i % 4)],
               list_value('A', 'B', 'C')[1 + (i % 3)]
        FROM range(1, {skus + 1}) t(i)""")

    conn.execute(f"""
        INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand, in_transit)
        SELECT DATE '{today - timedelta(days=1)}', 'QA-' || lpad(CAST(i AS VARCHAR), 6, '0'),
               list_value({", ".join(f"'{loc}'" for loc, _ in LOCATIONS)})[1 + (j % {len(LOCATIONS)})],
               ((i * 37 + j * 91) % 5000), 0
        FROM range(1, {skus + 1}) t(i), range(0, {len(LOCATIONS)}) u(j)""")

    # A year of weekly customer orders on every product: the largest table, and the one the
    # explorer has to page through without flinching.
    conn.execute(f"""
        INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, requested_delivery_date, sku,
                                     qty_ordered, qty_shipped, channel, location_id)
        SELECT 'QA-SO-' || CAST(i AS VARCHAR) || '-' || CAST(w AS VARCHAR),
               'QA-CUST-' || CAST(1 + (i % 40) AS VARCHAR),
               DATE '{today}' - CAST(7 * w AS INTEGER) * INTERVAL 1 DAY,
               DATE '{today}' - CAST(7 * w - 3 AS INTEGER) * INTERVAL 1 DAY,
               'QA-' || lpad(CAST(i AS VARCHAR), 6, '0'),
               50 + ((i * 13 + w * 7) % 900), 50 + ((i * 13 + w * 7) % 900) - ((i + w) % 11),
               'wholesale',
               list_value({", ".join(f"'{loc}'" for loc, _ in LOCATIONS)})[1 + (w % {len(LOCATIONS)})]
        FROM range(1, {skus + 1}) t(i), range(1, 53) v(w)""")

    conn.execute(f"""
        INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost,
                                              expected_delivery_date, destination_id)
        SELECT 'QA-PO-' || CAST(i AS VARCHAR) || '-' || CAST(w AS VARCHAR),
               DATE '{today}' - CAST(14 * w AS INTEGER) * INTERVAL 1 DAY,
               'QA-SUP-' || lpad(CAST(1 + (i % {suppliers}) AS VARCHAR), 4, '0'),
               'QA-' || lpad(CAST(i AS VARCHAR), 6, '0'),
               600 + ((i * 29 + w * 17) % 4000), round(0.8 + (i % 1300) / 100.0, 2),
               DATE '{today}' - CAST(14 * w - 21 AS INTEGER) * INTERVAL 1 DAY,
               '{LOCATIONS[0][0]}'
        FROM range(1, {skus + 1}) t(i), range(1, 13) v(w)""")

    conn.execute("""
        INSERT INTO stg_fmcg_receipts (receipt_id, po_id, receipt_date, sku, qty_received, qty_rejected)
        SELECT 'QA-RCPT-' || po_id, po_id,
               expected_delivery_date + (CAST(abs(hash(po_id)) % 11 AS INTEGER) - 3) * INTERVAL 1 DAY,
               sku, CAST(qty_ordered * (0.9 + CAST(abs(hash(po_id)) % 11 AS DOUBLE) / 100.0) AS DOUBLE), 0
        FROM stg_fmcg_purchase_orders
        WHERE expected_delivery_date < CURRENT_DATE - INTERVAL 14 DAY""")

    counts = {name: conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in (  # noqa: S608
        "stg_fmcg_skus", "stg_fmcg_inventory", "stg_fmcg_orders", "stg_fmcg_purchase_orders",
        "stg_fmcg_receipts", "stg_fmcg_suppliers")}
    return {"shape": "scale", "seed": seed, "requested_skus": skus, "rows": counts,
            "total_rows": sum(counts.values()), "classification": "SYNTHETIC QA FIXTURE"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shape", choices=["corridor", "scale"])
    parser.add_argument("--db", required=True, help="path to write the DuckDB file to")
    parser.add_argument("--skus", type=int, default=10_000, help="scale only: how many products")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--as-of", default=None, help="the date the history ends (default: today)")
    parser.add_argument("--operator", default="QA_OPERATOR",
                        help="the operator id declared amendment rights are keyed to. It MUST match the "
                             "operator whose vault this file becomes, or `stg_po_options` reads back empty "
                             "and every open order silently stays KEEP-only.")
    args = parser.parse_args()

    path = Path(args.db)
    conn = _connect(path)
    if args.shape == "corridor":
        report = build_corridor(conn, seed=args.seed if args.seed is not None else 11,
                                as_of=date.fromisoformat(args.as_of) if args.as_of else None,
                                operator=args.operator)
    else:
        report = build_scale(conn, skus=args.skus, seed=args.seed if args.seed is not None else 23,
                             as_of=date.fromisoformat(args.as_of) if args.as_of else None)
    conn.close()
    print(f"{path}  {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
