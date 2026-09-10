# P2 adversarial review

| case | status | state | wall s | period-0 transfers | period-0 purchases | selected service | incumbent service | central share of end stock | findings |
|---|---|---|---|---|---|---|---|---|---|
| huge_central_zero_local | RETAIN_INCUMBENT | CAPITAL_OPTIMIZATION | 1 | 445 | 0 | {'svc_north': 0.911, 'svc_south': 0.907} | {'svc_north': 0.911, 'svc_south': 0.907} | 98% | none |
| zero_central_excess_one_branch | PENDING_REVIEW | NETWORK_ALLOCATION | 2 | 0 | 110 | {'svc_north': 1.0, 'svc_south': 0.82} | {'svc_north': 1.0, 'svc_south': 0.019} | 3% | none |
| both_branches_short | RETAIN_INCUMBENT | NETWORK_ALLOCATION | 19 | 60 | 579 | {'svc_north': 0.85, 'svc_south': 0.844} | {'svc_north': 0.85, 'svc_south': 0.844} | 20% | none |
| perfectly_correlated_spike | PENDING_REVIEW | NORMAL_REPLENISHMENT | 13 | 189 | 130 | {'svc_north': 0.997, 'svc_south': 0.992} | {'svc_north': 0.979, 'svc_south': 0.975} | 5% | none |
| independent_spikes | PENDING_REVIEW | NO_ACTION | 7 | 281 | 88 | {'svc_north': 0.975, 'svc_south': 0.965} | {'svc_north': 0.977, 'svc_south': 0.969} | 6% | none |
| one_lane_unavailable | RETAIN_INCUMBENT | NORMAL_REPLENISHMENT | 4 | 118 | 0 | {'svc_north': 0.99, 'svc_south': 0.241} | {'svc_north': 0.99, 'svc_south': 0.241} | 11% | none |
| long_lane_lead | RETAIN_INCUMBENT | NORMAL_REPLENISHMENT | 10 | 800 | 565 | {'svc_north': 0.626, 'svc_south': 0.621} | {'svc_north': 0.626, 'svc_south': 0.621} | 3% | none |
| zero_transfer_cost | RETAIN_INCUMBENT | NO_ACTION | 5 | 145 | 0 | {'svc_north': 0.99, 'svc_south': 0.983} | {'svc_north': 0.99, 'svc_south': 0.983} | 14% | none |
| enormous_transfer_cost | RETAIN_INCUMBENT | NO_ACTION | 25 | 145 | 0 | {'svc_north': 0.99, 'svc_south': 0.983} | {'svc_north': 0.99, 'svc_south': 0.983} | 14% | none |
| zero_supplier_availability | RETAIN_INCUMBENT | NORMAL_REPLENISHMENT | 0 | 245 | 0 | {'svc_north': 0.253, 'svc_south': 0.245} | {'svc_north': 0.253, 'svc_south': 0.245} | - | none |
| supplier_short_fill | RETAIN_INCUMBENT | PROTECT | 11 | 145 | 139 | {'svc_north': 0.806, 'svc_south': 0.631} | {'svc_north': 0.806, 'svc_south': 0.631} | 100% | none |
| targets_90_vs_99 | RETAIN_INCUMBENT | NORMAL_REPLENISHMENT | 15 | 200 | 295 | {'svc_north': 0.977, 'svc_south': 0.966} | {'svc_north': 0.977, 'svc_south': 0.966} | 18% | none |
| very_unequal_demand | RETAIN_INCUMBENT | NO_ACTION | 7 | 506 | 237 | {'svc_north': 0.991, 'svc_south': 0.992} | {'svc_north': 0.991, 'svc_south': 0.992} | 13% | none |
| branch_with_no_demand | PENDING_REVIEW | CAPITAL_OPTIMIZATION | 3 | 70 | 0 | {'svc_north': 0.997} | {'svc_north': 0.593} | 4% | none |
| transfer_capacity_zero | RETAIN_INCUMBENT | CAPITAL_OPTIMIZATION | 0 | 0 | 0 | {'svc_north': 0.257, 'svc_south': 0.241} | {'svc_north': 0.257, 'svc_south': 0.241} | 100% | none |
| moq_larger_than_branch_demand | RETAIN_INCUMBENT | NETWORK_ALLOCATION | 13 | 100 | 900 | {'svc_north': 0.953, 'svc_south': 0.947} | {'svc_north': 0.953, 'svc_south': 0.947} | 89% | none |
| central_full_load_economics | RETAIN_INCUMBENT | NETWORK_ALLOCATION | 9 | 50 | 3339 | {'svc_north': 0.951, 'svc_south': 0.945} | {'svc_north': 0.951, 'svc_south': 0.945} | 95% | none |
| recovery_after_disruption | RETAIN_INCUMBENT | NETWORK_ALLOCATION | 9 | 100 | 419 | {'svc_north': 0.917, 'svc_south': 0.909} | {'svc_north': 0.917, 'svc_south': 0.909} | 19% | none |
| already_perfect_incumbent | RETAIN_INCUMBENT | NO_ACTION | 7 | 0 | 0 | {'svc_north': 0.99, 'svc_south': 0.984} | {'svc_north': 0.99, 'svc_south': 0.984} | 14% | none |
| reverse_lane_at_cost | RETAIN_INCUMBENT | NO_ACTION | 7 | 0 | 0 | {'svc_north': 0.99, 'svc_south': 0.984} | {'svc_north': 0.99, 'svc_south': 0.984} | 14% | none |
| reverse_lane_free | REFUSED | None | 0 | 0 | 0 | None | None | - | none |
| five_branches | RETAIN_INCUMBENT | NO_ACTION | 15 | 214 | 0 | {'svc_b1': 0.989, 'svc_b2': 0.986, 'svc_b3': 0.99, 'svc_b4': 0.99, 'svc_b5': 0.988} | {'svc_b1': 0.989, 'svc_b2': 0.986, 'svc_b3': 0.99, 'svc_b4': 0.99, 'svc_b5': 0.988} | 16% | none |
