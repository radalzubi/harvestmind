"""Reproducible synthetic Indiana regional-produce operator history.

This is not a sampled operator, a market forecast, or customer validation.
Public Indiana sources determine the product basket and broad harvest timing;
commercial economics and operating behavior are explicit modeled assumptions.
The generator exists to exercise HarvestMind under plausible seasonality,
correlated supply disruption, short shelf life, and imperfect records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import duckdb
import numpy as np


SOURCE_NOTES = {
    "crop_scope": "USDA NASS 2022 Census of Agriculture, Indiana Table 36",
    "seasonality": "Purdue Extension FoodLink Seasonal Chart for Indiana Fresh Produce",
    "climate": "NWS Indianapolis 1991-2020 Climate Normals",
    "operator_definition": "USDA AMS Local Food Directories food-hub definition",
}


@dataclass(frozen=True)
class IndianaSimulationConfig:
    seed: int = 42
    weeks: int = 80
    end_date: date = date(2026, 8, 24)
    annual_revenue_usd: float = 6_000_000.0
    target_waste_rate: float = 0.065


@dataclass(frozen=True)
class Product:
    name: str
    category: str
    shelf_days: int
    cost_per_kg: float
    sell_per_kg: float
    weekly_kg: float
    local_months: tuple[int, ...]


PRODUCTS = (
    Product("Leaf Lettuce", "Leafy Greens", 6, 2.15, 3.55, 650, (5, 6, 9, 10)),
    Product("Spinach", "Leafy Greens", 5, 2.60, 4.25, 430, (4, 5, 6, 9, 10)),
    Product("Tomatoes", "Fruiting Vegetables", 9, 1.55, 2.85, 1_250, (7, 8, 9)),
    Product("Cucumbers", "Fruiting Vegetables", 10, 1.10, 2.05, 780, (6, 7, 8, 9)),
    Product("Bell Peppers", "Fruiting Vegetables", 12, 1.85, 3.30, 610, (7, 8, 9)),
    Product("Summer Squash", "Fruiting Vegetables", 8, 1.15, 2.15, 560, (6, 7, 8, 9)),
    Product("Sweet Corn", "Fruiting Vegetables", 5, 1.05, 2.10, 1_100, (7, 8, 9)),
    Product("Green Beans", "Fruiting Vegetables", 8, 1.90, 3.40, 520, (6, 7, 8, 9)),
    Product("Broccoli", "Brassica", 12, 1.60, 2.95, 480, (5, 6, 9, 10)),
    Product("Cabbage", "Brassica", 25, 0.78, 1.55, 570, (6, 7, 8, 9, 10)),
    Product("Carrots", "Roots", 45, 0.78, 1.50, 730, (6, 7, 8, 9, 10, 11)),
    Product("Potatoes", "Roots", 75, 0.62, 1.20, 1_050, (7, 8, 9, 10)),
    Product("Onions", "Roots", 60, 0.72, 1.38, 940, (7, 8, 9, 10)),
    Product("Pumpkins", "Cucurbits", 45, 0.72, 1.55, 180, (9, 10)),
    Product("Apples", "Fruit", 60, 1.45, 2.70, 850, (8, 9, 10, 11)),
    Product("Strawberries", "Berries", 4, 5.30, 9.10, 330, (5, 6)),
)


BUYERS = (
    ("B001", "Central Indiana School Cooperative", "school", 1.10),
    ("B002", "Capital City Hospital Network", "hospital", 1.08),
    ("B003", "Hoosier University Dining", "school", 1.05),
    ("B004", "Northside Independent Grocers", "grocery", 1.02),
    ("B005", "Wabash Valley Foodservice", "foodservice", 1.00),
    ("B006", "Northeast Indiana Schools", "school", 0.97),
    ("B007", "Community Care Kitchens", "hospital", 0.95),
    ("B008", "South Central Restaurant Group", "foodservice", 0.92),
    ("B009", "Regional Food Bank Program", "institution", 0.90),
    ("B010", "Independent Market Collective", "grocery", 0.88),
)


def _week_dates(config: IndianaSimulationConfig) -> list[date]:
    start = config.end_date - timedelta(weeks=config.weeks - 1)
    return [start + timedelta(weeks=i) for i in range(config.weeks)]


def _season_factor(product: Product, month: int) -> float:
    if month in product.local_months:
        return 1.18
    distance = min((month - m) % 12 for m in product.local_months)
    reverse = min((m - month) % 12 for m in product.local_months)
    return 0.88 if min(distance, reverse) == 1 else 0.72


def build_indiana_dataset(
    conn: duckdb.DuckDBPyConnection,
    config: IndianaSimulationConfig = IndianaSimulationConfig(),
) -> dict[str, float | int | str]:
    """Populate the five staging tables and return auditable run metadata."""
    rng = np.random.default_rng(config.seed)
    weeks = _week_dates(config)
    product_ids = {p.name: f"IN-P{i:03d}" for i, p in enumerate(PRODUCTS, 1)}

    conn.executemany(
        "INSERT INTO stg_products (product_id, product_name, category, unit, "
        "default_shelf_life_days, traceability_required) VALUES (?,?,?,?,?,?)",
        [(product_ids[p.name], p.name, p.category, "kg", p.shelf_days,
          p.category in {"Leafy Greens", "Fruiting Vegetables"}) for p in PRODUCTS],
    )

    # Three sourcing regions. Names are fictional; behavior is modeled.
    suppliers = []
    for idx in range(18):
        region = "central_in" if idx < 7 else "southern_in" if idx < 12 else "national"
        mean_fill = rng.uniform(0.91, 0.985) if idx < 12 else rng.uniform(0.94, 0.992)
        suppliers.append((f"IN-S{idx + 1:03d}", f"Modeled Supplier {idx + 1:02d}", region, mean_fill))

    product_suppliers: dict[str, list[int]] = {}
    for product in PRODUCTS:
        local = list(rng.choice(12, size=2, replace=False))
        national = [int(rng.integers(12, 18))]
        product_suppliers[product.name] = local + national

    # Build orders before scaling, retaining seasonality and buyer calendars.
    order_rows: list[tuple] = []
    order_id = 0
    demand_by_week_product: dict[tuple[date, str], float] = {}
    for week in weeks:
        holiday = 1.18 if week.month in {11, 12} else 1.08 if week.month == 7 else 1.0
        for product in PRODUCTS:
            seasonal = 1.0 + 0.16 * np.sin(2 * np.pi * (week.timetuple().tm_yday - 110) / 365)
            weekly_total = product.weekly_kg * seasonal * holiday * rng.lognormal(0, 0.10)
            demand_by_week_product[(week, product.name)] = weekly_total
            buyer_weights = rng.dirichlet(np.full(len(BUYERS), 2.2))
            for buyer_index, (buyer_id, buyer_name, buyer_type, priority) in enumerate(BUYERS):
                school_factor = 0.42 if buyer_type == "school" and week.month in {6, 7} else 1.0
                requested = weekly_total * buyer_weights[buyer_index] * school_factor
                system_fill = np.clip(rng.normal(0.915, 0.035) * priority, 0.65, 1.0)
                fulfilled = requested * system_fill
                substituted = max(requested - fulfilled, 0) * rng.uniform(0.05, 0.28)
                order_id += 1
                order_rows.append((
                    f"IN-O{order_id:06d}", buyer_id, buyer_name,
                    product_ids[product.name], product.name, week, week + timedelta(days=3),
                    requested, fulfilled, substituted, product.sell_per_kg, "A",
                ))

    raw_revenue = sum(row[8] * row[10] for row in order_rows)
    annualizer = 52.0 / config.weeks
    scale = config.annual_revenue_usd / (raw_revenue * annualizer)
    scaled_orders = []
    for row in order_rows:
        mutable = list(row)
        for column in (7, 8, 9):
            mutable[column] = round(float(mutable[column]) * scale, 2)
        scaled_orders.append(tuple(mutable))
    conn.executemany(
        "INSERT INTO stg_buyer_orders (order_id,buyer_id,buyer_name,product_id,"
        "product_name,order_date,delivery_date,requested_quantity,fulfilled_quantity,"
        "substituted_quantity,sales_price,required_quality_grade) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        scaled_orders,
    )

    delivery_rows: list[tuple] = []
    delivery_id = 0
    accepted_value = 0.0
    week_shocks: dict[date, dict[str, float]] = {}
    for week in weeks:
        heat_risk = 0.16 if week.month in {7, 8} else 0.04
        storm_risk = 0.12 if week.month in {4, 5, 6} else 0.035
        week_shocks[week] = {
            "central_in": rng.uniform(0.68, 0.86) if rng.random() < heat_risk + storm_risk else rng.uniform(0.96, 1.01),
            "southern_in": rng.uniform(0.72, 0.89) if rng.random() < heat_risk else rng.uniform(0.96, 1.01),
            "national": rng.uniform(0.82, 0.94) if rng.random() < 0.055 else rng.uniform(0.98, 1.01),
        }
        for product in PRODUCTS:
            need = demand_by_week_product[(week, product.name)] * scale * 1.03
            source_indices = product_suppliers[product.name]
            for source_index in source_indices:
                supplier_id, supplier_name, region, base_fill = suppliers[source_index]
                local_factor = _season_factor(product, week.month) if region != "national" else 1.0
                share = 0.38 if region != "national" else 0.24
                ordered = need * share * rng.uniform(0.88, 1.12)
                fill = np.clip(base_fill * week_shocks[week][region] * local_factor + rng.normal(0, 0.025), 0.35, 1.0)
                delivered = ordered * fill
                reject_rate = np.clip(rng.beta(1.4, 42) + (0.025 if week.month in {7, 8} else 0), 0, 0.18)
                accepted = delivered * (1 - reject_rate)
                unit_cost = product.cost_per_kg * (1.12 if region == "national" else 0.96) * rng.uniform(0.94, 1.09)
                accepted_value += accepted * unit_cost
                delivery_id += 1
                delivery_rows.append((
                    f"IN-D{delivery_id:06d}", supplier_id, supplier_name,
                    product_ids[product.name], product.name, week, round(ordered, 2),
                    round(delivered, 2), round(accepted, 2), round(delivered - accepted, 2),
                    round(unit_cost, 4), "A", f"IN-LOT-{delivery_id:06d}",
                ))
    conn.executemany(
        "INSERT INTO stg_supplier_deliveries (delivery_id,supplier_id,supplier_name,"
        "product_id,product_name,delivery_date,ordered_quantity,delivered_quantity,"
        "accepted_quantity,rejected_quantity,unit_cost,quality_grade,lot_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        delivery_rows,
    )

    # Current lots include realistic record gaps to exercise traceability logic.
    inventory_rows = []
    for idx, product in enumerate(PRODUCTS, 1):
        for lot_index in range(3):
            quantity = product.weekly_kg * scale * rng.uniform(0.12, 0.38)
            arrival = config.end_date - timedelta(days=int(rng.integers(0, 8)))
            expiry = arrival + timedelta(days=product.shelf_days)
            source = suppliers[product_suppliers[product.name][lot_index % 3]][0]
            lot_id = None if rng.random() < 0.045 else f"IN-INV-{idx:03d}-{lot_index + 1}"
            supplier_id = None if rng.random() < 0.045 else source
            inventory_rows.append((
                lot_id, product_ids[product.name], product.name, supplier_id,
                round(quantity, 2), "kg", arrival, expiry, "IND-DC-1", "A",
                round(quantity * rng.uniform(0.05, 0.35), 2),
            ))
    conn.executemany(
        "INSERT INTO stg_inventory_lots (lot_id,product_id,product_name,supplier_id,"
        "quantity_on_hand,unit,arrival_date,expiration_date,warehouse_location,"
        "quality_grade,committed_quantity) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        inventory_rows,
    )

    target_waste = accepted_value * config.target_waste_rate
    waste_rows = []
    accumulated = 0.0
    adjustment_id = 0
    weights = np.array([1 / max(p.shelf_days, 3) for p in PRODUCTS], dtype=float)
    weights /= weights.sum()
    while accumulated < target_waste:
        product = PRODUCTS[int(rng.choice(len(PRODUCTS), p=weights))]
        quantity = rng.uniform(8, 70) * scale
        value = quantity * product.cost_per_kg
        week = weeks[int(rng.integers(0, len(weeks)))]
        adjustment_id += 1
        accumulated += value
        waste_rows.append((
            f"IN-W{adjustment_id:06d}", week, product_ids[product.name], product.name,
            None, round(quantity, 2), rng.choice(("Spoilage", "Overripe", "Temperature", "Bruising", "Expired")),
            None if rng.random() < 0.10 else round(value, 2),
        ))
    conn.executemany(
        "INSERT INTO stg_waste_adjustments (adjustment_id,date,product_id,product_name,"
        "lot_id,quantity_lost,reason,estimated_value_lost) VALUES (?,?,?,?,?,?,?,?)",
        waste_rows,
    )

    actual_revenue = conn.execute(
        "SELECT SUM(fulfilled_quantity * sales_price) FROM stg_buyer_orders"
    ).fetchone()[0]
    return {
        "seed": config.seed,
        "weeks": config.weeks,
        "products": len(PRODUCTS),
        "suppliers": len(suppliers),
        "buyers": len(BUYERS),
        "order_lines": len(scaled_orders),
        "delivery_lines": len(delivery_rows),
        "annualized_revenue_usd": round(float(actual_revenue) * annualizer, 2),
        "target_waste_rate": config.target_waste_rate,
        "data_basis": "synthetic Indiana-market scenario; no operator records",
    }
