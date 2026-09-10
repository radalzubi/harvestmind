# P2 benchmark tables (6 rolling reviews, continuation-valued cost, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | VALID | independent | +3.14% | 2% | 0.954 | 0.966 | 1126 | 4.0/6 | 6/7/8 | FAIL |
| B_correlated_demand | VALID | independent | +0.25% | 2% | 0.972 | 0.969 | 1187 | 4.0/6 | 9/10/12 | PASS |
| C_short_transfer_lead | VALID | independent | +3.14% | 2% | 0.954 | 0.966 | 1126 | 4.0/6 | 6/7/8 | FAIL |
| D_long_transfer_lead | VALID | independent | +6.23% | 2% | 0.976 | 0.998 | 1220 | 0.0/6 | 5/7/16 | FAIL |
| E_high_transfer_cost | VALID | independent | +17.08% | 2% | 0.969 | 0.966 | 1126 | 0.0/6 | 9/10/19 | FAIL |
| F_low_transfer_cost | VALID | network_rop | +1.38% | 2% | 0.902 | 0.914 | 1256 | 4.0/6 | 10/12/13 | FAIL |
| G_central_supply_shortage | INVALID: no competent baseline completed | - | +nan% | 0% | 0.565 | 0.565 | 689 | 6.0/6 | 4/8/11 | - |
| H_one_branch_demand_shock | VALID | independent | +8.84% | 3% | 0.924 | 0.721 | 1665 | 2.0/6 | 37/53/90 | FAIL |
| I_shared_supplier_disruption | VALID | independent | +0.67% | 5% | 0.953 | 0.966 | 1130 | 0.0/6 | 1/1/1 | PASS |
| J_asymmetric_service_targets | VALID | independent | +4.44% | 2% | 0.946 | 0.946 | 1127 | 4.0/6 | 16/17/18 | FAIL |
| K_unequal_demand_scale | VALID | network_rop | +1.17% | 2% | 0.967 | 0.976 | 2021 | 2.0/6 | 7/9/15 | PASS |
| L_already_efficient_network | VALID | independent | +3.39% | 2% | 0.969 | 0.969 | 946 | 5.0/6 | 8/10/11 | FAIL |
| M_transfer_not_reachable_in_time | INVALID: no competent baseline completed | - | +nan% | 0% | 0.401 | 0.401 | 1295 | 4.0/6 | 6/10/14 | - |
| N_pipeline_already_solves_shortage | INVALID: no competent baseline completed | - | +nan% | 0% | 0.897 | 0.897 | 736 | 6.0/6 | 7/10/21 | - |
| O_multiple_transfer_options | VALID | independent | -2.44% | 2% | 0.980 | 0.966 | 1215 | 0.0/6 | 5/7/10 | PASS |
| P_transfer_capacity_limit | INVALID: no competent baseline completed | - | +nan% | 0% | 0.763 | 0.763 | 840 | 6.0/6 | 7/8/9 | - |
| Q_pack_constraint_on_transfer | VALID | independent | +5.16% | 2% | 0.977 | 0.939 | 1632 | 0.0/6 | 158/167/306 | FAIL |
| R_order_transfer_interaction | VALID | independent | +1.59% | 2% | 0.968 | 0.978 | 1316 | 0.0/6 | 10/17/25 | PASS |
| S_recovery_after_imbalance | INVALID: no competent baseline completed | - | +nan% | 0% | 0.819 | 0.819 | 937 | 5.0/6 | 7/12/14 | - |
| T_single_node_network_off | VALID | echelon_base_stock | +1.00% | 2% | 0.993 | 1.000 | 0 | 0.0/6 | 0/1/1 | PASS |

## Policies per fixture (cost, service per branch)

### A_independent_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,732 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| central_pool | 6,732 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| independent | 6,703 | svc_north=0.982, svc_south=0.959 | 1.0 | 0 | 1059 | 72 | 0.8 |
| echelon_base_stock | 6,758 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1054 | 78 | 0.8 |
| gated | 6,914 | svc_north=0.992, svc_south=0.954 | 1.0 | 1126 | 1520 | 75 | 6.0 |

### B_correlated_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,811 | svc_north=0.997, svc_south=0.969 | 1.0 | 1175 | 1119 | 61 | 0.0 |
| central_pool | 6,811 | svc_north=0.997, svc_south=0.969 | 1.0 | 1175 | 1119 | 61 | 0.0 |
| independent | 6,786 | svc_north=0.995, svc_south=0.965 | 1.0 | 0 | 1125 | 66 | 0.8 |
| echelon_base_stock | 6,900 | svc_north=1.000, svc_south=0.948 | 1.0 | 1176 | 1112 | 69 | 0.7 |
| gated | 6,803 | svc_north=0.997, svc_south=0.972 | 0.0 | 1187 | 1122 | 68 | 9.4 |

### C_short_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,732 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| central_pool | 6,732 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| independent | 6,703 | svc_north=0.982, svc_south=0.959 | 1.0 | 0 | 1059 | 72 | 0.8 |
| echelon_base_stock | 6,758 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1054 | 78 | 0.8 |
| gated | 6,914 | svc_north=0.992, svc_south=0.954 | 1.0 | 1126 | 1520 | 75 | 6.0 |

### D_long_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,534 | svc_north=1.000, svc_south=0.998 | 0.0 | 1169 | 1098 | 192 | 0.0 |
| central_pool | 6,534 | svc_north=1.000, svc_south=0.998 | 0.0 | 1169 | 1098 | 192 | 0.0 |
| independent | 6,482 | svc_north=1.000, svc_south=1.000 | 0.0 | 0 | 1117 | 193 | 0.4 |
| echelon_base_stock | 6,536 | svc_north=1.000, svc_south=0.998 | 0.0 | 1174 | 1102 | 193 | 0.4 |
| gated | 6,886 | svc_north=0.979, svc_south=0.976 | 2.0 | 1220 | 1514 | 217 | 5.0 |

### E_high_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,122 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| central_pool | 9,122 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| independent | 8,611 | svc_north=0.982, svc_south=0.959 | 1.0 | 0 | 1059 | 71 | 0.7 |
| echelon_base_stock | 9,149 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1054 | 78 | 0.6 |
| gated | 10,082 | svc_north=0.976, svc_south=0.969 | 1.0 | 1126 | 1515 | 150 | 9.1 |

### F_low_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,987 | svc_north=0.918, svc_south=0.914 | 2.0 | 1253 | 861 | 112 | 0.0 |
| central_pool | 6,987 | svc_north=0.918, svc_south=0.914 | 2.0 | 1253 | 861 | 112 | 0.0 |
| independent | 7,005 | svc_north=0.920, svc_south=0.907 | 2.0 | 0 | 867 | 112 | 0.7 |
| echelon_base_stock | 7,013 | svc_north=0.938, svc_south=0.889 | 2.0 | 1249 | 862 | 116 | 1.1 |
| gated | 7,083 | svc_north=0.930, svc_south=0.902 | 2.0 | 1256 | 1328 | 110 | 10.3 |

### G_central_supply_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 10,266 | svc_north=0.572, svc_south=0.565 | 6.0 | 689 | 720 | 0 | 0.0 |
| central_pool | 10,266 | svc_north=0.572, svc_south=0.565 | 6.0 | 689 | 720 | 0 | 0.0 |
| independent | no run: ["ABSTAIN: north: ['ABSTAIN', 'operator_declared', 'mode=ALLOCATE', 'No candidate materially improves priority-weighted service shortfall over the incumbent; incumbent retained.', 'Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service recovery.', 'Incumbent itself has no verified feasible projection; no executable fallback is fabricated.', 'Requested service targets are not jointly achievable under the modeled state; selector evaluated best joint recovery instead of requiring an impossible SLA.']"] | | | | | | |
| echelon_base_stock | 10,450 | svc_north=0.938, svc_south=0.168 | 6.0 | 689 | 720 | 11 | 0.4 |
| gated | 10,266 | svc_north=0.572, svc_south=0.565 | 6.0 | 689 | 720 | 0 | 4.1 |

### H_one_branch_demand_shock
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 10,079 | svc_north=0.919, svc_south=0.721 | 4.0 | 1365 | 1261 | 165 | 0.0 |
| central_pool | 10,079 | svc_north=0.919, svc_south=0.721 | 4.0 | 1365 | 1261 | 165 | 0.0 |
| independent | 8,191 | svc_north=0.982, svc_south=0.967 | 1.0 | 0 | 1542 | 135 | 1.1 |
| echelon_base_stock | 9,846 | svc_north=1.000, svc_south=0.703 | 3.0 | 1397 | 1298 | 153 | 0.9 |
| gated | 8,915 | svc_north=0.924, svc_south=0.952 | 2.0 | 1665 | 2282 | 120 | 37.1 |

### I_shared_supplier_disruption
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,732 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1104 | 65 | 0.0 |
| central_pool | 6,732 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1104 | 65 | 0.0 |
| independent | 6,711 | svc_north=0.982, svc_south=0.959 | 1.0 | 0 | 1100 | 63 | 0.4 |
| echelon_base_stock | 6,758 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1104 | 70 | 0.7 |
| gated | 6,756 | svc_north=0.988, svc_south=0.953 | 2.0 | 1130 | 1102 | 64 | 0.7 |

### J_asymmetric_service_targets
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,738 | svc_north=1.000, svc_south=0.946 | 2.0 | 1146 | 1170 | 69 | 0.0 |
| central_pool | 6,738 | svc_north=1.000, svc_south=0.946 | 2.0 | 1146 | 1170 | 69 | 0.0 |
| independent | 6,623 | svc_north=1.000, svc_south=0.965 | 2.0 | 0 | 1185 | 60 | 0.8 |
| echelon_base_stock | 6,714 | svc_north=1.000, svc_south=0.952 | 2.0 | 1149 | 1177 | 71 | 1.2 |
| gated | 6,917 | svc_north=1.000, svc_south=0.946 | 2.0 | 1127 | 1628 | 68 | 16.1 |

### K_unequal_demand_scale
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,476 | svc_north=0.990, svc_south=0.976 | 0.0 | 2046 | 1955 | 101 | 0.0 |
| central_pool | 11,476 | svc_north=0.990, svc_south=0.976 | 0.0 | 2046 | 1955 | 101 | 0.0 |
| independent | no run: ["ABSTAIN: north: ['ABSTAIN', 'operator_declared', 'mode=LEAN', 'Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service recovery.', 'Incumbent itself has no verified feasible projection; no executable fallback is fabricated.']"] | | | | | | |
| echelon_base_stock | 11,606 | svc_north=1.000, svc_south=0.858 | 1.0 | 2052 | 1947 | 110 | 0.4 |
| gated | 11,610 | svc_north=0.981, svc_south=0.967 | 0.0 | 2021 | 1938 | 105 | 6.5 |

### L_already_efficient_network
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,648 | svc_north=0.982, svc_south=0.969 | 1.0 | 945 | 750 | 213 | 0.0 |
| central_pool | 6,648 | svc_north=0.982, svc_south=0.969 | 1.0 | 945 | 750 | 213 | 0.0 |
| independent | 6,606 | svc_north=0.983, svc_south=0.960 | 1.0 | 0 | 755 | 211 | 0.7 |
| echelon_base_stock | 6,685 | svc_north=1.000, svc_south=0.943 | 1.0 | 940 | 749 | 217 | 0.7 |
| gated | 6,830 | svc_north=0.982, svc_south=0.969 | 1.0 | 946 | 1218 | 212 | 8.1 |

### M_transfer_not_reachable_in_time
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,917 | svc_north=0.412, svc_south=0.401 | 4.0 | 1253 | 665 | 315 | 0.0 |
| central_pool | 11,917 | svc_north=0.412, svc_south=0.401 | 4.0 | 1253 | 665 | 314 | 0.0 |
| independent | 11,757 | svc_north=0.412, svc_south=0.401 | 4.0 | 0 | 688 | 229 | 0.4 |
| echelon_base_stock | 11,918 | svc_north=0.412, svc_south=0.401 | 4.0 | 1258 | 669 | 316 | 0.1 |
| gated | 12,126 | svc_north=0.412, svc_south=0.401 | 4.0 | 1295 | 1152 | 337 | 6.2 |

### N_pipeline_already_solves_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,277 | svc_north=0.905, svc_south=0.897 | 1.0 | 736 | 555 | 277 | 0.0 |
| central_pool | 7,277 | svc_north=0.905, svc_south=0.897 | 1.0 | 736 | 555 | 277 | 0.0 |
| independent | no run: ["ERROR: 1 validation error for Request\n  Value error, invalid reference or incompatible planning dimensions [type=value_error, input_value={'schema_version': 'zaad....nce_label': 'SYNTHETIC'}, input_type=dict]\n    For further information visit https://errors.pydantic.dev/2.13/v/value_error"] | | | | | | |
| echelon_base_stock | 7,278 | svc_north=0.905, svc_south=0.897 | 1.0 | 741 | 559 | 278 | 0.4 |
| gated | 7,277 | svc_north=0.905, svc_south=0.897 | 1.0 | 736 | 555 | 277 | 7.4 |

### O_multiple_transfer_options
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,645 | svc_north=0.980, svc_south=0.966 | 1.0 | 1002 | 912 | 137 | 0.0 |
| central_pool | 7,645 | svc_north=0.980, svc_south=0.966 | 1.0 | 1002 | 912 | 137 | 0.0 |
| independent | 7,401 | svc_north=0.982, svc_south=0.959 | 1.0 | 0 | 918 | 135 | 0.7 |
| echelon_base_stock | 7,671 | svc_north=1.000, svc_south=0.941 | 1.0 | 999 | 912 | 141 | 0.9 |
| gated | 7,220 | svc_north=0.998, svc_south=0.980 | 1.0 | 1215 | 1611 | 155 | 4.9 |

### P_transfer_capacity_limit
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,533 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 914 | 188 | 0.0 |
| central_pool | 8,533 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 914 | 188 | 0.0 |
| independent | 9,236 | svc_north=0.669, svc_south=0.671 | 3.0 | 0 | 420 | 39 | 0.2 |
| echelon_base_stock | 8,534 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 916 | 190 | 0.1 |
| gated | 8,533 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 914 | 188 | 7.2 |

### Q_pack_constraint_on_transfer
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,100 | svc_north=0.965, svc_south=0.939 | 2.0 | 1104 | 1027 | 89 | 0.0 |
| central_pool | 7,100 | svc_north=0.965, svc_south=0.939 | 2.0 | 1104 | 1027 | 89 | 0.0 |
| independent | 6,703 | svc_north=0.982, svc_south=0.959 | 1.0 | 0 | 1059 | 72 | 0.8 |
| echelon_base_stock | 7,049 | svc_north=0.977, svc_south=0.939 | 2.0 | 1104 | 1038 | 89 | 1.4 |
| gated | 7,049 | svc_north=0.977, svc_south=1.000 | 1.0 | 1632 | 1808 | 231 | 157.5 |

### R_order_transfer_interaction
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,290 | svc_north=1.000, svc_south=0.978 | 0.0 | 0 | 1180 | 346 | 0.0 |
| central_pool | 7,290 | svc_north=1.000, svc_south=0.978 | 0.0 | 0 | 1180 | 346 | 0.0 |
| independent | 7,246 | svc_north=0.994, svc_south=0.970 | 1.0 | 0 | 1167 | 42 | 1.1 |
| echelon_base_stock | 7,281 | svc_north=1.000, svc_south=0.981 | 0.0 | 0 | 1186 | 348 | 0.2 |
| gated | 7,361 | svc_north=1.000, svc_south=0.968 | 1.0 | 1316 | 2083 | 1050 | 9.7 |

### S_recovery_after_imbalance
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,344 | svc_north=0.981, svc_south=0.819 | 3.0 | 950 | 758 | 208 | 0.0 |
| central_pool | 7,344 | svc_north=0.982, svc_south=0.819 | 2.0 | 952 | 758 | 207 | 0.0 |
| independent | 7,228 | svc_north=1.000, svc_south=0.810 | 2.0 | 0 | 770 | 265 | 0.8 |
| echelon_base_stock | 7,380 | svc_north=1.000, svc_south=0.793 | 2.0 | 948 | 757 | 212 | 0.6 |
| gated | 7,527 | svc_north=0.981, svc_south=0.819 | 3.0 | 937 | 1227 | 210 | 7.0 |

### T_single_node_network_off
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 3,073 | svc_branch=1.000 | 0.0 | 0 | 588 | 22 | 0.0 |
| central_pool | 3,073 | svc_branch=1.000 | 0.0 | 0 | 588 | 22 | 0.0 |
| independent | 3,102 | svc_branch=0.993 | 0.0 | 0 | 579 | 20 | 0.4 |
| echelon_base_stock | 3,071 | svc_branch=1.000 | 0.0 | 0 | 590 | 23 | 0.1 |
| gated | 3,102 | svc_branch=0.993 | 0.0 | 0 | 579 | 20 | 0.5 |

## Network principles

| principle | pass | numbers |
|---|---|---|
| pooling_has_value | FAIL | {'pooling_benefit_vs_independent': -0.0314} |
| pooling_benefit_shrinks | FAIL | {'benefit_A': -0.0314, 'benefit_B': -0.0025} |
| correlated_demand_no_fabricated_diversification | PASS | {'protection_A': 74.9287, 'protection_B': 67.9273} |
| short_lead_pools_more_centrally | PASS | {'central_share_C': 0.3671, 'central_share_D': 0.3517} |
| no_churn_at_high_transfer_cost | PASS | {'zaad_units': 1125.9689, 'incumbent_units': 1142.0024, 'demand': 1217.6592} |
| rebalance_before_purchase | FAIL | {'zaad_purchases': 1328.3472, 'incumbent_purchases': 861.0563} |
| principled_allocation_under_shortage | PASS | {'service': {'svc_north': 0.572068210092659, 'svc_south': 0.5648954544168494}} |
| healthy_branch_not_starved | FAIL | {'north': 0.9245, 'south': 0.9519} |
| priority_branch_protected | PASS | {'north': 1.0, 'south': 0.9461} |
| small_branch_not_starved | PASS | {'south': 0.9669} |
| already_efficient_abstains | FAIL | {'abstained_share': 0.8333, 'cost_gap': 0.0274} |
| remote_stock_not_credited | FAIL | {'service': {'svc_north': 0.41157194967484056, 'svc_south': 0.4009067765529472}} |
| no_over_transfer_when_pipeline_covers | PASS | {'zaad_units': 736.477, 'demand': 1217.6592} |
| cheap_lane_when_time_allows | PASS | {} |
| capacity_respected | PASS | {} |
| legal_packs | PASS | {} |
| recovery_without_ping_pong | PASS | {'south': 0.8193} |
| single_node_identity | PASS | {} |
