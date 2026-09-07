"""Multi-echelon placement and recovery v6: regressions for the v6 rules.

- duplicate central/branch buffers are counted only when the transfer can land inside the window
- pooled versus local stock follows the transfer lead, capacity and the branch SLA (echelon comparator)
- a shared central shortage caps what the comparator can send
- terminal continuation keeps a short-horizon plan from idling when demand continues past it
- recovery exit: late-only trouble retires after three clean receipts, short receipts after six,
  an open backlog never retires the driver
- the excess penalty runs temporary stock down instead of replenishing it
- the procurement-timing audit reports early periods and cash committed early
"""
from __future__ import annotations

from datetime import timedelta


from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.echelon import echelon_targets
from zaad.full.model import solve
from zaad.full.planner import plan, procurement_timing
from zaad.full.protection import protection_profile
from zaad.full.replay import COMPARATOR_METHODS
from zaad.full.uncertainty import supply_profile, supply_profiles, supply_state
from zaad.full.worlds import draw, forecast_all


def _with(req: Request, **update) -> Request:
    return Request.model_validate({**req.model_dump(mode="json"), **update})


def _two_branches(lead: int = 1, capacity: float = 50., central: float = 80., branch: float = 40., south_target: float = .95,
                  north_target: float = .95) -> Request:
    """One central DC fed by the supplier, two branches served only by transfer (the v6 benchmark network)."""
    data = example("normal").model_dump(mode="json")
    data["locations"].append({**data["locations"][0], "id": "central", "kind": "central_dc", "holding_per_value_period": .003})
    data["locations"].append({**data["locations"][0], "id": "branch_south"})
    data["customers"].append({**data["customers"][0], "id": "customer_south"})
    data["services"][0]["target"] = north_target
    data["services"].append({**data["services"][0], "id": "retail_A_south", "location": "branch_south", "customer": "customer_south", "target": south_target})
    data["stock"][0]["quantity"] = branch
    data["stock"].append({**data["stock"][0], "id": "opening_south", "location": "branch_south", "quantity": branch})
    data["stock"].append({**data["stock"][0], "id": "central_pool", "location": "central", "quantity": central})
    for b in ("branch", "branch_south"):
        data["transfers"].append({"id": f"central_{b}", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": b,
                                  "lead_periods": lead, "capacity": capacity, "cost_per_unit": .2, "loss_fraction": .01, "approved": True})
    for source in data["sources"]:
        source["destination"] = "central"
        source["route"][-1] = "central"
    data["history"] += [{**h, "service": "retail_A_south"} for h in data["history"]]
    return Request.model_validate(data)


def _profile(req: Request) -> dict:
    return {(r["sku"], r["location"]): r for r in protection_profile(req, forecast_all(req), supply_profiles(req))}


# duplicate buffers

def test_duplicate_buffer_is_counted_only_when_the_transfer_lands_inside_the_window():
    fast = _profile(_two_branches(lead=1))[("A", "branch")]["state"]
    assert fast["duplicated_buffer_units"] > 0 and "buffer the same demand spread twice" in fast["duplicated_buffer_explanation"]
    slow = _profile(_two_branches(lead=4))[("A", "branch")]["state"]
    assert slow["duplicated_buffer_units"] == 0.
    tiny = _profile(_two_branches(lead=1, capacity=5.))[("A", "branch")]["state"]
    assert tiny["duplicated_buffer_units"] == 0.
    v5 = _profile(_with(_two_branches(lead=1), protection_v6=False))[("A", "branch")]["state"]
    assert v5["duplicated_buffer_units"] == 0.


def test_no_duplicate_when_the_central_holds_nothing():
    empty = _profile(_two_branches(lead=1, central=0.))[("A", "branch")]["state"]
    assert empty["duplicated_buffer_units"] == 0.


# echelon comparator: pooled versus local

def test_echelon_comparator_keeps_more_local_when_the_transfer_is_slower():
    fast, slow = echelon_targets(_two_branches(lead=1)), echelon_targets(_two_branches(lead=3))
    fast_transfer = sum(v for k, v in fast.items() if k[0] == "transfer" and k[2] <= 2)
    slow_transfer = sum(v for k, v in slow.items() if k[0] == "transfer" and k[2] <= 2)
    assert slow_transfer > fast_transfer          # a slower arc needs a higher local base stock


def test_echelon_comparator_respects_transfer_capacity_and_branch_sla():
    capped = echelon_targets(_two_branches(lead=1, capacity=12.))
    assert all(v <= 12. + 1e-9 for k, v in capped.items() if k[0] == "transfer")
    strict = echelon_targets(_two_branches(lead=1, south_target=.99, north_target=.9))
    south = sum(v for k, v in strict.items() if k[0] == "transfer" and k[1] == "central_branch_south" and k[2] <= 3)
    north = sum(v for k, v in strict.items() if k[0] == "transfer" and k[1] == "central_branch" and k[2] <= 3)
    assert south >= north


def test_echelon_comparator_cannot_send_what_the_central_does_not_hold():
    short = echelon_targets(_two_branches(lead=1, central=10.))
    first = sum(v for k, v in short.items() if k[0] == "transfer" and k[2] == 0)
    assert first <= 10. + 1e-9
    assert short[("main", 0)] > 0                  # and it buys to refill the echelon


def test_echelon_comparator_runs_through_the_common_model():
    req = _two_branches()
    sol = solve(req, draw(req, 1, 1, deterministic=True), targets=echelon_targets(req))
    assert sol.status == "OPTIMAL"
    assert sum(sol.transfers.values()) > 0
    assert "echelon_base_stock" not in COMPARATOR_METHODS   # it is a comparator method but not a gated engine profile


# terminal continuation

def test_terminal_continuation_prevents_late_horizon_idleness():
    req = _with(example("normal"), horizon=3)
    data = req.model_dump(mode="json")
    for s in data["sources"]:
        s["capacity_by_period"] = s["capacity_by_period"][:3]
        s["lead_days"] = 14                         # two-period lead: an order now lands in the last period
    for r in data["resources"]:
        r["capacity_by_period"] = r["capacity_by_period"][:3]
    data["liquidity"]["known_receivables"] = data["liquidity"]["known_receivables"][:3]
    data["liquidity"]["other_payments"] = data["liquidity"]["other_payments"][:3]
    data["stock"][0]["quantity"] = 45.               # two periods of demand on hand, nothing after
    req = Request.model_validate(data)
    world = draw(req, 1, 1, deterministic=True)
    idle = solve(req, world, service_floor=False)
    continuing = solve(req, world, service_floor=False, continuation={("A", "branch"): (60., 6.)})
    assert continuing.status == "OPTIMAL"
    assert sum(continuing.purchases.values()) > sum(idle.purchases.values())


# recovery exit

def _history(req: Request, pattern: str, overdue: int = 0) -> Request:
    """pattern: one char per receipt oldest -> newest: c clean, l late-but-full, s short."""
    data = req.model_dump(mode="json")
    main = next(s for s in data["sources"] if s["id"] == "main")
    now = req.as_of
    history = [o for o in data["shipment_history"] if o["source"] != "main"]
    for i, ch in enumerate(pattern):
        history.append({"id": f"r{i}", "known_at": (now - timedelta(days=7 * (len(pattern) - i) + 1)).isoformat(), "source": "main",
                        "elapsed_days": main["lead_days"] + (21 if ch in "ls" else 0), "arrived": True,
                        "stage": "placed", "carrier": "unknown", "accepted_ratio": .5 if ch == "s" else 1.})
    for j in range(overdue):
        history.append({"id": f"open{j}", "known_at": now.isoformat(), "source": "main", "elapsed_days": main["lead_days"] + 21,
                        "arrived": False, "stage": "placed", "carrier": "unknown"})
    return Request.model_validate({**data, "shipment_history": history})


def _state(req: Request) -> float:
    main = next(s for s in req.sources if s.id == "main")
    profile = supply_profile(main, req.shipment_history, req.period_days, overdue_as_late=True)
    return supply_state(profile, recency=True, exit_rules=True), profile


def test_late_only_trouble_retires_after_three_clean_receipts_short_receipts_after_six():
    base = example("normal")
    two, three = _state(_history(base, "cccclllcc"))[0], _state(_history(base, "ccccllccc"))[0]
    assert two > 0 and three == 0.
    five, six = _state(_history(base, "cccsssccccc"))[0], _state(_history(base, "cccssscccccc"))[0]
    assert five > 0 and six == 0.
    _, profile = _state(_history(base, "cccssscccccc"))
    assert profile.exit_receipts_needed == 6 and profile.driver_kind == "fill"


def test_open_backlog_blocks_the_recovery_exit():
    base = example("normal")
    retired, profile = _state(_history(base, "ccccllcccc"))
    assert retired == 0. and not profile.backlog_open
    blocked, profile = _state(_history(base, "ccccllcccc", overdue=2))
    assert blocked > 0 and profile.backlog_open and profile.driver_kind == "backlog"
    v5 = supply_state(profile, recency=True, exit_rules=False)
    assert v5 >= blocked


def test_exit_fields_are_reported_on_the_protection_state():
    req = _history(example("normal"), "ccccssscc")
    state = _profile(req)[("A", "branch")]["state"]
    exit_info = state["exit"]
    assert exit_info["driver_kind"] == "fill" and exit_info["receipts_needed"] == 6 and exit_info["recovery_evidence_receipts"] == 2
    assert exit_info["reviews_remaining_until_lean_eligible"] == 4 and exit_info["last_evidence"]


# temporary protection liquidation

def test_excess_penalty_runs_temporary_stock_down_instead_of_replenishing():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["stock"][0]["quantity"] = 120.              # six periods of demand inherited
    req = Request.model_validate(data)
    world = draw(req, 1, 1, deterministic=True)
    plain = solve(req, world, service_floor=True)
    penalised = solve(req, world, service_floor=True, excess_penalty={("A", "branch"): (30., 5. * .01 * 2.)})
    assert penalised.status == "OPTIMAL"
    assert sum(penalised.purchases.values()) <= sum(plain.purchases.values()) + 1e-6
    assert penalised.projected_service["retail_A"] >= .95 - 1e-6


# procurement timing

def test_procurement_timing_reports_early_periods_and_cash():
    req = example("normal")
    report = plan(req)
    timing = report["procurement_timing"]
    assert isinstance(timing, list)
    for row in timing:
        assert row["early_periods"] >= 0 and row["cash_committed_early"] >= 0
        assert row["arrival_period"] >= row["period"]
    fits = forecast_all(req)
    assert procurement_timing(req, fits, None) == []
    v5 = plan(_with(req, protection_v6=False))
    assert v5["procurement_timing"] is None


def test_network_service_frontier_is_reported_per_service():
    report = plan(_two_branches())
    rows = {r["service"]: r for r in report["network_service"]}
    assert set(rows) == {"retail_A", "retail_A_south"}
    for r in rows.values():
        assert r["requested"] in (.95,) and r["expected_achieved"] is not None
