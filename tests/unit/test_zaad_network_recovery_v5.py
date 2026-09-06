"""Network / recovery v5: regressions for the v5 rules on top of the v4 calibrated protection.

- supply state retires on a recent clean run instead of waiting for the whole history to dilute
- flexibility credit only for an alternate that can land inside the service window
- echelon accounting partitions the recommended protection (local / pooled / source / temporary)
- state transitions carry an explanation; selector rejections carry deltas
- the v5 ranking never buys inventory it does not need on a quiet cell (v5 burden <= v4 burden)
- the v4 comparator path (protection_v5=False) is still reachable from the replay method table
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.planner import plan
from zaad.full.protection import protection_profile
from zaad.full.replay import PR30_METHODS, V4_METHODS
from zaad.full.uncertainty import RECENT_RECEIPTS, resilience, supply_profile, supply_profiles, supply_state
from zaad.full.worlds import forecast_all


def _with(req: Request, **update) -> Request:
    return Request.model_validate({**req.model_dump(mode="json"), **update})


def _shipments(req: Request, late_tail: int, late_days: int = 21, short: bool = False, n: int = 14,
               middle_late: int = 0, overdue_open: int = 0) -> Request:
    """Give the main source a receipt history of `n` records: clean, except the last `late_tail`
    (late and optionally short), `middle_late` late records just before the recent window, and
    `overdue_open` orders still outstanding past the declared lead."""
    data = req.model_dump(mode="json")
    main = next(s for s in data["sources"] if s["id"] == "main")
    now = req.as_of
    history = [o for o in data["shipment_history"] if o["source"] != "main"]
    for i in range(n):
        late = i >= n - late_tail or (n - late_tail - RECENT_RECEIPTS - middle_late <= i < n - late_tail - RECENT_RECEIPTS)
        history.append({"id": f"rcpt-{i}", "known_at": (now - timedelta(days=7 * (n - i) + 1)).isoformat(), "source": "main",
                        "elapsed_days": main["lead_days"] + main.get("dispatch_days", 0) + (late_days if late else 0), "arrived": True,
                        "stage": "placed", "carrier": "unknown", "accepted_ratio": .6 if (late and short and i >= n - late_tail) else 1.})
    for j in range(overdue_open):
        history.append({"id": f"open-{j}", "known_at": now.isoformat(), "source": "main",
                        "elapsed_days": main["lead_days"] + main.get("dispatch_days", 0) + late_days, "arrived": False,
                        "stage": "placed", "carrier": "unknown"})
    return Request.model_validate({**data, "shipment_history": history})


def _main_profile(req: Request, overdue_as_late: bool = True):
    main = next(s for s in req.sources if s.id == "main")
    return supply_profile(main, req.shipment_history, req.period_days, overdue_as_late=overdue_as_late)


def _po(req: Request, po_id: str, age_days: int, quantity: float = 60.) -> dict:
    """An open order from main, placed `age_days` ago, shaped the way replay records one."""
    main = next(s for s in req.sources if s.id == "main")
    placed = req.as_of - timedelta(days=age_days)
    return {"id": po_id, "known_at": req.as_of.isoformat(), "source": "main", "revision": 1,
            "ordered": quantity, "confirmed": quantity, "shipped": 0., "received": 0., "rejected": 0.,
            "expected_accepted_remaining": quantity * main.fill_mean, "placed_at": placed.isoformat(), "confirmed_at": None,
            "departed_at": None, "current_eta": (placed + timedelta(days=main.lead_days)).isoformat(),
            "stage": "placed", "carrier": "unknown", "cancellation_status": "no_new_amendment_quote",
            "prepaid_per_remaining_unit": 0., "allow_split_amendments": False,
            "options": [{"id": "keep", "known_at": req.as_of.isoformat(), "action": "keep", "due_in": 0,
                         "fee_per_unit": 0., "remaining_invoice_per_unit": 0., "payment_due_in": 0,
                         "max_quantity": quantity, "deadline": req.as_of.isoformat(), "allowed_stages": ["placed"],
                         "contract_reference": "committed_after_review"}]}


# supply state recency

def test_supply_state_retires_after_a_recent_clean_run():
    clean = _main_profile(_shipments(example("normal"), late_tail=0))
    assert clean.recent_records == RECENT_RECEIPTS and clean.recent_late_probability == 0.
    mixed = _main_profile(_shipments(example("normal"), late_tail=0, middle_late=4))
    # Late receipts just before the recent window: the whole-history late probability still
    # scores them, the recent-receipt state has retired them.
    assert mixed.late_probability > 0.
    assert mixed.recent_late_probability == 0.
    assert supply_state(mixed, recency=True) < supply_state(mixed, recency=False)


def test_supply_state_reacts_to_a_recent_late_run():
    profile = _main_profile(_shipments(example("normal"), late_tail=4, short=True))
    assert profile.recent_late_probability >= .5 and profile.recent_partial_probability >= .5
    assert supply_state(profile, recency=True) >= .5


def test_overdue_open_orders_count_as_late_only_under_v5():
    req = _shipments(example("normal"), late_tail=0, overdue_open=4)
    v5 = _main_profile(req, overdue_as_late=True)
    v4 = _main_profile(req, overdue_as_late=False)
    assert v5.recent_late_probability >= .5 and v4.recent_late_probability == 0.
    assert supply_state(v5, recency=True) > supply_state(v4, recency=True)


def test_overdue_order_survival_moves_arrival_mass_outside_the_horizon():
    from zaad.full.worlds import draw
    req = example("normal")
    data = req.model_dump(mode="json")
    main = next(s for s in data["sources"] if s["id"] == "main")
    stale = _po(req, "po-stale", main["lead_days"] + 60)
    overdue = Request.model_validate({**data, "pipeline": [stale]})
    v5 = draw(overdue, 1, 12)
    v4 = draw(_with(overdue, protection_v5=False), 1, 12)
    outside_v5 = sum(w.po_due["po-stale"] > overdue.horizon for w in v5)
    outside_v4 = sum(w.po_due["po-stale"] > overdue.horizon for w in v4)
    assert outside_v5 > outside_v4
    fresh = Request.model_validate({**data, "pipeline": [_po(req, "po-fresh", 1)]})
    assert all(w.po_due["po-fresh"] <= fresh.horizon for w in draw(fresh, 1, 12))


# flexibility credit

def test_alternate_inside_the_service_window_earns_credit_and_a_slow_one_does_not():
    assert resilience(4, 2., 0., 100., alternative_inside_window=True) == .5
    assert resilience(4, 2., 0., 100., alternative_inside_window=False) == 0.
    assert resilience(4, 2., 0., 100., alternative_inside_window=None) == .5     # v4 semantics unchanged
    assert resilience(2, 2., 0., 100., alternative_inside_window=True) == 1.


def _profile(req: Request) -> list[dict]:
    return protection_profile(req, forecast_all(req), supply_profiles(req))


def test_flexibility_credit_only_when_the_alternate_can_arrive_in_time():
    req = example("normal")
    data = req.model_dump(mode="json")
    main = next(s for s in data["sources"] if s["id"] == "main")
    alt = {**main, "id": "alternate", "supplier": "alternate_supplier", "route": ["alternate_supplier"] + list(main["route"][1:]),
           "capacity_by_period": [200.] * len(main["capacity_by_period"]), "lead_days": main["lead_days"], "approved": True,
           "unit_price": main["unit_price"] + .5}      # a little dearer, so main stays the primary source
    fast = Request.model_validate({**data, "sources": data["sources"] + [alt]})
    slow = Request.model_validate({**data, "sources": data["sources"] + [{**alt, "lead_days": main["lead_days"] * 4 + 14}]})
    tiny = Request.model_validate({**data, "sources": data["sources"] + [{**alt, "capacity_by_period": [1.] * len(main["capacity_by_period"]), "maximum": 1.}]})
    f, s, t = _profile(fast)[0]["state"], _profile(slow)[0]["state"], _profile(tiny)[0]["state"]
    assert f["alternate_inside_window"] is True
    assert s["alternate_inside_window"] is False and t["alternate_inside_window"] is False
    assert f["resilience"] >= s["resilience"] and f["resilience"] >= t["resilience"]
    v4 = _profile(_with(fast, protection_v5=False))[0]["state"]
    assert v4["alternate_inside_window"] is None


# echelon accounting and transitions

def test_echelon_partition_never_exceeds_recommended_protection():
    for case in ["normal", "recovery", "transfer", "network"]:
        try:
            req = example(case)
        except (KeyError, ValueError):
            continue
        for row in _profile(req):
            e = row["state"]["echelon"]
            parts = e["local_service_units"] + e["pooled_network_units"] + e["source_protection_units"] + e["temporary_risk_units"]
            assert parts <= row["protection_units"] + 1e-6
            assert all(v >= 0 for k, v in e.items() if k != "scope")
            assert isinstance(row["state"]["transition"], str) and row["state"]["transition"]


def test_transition_explains_protect_and_lean():
    calm = _profile(example("normal"))[0]["state"]
    assert calm["regime"] == "LEAN" and calm["transition"].startswith("LEAN")
    stressed = _profile(_shipments(example("normal"), late_tail=5, short=True))[0]["state"]
    assert stressed["regime"] == "PROTECT"
    assert stressed["transition"].startswith("LEAN -> PROTECT: supply risk active")


# selector audit and ranking

def test_rejected_candidates_carry_deltas_and_reasons():
    evaluated = []
    for case in ["recovery", "substitution"]:      # incumbent retained / cheapest candidate rejected: alternatives are audited
        gates = plan(example(case))["candidate_gates"]
        assert gates, "candidate gates missing from the plan report"
        evaluated += [g for g in gates.values() if "deltas" in g]
    assert evaluated, "no evaluated candidate carries deltas"
    for gate in evaluated:
        assert gate.get("reason")
        assert set(gate["deltas"]) >= {"service", "cost_fitted", "inventory", "stress_service"}
        if not gate["accepted"]:
            assert gate["reason"] != "accepted"


def test_v5_ranking_does_not_carry_more_inventory_than_v4_on_a_quiet_cell():
    req = example("normal")
    v5 = plan(req)
    v4 = plan(_with(req, protection_v5=False))
    def burden(report):
        rows = report["actions"]
        return sum(r.get("quantity", 0.) for r in rows if r.get("action") in {"buy", "purchase", "order"}) if rows else 0.
    assert v5["status"] in {"PENDING_REVIEW", "RETAIN_INCUMBENT"}
    assert burden(v5) <= burden(v4) + 1e-6


def test_v4_comparator_is_reachable_from_the_method_table():
    assert "gated_v4" in V4_METHODS
    assert {"gated_pr30", "protected_pr30"} <= PR30_METHODS
    assert Request.model_fields["protection_v5"].default is True


# echelon placement: pooling follows the transfer lead

def test_slow_transfer_keeps_more_protection_local_than_fast_transfer():
    req = example("network")
    feeders = [t for t in req.transfers if t.approved]
    if not feeders:
        pytest.skip("network demo has no approved transfer arc")
    fed = feeders[0].destination
    def state_for(lead: int):
        data = req.model_dump(mode="json")
        for t in data["transfers"]:
            t["lead_periods"] = lead
        rows = _profile(Request.model_validate(data))
        return next(r["state"] for r in rows if r["location"] == fed)
    fast, slow = state_for(1), state_for(3)
    assert fast["placement"]["transfer_lead_periods"] == 1 and slow["placement"]["transfer_lead_periods"] == 3
    assert slow["placement"]["local_service_units"] >= fast["placement"]["local_service_units"]
    assert fast["placement"]["pooled_network_units"] >= slow["placement"]["pooled_network_units"]
    assert fast["echelon"]["local_service_units"] <= fast["placement"]["local_service_units"] + 1e-9


# recent fill run and backlog-implied lead

def test_recent_fill_run_needs_a_run_not_a_single_short_receipt():
    from zaad.full.uncertainty import recent_fill_run
    clean = _main_profile(_shipments(example("normal"), late_tail=0))
    assert recent_fill_run(clean) is None
    one_short = _main_profile(_shipments(example("normal"), late_tail=1, short=True))
    assert recent_fill_run(one_short) is None
    run = _main_profile(_shipments(example("normal"), late_tail=4, short=True))
    assert run.recent_fill_mean == pytest.approx(.6 * 4 / 6 + 1. * 2 / 6, abs=1e-6)
    assert recent_fill_run(run) == pytest.approx(run.recent_fill_mean)


def test_open_orders_fill_the_way_the_source_fills_now():
    from zaad.full.worlds import draw
    base = _shipments(example("normal"), late_tail=4, short=True)
    req = Request.model_validate({**base.model_dump(mode="json"), "pipeline": [_po(base, "po-open", 2)]})
    v5 = draw(req, 3, 1, deterministic=True)[0].po_fill["po-open"]
    v4 = draw(_with(req, protection_v5=False), 3, 1, deterministic=True)[0].po_fill["po-open"]
    assert v5 < v4 and v5 <= .8


def test_backlog_implied_lead_holds_younger_orders_behind_the_oldest_overdue_one():
    from zaad.full.worlds import draw
    req = example("normal")
    main = next(s for s in req.sources if s.id == "main")
    old, young = _po(req, "po-old", main.lead_days + 42), _po(req, "po-young", 3)
    with_backlog = _shipments(Request.model_validate({**req.model_dump(mode="json"), "pipeline": [old, young]}), late_tail=3, overdue_open=3)
    w = draw(with_backlog, 5, 1, deterministic=True)[0]
    assert w.po_due["po-young"] >= 2, w.po_due          # not "next period" while the backlog stands
    calm = draw(Request.model_validate({**req.model_dump(mode="json"), "pipeline": [young]}), 5, 1, deterministic=True)[0]
    assert calm.po_due["po-young"] <= w.po_due["po-young"]
