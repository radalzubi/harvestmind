# P1 authoritative final result table (final code; pre-fix record beside it, never overwritten)

Legacy: eleven rolling reviews of a shrinking twelve-period plan, realised ledger (declared salvage). Declared benchmark: constant rolling twelve-period planning horizon, 52 reviews, landed-cost continuation of the residual (pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`). PRE-FIX = `de4e771` product policy; FINAL-CODE = lot-sizing terminal valuation on P1-owned reviews with the consistent ledger key. Seed means over 41001-41003; ZAAD against the best baseline.

| fixture | legacy PRE-FIX delta | legacy FINAL delta | legacy FINAL verdict | declared PRE-FIX delta @52 | **declared FINAL @52** (ZAAD / best baseline) | FINAL verdict | stable (max dev 40..52) | service | unmet | avg inv units | purchases | orders (ZAAD / best base) | freight | carrying | terminal credit (landed) | P1 / P0 owned reviews | actions | abstentions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | +0.43% | +0.27% | PASS | +0.87% | **+0.81%** (26,645 / incumbent 26,431) | PASS | yes (0.22 pp) | 0.989 | 55.1 | 17 | 25,737 | 51.3 / 52.0 | 0 | 13 | 543 | 138 / 18 | 41 | 18 |
| B_fixed_order_cost_replace_sold | -10.70% | -10.70% | PASS | +2.49% | **+2.49%** (28,343 / economic_lot 27,654) | FAIL | NO (1.44 pp) | 1.000 | 0.0 | 621 | 28,993 | 7.3 / 3.0 | 0 | 464 | 3,697 | 137 / 19 | 150 | 0 |
| C_moq_four_weeks | +3.61% | +1.88% | PASS | +0.30% | **+0.46%** (26,553 / reorder_point 26,431) | PASS | yes (0.29 pp) | 1.000 | 2.4 | 364 | 27,780 | 12.7 / 14.0 | 0 | 272 | 2,279 | 137 / 19 | 140 | 0 |
| D_case_multiple | -0.58% | -0.51% | PASS | +0.63% | **+0.66%** (26,434 / incumbent 26,261) | PASS | yes (0.18 pp) | 0.995 | 24.7 | 32 | 25,920 | 52.0 / 52.0 | 0 | 24 | 569 | 138 / 18 | 78 | 7 |
| E_pallet_multiple | -0.00% | +0.00% | PASS | -0.10% | **-0.01%** (27,898 / incumbent 27,901) | PASS | yes (0.08 pp) | 1.000 | 2.2 | 102 | 26,333 | 26.3 / 26.7 | 1,580 | 76 | 869 | 139 / 17 | 36 | 7 |
| F_mov_two_skus | +0.24% | +0.30% | PASS | +0.72% | **+0.70%** (53,024 / periodic:2 52,657) | PASS | yes (0.15 pp) | 1.000 | 3.5 | 676 | 55,433 | 26.0 / 26.0 | 0 | 505 | 4,458 | 125 / 31 | 122 | 0 |
| G_freight_tiers | -10.01% | -0.98% | PASS | +6.18% | **+0.46%** (63,714 / economic_lot 63,421) | PASS | yes (0.88 pp) | 1.000 | 0.0 | 1186 | 59,130 | 8.0 / 7.0 | 10,600 | 887 | 9,203 | 125 / 31 | 151 | 0 |
| H_per_pallet_freight | -3.73% | -5.00% | PASS | -1.27% | **-1.67%** (29,772 / periodic:2 30,277) | PASS | yes (0.17 pp) | 0.997 | 14.7 | 121 | 25,958 | 35.3 / 26.0 | 3,400 | 90 | 610 | 138 / 18 | 124 | 30 |
| I_max_pallets_ftl_cap | +0.53% | +0.08% | PASS | +7.14% | **+0.57%** (40,895 / economic_lot 40,662) | PASS | yes (0.14 pp) | 1.000 | 1.1 | 276 | 27,021 | 12.3 / 12.0 | 13,467 | 206 | 2,412 | 137 / 19 | 155 | 0 |
| J_net60_cost_of_capital | -11.06% | -11.06% | PASS | +0.15% | **+0.15%** (27,496 / economic_lot 27,454) | PASS | yes (0.65 pp) | 1.000 | 0.0 | 582 | 28,983 | 5.3 / 5.0 | 0 | 435 | 3,528 | 136 / 20 | 142 | 8 |
| K_deposit_early_cash | -11.20% | -11.20% | PASS | +0.15% | **+0.15%** (27,508 / economic_lot 27,467) | PASS | yes (0.67 pp) | 1.000 | 0.0 | 582 | 28,983 | 5.3 / 5.0 | 0 | 435 | 3,528 | 136 / 20 | 142 | 8 |
| L_high_holding_rate | -10.16% | -10.16% | PASS | +0.81% | **+0.81%** (28,159 / economic_lot 27,933) | PASS | yes (0.60 pp) | 1.000 | 0.0 | 612 | 28,868 | 7.0 / 6.0 | 0 | 915 | 3,424 | 137 / 19 | 151 | 0 |
| M_order_calendar_wednesday | -0.54% | -1.11% | PASS | +0.05% | **-0.17%** (26,728 / incumbent 26,773) | PASS | yes (0.11 pp) | 0.989 | 57.6 | 87 | 26,587 | 50.7 / 52.0 | 0 | 65 | 1,394 | 12 / 144 | 141 | 1 |
| N_long_lead_21_days | -0.71% | -1.08% | FAIL ['categories'] | +1.07% | **+0.61%** (26,648 / incumbent 26,488) | proven invalid (kept); cost within tolerance | yes (0.13 pp) | 0.990 | 52.6 | 32 | 25,699 | 52.0 / 52.0 | 0 | 24 | 1,481 | 133 / 23 | 41 | 21 |
| O_low_opening_stock | +0.46% | +1.04% | PASS | +0.09% | **+0.21%** (27,062 / reorder_point 27,006) | PASS | yes (0.08 pp) | 0.980 | 104.9 | 64 | 26,453 | 42.3 / 52.0 | 0 | 48 | 850 | 96 / 60 | 133 | 17 |
| P_high_opening_stock | +0.29% | +0.41% | PASS | +0.16% | **+0.35%** (26,485 / reorder_point 26,394) | PASS | yes (0.27 pp) | 0.993 | 34.3 | 100 | 23,608 | 43.0 / 47.7 | 0 | 75 | 627 | 138 / 18 | 114 | 18 |
| Q_volatile_demand_high_target | +0.85% | +0.85% | PASS | +0.19% | **+0.17%** (25,575 / incumbent 25,532) | PASS | yes (0.04 pp) | 0.991 | 45.9 | 75 | 24,966 | 48.7 / 51.7 | 0 | 56 | 771 | 69 / 87 | 20 | 1 |
| R_asymmetric_prices_mov | -0.05% | -0.02% | FAIL ['categories'] | +0.65% | **+0.55%** (291,129 / incumbent 289,535) | proven invalid (kept); cost within tolerance | yes (0.19 pp) | 0.992 | 79.6 | 56 | 283,972 | 50.3 / 52.0 | 0 | 181 | 6,093 | 123 / 33 | 31 | 28 |
| S_cash_constrained | +0.26% | +0.26% | PASS | invalid | INVALID at 52 (all five policies complete only to W = 12; diagnostic there +5.16%) | PROVEN INVALID at the declared benchmark | - | | | | | | | | | | | |
| T_combined_realistic | -11.47% | -3.97% | PASS | +6.87% | **+2.06%** (64,919 / economic_lot 63,612) | FAIL | yes (0.38 pp) | 0.999 | 9.8 | 1037 | 58,320 | 8.7 / 6.7 | 10,900 | 931 | 8,920 | 124 / 32 | 149 | 0 |

Runtime, final rolling run, ZAAD reviews: n 3013, p50 0.96 s, p90 4.32 s, p95 6.53 s, max 79.3 s.
