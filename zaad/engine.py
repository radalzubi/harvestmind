"""Closed-loop finite-policy search with common physical/economic settlement.

There is no scenario-dependent first action, no withholding available stock,
and no production claim of calibrated disruption probabilities or safe savings.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, timezone
import hashlib
import json
import math
from statistics import mean
from typing import Any, Literal

import numpy as np

from zaad.contracts import Action, PlanningRequest, PlanReport
from zaad.forecast import fit


@dataclass(frozen=True)
class Policy:
    name: str
    buffer: float
    alternative_share: float = 0
    risk_aware: bool = True


POLICIES = (
    Policy("incumbent", 0, risk_aware=False),
    Policy("base_stock", 1, risk_aware=False),
    Policy("lean", 0), Policy("balanced", 1), Policy("protected", 2),
    Policy("high_protection", 3),
    Policy("route_split", 1, .5), Policy("alternate", 1, 1),
    Policy("route_protect", 2, .5), Policy("alternate_protect", 2, 1),
)


def fingerprint(request: PlanningRequest) -> str:
    return hashlib.sha256(request.model_dump_json().encode()).hexdigest()


def prepare(request: PlanningRequest) -> tuple[dict, list[dict], list[str]]:
    from zaad.signals import Signal, route_evidence
    signals = tuple(Signal.model_validate_json(json.dumps(s)) for s in request.signals)
    forecasts = {}
    warnings = []
    for item in request.items:
        rows = sorted((r for r in request.demand if r.item == item.id), key=lambda r: r.period)
        periods = [r.period for r in rows]
        if len(rows) < 16 or periods != list(range(-len(rows), 0)):
            warnings.append(f"{item.id}: need >=16 consecutive explicit demand periods ending -1")
            continue
        forecasts[item.id] = {"item": item.id, **fit(np.asarray([r.quantity for r in rows]))}
    edges = {e.id: e for e in request.edges}
    item_map = {i.id: i for i in request.items}
    cards = []
    for route in request.routes:
        history = sorted((r for r in request.deliveries if r.route == route.id),
                         key=lambda r: (r.period, r.known_at))
        path = [edges[e] for e in route.edges]
        entities = {route.id, route.supplier, *route.edges}
        domains: set[str] = set()
        for edge in path:
            entities.update((edge.origin, edge.destination))
            domains.update(edge.failure_domains)
        entities.update(domains)
        evidence = route_evidence(signals, sorted(entities), request.as_of.astimezone(timezone.utc))
        severity = max(evidence.physical_severity, evidence.official_severity)
        fills = [r.accepted / r.ordered for r in history]
        leads = [r.lead_periods for r in history]
        reason = None
        if not route.approved or route.compliance != "cleared":
            reason = "operator approval/compliance clearance missing or blocked"
        elif route.valid_until <= request.as_of or not all(e.available for e in path):
            reason = "expired quote or unavailable edge"
        elif len(history) < 12:
            reason = "thin route delivery history (<12 accepted observations)"
        avg_fill = mean(fills) if fills else 0
        if avg_fill <= 0:
            reason = "no demonstrated accepted supply"
        cards.append({"route": route.id, "item": route.item, "supplier": route.supplier,
                      "path": list(route.edges), "landed_cost": route.landed_cost,
                      "capacity": min(route.capacity, *(e.capacity/item_map[route.item].volume for e in path)),
                      "edge_capacity_unit": "volume units per review; item.volume converts base quantity",
                      "feasible": reason is None, "rejection_reason": reason,
                      "quote_reference": route.quote_reference,
                      "valid_until": route.valid_until.isoformat(),
                      "failure_domains": sorted(domains), "mean_fill": avg_fill,
                      "lead_p50": float(np.quantile(leads, .5)) if leads else None,
                      "lead_p90": float(np.quantile(leads, .9)) if leads else None,
                      "lead_mean": mean(leads) if leads else 1,
                      "severity": severity, "evidence": evidence.model_dump(mode="json"),
                      "risk_mapping": "ASSUMED stress: +ceil(3*severity) lead; fill*(1-.30*severity)",
                      "probability_calibrated": False,
                      "history_count": len(history)})
    for item in request.items:
        if not any(r["feasible"] and r["item"] == item.id for r in cards):
            warnings.append(f"{item.id}: no feasible sufficiently observed route")
    return forecasts, cards, warnings


def route_parameters(card: dict, aware: bool) -> tuple[float, int]:
    sev = card["severity"] if aware else 0
    return max(.01, card["mean_fill"] * (1 - .3 * sev)), max(
        1, int(math.ceil(card["lead_mean"])) + int(math.ceil(3 * sev)))


def order_actions(request: PlanningRequest, forecasts: dict, cards: list[dict],
                  policy: Policy, stock: dict[str, float], pending: list[dict],
                  t: int = 0) -> list[Action]:
    """One review only. Pipeline exposes booked expectation, never hidden actual arrival.

    All heuristics and optimized candidates share hard pack/MOQ, edge, route,
    warehouse commitment and cash bounds. The greedy capacity allocation is
    priority-weighted, not a globally optimal multi-item flow solve.
    """
    item_map = {i.id: i for i in request.items}
    route_map = {r.id: r for r in request.routes}
    stock = dict(stock)
    for p in pending:
        if p["due"] == t:
            stock[p["item"]] = stock.get(p["item"], 0)+p["expected"]
    pending = [p for p in pending if p["due"] != t]
    edge_left = {e.id: e.capacity for e in request.edges}
    route_left = {r["route"]: r["capacity"] for r in cards}
    cash = request.review_budget
    # Conservative physical bound on booked quantities, not expected partial fills.
    occupied = sum(stock.get(i.id, 0) * i.volume for i in request.items)
    occupied += sum((lot.reserved+lot.damaged)*item_map[lot.item].volume for lot in request.inventory)
    occupied += sum(p["ordered"] * item_map[p["item"]].volume for p in pending)
    space = max(0., request.warehouse_capacity - occupied)
    actions = []
    priority = sorted(request.items, key=lambda i: (-i.criticality *
                      (i.selling_price - i.base_cost), i.id))
    for item in priority:
        forecast = forecasts[item.id]
        options = sorted((r for r in cards if r["feasible"] and r["item"] == item.id
                          and route_map[r["route"]].valid_until >
                          request.as_of+timedelta(days=t*request.period_days)),
                         key=lambda r: (r["landed_cost"], r["route"]))
        if not options:
            continue
        primary = options[0]
        primary_fill, primary_lead = route_parameters(primary, policy.risk_aware)
        lead = primary_lead
        # A route shift changes the coverage horizon as well as procurement mix.
        if policy.alternative_share and len(options) > 1:
            _, alt_lead = route_parameters(options[1], policy.risk_aware)
            lead = int(math.ceil((1-policy.alternative_share)*lead + policy.alternative_share*alt_lead))
        coverage = lead + 1
        if policy.name == "incumbent":
            target = forecast["mean"] * (coverage + item.incumbent_cover)
        else:
            target = forecast["mean"] * coverage + policy.buffer * forecast["sd"] * math.sqrt(coverage)
        usable_pipeline = sum(p["expected"] for p in pending
                              if p["item"] == item.id and p["due"] <= t + coverage)
        shortfall = max(0., target - stock.get(item.id, 0) - usable_pipeline)
        preferred = [(primary, 1 - policy.alternative_share)]
        if len(options) > 1:
            preferred.append((options[1], policy.alternative_share))
        else:
            preferred = [(primary, 1.)]
        # Primary/alternate quotas first, then spill only into documented spare capacity.
        planned = {r["route"]: shortfall * share for r, share in preferred}
        for card in options:
            planned.setdefault(card["route"], 0.)
        remaining = shortfall
        for spill in (False, True):
            for card in options:
                if remaining <= 1e-9:
                    break
                rid = card["route"]
                route = route_map[rid]
                fill, due = route_parameters(card, policy.risk_aware)
                want = remaining if spill else min(remaining, planned[rid])
                if want <= 1e-9:
                    continue
                qty = math.ceil(want / fill / item.pack - 1e-10) * item.pack
                qty = max(item.moq, qty)
                limit = min(route_left[rid], *(edge_left[e]/item.volume for e in route.edges),
                            cash / route.landed_cost, space / item.volume)
                qty = min(qty, math.floor(limit / item.pack + 1e-10) * item.pack)
                if qty < item.moq or qty <= 0:
                    continue
                actions.append(Action(route=rid, item=item.id, quantity=qty,
                                      expected_accepted=qty*fill, expected_due_in=due,
                                      cash=qty*route.landed_cost))
                remaining -= qty * fill
                route_left[rid] -= qty
                for edge in route.edges:
                    edge_left[edge] -= qty*item.volume
                cash -= qty * route.landed_cost
                space -= qty * item.volume
    # Aggregate possible spill into one action per route.
    merged: dict[str, Action] = {}
    for action in actions:
        old = merged.get(action.route)
        merged[action.route] = action if old is None else action.model_copy(update={
            "quantity": action.quantity+old.quantity,
            "expected_accepted": action.expected_accepted+old.expected_accepted,
            "cash": action.cash+old.cash})
    return list(merged.values())


def initial_state(request: PlanningRequest) -> tuple[dict, list[dict]]:
    stock = {i.id: sum(x.quantity - x.reserved - x.damaged for x in request.inventory
                      if x.item == i.id and x.expires_in > 0) for i in request.items}
    route_items = {r.id: r.item for r in request.routes}
    pending = [{"id": p.id, "item": route_items[p.route], "route": p.route,
                "ordered": p.ordered, "expected": p.expected_accepted, "due": p.due_in}
               for p in request.pipeline]
    return stock, pending


def first_review_state(request: PlanningRequest) -> tuple[dict, list[dict]]:
    stock, pending = initial_state(request)
    for p in pending:
        if p["due"] == 0:
            stock[p["item"]] += p["expected"]
    return stock, [p for p in pending if p["due"] > 0]


def draw_paths(request: PlanningRequest, forecasts: dict, cards: list[dict],
               seed: int, count: int | None = None, *, deterministic: bool = False) -> dict:
    """Shared route failure-domain ranks; demand empirical residual bootstrap.

    Dependence is conservative structural coupling, NOT an estimated copula.
    Separate common random numbers support paired policy comparisons.
    """
    rng = np.random.default_rng(seed)
    n = count or request.scenarios
    shape = (n, request.horizon)
    demand = {}
    for item in request.items:
        y = np.asarray([r.quantity for r in sorted(request.demand, key=lambda r:r.period)
                        if r.item == item.id])
        residual = y[-52:] - np.mean(y[-52:])
        demand[item.id] = np.full(shape, forecasts[item.id]["mean"]) if deterministic else np.maximum(
            0, forecasts[item.id]["mean"] + rng.choice(residual, size=shape))
    domains = sorted({d for c in cards for d in c["failure_domains"]})
    domain_rank = {d: rng.random(shape) for d in domains}
    supply = {}
    for card in cards:
        history = [r for r in request.deliveries if r.route == card["route"]]
        if not history:
            continue
        rank = rng.random(shape)
        for domain in card["failure_domains"]:
            # Shared failures are not diversified merely by supplier count.
            rank = np.minimum(rank, domain_rank[domain])
        rank = 1 - (1-rank) ** (1+len(card["failure_domains"]))
        ordered = sorted(history, key=lambda r:r.accepted/r.ordered)
        indices = np.minimum((rank * len(ordered)).astype(int), len(ordered)-1)
        fills = np.asarray([r.accepted/r.ordered for r in ordered])[indices]
        leads = np.asarray([r.lead_periods for r in ordered])[indices]
        severity = card["severity"]
        if deterministic:
            fills = np.full(shape, card["mean_fill"])
            leads = np.full(shape, math.ceil(card["lead_mean"]), dtype=int)
        supply[card["route"]] = {
            "fills": np.ones(shape) if request.force_unit_fills else fills * (1-.3*severity),
            "leads": leads + int(math.ceil(3*severity))}
    return {"demand": demand, "supply": supply}


def settle(request: PlanningRequest, forecasts: dict, cards: list[dict], policy: Policy,
           paths: dict, scenario: int) -> dict:
    """One authoritative lost-sales, FEFO, full-ledger settlement for ALL policies.

    Known pipeline is delivered-equivalent. New fills apply once. Private actual
    arrival dates never enter the public pending book used for reordering.
    Normal POs paid on accepted quantity; freight/landed costs recorded separately.
    No source is credited with unconstrained phantom capacity.
    """
    items = {i.id: i for i in request.items}
    route_map = {r.id: r for r in request.routes}
    stock, pending = initial_state(request)
    lots = {i.id: [[float(x.quantity-x.reserved-x.damaged), x.expires_in]
                  for x in request.inventory if x.item == i.id and x.expires_in > 0]
            for i in request.items}
    arrivals = [{**p, "actual_due": p["due"], "actual": p["expected"]} for p in pending]
    opening = sum(stock[k]*items[k].base_cost for k in stock)
    opening += sum(p["expected"]*items[p["item"]].base_cost for p in pending)
    purchase = freight = holding = disposal = lost_revenue = 0.
    demand_total = {i.id: 0. for i in request.items}
    served_total = {i.id: 0. for i in request.items}
    waste_total = 0.
    inventory_values = []
    trace = []
    previous: dict[str, float] = {}
    churn = 0.
    capacity_breach = False
    for t in range(request.horizon):
        current_cards = paths.get("card_timeline", {}).get(t, cards)
        received_ids = set()
        for arrival in arrivals:
            if arrival["actual_due"] == t:
                lots[arrival["item"]].append([arrival["actual"], t+items[arrival["item"]].shelf_life])
                received_ids.add(arrival["id"])
        arrivals = [p for p in arrivals if p["id"] not in received_ids]
        pending = [p for p in pending if p["id"] not in received_ids]
        for p in pending:
            if p["due"] <= t:
                p["due"] = t+1  # overdue but unreceived; never reveal hidden actual time.
        for item in request.items:
            expired = sum(q for q, expiry in lots[item.id] if expiry <= t)
            waste_total += expired
            disposal += expired * item.disposal_per_unit
            lots[item.id] = [lot for lot in lots[item.id] if lot[1] > t]
            stock[item.id] = sum(q for q, _ in lots[item.id])
        occupied = sum(stock[i.id]*i.volume for i in request.items)
        occupied += sum((lot.reserved+lot.damaged)*items[lot.item].volume for lot in request.inventory)
        capacity_breach |= occupied > request.warehouse_capacity+1e-6
        # Orders placed before current demand resolves; first stage cannot see it.
        actions = order_actions(request, forecasts, current_cards, policy, stock, pending, t)
        placed = {a.route: a.quantity for a in actions}
        churn += sum(abs(placed.get(r, 0)-previous.get(r, 0)) for r in set(placed)|set(previous))
        previous = placed
        for a in actions:
            supply = paths["supply"][a.route]
            actual = a.quantity * float(supply["fills"][scenario, t])
            lead = int(supply["leads"][scenario, t])
            ident = f"new-{t}-{a.route}"
            p = {"id": ident, "item": a.item, "route": a.route, "ordered": a.quantity,
                 "expected": a.expected_accepted, "due": t+a.expected_due_in}
            pending.append(p)
            arrivals.append({**p, "actual_due": t+lead, "actual": actual})
            purchase += actual * items[a.item].base_cost
            freight += actual * (route_map[a.route].landed_cost-items[a.item].base_cost)
        period_served = period_demand = 0.
        for item in request.items:
            demand = float(paths["demand"][item.id][scenario, t])
            remaining = demand
            for lot in sorted(lots[item.id], key=lambda x:x[1]):
                used = min(remaining, lot[0])
                lot[0] -= used
                remaining -= used
            served = demand-remaining
            demand_total[item.id] += demand
            served_total[item.id] += served
            period_served += served
            period_demand += demand
            lost_revenue += remaining*item.selling_price
            stock[item.id] = sum(q for q, _ in lots[item.id])
            holding += stock[item.id]*item.holding_per_period
        value = sum(stock[k]*items[k].base_cost for k in stock)
        inventory_values.append(value)
        trace.append({"period": t, "inventory_value": value, "served": period_served,
                      "demand": period_demand, "ordered": sum(a.quantity for a in actions),
                      "pipeline": sum(p["expected"] for p in pending)})
    closing_stock = sum(stock[k]*items[k].base_cost for k in stock)
    closing_pipeline = sum(p["actual"]*items[p["item"]].base_cost for p in arrivals)
    # Purchase minus assets + lost sales at selling price is a consistent profit-loss
    # comparator. Do not add lost contribution a second time. Terminal assets use
    # base cost, NOT premium freight; expiry beyond horizon is a sensitivity limit.
    consumed_cost = opening+purchase-closing_stock-closing_pipeline
    total = consumed_cost+freight+holding+disposal+lost_revenue
    total_demand = sum(demand_total.values())
    return {"total_cost": total, "purchase_base_cash": purchase,
            "freight_premium": freight, "holding": holding, "disposal": disposal,
            "lost_sales_revenue": lost_revenue, "consumed_cost": consumed_cost,
            "opening_assets": opening, "closing_inventory_assets": closing_stock,
            "closing_pipeline_assets": closing_pipeline,
            "unit_fill": sum(served_total.values())/total_demand if total_demand else 1.,
            "item_fill": {k:served_total[k]/v if v else 1. for k,v in demand_total.items()},
            "demand": demand_total, "served": served_total,
            "average_inventory_value": mean(inventory_values), "peak_inventory_value": max(inventory_values),
            "waste_units": waste_total, "churn_units": churn, "capacity_breach": capacity_breach,
            "trace": trace}


def evaluate(request: PlanningRequest, forecasts: dict, cards: list[dict],
             policy: Policy, paths: dict) -> list[dict]:
    count = next(iter(paths["demand"].values())).shape[0]
    return [settle(request, forecasts, cards, policy, paths, s) for s in range(count)]


def summary(request: PlanningRequest, rows: list[dict], name: str) -> dict:
    costs = [r["total_cost"] for r in rows]
    fills = {i.id: (sum(r["served"][i.id] for r in rows) /
                   max(1e-9,sum(r["demand"][i.id] for r in rows))) for i in request.items}
    for i in request.items:
        if not sum(r["demand"][i.id] for r in rows):
            fills[i.id] = 1.
    return {"policy": name, "mean_cost": mean(costs), "cost_range": [min(costs), max(costs)],
            "cvar90_cost": mean(sorted(costs)[-max(1, math.ceil(.1*len(costs))):]),
            "unit_fill": sum(sum(r["served"].values()) for r in rows) /
            max(1e-9,sum(sum(r["demand"].values()) for r in rows)),
            "item_fill": fills,
            "zero_demand_items": [i.id for i in request.items if not sum(r["demand"][i.id] for r in rows)],
            "service_note": "Zero-demand SKU fill is a feasibility sentinel of 1, not observed service evidence",
            "service_feasible": all(fills[i.id]+1e-9 >= i.service_target for i in request.items),
            "physical_feasible": not any(r["capacity_breach"] for r in rows),
            "average_inventory_value": mean(r["average_inventory_value"] for r in rows),
            "peak_inventory_value": max(r["peak_inventory_value"] for r in rows),
            "freight_premium": mean(r["freight_premium"] for r in rows),
            "holding": mean(r["holding"] for r in rows),
            "churn_units": mean(r["churn_units"] for r in rows)}


def plan(request: PlanningRequest) -> PlanReport:
    forecasts, cards, warnings = prepare(request)
    if request.force_unit_fills:
        warnings.append("Unit-fill control cannot open the recommendation gate")
    severity = max((r["severity"] for r in cards if r["feasible"]), default=0.)
    recovery_observed = any(r["evidence"]["recovery_signal_ids"] for r in cards)
    mode: Literal["LEAN", "PROTECT", "ALLOCATE", "RECOVER"] = "PROTECT" if severity > 0 else "RECOVER" if recovery_observed and request.prior_mode in ("PROTECT", "ALLOCATE") else "LEAN"
    if request.prior_mode in ("PROTECT", "ALLOCATE") and not severity and not recovery_observed:
        warnings.append("Prior disruption has no fresh recovery evidence; cannot infer recovery from missing/stale feeds")
        mode = request.prior_mode
    base: dict[str, Any] = {"operator_id": request.operator_id, "as_of": request.as_of,
            "input_fingerprint": fingerprint(request), "evidence_label": request.evidence_label,
            "routes": tuple(cards), "forecasts": tuple(forecasts.values())}
    limitations = (
        "Synthetic/empirical scenario search is not real-operator validation or an Oracle comparison.",
        "Risk shifts are explicit stress assumptions, not calibrated disruption probabilities.",
        "Finite policy family; no global optimality, multi-echelon, OTIF, legal certification or automatic PO.",
        "Known pipeline expected quantities/dates held fixed; censored open-PO survival model deferred.",
        "Warehouse booked-quantity constraint conservative; terminal assets at base cost, future expiry not guaranteed.",
        "Only the first review may be approved; future simulated orders stop when supplied quotes expire.",
        "Human approval and current carrier/compliance quote required; simulation gate is not a no-harm guarantee.")
    if warnings:
        return PlanReport(**base, status="ABSTAIN", mode=mode, selected_policy="none",
                          actions=(), incumbent_actions=(), reasons=tuple(warnings), frontier=(),
                          economics={}, evidence={"gate": "insufficient_data", "seed": request.seed},
                          limitations=limitations)
    selection = draw_paths(request, forecasts, cards, request.seed)
    outcomes = {p.name:evaluate(request, forecasts, cards, p, selection) for p in POLICIES}
    frontier = [summary(request, outcomes[p.name], p.name) for p in POLICIES]
    feasible = [x for x in frontier if x["service_feasible"] and x["physical_feasible"]]
    proposed = min(feasible, key=lambda x:(x["mean_cost"], x["average_inventory_value"])) if feasible else frontier[0]
    policy = next(p for p in POLICIES if p.name == proposed["policy"])
    reasons = []
    evidence = {"seed": request.seed, "confirmation_seed": request.seed+1,
                "scenarios_per_stage": request.scenarios,
                "gate": "modeled independent Monte Carlo confirmation, not empirical safety validation",
                "force_unit_fills": False, "constraint_relaxations": [],
                "all_policies_common_settlement": True,
                "supplier_allocation": "approved routes, price/priority then spill; identical hard bounds",
                "probability_calibrated": False, "method": "finite_policy_stochastic_search"}
    selected = POLICIES[0]
    status: Literal["KEEP_INCUMBENT", "ABSTAIN", "RECOMMEND_FOR_REVIEW"] = "KEEP_INCUMBENT"
    chosen = frontier[0]
    comparator = frontier[0]
    if not feasible:
        status = "ABSTAIN"
        mode = "ALLOCATE"
        reasons.append("No candidate meets all SKU unit-fill targets and physical bounds; no relaxation or executable plan.")
    elif policy.name != "incumbent":
        confirmation = draw_paths(request, forecasts, cards, request.seed+1)
        candidate_rows = evaluate(request, forecasts, cards, policy, confirmation)
        incumbent_rows = evaluate(request, forecasts, cards, POLICIES[0], confirmation)
        confirmed = summary(request, candidate_rows, policy.name)
        confirmed_incumbent = summary(request, incumbent_rows, "incumbent")
        differences = np.asarray([a["total_cost"]-b["total_cost"]
                                  for a,b in zip(incumbent_rows,candidate_rows)])
        rng = np.random.default_rng(request.seed+2)
        lower = float(np.quantile(np.mean(rng.choice(differences,
                      size=(300,len(differences))),axis=1), .05))
        worst = float(min(differences))
        evidence.update({"proposed_policy": policy.name, "modeled_benefit_lower90": lower,
                         "modeled_worst_regret": max(0.,-worst), "confirmation": confirmed})
        # A modest regret cap and positive paired evidence; strictly no unit-fill waiver.
        if confirmed["service_feasible"] and confirmed["physical_feasible"] and lower > 0 and worst >= -.05*frontier[0]["mean_cost"]:
            selected, chosen, status = policy, confirmed, "RECOMMEND_FOR_REVIEW"
            comparator = confirmed_incumbent
            reasons.append("Lower modeled cost confirmed on independent simulation draws with per-SKU service and hard bounds intact.")
        else:
            reasons.append("Proposed change failed confirmation benefit, service, physical or worst-regret gate; keep incumbent.")
    else:
        reasons.append("Incumbent is the lowest-cost service-feasible member of the tested policy family.")
    stock, pending = first_review_state(request)
    incumbent = tuple(order_actions(request, forecasts, cards, POLICIES[0], stock, pending))
    actions = () if status == "ABSTAIN" else tuple(order_actions(request, forecasts, cards, selected, stock, pending))
    inv_release = comparator["average_inventory_value"]-chosen["average_inventory_value"]
    economics = {"currency": request.currency, "horizon_periods": request.horizon,
                 "incumbent_modeled_cost": comparator["mean_cost"],
                 "selected_modeled_cost": chosen["mean_cost"],
                 "modeled_horizon_benefit": comparator["mean_cost"]-chosen["mean_cost"],
                 "inventory_release_not_profit": inv_release,
                 "temporary_buffer_increase": max(0.,-inv_release),
                 "recurring_carry_benefit_in_horizon": comparator["holding"]-chosen["holding"],
                 "annualization": "not applied; validate persistence and avoidable carry costs first",
                 "cash_required_now": sum(a.cash for a in actions),
                 "tail_risk_benefit_not_booked_savings": comparator["cvar90_cost"]-chosen["cvar90_cost"]}
    return PlanReport(**base, status=status, mode=mode, selected_policy=selected.name,
                      actions=actions, incumbent_actions=incumbent, reasons=tuple(reasons),
                      frontier=tuple(frontier), economics=economics, evidence=evidence,
                      limitations=limitations)


def report_json(report: PlanReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, allow_nan=False)
