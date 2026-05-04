"""Demand archetypes for synthetic data generation.

Each archetype defines weekly demand statistics per product×buyer combination.
Values are calibrated to Indiana food hub order volumes (kg/week).
"""

from dataclasses import dataclass, field


@dataclass
class ProductArchetype:
    product_id: str
    crop_name: str
    base_demand_kg: float          # mean weekly demand across all buyers
    cv: float                      # coefficient of variation (std/mean)
    intermittent: bool             # True → Croston-style demand (many zeros)
    seasonality: str               # 'summer_peak','spring_fall','year_round','winter_dip'
    shelf_life_days: int
    price_per_kg: float            # approximate farm-gate price
    spot_premium_pct: float        # typical spot premium vs contract
    yield_cv: float                # supply-side yield variability


@dataclass
class BuyerArchetype:
    buyer_id: str
    buyer_name: str
    buyer_type: str                # maps to dim_buyers.buyer_type
    tier: int
    order_frequency: float         # expected orders per week (0-1 for intermittent)
    preferred_product_ids: list[str] = field(default_factory=list)
    volume_multiplier: float = 1.0  # scales base demand for this buyer
    reliability: float = 0.95       # prob of fulfilling committed order


# ---------------------------------------------------------------------------
# Indiana pilot market: 10 products
# ---------------------------------------------------------------------------

PRODUCT_ARCHETYPES: dict[str, ProductArchetype] = {
    "PRD-001": ProductArchetype(
        product_id="PRD-001", crop_name="Romaine Lettuce",
        base_demand_kg=280.0, cv=0.25, intermittent=False,
        seasonality="summer_peak", shelf_life_days=7,
        price_per_kg=1.85, spot_premium_pct=22.0, yield_cv=0.18,
    ),
    "PRD-002": ProductArchetype(
        product_id="PRD-002", crop_name="Baby Spinach",
        base_demand_kg=180.0, cv=0.30, intermittent=False,
        seasonality="spring_fall", shelf_life_days=5,
        price_per_kg=3.20, spot_premium_pct=28.0, yield_cv=0.22,
    ),
    "PRD-003": ProductArchetype(
        product_id="PRD-003", crop_name="Cherry Tomatoes",
        base_demand_kg=160.0, cv=0.35, intermittent=False,
        seasonality="summer_peak", shelf_life_days=10,
        price_per_kg=3.50, spot_premium_pct=31.0, yield_cv=0.25,
    ),
    "PRD-004": ProductArchetype(
        product_id="PRD-004", crop_name="Bell Pepper Mix",
        base_demand_kg=120.0, cv=0.28, intermittent=False,
        seasonality="summer_peak", shelf_life_days=14,
        price_per_kg=2.60, spot_premium_pct=24.0, yield_cv=0.20,
    ),
    "PRD-005": ProductArchetype(
        product_id="PRD-005", crop_name="Cucumber",
        base_demand_kg=140.0, cv=0.22, intermittent=False,
        seasonality="summer_peak", shelf_life_days=10,
        price_per_kg=1.40, spot_premium_pct=18.0, yield_cv=0.15,
    ),
    "PRD-006": ProductArchetype(
        product_id="PRD-006", crop_name="Zucchini",
        base_demand_kg=90.0, cv=0.40, intermittent=True,
        seasonality="summer_peak", shelf_life_days=7,
        price_per_kg=1.20, spot_premium_pct=20.0, yield_cv=0.30,
    ),
    "PRD-007": ProductArchetype(
        product_id="PRD-007", crop_name="Kale Bunched",
        base_demand_kg=70.0, cv=0.45, intermittent=True,
        seasonality="spring_fall", shelf_life_days=7,
        price_per_kg=2.80, spot_premium_pct=25.0, yield_cv=0.20,
    ),
    "PRD-008": ProductArchetype(
        product_id="PRD-008", crop_name="Sweet Corn",
        base_demand_kg=350.0, cv=0.50, intermittent=False,
        seasonality="summer_peak", shelf_life_days=4,
        price_per_kg=0.60, spot_premium_pct=35.0, yield_cv=0.28,
    ),
    "PRD-009": ProductArchetype(
        product_id="PRD-009", crop_name="Strawberry",
        base_demand_kg=80.0, cv=0.55, intermittent=True,
        seasonality="spring_fall", shelf_life_days=5,
        price_per_kg=5.50, spot_premium_pct=40.0, yield_cv=0.35,
    ),
    "PRD-010": ProductArchetype(
        product_id="PRD-010", crop_name="Yellow Onion",
        base_demand_kg=200.0, cv=0.15, intermittent=False,
        seasonality="year_round", shelf_life_days=60,
        price_per_kg=0.55, spot_premium_pct=12.0, yield_cv=0.10,
    ),
}


BUYER_ARCHETYPES: dict[str, BuyerArchetype] = {
    "BUY-001": BuyerArchetype(
        buyer_id="BUY-001", buyer_name="IU Health System",
        buyer_type="institution", tier=1,
        order_frequency=1.0,
        preferred_product_ids=["PRD-001","PRD-002","PRD-003","PRD-004","PRD-007"],
        volume_multiplier=1.8, reliability=0.97,
    ),
    "BUY-002": BuyerArchetype(
        buyer_id="BUY-002", buyer_name="Market Wagon",
        buyer_type="distributor", tier=1,
        order_frequency=1.0,
        preferred_product_ids=["PRD-001","PRD-002","PRD-007","PRD-009","PRD-006"],
        volume_multiplier=1.4, reliability=0.95,
    ),
    "BUY-003": BuyerArchetype(
        buyer_id="BUY-003", buyer_name="Piazza Produce",
        buyer_type="wholesale", tier=2,
        order_frequency=0.9,
        preferred_product_ids=["PRD-003","PRD-004","PRD-005","PRD-008"],
        volume_multiplier=1.1, reliability=0.92,
    ),
    "BUY-004": BuyerArchetype(
        buyer_id="BUY-004", buyer_name="Traders Point Café",
        buyer_type="restaurant", tier=2,
        order_frequency=0.7,
        preferred_product_ids=["PRD-001","PRD-007","PRD-003","PRD-002"],
        volume_multiplier=0.4, reliability=0.88,
    ),
    "BUY-005": BuyerArchetype(
        buyer_id="BUY-005", buyer_name="Gleaners Food Bank",
        buyer_type="foodbank", tier=2,
        order_frequency=0.5,
        preferred_product_ids=["PRD-010","PRD-006","PRD-008","PRD-005"],
        volume_multiplier=0.3, reliability=0.90,
    ),
}


SUPPLIER_PRODUCT_MAP: dict[str, list[str]] = {
    "SUP-001": ["PRD-001","PRD-002","PRD-003"],
    "SUP-002": ["PRD-004","PRD-005","PRD-006"],
    "SUP-003": ["PRD-001","PRD-002","PRD-007"],
    "SUP-004": ["PRD-003","PRD-004","PRD-008"],
    "SUP-005": ["PRD-009"],
    "SUP-006": ["PRD-010"],
}


SUPPLIER_RELIABILITY: dict[str, float] = {
    "SUP-001": 0.92,
    "SUP-002": 0.87,
    "SUP-003": 0.90,
    "SUP-004": 0.85,
    "SUP-005": 0.88,
    "SUP-006": 0.94,
}
