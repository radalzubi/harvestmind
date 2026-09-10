# P2 benchmark tables (8 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | VALID | independent | +0.12% | 2% | 0.978 | 0.978 | 1541 | 6.5/8 | 7/14/18 | PASS |
| B_correlated_demand | VALID | network_rop | -0.06% | 2% | 0.984 | 0.984 | 1531 | 6.0/8 | 12/16/21 | PASS |
| C_short_transfer_lead | VALID | independent | +0.12% | 2% | 0.978 | 0.978 | 1541 | 6.5/8 | 7/14/18 | PASS |
| D_long_transfer_lead | VALID | independent | -0.07% | 2% | 0.979 | 0.978 | 1618 | 0.0/8 | 58/87/88 | PASS |
| E_high_transfer_cost | VALID | independent | +0.34% | 2% | 0.977 | 0.978 | 1525 | 7.5/8 | 6/11/15 | PASS |
| F_low_transfer_cost | VALID | echelon_base_stock | +0.40% | 2% | 0.983 | 0.977 | 1605 | 6.5/8 | 7/11/16 | PASS |
| G_central_supply_shortage | VALID | independent | +0.00% | 3% | 0.565 | 0.565 | 922 | 8.0/8 | 4/9/12 | PASS |
| H_one_branch_demand_shock | VALID | independent | +2.06% | 3% | 0.963 | 0.770 | 2180 | 2.5/8 | 30/64/112 | PASS |
| I_shared_supplier_disruption | VALID | independent | +0.44% | 5% | 0.977 | 0.978 | 1522 | 0.5/8 | 1/1/1 | PASS |
| J_asymmetric_service_targets | VALID | echelon_base_stock | +1.35% | 2% | 0.968 | 0.972 | 1541 | 4.5/8 | 18/29/31 | PASS |
| K_unequal_demand_scale | VALID | network_rop | +0.63% | 2% | 0.980 | 0.985 | 2712 | 4.0/8 | 9/15/29 | PASS |
| L_already_efficient_network | VALID | echelon_base_stock | +0.46% | 2% | 0.977 | 0.977 | 1340 | 7.5/8 | 6/11/14 | PASS |
| M_transfer_not_reachable_in_time | VALID | central_pool | +0.02% | 2% | 0.545 | 0.545 | 1637 | 4.0/8 | 91/118/257 | PASS |
| N_pipeline_already_solves_shortage | VALID | echelon_base_stock | +0.40% | 2% | 0.920 | 0.919 | 1135 | 7.5/8 | 6/13/21 | PASS |
| O_multiple_transfer_options | VALID | independent | -0.69% | 2% | 0.990 | 0.978 | 1635 | 0.0/8 | 76/87/315 | PASS |
| P_transfer_capacity_limit | VALID | network_rop | +0.00% | 3% | 0.740 | 0.740 | 1120 | 8.0/8 | 7/9/11 | PASS |
| Q_pack_constraint_on_transfer | VALID | independent | -0.69% | 2% | 1.000 | 0.965 | 1812 | 0.0/8 | 26/59/89 | PASS |
| R_order_transfer_interaction | VALID | independent | -2.19% | 2% | 0.992 | 0.989 | 3935 | 0.0/8 | 12/60/96 | PASS |
| S_recovery_after_imbalance | VALID | independent | +0.71% | 3% | 0.872 | 0.872 | 1350 | 7.0/8 | 6/12/14 | PASS |
| T_single_node_network_off | VALID | echelon_base_stock | +0.86% | 2% | 0.986 | 0.990 | 0 | 2.0/8 | 0/1/1 | PASS |

## Policies per fixture (cost, service per branch)

### A_independent_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,826 | svc_north=0.987, svc_south=0.978 | 1.0 | 1543 | 1761 | 188 | 5.0 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1526 | 1469 | 67 | 0.9 |
| gated | 8,836 | svc_north=0.983, svc_south=0.978 | 1.0 | 1541 | 1494 | 152 | 6.5 |

### B_correlated_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,641 | svc_north=0.995, svc_south=0.984 | 0.5 | 1530 | 1449 | 66 | 0.0 |
| central_pool | 8,641 | svc_north=0.995, svc_south=0.984 | 0.5 | 1530 | 1449 | 66 | 0.0 |
| independent | 8,664 | svc_north=0.995, svc_south=0.982 | 0.5 | 1583 | 1658 | 115 | 5.2 |
| echelon_base_stock | 8,714 | svc_north=1.000, svc_south=0.968 | 1.0 | 1516 | 1438 | 74 | 0.7 |
| gated | 8,636 | svc_north=0.997, svc_south=0.984 | 0.0 | 1531 | 1446 | 71 | 12.1 |

### C_short_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,826 | svc_north=0.987, svc_south=0.978 | 1.0 | 1543 | 1761 | 188 | 5.1 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1526 | 1469 | 67 | 0.9 |
| gated | 8,836 | svc_north=0.983, svc_south=0.978 | 1.0 | 1541 | 1494 | 152 | 6.6 |

### D_long_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,734 | svc_north=0.978, svc_south=0.983 | 1.0 | 1559 | 1492 | 150 | 0.0 |
| central_pool | 8,734 | svc_north=0.978, svc_south=0.983 | 1.0 | 1559 | 1492 | 150 | 0.0 |
| independent | 8,713 | svc_north=0.990, svc_south=0.981 | 0.5 | 1730 | 1936 | 285 | 21.4 |
| echelon_base_stock | 8,757 | svc_north=0.987, svc_south=0.970 | 1.0 | 1564 | 1491 | 154 | 0.4 |
| gated | 8,707 | svc_north=0.979, svc_south=0.990 | 1.0 | 1618 | 1663 | 338 | 57.9 |

### E_high_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,169 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 11,169 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 11,131 | svc_north=0.987, svc_south=0.989 | 0.5 | 1871 | 2026 | 216 | 3.4 |
| echelon_base_stock | 11,170 | svc_north=0.992, svc_south=0.969 | 1.5 | 1527 | 1469 | 67 | 0.8 |
| gated | 11,170 | svc_north=0.984, svc_south=0.977 | 1.0 | 1525 | 1465 | 63 | 6.4 |

### F_low_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,539 | svc_north=0.977, svc_south=0.988 | 1.0 | 1587 | 1222 | 113 | 0.0 |
| central_pool | 8,539 | svc_north=0.977, svc_south=0.988 | 1.0 | 1587 | 1222 | 113 | 0.0 |
| independent | 8,575 | svc_north=0.972, svc_south=0.982 | 1.5 | 1676 | 1550 | 206 | 3.3 |
| echelon_base_stock | 8,504 | svc_north=0.992, svc_south=0.978 | 1.0 | 1596 | 1231 | 113 | 1.0 |
| gated | 8,539 | svc_north=0.983, svc_south=0.983 | 1.0 | 1605 | 1253 | 200 | 7.0 |

### G_central_supply_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 13,752 | svc_north=0.566, svc_south=0.565 | 8.0 | 922 | 960 | 0 | 0.0 |
| central_pool | 13,752 | svc_north=0.566, svc_south=0.565 | 8.0 | 922 | 960 | 0 | 0.0 |
| independent | 13,752 | svc_north=0.561, svc_south=0.569 | 8.0 | 922 | 960 | 0 | 3.4 |
| echelon_base_stock | 13,874 | svc_north=0.951, svc_south=0.166 | 8.0 | 921 | 960 | 14 | 0.4 |
| gated | 13,752 | svc_north=0.566, svc_south=0.565 | 8.0 | 922 | 960 | 0 | 4.4 |

### H_one_branch_demand_shock
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 12,101 | svc_north=0.948, svc_south=0.770 | 4.0 | 1694 | 1564 | 205 | 0.0 |
| central_pool | 12,101 | svc_north=0.948, svc_south=0.770 | 4.0 | 1694 | 1564 | 205 | 0.0 |
| independent | 10,206 | svc_north=0.987, svc_south=0.986 | 1.0 | 1967 | 1887 | 211 | 7.3 |
| echelon_base_stock | 11,991 | svc_north=0.992, svc_south=0.752 | 3.5 | 1710 | 1583 | 203 | 1.1 |
| gated | 10,417 | svc_north=0.963, svc_south=0.981 | 1.5 | 2180 | 2079 | 287 | 30.1 |

### I_shared_supplier_disruption
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,829 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1515 | 57 | 0.0 |
| central_pool | 8,829 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1515 | 57 | 0.0 |
| independent | 8,811 | svc_north=0.981, svc_south=0.983 | 1.0 | 1520 | 1521 | 60 | 1.7 |
| echelon_base_stock | 8,831 | svc_north=0.992, svc_south=0.969 | 1.5 | 1526 | 1519 | 61 | 0.9 |
| gated | 8,850 | svc_north=0.980, svc_south=0.977 | 1.5 | 1522 | 1513 | 56 | 0.8 |

### J_asymmetric_service_targets
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,786 | svc_north=0.997, svc_south=0.972 | 2.0 | 1546 | 1589 | 60 | 0.0 |
| central_pool | 8,786 | svc_north=0.997, svc_south=0.972 | 2.0 | 1546 | 1589 | 60 | 0.0 |
| independent | 8,835 | svc_north=0.997, svc_south=0.968 | 3.0 | 1538 | 1791 | 150 | 7.5 |
| echelon_base_stock | 8,760 | svc_north=0.997, svc_south=0.976 | 2.0 | 1552 | 1597 | 62 | 1.3 |
| gated | 8,879 | svc_north=0.988, svc_south=0.968 | 2.0 | 1541 | 1603 | 149 | 18.2 |

### K_unequal_demand_scale
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 15,252 | svc_north=0.985, svc_south=0.990 | 0.5 | 2726 | 2631 | 96 | 0.0 |
| central_pool | 15,252 | svc_north=0.985, svc_south=0.990 | 0.5 | 2726 | 2631 | 96 | 0.0 |
| independent | 15,509 | svc_north=0.972, svc_south=0.981 | 1.5 | 2681 | 2591 | 105 | 1.5 |
| echelon_base_stock | 15,408 | svc_north=0.992, svc_south=0.897 | 1.5 | 2703 | 2610 | 110 | 0.5 |
| gated | 15,348 | svc_north=0.980, svc_south=0.986 | 1.0 | 2712 | 2612 | 97 | 8.8 |

### L_already_efficient_network
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,736 | svc_north=0.977, svc_south=0.988 | 1.0 | 1329 | 1161 | 168 | 0.0 |
| central_pool | 8,736 | svc_north=0.977, svc_south=0.988 | 1.0 | 1329 | 1161 | 168 | 0.0 |
| independent | 8,718 | svc_north=0.984, svc_south=0.983 | 1.5 | 1541 | 1554 | 233 | 2.0 |
| echelon_base_stock | 8,706 | svc_north=0.992, svc_south=0.979 | 1.0 | 1337 | 1170 | 168 | 0.8 |
| gated | 8,746 | svc_north=0.977, svc_south=0.988 | 1.0 | 1340 | 1191 | 212 | 5.8 |

### M_transfer_not_reachable_in_time
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 13,807 | svc_north=0.576, svc_south=0.545 | 4.0 | 1652 | 1089 | 323 | 0.0 |
| central_pool | 13,807 | svc_north=0.576, svc_south=0.545 | 4.0 | 1652 | 1089 | 323 | 0.0 |
| independent | 13,865 | svc_north=0.576, svc_south=0.545 | 4.0 | 1698 | 1694 | 492 | 25.9 |
| echelon_base_stock | 13,808 | svc_north=0.576, svc_south=0.545 | 4.0 | 1655 | 1093 | 324 | 0.3 |
| gated | 13,810 | svc_north=0.576, svc_south=0.545 | 4.0 | 1637 | 1081 | 368 | 90.8 |

### N_pipeline_already_solves_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,421 | svc_north=0.919, svc_south=0.925 | 1.5 | 1129 | 957 | 215 | 0.0 |
| central_pool | 9,421 | svc_north=0.919, svc_south=0.925 | 1.5 | 1129 | 957 | 215 | 0.0 |
| independent | 9,407 | svc_north=0.924, svc_south=0.922 | 1.5 | 1143 | 1179 | 256 | 2.8 |
| echelon_base_stock | 9,379 | svc_north=0.926, svc_south=0.925 | 1.5 | 1139 | 968 | 214 | 0.6 |
| gated | 9,416 | svc_north=0.920, svc_south=0.925 | 1.5 | 1135 | 959 | 259 | 6.0 |

### O_multiple_transfer_options
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,920 | svc_north=0.978, svc_south=0.984 | 1.0 | 1385 | 1322 | 112 | 0.0 |
| central_pool | 9,920 | svc_north=0.978, svc_south=0.984 | 1.0 | 1385 | 1322 | 112 | 0.0 |
| independent | 8,634 | svc_north=0.995, svc_south=0.990 | 0.0 | 1623 | 2032 | 195 | 49.3 |
| echelon_base_stock | 9,923 | svc_north=0.992, svc_south=0.969 | 1.5 | 1386 | 1326 | 115 | 0.7 |
| gated | 8,575 | svc_north=0.994, svc_south=0.990 | 0.0 | 1635 | 1687 | 262 | 75.9 |

### P_transfer_capacity_limit
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,597 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1207 | 194 | 0.0 |
| central_pool | 11,597 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1207 | 194 | 0.0 |
| independent | 11,599 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1223 | 208 | 6.5 |
| echelon_base_stock | 11,598 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1210 | 197 | 0.1 |
| gated | 11,597 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1207 | 194 | 6.7 |

### Q_pack_constraint_on_transfer
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,248 | svc_north=0.965, svc_south=0.965 | 2.5 | 1476 | 1439 | 76 | 0.0 |
| central_pool | 9,248 | svc_north=0.965, svc_south=0.965 | 2.5 | 1476 | 1439 | 76 | 0.0 |
| independent | 8,815 | svc_north=0.993, svc_south=1.000 | 0.0 | 1848 | 2014 | 407 | 8.8 |
| echelon_base_stock | 9,189 | svc_north=0.973, svc_south=0.968 | 2.0 | 1500 | 1451 | 74 | 1.1 |
| gated | 8,754 | svc_north=1.000, svc_south=1.000 | 0.0 | 1812 | 1648 | 280 | 25.6 |

### R_order_transfer_interaction
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 23,990 | svc_north=0.989, svc_south=0.995 | 1.0 | 0 | 4045 | 344 | 0.0 |
| central_pool | 23,990 | svc_north=0.989, svc_south=0.995 | 1.0 | 0 | 4045 | 344 | 0.0 |
| independent | 23,236 | svc_north=0.991, svc_south=0.997 | 1.0 | 4194 | 5456 | 1135 | 11.7 |
| echelon_base_stock | 23,963 | svc_north=0.991, svc_south=0.996 | 0.5 | 0 | 4054 | 347 | 0.3 |
| gated | 22,728 | svc_north=0.998, svc_south=0.992 | 0.5 | 3935 | 5008 | 988 | 12.4 |

### S_recovery_after_imbalance
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,461 | svc_north=0.977, svc_south=0.872 | 2.5 | 1332 | 1165 | 166 | 0.0 |
| central_pool | 9,461 | svc_north=0.977, svc_south=0.871 | 2.0 | 1332 | 1165 | 166 | 0.0 |
| independent | 9,394 | svc_north=0.994, svc_south=0.868 | 1.5 | 1347 | 1401 | 327 | 3.2 |
| echelon_base_stock | 9,430 | svc_north=0.992, svc_south=0.862 | 2.0 | 1340 | 1174 | 166 | 0.7 |
| gated | 9,460 | svc_north=0.979, svc_south=0.872 | 2.5 | 1350 | 1197 | 254 | 5.6 |

### T_single_node_network_off
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 4,178 | svc_branch=0.990 | 0.5 | 0 | 771 | 22 | 0.0 |
| central_pool | 4,178 | svc_branch=0.990 | 0.5 | 0 | 771 | 22 | 0.0 |
| independent | 4,206 | svc_branch=0.986 | 0.5 | 0 | 768 | 20 | 0.5 |
| echelon_base_stock | 4,170 | svc_branch=0.992 | 0.5 | 0 | 774 | 24 | 0.1 |
| gated | 4,206 | svc_branch=0.986 | 0.5 | 0 | 768 | 20 | 0.5 |

## Network principles

| principle | pass | numbers |
|---|---|---|
| pooling_has_value | PASS | {'pooling_benefit_vs_independent': -0.0012} |
| pooling_benefit_shrinks | PASS | {'benefit_A': -0.0012, 'benefit_B': 0.0032} |
| correlated_demand_no_fabricated_diversification | PASS | {'protection_A': 151.7634, 'protection_B': 71.0259} |
| long_lead_positions_more_locally | PASS | {'branch_cover_C': 0.2131, 'branch_cover_D': 0.7475} |
| no_churn_at_high_transfer_cost | PASS | {'zaad_units': 1524.7049, 'incumbent_units': 1524.7049, 'demand': 1633.6456} |
| rebalance_before_purchase | PASS | {'zaad_early_purchases': 0, 'incumbent_early_purchases': 0, 'zaad_early_transfers': 391.1034} |
| principled_allocation_under_shortage | PASS | {'service': {'svc_north': 0.5660254014644304, 'svc_south': 0.5648309534634357}} |
| healthy_branch_not_starved | PASS | {'north': 0.9633, 'south': 0.9807, 'incumbent_north': 0.9476} |
| priority_branch_protected | PASS | {'north': 0.9877, 'south': 0.9678} |
| small_branch_not_starved | PASS | {'south': 0.9856} |
| already_efficient_abstains | PASS | {'abstained_share': 0.9375, 'cost_gap': 0.0011} |
| remote_stock_not_credited | PASS | {'service': {'svc_north': 0.5763728566728359, 'svc_south': 0.5454072445410698}, 'incumbent': {'svc_north': 0.5763728566728359, 'svc_south': 0.5454072445410698}} |
| no_over_transfer_when_pipeline_covers | PASS | {'zaad_units': 1134.5731, 'demand': 1633.6456} |
| cheap_lane_when_time_allows | PASS | {} |
| capacity_respected | PASS | {} |
| legal_packs | PASS | {} |
| recovery_without_ping_pong | PASS | {'south': 0.8715} |
| single_node_identity | PASS | {} |

## Runtime gate (ZAAD, every review of the final set)

| reviews | p50 s | p95 s | max s | gate p50 / p95 / max | required-candidate starvation | pass |
|---|---|---|---|---|---|---|
| 344 | 9.7 | 86.9 | 314.6 | 60 / 120 / 180 | 0 | FAIL |

Solve statuses over every ZAAD candidate: {'OPTIMAL': 1476, 'INFEASIBLE': 143, 'FEASIBLE_TIME_LIMIT': 19}. Reviews above the p95 gate: [('M_transfer_not_reachable_in_time', 41002, 7, 257, 'NETWORK_ALLOCATION'), ('O_multiple_transfer_options', 41001, 6, 315, 'CAPITAL_OPTIMIZATION')].
Sources: p2_authoritative for the sixteen untouched fixtures, p2_authoritative_c2 for ['D', 'M', 'O', 'Q'].
