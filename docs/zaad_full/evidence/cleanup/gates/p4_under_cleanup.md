# P4 fixture matrix `p4_under_cleanup`

28 / 28 fixtures PASS

| fixture | family | worlds | sets | static | adaptive | PI | value | ordering | NA | feasible | principle | wall s | result |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N1_disabled_is_frozen | neutrality | 3 | - | - | - | - | 0.0 | - | - | - | frozen_identity (PASS) | 0.5 | PASS |
| N2_no_epochs_is_static | neutrality | 3 | - | 12,529.7 | 12,529.7 | - | 0.0 | True | True | True | equals_static (PASS) | 0.11 | PASS |
| N3_zero_information | neutrality | 4 | 1 | 15,059.2 | 15,059.2 | 14,550.5 | 0.0 | True | True | True | one_set_equals_static (PASS) | 0.24 | PASS |
| A1_demand_visible_at_epoch | non_anticipativity | 4 | 2 | 15,869.1 | 15,206.0 | 15,186.5 | 663.2 | True | True | True | same_before_diverge_after (PASS) | 0.23 | PASS |
| A2_delayed_information | non_anticipativity | 4 | 1,2 | 12,682.0 | 12,682.0 | 12,657.9 | 0.0 | True | True | True | no_branch_until_observed (PASS) | 0.32 | PASS |
| D1_demand_recourse | demand | 4 | 2 | 16,683.7 | 15,858.0 | 15,835.0 | 825.7 | True | True | True | high_branch_buys_more (PASS) | 0.23 | PASS |
| D2_two_epochs | demand | 4 | 2,4 | 15,869.1 | 15,195.3 | 15,186.5 | 673.8 | True | True | True | high_branch_buys_more (PASS) | 0.23 | PASS |
| R1_supplier_short_fill | receipts | 4 | 2 | -20,768.6 | -20,888.4 | -20,980.1 | 119.8 | True | True | True | short_branch_replaces_supply (PASS) | 0.23 | PASS |
| R2_shipment_delay | receipts | 4 | 2 | 12,649.5 | 12,649.5 | 12,638.8 | 0.0 | True | True | True | late_branch_covers_gap (PASS) | 0.23 | PASS |
| V1_recovery | recovery | 4 | 2 | -20,485.4 | -20,709.5 | -20,795.0 | 224.1 | True | True | True | recovered_branch_buys_less (PASS) | 0.23 | PASS |
| W1_waiting_has_value | waiting | 4 | 2 | 15,268.4 | 13,945.7 | 13,924.7 | 1,322.7 | True | True | True | waiting_value (PASS) | 0.23 | PASS |
| W2_no_benefit | waiting | 4 | 1 | 12,646.6 | 12,646.6 | 12,637.3 | 0.0 | True | True | True | no_benefit (PASS) | 0.23 | PASS |
| W3_flexibility_costs_mov | waiting | 4 | 2 | 16,201.3 | 15,537.1 | 15,484.2 | 664.2 | True | True | True | ordering_only (PASS) | 3.09 | PASS |
| I1_p1_fixed_cost_lots | p1 | 4 | 2 | 16,171.3 | 15,492.1 | 15,454.2 | 679.2 | True | True | True | moq_in_every_branch (PASS) | 3.39 | PASS |
| I2_p2_transfer_recourse | p2 | 4 | 2 | 14,978.9 | 14,916.9 | 14,466.6 | 62.0 | True | True | True | transfers_adapt_conserved (PASS) | 0.22 | PASS |
| I3_p3_source_mix | p3 | 4 | 2 | -17,919.3 | -18,588.8 | -18,615.6 | 669.6 | True | True | True | capacity_in_every_branch (PASS) | 0.46 | PASS |
| I4_p3_shares_hold | p3 | 4 | 2 | 15,257.6 | 14,732.1 | 14,715.0 | 525.4 | True | True | True | shares_in_every_branch (PASS) | 0.24 | PASS |
| I5_p3_switching_cost | p3 | 4 | 2 | 14,507.9 | 14,507.9 | 14,499.2 | 0.0 | True | True | True | ordering_only (PASS) | 3.26 | PASS |
| I6_multi_sku_shared_capacity | p3 | 4 | 2 | 47,777.1 | 46,166.9 | 46,113.0 | 1,610.1 | True | True | True | capacity_in_every_branch (PASS) | 0.59 | PASS |
| I7_correlated_plant | correlated | 4 | 2 | 18,236.1 | 17,178.0 | 17,161.6 | 1,058.1 | True | True | True | plant_observed_once (PASS) | 17.36 | PASS |
| S1_commercial_packs | sector | 4 | 2 | 15,870.8 | 15,210.7 | 15,193.8 (feasible, not certified) | 660.1 | True | True | True | packs_in_every_branch (PASS) | 62.6 | PASS |
| S2_produce_sell_through | sector | 4 | 2 | 14,927.5 | 13,177.1 | 13,165.2 | 1,750.4 | True | True | True | feasible_every_world (PASS) | 19.21 | PASS |
| S3_meat_cold_chain | sector | 4 | 2 | 16,479.6 | 15,669.2 | 14,911.1 | 810.4 | True | True | True | feasible_every_world (PASS) | 0.13 | PASS |
| S4_mixed_sectors_static_infeasible | sector | 4 | 2 | - | 23,758.2 | 23,476.0 | 0.0 | None | True | True | feasible_every_world (PASS) | 10.05 | PASS |
| S5_mixed_sectors | sector | 4 | 2 | 22,790.4 | 21,952.8 | 21,932.1 | 837.7 | True | True | True | feasible_every_world (PASS) | 69.35 | PASS |
| T1_tree_three_histories | tree | 6 | 3 | 12,805.9 | 12,767.5 | 12,644.9 | 38.4 | True | True | True | ordering_only (PASS) | 0.43 | PASS |
| T2_tree_two_epochs | tree | 12 | 3,6 | 12,841.5 | 12,794.8 | 12,648.2 | 46.7 | True | True | True | ordering_only (PASS) | 1.35 | PASS |
| T3_perfect_information_bound | tree | 12 | 3,6 | 12,895.4 | 12,841.9 | 12,669.2 | 53.6 | True | True | True | pi_ordering (PASS) | 1.2 | PASS |
