#!/usr/bin/env python3
"""New, version-frozen synthetic network evidence. Never writes v1 evidence.

Development / validation / final are separate seeds. The final command refuses
any source mismatch with its pre-registered manifest and refuses overwriting.
Every failed solve, physical failure, loss, and parameter vector is retained.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
from pathlib import Path
from statistics import median
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
         "development6": [34001], "validation6": [35001, 35002]}
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


def cells(matrix="coverage"):
    if matrix == "reliability":
        return reliability_cells()
    if matrix == "v4":
        return v4_cells()
    if matrix == "v6":
        return v6_cells()
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
    shock = (supply in {"severe", "partial", "correlated", "deterioration_recovery", "closure_recovery"}) if reliability else kind not in {"normal", "none", "false_alarm", "transfer", "substitution", "recovery", "cash"}
    recovery = cell.get("truth_recovery", 9 if kind == "delayed_recovery" else 7)
    extra = cell.get("truth_extra_lead", 6 if kind in {"severe", "shared_outage"} or supply == "severe" else (0 if supply == "partial" else 3))
    floor = cell.get("truth_fill", .5 if kind in {"severe", "supplier_outage"} or supply == "severe" else (.6 if supply == "partial" else .8))
    if reliability and supply == "partial":
        recovery = H       # partial deliveries for the whole horizon, on time
    if reliability and supply == "deterioration_recovery":
        recovery, extra, floor = 8, 2, .85      # late and short from period 1 to 7, then clean
    if reliability and supply == "closure_recovery":
        recovery, extra, floor = 6, 10, .0      # main route closed from period 1 to 5, then restored
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


def task(args):
    cell, seed, method = args
    req = request_for(cell, seed)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=list(SEEDS), default="development")
    parser.add_argument("--matrix", choices=["coverage", "full", "reliability", "v4", "v6"], default="coverage")
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
        if args.limit or args.demand or args.family or args.target or args.supply or not manifest.exists() or json.loads(manifest.read_text()) != configuration:
            raise SystemExit(f"{args.split} requires an exact frozen source/configuration, no filters and no run limit")
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
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
    selected = [{**c, "adaptation": args.adaptation} for c in selected]
    methods = args.methods or (RELIABILITY_METHODS if args.matrix == "reliability" else V4_METHODS if args.matrix == "v4" else METHODS)
    if args.split in {"development5", "validation5"} and not args.methods:
        methods = V5_METHODS
    if args.split in {"development6", "validation6"} and not args.methods:
        methods = V6_METHODS
    tasks = [(c, s, m) for c in selected for s in SEEDS[args.split] for m in methods]
    with args.output.open("x") as file, ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(task, tasks, chunksize=1)):
            file.write(json.dumps(row, allow_nan=False) + "\n")
            file.flush()
            if i % 25 == 0:
                print(f"{i+1}/{len(tasks)} rows; {row['status']}", flush=True)
    rows = [json.loads(line) for line in args.output.read_text().splitlines()]
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
