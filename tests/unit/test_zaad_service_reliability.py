"""Service reliability: uncertainty-responsive protection, customer-specific targets, surge
detection, supplier distributions, correlated exposure, alternatives, service-first gating,
shortage classification and reliability metrics."""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.forecast import change_origin, estimate
from zaad.full.model import solve
from zaad.full.planner import plan, targets
from zaad.full.protection import protection_profile
from zaad.full.surge import bocpd_origin, page_hinkley_origin
from zaad.full.uncertainty import (demand_uncertainty, diversification, failure_domains_for, supply_profile,
                                   supply_profiles)
from zaad.full.worlds import draw, forecast_all


def _with(req: Request, **update) -> Request:
    return Request.model_validate({**req.model_dump(mode="json"), **update})


# 1. Protection responds to uncertainty, not to one universal factor.

def test_protection_quantile_follows_customer_targets_and_supply_tail():
    req = example("normal")
    fits = forecast_all(req)
    lean = protection_profile(req, fits, supply_profiles(req))[0]
    assert lean["stance"] == "lean" and "does not need extra inventory" in lean["explanation"]
    # A 99% strategic customer at the same SKU/location raises the quantile.
    data = req.model_dump(mode="json")
    data["customers"].append({**data["customers"][0], "id": "supermarket", "priority": 3., "service_class": "strategic"})
    data["services"].append({**data["services"][0], "id": "super_A", "customer": "supermarket", "target": .99})
    data["history"] += [{**h, "service": "super_A"} for h in data["history"]]
    strategic = Request.model_validate(data)
    profile = protection_profile(strategic, forecast_all(strategic), supply_profiles(strategic))[0]
    assert profile["weighted_target"] > .97 and profile["quantile_z"] > lean["quantile_z"]
    # A widened observed lead tail on the only source raises protection and says so.
    now = req.as_of
    history = [{"id": f"s{i}", "known_at": now, "source": "main", "elapsed_days": d, "arrived": True, "stage": "placed", "carrier": "x", "accepted_ratio": .95}
               for i, d in enumerate([7, 7, 8, 21, 28, 35, 42, 7, 7, 30])]
    widened = _with(req, shipment_history=history)
    wide = protection_profile(widened, forecast_all(widened), supply_profiles(widened))[0]
    assert wide["supply_scope"] == "observed" and wide["late_probability"] > .3
    assert wide["protection_units"] > lean["protection_units"]
    assert "supply tail widened" in wide["explanation"] or "lead-time tail" in wide["explanation"]


def test_alternatives_and_substitutes_reduce_protection():
    req = example("substitution")
    fits = forecast_all(req)
    row = protection_profile(req, fits, supply_profiles(req))[0]
    assert row["substitute_cover_units"] > 0 and row["protection_units"] == 0.
    assert "substitute stock covers" in row["explanation"]


def test_proxy_buffer_is_not_universal_under_reliability_profile():
    req = example("normal")
    frozen = targets(_with(req, engine_profile="pr24"))
    reliability = targets(req)
    assert set(frozen) == set(reliability)
    assert any(abs(frozen[k] - reliability[k]) > 1e-9 for k in frozen)
    assert targets(req, 0.) == targets(_with(req, engine_profile="pr24"), 0.)


# 2. Customer-specific service levels are enforced and reported per class.

def test_customer_classes_reported_separately():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["customers"][0]["service_class"] = "wholesale"
    data["customers"].append({**data["customers"][0], "id": "spot", "priority": .3, "service_class": "spot"})
    data["services"].append({**data["services"][0], "id": "spot_A", "customer": "spot", "target": .9})
    data["history"] += [{**h, "service": "spot_A", "quantity": 5.} for h in data["history"]]
    report = plan(Request.model_validate(data))
    classes = report["service_reliability"]["by_customer_class"]
    assert set(classes) == {"wholesale", "spot"}
    assert classes["spot"]["requested_mean"] == pytest.approx(.9) and classes["wholesale"]["requested_mean"] == pytest.approx(.95)
    assert {"unit_fill"} == {s["metric"] for s in report["service_reliability"]["services"]}


# 3. Fast surge response without panic after one abnormal week.

def _series(rng, pattern):
    y = np.array([max(0., rng.normal(20, 2)) for _ in range(52)])
    if pattern == "spike":
        return np.concatenate([y, [60.], rng.poisson(20, 4).astype(float)])
    if pattern == "shift":
        return np.concatenate([y, rng.poisson(36, 4).astype(float)])
    return y


@pytest.mark.parametrize("mode", ["symmetric", "asymmetric", "page_hinkley", "bocpd"])
def test_detectors_ignore_one_spike_and_catch_a_level_shift(mode):
    rng = np.random.default_rng(11)
    spike = _series(rng, "spike")
    for k in range(53, len(spike) + 1):
        assert change_origin(spike[:k], mode) == 0, f"{mode} moved the origin after a single spike"
    shift = _series(np.random.default_rng(12), "shift")
    origins = [change_origin(shift[:k], mode) for k in range(53, len(shift) + 1)]
    assert any(o >= 50 for o in origins), f"{mode} never detected a sustained 80% level shift within four observations"


def test_detector_helpers_are_deterministic_and_bounded():
    y = np.full(40, 20.)
    assert page_hinkley_origin(y) == 0 and bocpd_origin(y) == 0
    y2 = np.concatenate([y, np.full(6, 40.)])
    assert 40 <= page_hinkley_origin(y2) <= 44 and 40 <= bocpd_origin(y2) <= 44


def test_regime_uncertainty_widens_level_error_after_a_young_change():
    rng = np.random.default_rng(3)
    y = _series(rng, "shift")
    fit = estimate(y, 11., .05, True, "symmetric")
    unc = demand_uncertainty(fit, y)
    assert fit["segment_origin"] > 0 and unc["regime_uncertainty"] > 0 and unc["level_se"] > unc["residual_sd"] / 4


# 4. Supplier delay and fill distributions from censored history.

def test_supply_profile_uses_censored_history_and_declared_fallback():
    req = example("normal")
    source = req.sources[0]
    declared = supply_profile(source, (), req.period_days)
    assert declared.scope == "declared" and declared.records == 0
    now = req.as_of
    rows = [{"id": f"a{i}", "known_at": now, "source": "main", "elapsed_days": d, "arrived": True, "stage": "placed", "carrier": "c", "accepted_ratio": r}
            for i, (d, r) in enumerate([(7, 1.), (8, .9), (7, .95), (21, .8), (9, 1.), (7, .6), (7, .95), (8, .9)])]
    rows += [{"id": f"c{i}", "known_at": now, "source": "main", "elapsed_days": 30, "arrived": False, "stage": "placed", "carrier": "c"} for i in range(3)]
    observed = supply_profile(_with(req, shipment_history=rows).sources[0], _with(req, shipment_history=rows).shipment_history, req.period_days)
    assert observed.scope == "observed" and observed.censored == 3
    assert observed.partial_probability > .3 and 0 < observed.late_probability < 1
    assert observed.unresolved_mass > 0   # censored open POs keep their tail, never fabricated as arrived


def test_worlds_draw_supply_from_observed_profile():
    req = example("normal")
    now = req.as_of
    rows = [{"id": f"a{i}", "known_at": now, "source": "main", "elapsed_days": d, "arrived": True, "stage": "placed", "carrier": "c", "accepted_ratio": .7}
            for i, d in enumerate([7, 7, 7, 28, 28, 35, 7, 7])]
    observed = _with(req, shipment_history=rows)
    worlds = draw(observed, 5, 8)
    fills = [w.fills["main", 0] for w in worlds]
    delays = [w.arrival["main", 0] for w in worlds]
    assert max(fills) <= .7 + 1e-9 and max(delays) > min(delays)


# 5. Correlated exposure: shared ports are not diversification.

def test_shared_route_nodes_are_shared_failure_domains():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["sources"].append({**data["sources"][0], "id": "alt", "supplier": "other", "route": ["other", "port", "branch"],
                            "resources": ["alt_cap"]})
    data["resources"].append({**data["resources"][0], "id": "alt_cap", "failure_domains": []})
    shared = Request.model_validate(data)
    resources = {r.id: r for r in shared.resources}
    assert "port" in failure_domains_for(shared.sources[1], resources)
    d_shared = diversification(shared, "A", "branch")
    assert d_shared["effective_independent_sources"] == pytest.approx(1.) and "port" in d_shared["shared_domains"]
    data["sources"][1]["route"] = ["other", "other_port", "branch"]
    independent = diversification(Request.model_validate(data), "A", "branch")
    assert independent["effective_independent_sources"] > 1.5


# 6/7/8. Alternatives, transfers and substitutions are valued from solves, not assumed.

def test_alternative_value_reports_transfers_and_substitutions():
    for case, option in (("transfer", "transfers"), ("substitution", "substitutions")):
        report = plan(example(case))
        entry = report["alternatives"][option]
        assert entry["verdict"] in {"necessary", "justified", "cost_saving", "not_justified_on_modeled_evidence",
                                    "service_and_cost", "service", "cost_only", "no_modeled_benefit"}
        assert "sentence" in entry


def test_alternates_disabled_keeps_only_cheapest_source():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["sources"].append({**data["sources"][0], "id": "alt", "supplier": "other", "unit_price": 4., "route": ["other", "other_port", "branch"]})
    two = Request.model_validate(data)
    worlds = draw(two, two.seed, 1, deterministic=True)
    restricted = solve(two, worlds, service_floor=True, disabled=frozenset({"alternates"}))
    assert restricted.status == "OPTIMAL"
    assert all(source == "alt" for (source, _), q in restricted.purchases.items() if q > 0)


# 9/10. Quantile protection is stronger than the expected floor and vanishes with tight scenarios.

def test_cvar_service_constraint_protects_the_worst_scenarios():
    req = _with(example("normal"), scenarios=6)
    data = req.model_dump(mode="json")
    data["stock"][0]["quantity"] = 40.
    req = Request.model_validate(data)
    worlds = draw(req, req.seed, req.scenarios)
    expected = solve(req, worlds, service_floor=True)
    quantile = solve(req, worlds, service_floor=True, service_risk="cvar")
    assert expected.status == quantile.status == "OPTIMAL"
    assert sum(quantile.purchases.values()) >= sum(expected.purchases.values()) - 1e-6
    tight = draw(req, req.seed, 1, deterministic=True)
    assert solve(req, tight, service_floor=True, service_risk="cvar").projected_cost == pytest.approx(
        solve(req, tight, service_floor=True).projected_cost)


# 11/13. The selector prefers meeting service over saving cost, and explains misses.

def test_service_first_acceptance_when_incumbent_misses_target():
    report = plan(example("normal"))
    reliability = report["service_reliability"]["services"][0]
    assert reliability["incumbent_service"] < .95 - 1e-6
    assert report["status"] == "PENDING_REVIEW" and reliability["achieved_service"] >= .95 - 1e-6
    assert reliability["classification"]["class"] == "MET"
    assert any("service-first" in r for r in report["reasons"])
    frozen = plan(_with(example("normal"), engine_profile="pr24"))
    assert "protected_network" not in frozen["candidates"]


def test_unavoidable_shortage_is_named_not_hidden():
    report = plan(example("understock"))
    row = report["service_reliability"]["services"][0]
    assert row["classification"]["class"] == "UNAVOIDABLE" and row["unavoidable_shortfall"] > 0
    assert row["avoidable_service_loss"] == pytest.approx(0., abs=1e-9)
    assert report["mode"] == "ALLOCATE"


def test_economic_tradeoff_is_classified_when_downside_cap_blocks_service():
    req = _with(example("normal"), downside_cost_tolerance=0.)
    report = plan(req)
    row = report["service_reliability"]["services"][0]
    if report["status"] == "RETAIN_INCUMBENT":
        assert row["classification"]["class"] in {"ECONOMIC_TRADEOFF", "UNAVOIDABLE"}
    else:
        assert row["classification"]["class"] == "MET"


# 12. Reliability metrics are complete and separate from economics.

def test_reliability_metrics_present():
    report = plan(example("normal"))
    row = report["service_reliability"]["services"][0]
    for key in ("requested_service", "achieved_service", "best_modeled_jointly_feasible_service", "incumbent_service", "zaad_service",
                "avoidable_service_loss", "unavoidable_shortfall", "service_regret", "worst_case_stress_service", "stockout_period_share"):
        assert key in row
    assert report["service_reliability"]["customer_priority_weighted_service"] is not None
    assert "weighted_service_shortfall" in report["service_reliability"]
    assert report["executable_purchase_order"] is False and report["approval_required"] is True


def test_frozen_profile_is_unchanged_by_reliability_switch():
    req = _with(example("normal"), engine_profile="pr24")
    worlds = draw(req, 1, 3)
    again = draw(req, 1, 3)
    assert [w.fills for w in worlds] == [w.fills for w in again]
    assert "uncertainty" not in forecast_all(req)["retail_A"]
    assert plan(req)["engine_profile"] == "pr24"


def test_known_event_is_not_a_regime_change():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["events"] = [{"id": "promo", "known_at": data["as_of"], "service": "retail_A", "start": 1, "end": 2, "multiplier": 1.8, "label": "promo"}]
    promo = Request.model_validate(data)
    world = draw(promo, promo.seed, 1, deterministic=True)[0]
    assert world.demand["retail_A"][1] == pytest.approx(world.demand["retail_A"][0] * 1.8)
    assert forecast_all(promo)["retail_A"]["segment_origin"] == 0


def test_supply_profile_late_probability_respects_period():
    req = example("normal")
    quick = supply_profile(req.sources[0], (), 7)
    assert quick.late_probability < .01
    data = req.model_dump(mode="json")
    data["sources"][0]["lead_sd_days"] = 10.
    wide = supply_profile(Request.model_validate(data).sources[0], (), 7)
    assert wide.late_probability > .3 and wide.tail_days > 0
    assert (req.as_of + timedelta(days=1)).tzinfo is not None
