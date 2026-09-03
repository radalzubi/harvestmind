"""Synthetic Jordanian commercial food distributor. PROJECT B.

Separate from `synthetic/indiana_operator_sim.py`, which is PROJECT A
(US agriculture). They share the engine and nothing else. Do not use one
project's generator to validate the other's claims: weather-driven yield
and route-driven transit disruption are different uncertainty structures.

WHAT MAKES THIS DIFFERENT FROM THE AGRICULTURE GENERATOR

1. Uncertainty is ROUTE-DRIVEN, not weather-driven. A supplier's delivery
   depends on the channel it ships through, and channels fail for their own
   reasons: a congested berth at Aqaba, a closed land crossing, a security
   event on the Red Sea.

2. The shock is primarily a TIMING shock. Goods are not destroyed, they
   arrive late. Lead time is the random variable that matters, not just
   fill rate.

3. Routes are SUBSTITUTES. Goods landed at a Saudi port and trucked north
   are an alternative to Aqaba. Correlation runs through SHARED CHANNELS,
   not shared geography: two suppliers both shipping via Aqaba fail
   together even if their factories are continents apart.

4. Disruption is EPISODIC, not seasonal. Aqaba congestion and political
   events arrive as episodes with a start and an end, so the process is
   regime-switching rather than stationary. Fitting a single distribution
   to a mixture of calm and disrupted weeks understates the tails.

Everything here is synthetic and calibrated to public reporting about
Jordan's import channels. It is not operator data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

# Jordan's import channels, with nominal transit in weeks and how volatile
# each is. Aqaba is fast but exposed to congestion; the Saudi road route is
# slower but independent of the port; local supply is short and stable.
ROUTE_PROFILE: dict[str, dict[str, float]] = {
    "aqaba":      {"nominal_lead": 2.0, "lead_sd": 0.6, "base_fill": 0.93},
    "saudi_land": {"nominal_lead": 1.0, "lead_sd": 0.4, "base_fill": 0.95},
    "syria_land": {"nominal_lead": 1.0, "lead_sd": 0.8, "base_fill": 0.88},
    "iraq_land":  {"nominal_lead": 1.5, "lead_sd": 0.9, "base_fill": 0.86},
    "local":      {"nominal_lead": 0.0, "lead_sd": 0.1, "base_fill": 0.97},
    "air":        {"nominal_lead": 0.0, "lead_sd": 0.2, "base_fill": 0.99},
}

# Shelf-stable and semi-perishable mix, unlike the produce generator.
PRODUCTS: tuple[tuple[str, float, float, float], ...] = (
    # name, unit cost JOD, gross margin JOD, weekly decay fraction
    ("rice_5kg",        3.20, 0.55, 0.000),
    ("sunflower_oil_1L", 1.85, 0.35, 0.000),
    ("sugar_1kg",       0.70, 0.14, 0.000),
    ("pasta_500g",      0.55, 0.13, 0.000),
    ("canned_tuna",     1.10, 0.30, 0.000),
    ("milk_powder_900g", 4.50, 0.85, 0.000),
    ("white_cheese_1kg", 3.90, 0.95, 0.030),   # semi-perishable
    ("yoghurt_1kg",     1.40, 0.40, 0.120),    # perishable
    ("frozen_chicken_kg", 2.60, 0.55, 0.010),
    ("eggs_tray",       1.75, 0.35, 0.060),
)


@dataclass
class JordanSimulationConfig:
    """Every field is an assumption. None of it is measured."""

    seed: int = 42
    weeks: int = 160
    n_suppliers: int = 14
    annual_revenue_jod: float = 12_000_000.0
    # Episodic disruption, not seasonal. Probability per week of ENTERING a
    # disrupted state on a given route, and of leaving it once in one.
    p_disruption_start: float = 0.05
    p_disruption_end: float = 0.30
    # What a disruption does to the affected route.
    disruption_lead_multiplier: float = 2.5
    disruption_fill_multiplier: float = 0.65
    # Routes that can be disrupted, and which fail TOGETHER when they do.
    # Aqaba congestion also degrades everything arriving through the Red Sea.
    disruptable_routes: tuple[str, ...] = ("aqaba", "syria_land", "iraq_land",
                                           "saudi_land")
    correlated_route_groups: tuple[tuple[str, ...], ...] = (
        ("aqaba",),                      # port congestion
        ("syria_land", "iraq_land"),     # northern political events
        ("saudi_land",),                 # southern road route
    )
    demand_weekly_cv: float = 0.18
    ramadan_uplift: float = 1.45
    seed_offset: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        if self.weeks < 8:
            raise ValueError("weeks must be >= 8")
        if not 0.0 <= self.p_disruption_start <= 1.0:
            raise ValueError("p_disruption_start must be a probability")
        if not 0.0 < self.p_disruption_end <= 1.0:
            raise ValueError("p_disruption_end must be in (0, 1]")
        if self.disruption_lead_multiplier < 1.0:
            raise ValueError("a disruption cannot make transit faster")
        if not 0.0 < self.disruption_fill_multiplier <= 1.0:
            raise ValueError("disruption_fill_multiplier must be in (0, 1]")


def simulate_route_states(cfg: JordanSimulationConfig,
                          rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Regime-switching disruption per route group.

    Returns {route: boolean array over weeks, True where disrupted}.
    Routes inside a correlated group switch TOGETHER, because a northern
    political event closes Syria and Iraq at the same time. Routes in
    different groups are independent, which is what makes substitution
    valuable: when the land crossings shut, Aqaba is usually still open.
    """
    states: dict[str, np.ndarray] = {}
    for group in cfg.correlated_route_groups:
        disrupted = np.zeros(cfg.weeks, dtype=bool)
        on = False
        for t in range(cfg.weeks):
            if on:
                on = rng.random() >= cfg.p_disruption_end
            else:
                on = rng.random() < cfg.p_disruption_start
            disrupted[t] = on
        for route in group:
            states[route] = disrupted
    for route in ROUTE_PROFILE:
        states.setdefault(route, np.zeros(cfg.weeks, dtype=bool))
    return states


def build_jordan_dataset(cfg: JordanSimulationConfig | None = None) -> dict:
    """Generate the operator. Returns suppliers, demand, deliveries, states."""
    cfg = cfg or JordanSimulationConfig()
    rng = np.random.default_rng(cfg.seed + cfg.seed_offset)
    start = date(2026, 1, 5)
    weeks = [start + timedelta(weeks=w) for w in range(cfg.weeks)]

    route_states = simulate_route_states(cfg, rng)

    # Suppliers, each tagged with the channel it ships through. Route mix is
    # deliberately unbalanced: most volume comes through Aqaba and the Saudi
    # road route, which is what makes those two the ones that matter.
    route_weights = {"aqaba": 0.40, "saudi_land": 0.28, "local": 0.14,
                     "syria_land": 0.08, "iraq_land": 0.06, "air": 0.04}
    routes = list(route_weights)
    probs = np.array([route_weights[r] for r in routes], dtype=float)
    probs /= probs.sum()
    suppliers = []
    for k in range(cfg.n_suppliers):
        route = str(rng.choice(routes, p=probs))
        suppliers.append({
            "supplier_id": f"JO-S{k + 1:03d}",
            "route": route,
            "base_fill": float(np.clip(
                ROUTE_PROFILE[route]["base_fill"] + rng.normal(0, 0.02),
                0.5, 1.0)),
        })

    # Demand: shelf-stable, so no harvest seasonality. Ramadan is the one
    # large predictable swing, and it moves ~11 days earlier each year.
    ramadan_weeks = set()
    for yr in range(cfg.weeks // 52 + 2):
        centre = int(9 + yr * 52 - yr * 1.6)
        ramadan_weeks.update(range(max(centre - 2, 0), centre + 3))

    weekly_rev = cfg.annual_revenue_jod / 52.0
    demand_rows, delivery_rows = [], []
    shares = rng.dirichlet(np.ones(len(PRODUCTS)) * 4.0)

    for t, wk in enumerate(weeks):
        uplift = cfg.ramadan_uplift if t in ramadan_weeks else 1.0
        for (name, cost, margin, _decay), share in zip(PRODUCTS, shares,
                                                       strict=True):
            noise = max(0.15, rng.normal(1.0, cfg.demand_weekly_cv))
            qty = weekly_rev * share * uplift * noise / max(cost + margin, 0.01)
            demand_rows.append({
                "week_start": wk, "product_id": name,
                "demand_kg": round(float(qty), 1),
                "unit_cost": cost, "unit_margin": margin,
            })

    for s in suppliers:
        prof = ROUTE_PROFILE[s["route"]]
        disrupted = route_states[s["route"]]
        for t, wk in enumerate(weeks):
            hit = bool(disrupted[t])
            lead = prof["nominal_lead"] * (
                cfg.disruption_lead_multiplier if hit else 1.0)
            lead = max(0.0, rng.normal(lead, prof["lead_sd"]
                                       * (2.0 if hit else 1.0)))
            fill = s["base_fill"] * (
                cfg.disruption_fill_multiplier if hit else 1.0)
            fill = float(np.clip(rng.normal(fill, 0.04), 0.0, 1.0))
            delivery_rows.append({
                "week_start": wk, "supplier_id": s["supplier_id"],
                "route": s["route"], "lead_time_weeks": round(lead, 2),
                "fill_rate": round(fill, 4), "route_disrupted": hit,
            })

    return {
        "config": cfg,
        "suppliers": suppliers,
        "weeks": weeks,
        "demand": demand_rows,
        "deliveries": delivery_rows,
        "route_states": {r: v.tolist() for r, v in route_states.items()},
        "metadata": {
            "project": "B_commercial_jordan",
            "synthetic": True,
            "note": ("route-driven episodic disruption, not weather; "
                     "every parameter is an assumption"),
            "disrupted_week_share": {
                r: round(float(np.mean(v)), 3)
                for r, v in route_states.items()},
        },
    }
