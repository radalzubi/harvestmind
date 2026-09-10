from domain.uom import PackSpec
from optimization.explain import explain_order, explain_schedule


def test_explanation_reconciles_and_reads_commercially():
    e = explain_order("SKU-1", "SUP-1", 0, 480, demand_history=[100, 110, 90, 105],
                      on_hand=178, inbound=120, expected_fill=0.88, lead_periods=3,
                      service_target=0.97, pack_spec=PackSpec(units_per_case=12))
    txt = e.as_text()
    assert "Order 480 units" in txt and "40 x 12-unit lot" in txt
    assert "supplier expected fill: 88%" in txt and "target service level: 97%" in txt
    assert e.expected_demand_over_lead == 101.25 * 4
    assert abs((e.order_units - e.safety_buffer) - max(405 - 178 - 120, 0) / 0.88) < 1e-6
    assert "dual" not in txt.lower() and "pyomo" not in txt.lower()


def test_non_optimal_status_is_disclosed():
    e = explain_order("A", "S", 1, 24, demand_history=[10, 12], on_hand=0, inbound=0,
                      expected_fill=1.0, lead_periods=1, service_target=0.95,
                      solver_status="feasible", gap=0.02)
    assert "not a proven optimum" in e.as_text() and "gap 2.0%" in e.as_text()


def test_schedule_explanations_skip_zero_orders():
    sched = {("S", "A", 0): 120.0, ("S", "A", 1): 0.0, ("S", "B", 0): 36.0}
    out = explain_schedule(sched, demand_history={"A": [50, 60], "B": [10, 12]},
                           on_hand={"A": 20, "B": 5}, inbound={("A", 1): 30},
                           expected_fill={"S": 0.9}, lead_of={"S": 2}, supplier_of={"A": "S", "B": "S"},
                           service_target=0.95, pack_specs={"A": PackSpec(12), "B": PackSpec(6)})
    assert [o.product_id for o in out] == ["A", "B"] and out[0].lots == 10
