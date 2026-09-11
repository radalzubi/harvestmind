# P2 benchmark tables (8 rolling reviews, P2 continuation basis, mean over seeds)

| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| C1_case_pack_rounding | VALID | independent | +1.07% | 2% | 0.983 | 0.983 | 1548 | 6.5/8 | 11/51/61 | PASS |
| C2_pallet_load_threshold | VALID | independent | -0.07% | 2% | 0.988 | 0.978 | 1563 | 5.0/8 | 4/6/13 | PASS |
| C3_moq_mov_economics | VALID | independent | -0.53% | 2% | 1.000 | 0.992 | 1695 | 0.5/8 | 4/7/10 | PASS |
| C4_long_import_lead | VALID | network_rop | +0.02% | 2% | 0.980 | 0.975 | 1318 | 3.5/8 | 1/1/1 | PASS |
| C5_variable_supplier_arrival | VALID | independent | +2.11% | 3% | 0.773 | 0.773 | 1284 | 8.0/8 | 1/1/3 | PASS |
| C6_storage_capacity | VALID | independent | +0.38% | 2% | 0.978 | 0.978 | 1525 | 7.5/8 | 1/1/1 | PASS |
| C7_no_material_improvement | VALID | echelon_base_stock | +0.11% | 2% | 0.985 | 0.984 | 1414 | 7.5/8 | 1/1/1 | PASS |
| P1_fresh_no_unnecessary_purchase | VALID | independent | +0.88% | 2% | 0.981 | 0.977 | 1325 | 6.0/8 | 3/6/7 | PASS |
| P2_near_expiry_inventory | VALID | independent | +0.67% | 3% | 0.981 | 0.924 | 1637 | 5.5/8 | 4/9/14 | PASS |
| P3_age_at_receipt | VALID | independent | +0.33% | 3% | 0.982 | 0.992 | 1477 | 0.0/8 | 3/5/6 | PASS |
| P4_transfer_becomes_useless | VALID | independent | -0.19% | 3% | 0.983 | 0.795 | 765 | 0.5/8 | 5/15/30 | PASS |
| P5_spoilage_vs_service | VALID | independent | +1.27% | 3% | 0.962 | 0.963 | 1613 | 5.5/8 | 1/2/2 | PASS |
| P6_uncertain_usable_yield | VALID | echelon_base_stock | +0.02% | 3% | 0.944 | 0.945 | 1582 | 3.5/8 | 11/19/24 | PASS |
| P7_fefo_settlement | VALID | network_rop | +0.00% | 3% | 0.978 | 0.978 | 1525 | 7.5/8 | 3/4/5 | PASS |
| P8_no_material_improvement | VALID | echelon_base_stock | +0.09% | 2% | 0.986 | 0.983 | 1374 | 7.5/8 | 2/4/7 | PASS |
| M1_chilled_shelf_life | VALID | independent | +0.22% | 3% | 0.961 | 0.875 | 1647 | 3.0/8 | 1/1/1 | PASS |
| M2_frozen_shelf_life | VALID | independent | +0.98% | 2% | 0.978 | 0.978 | 1541 | 6.5/8 | 0/1/1 | PASS |
| M3_storage_state_infeasibility | VALID | network_rop | +0.00% | 3% | 0.000 | 0.000 | 759 | 8.0/8 | 0/0/1 | PASS |
| M4_cold_chain_lane | VALID | network_rop | -0.01% | 3% | 0.978 | 0.978 | 1525 | 7.5/8 | 2/4/4 | PASS |
| M5_aging_vs_service | VALID | independent | +2.51% | 3% | 0.962 | 0.975 | 1612 | 4.0/8 | 1/2/2 | PASS |
| M6_transfer_usable_lot | VALID | independent | +1.32% | 3% | 0.882 | 0.864 | 1586 | 7.0/8 | 1/2/3 | PASS |
| M7_transfer_rejected_by_expiry | VALID | independent | -0.41% | 3% | 0.775 | 0.711 | 1439 | 5.5/8 | 1/3/3 | PASS |
| M8_no_material_improvement | VALID | echelon_base_stock | +0.11% | 2% | 0.985 | 0.984 | 1414 | 7.5/8 | 0/1/1 | PASS |
| X1_commercial_plus_produce | VALID | independent | -0.05% | 3% | 0.978 | 0.970 | 3064 | 7.0/8 | 2/3/4 | PASS |
| X2_produce_plus_frozen_seafood | VALID | echelon_base_stock | +0.24% | 3% | 0.956 | 0.956 | 3044 | 8.0/8 | 2/3/4 | PASS |
| X3_three_sectors | VALID | independent | +0.38% | 3% | 0.000 | 0.000 | 3780 | 8.0/8 | 2/3/4 | PASS |

## Policies per fixture (cost, service per branch)

### C1_case_pack_rounding
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,775 | svc_north=0.983, svc_south=0.987 | 0.5 | 1538 | 1476 | 65 | 0.0 |
| central_pool | 8,775 | svc_north=0.983, svc_south=0.987 | 0.5 | 1538 | 1476 | 65 | 0.0 |
| independent | 8,702 | svc_north=1.000, svc_south=0.988 | 0.0 | 1688 | 1890 | 232 | 9.3 |
| echelon_base_stock | 8,818 | svc_north=0.991, svc_south=0.971 | 1.5 | 1532 | 1476 | 69 | 0.0 |
| gated | 8,795 | svc_north=0.983, svc_south=0.987 | 0.5 | 1548 | 1572 | 169 | 10.5 |

### C2_pallet_load_threshold
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,252 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 9,252 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 9,072 | svc_north=1.000, svc_south=0.993 | 0.0 | 1613 | 2129 | 376 | 5.3 |
| echelon_base_stock | 9,252 | svc_north=0.992, svc_south=0.969 | 1.5 | 1528 | 1469 | 67 | 0.0 |
| gated | 9,065 | svc_north=1.000, svc_south=0.988 | 0.5 | 1563 | 1635 | 233 | 4.1 |

### C3_moq_mov_economics
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,968 | svc_north=0.992, svc_south=0.993 | 0.5 | 1560 | 2591 | 614 | 0.0 |
| central_pool | 8,968 | svc_north=0.992, svc_south=0.993 | 0.5 | 1560 | 2591 | 614 | 0.0 |
| independent | 8,820 | svc_north=1.000, svc_south=1.000 | 0.0 | 2022 | 2497 | 941 | 3.5 |
| echelon_base_stock | 9,450 | svc_north=0.992, svc_south=0.890 | 3.0 | 1420 | 1440 | 154 | 0.0 |
| gated | 8,773 | svc_north=1.000, svc_south=1.000 | 0.0 | 1695 | 1979 | 598 | 4.1 |

### C4_long_import_lead
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,763 | svc_north=0.975, svc_south=0.992 | 0.5 | 1326 | 1699 | 300 | 0.0 |
| central_pool | 8,763 | svc_north=0.975, svc_south=0.992 | 0.5 | 1326 | 1699 | 300 | 0.0 |
| independent | 8,813 | svc_north=0.983, svc_south=0.980 | 1.0 | 1370 | 2190 | 326 | 0.3 |
| echelon_base_stock | 8,830 | svc_north=0.992, svc_south=0.964 | 1.0 | 1331 | 1695 | 304 | 0.0 |
| gated | 8,765 | svc_north=0.980, svc_south=0.987 | 0.5 | 1318 | 1704 | 297 | 0.6 |

### C5_variable_supplier_arrival
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,408 | svc_north=0.773, svc_south=0.773 | 3.5 | 1284 | 1453 | 80 | 0.0 |
| central_pool | 11,408 | svc_north=0.773, svc_south=0.773 | 3.5 | 1284 | 1453 | 80 | 0.0 |
| independent | 11,172 | svc_north=0.787, svc_south=0.795 | 4.0 | 1287 | 1448 | 85 | 0.7 |
| echelon_base_stock | 11,393 | svc_north=0.811, svc_south=0.741 | 4.0 | 1230 | 1256 | 65 | 0.0 |
| gated | 11,408 | svc_north=0.773, svc_south=0.773 | 3.5 | 1284 | 1453 | 80 | 1.0 |

### C6_storage_capacity
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,793 | svc_north=0.990, svc_south=0.978 | 1.0 | 1516 | 1519 | 112 | 0.7 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1528 | 1469 | 67 | 0.0 |
| gated | 8,827 | svc_north=0.983, svc_south=0.978 | 1.0 | 1525 | 1465 | 63 | 0.5 |

### C7_no_material_improvement
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,676 | svc_north=0.984, svc_south=0.988 | 1.0 | 1414 | 1348 | 89 | 0.0 |
| central_pool | 8,676 | svc_north=0.984, svc_south=0.988 | 1.0 | 1414 | 1348 | 89 | 0.0 |
| independent | 8,702 | svc_north=0.983, svc_south=0.979 | 1.0 | 1609 | 1495 | 141 | 0.5 |
| echelon_base_stock | 8,667 | svc_north=0.995, svc_south=0.979 | 0.5 | 1417 | 1354 | 91 | 0.0 |
| gated | 8,676 | svc_north=0.986, svc_south=0.985 | 1.0 | 1414 | 1348 | 89 | 0.5 |

### P1_fresh_no_unnecessary_purchase
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,736 | svc_north=0.977, svc_south=0.988 | 1.0 | 1329 | 1161 | 168 | 0.0 |
| central_pool | 8,736 | svc_north=0.977, svc_south=0.988 | 1.0 | 1329 | 1161 | 168 | 0.0 |
| independent | 8,682 | svc_north=0.983, svc_south=0.994 | 1.0 | 1324 | 1171 | 194 | 1.8 |
| echelon_base_stock | 8,706 | svc_north=0.992, svc_south=0.979 | 1.0 | 1337 | 1170 | 168 | 0.5 |
| gated | 8,759 | svc_north=0.981, svc_south=0.981 | 1.5 | 1325 | 1158 | 168 | 3.1 |

### P2_near_expiry_inventory
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 10,012 | svc_north=0.936, svc_south=0.924 | 3.0 | 1553 | 1494 | 67 | 0.0 |
| central_pool | 10,012 | svc_north=0.936, svc_south=0.924 | 3.0 | 1553 | 1494 | 67 | 0.0 |
| independent | 9,338 | svc_north=0.992, svc_south=0.984 | 0.5 | 1634 | 1613 | 164 | 2.2 |
| echelon_base_stock | 10,786 | svc_north=0.906, svc_south=0.822 | 4.0 | 1446 | 1387 | 97 | 0.4 |
| gated | 9,401 | svc_north=0.982, svc_south=0.981 | 1.0 | 1637 | 1579 | 61 | 4.5 |

### P3_age_at_receipt
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,049 | svc_north=0.992, svc_south=0.992 | 0.5 | 0 | 1645 | 110 | 0.0 |
| central_pool | 11,049 | svc_north=0.992, svc_south=0.992 | 0.5 | 0 | 1645 | 110 | 0.0 |
| independent | 9,170 | svc_north=0.980, svc_south=0.984 | 1.0 | 1420 | 1635 | 37 | 12.9 |
| echelon_base_stock | 9,943 | svc_north=0.989, svc_south=0.989 | 0.5 | 200 | 1448 | 65 | 0.2 |
| gated | 9,200 | svc_north=0.986, svc_south=0.982 | 1.0 | 1477 | 1649 | 41 | 3.5 |

### P4_transfer_becomes_useless
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 11,163 | svc_north=0.795, svc_south=0.993 | 2.5 | 719 | 1385 | 122 | 0.0 |
| central_pool | 11,163 | svc_north=0.795, svc_south=0.993 | 2.5 | 719 | 1385 | 122 | 0.0 |
| independent | 10,107 | svc_north=0.977, svc_south=0.988 | 1.0 | 755 | 1527 | 139 | 3.3 |
| echelon_base_stock | 11,752 | svc_north=0.696, svc_south=0.994 | 4.0 | 638 | 1309 | 135 | 0.1 |
| gated | 10,088 | svc_north=0.987, svc_south=0.983 | 1.0 | 765 | 1536 | 165 | 4.6 |

### P5_spoilage_vs_service
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,211 | svc_north=0.963, svc_south=0.968 | 2.0 | 1617 | 1619 | 70 | 0.0 |
| central_pool | 9,211 | svc_north=0.963, svc_south=0.968 | 2.0 | 1617 | 1619 | 70 | 0.0 |
| independent | 9,122 | svc_north=0.980, svc_south=0.967 | 1.5 | 1627 | 1642 | 75 | 1.4 |
| echelon_base_stock | 9,254 | svc_north=0.984, svc_south=0.941 | 2.0 | 1614 | 1618 | 75 | 0.0 |
| gated | 9,238 | svc_north=0.962, svc_south=0.964 | 2.0 | 1613 | 1616 | 68 | 1.3 |

### P6_uncertain_usable_yield
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 10,308 | svc_north=0.945, svc_south=0.949 | 2.0 | 1462 | 1618 | 59 | 0.0 |
| central_pool | 10,308 | svc_north=0.945, svc_south=0.949 | 2.0 | 1462 | 1618 | 59 | 0.0 |
| independent | 10,264 | svc_north=0.951, svc_south=0.939 | 3.0 | 1461 | 1773 | 170 | 4.2 |
| echelon_base_stock | 10,235 | svc_north=0.971, svc_south=0.937 | 3.0 | 1497 | 1680 | 78 | 0.3 |
| gated | 10,237 | svc_north=0.944, svc_south=0.952 | 2.0 | 1582 | 1776 | 132 | 10.6 |

### P7_fefo_settlement
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,827 | svc_north=0.987, svc_south=0.978 | 1.0 | 1507 | 1461 | 126 | 3.0 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1528 | 1469 | 67 | 0.5 |
| gated | 8,827 | svc_north=0.983, svc_south=0.978 | 1.0 | 1525 | 1465 | 63 | 2.7 |

### P8_no_material_improvement
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,659 | svc_north=0.983, svc_south=0.989 | 1.0 | 1374 | 1257 | 117 | 0.0 |
| central_pool | 8,659 | svc_north=0.983, svc_south=0.989 | 1.0 | 1374 | 1257 | 117 | 0.0 |
| independent | 8,837 | svc_north=0.968, svc_south=0.971 | 2.0 | 1338 | 1218 | 135 | 1.9 |
| echelon_base_stock | 8,651 | svc_north=0.995, svc_south=0.979 | 0.5 | 1380 | 1262 | 119 | 0.4 |
| gated | 8,659 | svc_north=0.986, svc_south=0.986 | 1.0 | 1374 | 1257 | 117 | 2.4 |

### M1_chilled_shelf_life
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 10,811 | svc_north=0.875, svc_south=0.920 | 3.5 | 1599 | 1630 | 51 | 0.0 |
| central_pool | 10,811 | svc_north=0.875, svc_south=0.920 | 3.5 | 1599 | 1630 | 51 | 0.0 |
| independent | 9,837 | svc_north=0.956, svc_south=0.960 | 3.0 | 1613 | 1653 | 46 | 0.5 |
| echelon_base_stock | 13,354 | svc_north=0.734, svc_south=0.786 | 6.0 | 1496 | 1508 | 88 | 0.0 |
| gated | 9,858 | svc_north=0.972, svc_south=0.961 | 2.5 | 1647 | 1699 | 51 | 0.8 |

### M2_frozen_shelf_life
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 8,826 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 8,751 | svc_north=0.991, svc_south=0.988 | 0.5 | 1662 | 1998 | 196 | 0.4 |
| echelon_base_stock | 8,828 | svc_north=0.992, svc_south=0.969 | 1.5 | 1527 | 1469 | 67 | 0.0 |
| gated | 8,836 | svc_north=0.983, svc_south=0.978 | 1.0 | 1541 | 1494 | 152 | 0.4 |

### M3_storage_state_infeasibility
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 14,597 | svc_north=0.991, svc_south=0.000 | 8.0 | 759 | 572 | 77 | 0.0 |
| central_pool | 14,597 | svc_north=0.991, svc_south=0.000 | 8.0 | 759 | 572 | 77 | 0.0 |
| independent | 14,639 | svc_north=0.991, svc_south=0.000 | 8.0 | 760 | 958 | 238 | 0.4 |
| echelon_base_stock | 14,631 | svc_north=0.992, svc_south=0.000 | 8.0 | 759 | 904 | 332 | 0.0 |
| gated | 14,597 | svc_north=0.991, svc_south=0.000 | 8.0 | 759 | 572 | 77 | 0.4 |

### M4_cold_chain_lane
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,139 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| central_pool | 9,139 | svc_north=0.978, svc_south=0.983 | 1.0 | 1525 | 1464 | 64 | 0.0 |
| independent | 9,167 | svc_north=0.996, svc_south=0.974 | 0.5 | 1654 | 1658 | 146 | 2.5 |
| echelon_base_stock | 9,248 | svc_north=0.992, svc_south=0.948 | 1.5 | 1497 | 1456 | 74 | 0.4 |
| gated | 9,138 | svc_north=0.983, svc_south=0.978 | 1.0 | 1525 | 1465 | 63 | 1.9 |

### M5_aging_vs_service
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,987 | svc_north=0.975, svc_south=0.982 | 1.5 | 1636 | 1636 | 67 | 0.0 |
| central_pool | 8,987 | svc_north=0.975, svc_south=0.982 | 1.5 | 1636 | 1636 | 67 | 0.0 |
| independent | 8,878 | svc_north=0.983, svc_south=0.992 | 1.0 | 1657 | 1661 | 78 | 0.8 |
| echelon_base_stock | 9,071 | svc_north=0.990, svc_south=0.955 | 2.0 | 1621 | 1621 | 70 | 0.0 |
| gated | 9,101 | svc_north=0.978, svc_south=0.962 | 2.0 | 1612 | 1612 | 63 | 0.9 |

### M6_transfer_usable_lot
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 9,648 | svc_north=0.864, svc_south=0.983 | 2.5 | 1586 | 1526 | 60 | 0.0 |
| central_pool | 9,648 | svc_north=0.864, svc_south=0.983 | 2.5 | 1586 | 1526 | 60 | 0.0 |
| independent | 9,395 | svc_north=0.882, svc_south=0.988 | 2.0 | 1563 | 1518 | 93 | 1.1 |
| echelon_base_stock | 9,423 | svc_north=0.898, svc_south=0.969 | 2.5 | 1586 | 1527 | 61 | 0.3 |
| gated | 9,519 | svc_north=0.882, svc_south=0.978 | 2.0 | 1586 | 1526 | 58 | 1.5 |

### M7_transfer_rejected_by_expiry
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 12,872 | svc_north=0.711, svc_south=0.829 | 4.5 | 1312 | 1554 | 122 | 0.0 |
| central_pool | 12,872 | svc_north=0.711, svc_south=0.829 | 4.5 | 1312 | 1554 | 122 | 0.0 |
| independent | 11,998 | svc_north=0.765, svc_south=0.923 | 3.5 | 1423 | 1674 | 129 | 1.2 |
| echelon_base_stock | 13,940 | svc_north=0.570, svc_south=0.785 | 5.0 | 1164 | 1401 | 144 | 0.2 |
| gated | 11,948 | svc_north=0.775, svc_south=0.921 | 3.0 | 1439 | 1682 | 100 | 1.3 |

### M8_no_material_improvement
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 8,676 | svc_north=0.984, svc_south=0.988 | 1.0 | 1414 | 1348 | 89 | 0.0 |
| central_pool | 8,676 | svc_north=0.984, svc_south=0.988 | 1.0 | 1414 | 1348 | 89 | 0.0 |
| independent | 8,702 | svc_north=0.983, svc_south=0.979 | 1.0 | 1609 | 1495 | 141 | 0.3 |
| echelon_base_stock | 8,667 | svc_north=0.995, svc_south=0.979 | 0.5 | 1417 | 1354 | 91 | 0.0 |
| gated | 8,676 | svc_north=0.986, svc_south=0.985 | 1.0 | 1414 | 1348 | 89 | 0.4 |

### X1_commercial_plus_produce
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 14,193 | svc_north=0.981, svc_north_B=0.970, svc_south=0.983, svc_south_B=0.985 | 1.0 | 3046 | 2911 | 132 | 0.0 |
| central_pool | 14,193 | svc_north=0.981, svc_north_B=0.970, svc_south=0.983, svc_south_B=0.985 | 1.0 | 3046 | 2911 | 132 | 0.0 |
| independent | 14,118 | svc_north=0.989, svc_north_B=0.984, svc_south=0.978, svc_south_B=0.988 | 0.5 | 3043 | 2919 | 185 | 1.9 |
| echelon_base_stock | 14,299 | svc_north=0.992, svc_north_B=0.979, svc_south=0.970, svc_south_B=0.955 | 1.0 | 3035 | 2899 | 141 | 0.1 |
| gated | 14,111 | svc_north=0.985, svc_north_B=0.983, svc_south=0.978, svc_south_B=0.994 | 0.5 | 3064 | 2927 | 128 | 1.7 |

### X2_produce_plus_frozen_seafood
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 28,895 | svc_north=0.956, svc_north_B=0.996, svc_south=0.983, svc_south_B=0.993 | 0.5 | 3044 | 2906 | 132 | 0.0 |
| central_pool | 28,895 | svc_north=0.956, svc_north_B=0.996, svc_south=0.983, svc_south_B=0.993 | 0.5 | 3044 | 2906 | 132 | 0.0 |
| independent | 28,921 | svc_north=0.969, svc_north_B=0.984, svc_south=0.982, svc_south_B=0.993 | 0.5 | 3015 | 2883 | 247 | 1.9 |
| echelon_base_stock | 28,826 | svc_north=0.990, svc_north_B=1.000, svc_south=0.965, svc_south_B=0.979 | 0.0 | 3039 | 2906 | 139 | 0.1 |
| gated | 28,895 | svc_north=0.956, svc_north_B=0.996, svc_south=0.983, svc_south_B=0.993 | 0.5 | 3044 | 2906 | 132 | 1.5 |

### X3_three_sectors
| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |
|---|---|---|---|---|---|---|---|
| network_rop | 45,997 | svc_north=0.980, svc_north_B=0.970, svc_north_C=0.994, svc_south=0.983, svc_south_B=0.986, svc_south_C=0.000 | 8.0 | 3780 | 3467 | 215 | 0.1 |
| central_pool | 45,997 | svc_north=0.980, svc_north_B=0.970, svc_north_C=0.994, svc_south=0.983, svc_south_B=0.986, svc_south_C=0.000 | 8.0 | 3780 | 3467 | 215 | 0.1 |
| independent | 45,824 | svc_north=0.987, svc_north_B=0.983, svc_north_C=0.998, svc_south=0.990, svc_south_B=0.995, svc_south_C=0.000 | 8.0 | 3820 | 3661 | 369 | 1.8 |
| echelon_base_stock | 46,164 | svc_north=0.992, svc_north_B=0.975, svc_north_C=0.996, svc_south=0.969, svc_south_B=0.958, svc_south_C=0.000 | 8.0 | 3780 | 3778 | 477 | 0.1 |
| gated | 45,997 | svc_north=0.980, svc_north_B=0.970, svc_north_C=0.994, svc_south=0.983, svc_south_B=0.986, svc_south_C=0.000 | 8.0 | 3780 | 3467 | 215 | 2.3 |

## Network principles

| principle | pass | numbers |
|---|---|---|

## Sector principles

| fixture | principle | pass | evidence |
|---|---|---|---|
| C1_case_pack_rounding | case_multiples | PASS | {"case_multiple": 12.0, "violations": [], "purchase_lines": 12} |
| C2_pallet_load_threshold | load_limits | PASS | {"max_weight": 2200.0, "weight_per_unit": 2.5, "max_pallets": 8.0, "violations": [], "largest_order": 840.0} |
| C3_moq_mov_economics | moq_mov | PASS | {"moq": 240.0, "mov": 1800.0, "violations": []} |
| C4_long_import_lead | not_worse | PASS | {"note": "economic and service gates only"} |
| C5_variable_supplier_arrival | not_worse | PASS | {"note": "economic and service gates only"} |
| C6_storage_capacity | capacity | PASS | {"capacity": {"central": 1000000.0, "north": 320.0, "south": 320.0}, "violations": []} |
| C7_no_material_improvement | abstains | PASS | {"abstained_reviews": [7, 8], "required": 6} |
| P1_fresh_no_unnecessary_purchase | no_purchase_first_two_reviews | PASS | {"early_purchases": []} |
| P2_near_expiry_inventory | acts_on_near_expiry | PASS | {"first_review_actions": [[41001, 0, 124.79804747090446, 300.0], [41002, 0, 142.12298594946634, 298.51952778709995]], "north_service_zaad_vs_incumbent": [[41001, 0.9941482687895183, 0.9372634528208068], [41002, 0.9691909709493736, 0.934418989164174]]} |
| P3_age_at_receipt | uses_fresh_source | PASS | {"local_units": [[41001, 161.70576616986398], [41002, 151.13261304389565]], "expired_zaad_vs_incumbent": [[41001, 38.192289203036964, 200.0], [41002, 9.370471840448715, 200.0]]} |
| P4_transfer_becomes_useless | no_useless_transfer | PASS | {"south_units_zaad_vs_incumbent": [[41001, 0.0, 0.0], [41002, 0.0, 0.0]], "north_service": [[41001, 1.0], [41002, 0.9749763576242204]]} |
| P5_spoilage_vs_service | not_worse | PASS | {"note": "economic and service gates only"} |
| P6_uncertain_usable_yield | service_under_yield | PASS | {"service": [[41001, {"svc_north": 0.9479438685269028, "svc_south": 0.9381243616309599}], [41002, {"svc_north": 0.9408313498347719, "svc_south": 0.9655894085780203}]], "incumbent": [[41001, {"svc_north": 0.9520489679814922, "svc_south": 0.9273802764593493}], [41002, {"svc_north": 0.9377507938603805, |
| P7_fefo_settlement | fefo | PASS | {"note": "FEFO and sellable-life consumption proved by scripts.sector_invariants (invariants 3, 5, 15) on the settlement"} |
| P8_no_material_improvement | abstains | PASS | {"abstained_reviews": [7, 8], "required": 5} |
| M1_chilled_shelf_life | not_worse | PASS | {"note": "economic and service gates only"} |
| M2_frozen_shelf_life | not_worse | PASS | {"note": "economic and service gates only"} |
| M3_storage_state_infeasibility | never_at_ineligible_location | PASS | {"south_end_stock": [], "south_lane_units": [[41001, 0.0], [41002, 0.0]], "south_service": [[41001, 0.0], [41002, 0.0]]} |
| M4_cold_chain_lane | eligible_lane_only | PASS | {"lanes": [[41001, {"lane_north": 735.9445935793644, "lane_south": 0.0, "reefer_south": 778.9616408095673}], [41002, {"lane_north": 754.3344426418529, "lane_south": 0.0, "reefer_south": 780.1690860247149}]]} |
| M5_aging_vs_service | not_worse | PASS | {"note": "economic and service gates only"} |
| M6_transfer_usable_lot | moves_usable_lot | PASS | {"first_review_north_transfer": [[41001, 198.05479042135508], [41002, 198.05479042135508]]} |
| M7_transfer_rejected_by_expiry | expiring_lot_not_moved | PASS | {"first_review_transfers": [[41001, {}], [41002, {}]]} |
| M8_no_material_improvement | abstains | PASS | {"abstained_reviews": [7, 8], "required": 6} |
| X1_commercial_plus_produce | isolation_and_capacity | PASS | {"capacity_violations": [], "expired_units": [[41001, 67.14215527590424], [41002, 0.0]]} |
| X2_produce_plus_frozen_seafood | shared_capacity_no_cross_expiry | PASS | {"capacity_violations": [], "expired_units": [[41001, 24.110032097845306], [41002, 22.71223307675534]]} |
| X3_three_sectors | no_cross_physics | PASS | {"capacity_violations": [], "expired_units": [[41001, 67.14215527590424], [41002, 0.0]], "frozen_at_south": []} |

## Runtime (ZAAD reviews)

reviews 416, p50 1.7 s, p95 11.0 s, max 60.6 s; by sector {'COMMERCIAL': {'p50': 1.071091562975198, 'max': 60.55472354218364}, 'PRODUCE': {'p50': 3.381288708653301, 'max': 30.02469970844686}, 'MEAT_SEAFOOD': {'p50': 0.7946023750118911, 'max': 4.310714750085026}, 'MIXED': {'p50': 1.7855533750262111, 'max': 3.7059084167703986}}; over 60 s: [('C1_case_pack_rounding', 41002, 6, 60.6, 'NO_ACTION')]; over 180 s: []; solve statuses {'OPTIMAL': 1826, 'INFEASIBLE': 198}; errors []
