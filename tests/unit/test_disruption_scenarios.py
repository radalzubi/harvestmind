"""Disruption presets are assumptions, and must behave like assumptions."""
from __future__ import annotations

import pytest

from risk.disruption_scenarios import (
    ALL_LAND_DISRUPTION, AQABA_CONGESTION, BASELINE, PRESETS, RED_SEA_HOUTHI,
    ROUTES, SAUDI_LAND_DISRUPTION, DisruptionScenario, benchmark_overrides,
    get_scenario,
)


class TestHonesty:
    def test_every_preset_is_flagged_assumed(self):
        """Nothing here is measured. There is no way to claim otherwise."""
        for s in PRESETS.values():
            assert s.assumed is True

    def test_assumed_cannot_be_set_false(self):
        with pytest.raises(TypeError):
            DisruptionScenario(name="x", description="y", assumed=False)

    def test_every_non_baseline_preset_cites_a_source(self):
        for name, s in PRESETS.items():
            if name == "baseline":
                continue
            assert s.source, f"{name} has no source"

    def test_describe_says_assumed_out_loud(self):
        text = RED_SEA_HOUTHI.describe()
        assert "ASSUMED" in text and "not measured" in text


class TestValidation:
    @pytest.mark.parametrize("kw", [
        {"fill_multiplier": 1.2},          # a disruption cannot improve supply
        {"fill_multiplier": 0.0},
        {"fill_variance_inflation": 0.5},  # nor make it more predictable
        {"recourse_cost_multiplier": 0.9},  # nor make emergency supply cheap
        {"recourse_capacity_factor": 1.5},
        {"landed_cost_multiplier": 0.8},
    ])
    def test_incoherent_scenarios_are_rejected(self, kw):
        with pytest.raises(ValueError):
            DisruptionScenario(name="bad", description="bad", **kw)

    def test_unknown_preset_raises_and_lists_options(self):
        with pytest.raises(ValueError, match="unknown disruption scenario"):
            get_scenario("hormuz_closure_gcc")


class TestRouteTargeting:
    """A Jordanian distributor is not uniformly exposed. A blanket haircut
    would overstate the shock enough to be worse than doing nothing."""

    def test_scenario_spares_unaffected_routes(self):
        assert RED_SEA_HOUTHI.applies_to("red_sea") is True
        assert RED_SEA_HOUTHI.applies_to("local_farm") is False
        assert RED_SEA_HOUTHI.adjusted_fill(0.90, "local_farm") == pytest.approx(0.90)
        # 0.75 after the PortWatch revision, not the original 0.85 guess.
        assert RED_SEA_HOUTHI.adjusted_fill(0.90, "red_sea") == pytest.approx(0.675)

    def test_red_sea_reaches_aqaba_itself(self):
        """Aqaba is INSIDE Bab el-Mandeb, so a Red Sea closure reaches it.

        This once was not true and the omission was silent: the preset
        listed only 'red_sea' and 'suez', neither of which any simulator
        ever tags a supplier with, so applying the scenario changed
        nothing at all. Measured Aqaba arrivals fell to 0.743 of their
        trailing norm during the crisis, which is not nothing.
        """
        assert RED_SEA_HOUTHI.applies_to("aqaba") is True
        assert RED_SEA_HOUTHI.adjusted_fill(0.93, "aqaba") < 0.93

    def test_scenario_with_no_routes_hits_everything(self):
        assert BASELINE.applies_to("anything") is True

    def test_adjusted_fill_stays_a_probability(self):
        s = DisruptionScenario(name="x", description="x", fill_multiplier=0.5)
        assert 0.0 <= s.adjusted_fill(1.0) <= 1.0
        assert 0.0 <= s.adjusted_fill(0.0) <= 1.0


class TestJordanCalibration:
    """Jordan imports through Aqaba on the Red Sea, not through Hormuz."""

    def test_no_hormuz_preset_exists_for_jordan(self):
        assert "hormuz_closure" not in PRESETS

    def test_congestion_is_modelled_separately_from_conflict(self):
        """Aqaba congestion is other people's cargo, not a conflict shock,
        and it is the mechanism most likely to bite a Jordanian importer."""
        assert "aqaba_congestion" in PRESETS
        assert AQABA_CONGESTION.fill_multiplier < 1.0
        assert "transit" in AQABA_CONGESTION.source.lower()

    def test_saudi_road_freight_is_modelled(self):
        """A large share of Jordan's imports arrive by truck from or
        through Saudi Arabia, including goods landed at Saudi ports and
        driven north. Omitting it understates land exposure badly."""
        assert "saudi_land" in ROUTES
        assert SAUDI_LAND_DISRUPTION.applies_to("saudi_land") is True
        assert SAUDI_LAND_DISRUPTION.applies_to("aqaba") is False

    def test_land_scenarios_leave_sea_arrivals_alone(self):
        """Routes are SUBSTITUTES. An operator who can shift to Aqaba when
        the land crossings close is far less exposed, and the model must
        be able to express that."""
        for s in (SAUDI_LAND_DISRUPTION, ALL_LAND_DISRUPTION):
            assert s.applies_to("aqaba") is False
            assert s.adjusted_fill(0.9, "aqaba") == pytest.approx(0.9)

    def test_every_route_is_named(self):
        for r in ("aqaba", "saudi_land", "syria_land", "iraq_land",
                  "air", "local"):
            assert r in ROUTES

    def test_severity_ordering_is_monotone(self):
        """Severity must increase down the ladder.

        red_sea_houthi and aqaba_congestion swapped places after
        measurement: the Red Sea crisis put Aqaba arrivals at 0.743 of
        their trailing norm, while the Iraq transit surge raised Aqaba
        tonnage to about 1.47x. Congestion is a TIMING shock, so a
        quantity haircut is the wrong shape for it, and it now sits above
        the conflict scenario rather than below it.
        """
        order = ["baseline", "aqaba_congestion", "red_sea_houthi",
                 "northern_land_disruption", "regional_escalation"]
        worst = [PRESETS[n].fill_multiplier for n in order]
        assert worst == sorted(worst, reverse=True)
        cost = [PRESETS[n].recourse_cost_multiplier for n in order]
        assert cost[0] <= cost[1] and cost[-1] == max(cost)

    def test_every_preset_reaches_at_least_one_real_route(self):
        """No preset may be silently dead.

        A scenario whose affected_routes name nothing the simulator ever
        assigns applies to zero suppliers, so running it returns the
        baseline while looking like a stress test. That is exactly what
        red_sea_houthi did before the PortWatch validation, and it is the
        most dangerous failure mode here because it is invisible in the
        output.
        """
        from synthetic.commercial.jordan_distributor_v2 import ROUTE_PROFILE
        live = set(ROUTE_PROFILE)
        for name, sc in PRESETS.items():
            if name == "baseline" or not sc.affected_routes:
                continue
            assert live & set(sc.affected_routes), (
                f"{name} targets {sc.affected_routes}, none of which any "
                f"supplier is ever tagged with; it would be a no-op")


def test_overrides_map_onto_run_benchmark_kwargs():
    kw = benchmark_overrides(AQABA_CONGESTION)
    assert kw["spot_cost_multiplier"] == AQABA_CONGESTION.recourse_cost_multiplier
    assert kw["spot_capacity_factor"] == AQABA_CONGESTION.recourse_capacity_factor
