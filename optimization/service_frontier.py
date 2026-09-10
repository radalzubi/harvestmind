"""Service-constrained inventory experiment on the common planning model.

Service is expected unit fill, not OTIF or a probability guarantee. Removing
the shortage reward is a policy experiment; evaluation still prices missed
margin. Targets are business inputs. This module never recommends lowering
an SLA merely because a lower target makes a cheaper plan.
"""
from __future__ import annotations

from dataclasses import replace
import math

import pyomo.environ as pyo

from optimization.multi_period_sp import MultiPeriodStochasticLP


def solve_service_target(model: MultiPeriodStochasticLP, demand, supply, *, targets: dict,
                         lead_times=None, yield_scenarios=None, opening_inventory=None,
                         per_period: bool = False) -> dict:
    products = list(demand["product_id"].unique())
    if set(targets) != set(products):
        raise ValueError("an explicit service target is required for every product")
    if any(not 0 < float(v) <= 1 for v in targets.values()):
        raise ValueError("service targets must be finite and in (0, 1]")
    carries = [float((model.holding_cost_by_product or {}).get(
               j, model.holding_cost_per_kg_per_period)) for j in products]
    if any(not math.isfinite(c) or c <= 0 for c in carries):
        raise ValueError("positive inventory carrying cost is required for right-sizing")
    candidate = replace(model, service_floor_by_product=dict(targets),
                        service_floor_each_period=per_period,
                        unmet_cost_by_product={j: 0.0 for j in products},
                        lost_sale_per_kg_usd=0.0)
    result = candidate.solve(demand, supply, lead_times=lead_times,
                             yield_scenarios=yield_scenarios,
                             opening_inventory=opening_inventory)
    result["candidate"] = "service_target"
    result["selection_objective"] = "carrying, waste and recourse subject to expected unit fill"
    result["shortage_cost_in_objective"] = False
    result["service_scope"] = "each_controllable_period" if per_period else "controllable_horizon"
    return result


def stock_service_frontier(model: MultiPeriodStochasticLP, demand, supply, levels, **kwargs) -> list:
    """Return every target, including infeasibility; never silently drop a cell.

    Frontier points are in-sample planning outcomes. The calling benchmark
    must replay their fixed schedules out of sample before using them.
    """
    rows = []
    products = list(demand["product_id"].unique())
    costs = supply.groupby("product_id")["price_per_kg"].mean().to_dict()
    for level in levels:
        r = solve_service_target(model, demand, supply,
                                 targets={j: float(level) for j in products}, **kwargs)
        row = {"target": float(level), "status": r["status"], "usable": r["usable"],
               "schedule": r["x"], "expected_fill": None, "average_inventory_value": None,
               "objective": r["objective"], "nondominated": False}
        if r["usable"]:
            m = r["model"]
            weights = r["scenario_weights"]
            den = sum(float(d.demand_kg) * weights[int(d.scenario_index)] for d in demand.itertuples())
            unmet = sum(weights[w] * pyo.value(m.u[j, t, w]) for j in m.J for t in m.T for w in m.W)
            row["expected_fill"] = 1 - unmet / den if den else 1.0
            row["average_inventory_value"] = sum(
                weights[w] * costs[j] * pyo.value(m.inv[j, t, w])
                for j in m.J for t in m.T for w in m.W) / model.n_periods
        rows.append(row)
    for row in rows:
        if row["usable"]:
            row["nondominated"] = not any(
                other["usable"] and other["expected_fill"] >= row["expected_fill"]
                and other["average_inventory_value"] < row["average_inventory_value"] - 1e-8
                for other in rows)
    return rows
