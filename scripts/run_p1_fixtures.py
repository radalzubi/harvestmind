"""Run the P1 fixtures A-T through the rolling replay for every policy and seed, and write the
per-cell evidence, the result table and the expectation check.

    python3 scripts/run_p1_fixtures.py --out docs/zaad_full/evidence/p1/fixtures.jsonl [--fixtures A_..,B_..] [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from statistics import mean

from scripts.p1_fixtures import FIXTURES, POLICIES, REVIEWS, SEEDS, build

STRESS_ARM = "none"
GATE_ARM = "default"
SMOOTHING_ARM = 0.
SCENARIOS_ARM = 0     # 0 = the fixture's own scenario count; >0 is a diagnostic override (world-count trade-off)
PRODUCT_DEFAULTS = False


def _build(name: str, seed: int):
    req = build(name, seed, stresses=STRESS_ARM, order_smoothing=SMOOTHING_ARM)
    if GATE_ARM != "default":
        req = req.model_copy(update={"service_gate_basis": GATE_ARM})
    if SCENARIOS_ARM > 0:
        req = req.model_copy(update={"scenarios": SCENARIOS_ARM})
    if PRODUCT_DEFAULTS:
        from zaad.full.contracts import Request
        req = req.model_copy(update={k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak")})
    return req
from zaad.full.economics import COMPONENTS, cost_breakdown, order_waterfall
from zaad.full.replay import replay
from zaad.full.tolerance import is_dust
from zaad.full.worlds import draw, forecast_all


def _init(stress: str, gate: str, smoothing: float, scenarios: int = 0, product_defaults: bool = False) -> None:
    global STRESS_ARM, GATE_ARM, SMOOTHING_ARM, SCENARIOS_ARM, PRODUCT_DEFAULTS
    STRESS_ARM, GATE_ARM, SMOOTHING_ARM, SCENARIOS_ARM, PRODUCT_DEFAULTS = stress, gate, smoothing, scenarios, product_defaults


def run_cell(name: str, policy: str, seed: int) -> dict:
    from zaad.full.planner import protection_profile, supply_profiles   # noqa: local import for workers
    req = _build(name, seed)
    truth = draw(req, seed + 10000, 1)[0]
    started = time.time()
    out = replay(req, truth, REVIEWS, policy)
    seconds = time.time() - started
    cell = {"fixture": name, "policy": policy, "seed": seed, "status": out["status"], "seconds": seconds,
            "failure": out.get("failure")}
    if out["status"] != "COMPLETE":
        return cell
    targets = {s.id: s.target for s in req.services}
    served = demand = 0.
    breaches = 0
    worst = 0.
    inventory_units, inventory_value, cash_deployed = [], [], []
    orders, order_lines, order_units = 0, 0, 0.
    components = {c: 0. for c in COMPONENTS}
    actions, abstentions, categories = 0, 0, set()
    per_review_service = []
    solver_seconds = []
    retained_reasons: list[str] = []
    for row in out["reviews"]:
        st = row["settlement"]
        s_ = d_ = 0.
        for x in st["service_by_period"]:
            s_ += x["served"]
            d_ += x["demand"]
            short = x["demand"] - x["served"]
            worst = max(worst, short)
        served += s_
        demand += d_
        review_service = s_ / d_ if d_ > 0 else None
        per_review_service.append(review_service)
        if review_service is not None and any(review_service < targets[k] - req.service_tolerance for k in targets):
            breaches += 1
        inventory_units.append(sum(x["quantity"] for x in st["end_stock"]))
        inventory_value.append(st["trace"][0]["inventory_value"])
        cash_deployed.append(max(0., req.liquidity.opening_cash - st["trace"][0]["cash"] + st["trace"][0]["debt"]))
        lines = [p for p in row["purchases"] if not is_dust(p["quantity"])]
        order_lines += len(lines)
        order_units += sum(p["quantity"] for p in lines)
        orders += len({p["source"].split("_")[0] for p in lines}) and (len(st["shipments"]) or (1 if lines else 0))
        for k, v in cost_breakdown(st["ledger"]).items():
            if k in components:
                components[k] += v
        if policy == "gated":
            warn = row["warnings"]
            if warn and warn[0] == "PENDING_REVIEW":
                actions += 1
            if any("NO MATERIAL IMPROVEMENT" in str(w) for w in warn):
                abstentions += 1
        solver_seconds.append(row.get("wall_seconds", 0.))
        if policy == "gated":
            retained_reasons.append("; ".join(str(w) for w in row["warnings"][3:]) or row["warnings"][0])
    # Attribution on the first review's period-0 plan for the ZAAD row (what the recommendation says).
    if policy == "gated":
        first = _build(name, seed)
        fits = forecast_all(first)
        prot = protection_profile(first, fits, supply_profiles(first))
        from zaad.full.model import Solution
        sol = Solution("OPTIMAL", {(p["source"], 0): p["quantity"] for p in out["reviews"][0]["purchases"]}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
        for o in order_waterfall(first, fits, prot, sol):
            categories |= {k for k, v in o["attribution"].items() if v > 1e-6}
            cell.setdefault("explanations", []).append(o["explanation"])
            cell.setdefault("attribution_sums_ok", True)
            cell["attribution_sums_ok"] &= abs(o["attribution_sum"] - o["quantity"]) < 1e-6
    cell.update({
        "service": served / demand if demand else None, "breaches": breaches, "unmet_units": demand - served, "worst_shortfall": worst,
        "avg_inventory_units": mean(inventory_units), "avg_inventory_value": mean(inventory_value),
        "order_count": order_lines, "avg_order_size": order_units / order_lines if order_lines else 0.,
        "components": components, "total_modeled_cost": out["economic_cost"], "ledger": out["ledger"],
        "working_capital": mean(cash_deployed), "actions": actions, "abstentions": abstentions,
        "categories": sorted(categories), "wall_seconds_per_review": solver_seconds, "per_review_service": per_review_service,
        "review_outcomes": retained_reasons})
    return cell


def table(cells: list[dict]) -> str:
    cols = ["FIXTURE", "POLICY", "SERVICE", "P10", "BREACHES", "UNMET", "WORST SHORTFALL", "AVG INV UNITS", "AVG INV VALUE",
            "ORDER COUNT", "AVG ORDER SIZE", "PURCHASE", "FREIGHT", "ORDERING", "RECEIVING", "CARRYING", "FINANCING", "SHORTAGE",
            "INV VALUE CHANGE", "TOTAL MODELED COST", "WORKING CAPITAL", "INVENTORY DELTA %", "TOTAL COST DELTA %", "ACTION RECOMMENDED?", "WHY?"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    by = {}
    for c in cells:
        if c["status"] == "COMPLETE":
            by.setdefault((c["fixture"], c["policy"]), []).append(c)
    for name in FIXTURES:
        base = by.get((name, "incumbent"))
        inc_cost = mean(c["total_modeled_cost"] for c in base) if base else None
        inc_inv = mean(c["avg_inventory_value"] for c in base) if base else None
        for policy in POLICIES:
            rows = by.get((name, policy))
            if not rows:
                failed = [c for c in cells if c["fixture"] == name and c["policy"] == policy]
                lines.append(f"| {name} | {policy} | " + " | ".join(["FAILED: " + str(failed[0].get("failure") if failed else "missing")] + [""] * (len(cols) - 3)) + " |")
                continue
            svc = [c["service"] for c in rows if c["service"] is not None]
            comp = {k: mean(c["components"][k] for c in rows) for k in COMPONENTS}
            cost = mean(c["total_modeled_cost"] for c in rows)
            inv = mean(c["avg_inventory_value"] for c in rows)
            action = ("-" if policy != "gated" else
                      f"yes ({sum(c['actions'] for c in rows)}/{REVIEWS * len(rows)} reviews)" if sum(c["actions"] for c in rows) else
                      f"no (NO MATERIAL IMPROVEMENT {sum(c['abstentions'] for c in rows)}/{REVIEWS * len(rows)})")
            why = "-" if policy != "gated" else ("; ".join(sorted({k for c in rows for k in c["categories"]})) or "no period-0 order")
            vals = [name, policy, f"{mean(svc):.3f}" if svc else "n/a", f"{sorted(svc)[max(0, int(.1 * len(svc)) - 1)]:.3f}" if svc else "n/a",
                    f"{mean(c['breaches'] for c in rows):.1f}", f"{mean(c['unmet_units'] for c in rows):.1f}", f"{max(c['worst_shortfall'] for c in rows):.1f}",
                    f"{mean(c['avg_inventory_units'] for c in rows):.0f}", f"{inv:,.0f}",
                    f"{mean(c['order_count'] for c in rows):.1f}", f"{mean(c['avg_order_size'] for c in rows):.0f}",
                    *[f"{comp[k]:,.0f}" for k in ("PURCHASE", "FREIGHT", "ORDERING", "RECEIVING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE")],
                    f"{cost:,.0f}", f"{mean(c['working_capital'] for c in rows):,.0f}",
                    f"{(inv - inc_inv) / inc_inv:+.1%}" if inc_inv else "n/a",
                    f"{(cost - inc_cost) / abs(inc_cost):+.1%}" if inc_cost else "n/a", action, why]
            lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def check(cells: list[dict]) -> list[dict]:
    """Pre-registered expectations, checked verbatim."""
    by = {}
    for c in cells:
        if c["status"] == "COMPLETE":
            by.setdefault((c["fixture"], c["policy"]), []).append(c)
    results = []
    for name, spec in FIXTURES.items():
        e = spec["expect"]
        costs = {p: mean(c["total_modeled_cost"] for c in by[name, p]) for p in POLICIES if (name, p) in by}
        gated = by.get((name, "gated"), [])
        checks = {}
        if costs:
            floor = min(costs.values())
            # Ties: every policy within half a percent of the cheapest is "best".
            best_set = {p for p, v in costs.items() if v <= floor + .005 * max(abs(floor), 1.)}
            checks["best_policy_in"] = bool(best_set & set(e["best_policy_in"]))
            baselines = {p: v for p, v in costs.items() if p != "gated"}
            if "gated" in costs and baselines:
                best_baseline = min(baselines.values())
                checks["zaad_not_worse"] = costs["gated"] <= best_baseline + e["zaad_not_worse"] * max(abs(best_baseline), 1.)
        checks["all_policies_completed"] = all((name, p) in by and len(by[name, p]) == len(SEEDS) for p in POLICIES)
        floor = e.get("service_floor")
        if floor is not None:
            checks["service_floor"] = all(c["service"] is not None and c["service"] >= floor for p in POLICIES for c in by.get((name, p), []))
        if gated:
            acts = sum(c["actions"] for c in gated)
            total = REVIEWS * len(gated)
            checks["action"] = {"yes": acts >= total / 2, "no": acts <= total / 4, "either": True}[e["action"]]
            seen = {k for c in gated for k in c["categories"]}
            checks["categories"] = all(k in seen for k in e["categories"])
            checks["attribution_partitions"] = all(c.get("attribution_sums_ok", True) for c in gated)
        results.append({"fixture": name, "expectation": e, "checks": checks, "pass": all(checks.values()), "costs": costs, "why": spec["why"]})
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/zaad_full/evidence/p1/fixtures.jsonl")
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--stress", default="none", choices=("none", "late", "severe"))
    ap.add_argument("--gate", default="default", choices=("default", "target", "incumbent"))
    ap.add_argument("--smoothing", type=float, default=0.)
    ap.add_argument("--product-defaults", action="store_true", help="drop the declared P1 fixture settings (stratified worlds, tie-break) and run at product defaults")
    a = ap.parse_args()
    global STRESS_ARM, GATE_ARM, SMOOTHING_ARM
    STRESS_ARM, GATE_ARM, SMOOTHING_ARM = a.stress, a.gate, a.smoothing
    global PRODUCT_DEFAULTS
    PRODUCT_DEFAULTS = a.product_defaults
    arm = a.stress + ("" if a.gate == "default" else "_gate_" + a.gate) + ("" if a.smoothing == 0 else f"_smoothing_{a.smoothing:g}") + ("_product_defaults" if a.product_defaults else "")
    names = [n for n in a.fixtures.split(",") if n] or list(FIXTURES)
    policies = [p for p in a.policies.split(",") if p]
    jobs = [(n, p, s) for n in names for p in policies for s in SEEDS]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cells = []
    started = time.time()
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(a.stress, a.gate, a.smoothing, 0, a.product_defaults)) as pool, out.open("w") as f:
        for cell in pool.map(run_cell, *zip(*jobs)):
            cells.append(cell)
            f.write(json.dumps(cell, allow_nan=False, default=float) + "\n")
            f.flush()
            print(f"{cell['fixture']:32s} {cell['policy']:14s} {cell['seed']} {cell['status']:10s} "
                  f"{cell.get('total_modeled_cost', float('nan')):12,.0f} {cell['seconds']:6.1f}s", flush=True)
    results = check(cells)
    walls = sorted(w for c in cells if c["policy"] == "gated" and c["status"] == "COMPLETE" for w in c.get("wall_seconds_per_review", []))
    runtime = ({"reviews": len(walls), "p50": walls[len(walls) // 2], "p90": walls[int(.9 * len(walls))], "p95": walls[min(len(walls) - 1, int(.95 * len(walls)))],
                "max": walls[-1], "total_seconds": time.time() - started, "stress_arm": a.stress, "gate_arm": a.gate, "smoothing_arm": a.smoothing} if walls else {"reviews": 0})
    (out.parent / f"P1_RUNTIME_{arm}.json").write_text(json.dumps(runtime, indent=1))
    (out.parent / f"P1_RESULT_TABLE_{arm}.md").write_text(f"# P1 fixtures A-T: result table (declared stress: {a.stress}; service gate basis: {a.gate}; order smoothing: {a.smoothing:g})\n\nMeans over seeds "
        f"{list(SEEDS)}, {REVIEWS} rolling reviews each, weekly periods, twelve-period horizon. Costs are the settlement's economic "
        "cost components (INVENTORY_VALUE_CHANGE is opening stock at asset value less closing stock at terminal value), so TOTAL MODELED "
        "COST reconciles to the settlement exactly. Deltas are against the INCUMBENT row of the same fixture.\n\n" + table(cells) + "\n")
    (out.parent / f"P1_EXPECTATIONS_{arm}.json").write_text(json.dumps(results, indent=1, default=float))
    print(json.dumps({"cells": len(cells), "complete": sum(c["status"] == "COMPLETE" for c in cells),
                      "fixtures_passing": sum(r["pass"] for r in results), "fixtures": len(results),
                      "runtime": runtime, "seconds": time.time() - started}, indent=1))


if __name__ == "__main__":
    main()
