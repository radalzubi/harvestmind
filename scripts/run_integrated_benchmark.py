"""PROJECT C benchmark: committing channel volume before harvest resolves.

The decision. Twenty weeks before harvest, an integrated producer promises
volume to channels. Then one lumpy uncertain harvest arrives. Shortfall is
covered by buying third-party fruit at a premium and limited availability;
surplus is diverted to a lower-value channel or carried in store and decays.

The question. Does optimizing over the harvest DISTRIBUTION beat a planner
who commits at a sensible PERCENTILE of it? That is the honest test, because
a percentile rule is what a competent grower already does in their head, and
the newsvendor answer IS a percentile. If the optimizer only beats a planner
who commits at the mean, it has proved very little.

Policies:
  expected_yield   commit against the expected harvest       (naive)
  p25 / p40 / p60  commit at that percentile of the harvest  (rule of thumb)
  stochastic       maximize expected profit over the distribution
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from synthetic.commercial.integrated_producer_sim import (  # noqa: E402
    CHANNELS, IntegratedProducerConfig, build_integrated_dataset,
)


def _season_economics(data, year: int) -> dict:
    """Channel prices and demand for the season following a harvest."""
    cfg = data["config"]
    w0 = year * cfg.weeks_per_year + cfg.harvest_start_week
    w1 = w0 + cfg.weeks_per_year
    rows = [r for r in data["demand"] if w0 <= r["week"] < w1]
    econ = {}
    for ch in CHANNELS:
        sub = [r for r in rows if r["channel"] == ch]
        if not sub:
            continue
        econ[ch] = {
            "price": float(np.mean([r["price"] for r in sub])),
            "demand": float(sum(r["demand_tonnes"] for r in sub)),
            "decay": CHANNELS[ch]["decay"],
        }
    return econ


def _profit(commit: dict, harvest: float, econ: dict, cfg) -> float:
    """Realized profit for a commitment vector given the actual harvest.

    Shortfall is bought externally at a premium, subject to availability.
    Anything still short is a broken commitment, penalised at the channel
    price (the customer buys elsewhere and you carry the relationship cost).
    Surplus is carried and decays.
    """
    total_commit = sum(commit.values())
    external_cap = cfg.expected_harvest_tonnes * cfg.external_availability_share
    revenue = penalty = ext_cost = carry_cost = 0.0

    if total_commit <= harvest:
        surplus = harvest - total_commit
        for ch, q in commit.items():
            revenue += q * econ[ch]["price"]
        # Surplus goes to the cheapest channel that can absorb it, after
        # storage loss. This is the diversion decision.
        proc = econ.get("processing")
        if proc and surplus > 0:
            weeks_held = 12.0
            kept = surplus * (1.0 - proc["decay"]) ** weeks_held
            revenue += kept * proc["price"]
            carry_cost += surplus * cfg.holding_cost_per_tonne_week * weeks_held
    else:
        shortfall = total_commit - harvest
        bought = min(shortfall, external_cap) * cfg.external_fill_mean
        unmet = shortfall - bought
        avg_price = (sum(q * econ[ch]["price"] for ch, q in commit.items())
                     / max(total_commit, 1e-9))
        ext_cost = bought * avg_price * (cfg.external_price_multiplier - 1.0)
        for ch, q in commit.items():
            revenue += q * econ[ch]["price"]
        revenue -= unmet * avg_price
        penalty = unmet * avg_price * 0.35     # relationship cost
    return revenue - ext_cost - carry_cost - penalty


def _allocate(total: float, econ: dict) -> dict:
    """Fill the highest-price channels first, up to their demand."""
    out, left = {}, total
    for ch in sorted(econ, key=lambda c: -econ[c]["price"]):
        take = min(left, econ[ch]["demand"])
        if take > 0:
            out[ch] = take
            left -= take
        if left <= 0:
            break
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", default="5,11,23,37,53")
    p.add_argument("--years", type=int, default=12)
    p.add_argument("--draws", type=int, default=4000)
    a = p.parse_args()

    policies = ["expected_yield", "p25", "p40", "p60", "stochastic"]
    profits: dict[str, list[float]] = {k: [] for k in policies}

    for seed in [int(s) for s in a.seeds.split(",")]:
        cfg = IntegratedProducerConfig(seed=seed, years=a.years)
        data = build_integrated_dataset(cfg)
        rng = np.random.default_rng(seed + 999)

        for y in range(1, a.years):
            econ = _season_economics(data, y)
            if not econ:
                continue
            realized = data["harvests"][y]["realized_tonnes"]
            # Belief formed from PRIOR years only. No lookahead.
            hist = [h["realized_tonnes"] for h in data["harvests"][:y]]
            if len(hist) < 2:
                continue
            mu, sd = float(np.mean(hist)), float(np.std(hist, ddof=1))
            draws = np.clip(rng.normal(mu, max(sd, 1.0), a.draws), 1.0, None)

            cands = {
                "expected_yield": mu,
                "p25": float(np.quantile(draws, 0.25)),
                "p40": float(np.quantile(draws, 0.40)),
                "p60": float(np.quantile(draws, 0.60)),
            }
            # Stochastic: pick the commitment maximizing EXPECTED profit
            # over the harvest distribution, evaluated on the same
            # economics every policy sees.
            grid = np.linspace(0.4 * mu, 1.5 * mu, 45)
            best, best_ev = mu, -1e18
            for cand in grid:
                alloc = _allocate(float(cand), econ)
                ev = float(np.mean([_profit(alloc, float(h), econ, cfg)
                                    for h in draws[:400]]))
                if ev > best_ev:
                    best_ev, best = ev, float(cand)
            cands["stochastic"] = best

            for name, total in cands.items():
                profits[name].append(
                    _profit(_allocate(total, econ), realized, econ, cfg))

    print("\nPROJECT C — vertically integrated, commitment before harvest")
    print(f"  seasons scored: {len(profits['stochastic'])}\n")
    base = profits["expected_yield"]
    for name in policies:
        v = profits[name]
        if not v:
            continue
        edge = [(x - b) / abs(b) * 100 for x, b in zip(v, base, strict=True)
                if b != 0]
        tag = "  (baseline)" if name == "expected_yield" else ""
        print(f"  {name:16} mean profit {st.mean(v):12,.0f}"
              f"   median edge vs expected-yield "
              f"{st.median(edge) if edge else 0:+7.2f}%{tag}")
    sto, p40 = profits["stochastic"], profits["p40"]
    if sto and p40:
        e = [(s - p) / abs(p) * 100 for s, p in zip(sto, p40, strict=True)
             if p != 0]
        wins = sum(1 for x in e if x > 0)
        print("\n  THE TEST THAT MATTERS — stochastic vs the p40 rule of thumb:")
        print(f"    median {st.median(e):+.2f}%   wins {wins}/{len(e)}")
        print("    If this is near zero, a percentile rule is enough and the")
        print("    optimizer is not the product.")
    print("\n  Synthetic data. Every parameter is an assumption.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
