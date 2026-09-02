"""Synthetic vertically integrated grower-packer-shipper. PROJECT C.

A THIRD structure, not a variant of A or B.

  Project A  buys from many growers weekly; uncertainty is their yield
  Project B  buys through routes; uncertainty is transit timing
  Project C  GROWS most of what it sells; uncertainty is its OWN harvest

WHY THIS IS STILL AN OPTIMIZATION PROBLEM. The intuition that vertical
integration removes supply uncertainty is wrong twice over.

1. The uncertainty moves inward rather than disappearing. One harvest per
   year, realized months after buyers were promised volume, and the whole
   book depends on that single draw. There is no diversification across
   suppliers to soften it.

2. Integrated shippers BUY EXTERNALLY as well. Reported industry practice:
   California grape shippers import from Mexico and Chile to hold
   year-round supply, and integrated date packers market third-party fruit
   alongside their own. So the decision is MAKE VERSUS BUY under
   uncertainty, and external purchase is the recourse channel.

THE DECISION THIS MODELS

  Stage 1, pre-harvest: commit volume to buyers and channels before the
    harvest is known.
  Nature: harvest realizes, one lumpy uncertain quantity.
  Stage 2: buy externally to cover a shortfall, divert surplus to a lower
    value channel, or carry it in store and sell it later.

Then a DEPLETION problem the other two projects do not have: a single
harvest must be sold down across a long storage window, across channels
with different prices and different shelf lives.

Everything here is synthetic. Storage behaviour is calibrated to public
guidance for dates (cold storage viable around 0-10C, roughly 12 months at
5C, dried varieties far longer) but no operator data was used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

# Channels an integrated producer can sell into. Price, weekly decay while
# stored, and how much of the crop the channel can absorb in a week.
CHANNELS: dict[str, dict[str, float]] = {
    "fresh_export":   {"price": 4.20, "decay": 0.080, "weekly_cap_share": 0.10},
    "fresh_domestic": {"price": 2.60, "decay": 0.080, "weekly_cap_share": 0.15},
    "dried_export":   {"price": 3.10, "decay": 0.004, "weekly_cap_share": 0.12},
    "processing":     {"price": 1.15, "decay": 0.002, "weekly_cap_share": 0.40},
}


@dataclass
class IntegratedProducerConfig:
    """Every field is an assumption. None of it is measured."""

    seed: int = 42
    years: int = 6
    weeks_per_year: int = 52
    # Harvest arrives in a short window, not continuously. This is the
    # structural difference from Projects A and B.
    harvest_start_week: int = 32
    harvest_weeks: int = 8
    expected_harvest_tonnes: float = 4_000.0
    # Farm-level yield variability. USDA reports farm-level CV around
    # 0.2-0.4 for field crops and notes farm variability exceeds regional;
    # perennial tree crops with one harvest sit at the higher end.
    harvest_cv: float = 0.28
    # Third-party fruit the producer can buy to cover a shortfall. This is
    # the recourse channel and it is neither free nor unlimited.
    external_price_multiplier: float = 1.45
    external_availability_share: float = 0.25
    external_fill_mean: float = 0.85
    # Storage
    storage_capacity_tonnes: float = 2_500.0
    holding_cost_per_tonne_week: float = 1.10
    # Buyers commit this many weeks before harvest resolves.
    commitment_lead_weeks: int = 20

    def __post_init__(self) -> None:
        if self.years < 2:
            raise ValueError("years must be >= 2")
        if not 0.0 < self.harvest_cv < 1.5:
            raise ValueError("harvest_cv must be in (0, 1.5)")
        if self.external_price_multiplier < 1.0:
            raise ValueError("external fruit is never cheaper than own")
        if self.harvest_weeks < 1:
            raise ValueError("harvest_weeks must be >= 1")


def build_integrated_dataset(
    cfg: IntegratedProducerConfig | None = None,
) -> dict:
    """Generate an integrated producer's harvest and demand history."""
    cfg = cfg or IntegratedProducerConfig()
    rng = np.random.default_rng(cfg.seed)
    start = date(2020, 1, 6)
    total_weeks = cfg.years * cfg.weeks_per_year
    weeks = [start + timedelta(weeks=w) for w in range(total_weeks)]

    # One harvest per year. The whole book depends on this single draw, and
    # there is no supplier diversification to soften it.
    harvests = []
    for y in range(cfg.years):
        realized = float(np.clip(
            rng.normal(cfg.expected_harvest_tonnes,
                       cfg.expected_harvest_tonnes * cfg.harvest_cv),
            cfg.expected_harvest_tonnes * 0.20, None))
        harvests.append({
            "year": y,
            "expected_tonnes": cfg.expected_harvest_tonnes,
            "realized_tonnes": round(realized, 1),
            "yield_ratio": round(realized / cfg.expected_harvest_tonnes, 3),
            "start_week": y * cfg.weeks_per_year + cfg.harvest_start_week,
            "weeks": cfg.harvest_weeks,
        })

    # Weekly arrivals spread over the harvest window.
    arrivals = np.zeros(total_weeks)
    for h in harvests:
        shape = rng.dirichlet(np.ones(h["weeks"]) * 6.0)
        for k in range(h["weeks"]):
            wk = h["start_week"] + k
            if wk < total_weeks:
                arrivals[wk] += h["realized_tonnes"] * shape[k]

    # Channel demand, with a seasonal export peak and price noise.
    demand_rows = []
    for t in range(total_weeks):
        woy = t % cfg.weeks_per_year
        season = 1.0 + 0.45 * np.sin(2 * np.pi * (woy - 30) / cfg.weeks_per_year)
        for ch, spec in CHANNELS.items():
            base = cfg.expected_harvest_tonnes / cfg.weeks_per_year
            qty = base * spec["weekly_cap_share"] * 4.0 * season * \
                max(0.2, rng.normal(1.0, 0.20))
            price = spec["price"] * max(0.5, rng.normal(1.0, 0.12))
            demand_rows.append({
                "week": t, "week_start": weeks[t], "channel": ch,
                "demand_tonnes": round(float(qty), 2),
                "price": round(float(price), 3),
                "decay": spec["decay"],
            })

    # External purchase availability, the recourse channel.
    external_rows = []
    for t in range(total_weeks):
        avail = cfg.expected_harvest_tonnes / cfg.weeks_per_year * \
            cfg.external_availability_share * max(0.0, rng.normal(1.0, 0.35))
        fill = float(np.clip(rng.normal(cfg.external_fill_mean, 0.08), 0, 1))
        external_rows.append({
            "week": t, "available_tonnes": round(float(avail), 2),
            "price_multiplier": cfg.external_price_multiplier,
            "fill_rate": round(fill, 3),
        })

    return {
        "config": cfg,
        "weeks": weeks,
        "harvests": harvests,
        "weekly_arrivals": arrivals.tolist(),
        "demand": demand_rows,
        "external": external_rows,
        "metadata": {
            "project": "C_vertically_integrated",
            "synthetic": True,
            "structure": ("one lumpy harvest per year, committed to buyers "
                          f"{cfg.commitment_lead_weeks} weeks before it "
                          "resolves; external purchase is the recourse"),
            "realized_yield_ratios": [h["yield_ratio"] for h in harvests],
            "note": "every parameter is an assumption, not a measurement",
        },
    }
