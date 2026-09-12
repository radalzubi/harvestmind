# P5 fixture matrix `p5_release_audit`

24 / 24 fixtures PASS (principle + invariants 1-19 on the recommended allocation; 3 runs identical)

| fixture | principle | verdict | incumbent | optimised | value | result |
|---|---|---|---|---|---|---|
| A_enough_for_everyone | incumbent_retained | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 0.0 | 0.0 | 0.0 | PASS |
| B_true_scarcity | higher_penalty_first | ALLOCATION CHANGE RECOMMENDED | 1100.0 | 300.0 | 800.0 | PASS |
| C_penalty_vs_margin | higher_total_driver_first | ALLOCATION CHANGE RECOMMENDED | 2000.0 | 1625.0 | 375.0 | PASS |
| D_partial_allowed | every_line_share | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 450.0 | 450.0 | 0.0 | PASS |
| E_partial_forbidden | all_or_nothing | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 450.0 | 450.0 | 0.0 | PASS |
| F_backorder_allowed | backordered_at_arrival | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 100.0 | 100.0 | 0.0 | PASS |
| G_backorder_forbidden | no_late_promise | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 375.0 | 375.0 | 0.0 | PASS |
| H_different_dates | own_dates | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 0.0 | 0.0 | 0.0 | PASS |
| I_inbound_in_time | inbound_counts | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 0.0 | 0.0 | 0.0 | PASS |
| J_inbound_too_late | inbound_excluded | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 450.0 | 450.0 | 0.0 | PASS |
| K_multiple_locations | alternative_priced | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 10.0 | 10.0 | 0.0 | PASS |
| L_transfer_lead | lead_respected_unmet | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 375.0 | 375.0 | 0.0 | PASS |
| L2_transfer_lead_backorder | lead_respected_backorder | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 35.0 | 35.0 | 0.0 | PASS |
| M_produce_remaining_life | no_expiring_cohort | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 20.0 | 20.0 | 0.0 | PASS |
| N_cold_chain | no_ineligible_state | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 450.0 | 450.0 | 0.0 | PASS |
| O_service_floor | floor_met | ALLOCATION CHANGE RECOMMENDED | 500.0 | 449.99999999500005 | 50.00000000499995 | PASS |
| P1_indifferent_lexical | deterministic_tie | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 375.0 | 375.0 | 0.0 | PASS |
| P2_indifferent_proportional | proportional_tie | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 375.0 | 375.0 | 0.0 | PASS |
| Q_optimal_incumbent | incumbent_retained_zero_value | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 300.0 | 300.0 | 0.0 | PASS |
| R_strategic_declared | strategic_through_economics | ALLOCATION CHANGE RECOMMENDED | 900.0 | 300.0 | 600.0 | PASS |
| S_malformed_provenance | refused_at_contract | 1 validation error for ServiceClass
  Va | - | - | - | PASS |
| T_double_reservation | reserved_never_promised | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 150.0 | 150.0 | 0.0 | PASS |
| U_substitution | declared_substitute_used | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 20.0 | 20.0 | 0.0 | PASS |
| V_mixed_sectors | each_line_own_physics | NO MATERIAL ALLOCATION IMPROVEMENT AVAIL | 340.0 | 340.0 | 0.0 | PASS |
