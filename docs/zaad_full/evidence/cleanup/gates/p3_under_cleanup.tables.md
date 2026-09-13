# P3 benchmark `p3_under_cleanup`

30 / 30 fixtures PASS

| fixture | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent mix | abstained / 8 | wall p50 / max s | principle |
|---|---|---|---|---|---|---|---|---|
| E1_dominant_source | cheapest_landed | +0.00% | 2% | 0.978 | 0.978 | 7.5 | 0.4 / 0.8 | b_unused (PASS) | PASS
| E2_landed_beats_unit_price | cheapest_landed | +0.00% | 2% | 0.978 | 0.978 | 7.5 | 0.5 / 0.8 | a_dominant_share (PASS) | PASS
| E3_price_break_scale | cheapest_landed | +0.28% | 2% | 0.980 | 0.977 | 7.0 | 1.6 / 2.7 | tier2_when_large (PASS) | PASS
| E4_moq_mov_small_order | cheapest_landed | -1.00% | 2% | 0.998 | 0.992 | 1.5 | 7.4 / 12.6 | b_orders_executable (PASS) | PASS
| E5_payment_terms_preference | single:supplier_b | +0.96% | 2% | 0.980 | 0.980 | 5.5 | 0.4 / 0.9 | a_dominant_share (PASS) | PASS
| E6_switching_cost_retains_incumbent | incumbent_mix | +0.00% | 2% | 0.978 | 0.978 | 7.5 | 2.4 / 2.9 | b_unused (PASS) | PASS
| R1_cheap_unreliable | incumbent_mix | -0.59% | 3% | 0.978 | 0.979 | 3.5 | 1.2 / 1.4 | not_worse (PASS) | PASS
| R2_capacity_forces_split | single:supplier_b | -2.59% | 3% | 0.978 | 0.722 | 6.0 | 0.6 / 1.0 | a_at_capacity_then_b (PASS) | PASS
| R3_independent_tail_benefit | cheapest_landed | +0.10% | 3% | 0.978 | 0.978 | 1.5 | 0.4 / 1.0 | not_worse (PASS) | PASS
| R4_shared_plant_no_fake_diversification | cheapest_landed | +0.43% | 3% | 0.987 | 0.992 | 1.5 | 5.2 / 7.4 | no_split (PASS) | PASS
| R5_shared_port_risk | single:supplier | +0.12% | 3% | 0.982 | 0.979 | 2.5 | 0.4 / 0.9 | group_listed (PASS) | PASS
| R6_identical_no_split | single:supplier_b | +0.27% | 3% | 0.987 | 0.992 | 1.5 | 5.1 / 7.4 | no_split (PASS) | PASS
| C1_supplier_max_capacity | incumbent_mix | +0.22% | 2% | 0.888 | 0.893 | 6.0 | 0.4 / 0.7 | both_used_within_capacity (PASS) | PASS
| C2_declared_min_max_share | cheapest_landed | +0.82% | 2% | 0.980 | 0.979 | 7.5 | 0.4 / 0.7 | min_share_honoured (PASS) | PASS
| C3_source_blackout | single:supplier_b | +0.00% | 2% | 0.989 | 0.639 | 7.0 | 0.4 / 0.8 | no_purchase_in_blackout (PASS) | PASS
| C4_unqualified_source | cheapest_landed | +0.26% | 2% | 0.978 | 0.978 | 6.5 | 0.4 / 0.8 | unqualified_unused (PASS) | PASS
| C5_shared_capacity_multi_sku | single:supplier_s2 | -4.27% | 2% | 0.966 | 0.570 | 3.0 | 1.6 / 2.6 | shared_resource_respected (PASS) | PASS
| C6_shared_mov_multi_sku | single:supplier | -1.29% | 2% | 0.988 | 0.992 | 1.0 | 17.7 / 25.6 | shared_mov_respected (PASS) | PASS
| S1_produce_short_life | incumbent_mix | +0.01% | 3% | 0.978 | 0.978 | 7.0 | 1.3 / 3.8 | b_unused (PASS) | PASS
| S2_produce_yield_uncertainty | incumbent_mix | +1.66% | 3% | 0.969 | 0.976 | 0.0 | 15.0 / 26.0 | not_worse (PASS) | PASS
| S3_frozen_invalid_route | cheapest_landed | +0.00% | 3% | 0.978 | 0.978 | 7.5 | 0.4 / 1.0 | b_unused (PASS) | PASS
| S4_commercial_pallets | single:supplier | +0.66% | 3% | 0.987 | 0.992 | 4.5 | 24.1 / 42.9 | whole_packs (PASS) | PASS
| N1_source_to_central_with_transfers | cheapest_landed | +0.23% | 2% | 0.929 | 0.933 | 1.5 | 0.9 / 1.2 | conservation (PASS) | PASS
| N2_local_and_central_conserved | cheapest_landed | -0.04% | 2% | 0.980 | 0.991 | 1.0 | 0.3 / 0.3 | conservation (PASS) | PASS
| N3_mixed_sector_shared_capacity | single:supplier_s2 | -3.97% | 2% | 0.972 | 0.570 | 3.5 | 6.6 / 14.6 | shared_resource_respected (PASS) | PASS
| A1_incumbent_mix_optimal | incumbent_mix | +0.00% | 2% | 0.979 | 0.979 | 8.0 | 0.4 / 0.7 | abstains (PASS) | PASS
| A2_weak_evidence_flagged | single:supplier_b | +1.01% | 3% | 0.978 | 0.978 | 8.0 | 0.5 / 0.9 | weak_evidence_flagged (PASS) | PASS
| A3_pruning_identity | incumbent_mix | -1.04% | 2% | 0.984 | 0.978 | 6.5 | 0.4 / 0.7 | prune_identity (PASS) | PASS
| A5_single_source_legacy_identity | cheapest_landed | +0.12% | 2% | 0.978 | 0.978 | 6.5 | 0.3 / 0.6 | legacy_identity (PASS) | PASS
| A6_no_order_no_allocation | single:supplier | +0.44% | 2% | 1.000 | 1.000 | 5.0 | 0.5 / 0.6 | no_order_no_allocation (PASS) | PASS

Runtime (ZAAD reviews 480): p50 0.6719402289018035, p95 18.059279874898493, max 42.91339954268187; over 60 s: 0; over 180 s: 0; solve statuses {'OPTIMAL': 2251, 'INFEASIBLE': 6}
Errors: []
