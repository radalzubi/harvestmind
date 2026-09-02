"""Disruption presets are assumptions, and must behave like assumptions."""
from __future__ import annotations

import pytest

from risk.disruption_scenarios import (
    AQABA_CONGESTION, BASELINE, PRESETS, RED_SEA_HOUTHI,
    DisruptionScenario, benchmark_overrides, get_scenario,
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
        assert RED_SEA_HOUTHI.adjusted_fill(0.90, "red_sea") == pytest.approx(0.765)

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

    def test_severity_ordering_is_monotone(self):
        order = ["baseline", "red_sea_houthi", "aqaba_congestion",
                 "land_border_disruption", "regional_escalation"]
        worst = [PRESETS[n].fill_multiplier for n in order]
        assert worst == sorted(worst, reverse=True)
        cost = [PRESETS[n].recourse_cost_multiplier for n in order]
        assert cost[0] <= cost[1] and cost[-1] == max(cost)


def test_overrides_map_onto_run_benchmark_kwargs():
    kw = benchmark_overrides(AQABA_CONGESTION)
    assert kw["spot_cost_multiplier"] == AQABA_CONGESTION.recourse_cost_multiplier
    assert kw["spot_capacity_factor"] == AQABA_CONGESTION.recourse_capacity_factor
