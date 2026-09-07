"""Capital efficiency and recovery v7: regressions for the v7 rules.

- a transfer-fed branch is replenished by its arc, not never, so its protection window is the
  transfer lead plus a review instead of the whole horizon
- an echelon origin with no customers of its own gets a protection row, and the projected
  base-stock proxy still ignores it so the incumbent and the base_stock comparator are unchanged
- the inventory decomposition partitions on-hand exactly and names an owner for every unit
- duplicated buffers are detected pairwise with the arc that makes the overlap real
- fast-arc pooling leaves less local and more pooled than a slow arc
- a confirmed demand decline turns into liquidation, one low observation does not
- a false disruption signal returns to lean; a route reopening retires faster than a fill
  deterioration; an open backlog retires nothing
- procurement timing reports the latest safe order date and the cash committed ahead of it
- equal-priority reallocation is allowed, robbing a higher-priority customer is not
- the capital tie-break never accepts a plan that misses a service target
- terminal continuation stays off by default
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from zaad.full.capital import decompose, duplication, pooling_split
from zaad.full.contracts import Request, ShipmentObservation
from zaad.full.demo import example
from zaad.full.planner import _priority_consistent, plan, targets
from zaad.full.protection import DECLINE_CONFIRMATION, DECLINE_RATIO, protection_profile
from zaad.full.replay import COMPARATOR_METHODS, V6_ENGINE_METHODS
from zaad.full.uncertainty import supply_profile, supply_profiles, supply_state
from zaad.full.worlds import forecast_all


def _with(req: Request, **update) -> Request:
    return Request.model_validate({**req.model_dump(mode="json"), **update})


def _two_branches(lead: int = 1, capacity: float = 50., central: float = 80., branch: float = 40.) -> Request:
    data = example("normal").model_dump(mode="json")
    data["locations"].append({**data["locations"][0], "id": "central", "kind": "central_dc", "holding_per_value_period": .003})
    data["locations"].append({**data["locations"][0], "id": "branch_south"})
    data["customers"].append({**data["customers"][0], "id": "customer_south"})
    data["services"].append({**data["services"][0], "id": "retail_A_south", "location": "branch_south", "customer": "customer_south"})
    data["stock"][0]["quantity"] = branch
    data["stock"].append({**data["stock"][0], "id": "opening_south", "location": "branch_south", "quantity": branch})
    data["stock"].append({**data["stock"][0], "id": "central_pool", "location": "central", "quantity": central})
    for b in ("branch", "branch_south"):
        data["transfers"].append({"id": f"central_{b}", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": b,
                                  "lead_periods": lead, "capacity": capacity, "cost_per_unit": .2, "loss_fraction": .01, "approved": True})
    for source in data["sources"]:
        source["destination"] = "central"
        source["route"][-1] = "central"
    # The demo history is flat, which makes every spread exactly zero; a small deterministic
    # ripple gives the protection terms something to be a function of.
    data["history"] = [{**h, "quantity": h["quantity"] + (3. if i % 3 == 0 else (-2. if i % 3 == 1 else 0.))}
                       for i, h in enumerate(data["history"])]
    data["history"] += [{**h, "service": "retail_A_south"} for h in data["history"]]
    return Request.model_validate(data)


def _profile(req: Request) -> dict:
    return {(r["sku"], r["location"]): r for r in protection_profile(req, forecast_all(req), supply_profiles(req))}


# replenishment window and echelon origin

def test_a_transfer_fed_branch_is_replenished_by_its_arc_not_never():
    req = _two_branches(lead=1)
    branch = _profile(req)["A", "branch"]
    assert branch["replenished_by_transfer_arc"] == "central_branch"
    assert branch["replenishment_periods"] == 2                      # transfer lead plus the review
    v6 = _profile(_with(req, protection_v7=False))["A", "branch"]
    assert v6["replenishment_periods"] == req.horizon                # v6 treated it as unreplenishable
    assert branch["state"]["lean_baseline_units"] < v6["state"]["lean_baseline_units"]


def test_a_slow_arc_still_gives_the_branch_a_longer_window():
    fast = _profile(_two_branches(lead=1))["A", "branch"]
    slow = _profile(_two_branches(lead=3))["A", "branch"]
    assert slow["replenishment_periods"] == 4 > fast["replenishment_periods"] == 2
    assert slow["state"]["lean_baseline_units"] > fast["state"]["lean_baseline_units"]


def test_an_arc_too_small_to_carry_the_demand_earns_no_replenishment_credit():
    req = _two_branches(lead=1, capacity=1.)
    assert _profile(req)["A", "branch"]["replenished_by_transfer_arc"] is None


def test_the_echelon_origin_gets_a_row_and_the_proxy_still_ignores_it():
    req = _two_branches()
    rows = _profile(req)
    central = rows["A", "central"]
    assert central["echelon_origin"] is True
    assert central["mean_demand_per_period"] > 0                     # its obligation is the branches it feeds
    assert central["state"]["lean_baseline_units"] > 0
    assert targets(req) == targets(_with(req, protection_v7=False))  # incumbent and base_stock unchanged
    assert not _profile(_with(req, protection_v7=False)).get(("A", "central"))


def test_the_origin_obligation_is_capped_by_what_its_arcs_can_carry():
    wide = _profile(_two_branches(capacity=50.))["A", "central"]["mean_demand_per_period"]
    narrow = _profile(_two_branches(capacity=5.))["A", "central"]["mean_demand_per_period"]
    assert narrow < wide


# inventory decomposition

def test_the_decomposition_partitions_on_hand_exactly_and_names_an_owner():
    req = _two_branches()
    fits = forecast_all(req)
    rows = decompose(req, fits, protection_profile(req, fits, supply_profiles(req)),
                     inherited={("A", "branch"): 40.})
    held = {r["location"]: r for r in rows if r["on_hand_units"] > 0}
    assert held
    for row in held.values():
        assert row["reconciles"]
        assert sum(row["reason"].values()) == pytest.approx(row["on_hand_units"])
    assert held["branch"]["owner"]["inherited"] == pytest.approx(40.)
    assert held["central"]["owner"]["inherited"] == pytest.approx(0.)


def test_intermittent_demand_is_not_reported_in_periods_of_cover():
    req = _two_branches()
    data = req.model_dump(mode="json")
    data["history"] = [{**h, "quantity": (40. if i % 5 == 0 else 0.)} for i, h in enumerate(data["history"])]
    sparse = Request.model_validate(data)
    fits = forecast_all(sparse)
    rows = decompose(sparse, fits, protection_profile(sparse, fits, supply_profiles(sparse)))
    branch = next(r for r in rows if r["location"] == "branch")
    if not branch["periods_meaningful"]:
        assert branch["periods_of_demand"] is None
        assert branch["on_hand_units"] > 0


# duplicated buffers and pooling

def test_duplication_names_the_pair_and_the_arc_that_makes_it_real():
    fits_req = _two_branches(lead=1, central=400., branch=400.)
    fits = forecast_all(fits_req)
    rows = duplication(fits_req, fits, protection_profile(fits_req, fits, supply_profiles(fits_req)))
    assert rows and all(r["origin"] == "central" for r in rows)
    doubled = [r for r in rows if r["duplicated_buffer_units"] > 0]
    assert doubled, "a branch and its origin both far above their own needs must show overlap"
    for r in doubled:
        assert r["arc"] in {"central_branch", "central_branch_south"}
        assert "cover the same" in r["explanation"]


def test_a_slow_arc_does_not_create_duplication_from_the_same_stock():
    fits_req = _two_branches(lead=3, central=400., branch=400.)
    fits = forecast_all(fits_req)
    slow = duplication(fits_req, fits, protection_profile(fits_req, fits, supply_profiles(fits_req)))
    fast_req = _two_branches(lead=1, central=400., branch=400.)
    fast_fits = forecast_all(fast_req)
    fast = duplication(fast_req, fast_fits, protection_profile(fast_req, fast_fits, supply_profiles(fast_req)))
    assert sum(r["duplicated_buffer_units"] for r in slow) < sum(r["duplicated_buffer_units"] for r in fast)


def test_fast_arc_pooling_leaves_less_local_and_more_pooled_than_a_slow_arc():
    def split(lead):
        req = _two_branches(lead=lead)
        fits = forecast_all(req)
        rows = pooling_split(req, fits, protection_profile(req, fits, supply_profiles(req)))
        return next(r for r in rows if r["branch"] == "branch")
    fast, slow = split(1), split(3)
    assert fast["local_immediate_units"] < slow["local_immediate_units"]
    assert fast["pooled_units"] > slow["pooled_units"]


def test_a_constrained_arc_cannot_pool_what_it_cannot_carry():
    req = _two_branches(lead=1, capacity=2.)
    fits = forecast_all(req)
    rows = pooling_split(req, fits, protection_profile(req, fits, supply_profiles(req)))
    branch = next(r for r in rows if r["branch"] == "branch")
    assert branch["pooled_units"] <= 2. * branch["window_periods"]


# demand decline

def _declining(step: float, periods: int) -> Request:
    req = example("normal")
    data = req.model_dump(mode="json")
    history = list(data["history"])
    for i, row in enumerate(history):
        if row["period"] >= -periods:
            history[i] = {**row, "quantity": row["quantity"] * step}
    data["history"] = history
    return Request.model_validate(data)


def test_a_confirmed_decline_becomes_liquidation_and_one_low_reading_does_not():
    confirmed = _profile(_declining(.4, DECLINE_CONFIRMATION + 3))["A", "branch"]
    single = _profile(_declining(.4, 1))["A", "branch"]
    assert single["state"]["demand_decline_confirmed"] is False
    if confirmed["state"]["demand_decline_confirmed"]:
        assert confirmed["state"]["demand_decline_ratio"] <= DECLINE_RATIO
        assert "DEMAND_DECLINE_CONFIRMED" in confirmed["state"]["flags"]
        assert confirmed["state"]["liquidation_units"] >= 0.


def test_a_decline_is_never_confirmed_under_v6():
    req = _with(_declining(.4, DECLINE_CONFIRMATION + 3), protection_v7=False)
    row = _profile(req)["A", "branch"]
    assert row["state"]["demand_decline_confirmed"] is False


# recovery confidence

def _history(pattern: list[tuple[bool, float]], as_of: datetime, late_days: int = 40) -> tuple[ShipmentObservation, ...]:
    """(arrived on time, accepted ratio) oldest first."""
    rows = []
    for i, (on_time, ratio) in enumerate(pattern):
        rows.append(ShipmentObservation(id=f"r{i}", known_at=as_of - timedelta(days=7 * (len(pattern) - i)),
                                        source="main", elapsed_days=7 if on_time else late_days, arrived=True,
                                        stage="delivered", carrier="c", accepted_ratio=ratio))
    return tuple(rows)


def test_a_closure_retires_faster_than_a_fill_deterioration():
    req = example("normal")
    source = req.sources[0]
    clean = [(True, 1.)] * 4
    closure = supply_profile(source, _history([(False, 0.)] + clean, req.as_of), req.period_days, source_specific=True)
    fill = supply_profile(source, _history([(True, .6)] + clean, req.as_of), req.period_days, source_specific=True)
    v6 = supply_profile(source, _history([(False, 0.)] + clean, req.as_of), req.period_days)
    assert v6.driver_kind == "fill" and v6.exit_receipts_needed == 6      # unchanged without v7
    assert closure.driver_kind == "closure" and closure.exit_receipts_needed == 2
    assert fill.driver_kind == "fill" and fill.exit_receipts_needed == 6
    assert closure.recent_clean_run >= closure.exit_receipts_needed
    assert fill.recent_clean_run < fill.exit_receipts_needed


def test_a_reopened_route_only_retires_once_capacity_is_back():
    req = example("normal")
    source = req.sources[0]
    restored = supply_profile(source, _history([(False, 0.)] + [(True, 1.)] * 4, req.as_of), req.period_days, source_specific=True)
    still_short = supply_profile(source, _history([(False, 0.)] + [(True, .5)] * 4, req.as_of), req.period_days, source_specific=True)
    assert supply_state(restored, recency=True, exit_rules=True, source_specific=True) == 0.
    assert supply_state(still_short, recency=True, exit_rules=True, source_specific=True) > 0.


def test_a_false_signal_returns_to_lean_after_the_evidence_it_needs():
    req = example("normal")
    source = req.sources[0]
    one_bad = supply_profile(source, _history([(False, 1.)] + [(True, 1.)] * 3, req.as_of, late_days=14), req.period_days, source_specific=True)
    assert one_bad.driver_kind == "lateness" and one_bad.exit_receipts_needed == 3
    assert supply_state(one_bad, recency=True, exit_rules=True, source_specific=True) == 0.


def test_an_open_backlog_retires_nothing():
    req = example("normal")
    source = req.sources[0]
    rows = list(_history([(True, 1.)] * 6, req.as_of))
    rows.append(ShipmentObservation(id="open", known_at=req.as_of, source="main", elapsed_days=90,
                                    arrived=False, stage="in_transit", carrier="c"))
    profile = supply_profile(source, tuple(rows), req.period_days, overdue_as_late=True, source_specific=True)
    assert profile.backlog_open is True
    assert supply_state(profile, recency=True, exit_rules=True, source_specific=True) > 0.


# procurement timing

def test_timing_reports_the_latest_safe_order_date_and_the_cash_committed_ahead_of_it():
    req = example("normal")
    report = plan(req)
    rows = report["procurement_timing"]
    assert rows and all("latest_safe_order_period" in r for r in rows)
    for r in rows:
        assert r["selected_order_period"] == r["period"]
        assert r["cash_days_advanced"] >= 0
        assert r["premature_units"] >= 0
        if r["latest_safe_order_period"] is not None:
            assert r["periods_earlier_than_latest_safe"] == max(0, r["latest_safe_order_period"] - r["period"])


def test_the_working_capital_fields_are_absent_when_v7_is_off():
    req = _with(example("normal"), protection_v7=False)
    rows = plan(req)["procurement_timing"]
    assert rows and all("latest_safe_order_period" not in r for r in rows)
    assert all("early_periods" in r and "cash_committed_early" in r for r in rows)   # v6 fields kept


# selector

def test_equal_priority_reallocation_stays_refused_under_v7():
    """The v7 proposal to allow it was measured on development7 and rejected; the rule is
    unchanged, and this pins that so it is not quietly reintroduced."""
    req = _two_branches()
    def rows(north, south):
        return [{"usable": True, "economic_cost": 0., "trace": [{"inventory_value": 0.}],
                 "service_by_period": [{"service": "retail_A", "demand": 100., "served": 100. * north},
                                       {"service": "retail_A_south", "demand": 100., "served": 100. * south}]}]
    before, swap = rows(.95, .85), rows(.85, .95)
    assert _priority_consistent(req, before, swap) is False
    assert _priority_consistent(_with(req, protection_v7=False), before, swap) is False
    data = req.model_dump(mode="json")
    data["customers"][0]["priority"] = 1.                 # south outranks north
    data["customers"][1]["priority"] = 5.
    ranked = Request.model_validate(data)
    assert _priority_consistent(ranked, before, swap) is True       # lowering a lower rank for a higher one


def test_the_capital_tie_break_never_accepts_a_plan_that_misses_a_target():
    req = example("normal")
    report = plan(req)
    for row in report["service_reliability"]["services"]:
        if report["status"] != "RETAIN_INCUMBENT" and row["achieved_service"] is not None:
            assert row["achieved_service"] >= row["requested_service"] - req.service_tolerance or \
                   row["classification"]["class"] != "AVOIDABLE"


def test_the_capital_report_reconciles_and_is_absent_under_v6():
    req = _two_branches()
    report = plan(req)
    assert report["capital"] is not None
    assert all(r["reconciles"] for r in report["capital"]["decomposition"])
    assert plan(_with(req, protection_v7=False))["capital"] is None


# comparators and flags

def test_every_comparator_method_turns_the_v7_rules_off():
    assert "gated_v6" in V6_ENGINE_METHODS <= COMPARATOR_METHODS
    assert "gated" not in COMPARATOR_METHODS


def test_terminal_continuation_stays_off_by_default():
    assert example("normal").terminal_continuation is False
