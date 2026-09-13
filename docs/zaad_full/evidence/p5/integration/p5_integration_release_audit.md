# P5 shared-core integration matrix `p5_integration_release_audit`

20 / 20 fixtures PASS (principle + invariants 1-19 on every recommendation; engine fixtures 3 runs identical)

| fixture | path | verdict | incumbent | optimised | value | result |
|---|---|---|---|---|---|---|
| I01_p0_protection_scarcity | planner | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | - | - | - | PASS |
| I02_network_direct_ship_from | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 0.0 | 0.0 | 0.0 | PASS |
| I03_implicit_transfer_rejected | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 375.0 | 375.0 | 0.0 | PASS |
| I04_perishable_fefo | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 0.0 | 0.0 | 0.0 | PASS |
| I05_cold_chain_eligibility | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 450.0 | 450.0 | 0.0 | PASS |
| I06_existing_reservation_excluded | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 150.0 | 150.0 | 0.0 | PASS |
| I07_order_bound_reservation_conservation | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 225.0 | 225.0 | 0.0 | PASS |
| I08_firm_vs_uncertain_inbound | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 450.0 | 450.0 | 0.0 | PASS |
| I09_partial_shipment | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 225.0 | 225.0 | 0.0 | PASS |
| I10_minimum_ship | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 600.0 | 600.0 | 0.0 | PASS |
| I11_backorder_allowed | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 100.0 | 100.0 | 0.0 | PASS |
| I12_backorder_prohibited | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 375.0 | 375.0 | 0.0 | PASS |
| I13_substitution_allowed | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 20.0 | 20.0 | 0.0 | PASS |
| I14_substitution_prohibited | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 300.0 | 300.0 | 0.0 | PASS |
| I15_identical_economics_identical_treatment | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 475.0 | 475.0 | 0.0 | PASS |
| I16_declared_priority_changes_allocation | engine | ALLOCATION CHANGE RECOMMENDED | 1475.0 | 475.0 | 1000.0 | PASS |
| I17_ledger_reconciliation | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 663.0 | 663.0 | 0.0 | PASS |
| I18_incumbent_wins | engine | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 300.0 | 300.0 | 0.0 | PASS |
| I19_tenant_mismatch_api | api |  | - | - | - | PASS |
| I20_disabled_exact_pre_p5 | planner |  | - | - | - | PASS |
