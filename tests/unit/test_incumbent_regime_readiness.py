import duckdb
import pytest

from backtesting.counterfactual import FoldInputs
from backtesting.incumbent import configured_incumbent, infer_incumbent
from backtesting.regime import CALM, PROMOTION, VOLATILE, diagnose, summarize
from domain.carrying_cost import CarryingCostComponents, sensitivity_grid
from domain.economics import CostConfig
from domain.model import fmcg_policy
from domain.uom import PackSpec
from ingestion.pilot_readiness import assess


def _fi(demand, promo=None, fills=None):
    pol = fmcg_policy({"A": PackSpec(1)}, cost_config=CostConfig(
        holding_rate_per_period=0.005, shortage_cost_per_unit={"A": 2.0}, waste_cost_per_unit={"A": 5.0}))
    return FoldInputs(origin=100, horizon=6, products=["A"], supplier_of={"A": "S"}, lead_of={"S": 1},
                      train_demand={"A": demand}, train_fill={"S": fills or [0.97] * 10}, unit_cost={"A": 5.0},
                      margin={"A": 2.0}, capacity={"A": 1000.0}, opening={"A": 200.0}, pipeline={},
                      policy=pol, promo_multiplier=promo or {})


class TestIncumbent:
    def test_inferred_is_labelled_and_uses_po_history(self):
        pos = [{"sku": "A", "period": p, "qty": 300.0, "inventory_position_before": 100.0} for p in range(-40, 0, 2)]
        inc = infer_incumbent(pos, {"A": 100.0})
        assert inc.source == "inferred" and "INFERRED" in inc.label
        assert inc.cover_weeks["A"] == pytest.approx(4.0) and inc.review_periods["A"] == 2

    def test_too_few_pos_falls_back_with_a_note(self):
        inc = infer_incumbent([{"sku": "A", "period": -1, "qty": 10, "inventory_position_before": 0}], {"A": 100.0})
        assert "A" not in inc.cover_weeks and any("too few" in n for n in inc.notes)

    def test_configured_schedule_is_whole_lots_and_tops_up(self):
        inc = configured_incumbent(cover_weeks=3.0, review_periods=1)
        sched = inc.build_schedule(_fi([100.0] * 60))
        assert sched and all(q >= 0 for q in sched.values())
        assert sum(sched.values()) > 0


class TestRegime:
    def test_calm_volatile_promotion(self):
        assert diagnose(_fi([100.0] * 60))["A"].regime == CALM
        vol = [100.0, 0.0, 300.0, 5.0] * 15
        assert diagnose(_fi(vol))["A"].regime == VOLATILE
        assert diagnose(_fi([100.0] * 60, promo={("A", 2): 2.0}))["A"].regime == PROMOTION
        s = summarize(diagnose(_fi([100.0] * 60)))
        assert s["dominant"] == CALM and s["n"] == 1

    def test_reasons_are_human_readable(self):
        r = diagnose(_fi([100.0] * 60, fills=[0.7] * 10))["A"]
        assert r.regime in ("SUPPLY_CONSTRAINED", "DISRUPTION") and "fill" in r.reasons[0]


class TestCarryingCost:
    def test_components_convert_and_sweep(self):
        c = CarryingCostComponents(0.10, 0.06, 0.01, 0.03, provenance={"cost_of_capital_annual": "operator"})
        assert c.annual_rate == pytest.approx(0.20)
        assert c.per_period("week") == pytest.approx(0.20 / 52)
        grid = sensitivity_grid(c)
        assert [g["multiplier"] for g in grid] == [0.5, 1.0, 2.0, 4.0, 10.0]
        with pytest.raises(ValueError):
            CarryingCostComponents(cost_of_capital_annual=5.0)


class TestPilotReadiness:
    def test_empty_vault_is_not_ready(self):
        c = duckdb.connect()
        for f in ("013_fmcg_staging", "014_fmcg_economics_provenance"):
            c.execute(open(f"db/migrations/{f}.sql").read())
        r = assess(c)
        assert r.verdict.startswith("NOT_READY") and r.score < 0.5 and r.required_missing

    def test_missing_preferred_fields_name_the_weakened_conclusion(self):
        c = duckdb.connect()
        for f in ("013_fmcg_staging", "014_fmcg_economics_provenance"):
            c.execute(open(f"db/migrations/{f}.sql").read())
        c.execute("INSERT INTO stg_fmcg_skus (sku, supplier_id, unit_cost, units_per_case) VALUES ('A','S',1.0,6)")
        c.execute("INSERT INTO stg_fmcg_orders (sku, order_date, qty_ordered) VALUES ('A', DATE '2025-01-06', 10)")
        c.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered) VALUES ('P1', DATE '2025-01-01','S','A',60)")
        c.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, qty_received) VALUES ('P1', DATE '2025-01-08', 60)")
        c.execute("INSERT INTO stg_fmcg_inventory (sku, snapshot_date, on_hand) VALUES ('A', DATE '2025-01-06', 100)")
        r = assess(c)
        assert not r.required_missing and r.verdict == "READY_WITH_CAVEATS"
        assert any("shortage cost is UNKNOWN" in w for w in r.weakened_conclusions)
        assert any("weeks of order history" in w for w in r.weakened_conclusions)
