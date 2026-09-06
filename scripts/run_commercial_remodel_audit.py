"""Frozen synthetic regression experiment, not customer savings validation.

Service target x opening cover factorial; other factors vary one at a time.
Every cell and failed solve is retained. All policies use counterfactual.settle
with their own rolling state. Legacy SP hides pipeline from the planner only.
No external data, production vault or training pool is used.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import statistics as st
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.counterfactual import (  # noqa: E402
    FoldInputs, FoldTruth, policy_adaptive_sp, policy_anchored_sp, policy_deterministic_sp,
    policy_order_up_to, policy_service_target, policy_stochastic_sp, settle,
)
from backtesting.incumbent import configured_incumbent  # noqa: E402
from backtesting.safe_selector import SafeSelectionConfig, safe_select  # noqa: E402
from domain.economics import CostConfig  # noqa: E402
from domain.model import fmcg_policy  # noqa: E402
from domain.uom import PackSpec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ("incumbent", "order_up_to", "deterministic_sp", "legacy_sp",
            "stochastic_sp", "service_target", "anchored_sp", "safe_selected", "service_periodic")
FUNCTIONS = {"order_up_to": lambda f, cap, rng, n: (policy_order_up_to(f), {"usable": True}),
             "deterministic_sp": policy_deterministic_sp, "stochastic_sp": policy_stochastic_sp,
             "service_target": policy_service_target, "anchored_sp": policy_anchored_sp,
             "adaptive_sp": policy_adaptive_sp,
             "service_periodic": lambda f, cap, rng, n: policy_service_target(f, cap, rng, n, per_period=True),
             "anchored_no_cvar": lambda f, cap, rng, n: policy_anchored_sp(f, cap, rng, n, cvar_lambda=0.)}


@dataclass(frozen=True)
class Cell:
    target: float = .97
    cover: float = 2.
    disruption: str = "none"
    demand: str = "stable"
    lead: str = "stable"
    supply: str = "reliable"
    margin: str = "normal"


def cells():
    all_cells = [Cell(target=t, cover=c) for t in (.85, .90, .93, .95, .97, .98, .99, .995, 1.)
                 for c in (0., .5, 1., 2., 3., 4., 6., 8.)]
    for name, values in {
        "disruption": ("mild", "moderate", "severe"),
        "demand": ("seasonal", "intermittent", "promotion", "structural_shift"),
        "lead": ("variable", "heavy_tail", "route_closure"),
        "supply": ("variable", "correlated_failures"),
        "margin": ("low", "high"),
    }.items():
        all_cells.extend(replace(Cell(), **{name: v}) for v in values)
    # Explicit marginal targets requested by the prompt, at fixed cover.
    all_cells.extend([Cell(target=.94), Cell(target=.96), Cell(target=.999)])
    return all_cells


def history(cell, seed, count=100):
    rng = np.random.default_rng(seed)
    demand = {j: np.maximum(0., rng.normal(mu, .15 * mu, count))
              for j, mu in (("A", 100.), ("B", 40.))}
    for j, ds in demand.items():
        if cell.demand == "seasonal":
            ds *= 1 + .3 * np.sin(2 * math.pi * np.arange(count) / 52)
        elif cell.demand == "intermittent":
            ds *= rng.random(count) > .5
        elif cell.demand == "promotion":
            ds[62:68] *= 1.5
        elif cell.demand == "structural_shift":
            ds[60:] *= 1.5
    common = rng.random(count) < .18
    events = {}
    for supplier in ("S1", "S2"):
        fills = np.clip(rng.normal(.98 if cell.supply == "reliable" else .85, .03, count), 0., 1.)
        leads = np.ones(count, dtype=int)
        if cell.supply == "correlated_failures":
            fills[common] *= .6
        if cell.lead == "variable":
            leads += rng.integers(0, 3, count)
        elif cell.lead == "heavy_tail":
            leads += (rng.pareto(3., count)).clip(0, 6).astype(int)
        elif cell.lead == "route_closure":
            leads[60:66] += 5
        if cell.disruption != "none" and supplier == "S1":
            severity = {"mild": .85, "moderate": .65, "severe": .35}[cell.disruption]
            # Two historical episodes permit learning; final episode recovers.
            for start in (16, 38, 60):
                fills[start:start + 6] *= severity
                leads[start:start + 6] += 2
        events[supplier] = list(zip(map(float, fills), map(int, leads)))
    return demand, events


def inputs(cell, demand, events, origin, horizon, opening=None, pipeline=None):
    supplier = {"A": "S1", "B": "S2"}
    train = {j: list(map(float, ds[max(0, origin - 52):origin])) for j, ds in demand.items()}
    ev = {}
    for s, es in events.items():
        received = defaultdict(list)
        for t, (fill, lag) in enumerate(es[:origin]):
            receipt = t + lag
            if max(0, origin - 52) <= receipt < origin:
                received[receipt - origin].append((fill, lag))
        # Supplier outcomes become knowable on RECEIPT, not PO placement.
        # Multiple synthetic shipments received in a week are equal-weight
        # observations, not order-volume-weighted operator fill estimates.
        ev[s] = {t: (st.mean(v[0] for v in vs), round(st.mean(v[1] for v in vs)))
                 for t, vs in received.items()}
    lead = {s: max(1, round(st.mean(v[1] for v in ev[s].values()))) for s in ev}
    margin = {j: {"low": .5, "normal": 2., "high": 5.}[cell.margin] for j in supplier}
    costs = CostConfig(holding_rate_per_period=.005, shortage_cost_per_unit=margin,
                       waste_cost_per_unit={j: 5. for j in supplier}, emergency_capacity_factor=0.)
    pol = fmcg_policy({j: PackSpec(1) for j in supplier}, cost_config=costs, service_level=cell.target)
    return FoldInputs(origin=origin, horizon=horizon, products=list(supplier), supplier_of=supplier,
                      lead_of=lead, train_demand=train, train_fill={s: [v[0] for v in ev[s].values()] for s in ev},
                      unit_cost={j: 5. for j in supplier}, margin=margin,
                      # Exogenous, time-invariant capacity: inner folds must not
                      # inherit a capacity inferred from their own later demand.
                      capacity={"A": 150., "B": 60.},
                      opening=opening if opening is not None else {j: cell.cover * st.mean(train[j]) for j in supplier},
                      pipeline=pipeline if pipeline is not None else {(j, t): st.mean(train[j])
                                  for j in supplier for t in range(lead[supplier[j]])},
                      policy=pol, supply_events=ev,
                      incumbent=configured_incumbent(cover_weeks=2., review_periods=1),
                      promo_multiplier={(j, t): 1.5 for j in supplier for t in range(horizon)
                                        if cell.demand == "promotion" and 62 <= origin + t < 68})


def expected_pipeline(pending, origin):
    """Planner-visible open-PO expectation; no future delivered quantity/ETA.

    An overdue, not-yet-received PO is provisionally due now. This is an
    explicit simplistic promise rule, not supplier ETA intelligence.
    Pending membership records only receipts already observed at the origin.
    """
    out = {}
    for po in pending:
        at = max(0, po["placed"] + po["promised_lead"] - origin)
        key = (po["sku"], at)
        out[key] = out.get(key, 0.) + po["quantity"] * po["expected_fill"]
    return out


def run(cell, seed, name, scenarios, periods=12):
    demand, events = history(cell, seed)
    on_hand = None
    pending = []
    confirmed_initial = None
    totals = dict(total=0., holding=0., shortage=0., disposal=0., sla_penalty=0.,
                  served=0., demanded=0., inventory_value=0., ordered=0.)
    modes, failures, changes = [], [], []
    prev = None
    review = 12 if name == "stochastic_open_loop" else 4
    for step in range(0, periods, review):
        origin = 60 + step
        fi = inputs(cell, demand, events, origin, 12, on_hand, {})
        if confirmed_initial is None:
            confirmed_initial = inputs(cell, demand, events, origin, 12).pipeline
        initial_due = {(j, t - step): q for (j, t), q in confirmed_initial.items() if t >= step}
        fi.pipeline = dict(initial_due)
        for key, q in expected_pipeline(pending, origin).items():
            fi.pipeline[key] = fi.pipeline.get(key, 0.) + q
        rng = np.random.default_rng(seed * 1000 + step)
        meta = {}
        if name == "incumbent":
            schedule = fi.incumbent.build_schedule(fi)
        elif name == "legacy_sp":
            schedule, meta = policy_stochastic_sp(replace(fi, pipeline={}), None, rng, scenarios)
        elif name == "safe_selected":
            decision = safe_select(fi, None, rng,
                                   SafeSelectionConfig(n_scen=scenarios, n_boot=200),
                                   candidates=("order_up_to", "deterministic_sp", "service_target", "stochastic_sp"))
            schedule = decision.schedule
            modes.append(decision.mode_run)
        elif name == "stochastic_open_loop":
            schedule, meta = policy_stochastic_sp(fi, None, rng, scenarios)
        else:
            schedule, meta = FUNCTIONS[name](fi, None, rng, scenarios)
        if schedule is None or not meta.get("usable", True) or meta.get("floor_relaxed") or meta.get("budget_relaxed"):
            failures.append({"step": step, "status": meta.get("status"),
                             "floor_relaxed": bool(meta.get("floor_relaxed"))})
            schedule = fi.incumbent.build_schedule(fi)
        committed = {k: q for k, q in schedule.items() if k[2] < review}
        if prev is not None:
            changes.append(sum(abs(committed.get(k, 0.) - prev.get(k, 0.)) for k in set(committed) | set(prev)))
        prev = committed
        truth = FoldTruth(demand={(j, t): float(demand[j][origin + t]) for j in fi.products for t in range(review)},
                          fill={(s, t): events[s][origin + t][0] for s in events for t in range(review)},
                          lead={(s, t): events[s][origin + t][1] for s in events for t in range(review)})
        # Truth pipeline is private to physical settlement. The planner only
        # received the independently computed expectation above.
        actual_pipeline = dict(initial_due)
        for po in pending:
            key = (po["sku"], po["actual_arrival"] - origin)
            actual_pipeline[key] = actual_pipeline.get(key, 0.) + po["quantity"] * po["actual_fill"]
        score = settle(committed, replace(fi, horizon=review, pipeline=actual_pipeline), truth, None)
        for (s, j, t), q in committed.items():
            pending.append(dict(sku=j, placed=origin+t, quantity=min(q, fi.capacity[j]),
                                promised_lead=fi.lead_of[s], expected_fill=st.mean(fi.train_fill[s]),
                                actual_arrival=origin+t+truth.lead[(s, t)], actual_fill=truth.fill[(s, t)]))
        # At the NEXT review, receipts before that date really have occurred.
        pending = [po for po in pending if po["actual_arrival"] >= origin + review]
        for metric in ("total", "holding", "shortage", "disposal", "sla_penalty"):
            totals[metric] += getattr(score, metric)
        totals["served"] += score.components["served_units"]
        totals["demanded"] += score.components["demanded_units"]
        totals["inventory_value"] += score.components["average_inventory_value"] * review
        totals["ordered"] += sum(min(q, fi.capacity[k[1]]) for k, q in committed.items())
        on_hand = score.components["inventory_by_product"]
    totals["inventory_value"] /= periods
    totals["fill"] = totals["served"] / totals["demanded"] if totals["demanded"] else 1.
    totals["gross_contribution_after_carry"] = totals["served"] * fi.margin["A"] - totals["holding"] - totals["disposal"]
    return {"seed": seed, "policy": name, **asdict(cell), **totals,
            "failures": failures, "selections": modes, "plan_change_units": st.mean(changes) if changes else 0.,
            "service_target_breached": totals["fill"] < cell.target}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="401,402,403,404,405")
    parser.add_argument("--scenarios", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ablations", action="store_true")
    parser.add_argument("--output", default="docs/remodel/evidence/causal")
    args = parser.parse_args()
    chosen = cells()[:args.limit]
    policies = POLICIES
    if args.ablations:
        chosen = [Cell(cover=0.), Cell(), Cell(cover=6.),
                  Cell(disruption="severe"), Cell(demand="structural_shift")]
        policies = (*POLICIES, "anchored_no_cvar", "adaptive_sp", "stochastic_open_loop")
    seeds = [int(s) for s in args.seeds.split(",")]
    output = ROOT / args.output
    if args.ablations:
        output /= "ablations"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, cell in enumerate(chosen):
        for seed in seeds:
            group = [run(cell, seed, p, args.scenarios) for p in policies]
            incumbent = group[0]
            for row in group:
                row["cell"] = index
                row["saved"] = incumbent["total"] - row["total"]
                row["saving_pct"] = 100 * row["saved"] / incumbent["total"] if incumbent["total"] > 0 else None
                row["service_delta"] = row["fill"] - incumbent["fill"]
                row["inventory_release"] = incumbent["inventory_value"] - row["inventory_value"]
                row["realized_harm"] = row["total"] > incumbent["total"] + 1e-7
            rows.extend(group)
        (output / "runs.json").write_text(json.dumps({"synthetic": True, "base_commit": "2820a69",
            "design": "target x cover factorial plus OFAT; two SKUs, one supplier per SKU, weekly",
            "information": "receipt-dated training; expected open POs separate from private realized pipeline",
            "scenarios": args.scenarios, "seeds": seeds, "completed_cells": index + 1,
            "planned_cells": len(chosen), "rows": rows}, indent=2, allow_nan=False))
        print(f"cell {index + 1}/{len(chosen)} complete; {len(rows)} policy runs", flush=True)
    with (output / "runs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({**r, "failures": json.dumps(r["failures"]), "selections": json.dumps(r["selections"])} for r in rows)


if __name__ == "__main__":
    main()
