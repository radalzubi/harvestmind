# P2 benchmark tables (8 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| A_independent_demand | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| B_correlated_demand | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| C_short_transfer_lead | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| D_long_transfer_lead | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| E_high_transfer_cost | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| F_low_transfer_cost | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| G_central_supply_shortage | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| H_one_branch_demand_shock | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| I_shared_supplier_disruption | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| J_asymmetric_service_targets | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| K_unequal_demand_scale | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| L_already_efficient_network | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| M_transfer_not_reachable_in_time | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| N_pipeline_already_solves_shortage | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| O_multiple_transfer_options | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| P_transfer_capacity_limit | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| Q_pack_constraint_on_transfer | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| R_order_transfer_interaction | VALID | independent | -3.02% | 2% | 0.985 | 0.989 | 4160 | 1.0/8 | 3/9/11 | PASS |
| S_recovery_after_imbalance | INVALID: ZAAD run incomplete | - | +nan% | 0% | nan | nan | 0 | 0.0/8 | 0/0/0 | - |
| T_single_node_network_off | VALID | echelon_base_stock | +0.86% | 2% | 0.986 | 0.990 | 0 | 2.0/8 | 0/1/1 | PASS |

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
| gated | no run: [] | | | | | | |

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
| network_rop | 23,990 | svc_north=0.989, svc_south=0.995 | 1.0 | 0 | 4045 | 344 | 0.0 |
| central_pool | 23,990 | svc_north=0.989, svc_south=0.995 | 1.0 | 0 | 4045 | 344 | 0.0 |
| independent | 23,354 | svc_north=0.979, svc_south=0.996 | 1.5 | 4096 | 5409 | 1115 | 2.4 |
| echelon_base_stock | 23,963 | svc_north=0.991, svc_south=0.996 | 0.5 | 0 | 4054 | 347 | 0.0 |
| gated | 22,649 | svc_north=0.985, svc_south=0.990 | 1.0 | 4160 | 4146 | 967 | 3.1 |

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
| network_rop | 4,178 | svc_branch=0.990 | 0.5 | 0 | 771 | 22 | 0.0 |
| central_pool | 4,178 | svc_branch=0.990 | 0.5 | 0 | 771 | 22 | 0.0 |
| independent | 4,206 | svc_branch=0.986 | 0.5 | 0 | 768 | 20 | 0.4 |
| echelon_base_stock | 4,170 | svc_branch=0.992 | 0.5 | 0 | 774 | 24 | 0.1 |
| gated | 4,206 | svc_branch=0.986 | 0.5 | 0 | 768 | 20 | 0.4 |

## Network principles

| principle | pass | numbers |
|---|---|---|
| single_node_identity | PASS | {} |
