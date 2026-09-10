# P2 benchmark tables (8 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| B_correlated_demand | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| C_short_transfer_lead | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| D_long_transfer_lead | VALID | independent | -0.16% | 2% | 0.979 | 0.978 | 1568 | 0.0/8 | 55/80/87 | PASS |
| E_high_transfer_cost | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| F_low_transfer_cost | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| G_central_supply_shortage | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| H_one_branch_demand_shock | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| I_shared_supplier_disruption | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| J_asymmetric_service_targets | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| K_unequal_demand_scale | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| L_already_efficient_network | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| M_transfer_not_reachable_in_time | VALID | central_pool | +0.01% | 2% | 0.545 | 0.545 | 1670 | 4.0/8 | 91/104/121 | PASS |
| N_pipeline_already_solves_shortage | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| O_multiple_transfer_options | VALID | independent | -0.55% | 2% | 0.990 | 0.978 | 1630 | 0.0/8 | 76/88/88 | PASS |
| P_transfer_capacity_limit | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| Q_pack_constraint_on_transfer | VALID | independent | -0.69% | 2% | 1.000 | 0.965 | 1812 | 0.0/8 | 25/57/86 | PASS |
| R_order_transfer_interaction | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| S_recovery_after_imbalance | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| T_single_node_network_off | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |

## Policies per fixture (cost, service per branch)

### A_independent_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### B_correlated_demand
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### C_short_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### D_long_transfer_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,734 | svc_north=0.978, svc_south=0.983 | 1.0 | 1559 | 1492 | 150 | 0.0 |
| central_pool | 8,734 | svc_north=0.978, svc_south=0.983 | 1.0 | 1559 | 1492 | 150 | 0.0 |
| independent | 8,713 | svc_north=0.990, svc_south=0.981 | 0.5 | 1730 | 1936 | 285 | 21.8 |
| echelon_base_stock | 8,757 | svc_north=0.987, svc_south=0.970 | 1.0 | 1564 | 1491 | 154 | 0.5 |
| gated | 8,699 | svc_north=0.979, svc_south=0.990 | 1.0 | 1568 | 1627 | 344 | 54.6 |

### E_high_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### F_low_transfer_cost
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### G_central_supply_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### H_one_branch_demand_shock
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### I_shared_supplier_disruption
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### J_asymmetric_service_targets
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### K_unequal_demand_scale
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### L_already_efficient_network
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### M_transfer_not_reachable_in_time
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 13,807 | svc_north=0.576, svc_south=0.545 | 4.0 | 1652 | 1089 | 323 | 0.0 |
| central_pool | 13,807 | svc_north=0.576, svc_south=0.545 | 4.0 | 1652 | 1089 | 323 | 0.0 |
| independent | 13,865 | svc_north=0.576, svc_south=0.545 | 4.0 | 1698 | 1694 | 492 | 25.9 |
| echelon_base_stock | 13,808 | svc_north=0.576, svc_south=0.545 | 4.0 | 1655 | 1093 | 324 | 0.3 |
| gated | 13,809 | svc_north=0.576, svc_south=0.545 | 4.0 | 1670 | 1092 | 377 | 91.1 |

### N_pipeline_already_solves_shortage
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### O_multiple_transfer_options
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,920 | svc_north=0.978, svc_south=0.984 | 1.0 | 1385 | 1322 | 112 | 0.0 |
| central_pool | 9,920 | svc_north=0.978, svc_south=0.984 | 1.0 | 1385 | 1322 | 112 | 0.0 |
| independent | 8,634 | svc_north=0.995, svc_south=0.990 | 0.0 | 1623 | 2032 | 195 | 49.7 |
| echelon_base_stock | 9,923 | svc_north=0.992, svc_south=0.969 | 1.5 | 1386 | 1326 | 115 | 0.8 |
| gated | 8,587 | svc_north=0.992, svc_south=0.990 | 0.0 | 1630 | 1680 | 268 | 76.4 |

### P_transfer_capacity_limit
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### Q_pack_constraint_on_transfer
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,248 | svc_north=0.965, svc_south=0.965 | 2.5 | 1476 | 1439 | 76 | 0.0 |
| central_pool | 9,248 | svc_north=0.965, svc_south=0.965 | 2.5 | 1476 | 1439 | 76 | 0.0 |
| independent | 8,815 | svc_north=0.993, svc_south=1.000 | 0.0 | 1848 | 2014 | 407 | 9.1 |
| echelon_base_stock | 9,189 | svc_north=0.973, svc_south=0.968 | 2.0 | 1500 | 1451 | 74 | 1.1 |
| gated | 8,754 | svc_north=1.000, svc_south=1.000 | 0.0 | 1812 | 1648 | 280 | 24.9 |

### R_order_transfer_interaction
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### S_recovery_after_imbalance
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

### T_single_node_network_off
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

## Network principles

| principle | pass | numbers |
|---|---|---|
| remote_stock_not_credited | PASS | {'service': {'svc_north': 0.5763728566728359, 'svc_south': 0.5454072445410698}, 'incumbent': {'svc_north': 0.5763728566728359, 'svc_south': 0.5454072445410698}} |
| cheap_lane_when_time_allows | PASS | {} |
| legal_packs | PASS | {} |
