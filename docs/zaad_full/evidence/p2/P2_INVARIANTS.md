# P2 invariants

| invariant | result | numbers |
|---|---|---|
| 01_conservation | PASS | {"settlement_residual": 0.0, "max_flow_row_residual": 0.0, "transfers_units": 2205.0769} |
| 02_no_double_count | PASS | {"period_0_outbound": 100.0, "central_usable": 100.0, "settlement_refuses_200_from_100": true} |
| 03_unreachable_inventory | PASS | {"served_in_periods_0_to_3": 0.0, "demand_in_periods_0_to_3": 801.8462, "central_units": 1000.0, "lane_lead": 4} |
| 04_05_transfer_cost_monotone | PASS | {"transfer_units_by_lane_cost": {"0.0": 2205.0769230769233, "0.2": 2205.0769230769233, "5.0": 2205.0769230769233}} |
| 06_shorter_lead_more_useful | PASS | {"projected_cost_by_lead": {"1": 12631.413943786147, "3": 15230.95945893637}} |
| 07_capacity | PASS | {"peak_lane_period_units": 60.0, "capacity": 60.0, "settlement_refuses_61": true} |
| 08_pack_rounding | PASS | {"period_units": {"lane_north@0": 96.0, "lane_north@1": 187.53846153846155, "lane_north@3": 98.38461538461539, "lane_north@4": 98.38461538461539, "lane_north@5": 98.38461538461539, "lane_north@6": 98.38461538461539, "lane_north@7": 98.38461538461539, "lane_north@8": 98.38461538461539, "lane_north@9": 98.38461538461539, "lane_north@10": 98.38461538461539, "lane_south@0": 96.0, "lane_south@1": 100.2 |
| 09_shared_central_inventory | PASS | {"period_0_allocations": 150.0, "central_usable": 150.0} |
| 10_supply_cap | PASS | {"peak_period_purchases": 90.0, "shared_capacity": 90.0, "settlement_refuses_120": true} |
| 11_single_node_identity | PASS | {"status": "PENDING_REVIEW", "selected": "deterministic_network"} |
| 12_zero_lane_identity | PASS | {"transfers": 0, "service": {"svc_north": 0.0, "svc_south": 0.0}, "central_units_stranded": 500.0} |
| 13_14_pooling_and_correlation | PASS | {"worlds": {"independent": {"pooled_p95": 463.9216388873129, "sum_of_branch_p95": 490.9681955453657, "ratio": 0.9449117948912973}, "correlated": {"pooled_p95": 496.36799460440375, "sum_of_branch_p95": 497.49290514591996, "ratio": 0.9977388410369666}}, "worlds_pass": {"13": true, "14": true}, "model": {"independent": {"pooled_status": "OPTIMAL", "isolated_status": "OPTIMAL", "pooled_inventory_value |
| 15_no_action | PASS | {"status": "RETAIN_INCUMBENT", "state": "NO_ACTION", "selected": "operator_rule:network:rop", "period_0": {"purchases_period_0": 0, "purchase_lines": 9, "transfers_period_0": 0, "transfer_lines": 23, "no_action": true}} |
| 16_service_not_overridden | PASS | {"projected_service": {"svc_north": 1.0, "svc_south": 1.0}, "targets": {"svc_north": 0.99, "svc_south": 0.95}} |
| 17_allocation | PASS | {"north_units": 80.0, "south_units": 0.0, "explanation": "central holds 80 of A against requests of 401. north receives 80 because its customers carry the higher priority (3); south receives 0.", "status": "RETAIN_INCUMBENT"} |
| 18_recovery | PASS | {"cells": [{"seed": 41001, "early_transfers": 226.54632770689315, "late_transfers": 399.063520435244, "late_demand": 410.7406284324226, "reverse": 0.0}, {"seed": 41002, "early_transfers": 226.54632770689315, "late_transfers": 380.6091178633275, "late_demand": 407.9606798689911, "reverse": 0.0}]} |
| 19_terminal_edge_and_loops | PASS | {"last_period_transfers": 801.8462, "max_mid_period_transfers": 688.6923, "demand_rate": 200.4615, "reverse_pair_forward": 880.6154, "reverse_pair_back": 0} |
| 20_accounting | PASS | {"buckets": {"node": 11637.309663394486, "lane": 480.21402160319013, "upstream": 99.99999999999999, "network": 1828.2178464788994}, "economic_cost": 14045.7415, "worst_check": 0.0} |
