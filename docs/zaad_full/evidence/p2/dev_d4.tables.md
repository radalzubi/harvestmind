# P2 benchmark tables (6 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| B_correlated_demand | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| C_short_transfer_lead | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| D_long_transfer_lead | INVALID: no competent baseline completed | - | +nan% | 0% | 0.974 | nan | 1265 | 0.0/6 | 10/18/20 | - |
| E_high_transfer_cost | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| F_low_transfer_cost | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| G_central_supply_shortage | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| H_one_branch_demand_shock | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| I_shared_supplier_disruption | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| J_asymmetric_service_targets | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| K_unequal_demand_scale | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| L_already_efficient_network | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| M_transfer_not_reachable_in_time | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| N_pipeline_already_solves_shortage | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| O_multiple_transfer_options | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| P_transfer_capacity_limit | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| Q_pack_constraint_on_transfer | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| R_order_transfer_interaction | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| S_recovery_after_imbalance | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |
| T_single_node_network_off | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/6 | 0/0/0 | - |

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
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | 6,472 | svc_north=0.996, svc_south=0.974 | 1.0 | 1265 | 1095 | 352 | 9.7 |

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
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

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
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

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
| network_rop | no run: [] | | | | | | |
| central_pool | no run: [] | | | | | | |
| independent | no run: [] | | | | | | |
| echelon_base_stock | no run: [] | | | | | | |
| gated | no run: [] | | | | | | |

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
