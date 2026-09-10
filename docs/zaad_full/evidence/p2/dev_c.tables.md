# P2 benchmark tables (6 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | VALID | network_rop | +0.69% | 2% | 0.954 | 0.966 | 1126 | 4.0/6 | 6/7/13 | PASS |
| B_correlated_demand | VALID | network_rop | -0.13% | 2% | 0.972 | 0.969 | 1187 | 5.0/6 | 7/16/17 | PASS |
| C_short_transfer_lead | VALID | network_rop | +0.69% | 2% | 0.954 | 0.966 | 1126 | 4.0/6 | 6/7/13 | PASS |
| D_long_transfer_lead | VALID | network_rop | +3.56% | 2% | 0.976 | 0.998 | 1187 | 0.0/6 | 5/8/19 | FAIL |
| E_high_transfer_cost | VALID | independent | +0.79% | 2% | 0.950 | 0.966 | 1142 | 5.0/6 | 5/6/10 | PASS |
| F_low_transfer_cost | VALID | independent | +1.01% | 2% | 0.955 | 0.967 | 1187 | 4.0/6 | 8/11/16 | PASS |
| G_central_supply_shortage | VALID | independent | +0.00% | 3% | 0.565 | 0.565 | 689 | 6.0/6 | 5/9/12 | PASS |
| H_one_branch_demand_shock | VALID | independent | +5.59% | 3% | 0.924 | 0.721 | 1665 | 2.0/6 | 40/57/93 | FAIL |
| I_shared_supplier_disruption | VALID | network_rop | +0.37% | 5% | 0.953 | 0.966 | 1130 | 0.0/6 | 1/1/1 | PASS |
| J_asymmetric_service_targets | VALID | independent | +1.43% | 2% | 0.946 | 0.946 | 1127 | 3.0/6 | 20/23/30 | PASS |
| K_unequal_demand_scale | VALID | network_rop | +1.20% | 2% | 0.968 | 0.976 | 2021 | 1.0/6 | 10/16/33 | PASS |
| L_already_efficient_network | VALID | independent | +0.84% | 2% | 0.969 | 0.969 | 930 | 5.0/6 | 10/12/13 | PASS |
| M_transfer_not_reachable_in_time | VALID | independent | +0.60% | 2% | 0.401 | 0.401 | 1321 | 4.0/6 | 9/11/16 | FAIL |
| N_pipeline_already_solves_shortage | VALID | independent | +0.16% | 2% | 0.897 | 0.897 | 736 | 6.0/6 | 7/14/24 | PASS |
| O_multiple_transfer_options | VALID | independent | -1.20% | 2% | 0.980 | 0.966 | 1215 | 0.0/6 | 6/10/13 | PASS |
| P_transfer_capacity_limit | VALID | network_rop | +0.00% | 3% | 0.763 | 0.763 | 840 | 6.0/6 | 7/8/10 | PASS |
| Q_pack_constraint_on_transfer | VALID | independent | +1.69% | 2% | 1.000 | 0.939 | 1512 | 0.0/6 | 117/127/146 | PASS |
| R_order_transfer_interaction | VALID | independent | -2.34% | 2% | 0.988 | 0.991 | 3920 | 0.0/6 | 13/61/103 | PASS |
| S_recovery_after_imbalance | VALID | independent | +0.87% | 3% | 0.819 | 0.819 | 950 | 5.0/6 | 8/11/15 | PASS |
| T_single_node_network_off | VALID | echelon_base_stock | +1.02% | 2% | 0.993 | 1.000 | 0 | 0.0/6 | 0/0/1 | PASS |

## Policies per fixture (cost, service per branch)

### A_independent_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,597 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| central_pool | 6,597 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| independent | 6,608 | svc_north=0.994, svc_south=0.960 | 1.0 | 1126 | 1073 | 106 | 10.0 |
| echelon_base_stock | 6,623 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1054 | 78 | 0.8 |
| gated | 6,642 | svc_north=0.992, svc_south=0.954 | 1.0 | 1126 | 1520 | 75 | 6.3 |

### B_correlated_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,669 | svc_north=0.997, svc_south=0.969 | 1.0 | 1175 | 1119 | 61 | 0.0 |
| central_pool | 6,669 | svc_north=0.997, svc_south=0.969 | 1.0 | 1175 | 1119 | 61 | 0.0 |
| independent | 6,755 | svc_north=0.986, svc_south=0.957 | 1.0 | 1149 | 1106 | 94 | 13.4 |
| echelon_base_stock | 6,757 | svc_north=1.000, svc_south=0.948 | 1.0 | 1176 | 1112 | 69 | 0.7 |
| gated | 6,661 | svc_north=0.997, svc_south=0.972 | 0.0 | 1187 | 1122 | 67 | 7.5 |

### C_short_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,597 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| central_pool | 6,597 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| independent | 6,608 | svc_north=0.994, svc_south=0.960 | 1.0 | 1126 | 1073 | 106 | 10.6 |
| echelon_base_stock | 6,623 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1054 | 78 | 0.8 |
| gated | 6,642 | svc_north=0.992, svc_south=0.954 | 1.0 | 1126 | 1520 | 75 | 6.3 |

### D_long_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,275 | svc_north=1.000, svc_south=0.998 | 0.0 | 1169 | 1098 | 192 | 0.0 |
| central_pool | 6,275 | svc_north=1.000, svc_south=0.998 | 0.0 | 1169 | 1098 | 192 | 0.0 |
| independent | 6,504 | svc_north=0.985, svc_south=0.965 | 1.0 | 1157 | 1118 | 235 | 1.4 |
| echelon_base_stock | 6,276 | svc_north=1.000, svc_south=0.998 | 0.0 | 1174 | 1102 | 193 | 0.5 |
| gated | 6,498 | svc_north=0.979, svc_south=0.976 | 1.0 | 1187 | 1514 | 244 | 5.0 |

### E_high_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,189 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| central_pool | 8,189 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1054 | 74 | 0.0 |
| independent | 8,126 | svc_north=0.997, svc_south=0.975 | 0.0 | 1160 | 1076 | 90 | 1.9 |
| echelon_base_stock | 8,209 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1054 | 78 | 0.6 |
| gated | 8,190 | svc_north=0.996, svc_south=0.950 | 1.0 | 1142 | 1054 | 72 | 5.3 |

### F_low_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,406 | svc_north=0.981, svc_south=0.967 | 1.0 | 1203 | 810 | 140 | 0.0 |
| central_pool | 6,406 | svc_north=0.981, svc_south=0.967 | 1.0 | 1203 | 810 | 140 | 0.0 |
| independent | 6,387 | svc_north=0.983, svc_south=0.960 | 1.0 | 1380 | 811 | 205 | 2.5 |
| echelon_base_stock | 6,434 | svc_north=1.000, svc_south=0.941 | 1.0 | 1199 | 810 | 144 | 0.7 |
| gated | 6,452 | svc_north=0.992, svc_south=0.955 | 1.0 | 1187 | 1277 | 142 | 7.8 |

### G_central_supply_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 10,196 | svc_north=0.572, svc_south=0.565 | 6.0 | 689 | 720 | 0 | 0.0 |
| central_pool | 10,196 | svc_north=0.572, svc_south=0.565 | 6.0 | 689 | 720 | 0 | 0.0 |
| independent | 10,195 | svc_north=0.566, svc_south=0.570 | 6.0 | 689 | 720 | 0 | 3.2 |
| echelon_base_stock | 10,372 | svc_north=0.938, svc_south=0.168 | 6.0 | 689 | 720 | 11 | 0.4 |
| gated | 10,196 | svc_north=0.572, svc_south=0.565 | 6.0 | 689 | 720 | 0 | 4.5 |

### H_one_branch_demand_shock
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,853 | svc_north=0.919, svc_south=0.721 | 4.0 | 1365 | 1261 | 165 | 0.0 |
| central_pool | 9,853 | svc_north=0.919, svc_south=0.721 | 4.0 | 1365 | 1261 | 165 | 0.0 |
| independent | 8,003 | svc_north=0.997, svc_south=0.966 | 1.0 | 1640 | 1616 | 164 | 7.7 |
| echelon_base_stock | 9,619 | svc_north=1.000, svc_south=0.703 | 3.0 | 1397 | 1298 | 153 | 0.9 |
| gated | 8,451 | svc_north=0.924, svc_south=0.952 | 2.0 | 1665 | 2282 | 120 | 40.3 |

### I_shared_supplier_disruption
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,597 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1104 | 65 | 0.0 |
| central_pool | 6,597 | svc_north=0.980, svc_south=0.966 | 1.0 | 1142 | 1104 | 65 | 0.0 |
| independent | 6,616 | svc_north=0.982, svc_south=0.959 | 1.0 | 1131 | 1116 | 69 | 2.8 |
| echelon_base_stock | 6,623 | svc_north=1.000, svc_south=0.941 | 1.0 | 1138 | 1104 | 70 | 0.7 |
| gated | 6,621 | svc_north=0.988, svc_south=0.953 | 2.0 | 1130 | 1102 | 64 | 0.8 |

### J_asymmetric_service_targets
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,599 | svc_north=1.000, svc_south=0.946 | 2.0 | 1146 | 1170 | 69 | 0.0 |
| central_pool | 6,599 | svc_north=1.000, svc_south=0.946 | 2.0 | 1146 | 1170 | 69 | 0.0 |
| independent | 6,548 | svc_north=1.000, svc_south=0.958 | 2.0 | 1118 | 1157 | 71 | 6.8 |
| echelon_base_stock | 6,574 | svc_north=1.000, svc_south=0.952 | 2.0 | 1149 | 1177 | 71 | 1.3 |
| gated | 6,642 | svc_north=1.000, svc_south=0.946 | 2.0 | 1127 | 1628 | 69 | 20.0 |

### K_unequal_demand_scale
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,239 | svc_north=0.990, svc_south=0.976 | 0.0 | 2046 | 1955 | 101 | 0.0 |
| central_pool | 11,239 | svc_north=0.990, svc_south=0.976 | 0.0 | 2046 | 1955 | 101 | 0.0 |
| independent | 11,373 | svc_north=0.982, svc_south=0.959 | 1.0 | 2025 | 1938 | 101 | 1.3 |
| echelon_base_stock | 11,366 | svc_north=1.000, svc_south=0.858 | 1.0 | 2052 | 1947 | 110 | 0.4 |
| gated | 11,374 | svc_north=0.981, svc_south=0.968 | 1.0 | 2021 | 1938 | 99 | 10.1 |

### L_already_efficient_network
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,513 | svc_north=0.982, svc_south=0.969 | 1.0 | 945 | 750 | 213 | 0.0 |
| central_pool | 6,513 | svc_north=0.982, svc_south=0.969 | 1.0 | 945 | 750 | 213 | 0.0 |
| independent | 6,504 | svc_north=0.983, svc_south=0.960 | 2.0 | 1032 | 740 | 294 | 2.0 |
| echelon_base_stock | 6,549 | svc_north=1.000, svc_south=0.943 | 1.0 | 940 | 749 | 217 | 0.7 |
| gated | 6,558 | svc_north=0.982, svc_south=0.969 | 1.0 | 930 | 1218 | 215 | 9.6 |

### M_transfer_not_reachable_in_time
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,596 | svc_north=0.412, svc_south=0.401 | 4.0 | 1253 | 665 | 315 | 0.0 |
| central_pool | 11,596 | svc_north=0.412, svc_south=0.401 | 4.0 | 1253 | 665 | 314 | 0.0 |
| independent | 11,593 | svc_north=0.412, svc_south=0.401 | 4.0 | 1280 | 683 | 299 | 3.4 |
| echelon_base_stock | 11,596 | svc_north=0.412, svc_south=0.401 | 4.0 | 1258 | 669 | 316 | 0.1 |
| gated | 11,663 | svc_north=0.412, svc_south=0.401 | 4.0 | 1321 | 1159 | 323 | 8.7 |

### N_pipeline_already_solves_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,142 | svc_north=0.905, svc_south=0.897 | 1.0 | 736 | 555 | 277 | 0.0 |
| central_pool | 7,142 | svc_north=0.905, svc_south=0.897 | 1.0 | 736 | 555 | 277 | 0.0 |
| independent | 7,131 | svc_north=0.905, svc_south=0.897 | 1.0 | 746 | 554 | 298 | 3.9 |
| echelon_base_stock | 7,143 | svc_north=0.905, svc_south=0.897 | 1.0 | 741 | 559 | 278 | 0.5 |
| gated | 7,142 | svc_north=0.905, svc_south=0.897 | 1.0 | 736 | 555 | 277 | 7.2 |

### O_multiple_transfer_options
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,392 | svc_north=0.980, svc_south=0.966 | 1.0 | 1002 | 912 | 137 | 0.0 |
| central_pool | 7,392 | svc_north=0.980, svc_south=0.966 | 1.0 | 1002 | 912 | 137 | 0.0 |
| independent | 6,530 | svc_north=0.994, svc_south=0.972 | 1.0 | 1195 | 1343 | 131 | 3.2 |
| echelon_base_stock | 7,413 | svc_north=1.000, svc_south=0.941 | 1.0 | 999 | 912 | 141 | 0.9 |
| gated | 6,452 | svc_north=0.998, svc_south=0.980 | 1.0 | 1215 | 1610 | 160 | 5.9 |

### P_transfer_capacity_limit
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,384 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 914 | 188 | 0.0 |
| central_pool | 8,384 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 914 | 188 | 0.0 |
| independent | 8,384 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 929 | 201 | 5.7 |
| echelon_base_stock | 8,384 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 916 | 190 | 0.1 |
| gated | 8,384 | svc_north=0.781, svc_south=0.763 | 4.0 | 840 | 914 | 188 | 7.4 |

### Q_pack_constraint_on_transfer
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 6,965 | svc_north=0.965, svc_south=0.939 | 2.0 | 1104 | 1027 | 89 | 0.0 |
| central_pool | 6,965 | svc_north=0.965, svc_south=0.939 | 2.0 | 1104 | 1027 | 89 | 0.0 |
| independent | 6,451 | svc_north=1.000, svc_south=1.000 | 0.0 | 1344 | 1498 | 331 | 28.5 |
| echelon_base_stock | 6,913 | svc_north=0.977, svc_south=0.939 | 2.0 | 1104 | 1038 | 89 | 0.5 |
| gated | 6,560 | svc_north=1.000, svc_south=1.000 | 0.0 | 1512 | 1851 | 261 | 116.8 |

### R_order_transfer_interaction
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 24,008 | svc_north=0.991, svc_south=0.993 | 1.0 | 0 | 4050 | 343 | 0.0 |
| central_pool | 24,008 | svc_north=0.991, svc_south=0.993 | 1.0 | 0 | 4050 | 343 | 0.0 |
| independent | 23,112 | svc_north=0.992, svc_south=1.000 | 1.0 | 3961 | 5553 | 1126 | 13.2 |
| echelon_base_stock | 23,987 | svc_north=0.992, svc_south=0.994 | 1.0 | 0 | 4058 | 346 | 0.3 |
| gated | 22,570 | svc_north=0.995, svc_south=0.988 | 1.0 | 3920 | 4163 | 949 | 12.5 |

### S_recovery_after_imbalance
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 7,209 | svc_north=0.981, svc_south=0.819 | 3.0 | 950 | 758 | 208 | 0.0 |
| central_pool | 7,209 | svc_north=0.982, svc_south=0.819 | 2.0 | 952 | 758 | 207 | 0.0 |
| independent | 7,191 | svc_north=0.993, svc_south=0.810 | 2.0 | 935 | 770 | 280 | 1.9 |
| echelon_base_stock | 7,244 | svc_north=1.000, svc_south=0.793 | 2.0 | 948 | 757 | 212 | 0.5 |
| gated | 7,254 | svc_north=0.981, svc_south=0.819 | 3.0 | 950 | 1227 | 208 | 8.1 |

### T_single_node_network_off
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 3,060 | svc_branch=1.000 | 0.0 | 0 | 588 | 22 | 0.0 |
| central_pool | 3,060 | svc_branch=1.000 | 0.0 | 0 | 588 | 22 | 0.0 |
| independent | 3,090 | svc_branch=0.993 | 0.0 | 0 | 579 | 20 | 0.4 |
| echelon_base_stock | 3,058 | svc_branch=1.000 | 0.0 | 0 | 590 | 23 | 0.1 |
| gated | 3,090 | svc_branch=0.993 | 0.0 | 0 | 579 | 20 | 0.5 |

## Network principles

| principle | pass | numbers |
|---|---|---|
| pooling_has_value | PASS | {'pooling_benefit_vs_independent': -0.0053} |
| pooling_benefit_shrinks | PASS | {'benefit_A': -0.0053, 'benefit_B': 0.0139} |
| correlated_demand_no_fabricated_diversification | PASS | {'protection_A': 74.9287, 'protection_B': 67.2807} |
| long_lead_positions_more_locally | PASS | {'branch_cover_C': 0.2249, 'branch_cover_D': 0.8434} |
| no_churn_at_high_transfer_cost | PASS | {'zaad_units': 1142.0024, 'incumbent_units': 1142.0024, 'demand': 1217.6592} |
| rebalance_before_purchase | PASS | {'zaad_early_purchases': 0, 'incumbent_early_purchases': 0, 'zaad_early_transfers': 391.3427} |
| principled_allocation_under_shortage | PASS | {'service': {'svc_north': 0.572068210092659, 'svc_south': 0.5648954544168494}} |
| healthy_branch_not_starved | PASS | {'north': 0.9245, 'south': 0.9519, 'incumbent_north': 0.919} |
| priority_branch_protected | PASS | {'north': 1.0, 'south': 0.9464} |
| small_branch_not_starved | PASS | {'south': 0.968} |
| already_efficient_abstains | PASS | {'abstained_share': 0.8333, 'cost_gap': 0.0069} |
| remote_stock_not_credited | FAIL | {'service': {'svc_north': 0.41157194967484056, 'svc_south': 0.4009067765529472}} |
| no_over_transfer_when_pipeline_covers | PASS | {'zaad_units': 736.477, 'demand': 1217.6592} |
| cheap_lane_when_time_allows | PASS | {} |
| capacity_respected | PASS | {} |
| legal_packs | PASS | {} |
| recovery_without_ping_pong | PASS | {'south': 0.8193} |
| single_node_identity | PASS | {} |
