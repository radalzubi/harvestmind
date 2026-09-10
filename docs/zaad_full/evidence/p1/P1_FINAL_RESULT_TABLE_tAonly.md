# P1 authoritative final result table (final code; pre-fix record beside it, never overwritten)

Legacy: eleven rolling reviews of a shrinking twelve-period plan, realised ledger (declared salvage). Declared benchmark: constant rolling twelve-period planning horizon, 52 reviews, landed-cost continuation of the residual (pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`). PRE-FIX = `de4e771` product policy; FINAL-CODE = lot-sizing terminal valuation on P1-owned reviews with the consistent ledger key. Seed means over 41001-41003; ZAAD against the best baseline.

| fixture | legacy PRE-FIX delta | legacy FINAL delta | legacy FINAL verdict | declared PRE-FIX delta @52 | **declared FINAL @52** (ZAAD / best baseline) | FINAL verdict | stable (max dev 40..52) | service | unmet | avg inv units | purchases | orders (ZAAD / best base) | freight | carrying | terminal credit (landed) | P1 / P0 owned reviews | actions | abstentions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | +0.43% | +0.27% | PASS | +0.87% | **+0.81%** (26,645 / incumbent 26,431) | PASS | yes (0.22 pp) | 0.989 | 55.1 | 17 | 25,737 | 51.3 / 52.0 | 0 | 13 | 543 | 153 / 3 | 43 | 21 |
| B_fixed_order_cost_replace_sold | -10.70% | -10.70% | PASS | +2.49% | **+2.66%** (28,390 / economic_lot 27,654) | FAIL | NO (1.77 pp) | 1.000 | 0.0 | 597 | 29,240 | 7.7 / 3.0 | 0 | 446 | 3,963 | 153 / 3 | 149 | 0 |
| C_moq_four_weeks | +3.61% | +1.88% | PASS | +0.30% | **+0.39%** (26,534 / reorder_point 26,431) | PASS | yes (0.30 pp) | 1.000 | 2.4 | 354 | 27,495 | 12.7 / 14.0 | 0 | 265 | 2,005 | 153 / 3 | 141 | 0 |
| D_case_multiple | -0.58% | -0.51% | PASS | +0.63% | **+0.65%** (26,432 / incumbent 26,261) | PASS | yes (0.19 pp) | 0.995 | 24.7 | 32 | 25,920 | 52.0 / 52.0 | 0 | 24 | 570 | 153 / 3 | 81 | 7 |
| E_pallet_multiple | -0.00% | +0.00% | PASS | -0.10% | **-0.02%** (27,895 / incumbent 27,901) | PASS | yes (0.08 pp) | 1.000 | 2.2 | 103 | 26,333 | 26.3 / 26.7 | 1,580 | 77 | 873 | 153 / 3 | 36 | 10 |
| F_mov_two_skus | +0.24% | +0.30% | PASS | +0.72% | **+0.80%** (53,077 / periodic:2 52,657) | PASS | yes (0.11 pp) | 1.000 | 3.5 | 691 | 56,096 | 26.3 / 26.0 | 0 | 517 | 5,080 | 153 / 3 | 120 | 0 |
| G_freight_tiers | -10.01% | -0.98% | PASS | +6.18% | **-0.76%** (62,938 / economic_lot 63,421) | PASS | yes (0.72 pp) | 1.000 | 0.0 | 1168 | 58,589 | 7.0 / 7.0 | 9,800 | 874 | 8,525 | 153 / 3 | 154 | 0 |
| H_per_pallet_freight | -3.73% | -5.00% | PASS | -1.27% | **-1.97%** (29,681 / periodic:2 30,277) | PASS | yes (0.17 pp) | 0.997 | 15.5 | 101 | 25,926 | 37.0 / 26.0 | 3,340 | 76 | 605 | 153 / 3 | 128 | 28 |
| I_max_pallets_ftl_cap | +0.53% | +0.08% | PASS | +7.14% | **+0.07%** (40,690 / economic_lot 40,662) | PASS | yes (0.12 pp) | 1.000 | 1.1 | 280 | 26,930 | 12.0 / 12.0 | 13,200 | 209 | 2,212 | 153 / 3 | 155 | 0 |
| J_net60_cost_of_capital | -11.06% | -11.06% | PASS | +0.15% | **+0.34%** (27,547 / economic_lot 27,454) | PASS at 52 and at every endpoint 40..52; magnitude not converged (class E) | NO (1.25 pp) | 1.000 | 0.0 | 580 | 28,943 | 5.3 / 5.0 | 0 | 434 | 3,435 | 153 / 3 | 142 | 9 |
| K_deposit_early_cash | -11.20% | -11.20% | PASS | +0.15% | **+0.34%** (27,560 / economic_lot 27,467) | PASS at 52 and at every endpoint 40..52; magnitude not converged (class E) | NO (1.28 pp) | 1.000 | 0.0 | 580 | 28,943 | 5.3 / 5.0 | 0 | 434 | 3,435 | 153 / 3 | 142 | 9 |
| L_high_holding_rate | -10.16% | -10.16% | PASS | +0.81% | **+1.07%** (28,232 / economic_lot 27,933) | PASS | yes (0.54 pp) | 1.000 | 0.0 | 595 | 29,419 | 7.7 / 6.0 | 0 | 889 | 3,976 | 153 / 3 | 149 | 0 |
| M_order_calendar_wednesday | -0.54% | -1.11% | PASS | +0.05% | **-0.17%** (26,728 / incumbent 26,773) | PASS | yes (0.11 pp) | 0.989 | 57.6 | 87 | 26,587 | 50.7 / 52.0 | 0 | 65 | 1,394 | 12 / 144 | 141 | 1 |
| N_long_lead_21_days | -0.71% | -1.08% | FAIL ['categories'] | +1.07% | **+0.61%** (26,649 / incumbent 26,488) | proven invalid (kept); cost within tolerance | yes (0.13 pp) | 0.990 | 52.6 | 33 | 25,730 | 52.0 / 52.0 | 0 | 25 | 1,513 | 152 / 4 | 33 | 23 |
| O_low_opening_stock | +0.46% | +1.04% | PASS | +0.09% | **+0.13%** (27,041 / reorder_point 27,006) | PASS | yes (0.14 pp) | 0.980 | 102.4 | 67 | 26,461 | 41.3 / 52.0 | 0 | 50 | 850 | 108 / 48 | 132 | 18 |
| P_high_opening_stock | +0.29% | +0.41% | PASS | +0.16% | **+0.29%** (26,469 / reorder_point 26,394) | PASS | yes (0.25 pp) | 0.994 | 32.1 | 102 | 23,618 | 43.3 / 47.7 | 0 | 77 | 627 | 153 / 3 | 108 | 20 |
| Q_volatile_demand_high_target | +0.85% | +0.85% | PASS | +0.19% | **+0.17%** (25,575 / incumbent 25,532) | PASS | yes (0.04 pp) | 0.991 | 45.9 | 75 | 24,966 | 48.7 / 51.7 | 0 | 56 | 771 | 72 / 84 | 20 | 1 |
| R_asymmetric_prices_mov | -0.05% | -0.02% | FAIL ['categories'] | +0.65% | **+0.59%** (291,231 / incumbent 289,535) | proven invalid (kept); cost within tolerance | yes (0.15 pp) | 0.993 | 73.3 | 64 | 288,112 | 48.3 / 52.0 | 0 | 257 | 9,780 | 153 / 3 | 34 | 37 |
| S_cash_constrained | +0.26% | +0.26% | PASS | invalid | INVALID at 52 (all five policies complete only to W = 12; diagnostic there +5.16%) | PROVEN INVALID at the declared benchmark | - | | | | | | | | | | | |
| T_combined_realistic | -11.47% | -3.97% | PASS | +6.87% | **-0.28%** (63,436 / economic_lot 63,612) | PASS | yes (0.86 pp) | 0.999 | 9.8 | 1077 | 57,720 | 6.7 / 6.7 | 9,533 | 967 | 8,021 | 153 / 3 | 154 | 0 |

Runtime, final rolling run, ZAAD reviews: n 3013, p50 1.02 s, p90 4.10 s, p95 6.29 s, max 67.4 s.
