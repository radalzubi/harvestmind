# P3 sourcing invariants

34 / 34 PASS

| invariant | result | evidence |
|---|---|---|
| 01_legacy_unchanged | PASS | {"sourcing_field": null, "report_has_block": false, "canonical_regression": "PASS (gates/canonical_regression_final.log)"} |
| 02_single_source_reduces_to_p1 | PASS | {"purchases_identical": true, "policy": ["operator_rule:network:rop", "operator_rule:network:rop"], "owner": "PURCHASING_ECONOMICS"} |
| 03_sum_of_sources_equals_commitment | PASS | {"pairs": 1, "mismatched": []} |
| 04_unapproved_source_gets_nothing | PASS | {"unapproved_used": [], "settlement_refuses_forced_purchase": true} |
| 05_capacity_never_exceeded | PASS | {"over_capacity": [], "settlement_refuses_600_on_cap_500": true} |
| 06_shared_capacity_across_skus | PASS | {"shared_usage_by_period": {"0": 450.0, "1": 450.0, "2": 450.0, "3": 450.0, "4": 450.0, "5": 450.0, "6": 450.0, "7": 450.0, "8": 450.0, "9": 450.0}, "over": {}} |
| 07_moq_respected | PASS | {"b_orders": [[0, 1333.3], [4, 1333.3]], "below_moq": []} |
| 08_mov_respected | PASS | {"supplier_b_order_values": {"0": 6000, "4": 6000}, "below_mov": {}} |
| 09_packs_executable | PASS | {"purchases": [["src_A", 0, 120.0000000021298], ["src_A", 1, 120.0], ["src_A", 2, 239.9999999978702], ["src_A", 3, 240.0], ["src_A", 4, 240.00000000004127], ["src_A", 5, 120.0], ["src_A", 6, 240.0], ["src_A", 7, 240.0]], "pack_violations": []} |
| 10_payment_terms_not_double_counted | PASS | {"reconciled": true, "unmapped": [], "ledger_keys": ["closing_assets", "financing", "freight", "handling", "holding", "lost_sales_opportunity", "opening_assets", "order_fees", "procurement", "sla", "substitution", "transfer", "working_capital"], "financing_line": 0.0} |
| 11_commitments_scenario_invariant | PASS | {"procurement_value_by_world": [9482.519026], "worlds": 4} |
| 12_receipts_vary_commitments_do_not | PASS | {"fills_b_period_0_by_world": [0.8797, 0.9482, 0.777, 0.6444], "purchases_identical_across_worlds": true, "received_units_by_world": [0.0, 0.0, 0.0, 0.0]} |
| 13_shared_dependency_not_independent | PASS | {"fill_correlation_plant_group": 1.0} |
| 14_single_source_unaffected_by_correlation | PASS | {"worlds_bit_identical": true} |
| 15_marginals_preserved | PASS | {"src_A": {"mean_grouped": 0.9029846910732212, "mean_frozen": 0.8971814898094772, "sd_grouped": 0.12409199830473037, "sd_frozen": 0.12832753464879249}, "src_B": {"mean_grouped": 0.9035663296659442, "mean_frozen": 0.8961195743961856, "sd_grouped": 0.12651280553086866, "sd_frozen": 0.1329864536685458}} |
| 16_no_artificial_diversification | PASS | {"periods_with_both_sources": [], "sources_used": ["src_A", "src_B"]} |
| 17_declared_shares_respected | PASS | {"violations": [], "b_share_by_period": {"0": 0.3, "1": 0.3, "2": 0.3, "3": 0.3, "4": 0.3, "5": 0.3, "6": 0.3, "7": 0.3, "8": 0.3, "9": 0.3, "10": 0.3}} |
| 18_switching_cost_only_when_switching | PASS | {"plan_uses_b": false, "ledger_plan": 0.0, "ledger_forced_b": 2000.0, "ledger_cost_declared_on_incumbent": 0.0} |
| 19_produce_arrival_cannot_reset_life | PASS | {"receipt_life_b": 3, "receipt_life_a": 8, "shelf_life": 8, "pending_cohort_lives": [3, 7, 8]} |
| 20_unusable_life_cannot_serve | PASS | {"b_units_in_plan": 0, "forced_b_units_unsellable_at_end_or_expired": 4.190832682412463, "note": "B's cohorts are never allocated to demand (life at receipt 3 = minimum at sale 3)"} |
| 21_cold_chain_eligibility | PASS | {"b_units": 0, "settlement_refuses_forced_receipt": true, "block_explains": true} |
| 22_network_conservation_exact | PASS | {"max_residual": 5.258016244624741e-13, "transfers_in_plan": 2050.656622630001} |
| 23_no_double_allocation | PASS | {"served": 2294.9548391883245, "demand": 2417.3614382533137, "opening_plus_received": 600.0, "residual": -2.842170943040401e-14} |
| 24_no_negative_commitment | PASS | {"negative": [], "fixtures": 3} |
| 25_plan_rows_reconcile | PASS | {"options": 2, "mismatched": []} |
| 26_economics_reconcile | PASS | {"E2_landed_beats_unit_price": {"reconciled": true, "unmapped": []}, "E6_switching_cost_retains_incumbent": {"reconciled": true, "unmapped": []}} |
| 27_incumbent_retained_when_not_material | PASS | {"status": "RETAIN_INCUMBENT", "recommendations": ["RETAIN_INCUMBENT_MIX"], "reasons": ["Independent fitted-model confirmation does not establish positive benefit."]} |
| 28_no_hidden_score | PASS | {"score_identifiers_in_sourcing_package": [], "score_keys_in_block": [], "objective": "landed cost, order economics, holding, shortage, capital, declared switching cost only"} |
| 29_30_approval_and_no_po | PASS | {"report": [true, false], "block": [true, false]} |
| 31_p0_ownership_unchanged | PASS | {"owner_with_block_vs_without": ["PROTECTION_RECOVERY", "PROTECTION_RECOVERY"], "state": ["NO_ACTION", "NO_ACTION"]} |
| 32_p1_ownership_unchanged | PASS | {"owner": ["PURCHASING_ECONOMICS", "PURCHASING_ECONOMICS"], "block_owner_labels": {"total_commitment": "P1 purchasing economics (or P0 protection / recovery when it owns the review)", "source_split": "P3 sourcing portfolio"}} |
| 33_p2_ownership_unchanged | PASS | {"owner": ["PURCHASING_ECONOMICS", "PURCHASING_ECONOMICS"], "transfer_actions_in_plan": 25, "block_carries_transfers": false} |
| 34_sector_physics_unchanged | PASS | {"profiles_identical": true, "sector_invariants": "19 / 19 (gates/sector_invariants.log)"} |
| benchmark | PASS | {"fixtures": "30 / 30", "tag": "p3_under_p4rel"} |
