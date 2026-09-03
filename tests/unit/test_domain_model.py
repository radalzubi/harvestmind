"""Domain layer: units, pack structure, economics and policy validation."""
from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from domain import (
    AGRICULTURE_PERISHABLE, FMCG, CostConfig, Domain, PackSpec, Quantity,
    ServiceTarget, Unit, get_policy, round_to_pack,
)
from domain.model import agriculture_policy, fmcg_policy


class TestQuantity:
    def test_rejects_negative_and_nonfinite(self):
        for bad in (-1.0, float("nan"), float("inf")):
            with pytest.raises(ValueError):
                Quantity(bad, Unit.KG)

    def test_mass_conversion(self):
        assert Quantity(10, Unit.LB).to_kg().value == pytest.approx(4.5359237)

    def test_cannot_add_across_units(self):
        with pytest.raises(ValueError):
            Quantity(1, Unit.KG) + Quantity(1, Unit.CASE)

    def test_count_unit_has_no_mass(self):
        with pytest.raises(ValueError):
            Quantity(1, Unit.CASE).to_kg()


class TestPackSpec:
    def test_lot_units_by_level(self):
        sp = PackSpec(units_per_case=12, cases_per_layer=10, layers_per_pallet=6)
        assert sp.lot_units == 12
        assert PackSpec(12, 10, 6, order_multiple=Unit.LAYER).lot_units == 120
        assert PackSpec(12, 10, 6, order_multiple=Unit.PALLET).lot_units == 720

    def test_pallet_ordering_needs_hierarchy(self):
        with pytest.raises(ValueError):
            PackSpec(12, order_multiple=Unit.PALLET)

    def test_moq_rounded_up_to_whole_lot(self):
        assert PackSpec(12, moq_units=100).moq_units == 108

    def test_moq_above_max_rejected(self):
        with pytest.raises(ValueError):
            PackSpec(12, moq_units=500, max_units_per_order=120)

    def test_round_up_never_down_and_zero_stays_zero(self):
        sp = PackSpec(12, moq_units=60)
        assert round_to_pack(0.0, sp) == 0.0
        assert round_to_pack(437.36, sp) == 444.0
        assert round_to_pack(1.0, sp) == 60.0       # MOQ applies once ordering

    @settings(max_examples=300, deadline=None)
    @given(units=st.floats(min_value=0, max_value=1e7, allow_nan=False),
           case=st.integers(min_value=1, max_value=500),
           moq_lots=st.integers(min_value=0, max_value=50))
    def test_rounding_properties(self, units, case, moq_lots):
        sp = PackSpec(units_per_case=case, moq_units=float(moq_lots * case))
        q = round_to_pack(units, sp)
        assert math.isfinite(q) and q >= 0
        assert q >= units - 1e-6                         # never short
        assert abs(q / case - round(q / case)) < 1e-9    # whole cases
        if units > 0:
            assert q - units < case + 1e-6 or q == sp.moq_units  # at most one case over, or MOQ
            assert q >= sp.moq_units
        else:
            assert q == 0.0


class TestCostConfig:
    def test_currency_must_be_iso(self):
        for bad in ("usd", "US", "dollars", ""):
            with pytest.raises(ValueError):
                CostConfig(currency=bad)

    def test_negative_or_nan_rate_rejected(self):
        with pytest.raises(ValueError):
            CostConfig(holding_rate_per_period=-0.01)
        with pytest.raises(ValueError):
            CostConfig(shortage_cost_per_unit={"A": float("nan")})

    def test_emergency_never_cheaper_than_contract(self):
        with pytest.raises(ValueError):
            CostConfig(emergency_cost_multiplier=0.9)

    def test_sla_penalty_needs_target(self):
        with pytest.raises(ValueError):
            CostConfig(sla_penalty_rate=0.03)

    def test_implausible_holding_rate_caught(self):
        with pytest.raises(ValueError):
            CostConfig(holding_rate_per_period=0.30)

    def test_refuses_products_with_no_priced_recourse(self):
        cc = CostConfig(shortage_cost_per_unit={"A": 1.0})
        cc.validate_for_products(["A"])
        with pytest.raises(ValueError):
            CostConfig().validate_for_products(["A", "B"])


class TestServiceTarget:
    def test_level_and_metric_validation(self):
        with pytest.raises(ValueError):
            ServiceTarget(1.2)
        with pytest.raises(ValueError):
            ServiceTarget(0.95, metric="otif_magic")
        with pytest.raises(ValueError):
            ServiceTarget(0.95, scope="customer")   # scope needs a key
        ServiceTarget(0.95, scope="customer", key="C1")


class TestPolicies:
    def test_agriculture_defaults(self):
        p = agriculture_policy()
        assert p.domain is Domain.AGRICULTURE_PERISHABLE
        assert p.decay_rate_per_period > 0 and p.fefo and p.supply_uncertainty == "yield"
        assert p.pack_spec_for("anything").is_discrete is False

    def test_fmcg_requires_pack_specs_for_every_product(self):
        p = fmcg_policy({"A": PackSpec(12)},
                        cost_config=CostConfig(shortage_cost_per_unit={"A": 1, "B": 1}))
        with pytest.raises(ValueError, match="PackSpec"):
            p.validate_products(["A", "B"])
        p.validate_products(["A"])

    def test_fmcg_base_unit_constraint(self):
        with pytest.raises(ValueError):
            fmcg_policy({"A": PackSpec(12)}, base_unit=Unit.KG)

    def test_get_policy_by_string_and_enum(self):
        assert get_policy("agriculture_perishable").domain is AGRICULTURE_PERISHABLE
        assert get_policy(FMCG, pack_specs={"A": PackSpec(6)}).domain is FMCG
        with pytest.raises(ValueError):
            get_policy("fmcg")
        with pytest.raises(ValueError):
            get_policy("retail_banking")

    def test_inert_fefo_rejected(self):
        with pytest.raises(ValueError):
            fmcg_policy({"A": PackSpec(6)}).__class__(
                **{**fmcg_policy({"A": PackSpec(6)}).__dict__, "fefo": True})
