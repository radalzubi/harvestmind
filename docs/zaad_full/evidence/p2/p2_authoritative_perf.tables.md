# P2 benchmark tables (8 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | VALID | independent | +0.98% | 2% | 0.978 | 0.978 | 1541 | 6.5/8 | 0/0/1 | PASS |
| B_correlated_demand | VALID | independent | +0.07% | 2% | 0.984 | 0.984 | 1531 | 6.0/8 | 0/1/1 | PASS |
| C_short_transfer_lead | VALID | independent | +0.98% | 2% | 0.978 | 0.978 | 1541 | 6.5/8 | 0/0/1 | PASS |
| D_long_transfer_lead | VALID | independent | +0.05% | 2% | 0.989 | 0.978 | 1683 | 0.0/8 | 1/1/1 | PASS |
| E_high_transfer_cost | VALID | independent | +0.66% | 2% | 0.977 | 0.978 | 1525 | 7.5/8 | 0/1/1 | PASS |
| F_low_transfer_cost | VALID | echelon_base_stock | +0.53% | 2% | 0.981 | 0.977 | 1599 | 7.0/8 | 0/0/1 | PASS |
| G_central_supply_shortage | VALID | independent | +0.00% | 3% | 0.565 | 0.565 | 922 | 8.0/8 | 1/2/2 | PASS |
| H_one_branch_demand_shock | VALID | independent | +1.05% | 3% | 0.970 | 0.770 | 2342 | 2.5/8 | 1/1/1 | PASS |
| I_shared_supplier_disruption | VALID | independent | +0.40% | 5% | 0.976 | 0.978 | 1523 | 1.5/8 | 0/0/1 | PASS |
| J_asymmetric_service_targets | VALID | echelon_base_stock | +1.22% | 2% | 0.968 | 0.972 | 1542 | 4.0/8 | 0/0/1 | PASS |
| K_unequal_demand_scale | VALID | independent | +0.73% | 2% | 0.985 | 0.985 | 2725 | 4.5/8 | 0/1/1 | PASS |
| L_already_efficient_network | VALID | echelon_base_stock | +0.46% | 2% | 0.977 | 0.977 | 1340 | 7.5/8 | 0/0/1 | PASS |
| M_transfer_not_reachable_in_time | VALID | central_pool | -0.01% | 2% | 0.545 | 0.545 | 1681 | 4.0/8 | 1/1/1 | PASS |
| N_pipeline_already_solves_shortage | VALID | independent | +0.77% | 2% | 0.920 | 0.919 | 1135 | 7.5/8 | 0/1/1 | PASS |
| O_multiple_transfer_options | VALID | independent | -1.38% | 2% | 0.996 | 0.978 | 1783 | 0.0/8 | 1/1/1 | PASS |
| P_transfer_capacity_limit | VALID | network_rop | +0.00% | 3% | 0.740 | 0.740 | 1120 | 8.0/8 | 1/1/1 | PASS |
| Q_pack_constraint_on_transfer | VALID | independent | -0.12% | 2% | 1.000 | 0.965 | 1764 | 0.0/8 | 8/14/15 | PASS |
| R_order_transfer_interaction | VALID | independent | -3.02% | 2% | 0.985 | 0.989 | 4160 | 1.0/8 | 3/10/10 | PASS |
| S_recovery_after_imbalance | VALID | independent | +0.77% | 3% | 0.872 | 0.872 | 1344 | 7.5/8 | 0/0/1 | PASS |
| T_single_node_network_off | VALID | echelon_base_stock | +0.86% | 2% | 0.986 | 0.990 | 0 | 2.0/8 | 0/1/1 | PASS |

## Policies per fixture (cost, service per branch)

### A_independent_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,751 | svc_north=0.991, svc_south=0.988 | 0.5 | 1662 | 1998 | 196 | 0.4 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1527 | 1469 | 67 | 0.0 |
| gated | 8,836 | svc_north=0.983, svc_south=0.978 | 1.0 | 1541 | 1494 | 152 | 0.3 |

### B_correlated_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,641 | svc_north=0.995, svc_south=0.984 | 0.5 | 1530 | 1449 | 66 | 0.0 |
| central_pool | 8,641 | svc_north=0.995, svc_south=0.984 | 0.5 | 1530 | 1449 | 66 | 0.0 |
| independent | 8,630 | svc_north=0.995, svc_south=0.991 | 0.5 | 1542 | 1593 | 132 | 0.3 |
| echelon_base_stock | 8,714 | svc_north=1.000, svc_south=0.968 | 1.0 | 1514 | 1438 | 74 | 0.0 |
| gated | 8,636 | svc_north=0.997, svc_south=0.984 | 0.0 | 1531 | 1446 | 71 | 0.3 |

### C_short_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,751 | svc_north=0.991, svc_south=0.988 | 0.5 | 1662 | 1998 | 196 | 0.4 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1527 | 1469 | 67 | 0.0 |
| gated | 8,836 | svc_north=0.983, svc_south=0.978 | 1.0 | 1541 | 1494 | 152 | 0.3 |

### D_long_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,734 | svc_north=0.978, svc_south=0.983 | 1.0 | 1559 | 1492 | 150 | 0.0 |
| central_pool | 8,734 | svc_north=0.978, svc_south=0.983 | 1.0 | 1559 | 1492 | 150 | 0.0 |
| independent | 8,630 | svc_north=0.990, svc_south=0.994 | 0.5 | 1738 | 1984 | 275 | 1.0 |
| echelon_base_stock | 8,757 | svc_north=0.987, svc_south=0.970 | 1.0 | 1564 | 1491 | 154 | 0.0 |
| gated | 8,634 | svc_north=0.989, svc_south=0.990 | 0.0 | 1683 | 1615 | 296 | 0.5 |

### E_high_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,169 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 11,169 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 11,097 | svc_north=0.992, svc_south=0.990 | 0.5 | 2282 | 2031 | 163 | 0.4 |
| echelon_base_stock | 11,170 | svc_north=0.992, svc_south=0.969 | 1.5 | 1528 | 1469 | 67 | 0.0 |
| gated | 11,170 | svc_north=0.984, svc_south=0.977 | 1.0 | 1525 | 1465 | 63 | 0.3 |

### F_low_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,539 | svc_north=0.977, svc_south=0.988 | 1.0 | 1587 | 1222 | 113 | 0.0 |
| central_pool | 8,539 | svc_north=0.977, svc_south=0.988 | 1.0 | 1587 | 1222 | 113 | 0.0 |
| independent | 8,568 | svc_north=0.972, svc_south=0.982 | 1.5 | 1654 | 1380 | 183 | 0.3 |
| echelon_base_stock | 8,504 | svc_north=0.992, svc_south=0.978 | 1.0 | 1596 | 1231 | 113 | 0.0 |
| gated | 8,550 | svc_north=0.981, svc_south=0.983 | 1.0 | 1599 | 1251 | 156 | 0.3 |

### G_central_supply_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 13,752 | svc_north=0.566, svc_south=0.565 | 8.0 | 922 | 960 | 0 | 0.0 |
| central_pool | 13,752 | svc_north=0.566, svc_south=0.565 | 8.0 | 922 | 960 | 0 | 0.0 |
| independent | 13,752 | svc_north=0.561, svc_south=0.569 | 8.0 | 922 | 960 | 0 | 1.7 |
| echelon_base_stock | 13,874 | svc_north=0.951, svc_south=0.166 | 8.0 | 922 | 960 | 14 | 0.0 |
| gated | 13,752 | svc_north=0.566, svc_south=0.565 | 8.0 | 922 | 960 | 0 | 0.5 |

### H_one_branch_demand_shock
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 12,101 | svc_north=0.948, svc_south=0.770 | 4.0 | 1694 | 1564 | 205 | 0.0 |
| central_pool | 12,101 | svc_north=0.948, svc_south=0.770 | 4.0 | 1694 | 1564 | 205 | 0.0 |
| independent | 10,188 | svc_north=0.986, svc_south=0.986 | 1.0 | 2225 | 2055 | 217 | 0.4 |
| echelon_base_stock | 11,991 | svc_north=0.992, svc_south=0.752 | 3.5 | 1710 | 1583 | 203 | 0.0 |
| gated | 10,295 | svc_north=0.970, svc_south=0.991 | 1.5 | 2342 | 2097 | 268 | 0.8 |

### I_shared_supplier_disruption
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,829 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1515 | 57 | 0.0 |
| central_pool | 8,829 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1515 | 57 | 0.0 |
| independent | 8,813 | svc_north=0.986, svc_south=0.978 | 1.0 | 1518 | 1522 | 60 | 0.4 |
| echelon_base_stock | 8,831 | svc_north=0.992, svc_south=0.969 | 1.5 | 1527 | 1519 | 61 | 0.0 |
| gated | 8,849 | svc_north=0.976, svc_south=0.982 | 1.0 | 1523 | 1512 | 57 | 0.2 |

### J_asymmetric_service_targets
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,786 | svc_north=0.997, svc_south=0.972 | 2.0 | 1546 | 1589 | 60 | 0.0 |
| central_pool | 8,786 | svc_north=0.997, svc_south=0.972 | 2.0 | 1546 | 1589 | 60 | 0.0 |
| independent | 8,925 | svc_north=0.997, svc_south=0.948 | 3.5 | 1500 | 1721 | 111 | 0.6 |
| echelon_base_stock | 8,760 | svc_north=0.997, svc_south=0.976 | 2.0 | 1552 | 1597 | 62 | 0.0 |
| gated | 8,868 | svc_north=0.990, svc_south=0.968 | 2.0 | 1542 | 1604 | 149 | 0.4 |

### K_unequal_demand_scale
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 15,252 | svc_north=0.985, svc_south=0.990 | 0.5 | 2726 | 2631 | 96 | 0.0 |
| central_pool | 15,252 | svc_north=0.985, svc_south=0.990 | 0.5 | 2726 | 2631 | 96 | 0.0 |
| independent | 15,142 | svc_north=0.993, svc_south=0.983 | 0.0 | 2776 | 2665 | 93 | 0.3 |
| echelon_base_stock | 15,408 | svc_north=0.992, svc_south=0.897 | 1.5 | 2703 | 2610 | 110 | 0.0 |
| gated | 15,253 | svc_north=0.985, svc_south=0.989 | 0.5 | 2725 | 2625 | 95 | 0.3 |

### L_already_efficient_network
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,736 | svc_north=0.977, svc_south=0.988 | 1.0 | 1329 | 1161 | 168 | 0.0 |
| central_pool | 8,736 | svc_north=0.977, svc_south=0.988 | 1.0 | 1329 | 1161 | 168 | 0.0 |
| independent | 8,717 | svc_north=0.981, svc_south=0.983 | 1.0 | 1767 | 1494 | 207 | 0.3 |
| echelon_base_stock | 8,706 | svc_north=0.992, svc_south=0.979 | 1.0 | 1337 | 1170 | 168 | 0.0 |
| gated | 8,746 | svc_north=0.977, svc_south=0.988 | 1.0 | 1340 | 1191 | 212 | 0.3 |

### M_transfer_not_reachable_in_time
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 13,807 | svc_north=0.576, svc_south=0.545 | 4.0 | 1652 | 1089 | 323 | 0.0 |
| central_pool | 13,807 | svc_north=0.576, svc_south=0.545 | 4.0 | 1652 | 1089 | 323 | 0.0 |
| independent | 13,863 | svc_north=0.576, svc_south=0.545 | 4.0 | 1763 | 1688 | 455 | 1.1 |
| echelon_base_stock | 13,808 | svc_north=0.576, svc_south=0.545 | 4.0 | 1656 | 1093 | 324 | 0.0 |
| gated | 13,806 | svc_north=0.576, svc_south=0.545 | 4.0 | 1681 | 1092 | 342 | 0.7 |

### N_pipeline_already_solves_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,421 | svc_north=0.919, svc_south=0.925 | 1.5 | 1129 | 957 | 215 | 0.0 |
| central_pool | 9,421 | svc_north=0.919, svc_south=0.925 | 1.5 | 1129 | 957 | 215 | 0.0 |
| independent | 9,344 | svc_north=0.929, svc_south=0.929 | 1.0 | 1155 | 1234 | 261 | 0.3 |
| echelon_base_stock | 9,379 | svc_north=0.926, svc_south=0.925 | 1.5 | 1139 | 968 | 214 | 0.0 |
| gated | 9,416 | svc_north=0.920, svc_south=0.925 | 1.5 | 1135 | 959 | 259 | 0.3 |

### O_multiple_transfer_options
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,920 | svc_north=0.978, svc_south=0.984 | 1.0 | 1385 | 1322 | 112 | 0.0 |
| central_pool | 9,920 | svc_north=0.978, svc_south=0.984 | 1.0 | 1385 | 1322 | 112 | 0.0 |
| independent | 8,641 | svc_north=0.993, svc_south=0.992 | 0.5 | 1654 | 2032 | 191 | 0.9 |
| echelon_base_stock | 9,925 | svc_north=0.992, svc_south=0.969 | 1.5 | 1388 | 1326 | 114 | 0.0 |
| gated | 8,522 | svc_north=0.996, svc_south=0.997 | 0.0 | 1783 | 1689 | 229 | 0.7 |

### P_transfer_capacity_limit
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,597 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1207 | 194 | 0.0 |
| central_pool | 11,597 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1207 | 194 | 0.0 |
| independent | 11,599 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1223 | 208 | 1.7 |
| echelon_base_stock | 11,598 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1210 | 197 | 0.1 |
| gated | 11,597 | svc_north=0.754, svc_south=0.740 | 6.5 | 1120 | 1207 | 194 | 0.9 |

### Q_pack_constraint_on_transfer
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,248 | svc_north=0.965, svc_south=0.965 | 2.5 | 1476 | 1439 | 76 | 0.0 |
| central_pool | 9,248 | svc_north=0.965, svc_south=0.965 | 2.5 | 1476 | 1439 | 76 | 0.0 |
| independent | 8,767 | svc_north=0.993, svc_south=1.000 | 0.0 | 1740 | 1804 | 412 | 3.5 |
| echelon_base_stock | 9,189 | svc_north=0.973, svc_south=0.968 | 2.0 | 1500 | 1451 | 74 | 0.0 |
| gated | 8,757 | svc_north=1.000, svc_south=1.000 | 0.0 | 1764 | 1778 | 320 | 7.7 |

### R_order_transfer_interaction
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 23,990 | svc_north=0.989, svc_south=0.995 | 1.0 | 0 | 4045 | 344 | 0.0 |
| central_pool | 23,990 | svc_north=0.989, svc_south=0.995 | 1.0 | 0 | 4045 | 344 | 0.0 |
| independent | 23,354 | svc_north=0.979, svc_south=0.996 | 1.5 | 4096 | 5409 | 1115 | 2.5 |
| echelon_base_stock | 23,963 | svc_north=0.991, svc_south=0.996 | 0.5 | 0 | 4054 | 347 | 0.0 |
| gated | 22,649 | svc_north=0.985, svc_south=0.990 | 1.0 | 4160 | 4146 | 967 | 3.1 |

### S_recovery_after_imbalance
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,461 | svc_north=0.977, svc_south=0.872 | 2.5 | 1332 | 1165 | 166 | 0.0 |
| central_pool | 9,461 | svc_north=0.977, svc_south=0.871 | 2.0 | 1332 | 1165 | 166 | 0.0 |
| independent | 9,399 | svc_north=0.989, svc_south=0.871 | 2.0 | 1571 | 1634 | 304 | 0.3 |
| echelon_base_stock | 9,430 | svc_north=0.992, svc_south=0.862 | 2.0 | 1340 | 1174 | 166 | 0.0 |
| gated | 9,471 | svc_north=0.977, svc_south=0.872 | 2.5 | 1344 | 1195 | 210 | 0.3 |

### T_single_node_network_off
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 4,178 | svc_branch=0.990 | 0.5 | 0 | 771 | 22 | 0.0 |
| central_pool | 4,178 | svc_branch=0.990 | 0.5 | 0 | 771 | 22 | 0.0 |
| independent | 4,206 | svc_branch=0.986 | 0.5 | 0 | 768 | 20 | 0.5 |
| echelon_base_stock | 4,170 | svc_branch=0.992 | 0.5 | 0 | 774 | 24 | 0.1 |
| gated | 4,206 | svc_branch=0.986 | 0.5 | 0 | 768 | 20 | 0.4 |

## Network principles

| principle | pass | numbers |
|---|---|---|
| pooling_has_value | PASS | {'pooling_benefit_vs_independent': -0.0098} |
| pooling_benefit_shrinks | PASS | {'benefit_A': -0.0098, 'benefit_B': -0.0007} |
| correlated_demand_no_fabricated_diversification | PASS | {'protection_A': 151.7634, 'protection_B': 71.0259} |
| long_lead_positions_more_locally | PASS | {'branch_cover_C': 0.2178, 'branch_cover_D': 0.7001} |
| no_churn_at_high_transfer_cost | PASS | {'zaad_units': 1524.7049, 'incumbent_units': 1524.7049, 'demand': 1633.6456} |
| rebalance_before_purchase | PASS | {'zaad_early_purchases': 0, 'incumbent_early_purchases': 0, 'zaad_early_transfers': 391.1034} |
| principled_allocation_under_shortage | PASS | {'service': {'svc_north': 0.5660254014644304, 'svc_south': 0.5648309534634357}} |
| healthy_branch_not_starved | PASS | {'north': 0.9696, 'south': 0.9907, 'incumbent_north': 0.9476} |
| priority_branch_protected | PASS | {'north': 0.9896, 'south': 0.9678} |
| small_branch_not_starved | PASS | {'south': 0.9891} |
| already_efficient_abstains | PASS | {'abstained_share': 0.9375, 'cost_gap': 0.0011} |
| remote_stock_not_credited | PASS | {'service': {'svc_north': 0.5763728566728359, 'svc_south': 0.5454072445410698}, 'incumbent': {'svc_north': 0.5763728566728359, 'svc_south': 0.5454072445410698}} |
| no_over_transfer_when_pipeline_covers | PASS | {'zaad_units': 1134.5731, 'demand': 1633.6456} |
| cheap_lane_when_time_allows | PASS | {} |
| capacity_respected | PASS | {} |
| legal_packs | PASS | {} |
| recovery_without_ping_pong | PASS | {'south': 0.8715} |
| single_node_identity | PASS | {} |
