"""Rolling observe/refit/reoptimize replay with a private realized pipeline.

The planner never sees the pre-drawn truth. Every review receives a newly built
as-of snapshot; supplier training outcomes appear only when actually received.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import time
import numpy as np

from zaad.full.contracts import Request
from zaad.full.model import Solution, solve
from zaad.full.planner import plan, targets
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.tolerance import is_dust, po_closed, source_pack
from zaad.full.worlds import World, dates, draw, forecast_all


# Methods frozen at PR23/PR24 behaviour run on the frozen engine profile so paired comparisons
# against the reliability profile are like for like. "protected" and "gated" use the new profile.
FROZEN_METHODS = {"base_stock", "order_up_to", "deterministic", "stochastic", "robust", "frozen_forecast", "gated_pr24"}
PR30_METHODS = {"gated_pr30", "protected_pr30"}   # reliability profile without state-dependent decay
V4_METHODS = {"gated_v4"}                         # PR 33 profile: decay on, v5 rules off
V5_ENGINE_METHODS = {"gated_v5"}                  # PR 35 engine: v5 rules on, v6 rules off
V6_ENGINE_METHODS = {"gated_v6"}                  # PR 36 engine: v6 rules on, v7 rules off
COMPARATOR_METHODS = FROZEN_METHODS | PR30_METHODS | V4_METHODS | V5_ENGINE_METHODS | V6_ENGINE_METHODS


# Additional replay methods registered by later passes (P2 network baselines register here). The
# frozen method table below is untouched; an unknown method still falls through to it.
NETWORK_METHODS: dict = {}


def choose(req: Request, method: str) -> Solution:
    if method in NETWORK_METHODS:
        return NETWORK_METHODS[method](req)
    if method in FROZEN_METHODS and req.engine_profile != "pr24":
        req = req.model_copy(update={"engine_profile": "pr24"})
    if method in PR30_METHODS and req.protection_decay:
        req = req.model_copy(update={"protection_decay": False, "carry_incumbent": False})
    if method == "gated_pr24" and req.carry_incumbent:
        req = req.model_copy(update={"carry_incumbent": False})
    if method in V4_METHODS and req.protection_v5:
        req = req.model_copy(update={"protection_v5": False})
    if method in PR30_METHODS and req.protection_v5:
        req = req.model_copy(update={"protection_v5": False})
    if method in COMPARATOR_METHODS and req.protection_v6 and method not in V6_ENGINE_METHODS:
        req = req.model_copy(update={"protection_v6": False})
    if method in COMPARATOR_METHODS and req.protection_v7:
        req = req.model_copy(update={"protection_v7": False})
    if method == "incumbent" or method.startswith(("replace_sold", "periodic", "reorder_point", "economic_lot")):
        # P1 comparators and declared operator rules, projected over the horizon; lot-aware.
        from zaad.full.policies import baseline_plan
        rule = req.incumbent_rule if method == "incumbent" else method
        if rule is None:
            raise ValueError("the incumbent method needs a declared incumbent_rule on the request")
        return baseline_plan(req, rule)
    if method == "echelon_base_stock":
        # Independent MEIO-style comparator: echelon base stock projected through the common model.
        from zaad.full.echelon import echelon_targets
        return solve(req, draw(req, req.seed, 1, deterministic=True), targets=echelon_targets(req))
    if method in {"gated", "gated_pr24", "gated_pr30", "gated_v4", "gated_v5", "gated_v6"}:
        report = plan(req)
        rows = report["actions"]
        solution = Solution("OPTIMAL" if report["status"] != "ABSTAIN" else "ABSTAIN",
                            {(r["source"], r["period"]): r["quantity"] for r in rows if r["action"] == "purchase"},
                            {(r["transfer"], r["expiry_cohort"], r["period"]): r["quantity"] for r in rows if r["action"] == "transfer"},
                            {(r["po"], r["option"]): r["quantity"] for r in rows if r["action"] == "po_option"},
                            {}, None, report["cash"], 0., 0, 0, None, None,
                            [report["status"], report["selected_policy"], f"mode={report['mode']}", *report["reasons"]])
        # Protection state per SKU/location, kept for recovery measurement (state, activity, units).
        solution.protection_state = [{"sku": p["sku"], "location": p["location"], "regime": p["state"].get("regime"), "activity": p["state"]["activity"],
                                      "protection_units": p["protection_units"], "lean_baseline_units": p["state"]["lean_baseline_units"],
                                      "on_hand_units": p["on_hand_units"], "periods_to_lean": p["state"]["periods_to_lean"], "flags": p["state"].get("flags", []),
                                      "echelon": p["state"].get("echelon"), "duplicated_buffer_units": p["state"].get("duplicated_buffer_units", 0.),
                                      "echelon_origin": bool(p.get("echelon_origin")),
                                      "replenishment_periods": p.get("replenishment_periods"),
                                      "replenished_by_transfer_arc": p.get("replenished_by_transfer_arc"),
                                      "exit": p["state"].get("exit")}
                                     for p in report["protection"]]
        solution.procurement_timing = report.get("procurement_timing")
        solution.capital = report.get("capital")
        solution.inherited_on_hand = None      # type: ignore[attr-defined]  # filled by replay, which alone knows the provenance
        solution.solve_quality = report.get("solve_quality")
        orch = report.get("orchestration") or {}
        solution.orchestration = {k: orch.get(k) for k in ("state", "planner_owner", "p1_classes_added", "candidate_classes_requested",   # type: ignore[attr-defined]
                                                            "candidates_built", "milps_attempted", "required_candidate_starved")}
        return solution
    deterministic = method in {"base_stock", "order_up_to", "deterministic", "frozen_forecast"}
    worlds = draw(req, req.seed, 1 if deterministic else req.scenarios, deterministic=deterministic,
                  adaptive=method != "frozen_forecast")
    if method in {"base_stock", "order_up_to"}:
        return solve(req, worlds, targets=targets(req, 1.645 if method == "base_stock" else 0.))
    if method == "robust":
        extra = [w for i, stress in enumerate(req.stresses) for w in draw(req, req.seed + 100 + i, 1, stress)]
        worlds = [replace(w, weight=1 / (len(worlds) + len(extra))) for w in worlds + extra]
    result = solve(req, worlds, service_floor=True, per_world_service=method == "robust",
                   service_risk="cvar" if method in {"protected", "protected_pr30"} else "expected")
    if result.status == "INFEASIBLE":
        # Explicit recovery solve, not a relaxed solve passed off as achieving the SLA.
        result = solve(req, worlds, service_first="all")
        result.warnings.append("REQUESTED_SERVICE_INFEASIBLE: lexicographic service-recovery plan")
    return result


def replay(initial: Request, truth: World, reviews: int, method: str, keep_requests: list | None = None,
           rolling: bool = False) -> dict:
    """Legacy mode (default): the planning horizon shrinks by one period per review (H-1 convention) and
    the truth must cover `reviews` periods. Rolling mode (`rolling=True`, P1 benchmark evaluation): every
    review replans on a fresh full-horizon snapshot, as production replanning does; declared
    period-indexed data roll forward by repeating their last declared value, committed future payments
    roll into `other_payments` at their due period, and the truth must cover `reviews - 1 + horizon`
    periods (see `zaad.full.evaluation.long_truth`). Nothing else differs between the modes."""
    truth_periods = min(len(v) for v in truth.demand.values()) if truth.demand else initial.horizon
    if rolling:
        if reviews - 1 + initial.horizon > truth_periods:
            raise ValueError("truth shorter than the rolling window plus the planning horizon")
    elif reviews > initial.horizon:
        raise ValueError("truth horizon shorter than replay")
    last_truth = (truth_periods if rolling else initial.horizon) - 1
    deferred: dict[int, float] = {}      # rolling mode: committed payments due beyond the next snapshot, by absolute period
    req = initial
    private = {p.id: (truth.po_due[p.id], truth.po_fill[p.id]) for p in initial.pipeline}
    reviews_log: list[dict] = []
    total_components: dict[str, float] = {}
    first_assets, last_assets = None, 0.
    # Inherited stock, tracked through the replay (v8). Opening usable stock per SKU/location,
    # drawn down first as demand is served, so at any review it is the part of what is on hand that
    # the optimizer did not buy. Consumption is charged to inherited units before purchased ones,
    # which is the FEFO-consistent reading for a position that starts older than anything bought.
    inherited: dict[tuple[str, str], float] = {}
    for lot in initial.stock:
        inherited[lot.sku, lot.location] = inherited.get((lot.sku, lot.location), 0.) + lot.usable
    for t in range(reviews):
        # OBSERVE arrivals at the current origin BEFORE choosing any transfer/order.
        # Future receipts stay private; only now-arrived POs are materialized.
        arrived = [p for p in req.pipeline if private[p.id][0] <= t]
        if arrived:
            state = req.model_dump()
            state["pipeline"] = [p.model_dump() for p in req.pipeline if p not in arrived]
            state["stock"] = list(state["stock"])
            state["shipment_history"] = [r.model_dump() for r in req.shipment_history if r.id not in {"censored-" + p.id for p in arrived}]
            other_payments = list(req.liquidity.other_payments)
            for po in arrived:
                source = next(s for s in req.sources if s.id == po.source)
                sku = next(s for s in req.skus if s.id == source.sku)
                ratio = private[po.id][1]
                state["stock"].append({"id": "observed-" + po.id, "known_at": req.as_of, "sku": source.sku,
                                       "location": source.destination, "quantity": po.remaining * ratio,
                                       "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": sku.shelf_life, "age_periods": 0})
                state["shipment_history"].append({"id": "received-" + po.id, "known_at": req.as_of, "source": po.source,
                        "elapsed_days": max(1, (req.as_of - po.placed_at).days), "arrived": True,
                        "stage": po.stage, "carrier": po.carrier, "accepted_ratio": ratio})
                keep = next(o for o in po.options if o.action == "keep")
                if keep.payment_due_in < req.horizon:
                    other_payments[keep.payment_due_in] += po.remaining * keep.remaining_invoice_per_unit
            state["liquidity"] = {**req.liquidity.model_dump(), "other_payments": other_payments}
            state["sources"] = []
            for source in req.sources:
                ratios = [r["accepted_ratio"] for r in state["shipment_history"] if r["source"] == source.id and r.get("accepted_ratio") is not None]
                prior = next(s for s in initial.sources if s.id == source.id)
                fields = source.model_dump()
                if ratios:
                    fields["fill_mean"] = max(1e-6, (12 * prior.fill_mean + sum(ratios)) / (12 + len(ratios)))
                    if len(ratios) >= 3:
                        fields["fill_sd"] = max(prior.fill_sd, min(.5, float(np.std(ratios))))
                state["sources"].append(fields)
            req = Request.model_validate(state)
        planning_req = req.model_copy(update={"history": initial.history}) if method == "frozen_forecast" else req
        # Inherited stock cannot exceed what is physically present at this location now.
        on_hand_now: dict[tuple[str, str], float] = {}
        for lot in req.stock:
            on_hand_now[lot.sku, lot.location] = on_hand_now.get((lot.sku, lot.location), 0.) + lot.usable
        for key in list(inherited):
            inherited[key] = min(inherited[key], on_hand_now.get(key, 0.))
        planning_req = planning_req.model_copy(update={"inherited_on_hand": {f"{k[0]}|{k[1]}": v for k, v in inherited.items() if v > 1e-9}})
        if req.incumbent_rule and not planning_req.incumbent_orders:
            # The operator's declared rule is the incumbent at every review (P1): what the rule
            # would buy from this snapshot, so ZAAD is always compared against the real policy.
            from zaad.full.policies import baseline_plan
            declared = baseline_plan(planning_req, req.incumbent_rule)
            from zaad.full.contracts import IncumbentOrder, IncumbentTransfer
            planning_req = planning_req.model_copy(update={"incumbent_orders": tuple(
                IncumbentOrder(known_at=planning_req.as_of, source=sid, period=t, quantity=q)
                for (sid, t), q in declared.purchases.items() if q > 0 and t < planning_req.horizon),
                # a network policy's transfers (P2) ride along; frozen rules never transfer, so this stays empty for them
                "incumbent_transfers": tuple(
                IncumbentTransfer(known_at=planning_req.as_of, transfer=arc, period=t, expiry=expiry, quantity=q)
                for (arc, expiry, t), q in declared.transfers.items() if q > 0 and t < planning_req.horizon)})
        if keep_requests is not None:
            keep_requests.append(planning_req)      # diagnostics only: the exact snapshot each review planned on
        wall_started = time.perf_counter()
        solution = choose(planning_req, method)
        wall_seconds = time.perf_counter() - wall_started
        if not solution.usable_plan:
            return {"status": solution.status, "reviews": reviews_log, "failure": solution.warnings}
        H = req.horizon
        # The current review's exogenous truth is not supplied to choose().
        demand = {s.id: tuple(list(truth.demand[s.id][t:]) + [0.] * t)[:H] for s in req.services}
        arrival = {(s.id, k): truth.arrival[s.id, min(t + k, last_truth)] - t for s in req.sources for k in range(H)}
        fills = {(s.id, k): truth.fills[s.id, min(t + k, last_truth)] for s in req.sources for k in range(H)}
        world = World(f"truth-review-{t}", 1., demand, arrival, fills,
                      {p.id: max(0, private[p.id][0] - t) for p in req.pipeline}, {p.id: private[p.id][1] for p in req.pipeline})
        try:
            outcome = settle(req, solution, world, steps=1)
        except PhysicalViolation as exc:
            return {"status": "PHYSICAL_FAILURE", "reviews": reviews_log, "failure": str(exc)}
        if first_assets is None:
            first_assets = outcome["ledger"]["opening_assets"]
        last_assets = outcome["ledger"]["closing_assets"]
        for component, amount in outcome["ledger"].items():
            if component not in {"opening_assets", "closing_assets"}:
                total_components[component] = total_components.get(component, 0.) + amount
        reviews_log.append({"review": t, "as_of": req.as_of.isoformat(), "forecast": forecast_all(req),
                            "purchases": [{"source": s, "quantity": q} for (s, k), q in solution.purchases.items() if k == 0],
                            "warnings": solution.warnings, "settlement": outcome,
                            "protection": getattr(solution, "protection_state", None),
                            "procurement_timing": getattr(solution, "procurement_timing", None),
                            "capital": getattr(solution, "capital", None),
                            "inherited_on_hand": {f"{k[0]}|{k[1]}": v for k, v in inherited.items() if v > 1e-9},
                            "solve_quality": getattr(solution, "solve_quality", None),
                            "orchestration": getattr(solution, "orchestration", None),
                            "wall_seconds": wall_seconds,
                            "solver": {"status": solution.status, "seconds": solution.solve_seconds,
                                       "gap": solution.gap, "variables": solution.variables,
                                       "constraints": solution.constraints}})
        # Draw inherited stock down by this review's consumption at each location, oldest first.
        served_by_location: dict[tuple[str, str], float] = {}
        for service in req.services:
            served = sum(x["served"] for x in outcome["service_by_period"] if x["service"] == service.id)
            key = (service.sku, service.location)
            served_by_location[key] = served_by_location.get(key, 0.) + served
        for key, used in served_by_location.items():
            if key in inherited:
                inherited[key] = max(0., inherited[key] - used)
        if t == reviews - 1:
            break
        now = req.as_of + timedelta(days=req.period_days)
        data = req.model_dump(mode="python")
        data["as_of"], data["seed"] = now, initial.seed + t + 1
        # Forecast truth is appended ONLY after the outcome becomes observable.
        history = [{**r.model_dump(), "period": r.period - 1} for r in req.history]
        history += [{"known_at": now, "service": s.id, "period": -1, "quantity": demand[s.id][0]} for s in req.services]
        data["history"] = history
        data["stock"] = [{"id": f"stock-{n}", "known_at": now, "sku": row["sku"], "location": row["location"],
                          "quantity": row["quantity"], "reserved": 0., "damaged": 0., "quarantined": 0.,
                          "expires_in": max(0, row["expiry"] - 1), "age_periods": 0}
                         for n, row in enumerate(outcome["end_stock"]) if not is_dust(row["quantity"])]
        # Preserve locked inventory separately; it never becomes salable through replay.
        data["stock"] += [{**lot.model_dump(), "id": f"locked-{n}", "known_at": now,
                           "quantity": lot.reserved + lot.damaged + lot.quarantined,
                           "expires_in": max(0, lot.expires_in - 1)} for n, lot in enumerate(req.stock)
                          if lot.reserved + lot.damaged + lot.quarantined > 0]
        pipeline = []
        shipment_history: list = list(req.shipment_history)
        for po in req.pipeline:
            actual_due, actual_fill = private[po.id]
            po_source = next(s for s in req.sources if s.id == po.source)
            if po_closed(po, po_source):
                continue
            for option in po.options:
                q = solution.amendments.get((po.id, option.id), 0.)
                if is_dust(q, source_pack(po_source)) or option.action == "cancel":
                    continue
                expected_due = option.due_in
                due = actual_due
                if option.action != "keep":
                    keep = next(o for o in po.options if o.action == "keep")
                    due = t + option.due_in + max(0, actual_due - t - keep.due_in)
                if due <= t:
                    shipment_history.append({"id": f"received-{po.id}-{t}", "known_at": now, "source": po.source,
                                             "elapsed_days": max(1, (req.as_of - po.placed_at).days), "arrived": True,
                                             "stage": po.stage, "carrier": po.carrier})
                    continue
                identity = f"{po.id}_{option.id}"
                private[identity] = due, actual_fill
                row = po.model_dump()
                row.update(id=identity, known_at=now, ordered=q, confirmed=q, shipped=min(q, po.shipped), received=0., rejected=0.,
                           expected_accepted_remaining=q * po.expected_accepted_remaining / po.remaining,
                           prepaid_per_remaining_unit=0., allow_split_amendments=False,
                           options=[{"id": "keep", "known_at": now, "action": "keep", "due_in": max(1, expected_due - 1),
                                     "fee_per_unit": 0., "remaining_invoice_per_unit": 0., "payment_due_in": 0,
                                     "max_quantity": q, "deadline": now, "allowed_stages": [po.stage], "contract_reference": "committed_after_review"}])
                pipeline.append(row)
        for (source_id, period), q in solution.purchases.items():
            source = next(s for s in req.sources if s.id == source_id)
            if period != 0 or is_dust(q, source_pack(source)):
                continue
            expected = dates(req, source, 0)[1]
            identity = f"new_{t}_{source_id}"
            private[identity] = truth.arrival[source_id, t], truth.fills[source_id, t]
            pipeline.append({"id": identity, "known_at": now, "source": source_id, "revision": 1,
                "ordered": q, "confirmed": q, "shipped": 0., "received": 0., "rejected": 0.,
                "expected_accepted_remaining": q * source.fill_mean, "placed_at": req.as_of, "confirmed_at": None,
                "departed_at": None, "current_eta": req.as_of + timedelta(days=expected * req.period_days),
                "stage": "placed", "carrier": "unknown", "cancellation_status": "no_new_amendment_quote",
                "prepaid_per_remaining_unit": 0., "allow_split_amendments": False,
                "options": [{"id": "keep", "known_at": now, "action": "keep", "due_in": max(0, expected - 1),
                   "fee_per_unit": 0., "remaining_invoice_per_unit": 0., "payment_due_in": 0,
                   "max_quantity": q, "deadline": now, "allowed_stages": ["placed"], "contract_reference": "committed_after_review"}]})
        data["pipeline"] = pipeline
        # Completed and open observations both enter the survival risk set, one current record per PO.
        data["shipment_history"] = [r.model_dump() if hasattr(r, "model_dump") else r for r in shipment_history if not (hasattr(r, "id") and r.id.startswith("censored-"))]
        data["shipment_history"] += [{"id": "censored-" + p["id"], "known_at": now, "source": p["source"],
                                      "elapsed_days": (now - p["placed_at"]).days, "arrived": False,
                                      "stage": p["stage"], "carrier": p["carrier"]} for p in pipeline]
        data["inbound_transfers"] = [{"id": f"inbound-{n}", "known_at": now, "sku": sku,
             # an in-flight transfer normally has a lane; a declared inbound without one (an isolated-branch
             # projection, P2) keeps its destination as origin rather than failing the replay
             "origin": next((a.origin for a in req.transfers if a.sku == sku and a.destination == location), location),
             "destination": location, "accepted_quantity": quantity, "due_in": max(0, due - 1), "expires_in": expiry - 1}
            for n, (sku, location, expiry, due, quantity, kind) in enumerate(outcome["pending"]) if kind == "transfer"]
        future = outcome["future_payments"]
        if rolling:
            # Constant planning horizon: declared period data roll forward by repeating their last declared
            # value; every committed payment is kept and lands in `other_payments` at its due period.
            next_h = H
            data["horizon"] = H
            for name in ("sources", "resources"):
                data[name] = [{**r.model_dump(), "capacity_by_period": [*r.capacity_by_period[1:], r.capacity_by_period[-1]]} for r in getattr(req, name)]
            for k, v in future.items():
                if k > H:
                    deferred[t + k] = deferred.get(t + k, 0.) + v
            other = [req.liquidity.other_payments[k] + future.get(k, 0.) for k in range(1, H)] + [future.get(H, 0.)]
            for j in range(H):
                other[j] += deferred.pop(t + 1 + j, 0.)
            liquidity = req.liquidity.model_dump()
            liquidity.update(known_at=now, opening_cash=outcome["trace"][0]["cash"], opening_debt=outcome["trace"][0]["debt"],
                             known_receivables=[*req.liquidity.known_receivables[1:], req.liquidity.known_receivables[-1]],
                             other_payments=tuple(other))
        else:
            # Replay does not fabricate new financial data: finite input horizon shrinks.
            next_h = H - 1
            data["horizon"] = H - 1
            for name in ("sources", "resources"):
                data[name] = [{**r.model_dump(), "capacity_by_period": r.capacity_by_period[1:]} for r in getattr(req, name)]
            liquidity = req.liquidity.model_dump()
            liquidity.update(known_at=now, opening_cash=outcome["trace"][0]["cash"], opening_debt=outcome["trace"][0]["debt"],
                             known_receivables=req.liquidity.known_receivables[1:],
                             other_payments=tuple(req.liquidity.other_payments[k] + future.get(k, 0.) for k in range(1, H)))
        data["liquidity"] = liquidity
        data["events"] = [{**e.model_dump(), "start": max(0, e.start - 1), "end": e.end - 1} for e in req.events if e.end >= 1]
        data["order_lines"] = [{**line.model_dump(), "due_in": line.due_in - 1} for line in req.order_lines if line.due_in >= 1]
        # The operator executes the accepted plan: its remaining purchase schedule, shifted one
        # period, is the declared incumbent for the next review. A retained proxy carries nothing.
        if req.carry_incumbent and method in {"gated", "gated_pr30", "gated_pr24", "gated_v4", "gated_v5"} and solution.warnings and solution.warnings[0] == "PENDING_REVIEW":
            data["incumbent_orders"] = [{"known_at": now, "source": source_id, "period": period - 1, "quantity": q}
                                        for (source_id, period), q in solution.purchases.items() if period >= 1 and period - 1 < next_h and q > 0]
        else:
            data["incumbent_orders"] = []
        req = Request.model_validate(data)
    total_components["opening_assets"] = first_assets or 0.
    total_components["closing_assets"] = last_assets
    # Finite-horizon continuation value of the residual stock (evaluation only, `terminal.py`): the
    # ledger above keeps the declared salvage credit; this reports what the stock is worth beyond the
    # window and the adjustment, so a window ending inside a lot cycle can be read either way.
    from zaad.full.terminal import continuation_value
    last = reviews_log[-1]["settlement"] if reviews_log else {"end_stock": [], "pending": []}
    terminal = continuation_value(req, last.get("end_stock", []), last.get("pending", []), forecast_all(req))
    return {"status": "COMPLETE", "method": method, "reviews": reviews_log, "ledger": total_components,
            "economic_cost": sum(total_components.values()), "information_boundary": "new demand/supply evidence enters after observation only",
            "terminal_continuation": terminal, "economic_cost_continuation": sum(total_components.values()) + terminal["adjustment"],
            "horizon_note": "shrinking replay horizon; production replanning accepts a fresh full-horizon operator snapshot"}
