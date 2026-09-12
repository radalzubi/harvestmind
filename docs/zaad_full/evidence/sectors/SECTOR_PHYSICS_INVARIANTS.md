# Sector physics invariants

| invariant | result | evidence |
|---|---|---|
| 01_legacy_unchanged | PASS | {"actions": 36, "note": "canonical regression (B/T/Q/A, P0 cell 15) is the authoritative frozen-identity gate; recorded in the closeout"} |
| 02_commercial_packs_executable | PASS | {"purchases": {"src_A@0": 12.0, "src_A@1": 204.0, "src_A@2": 204.0, "src_A@3": 204.0, "src_A@4": 204.0, "src_A@5": 204.0, "src_A@6": 204.0, "src_A@7": 204.0, "src_A@8": 204.0, "src_A@9": 204.0}} |
| 03_produce_expired_cannot_serve | PASS | {"served_after_expiry": 0.0, "expired_units": 1599.076923076923} |
| 04_terminal_monotone_in_life | PASS | {"credit_by_expiry": {"10": 499.27, "8": 499.27, "6": 499.27, "4": 499.27, "3": 497.3, "2": 400.0, "1": 400.0}} |
| 05_fefo_settlement | PASS | {"end_stock": {"north": [[2, 0.0], [5, 51.61538461538461]], "south": [[2, 0.0], [5, 47.92307692307692]]}} |
| 06_fefo_symmetry_elimination_active | PASS | {"commercial": {"fefo": 0, "binary": 72}, "produce": {"fefo": 594, "binary": 666}} |
| 07_transfer_never_gains_life | PASS | {"in_transit": [[4, 1, 46.8]]} |
| 08_incompatible_location_cannot_hold | PASS | {"south_transfer_in_plan": 0} |
| 09_incompatible_lane_cannot_move | PASS | {"lane_units": {"lane_south": 0, "reefer_south": 1074.923076923077, "lane_north": 1030.6153846153848}} |
| 10_meat_expired_cannot_serve | PASS | {"served_after_expiry": 0.0} |
| 11_mixed_isolation | PASS | {"A_profile": {"sku": "A", "sector": "COMMERCIAL", "storage_state": "AMBIENT", "age_at_receipt_periods": 0, "age_at_receipt_by_source": {}, "minimum_remaining_life_at_receipt": 0, "minimum_remaining_life_at_sale": 0, "weight_per_unit": null, "provenance": {}}} |
| 12_network_conservation | PASS | {"worst_residual": 6.252776074688882e-12} |
| 13_no_double_allocation | PASS | {"served": 200.46153846153845, "opening_branch_units": 300.0} |
| 14_no_negative_inventory | PASS | {"most_negative": -1.4210854715202004e-14} |
| 15_no_resurrection | PASS | {"expired_cumulative": [0.0, 0.0, 803.2307692307693, 803.2307692307693, 803.2307692307693, 803.2307692307693]} |
| 16_no_shelf_life_reset_on_transfer | PASS | {"in_transit_expiry": [[4, 1], [4, 1]]} |
| 17_18_no_autonomous_po_and_approval | PASS | {"reviews": 3} |
| 19_20_21_ownership_unchanged | PASS | {"owners": {"C7_no_material_improvement": ["PURCHASING_ECONOMICS", "NO_ACTION"], "P1_fresh_no_unnecessary_purchase": ["PURCHASING_ECONOMICS", "NO_ACTION"], "M1_chilled_shelf_life": ["PROTECTION_RECOVERY", "NORMAL_REPLENISHMENT"], "X3_three_sectors": ["PROTECTION_RECOVERY", "NORMAL_REPLENISHMENT"]}, "note": "no sector owner exists; P0 / P1 / P2 labels only"} |
| 12b_benchmark_conservation | PASS | {"worst_residual": 3.410605131648481e-13, "physical_failures": []} |

19 / 19 PASS. benchmark sector_under_p4rel: 52 ZAAD cells, worst conservation residual 3.41e-13, ZAAD physical failures []
