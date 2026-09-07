#!/usr/bin/env python3
"""New, version-frozen synthetic network evidence. Never writes v1 evidence.

Development / validation / final are separate seeds. The final command refuses
any source mismatch with its pre-registered manifest and refuses overwriting.
Every failed solve, physical failure, loss, and parameter vector is retained.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import itertools
import json
import os
from pathlib import Path
from statistics import median
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zaad.full.capital import REASONS as CAPITAL_REASONS  # noqa: E402
from zaad.full.contracts import Request  # noqa: E402
from zaad.full.demo import example  # noqa: E402
from zaad.full.replay import replay  # noqa: E402
from zaad.full.worlds import World  # noqa: E402

SEEDS = {"development": [14001], "validation": [15001, 15002], "final": [22001, 22002, 22003, 22004, 22005],
         # Demand-adaptation study (PR24 follow-up). Never reuses consumed seeds above.
         "development2": [23001], "validation2": [24001, 24002], "holdout2": [25001, 25002],
         # Service-reliability study. New seeds again; holdout3 stays frozen until a profile is promoted.
         "development3": [26001], "validation3": [27001, 27002], "holdout3": [28001, 28002],
         # Calibrated-protection cycle (v4). holdout3 is consumed; holdout4 is frozen and unrun during development.
         "development4": [29001], "validation4": [30001, 30002], "holdout4": [31001, 31002],
         # Network/recovery cycle (v5). holdout4 stays frozen and unrun; v5 may only use these two splits.
         "development5": [32001], "validation5": [33001, 33002],
         # Multi-echelon / recovery cycle (v6). holdout4 stays frozen and unrun; v6 may only use these two splits.
         "development6": [34001], "validation6": [35001, 35002],
         # Capital-efficiency / recovery cycle (v7). holdout4 stays frozen and unrun; v7 may only
         # use these two splits. No seed here appears in any split above.
         "development7": [36001], "validation7": [37001, 37002],
         # Industry-standard cycle (v8). validation7 stays untouched and unused; holdout4 stays
         # frozen. No seed here appears in any split above.
         "development8": [38001], "validation8": [39001, 39002]}
METHODS = ["base_stock", "order_up_to", "deterministic", "stochastic", "robust", "frozen_forecast", "gated"]
RELIABILITY_METHODS = ["base_stock", "stochastic", "robust", "protected", "gated_pr24", "gated_pr30", "gated"]
INVENTORY = {"low": .5, "balanced": 2., "high": 4.}
RELIABILITY_DEMANDS = ["stable", "volatile", "promotion", "increase", "decrease", "intermittent",
                       "spike", "temporary_spike", "gradual", "unknown_promotion"]
RELIABILITY_SUPPLIES = ["stable", "fill", "lead", "severe", "partial", "correlated"]
RELIABILITY_NETWORKS = ["single", "two_locations", "central_branches"]
ALTERNATIVES = ["none", "supplier", "route", "transfer", "substitution"]
RELIABILITY_TARGETS = [.9, .95, .97, .99]


def reliability_cells(random_cells: int = 30) -> list[dict]:
    """One-factor-at-a-time around a balanced centre plus a seeded random sample of the grid."""
    centre = ("balanced", "stable", "stable", "single", "none", .95)
    combos: list[tuple] = []
    for i, levels in enumerate((list(INVENTORY), RELIABILITY_DEMANDS, RELIABILITY_SUPPLIES, RELIABILITY_NETWORKS, ALTERNATIVES, RELIABILITY_TARGETS)):
        for level in levels:
            combo = list(centre)
            combo[i] = level
            if tuple(combo) not in combos:
                combos.append(tuple(combo))
    rng = np.random.default_rng(7)
    while len(combos) < len(combos) + random_cells and random_cells > 0:
        combo = (str(rng.choice(list(INVENTORY))), str(rng.choice(RELIABILITY_DEMANDS)), str(rng.choice(RELIABILITY_SUPPLIES)),
                 str(rng.choice(RELIABILITY_NETWORKS)), str(rng.choice(ALTERNATIVES)), float(rng.choice(RELIABILITY_TARGETS)))
        if combo not in combos:
            combos.append(combo)
            random_cells -= 1
    values = []
    for inventory, demand, supply, network, alternative, target in combos:
        suppliers = "correlated" if supply == "correlated" else ("independent" if alternative == "supplier" else "single")
        values.append({"family": "reliability", "target": target, "cover": INVENTORY[inventory], "inventory": inventory,
                       "demand": demand, "supply": supply, "network": network, "suppliers": suppliers,
                       "alternative": alternative, "case": "normal"})
    return [{"cell": i, **value} for i, value in enumerate(values)]


V4_METHODS = ["base_stock", "stochastic", "robust", "gated_pr24", "gated_pr30", "gated"]
V5_METHODS = ["base_stock", "gated_pr24", "gated_pr30", "gated_v4", "gated"]
V6_METHODS = ["base_stock", "echelon_base_stock", "gated_pr24", "gated_pr30", "gated_v4", "gated_v5", "gated"]
V7_METHODS = ["base_stock", "echelon_base_stock", "gated_pr24", "gated_pr30", "gated_v4", "gated_v5", "gated_v6", "gated"]
V7_SUPPLIES = ["deterioration_recovery", "closure_recovery", "false_signal"]
V6_NETWORKS = RELIABILITY_NETWORKS + ["central_two_branches"]
V4_DEMANDS = RELIABILITY_DEMANDS + ["intermittent_spiky", "promotion_recovery", "surge_recovery"]
V4_SUPPLIES = RELIABILITY_SUPPLIES + ["deterioration_recovery", "closure_recovery"]
V4_ALTERNATIVES = ALTERNATIVES + ["transfer_constrained", "shared_route"]
LONG_HORIZON = {"promotion_recovery", "surge_recovery", "deterioration_recovery", "closure_recovery", "decrease", "temporary_spike"}


def v4_cells(random_cells: int = 24) -> list[dict]:
    """Calibrated-protection matrix: the reliability OFAT set, explicit intermittent / shift /
    supply-recovery / network / disruption cells, and a seeded random sample. Recovery cells
    run a 20-period horizon so the return toward lean is observable."""
    centre = ("balanced", "stable", "stable", "single", "none", .95)
    combos: list[tuple] = []
    for i, levels in enumerate((list(INVENTORY), V4_DEMANDS, V4_SUPPLIES, RELIABILITY_NETWORKS, V4_ALTERNATIVES, RELIABILITY_TARGETS)):
        for level in levels:
            combo = list(centre)
            combo[i] = level
            if tuple(combo) not in combos:
                combos.append(tuple(combo))
    explicit = [
        ("balanced", "intermittent", "stable", "single", "transfer", .95),
        ("balanced", "intermittent", "stable", "single", "substitution", .95),
        ("balanced", "intermittent", "stable", "central_branches", "none", .95),
        ("balanced", "intermittent_spiky", "stable", "single", "transfer", .95),
        ("balanced", "intermittent_spiky", "stable", "single", "substitution", .95),
        ("high", "intermittent", "stable", "two_locations", "transfer", .9),
        ("balanced", "stable", "stable", "central_branches", "transfer_constrained", .95),
        ("balanced", "stable", "stable", "central_branches", "none", .99),
        ("balanced", "stable", "correlated", "single", "shared_route", .95),
        ("balanced", "stable", "closure_recovery", "single", "supplier", .95),
        ("balanced", "stable", "closure_recovery", "single", "none", .95),
        ("balanced", "stable", "deterioration_recovery", "single", "supplier", .95),
        ("balanced", "surge_recovery", "stable", "single", "none", .97),
        ("balanced", "promotion_recovery", "stable", "central_branches", "none", .95),
        ("low", "stable", "lead", "single", "none", .99),
        ("balanced", "stable", "stable", "single", "supplier", .9),
    ]
    for combo in explicit:
        if combo not in combos:
            combos.append(combo)
    rng = np.random.default_rng(11)
    while random_cells > 0:
        combo = (str(rng.choice(list(INVENTORY))), str(rng.choice(V4_DEMANDS)), str(rng.choice(V4_SUPPLIES)),
                 str(rng.choice(RELIABILITY_NETWORKS)), str(rng.choice(V4_ALTERNATIVES)), float(rng.choice(RELIABILITY_TARGETS)))
        if combo not in combos:
            combos.append(combo)
            random_cells -= 1
    values = []
    for inventory, demand, supply, network, alternative, target in combos:
        suppliers = "correlated" if (supply == "correlated" or alternative == "shared_route") else ("independent" if alternative == "supplier" or supply == "closure_recovery" and alternative != "none" else "single")
        values.append({"family": "reliability", "matrix": "v4", "target": target, "cover": INVENTORY[inventory], "inventory": inventory,
                       "demand": demand, "supply": supply, "network": network, "suppliers": suppliers,
                       "alternative": alternative, "case": "normal",
                       "horizon": 20 if (demand in LONG_HORIZON or supply in LONG_HORIZON) else 12})
    return [{"cell": i, **value} for i, value in enumerate(values)]


def v6_cells() -> list[dict]:
    """Multi-echelon / recovery matrix: every v4 cell unchanged (ids 0-71), then explicit cells on a
    one-central / two-branch network (independent or correlated branch demand, transfer lead 1-3
    reviews, constrained transfer capacity, branch-specific SLA, central stock sufficient or short)
    and 26-review recovery scenarios (supplier delay, route closure with alternate, promotion end,
    demand level up, demand level down, central shortage) so the unwind is observable."""
    base = v4_cells()
    for cell in base:
        cell["matrix"] = "v6"
    def two(demand="stable", supply="stable", alternative="none", target=.95, branch_sla=None, transfer_lead=1,
            transfer_capacity=50., central_cover=2., correlation="independent", inventory="balanced", horizon=12):
        return {"family": "reliability", "matrix": "v6", "target": target, "cover": INVENTORY[inventory], "inventory": inventory,
                "demand": demand, "supply": supply, "network": "central_two_branches",
                "suppliers": "independent" if alternative == "supplier" else "single", "alternative": alternative, "case": "normal",
                "horizon": horizon, "branch_sla": target if branch_sla is None else branch_sla, "transfer_lead": transfer_lead,
                "transfer_capacity": transfer_capacity, "central_cover": central_cover, "demand_correlation": correlation}
    def one(demand="stable", supply="stable", alternative="none", network="single", target=.95, horizon=26, inventory="balanced"):
        suppliers = "independent" if alternative == "supplier" else "single"
        return {"family": "reliability", "matrix": "v6", "target": target, "cover": INVENTORY[inventory], "inventory": inventory,
                "demand": demand, "supply": supply, "network": network, "suppliers": suppliers, "alternative": alternative,
                "case": "normal", "horizon": horizon}
    explicit = [
        two(),                                                   # pooling baseline: independent branches, fast transfer
        two(correlation="correlated"),                           # correlated branches: pooling is worth less
        two(transfer_lead=2), two(transfer_lead=3),              # slow transfer: more must sit local
        two(transfer_capacity=12.),                              # constrained transfer
        two(target=.99, branch_sla=.9),                          # branch-specific SLA
        two(target=.9, branch_sla=.9), two(target=.99, branch_sla=.99),
        two(inventory="high"), two(inventory="low"),
        two(central_cover=0., horizon=26),                       # central shortage -> transfer response -> recovery
        two(supply="deterioration_recovery", horizon=26),
        two(supply="closure_recovery", alternative="supplier", horizon=26),
        two(demand="promotion_recovery", horizon=26),
        two(demand="increase", horizon=26), two(demand="decrease", horizon=26),
        two(demand="volatile"), two(demand="intermittent"),
        one(supply="deterioration_recovery"),                    # normal -> supplier delay -> recovery -> long stable tail
        one(supply="closure_recovery", alternative="supplier"),  # normal -> closure -> alternate -> primary restored -> quiet tail
        one(demand="promotion_recovery"), one(demand="increase"), one(demand="decrease"),
        one(supply="deterioration_recovery", network="central_branches"),
        one(demand="temporary_spike", horizon=26),
    ]
    return base + [{"cell": len(base) + i, **value} for i, value in enumerate(explicit)]


def v7_cells() -> list[dict]:
    """Capital-efficiency / recovery matrix: every v6 cell unchanged (ids 0-96), then the v7 cells.

    Fast-arc pooling cells vary the transfer lead and capacity on a one-central / two-branch network
    so the pooling question is asked directly: with a one-review arc most of the branch buffer can
    sit at the origin, with a three-review arc almost none of it can. (Transfer.lead_periods is at
    least one review by contract, so a genuinely same-review arc cannot be expressed; the one-review
    arc is the fastest the model allows and is used as the fast case.)

    Recovery scenarios A-G run 26-32 reviews so the peak, the unwind and a long quiet tail are all
    inside the window and the return to LEAN is observable rather than truncated.
    """
    base = v6_cells()
    for cell in base:
        cell["matrix"] = "v7"
    def two(demand="stable", supply="stable", alternative="none", target=.95, branch_sla=None, transfer_lead=1,
            transfer_capacity=50., central_cover=2., correlation="independent", inventory="balanced", horizon=12):
        return {"family": "reliability", "matrix": "v7", "target": target, "cover": INVENTORY[inventory], "inventory": inventory,
                "demand": demand, "supply": supply, "network": "central_two_branches",
                "suppliers": "independent" if alternative == "supplier" else "single", "alternative": alternative, "case": "normal",
                "horizon": horizon, "branch_sla": target if branch_sla is None else branch_sla, "transfer_lead": transfer_lead,
                "transfer_capacity": transfer_capacity, "central_cover": central_cover, "demand_correlation": correlation}
    def one(demand="stable", supply="stable", alternative="none", network="single", target=.95, horizon=30, inventory="balanced"):
        return {"family": "reliability", "matrix": "v7", "target": target, "cover": INVENTORY[inventory], "inventory": inventory,
                "demand": demand, "supply": supply, "network": network,
                "suppliers": "independent" if alternative == "supplier" else "single", "alternative": alternative,
                "case": "normal", "horizon": horizon}
    explicit = [
        # P2 fast-arc pooling: the same network at three arc speeds and two capacities.
        two(transfer_lead=1, transfer_capacity=50.), two(transfer_lead=2, transfer_capacity=50.), two(transfer_lead=3, transfer_capacity=50.),
        two(transfer_lead=1, transfer_capacity=15.), two(transfer_lead=3, transfer_capacity=15.),
        two(transfer_lead=1, correlation="correlated"), two(transfer_lead=3, correlation="correlated"),
        two(transfer_lead=1, central_cover=0.), two(transfer_lead=1, inventory="high"),
        two(transfer_lead=1, demand="volatile"), two(transfer_lead=1, demand="intermittent"),
        # A stable -> supplier delay -> recovery -> long stable tail
        one(supply="deterioration_recovery", horizon=30), one(supply="deterioration_recovery", horizon=30, network="central_branches"),
        # B route closure -> reopening -> stable tail
        one(supply="closure_recovery", alternative="supplier", horizon=30), one(supply="closure_recovery", horizon=30),
        # C promotion -> end -> stable tail
        one(demand="promotion_recovery", horizon=28), two(demand="promotion_recovery", horizon=28),
        # D demand surge -> normalization
        one(demand="surge_recovery", horizon=28), one(demand="temporary_spike", horizon=28),
        # E demand decline -> new lower stable level
        one(demand="decrease", horizon=30), two(demand="decrease", horizon=30), two(demand="decrease", horizon=30, transfer_lead=3),
        # F central/branch disruption -> pooled recovery
        two(supply="closure_recovery", alternative="supplier", central_cover=0., horizon=30),
        two(supply="deterioration_recovery", horizon=30),
        # G one false risk signal -> return to lean
        one(supply="false_signal", horizon=26), two(supply="false_signal", horizon=26),
        one(supply="false_signal", horizon=26, network="central_branches"),
    ]
    return base + [{"cell": len(base) + i, **value} for i, value in enumerate(explicit)]


def cells(matrix="coverage"):
    if matrix == "reliability":
        return reliability_cells()
    if matrix == "v4":
        return v4_cells()
    if matrix == "v6":
        return v6_cells()
    if matrix == "v7":
        return v7_cells()
    values = []
    targets_ = [.9, .93, .95, .97, .98, .99, .995]
    stock = [.1, 1., 2., 4., 7.]
    demands = ["stable", "seasonal", "intermittent", "promotion", "increase", "decrease"]
    supplies = ["stable", "fill", "lead", "long"]
    networks = ["single", "two_locations", "central_branches"]
    suppliers = ["single", "independent", "correlated"]
    if matrix == "full":
        normal = itertools.product(targets_, stock, demands, supplies, networks, suppliers)
    else:
        normal = list(itertools.product(targets_, stock, ["stable"], ["stable"], ["single"], ["single"]))
        normal += [( .95, 2., demand, supply, networks[(i + j) % 3], suppliers[(i + 2*j) % 3])
                   for i, demand in enumerate(demands) for j, supply in enumerate(supplies)]
    for target, cover, demand, supply, network, supplier in normal:
        values.append({"family": "normal", "target": target, "cover": cover, "demand": demand,
                       "supply": supply, "network": network, "suppliers": supplier, "case": "normal"})
    disruption = ["none", "early", "mild", "moderate", "severe", "partial_closure", "supplier_outage",
                  "shared_outage", "alternative", "no_alternative", "delayed_recovery", "false_alarm",
                  "physical_before_news", "news_before_physical", "correlated", "freight_spike", "cash_crisis"]
    for kind in disruption:
        values.append({"family": "disruption", "target": .95, "cover": 2., "demand": "stable", "supply": "stable",
                       "network": "single", "suppliers": "independent" if kind == "alternative" else "single", "case": kind})
    for extra_lead, fill, recovery in [(3, .8, 7), (4, .7, 7), (6, .5, 9), (2, .9, 9), (4, .8, 9)]:
        values.append({"family": "misspecification", "target": .95, "cover": 2., "demand": "stable", "supply": "stable",
                       "network": "single", "suppliers": "correlated", "case": "misspecified",
                       "truth_extra_lead": extra_lead, "truth_fill": fill, "truth_recovery": recovery})
    for kind in ["transfer", "substitution", "recovery", "cash"]:
        values.append({"family": "action", "target": .95, "cover": 2., "demand": "stable", "supply": "stable", "network": "single", "suppliers": "single", "case": kind})
    return [{"cell": i, **value} for i, value in enumerate(values)]


def request_for(cell, seed):
    case = cell["case"] if cell["family"] == "action" else "normal"
    req = example(case, seed)
    data = req.model_dump(mode="json")
    H = int(cell.get("horizon", 12))
    data["horizon"], data["scenarios"], data["max_solve_seconds"] = H, 3, 5.
    data["liquidity"]["known_receivables"] = [0.] * H
    data["liquidity"]["other_payments"] = [0.] * H
    data["liquidity"]["opening_cash"] = 10000. if cell["case"] not in {"cash", "cash_crisis"} else 350.
    if cell["case"] == "cash_crisis":
        data["liquidity"]["credit_limit"] = 0.
        data["terms"][0]["deposit_fraction"] = 1.
    for source in data["sources"]:
        source["capacity_by_period"] = [100.] * H
        source["lead_days"] = 21 if cell["supply"] == "long" else 7
        source["fill_mean"] = .85 if cell["supply"] == "fill" else .97
        source["fill_sd"] = .08 if cell["supply"] == "fill" else .01
        source["lead_sd_days"] = 7. if cell["supply"] == "lead" else 0.
        if cell["case"] == "freight_spike":
            source["freight_per_unit"] = 2.
    alternative = cell.get("alternative", "none")
    # shared_route: the correlated alternate (same port failure domain) is added by the suppliers block above.
    if alternative == "route":
        # Same supplier, a second approved itinerary through another port on its own capacity.
        route = {**data["sources"][0], "id": "alternate_route", "route": ["supplier", "other_port", "branch"],
                 "resources": ["alternate_route_capacity"], "freight_per_unit": data["sources"][0]["freight_per_unit"] + 1.,
                 "capacity_by_period": [50.] * H}
        data["sources"].append(route)
        data["resources"].append({"id": "alternate_route_capacity", "known_at": data["as_of"], "capacity_by_period": [50.] * H,
                                  "failure_domains": ["other_port"]})
    for resource in data["resources"]:
        resource["capacity_by_period"] = [100.] * H
    if cell["suppliers"] != "single":
        source = {**data["sources"][0], "id": "alternate", "supplier": "alternate_supplier",
                  "route": ["alternate_supplier", "other_port", "branch"], "unit_price": 5.5,
                  "resources": ["alternate_capacity"], "capacity_by_period": [50.] * H}
        data["sources"].append(source)
        data["resources"].append({"id": "alternate_capacity", "known_at": data["as_of"], "capacity_by_period": [50.] * H,
                                  "failure_domains": ["port"] if cell["suppliers"] == "correlated" else ["other_port"]})
    network = cell["network"]
    if network == "single" and alternative in {"transfer", "transfer_constrained"}:
        network = "two_locations"
    if network == "central_two_branches":
        # One central DC fed by the supplier(s); two branches each served only by transfer from it.
        lead, capacity = int(cell.get("transfer_lead", 1)), float(cell.get("transfer_capacity", 50.))
        data["locations"].append({**data["locations"][0], "id": "central", "kind": "central_dc", "holding_per_value_period": .003})
        data["locations"].append({**data["locations"][0], "id": "branch_south"})
        data["customers"].append({**data["customers"][0], "id": "customer_south"})
        data["services"].append({**data["services"][0], "id": "retail_A_south", "location": "branch_south", "customer": "customer_south",
                                 "target": float(cell.get("branch_sla", cell["target"]))})
        data["stock"].append({**data["stock"][0], "id": "opening_south", "location": "branch_south"})
        data["stock"].append({**data["stock"][0], "id": "central_pool", "location": "central", "quantity": float(cell.get("central_cover", 2.)) * 40.})
        for branch in ("branch", "branch_south"):
            data["transfers"].append({"id": f"central_{branch}", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": branch,
                                      "lead_periods": lead, "capacity": capacity, "cost_per_unit": .2, "loss_fraction": .01, "approved": True})
        for source in data["sources"]:
            source["destination"] = "central"
            source["route"][-1] = "central"
    elif network != "single":
        data["locations"].append({**data["locations"][0], "id": "central", "kind": "central_dc", "holding_per_value_period": .003})
        data["stock"].append({**data["stock"][0], "id": "central_excess", "location": "central", "quantity": 80.})
        data["transfers"].append({"id": "central_branch", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": "branch",
                                  "lead_periods": 1, "capacity": 50., "cost_per_unit": .2, "loss_fraction": .01, "approved": True})
        if network == "central_branches":
            data["sources"][0]["destination"] = "central"
            data["sources"][0]["route"][-1] = "central"
        if alternative == "transfer_constrained":
            data["transfers"][-1]["capacity"] = 12.
    if alternative == "substitution":
        data["skus"].append({**data["skus"][0], "id": "B", "asset_value": 4., "terminal_value": 3.})
        data["stock"].append({**data["stock"][0], "id": "sub_stock", "sku": "B", "quantity": 60.})
        data["substitutions"].append({"id": "approved_B_for_A", "known_at": data["as_of"], "supplied_sku": "B", "requested_sku": "A",
            "customers": ["customer"], "channels": ["retail"], "input_per_output": 1., "penalty_per_output": .1,
            "service_equivalence": 1., "approved": True, "brand_approval_reference": "fixture", "cannibalization_assumption": "none"})
    if cell["family"] != "action":
        for lot in data["stock"]:
            if lot["id"] in {"opening", "opening_south"}:
                lot["quantity"] = cell["cover"] * 20
    data["services"][0]["target"] = cell["target"]
    data["demand_adaptation"] = cell.get("adaptation", "symmetric")
    rng = np.random.default_rng(seed + 210000)
    history = []
    for period in range(-78, 0):
        mu = 20 * (1 + .3 * np.sin(2 * np.pi * period / 26)) if cell["demand"] == "seasonal" else 20.
        q = max(0., rng.normal(mu, 6. if cell["demand"] == "volatile" else 2))
        if cell["demand"] == "intermittent":
            q = q * 2 if rng.random() < .5 else 0.
        if cell["demand"] == "intermittent_spiky":
            # Sparse usage: one period in four, with one historical spike three times the usual size.
            q = q * 4 if rng.random() < .25 else 0.
            if period == -30:
                q = 20 * 12.
        history.append({"known_at": data["as_of"], "service": "retail_A", "period": period, "quantity": q})
    if network == "central_two_branches":
        south = np.random.default_rng(seed + 220000)
        for period in range(-78, 0):
            q = max(0., south.normal(20., 6. if cell["demand"] == "volatile" else 2))
            if cell["demand"] == "intermittent":
                q = q * 2 if south.random() < .5 else 0.
            history.append({"known_at": data["as_of"], "service": "retail_A_south", "period": period, "quantity": q})
    data["history"] = history
    if cell["demand"] in {"promotion", "promotion_recovery"}:
        data["events"] = [{"id": "promotion", "known_at": data["as_of"], "service": "retail_A", "start": 3, "end": 5, "multiplier": 1.8, "label": "known promotion"}]
    # Estimated stress differs deliberately from final realized severity/recovery.
    data["stresses"] = [{"name": "operator_adverse", "fill_multiplier": .7, "extra_lead_days": 28,
                         "demand_multiplier": 1.1, "recovery_period": 9, "shared_failure": True,
                         "affected_resources": ["port_cap"]}]
    if cell["family"] == "reliability":
        data["engine_profile"] = cell.get("engine_profile", "reliability")
    return Request.model_validate(data)


def truth_for(req, cell, seed):
    """Separate generator, not the fitted/bootstrap scenario model."""
    rng = np.random.default_rng(seed + 410000)
    H = req.horizon
    demand = []
    # Second branch (v6): its own Poisson draws, or a shared multiplicative shock when the cell
    # declares correlated branch demand, on the same level path as the first branch.
    south_rng = np.random.default_rng(seed + 420000)
    shared = rng.normal(size=H) if cell.get("demand_correlation") == "correlated" else None
    demand_south = []
    for t in range(H):
        mu = 20 * (1 + .3 * np.sin(2 * np.pi * t / 26)) if cell["demand"] == "seasonal" else 20.
        if cell["demand"] == "promotion" and 3 <= t <= 5:
            mu *= 1.8
        if cell["demand"] in {"increase", "decrease"} and t >= 3:
            mu *= 1.8 if cell["demand"] == "increase" else .35
        if cell["demand"] == "unknown_promotion" and 3 <= t <= 5:
            mu *= 1.8          # no event declared: the planner must detect it
        if cell["demand"] == "spike" and t == 4:
            mu *= 3.           # one abnormal week; a level reset here is panic buying
        if cell["demand"] == "temporary_spike" and 4 <= t <= 5:
            mu *= 2.
        if cell["demand"] == "gradual":
            mu *= 1 + .05 * t
        if cell["demand"] == "promotion_recovery" and 3 <= t <= 5:
            mu *= 1.8          # declared promotion, then a long normal tail
        if cell["demand"] == "surge_recovery" and 3 <= t <= 8:
            mu *= 1.8          # undeclared six-period surge, then normal
        if shared is not None:
            mu *= float(np.exp(.25 * shared[t] - .03))          # common shock on both branches
        if cell["demand"] == "volatile":
            q = float(rng.negative_binomial(4, 4 / (4 + mu)))   # mean mu, variance mu + mu^2/4
        else:
            q = float(rng.poisson(mu))
        if cell["demand"] == "intermittent":
            q = 2 * q if rng.random() < .5 else 0.
        if cell["demand"] == "intermittent_spiky":
            q = 4 * q if rng.random() < .25 else 0.
        demand.append(q)
        if any(s.id == "retail_A_south" for s in req.services):
            mu_s = mu
            qs = float(south_rng.negative_binomial(4, 4 / (4 + mu_s))) if cell["demand"] == "volatile" else float(south_rng.poisson(mu_s))
            if cell["demand"] == "intermittent":
                qs = 2 * qs if south_rng.random() < .5 else 0.
            demand_south.append(qs)
    arrivals, fills = {}, {}
    kind = cell["case"]
    supply = cell["supply"]
    reliability = cell["family"] == "reliability"
    shock = (supply in {"severe", "partial", "correlated", "deterioration_recovery", "closure_recovery", "false_signal"}) if reliability else kind not in {"normal", "none", "false_alarm", "transfer", "substitution", "recovery", "cash"}
    recovery = cell.get("truth_recovery", 9 if kind == "delayed_recovery" else 7)
    extra = cell.get("truth_extra_lead", 6 if kind in {"severe", "shared_outage"} or supply == "severe" else (0 if supply == "partial" else 3))
    floor = cell.get("truth_fill", .5 if kind in {"severe", "supplier_outage"} or supply == "severe" else (.6 if supply == "partial" else .8))
    if reliability and supply == "partial":
        recovery = H       # partial deliveries for the whole horizon, on time
    if reliability and supply == "deterioration_recovery":
        recovery, extra, floor = 8, 2, .85      # late and short from period 1 to 7, then clean
    if reliability and supply == "closure_recovery":
        recovery, extra, floor = 6, 10, .0      # main route closed from period 1 to 5, then restored
    if reliability and supply == "false_signal":
        recovery, extra, floor = 2, 4, .6       # one late and short receipt at period 1, clean ever after
    shared = rng.normal(size=H)
    for source in req.sources:
        for t in range(H):
            z = shared[t] if cell["suppliers"] == "correlated" else rng.normal()
            fill = float(np.clip(source.fill_mean + source.fill_sd * z, 0, 1))
            lead = max(1, round(source.lead_days / req.period_days + abs(rng.normal()) * source.lead_sd_days / req.period_days))
            affected = shock and 1 <= t < recovery and (source.id == "main" or kind in {"shared_outage", "correlated"} or supply == "correlated"
                                                          or (cell.get("alternative") == "shared_route"))
            if affected:
                fill *= floor
                lead += extra
            arrivals[source.id, t], fills[source.id, t] = t + lead, fill
    truth_demand = {"retail_A": tuple(demand)}
    if demand_south:
        truth_demand["retail_A_south"] = tuple(demand_south)
    return World(f"independent_truth:{seed}:{cell['cell']}", 1., truth_demand, arrivals, fills,
                 {p.id: next(o.due_in for o in p.options if o.action == "keep") for p in req.pipeline},
                 {p.id: p.expected_accepted_remaining / p.remaining for p in req.pipeline})


def v6_metrics(req, rows) -> dict:
    """Multi-echelon / recovery metrics (v6) from the replay log: echelon accounting means, duplicated
    buffer units, procurement timing, recovery exit, and a compact per-review network trace
    (on hand per location, transfers, unmet, remaining planning horizon)."""
    states = [p for r in rows for p in (r.get("protection") or [])]
    echelon_keys = ("local_service_units", "pooled_network_units", "source_protection_units", "temporary_risk_units")
    echelon = {k: float(np.mean([p["echelon"][k] for p in states if p.get("echelon")])) if any(p.get("echelon") for p in states) else None for k in echelon_keys}
    duplicated = [p.get("duplicated_buffer_units", 0.) for p in states]
    timing = [x for r in rows for x in (r.get("procurement_timing") or [])]
    reviews_to_lean = [p["exit"]["reviews_remaining_until_lean_eligible"] for p in states if p.get("exit")]
    trace = []
    for n, r in enumerate(rows):
        end = r["settlement"].get("end_stock") or []
        on_hand = {}
        for row in end:
            on_hand[row["location"]] = on_hand.get(row["location"], 0.) + row["quantity"]
        unmet = sum(s["demand"] - s["served"] for s in r["settlement"]["service_by_period"])
        trace.append({"review": n, "on_hand": {k: round(v, 1) for k, v in on_hand.items()}, "transfer_spend": round(r["settlement"]["ledger"].get("transfer", 0.), 2),
                      "unmet": round(unmet, 1), "remaining_horizon": req.horizon - n})
    return {"echelon_mean": echelon, "duplicated_buffer_units_mean": float(np.mean(duplicated)) if duplicated else None,
            "duplicated_buffer_reviews": int(sum(1 for d in duplicated if d > 0)),
            "early_periods_mean": float(np.mean([x["early_periods"] for x in timing])) if timing else None,
            "cash_committed_early_total": float(sum(x["cash_committed_early"] for x in timing)) if timing else None,
            "reviews_to_lean_eligible_median": float(np.median(reviews_to_lean)) if reviews_to_lean else None,
            "network_trace": trace}


def v7_metrics(req, rows) -> dict:
    """Capital-efficiency metrics (v7). The reason categories partition on-hand exactly, so their
    means sum to mean inventory; `duplicated_buffer_units_v7` is the explicit pairwise detector,
    reported next to the v6 number rather than replacing it. Recovery is reported twice: over every
    protection row, and over service-bearing rows only, so the figure stays comparable with V5/V6,
    which had no echelon-origin rows at all."""
    capital = [c for r in rows for c in ((r.get("capital") or {}).get("decomposition") or [])]
    dup = [d for r in rows for d in ((r.get("capital") or {}).get("duplication") or [])]
    pool = [x for r in rows for x in ((r.get("capital") or {}).get("pooling") or [])]
    timing = [x for r in rows for x in (r.get("procurement_timing") or [])]
    states = [p for r in rows for p in (r.get("protection") or [])]
    service_states = [p for p in states if not p.get("echelon_origin")]
    reasons = {}
    if capital:
        for key in CAPITAL_REASONS:
            reasons[key] = float(np.mean([c["reason"].get(key, 0.) for c in capital]) * len({c["location"] for c in capital}))
    def lean_share(rows_):
        return (float(np.mean([p["regime"] == "LEAN" for p in rows_])) if rows_ else None)
    return {
        "capital_reason_units_mean": reasons or None,
        "capital_unexplained_share": (float(np.sum([c["reason"]["unexplained"] for c in capital])
                                            / max(1e-9, np.sum([c["on_hand_units"] for c in capital]))) if capital else None),
        "capital_stale_protection_share": (float(np.sum([c["reason"]["stale_protection"] for c in capital])
                                                 / max(1e-9, np.sum([c["on_hand_units"] for c in capital]))) if capital else None),
        "capital_reconciles": (bool(all(c["reconciles"] for c in capital)) if capital else None),
        "duplicated_buffer_units_v7_mean": (float(np.mean([d["duplicated_buffer_units"] for d in dup])) if dup else None),
        "duplicated_buffer_arc_reviews_v7": int(sum(1 for d in dup if d["duplicated_buffer_units"] > 0)),
        "pooling_local_immediate_mean": (float(np.mean([x["local_immediate_units"] for x in pool])) if pool else None),
        "pooling_pooled_mean": (float(np.mean([x["pooled_units"] for x in pool])) if pool else None),
        "pooling_excess_over_local_mean": (float(np.mean([x["excess_over_local_immediate"] for x in pool])) if pool else None),
        "premature_purchase_units": (float(sum(x.get("premature_units", 0.) for x in timing)) if timing else None),
        "premature_inventory_days": (float(sum(x.get("premature_inventory_days", 0.) for x in timing)) if timing else None),
        "cash_days_advanced": (float(sum(x.get("cash_days_advanced", 0.) for x in timing)) if timing else None),
        "lean_share_all_rows": lean_share(states),
        "lean_share_service_rows": lean_share(service_states),
        "echelon_origin_rows": int(sum(1 for p in states if p.get("echelon_origin")))}


def v8_solver_metrics(rows) -> dict:
    """Solver profile per replay (v8). Reported so pathological cells are visible in the evidence
    rather than only in wall time: how many candidate solves ran, how many stopped at the wall-clock
    cap, the worst achieved optimality gap, and whether the selected plan was economically
    comparable at all. None of this changes a decision; it describes one."""
    per_review = [r.get("solve_quality") for r in rows if r.get("solve_quality")]
    gaps, capped, solves, incomparable, not_optimal, selected_bad = [], 0, 0, 0, 0, 0
    for quality in per_review:
        for row in (quality.get("candidates") or {}).values():
            solves += 1
            gap, seconds = row.get("achieved_gap"), row.get("solve_seconds")
            if isinstance(gap, (int, float)) and np.isfinite(gap):
                gaps.append(float(gap))
            if isinstance(seconds, (int, float)) and seconds >= 4.9:
                capped += 1
            if row.get("economically_comparable") is False:
                # Two different exclusions, kept apart: a candidate the solver could not optimise
                # inside its budget, and a candidate that is not a usable plan at all.
                if row.get("status") == "OPTIMAL":
                    incomparable += 1
                else:
                    not_optimal += 1
        if quality.get("selected_is_comparable") is False:
            selected_bad += 1
    single = [r["solver"] for r in rows if r.get("solver")]
    single_gaps = [x["gap"] for x in single if isinstance(x.get("gap"), (int, float)) and np.isfinite(x["gap"])]
    return {
        "solver_candidate_solves": solves or (len(single) or None),
        "solver_solves_at_time_cap": capped or None,
        "solver_worst_gap": (float(max(gaps)) if gaps else (float(max(single_gaps)) if single_gaps else None)),
        "solver_median_gap": (float(np.median(gaps)) if gaps else (float(np.median(single_gaps)) if single_gaps else None)),
        "solver_undersolved_candidates": incomparable or None,
        "solver_non_optimal_candidates": not_optimal or None,
        "solver_reviews_with_incomparable_selection": selected_bad or None,
        "solver_reviews_profiled": len(per_review) or None,
        # Gated methods synthesise their Solution in replay.choose, so the model size lives on the
        # per-candidate rows rather than on the returned solution; report whichever is present and
        # never emit a NaN, which the evidence writer rejects.
        "solver_mean_variables": _mean_or_none([x["variables"] for x in single if x.get("variables")]
                                               or [row.get("variables") for quality in per_review
                                                   for row in (quality.get("candidates") or {}).values()])}


def _mean_or_none(values):
    usable = [float(v) for v in values if isinstance(v, (int, float)) and np.isfinite(v)]
    return float(np.mean(usable)) if usable else None


def task(args):
    cell, seed, method = args[:3]
    overrides = args[3] if len(args) > 3 else {}
    req = request_for(cell, seed)
    if overrides:
        # Solver settings are part of the cache key, so they must actually reach the request.
        req = req.model_copy(update={k: v for k, v in overrides.items() if v is not None})
    truth = truth_for(req, cell, seed)
    started = time.monotonic()
    result = replay(req, truth, req.horizon, method)
    rows = result["reviews"]
    d = sum(s["demand"] for r in rows for s in r["settlement"]["service_by_period"])
    served = sum(s["served"] for r in rows for s in r["settlement"]["service_by_period"])
    return {**cell, "seed": seed, "method": method, "status": result["status"], "cost": result.get("economic_cost"),
            **reliability_metrics(req, truth, rows, cell),
            "service": served / d if d else None, "completed_reviews": len(rows), "service_breach": bool(d and served / d < cell["target"] - 1e-6),
            "recovery_solves": sum(bool(r["warnings"]) for r in rows), "failure": result.get("failure"),
            "ledger": result.get("ledger"), "seconds": time.monotonic() - started,
            "forecast_methods": [r["forecast"]["retail_A"]["method"] for r in rows],
            "review_status": [r["warnings"][0] if r["warnings"] else None for r in rows],
            "review_policy": [r["warnings"][1] if len(r["warnings"]) > 1 else None for r in rows],
            "review_mode": [next((w[5:] for w in r["warnings"] if isinstance(w, str) and w.startswith("mode=")), None) for r in rows],
            # Protection trajectory per review (gated methods): regime, activity, recommended and lean units, on hand.
            "protection_trajectory": [[{k: p[k] for k in ("regime", "activity", "protection_units", "lean_baseline_units", "on_hand_units", "periods_to_lean")}
                                       for p in (r.get("protection") or [])] for r in rows] if any(r.get("protection") for r in rows) else None,
            **v6_metrics(req, rows),
            **v7_metrics(req, rows),
            **v8_solver_metrics(rows),
            "change_origins": [r["forecast"]["retail_A"]["segment_origin"] for r in rows],
            "min_cash": min((x["cash"] for r in rows for x in r["settlement"]["trace"]), default=None),
            "max_debt": max((x["debt"] for r in rows for x in r["settlement"]["trace"]), default=None),
            "closing_inventory": rows[-1]["settlement"]["trace"][-1]["inventory_value"] if rows else None}


def reliability_metrics(req, truth, rows, cell) -> dict:
    """Service-reliability measurements per replay, kept apart from economic savings."""
    if not rows:
        return {"stockout_periods": None, "recovery_periods": None, "inventory_periods": None, "working_capital": None,
                "emergency_reviews": None, "model_failure": None}
    served_rows = [(s["demand"], s["served"]) for r in rows for s in r["settlement"]["service_by_period"]]
    served = served_rows
    stockouts = [i for i, (d, v) in enumerate(served) if v < d - 1e-9]
    recovery = None
    if stockouts:
        first = stockouts[0]
        later = [i for i, (d, v) in enumerate(served) if i > first and v >= d - 1e-9]
        recovery = (later[0] - first) if later else None
    asset = req.skus[0].asset_value
    mean_demand = max(1e-9, sum(d for d, _ in served) / len(served))
    inventory = [x["inventory_value"] for r in rows for x in r["settlement"]["trace"]]
    primary = req.sources[0].id
    emergency = sum(1 for r in rows if r["settlement"]["ledger"].get("transfer", 0.) > 0
                    or any(p["source"] != primary and p["quantity"] > 0 for p in r["purchases"]))
    # Ex-post model failure: realized demand far outside the review's own forecast spread, or
    # realized supply far outside the declared fill/lead, on at least two reviews.
    demand_misses, supply_misses = 0, 0
    for t, r in enumerate(rows):
        f = r["forecast"]["retail_A"]
        if truth.demand["retail_A"][t] > f["mean"] + 3 * max(f["sd"], 1.):
            demand_misses += 1
        for source in req.sources:
            if truth.fills[source.id, t] < source.fill_mean - 3 * source.fill_sd - .05 or truth.arrival[source.id, t] - t > source.lead_days / req.period_days + 2:
                supply_misses += 1
                break
    # Purchased versus inherited stock: what the planner bought over the replay against what the
    # fixture handed it (branch, central and substitute stock), so an inventory figure can be read
    # as protection bought rather than stock inherited.
    purchased = sum(p["quantity"] for r in rows for p in r["purchases"])
    served_units = sum(v for _, v in served_rows)
    inherited = sum(x.usable for x in req.stock)
    transferred = sum(r["settlement"]["ledger"].get("transfer", 0.) for r in rows)
    return {"stockout_periods": len(stockouts), "recovery_periods": recovery,
            "purchased_units": purchased, "served_units": served_units, "inherited_units": inherited,
            "purchase_to_demand_ratio": purchased / max(1e-9, sum(d for d, _ in served_rows)),
            "transfer_spend": transferred,
            "inventory_periods": float(np.mean(inventory) / (mean_demand * asset)),
            "inventory_units_mean": float(np.mean(inventory) / asset),
            "forecast_mean_demand": float(np.mean([r["forecast"]["retail_A"]["mean"] for r in rows])),
            "inventory_periods_of_forecast": float(np.mean(inventory) / (asset * max(1e-9, np.mean([r["forecast"]["retail_A"]["mean"] for r in rows])))),
            "inventory_turn_periods": float(np.mean(inventory) / asset / max(1e-9, purchased / max(1, len(rows)))),
            "working_capital": float(np.mean(inventory)), "emergency_reviews": emergency,
            "model_failure": {"demand": demand_misses >= 2, "supply": supply_misses >= 2},
            "benign": cell.get("supply") == "stable" and cell.get("demand") in {"stable", "seasonal"} and cell.get("case") in {"normal", "none"}}


def source_hash():
    paths = sorted((ROOT / "zaad/full").glob("*.py")) + [Path(__file__)]
    return hashlib.sha256(b"".join(p.relative_to(ROOT).as_posix().encode() + p.read_bytes() for p in paths)).hexdigest()


def task_key(cell, seed, method, source, solver) -> str:
    """Exact-result cache key. Any difference that could change the row must change the key: the
    engine source, the full cell definition, the seed, the method and the solver settings. A hit is
    therefore a rerun of identical work, never a stale reuse across a behavioural change."""
    payload = {"source_hash": source, "cell": cell, "seed": seed, "method": method, "solver": solver}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def load_cache(path: Path) -> dict:
    if not path or not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue                      # a torn final line from an interrupted run
        if isinstance(entry, dict) and "key" in entry and "row" in entry:
            out[entry["key"]] = entry["row"]
    return out


def completed_keys(path: Path) -> dict:
    """Rows already written by an interrupted run of the same output file, by cache key."""
    if not path.exists():
        return {}
    done = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("task_key"):
            done[row["task_key"]] = row
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=list(SEEDS), default="development")
    parser.add_argument("--matrix", choices=["coverage", "full", "reliability", "v4", "v6", "v7"], default="coverage")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--adaptation", choices=["symmetric", "asymmetric", "soft", "ensemble"], default="symmetric")
    parser.add_argument("--methods", nargs="+", default=None, help="subset of METHODS")
    parser.add_argument("--demand", nargs="+", default=None, help="only cells with these demand patterns")
    parser.add_argument("--family", nargs="+", default=None, help="only cells of these families")
    parser.add_argument("--target", nargs="+", type=float, default=None, help="only cells with these service targets")
    parser.add_argument("--supply", nargs="+", default=None, help="only cells with these supply patterns")
    parser.add_argument("--network", nargs="+", default=None, help="only cells with these networks")
    parser.add_argument("--cells", nargs="+", type=int, default=None, help="only these cell ids")
    parser.add_argument("--cache", type=Path, default=None,
                        help="exact-result cache file; a hit is reused only when engine source, cell, seed, method and solver settings all match")
    parser.add_argument("--resume", action="store_true",
                        help="continue an interrupted run of the same --output, skipping rows already written")
    parser.add_argument("--mip-gap", type=float, default=None, help="override the solver optimality gap (recorded in the manifest)")
    parser.add_argument("--comparable-gap", type=float, default=None, help="override the solve-quality comparability threshold")
    args = parser.parse_args()
    manifest = args.output.parent / "preregistered.json"
    configuration = {"source_hash": source_hash(), "seeds": SEEDS, "methods": METHODS,
                     "matrix": args.matrix, "cells": cells(args.matrix),
                     "gated_controller_included": True,
                     "scope": "rolling policy comparison including gated controller; not real-operator validation"}
    if args.freeze:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x") as f:
            json.dump(configuration, f, indent=2)
        print("FROZEN", configuration["source_hash"], flush=True)
        return
    if args.split in {"final", "holdout3", "holdout4"}:
        # Frozen splits: the manifest written by --freeze must match the current source and
        # configuration exactly, and no cell subset or limit may be applied.
        if args.limit or args.demand or args.family or args.target or args.supply or args.network or args.cells or not manifest.exists() or json.loads(manifest.read_text()) != configuration:
            raise SystemExit(f"{args.split} requires an exact frozen source/configuration, no filters and no run limit")
    if args.output.exists() and not args.resume:
        raise SystemExit("Refusing to overwrite evidence (pass --resume to continue an interrupted run)")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    selected = configuration["cells"][:args.limit] if args.limit else configuration["cells"]
    if args.demand:
        selected = [c for c in selected if c["demand"] in args.demand]
    if args.family:
        selected = [c for c in selected if c["family"] in args.family]
    if args.target:
        selected = [c for c in selected if any(abs(c["target"] - t) < 1e-9 for t in args.target)]
    if args.supply:
        selected = [c for c in selected if c["supply"] in args.supply]
    if args.network:
        selected = [c for c in selected if c["network"] in args.network]
    if args.cells:
        selected = [c for c in selected if c["cell"] in args.cells]
    selected = [{**c, "adaptation": args.adaptation} for c in selected]
    methods = args.methods or (RELIABILITY_METHODS if args.matrix == "reliability" else V4_METHODS if args.matrix == "v4" else METHODS)
    if args.split in {"development5", "validation5"} and not args.methods:
        methods = V5_METHODS
    if args.split in {"development6", "validation6"} and not args.methods:
        methods = V6_METHODS
    if args.split in {"development7", "validation7"} and not args.methods:
        methods = V7_METHODS
    solver_settings = {"mip_gap": args.mip_gap, "comparable_gap": args.comparable_gap,
                       "max_solve_seconds": None, "workers": args.workers}
    overrides = {"solver_mip_gap": args.mip_gap, "comparable_gap": args.comparable_gap}
    overrides = {k: v for k, v in overrides.items() if v is not None}
    tasks = [(c, s, m, overrides) for c in selected for s in SEEDS[args.split] for m in methods]
    keys = [task_key(c, s, m, configuration["source_hash"], solver_settings) for c, s, m, _ in tasks]
    cache = load_cache(args.cache)
    done = completed_keys(args.output) if args.resume else {}
    pending = [(i, t) for i, t in enumerate(tasks) if keys[i] not in done and keys[i] not in cache]
    reused = len(tasks) - len(pending)
    if reused:
        print(f"reusing {reused} of {len(tasks)} rows "
              f"({len(done)} already written, {sum(1 for i in range(len(tasks)) if keys[i] in cache and keys[i] not in done)} from cache)", flush=True)
    # Out-of-order writes: a completed worker persists immediately instead of waiting for its turn
    # in submission order, so an interrupted run loses only the work still in flight and the file
    # never appears frozen behind one slow cell. Deterministic order is restored on read via
    # task_index, which every row carries.
    with args.output.open("a" if args.resume else "x") as file, ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(task, t): i for i, t in pending}
        written = 0
        for future in as_completed(futures):
            index = futures[future]
            row = {**future.result(), "task_index": index, "task_key": keys[index]}
            file.write(json.dumps(row, allow_nan=False) + "\n")
            file.flush()
            os.fsync(file.fileno())
            if args.cache:
                args.cache.parent.mkdir(parents=True, exist_ok=True)
                with args.cache.open("a") as store:
                    store.write(json.dumps({"key": keys[index], "row": row}, allow_nan=False) + "\n")
            written += 1
            if written % 25 == 1 or written == len(pending):
                print(f"{written}/{len(pending)} solved ({reused} reused); cell {row['cell']} {row['method']} {row['status']}", flush=True)
        for i, t in enumerate(tasks):
            if keys[i] in cache and keys[i] not in done:
                file.write(json.dumps({**cache[keys[i]], "task_index": i, "task_key": keys[i], "from_cache": True},
                                      allow_nan=False) + "\n")
        file.flush()
    rows = [json.loads(line) for line in args.output.read_text().splitlines() if line.strip()]
    rows.sort(key=lambda r: r.get("task_index", 0))          # deterministic final ordering
    summary = {}
    for method in methods:
        runs = [r for r in rows if r["method"] == method]
        savings = []
        for r in runs:
            before = next((b for b in rows if b["cell"] == r["cell"] and b["seed"] == r["seed"] and b["method"] == "base_stock"), None)
            if before is not None and before["cost"] is not None and r["cost"] is not None:
                savings.append(100 * (before["cost"] - r["cost"]) / max(abs(before["cost"]), 1.))
        summary[method] = {"runs": len(runs), "complete": sum(r["status"] == "COMPLETE" for r in runs),
                           "service_breaches": sum(r["service_breach"] for r in runs),
                           "paired_completes": len(savings), "median_vs_base_stock_pct": median(savings) if savings else None,
                           "min": min(savings, default=None), "max": max(savings, default=None), "cost_losses": sum(v < -1e-6 for v in savings)}
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
