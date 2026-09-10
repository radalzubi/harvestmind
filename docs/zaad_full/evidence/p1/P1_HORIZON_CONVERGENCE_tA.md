# P1 extended-window benchmark: convergence, stability, selection and the declared result

Source `docs/zaad_full/evidence/p1/closure/horizon52_tA_full.jsonl`: 300 cells, rolling twelve-period planning horizon, 52 reviews requested, stitched truth per seed, scored at every endpoint under both terminal rules. Pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`.

## Completeness and validity at the declared endpoint (section 7)

| fixture | last endpoint with all five policies complete | incomplete cells (policy, seed, reviews, status) |
|---|---|---|
| A_no_terms_good_incumbent | 52 | - |
| B_fixed_order_cost_replace_sold | 52 | - |
| C_moq_four_weeks | 52 | - |
| D_case_multiple | 52 | - |
| E_pallet_multiple | 52 | - |
| F_mov_two_skus | 52 | - |
| G_freight_tiers | 52 | - |
| H_per_pallet_freight | 52 | - |
| I_max_pallets_ftl_cap | 52 | - |
| J_net60_cost_of_capital | 52 | - |
| K_deposit_early_cash | 52 | - |
| L_high_holding_rate | 52 | - |
| M_order_calendar_wednesday | 52 | - |
| N_long_lead_21_days | 52 | - |
| O_low_opening_stock | 52 | - |
| P_high_opening_stock | 52 | - |
| Q_volatile_demand_high_target | 52 | - |
| R_asymmetric_prices_mov | 52 | - |
| S_cash_constrained | 12 | [('incumbent', 41001, 26, 'PHYSICAL_FAILURE'), ('incumbent', 41002, 24, 'PHYSICAL_FAILURE'), ('incumbent', 41003, 29, 'PHYSICAL_FAILURE'), ('reorder_point', 41001, 26, 'PHYSICAL_FAILURE'), ('reorder_point', 41002, 24, 'PHYSICAL_FAILURE'), ('reorder_point', 41003, 29, 'PHYSICAL_FAILURE'), ('economic_lot', 41001, 45, 'PHYSICAL_FAILURE'), ('economic_lot', 41002, 41, 'PHYSICAL_FAILURE'), ('economic_lot', 41003, 44, 'PHYSICAL_FAILURE'), ('gated', 41001, 19, 'ABSTAIN'), ('gated', 41002, 18, 'ABSTAIN'), ('gated', 41003, 12, 'ABSTAIN')] |
| T_combined_realistic | 52 | - |

## Stage 3: endpoint sensitivity (seed means; ZAAD against the best baseline at that endpoint)

### A_no_terms_good_incumbent (valid to W = 52; legacy 12-week: salvage +0.43%, continuation +0.46%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,910 | incumbent 5,824 | +1.48% | 0.982 | 20.4 | 25 | 93 | [0, 0, 0] | 471 | 588 / 588 |
| 11 | continuation | 5,793 | incumbent 5,710 | +1.46% | 0.982 | 20.4 | 25 | 93 | [0, 0, 0] | 471 | 588 / 588 |
| 11 | continuation_landed | 5,793 | incumbent 5,710 | +1.46% | 0.982 | 20.4 | 25 | 93 | [0, 0, 0] | 471 | 588 / 588 |
| 13 | salvage | 6,956 | incumbent 6,874 | +1.19% | 0.984 | 21.4 | 7 | 112 | [0, 0, 0] | 479 | 598 / 598 |
| 13 | continuation | 6,837 | incumbent 6,757 | +1.18% | 0.984 | 21.4 | 7 | 112 | [0, 0, 0] | 479 | 598 / 598 |
| 13 | continuation_landed | 6,837 | incumbent 6,757 | +1.18% | 0.984 | 21.4 | 7 | 112 | [0, 0, 0] | 479 | 598 / 598 |
| 15 | salvage | 7,947 | incumbent 7,870 | +0.98% | 0.986 | 21.6 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 15 | continuation | 7,838 | incumbent 7,757 | +1.04% | 0.986 | 21.6 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 15 | continuation_landed | 7,838 | incumbent 7,757 | +1.04% | 0.986 | 21.6 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 17 | salvage | 8,969 | incumbent 8,861 | +1.23% | 0.985 | 25.4 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 17 | continuation | 8,866 | incumbent 8,757 | +1.25% | 0.985 | 25.4 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 17 | continuation_landed | 8,866 | incumbent 8,757 | +1.25% | 0.985 | 25.4 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 19 | salvage | 10,046 | incumbent 9,934 | +1.12% | 0.984 | 30.3 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 19 | continuation | 9,932 | incumbent 9,821 | +1.14% | 0.984 | 30.3 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 19 | continuation_landed | 9,932 | incumbent 9,821 | +1.14% | 0.984 | 30.3 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 23 | salvage | 12,100 | incumbent 11,993 | +0.89% | 0.986 | 31.1 | 23 | 94 | [0, 0, 0] | 467 | 582 / 582 |
| 23 | continuation | 11,984 | incumbent 11,874 | +0.93% | 0.986 | 31.1 | 23 | 94 | [0, 0, 0] | 467 | 582 / 582 |
| 23 | continuation_landed | 11,984 | incumbent 11,874 | +0.93% | 0.986 | 31.1 | 23 | 94 | [0, 0, 0] | 467 | 582 / 582 |
| 35 | salvage | 18,230 | incumbent 18,033 | +1.10% | 0.987 | 46.2 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 35 | continuation | 18,106 | incumbent 17,917 | +1.05% | 0.987 | 46.2 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 35 | continuation_landed | 18,106 | incumbent 17,917 | +1.05% | 0.987 | 46.2 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 47 | salvage | 24,281 | incumbent 24,046 | +0.98% | 0.988 | 57.8 | 18 | 102 | [0, 0, 0] | 480 | 598 / 598 |
| 47 | continuation | 24,162 | incumbent 23,927 | +0.98% | 0.988 | 57.8 | 18 | 102 | [0, 0, 0] | 480 | 598 / 598 |
| 47 | continuation_landed | 24,162 | incumbent 23,927 | +0.98% | 0.988 | 57.8 | 18 | 102 | [0, 0, 0] | 480 | 598 / 598 |
| 52 | salvage | 26,773 | incumbent 26,539 | +0.88% | 0.989 | 57.8 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation | 26,665 | incumbent 26,431 | +0.89% | 0.989 | 57.8 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation_landed | 26,665 | incumbent 26,431 | +0.89% | 0.989 | 57.8 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |

### B_fixed_order_cost_replace_sold (valid to W = 52; legacy 12-week: salvage -10.70%, continuation -1.06%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,339 | economic_lot 6,995 | +4.92% | 1.000 | 0.0 | 734 | 319 | [0, None, None] | 4,212 | 5,185 / 5,442 |
| 11 | continuation | 6,366 | economic_lot 6,182 | +2.98% | 1.000 | 0.0 | 734 | 319 | [0, None, None] | 4,212 | 5,185 / 5,442 |
| 11 | continuation_landed | 6,109 | economic_lot 6,065 | +0.73% | 1.000 | 0.0 | 734 | 319 | [0, None, None] | 4,212 | 5,185 / 5,442 |
| 13 | salvage | 8,177 | economic_lot 7,827 | +4.46% | 1.000 | 0.0 | 850 | 0 | [None, None, None] | 3,400 | 4,197 / 4,405 |
| 13 | continuation | 7,379 | economic_lot 7,195 | +2.56% | 1.000 | 0.0 | 850 | 0 | [None, None, None] | 3,400 | 4,197 / 4,405 |
| 13 | continuation_landed | 7,172 | economic_lot 7,105 | +0.94% | 1.000 | 0.0 | 850 | 0 | [None, None, None] | 3,400 | 4,197 / 4,405 |
| 15 | salvage | 8,980 | economic_lot 8,625 | +4.11% | 1.000 | 0.0 | 654 | 0 | [None, None, None] | 2,617 | 3,239 / 3,399 |
| 15 | continuation | 8,357 | economic_lot 8,173 | +2.26% | 1.000 | 0.0 | 654 | 0 | [None, None, None] | 2,617 | 3,239 / 3,399 |
| 15 | continuation_landed | 8,198 | economic_lot 8,110 | +1.09% | 1.000 | 0.0 | 654 | 0 | [None, None, None] | 2,617 | 3,239 / 3,399 |
| 17 | salvage | 9,780 | economic_lot 9,420 | +3.82% | 1.000 | 0.0 | 458 | 0 | [None, None, None] | 1,831 | 2,273 / 2,384 |
| 17 | continuation | 9,339 | economic_lot 9,154 | +2.02% | 1.000 | 0.0 | 458 | 0 | [None, None, None] | 1,831 | 2,273 / 2,384 |
| 17 | continuation_landed | 9,228 | economic_lot 9,118 | +1.21% | 1.000 | 0.0 | 458 | 0 | [None, None, None] | 1,831 | 2,273 / 2,384 |
| 19 | salvage | 11,053 | economic_lot 11,775 | -6.13% | 1.000 | 0.0 | 257 | 324 | [None, None, 0] | 2,326 | 2,873 / 3,019 |
| 19 | continuation | 10,506 | economic_lot 10,666 | -1.50% | 1.000 | 0.0 | 257 | 324 | [None, None, 0] | 2,326 | 2,873 / 3,019 |
| 19 | continuation_landed | 10,360 | economic_lot 10,494 | -1.28% | 1.000 | 0.0 | 257 | 324 | [None, None, 0] | 2,326 | 2,873 / 3,019 |
| 23 | salvage | 13,697 | economic_lot 14,233 | -3.76% | 1.000 | 0.0 | 922 | 0 | [None, None, None] | 3,686 | 4,547 / 4,766 |
| 23 | continuation | 12,837 | economic_lot 12,892 | -0.43% | 1.000 | 0.0 | 922 | 0 | [None, None, None] | 3,686 | 4,547 / 4,766 |
| 23 | continuation_landed | 12,618 | economic_lot 12,691 | -0.58% | 1.000 | 0.0 | 922 | 0 | [None, None, None] | 3,686 | 4,547 / 4,766 |
| 35 | salvage | 19,814 | economic_lot 19,080 | +3.85% | 1.000 | 0.0 | 718 | 0 | [None, None, None] | 2,872 | 3,546 / 3,715 |
| 35 | continuation | 19,140 | economic_lot 18,764 | +2.01% | 1.000 | 0.0 | 718 | 0 | [None, None, None] | 2,872 | 3,546 / 3,715 |
| 35 | continuation_landed | 18,971 | economic_lot 18,720 | +1.34% | 1.000 | 0.0 | 718 | 0 | [None, None, None] | 2,872 | 3,546 / 3,715 |
| 47 | salvage | 25,978 | economic_lot 26,174 | -0.75% | 1.000 | 0.0 | 518 | 0 | [None, None, None] | 2,072 | 2,562 / 2,686 |
| 47 | continuation | 25,488 | economic_lot 25,264 | +0.89% | 1.000 | 0.0 | 518 | 0 | [None, None, None] | 2,072 | 2,562 / 2,686 |
| 47 | continuation_landed | 25,364 | economic_lot 25,133 | +0.92% | 1.000 | 0.0 | 518 | 0 | [None, None, None] | 2,072 | 2,562 / 2,686 |
| 52 | salvage | 28,957 | economic_lot 28,189 | +2.72% | 1.000 | 0.0 | 716 | 0 | [None, None, None] | 2,866 | 3,541 / 3,727 |
| 52 | continuation | 28,281 | economic_lot 27,719 | +2.03% | 1.000 | 0.0 | 716 | 0 | [None, None, None] | 2,866 | 3,541 / 3,727 |
| 52 | continuation_landed | 28,095 | economic_lot 27,654 | +1.60% | 1.000 | 0.0 | 716 | 0 | [None, None, None] | 2,866 | 3,541 / 3,727 |

### C_moq_four_weeks (valid to W = 52; legacy 12-week: salvage +3.61%, continuation +0.77%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,182 | reorder_point 5,898 | +4.83% | 1.000 | 0.0 | 334 | 132 | [None, None, 0] | 1,861 | 2,311 / 2,311 |
| 11 | continuation | 5,733 | reorder_point 5,681 | +0.92% | 1.000 | 0.0 | 334 | 132 | [None, None, 0] | 1,861 | 2,311 / 2,311 |
| 11 | continuation_landed | 5,733 | reorder_point 5,681 | +0.92% | 1.000 | 0.0 | 334 | 132 | [None, None, 0] | 1,861 | 2,311 / 2,311 |
| 13 | salvage | 7,003 | reorder_point 7,147 | -2.01% | 1.000 | 0.0 | 262 | 0 | [None, None, None] | 1,049 | 1,306 / 1,306 |
| 13 | continuation | 6,747 | reorder_point 6,749 | -0.04% | 1.000 | 0.0 | 262 | 0 | [None, None, None] | 1,049 | 1,306 / 1,306 |
| 13 | continuation_landed | 6,747 | reorder_point 6,749 | -0.04% | 1.000 | 0.0 | 262 | 0 | [None, None, None] | 1,049 | 1,306 / 1,306 |
| 15 | salvage | 8,085 | reorder_point 7,937 | +1.86% | 1.000 | 0.0 | 215 | 132 | [None, None, 0] | 1,385 | 1,721 / 1,721 |
| 15 | continuation | 7,749 | reorder_point 7,727 | +0.28% | 1.000 | 0.0 | 215 | 132 | [None, None, 0] | 1,385 | 1,721 / 1,721 |
| 15 | continuation_landed | 7,749 | reorder_point 7,727 | +0.28% | 1.000 | 0.0 | 215 | 132 | [None, None, 0] | 1,385 | 1,721 / 1,721 |
| 17 | salvage | 9,025 | reorder_point 9,167 | -1.54% | 1.000 | 0.0 | 280 | 0 | [None, None, None] | 1,119 | 1,392 / 1,392 |
| 17 | continuation | 8,752 | reorder_point 8,771 | -0.22% | 1.000 | 0.0 | 280 | 0 | [None, None, None] | 1,119 | 1,392 / 1,392 |
| 17 | continuation_landed | 8,752 | reorder_point 8,771 | -0.22% | 1.000 | 0.0 | 280 | 0 | [None, None, None] | 1,119 | 1,392 / 1,392 |
| 19 | salvage | 10,223 | reorder_point 9,976 | +2.47% | 1.000 | 0.0 | 290 | 129 | [None, None, 0] | 1,677 | 2,081 / 2,081 |
| 19 | continuation | 9,819 | reorder_point 9,772 | +0.48% | 1.000 | 0.0 | 290 | 129 | [None, None, 0] | 1,677 | 2,081 / 2,081 |
| 19 | continuation_landed | 9,819 | reorder_point 9,772 | +0.48% | 1.000 | 0.0 | 290 | 129 | [None, None, 0] | 1,677 | 2,081 / 2,081 |
| 23 | salvage | 12,133 | reorder_point 12,019 | +0.95% | 1.000 | 0.0 | 279 | 0 | [None, None, None] | 1,117 | 1,389 / 1,389 |
| 23 | continuation | 11,861 | reorder_point 11,823 | +0.33% | 1.000 | 0.0 | 279 | 0 | [None, None, None] | 1,117 | 1,389 / 1,389 |
| 23 | continuation_landed | 11,861 | reorder_point 11,823 | +0.33% | 1.000 | 0.0 | 279 | 0 | [None, None, None] | 1,117 | 1,389 / 1,389 |
| 35 | salvage | 18,199 | reorder_point 18,048 | +0.84% | 1.000 | 0.0 | 174 | 134 | [0, None, None] | 1,231 | 1,531 / 1,531 |
| 35 | continuation | 17,899 | reorder_point 17,850 | +0.27% | 1.000 | 0.0 | 174 | 134 | [0, None, None] | 1,231 | 1,531 / 1,531 |
| 35 | continuation_landed | 17,899 | reorder_point 17,850 | +0.27% | 1.000 | 0.0 | 174 | 134 | [0, None, None] | 1,231 | 1,531 / 1,531 |
| 47 | salvage | 24,277 | reorder_point 24,077 | +0.83% | 1.000 | 0.0 | 381 | 0 | [None, None, None] | 1,524 | 1,893 / 1,893 |
| 47 | continuation | 23,908 | reorder_point 23,876 | +0.13% | 1.000 | 0.0 | 381 | 0 | [None, None, None] | 1,524 | 1,893 / 1,893 |
| 47 | continuation_landed | 23,908 | reorder_point 23,876 | +0.13% | 1.000 | 0.0 | 381 | 0 | [None, None, None] | 1,524 | 1,893 / 1,893 |
| 52 | salvage | 27,024 | reorder_point 26,911 | +0.42% | 1.000 | 0.0 | 398 | 185 | [0, None, None] | 2,334 | 2,891 / 2,891 |
| 52 | continuation | 26,466 | reorder_point 26,431 | +0.13% | 1.000 | 0.0 | 398 | 185 | [0, None, None] | 2,334 | 2,891 / 2,891 |
| 52 | continuation_landed | 26,466 | reorder_point 26,431 | +0.13% | 1.000 | 0.0 | 398 | 185 | [0, None, None] | 2,334 | 2,891 / 2,891 |

### D_case_multiple (valid to W = 52; legacy 12-week: salvage -0.58%, continuation +0.17%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,777 | incumbent 5,807 | -0.52% | 0.997 | 2.8 | 51 | 62 | [0, 0, 0] | 454 | 567 / 567 |
| 11 | continuation | 5,664 | incumbent 5,651 | +0.23% | 0.997 | 2.8 | 51 | 62 | [0, 0, 0] | 454 | 567 / 567 |
| 11 | continuation_landed | 5,664 | incumbent 5,651 | +0.23% | 0.997 | 2.8 | 51 | 62 | [0, 0, 0] | 454 | 567 / 567 |
| 13 | salvage | 6,839 | incumbent 6,845 | -0.09% | 0.996 | 5.7 | 23 | 94 | [0, 0, 0] | 469 | 585 / 585 |
| 13 | continuation | 6,722 | incumbent 6,689 | +0.51% | 0.996 | 5.7 | 23 | 94 | [0, 0, 0] | 469 | 585 / 585 |
| 13 | continuation_landed | 6,722 | incumbent 6,689 | +0.51% | 0.996 | 5.7 | 23 | 94 | [0, 0, 0] | 469 | 585 / 585 |
| 15 | salvage | 7,868 | incumbent 7,820 | +0.61% | 0.996 | 6.1 | 16 | 125 | [0, 0, 0] | 565 | 704 / 704 |
| 15 | continuation | 7,728 | incumbent 7,687 | +0.54% | 0.996 | 6.1 | 16 | 125 | [0, 0, 0] | 565 | 704 / 704 |
| 15 | continuation_landed | 7,728 | incumbent 7,687 | +0.54% | 0.996 | 6.1 | 16 | 125 | [0, 0, 0] | 565 | 704 / 704 |
| 17 | salvage | 8,861 | incumbent 8,813 | +0.54% | 0.996 | 6.1 | 39 | 94 | [0, 0, 0] | 533 | 665 / 665 |
| 17 | continuation | 8,729 | incumbent 8,687 | +0.48% | 0.996 | 6.1 | 39 | 94 | [0, 0, 0] | 533 | 665 / 665 |
| 17 | continuation_landed | 8,729 | incumbent 8,687 | +0.48% | 0.996 | 6.1 | 39 | 94 | [0, 0, 0] | 533 | 665 / 665 |
| 19 | salvage | 9,875 | incumbent 9,861 | +0.14% | 0.997 | 6.1 | 11 | 109 | [0, 0, 0] | 479 | 598 / 598 |
| 19 | continuation | 9,757 | incumbent 9,718 | +0.40% | 0.997 | 6.1 | 11 | 109 | [0, 0, 0] | 479 | 598 / 598 |
| 19 | continuation_landed | 9,757 | incumbent 9,718 | +0.40% | 0.997 | 6.1 | 11 | 109 | [0, 0, 0] | 479 | 598 / 598 |
| 23 | salvage | 11,984 | incumbent 11,917 | +0.57% | 0.995 | 12.5 | 55 | 78 | [0, 0, 0] | 532 | 663 / 663 |
| 23 | continuation | 11,852 | incumbent 11,767 | +0.73% | 0.995 | 12.5 | 55 | 78 | [0, 0, 0] | 532 | 663 / 663 |
| 23 | continuation_landed | 11,852 | incumbent 11,767 | +0.73% | 0.995 | 12.5 | 55 | 78 | [0, 0, 0] | 532 | 663 / 663 |
| 35 | salvage | 18,075 | incumbent 17,927 | +0.83% | 0.993 | 23.9 | 34 | 94 | [0, 0, 0] | 510 | 636 / 636 |
| 35 | continuation | 17,949 | incumbent 17,778 | +0.96% | 0.993 | 23.9 | 34 | 94 | [0, 0, 0] | 510 | 636 / 636 |
| 35 | continuation_landed | 17,949 | incumbent 17,778 | +0.96% | 0.993 | 23.9 | 34 | 94 | [0, 0, 0] | 510 | 636 / 636 |
| 47 | salvage | 24,061 | incumbent 23,910 | +0.63% | 0.995 | 24.7 | 41 | 94 | [0, 0, 0] | 539 | 673 / 673 |
| 47 | continuation | 23,928 | incumbent 23,755 | +0.73% | 0.995 | 24.7 | 41 | 94 | [0, 0, 0] | 539 | 673 / 673 |
| 47 | continuation_landed | 23,928 | incumbent 23,755 | +0.73% | 0.995 | 24.7 | 41 | 94 | [0, 0, 0] | 539 | 673 / 673 |
| 52 | salvage | 26,546 | incumbent 26,396 | +0.57% | 0.995 | 24.7 | 20 | 94 | [0, 0, 0] | 457 | 570 / 570 |
| 52 | continuation | 26,433 | incumbent 26,261 | +0.65% | 0.995 | 24.7 | 20 | 94 | [0, 0, 0] | 457 | 570 / 570 |
| 52 | continuation_landed | 26,433 | incumbent 26,261 | +0.65% | 0.995 | 24.7 | 20 | 94 | [0, 0, 0] | 457 | 570 / 570 |

### E_pallet_multiple (valid to W = 52; legacy 12-week: salvage -0.00%, continuation +0.00%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,239 | incumbent 6,239 | +0.00% | 1.000 | 0.0 | 91 | 130 | [0, None, 0] | 885 | 1,103 / 1,169 |
| 11 | continuation | 6,021 | incumbent 6,021 | +0.00% | 1.000 | 0.0 | 91 | 130 | [0, None, 0] | 885 | 1,103 / 1,169 |
| 11 | continuation_landed | 5,955 | incumbent 5,955 | +0.00% | 1.000 | 0.0 | 91 | 130 | [0, None, 0] | 885 | 1,103 / 1,169 |
| 13 | salvage | 7,332 | incumbent 7,331 | +0.02% | 1.000 | 0.0 | 84 | 130 | [0, 0, None] | 855 | 1,065 / 1,129 |
| 13 | continuation | 7,122 | incumbent 7,120 | +0.02% | 1.000 | 0.0 | 84 | 130 | [0, 0, None] | 855 | 1,065 / 1,129 |
| 13 | continuation_landed | 7,057 | incumbent 7,056 | +0.03% | 1.000 | 0.0 | 84 | 130 | [0, 0, None] | 855 | 1,065 / 1,129 |
| 15 | salvage | 8,408 | incumbent 8,400 | +0.09% | 0.999 | 1.4 | 85 | 130 | [0, 0, None] | 860 | 1,072 / 1,136 |
| 15 | continuation | 8,196 | incumbent 8,191 | +0.06% | 0.999 | 1.4 | 85 | 130 | [0, 0, None] | 860 | 1,072 / 1,136 |
| 15 | continuation_landed | 8,131 | incumbent 8,127 | +0.05% | 0.999 | 1.4 | 85 | 130 | [0, 0, None] | 860 | 1,072 / 1,136 |
| 17 | salvage | 9,476 | incumbent 9,469 | +0.08% | 0.999 | 1.4 | 149 | 65 | [0, None, None] | 855 | 1,066 / 1,130 |
| 17 | continuation | 9,266 | incumbent 9,261 | +0.06% | 0.999 | 1.4 | 149 | 65 | [0, None, None] | 855 | 1,066 / 1,130 |
| 17 | continuation_landed | 9,202 | incumbent 9,197 | +0.05% | 0.999 | 1.4 | 149 | 65 | [0, None, None] | 855 | 1,066 / 1,130 |
| 19 | salvage | 10,564 | incumbent 10,557 | +0.07% | 0.999 | 1.4 | 78 | 130 | [0, None, 0] | 830 | 1,035 / 1,097 |
| 19 | continuation | 10,360 | incumbent 10,354 | +0.05% | 0.999 | 1.4 | 78 | 130 | [0, None, 0] | 830 | 1,035 / 1,097 |
| 19 | continuation_landed | 10,297 | incumbent 10,293 | +0.04% | 0.999 | 1.4 | 78 | 130 | [0, None, 0] | 830 | 1,035 / 1,097 |
| 23 | salvage | 12,722 | incumbent 12,719 | +0.02% | 0.999 | 1.4 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 23 | continuation | 12,526 | incumbent 12,526 | -0.00% | 0.999 | 1.4 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 23 | continuation_landed | 12,466 | incumbent 12,467 | -0.01% | 0.999 | 1.4 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 35 | salvage | 19,108 | incumbent 19,106 | +0.01% | 1.000 | 1.4 | 133 | 65 | [None, None, 0] | 791 | 986 / 1,046 |
| 35 | continuation | 18,913 | incumbent 18,915 | -0.01% | 1.000 | 1.4 | 133 | 65 | [None, None, 0] | 791 | 986 / 1,046 |
| 35 | continuation_landed | 18,854 | incumbent 18,856 | -0.01% | 1.000 | 1.4 | 133 | 65 | [None, None, 0] | 791 | 986 / 1,046 |
| 47 | salvage | 25,476 | incumbent 25,484 | -0.03% | 1.000 | 2.1 | 137 | 65 | [None, None, 0] | 811 | 1,010 / 1,071 |
| 47 | continuation | 25,277 | incumbent 25,285 | -0.03% | 1.000 | 2.1 | 137 | 65 | [None, None, 0] | 811 | 1,010 / 1,071 |
| 47 | continuation_landed | 25,216 | incumbent 25,224 | -0.03% | 1.000 | 2.1 | 137 | 65 | [None, None, 0] | 811 | 1,010 / 1,071 |
| 52 | salvage | 28,106 | incumbent 28,199 | -0.33% | 1.000 | 2.1 | 101 | 64 | [None, None, 0] | 663 | 826 / 875 |
| 52 | continuation | 27,943 | incumbent 27,971 | -0.10% | 1.000 | 2.1 | 101 | 64 | [None, None, 0] | 663 | 826 / 875 |
| 52 | continuation_landed | 27,893 | incumbent 27,901 | -0.03% | 1.000 | 2.1 | 101 | 64 | [None, None, 0] | 663 | 826 / 875 |

### F_mov_two_skus (valid to W = 52; legacy 12-week: salvage +0.24%, continuation +0.28%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 12,113 | periodic:2 11,766 | +2.95% | 0.998 | 3.5 | 508 | 191 | [None, None, 0] | 2,795 | 3,474 / 3,474 |
| 11 | continuation | 11,435 | periodic:2 11,311 | +1.10% | 0.998 | 3.5 | 508 | 191 | [None, None, 0] | 2,795 | 3,474 / 3,474 |
| 11 | continuation_landed | 11,435 | periodic:2 11,311 | +1.10% | 0.998 | 3.5 | 508 | 191 | [None, None, 0] | 2,795 | 3,474 / 3,474 |
| 13 | salvage | 14,266 | periodic:2 13,812 | +3.29% | 0.996 | 9.2 | 485 | 259 | [0, None, 0] | 2,977 | 3,696 / 3,696 |
| 13 | continuation | 13,547 | periodic:2 13,360 | +1.40% | 0.996 | 9.2 | 485 | 259 | [0, None, 0] | 2,977 | 3,696 / 3,696 |
| 13 | continuation_landed | 13,547 | periodic:2 13,360 | +1.40% | 0.996 | 9.2 | 485 | 259 | [0, None, 0] | 2,977 | 3,696 / 3,696 |
| 15 | salvage | 16,200 | periodic:2 15,828 | +2.35% | 0.996 | 11.2 | 499 | 139 | [None, None, 0] | 2,553 | 3,175 / 3,175 |
| 15 | continuation | 15,578 | periodic:2 15,380 | +1.29% | 0.996 | 11.2 | 499 | 139 | [None, None, 0] | 2,553 | 3,175 / 3,175 |
| 15 | continuation_landed | 15,578 | periodic:2 15,380 | +1.29% | 0.996 | 11.2 | 499 | 139 | [None, None, 0] | 2,553 | 3,175 / 3,175 |
| 17 | salvage | 18,175 | periodic:2 17,878 | +1.66% | 0.997 | 11.2 | 368 | 188 | [None, None, 0] | 2,225 | 2,769 / 2,769 |
| 17 | continuation | 17,631 | periodic:2 17,437 | +1.11% | 0.997 | 11.2 | 368 | 188 | [None, None, 0] | 2,225 | 2,769 / 2,769 |
| 17 | continuation_landed | 17,631 | periodic:2 17,437 | +1.11% | 0.997 | 11.2 | 368 | 188 | [None, None, 0] | 2,225 | 2,769 / 2,769 |
| 19 | salvage | 20,294 | periodic:2 19,910 | +1.93% | 0.997 | 11.2 | 483 | 149 | [None, 0, None] | 2,530 | 3,147 / 3,147 |
| 19 | continuation | 19,677 | periodic:2 19,470 | +1.07% | 0.997 | 11.2 | 483 | 149 | [None, 0, None] | 2,530 | 3,147 / 3,147 |
| 19 | continuation_landed | 19,677 | periodic:2 19,470 | +1.07% | 0.997 | 11.2 | 483 | 149 | [None, 0, None] | 2,530 | 3,147 / 3,147 |
| 23 | salvage | 24,335 | periodic:2 24,003 | +1.38% | 0.998 | 11.2 | 461 | 131 | [None, None, 0] | 2,371 | 2,951 / 2,951 |
| 23 | continuation | 23,755 | periodic:2 23,555 | +0.85% | 0.998 | 11.2 | 461 | 131 | [None, None, 0] | 2,371 | 2,951 / 2,951 |
| 23 | continuation_landed | 23,755 | periodic:2 23,555 | +0.85% | 0.998 | 11.2 | 461 | 131 | [None, None, 0] | 2,371 | 2,951 / 2,951 |
| 35 | salvage | 36,507 | periodic:2 36,021 | +1.35% | 0.997 | 19.8 | 383 | 291 | [0, None, 0] | 2,699 | 3,355 / 3,355 |
| 35 | continuation | 35,850 | periodic:2 35,555 | +0.83% | 0.997 | 19.8 | 383 | 291 | [0, None, 0] | 2,699 | 3,355 / 3,355 |
| 35 | continuation_landed | 35,850 | periodic:2 35,555 | +0.83% | 0.997 | 19.8 | 383 | 291 | [0, None, 0] | 2,699 | 3,355 / 3,355 |
| 47 | salvage | 48,231 | periodic:2 48,127 | +0.22% | 0.998 | 20.2 | 338 | 0 | [None, None, None] | 1,353 | 1,687 / 1,687 |
| 47 | continuation | 47,897 | periodic:2 47,664 | +0.49% | 0.998 | 20.2 | 338 | 0 | [None, None, None] | 1,353 | 1,687 / 1,687 |
| 47 | continuation_landed | 47,897 | periodic:2 47,664 | +0.49% | 0.998 | 20.2 | 338 | 0 | [None, None, None] | 1,353 | 1,687 / 1,687 |
| 52 | salvage | 53,899 | periodic:2 52,929 | +1.83% | 0.998 | 25.0 | 593 | 280 | [None, 0, 0] | 3,493 | 4,337 / 4,337 |
| 52 | continuation | 53,054 | periodic:2 52,657 | +0.75% | 0.998 | 25.0 | 593 | 280 | [None, 0, 0] | 3,493 | 4,337 / 4,337 |
| 52 | continuation_landed | 53,054 | periodic:2 52,657 | +0.75% | 0.998 | 25.0 | 593 | 280 | [None, 0, 0] | 3,493 | 4,337 / 4,337 |

### G_freight_tiers (valid to W = 52; legacy 12-week: salvage -10.01%, continuation -0.41%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 16,591 | economic_lot 16,720 | -0.77% | 1.000 | 0.0 | 1176 | 642 | [0, None, None] | 7,270 | 8,966 / 10,495 |
| 11 | continuation | 14,895 | economic_lot 14,837 | +0.39% | 1.000 | 0.0 | 1176 | 642 | [0, None, None] | 7,270 | 8,966 / 10,495 |
| 11 | continuation_landed | 13,366 | economic_lot 13,211 | +1.18% | 1.000 | 0.0 | 1176 | 642 | [0, None, None] | 7,270 | 8,966 / 10,495 |
| 13 | salvage | 18,240 | economic_lot 18,375 | -0.73% | 1.000 | 0.0 | 1416 | 0 | [None, None, None] | 5,665 | 7,009 / 8,200 |
| 13 | continuation | 16,896 | economic_lot 16,838 | +0.35% | 1.000 | 0.0 | 1416 | 0 | [None, None, None] | 5,665 | 7,009 / 8,200 |
| 13 | continuation_landed | 15,705 | economic_lot 15,532 | +1.11% | 1.000 | 0.0 | 1416 | 0 | [None, None, None] | 5,665 | 7,009 / 8,200 |
| 15 | salvage | 19,857 | economic_lot 19,998 | -0.70% | 1.000 | 0.0 | 1020 | 0 | [None, None, None] | 4,080 | 5,061 / 5,919 |
| 15 | continuation | 18,875 | economic_lot 18,818 | +0.31% | 1.000 | 0.0 | 1020 | 0 | [None, None, None] | 4,080 | 5,061 / 5,919 |
| 15 | continuation_landed | 18,018 | economic_lot 17,829 | +1.06% | 1.000 | 0.0 | 1020 | 0 | [None, None, None] | 4,080 | 5,061 / 5,919 |
| 17 | salvage | 21,478 | economic_lot 21,625 | -0.68% | 1.000 | 0.0 | 620 | 0 | [None, None, None] | 2,480 | 3,084 / 3,605 |
| 17 | continuation | 20,873 | economic_lot 20,816 | +0.28% | 1.000 | 0.0 | 620 | 0 | [None, None, None] | 2,480 | 3,084 / 3,605 |
| 17 | continuation_landed | 20,353 | economic_lot 20,147 | +1.02% | 1.000 | 0.0 | 620 | 0 | [None, None, None] | 2,480 | 3,084 / 3,605 |
| 19 | salvage | 25,632 | economic_lot 23,231 | +10.34% | 0.998 | 8.7 | 231 | 1246 | [None, 0, 0] | 5,910 | 7,283 / 8,531 |
| 19 | continuation | 24,259 | economic_lot 22,800 | +6.40% | 0.998 | 8.7 | 231 | 1246 | [None, 0, 0] | 5,910 | 7,283 / 8,531 |
| 19 | continuation_landed | 23,011 | economic_lot 22,449 | +2.50% | 0.998 | 8.7 | 231 | 1246 | [None, 0, 0] | 5,910 | 7,283 / 8,531 |
| 23 | salvage | 30,167 | economic_lot 30,982 | -2.63% | 0.998 | 8.7 | 1255 | 0 | [None, None, None] | 5,021 | 6,220 / 7,279 |
| 23 | continuation | 28,969 | economic_lot 29,370 | -1.37% | 0.998 | 8.7 | 1255 | 0 | [None, None, None] | 5,021 | 6,220 / 7,279 |
| 23 | continuation_landed | 27,910 | economic_lot 27,867 | +0.15% | 0.998 | 8.7 | 1255 | 0 | [None, None, None] | 5,021 | 6,220 / 7,279 |
| 35 | salvage | 43,779 | economic_lot 45,568 | -3.93% | 0.998 | 17.1 | 771 | 0 | [None, None, None] | 3,085 | 3,835 / 4,516 |
| 35 | continuation | 43,029 | economic_lot 44,103 | -2.43% | 0.998 | 17.1 | 771 | 0 | [None, None, None] | 3,085 | 3,835 / 4,516 |
| 35 | continuation_landed | 42,348 | economic_lot 42,583 | -0.55% | 0.998 | 17.1 | 771 | 0 | [None, None, None] | 3,085 | 3,835 / 4,516 |
| 47 | salvage | 58,687 | economic_lot 60,213 | -2.53% | 0.998 | 17.1 | 387 | 648 | [None, 0, None] | 4,142 | 5,106 / 6,035 |
| 47 | continuation | 57,723 | economic_lot 58,896 | -1.99% | 0.998 | 17.1 | 387 | 648 | [None, 0, None] | 4,142 | 5,106 / 6,035 |
| 47 | continuation_landed | 56,794 | economic_lot 57,487 | -1.21% | 0.998 | 17.1 | 387 | 648 | [None, 0, None] | 4,142 | 5,106 / 6,035 |
| 52 | salvage | 65,101 | economic_lot 65,440 | -0.52% | 0.998 | 17.1 | 1262 | 0 | [None, None, None] | 5,046 | 6,248 / 7,371 |
| 52 | continuation | 63,899 | economic_lot 64,438 | -0.84% | 0.998 | 17.1 | 1262 | 0 | [None, None, None] | 5,046 | 6,248 / 7,371 |
| 52 | continuation_landed | 62,776 | economic_lot 63,421 | -1.02% | 0.998 | 17.1 | 1262 | 0 | [None, None, None] | 5,046 | 6,248 / 7,371 |

### H_per_pallet_freight (valid to W = 52; legacy 12-week: salvage -3.73%, continuation -2.29%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,658 | periodic:2 6,826 | -2.47% | 1.000 | 0.0 | 249 | 0 | [None, None, None] | 998 | 1,242 / 1,392 |
| 11 | continuation | 6,414 | periodic:2 6,610 | -2.97% | 1.000 | 0.0 | 249 | 0 | [None, None, None] | 998 | 1,242 / 1,392 |
| 11 | continuation_landed | 6,263 | periodic:2 6,448 | -2.86% | 1.000 | 0.0 | 249 | 0 | [None, None, None] | 998 | 1,242 / 1,392 |
| 13 | salvage | 7,682 | periodic:2 8,027 | -4.30% | 1.000 | 0.0 | 112 | 51 | [0, None, 0] | 651 | 811 / 910 |
| 13 | continuation | 7,521 | periodic:2 7,810 | -3.69% | 1.000 | 0.0 | 112 | 51 | [0, None, 0] | 651 | 811 / 910 |
| 13 | continuation_landed | 7,422 | periodic:2 7,645 | -2.92% | 1.000 | 0.0 | 112 | 51 | [0, None, 0] | 651 | 811 / 910 |
| 15 | salvage | 8,843 | periodic:2 9,162 | -3.48% | 1.000 | 0.0 | 35 | 131 | [0, 0, 0] | 663 | 826 / 930 |
| 15 | continuation | 8,679 | periodic:2 8,951 | -3.03% | 1.000 | 0.0 | 35 | 131 | [0, 0, 0] | 663 | 826 / 930 |
| 15 | continuation_landed | 8,575 | periodic:2 8,791 | -2.46% | 1.000 | 0.0 | 35 | 131 | [0, 0, 0] | 663 | 826 / 930 |
| 17 | salvage | 9,970 | periodic:2 10,293 | -3.14% | 1.000 | 0.0 | 67 | 84 | [0, 0, None] | 605 | 755 / 852 |
| 17 | continuation | 9,821 | periodic:2 10,093 | -2.69% | 1.000 | 0.0 | 67 | 84 | [0, 0, None] | 605 | 755 / 852 |
| 17 | continuation_landed | 9,723 | periodic:2 9,942 | -2.20% | 1.000 | 0.0 | 67 | 84 | [0, 0, None] | 605 | 755 / 852 |
| 19 | salvage | 11,174 | periodic:2 11,559 | -3.33% | 0.998 | 4.6 | 85 | 67 | [None, 0, 0] | 608 | 759 / 858 |
| 19 | continuation | 11,024 | periodic:2 11,343 | -2.82% | 0.998 | 4.6 | 85 | 67 | [None, 0, 0] | 608 | 759 / 858 |
| 19 | continuation_landed | 10,924 | periodic:2 11,179 | -2.28% | 0.998 | 4.6 | 85 | 67 | [None, 0, 0] | 608 | 759 / 858 |
| 23 | salvage | 13,570 | periodic:2 13,931 | -2.59% | 0.998 | 4.6 | 143 | 64 | [0, 0, None] | 829 | 1,033 / 1,166 |
| 23 | continuation | 13,367 | periodic:2 13,709 | -2.50% | 0.998 | 4.6 | 143 | 64 | [0, 0, None] | 829 | 1,033 / 1,166 |
| 23 | continuation_landed | 13,234 | periodic:2 13,540 | -2.26% | 0.998 | 4.6 | 143 | 64 | [0, 0, None] | 829 | 1,033 / 1,166 |
| 35 | salvage | 20,450 | periodic:2 20,838 | -1.86% | 0.998 | 8.1 | 86 | 152 | [0, None, 0] | 951 | 1,185 / 1,338 |
| 35 | continuation | 20,216 | periodic:2 20,622 | -1.97% | 0.998 | 8.1 | 86 | 152 | [0, None, 0] | 951 | 1,185 / 1,338 |
| 35 | continuation_landed | 20,063 | periodic:2 20,460 | -1.94% | 0.998 | 8.1 | 86 | 152 | [0, None, 0] | 951 | 1,185 / 1,338 |
| 47 | salvage | 27,271 | periodic:2 27,796 | -1.89% | 0.997 | 15.5 | 195 | 65 | [0, 0, None] | 1,042 | 1,297 / 1,463 |
| 47 | continuation | 27,016 | periodic:2 27,578 | -2.04% | 0.997 | 15.5 | 195 | 65 | [0, 0, None] | 1,042 | 1,297 / 1,463 |
| 47 | continuation_landed | 26,850 | periodic:2 27,413 | -2.05% | 0.997 | 15.5 | 195 | 65 | [0, 0, None] | 1,042 | 1,297 / 1,463 |
| 52 | salvage | 29,856 | periodic:2 30,455 | -1.97% | 0.997 | 15.5 | 11 | 96 | [0, 0, 0] | 429 | 535 / 605 |
| 52 | continuation | 29,749 | periodic:2 30,353 | -1.99% | 0.997 | 15.5 | 11 | 96 | [0, 0, 0] | 429 | 535 / 605 |
| 52 | continuation_landed | 29,680 | periodic:2 30,277 | -1.97% | 0.997 | 15.5 | 11 | 96 | [0, 0, 0] | 429 | 535 / 605 |

### I_max_pallets_ftl_cap (valid to W = 52; legacy 12-week: salvage +0.53%, continuation +3.05%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 10,382 | economic_lot 9,814 | +5.78% | 1.000 | 0.0 | 370 | 148 | [0, None, None] | 2,073 | 2,568 / 4,008 |
| 11 | continuation | 9,887 | economic_lot 9,456 | +4.56% | 1.000 | 0.0 | 370 | 148 | [0, None, None] | 2,073 | 2,568 / 4,008 |
| 11 | continuation_landed | 8,447 | economic_lot 8,433 | +0.16% | 1.000 | 0.0 | 370 | 148 | [0, None, None] | 2,073 | 2,568 / 4,008 |
| 13 | salvage | 11,204 | economic_lot 10,632 | +5.38% | 1.000 | 0.0 | 315 | 0 | [None, None, None] | 1,261 | 1,565 / 2,441 |
| 13 | continuation | 10,901 | economic_lot 10,469 | +4.12% | 1.000 | 0.0 | 315 | 0 | [None, None, None] | 1,261 | 1,565 / 2,441 |
| 13 | continuation_landed | 10,025 | economic_lot 10,011 | +0.14% | 1.000 | 0.0 | 315 | 0 | [None, None, None] | 1,261 | 1,565 / 2,441 |
| 15 | salvage | 13,162 | economic_lot 13,171 | -0.07% | 1.000 | 0.0 | 412 | 0 | [None, None, None] | 1,646 | 2,045 / 3,189 |
| 15 | continuation | 12,763 | economic_lot 12,776 | -0.11% | 1.000 | 0.0 | 412 | 0 | [None, None, None] | 1,646 | 2,045 / 3,189 |
| 15 | continuation_landed | 11,620 | economic_lot 11,647 | -0.24% | 1.000 | 0.0 | 412 | 0 | [None, None, None] | 1,646 | 2,045 / 3,189 |
| 17 | salvage | 13,955 | economic_lot 13,964 | -0.06% | 1.000 | 0.0 | 215 | 0 | [None, None, None] | 860 | 1,072 / 1,669 |
| 17 | continuation | 13,744 | economic_lot 13,758 | -0.10% | 1.000 | 0.0 | 215 | 0 | [None, None, None] | 860 | 1,072 / 1,669 |
| 17 | continuation_landed | 13,147 | economic_lot 13,174 | -0.21% | 1.000 | 0.0 | 215 | 0 | [None, None, None] | 860 | 1,072 / 1,669 |
| 19 | salvage | 16,517 | economic_lot 16,522 | -0.03% | 1.000 | 0.0 | 306 | 145 | [None, None, 0] | 1,804 | 2,240 / 3,493 |
| 19 | continuation | 16,081 | economic_lot 16,090 | -0.06% | 1.000 | 0.0 | 306 | 145 | [None, None, 0] | 1,804 | 2,240 / 3,493 |
| 19 | continuation_landed | 14,828 | economic_lot 14,850 | -0.15% | 1.000 | 0.0 | 306 | 145 | [None, None, 0] | 1,804 | 2,240 / 3,493 |
| 23 | salvage | 19,882 | economic_lot 19,879 | +0.02% | 1.000 | 1.1 | 53 | 438 | [0, 0, 0] | 1,964 | 2,439 / 3,803 |
| 23 | continuation | 19,408 | economic_lot 19,410 | -0.01% | 1.000 | 1.1 | 53 | 438 | [0, 0, 0] | 1,964 | 2,439 / 3,803 |
| 23 | continuation_landed | 18,044 | economic_lot 18,060 | -0.09% | 1.000 | 1.1 | 53 | 438 | [0, 0, 0] | 1,964 | 2,439 / 3,803 |
| 35 | salvage | 28,084 | economic_lot 28,093 | -0.03% | 1.000 | 1.1 | 203 | 0 | [None, None, None] | 812 | 1,012 / 1,576 |
| 35 | continuation | 27,884 | economic_lot 27,903 | -0.07% | 1.000 | 1.1 | 203 | 0 | [None, None, None] | 812 | 1,012 / 1,576 |
| 35 | continuation_landed | 27,320 | economic_lot 27,367 | -0.17% | 1.000 | 1.1 | 203 | 0 | [None, None, None] | 812 | 1,012 / 1,576 |
| 47 | salvage | 38,368 | economic_lot 38,052 | +0.83% | 1.000 | 1.1 | 395 | 0 | [None, None, None] | 1,579 | 1,962 / 3,079 |
| 47 | continuation | 37,984 | economic_lot 37,721 | +0.70% | 1.000 | 1.1 | 395 | 0 | [None, None, None] | 1,579 | 1,962 / 3,079 |
| 47 | continuation_landed | 36,868 | economic_lot 36,778 | +0.24% | 1.000 | 1.1 | 395 | 0 | [None, None, None] | 1,579 | 1,962 / 3,079 |
| 52 | salvage | 42,078 | economic_lot 41,758 | +0.77% | 1.000 | 1.1 | 347 | 0 | [None, None, None] | 1,388 | 1,726 / 2,707 |
| 52 | continuation | 41,740 | economic_lot 41,472 | +0.64% | 1.000 | 1.1 | 347 | 0 | [None, None, None] | 1,388 | 1,726 / 2,707 |
| 52 | continuation_landed | 40,759 | economic_lot 40,662 | +0.24% | 1.000 | 1.1 | 347 | 0 | [None, None, None] | 1,388 | 1,726 / 2,707 |

### J_net60_cost_of_capital (valid to W = 52; legacy 12-week: salvage -11.06%, continuation -3.52%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,234 | periodic:2 6,850 | +5.60% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,397 / 5,555 |
| 11 | continuation | 6,283 | economic_lot 6,182 | +1.63% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,397 / 5,555 |
| 11 | continuation_landed | 6,124 | economic_lot 6,071 | +0.88% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,397 / 5,555 |
| 13 | salvage | 8,073 | periodic:2 8,044 | +0.37% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,436 / 4,566 |
| 13 | continuation | 7,271 | economic_lot 7,317 | -0.63% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,436 / 4,566 |
| 13 | continuation_landed | 7,141 | economic_lot 7,186 | -0.62% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,436 / 4,566 |
| 15 | salvage | 8,878 | economic_lot 8,948 | -0.78% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,497 / 3,599 |
| 15 | continuation | 8,232 | economic_lot 8,277 | -0.55% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,497 / 3,599 |
| 15 | continuation_landed | 8,130 | economic_lot 8,174 | -0.53% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,497 / 3,599 |
| 17 | salvage | 9,681 | economic_lot 9,751 | -0.72% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,545 / 2,619 |
| 17 | continuation | 9,200 | economic_lot 9,245 | -0.49% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,545 / 2,619 |
| 17 | continuation_landed | 9,126 | economic_lot 9,169 | -0.46% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,545 / 2,619 |
| 19 | salvage | 10,493 | economic_lot 10,564 | -0.68% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,565 / 1,610 |
| 19 | continuation | 10,190 | economic_lot 10,235 | -0.43% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,565 / 1,610 |
| 19 | continuation_landed | 10,145 | economic_lot 10,186 | -0.40% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,565 / 1,610 |
| 23 | salvage | 13,566 | economic_lot 13,565 | +0.01% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,094 / 5,238 |
| 23 | continuation | 12,658 | economic_lot 12,674 | -0.13% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,094 / 5,238 |
| 23 | continuation_landed | 12,514 | economic_lot 12,533 | -0.15% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,094 / 5,238 |
| 35 | salvage | 19,706 | economic_lot 19,713 | -0.03% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,595 / 4,725 |
| 35 | continuation | 18,882 | economic_lot 18,888 | -0.03% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,595 / 4,725 |
| 35 | continuation_landed | 18,752 | economic_lot 18,758 | -0.03% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,595 / 4,725 |
| 47 | salvage | 25,845 | economic_lot 25,850 | -0.02% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,135 / 4,251 |
| 47 | continuation | 25,096 | economic_lot 25,085 | +0.04% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,135 / 4,251 |
| 47 | continuation_landed | 24,980 | economic_lot 24,967 | +0.06% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,135 / 4,251 |
| 52 | salvage | 28,252 | economic_lot 27,857 | +1.42% | 1.000 | 0.0 | 355 | 328 | [0, None, None] | 2,730 | 3,339 / 3,435 |
| 52 | continuation | 27,643 | economic_lot 27,505 | +0.50% | 1.000 | 0.0 | 355 | 328 | [0, None, None] | 2,730 | 3,339 / 3,435 |
| 52 | continuation_landed | 27,547 | economic_lot 27,454 | +0.34% | 1.000 | 0.0 | 355 | 328 | [0, None, None] | 2,730 | 3,339 / 3,435 |

### K_deposit_early_cash (valid to W = 52; legacy 12-week: salvage -11.20%, continuation -3.64%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,246 | periodic:2 6,862 | +5.59% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,397 / 5,555 |
| 11 | continuation | 6,294 | economic_lot 6,190 | +1.69% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,397 / 5,555 |
| 11 | continuation_landed | 6,136 | economic_lot 6,079 | +0.94% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,397 / 5,555 |
| 13 | salvage | 8,085 | periodic:2 8,056 | +0.37% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,436 / 4,566 |
| 13 | continuation | 7,283 | economic_lot 7,329 | -0.64% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,436 / 4,566 |
| 13 | continuation_landed | 7,153 | economic_lot 7,198 | -0.62% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,436 / 4,566 |
| 15 | salvage | 8,890 | economic_lot 8,960 | -0.78% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,497 / 3,599 |
| 15 | continuation | 8,244 | economic_lot 8,290 | -0.56% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,497 / 3,599 |
| 15 | continuation_landed | 8,142 | economic_lot 8,186 | -0.54% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,497 / 3,599 |
| 17 | salvage | 9,692 | economic_lot 9,763 | -0.73% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,545 / 2,619 |
| 17 | continuation | 9,212 | economic_lot 9,257 | -0.49% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,545 / 2,619 |
| 17 | continuation_landed | 9,138 | economic_lot 9,181 | -0.47% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,545 / 2,619 |
| 19 | salvage | 10,505 | economic_lot 10,577 | -0.68% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,565 / 1,610 |
| 19 | continuation | 10,202 | economic_lot 10,247 | -0.44% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,565 / 1,610 |
| 19 | continuation_landed | 10,157 | economic_lot 10,199 | -0.41% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,565 / 1,610 |
| 23 | salvage | 13,580 | economic_lot 13,578 | +0.01% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,094 / 5,238 |
| 23 | continuation | 12,671 | economic_lot 12,687 | -0.13% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,094 / 5,238 |
| 23 | continuation_landed | 12,527 | economic_lot 12,546 | -0.15% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,094 / 5,238 |
| 35 | salvage | 19,719 | economic_lot 19,726 | -0.03% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,595 / 4,725 |
| 35 | continuation | 18,894 | economic_lot 18,900 | -0.03% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,595 / 4,725 |
| 35 | continuation_landed | 18,765 | economic_lot 18,771 | -0.03% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,595 / 4,725 |
| 47 | salvage | 25,858 | economic_lot 25,863 | -0.02% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,135 / 4,251 |
| 47 | continuation | 25,108 | economic_lot 25,097 | +0.04% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,135 / 4,251 |
| 47 | continuation_landed | 24,993 | economic_lot 24,979 | +0.05% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,135 / 4,251 |
| 52 | salvage | 28,265 | economic_lot 27,870 | +1.42% | 1.000 | 0.0 | 355 | 328 | [0, None, None] | 2,730 | 3,339 / 3,435 |
| 52 | continuation | 27,656 | economic_lot 27,518 | +0.50% | 1.000 | 0.0 | 355 | 328 | [0, None, None] | 2,730 | 3,339 / 3,435 |
| 52 | continuation_landed | 27,560 | economic_lot 27,467 | +0.34% | 1.000 | 0.0 | 355 | 328 | [0, None, None] | 2,730 | 3,339 / 3,435 |

### L_high_holding_rate (valid to W = 52; legacy 12-week: salvage -10.16%, continuation -4.74%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,306 | periodic:2 6,856 | +6.56% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,379 / 5,537 |
| 11 | continuation | 6,373 | economic_lot 6,332 | +0.65% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,379 / 5,537 |
| 11 | continuation_landed | 6,214 | economic_lot 6,177 | +0.60% | 1.000 | 0.0 | 462 | 649 | [0, None, 0] | 4,446 | 5,379 / 5,537 |
| 13 | salvage | 8,173 | periodic:2 8,048 | +1.55% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,424 / 4,554 |
| 13 | continuation | 7,382 | economic_lot 7,342 | +0.55% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,424 / 4,554 |
| 13 | continuation_landed | 7,253 | economic_lot 7,217 | +0.49% | 1.000 | 0.0 | 908 | 0 | [None, None, None] | 3,633 | 4,424 / 4,554 |
| 15 | salvage | 9,000 | economic_lot 8,910 | +1.01% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,490 / 3,591 |
| 15 | continuation | 8,361 | economic_lot 8,320 | +0.49% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,490 / 3,591 |
| 15 | continuation_landed | 8,259 | economic_lot 8,224 | +0.43% | 1.000 | 0.0 | 713 | 0 | [None, None, None] | 2,850 | 3,490 / 3,591 |
| 17 | salvage | 9,819 | economic_lot 9,725 | +0.96% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,541 / 2,615 |
| 17 | continuation | 9,342 | economic_lot 9,301 | +0.44% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,541 / 2,615 |
| 17 | continuation_landed | 9,268 | economic_lot 9,234 | +0.38% | 1.000 | 0.0 | 516 | 0 | [None, None, None] | 2,065 | 2,541 / 2,615 |
| 19 | salvage | 10,641 | economic_lot 10,545 | +0.92% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,564 / 1,609 |
| 19 | continuation | 10,340 | economic_lot 10,299 | +0.40% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,564 / 1,609 |
| 19 | continuation_landed | 10,295 | economic_lot 10,262 | +0.33% | 1.000 | 0.0 | 316 | 0 | [None, None, None] | 1,263 | 1,564 / 1,609 |
| 23 | salvage | 13,728 | economic_lot 13,462 | +1.97% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,079 / 5,223 |
| 23 | continuation | 12,835 | economic_lot 12,704 | +1.02% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,079 / 5,223 |
| 23 | continuation_landed | 12,690 | economic_lot 12,578 | +0.89% | 1.000 | 0.0 | 1046 | 0 | [None, None, None] | 4,186 | 5,079 / 5,223 |
| 35 | salvage | 19,964 | economic_lot 19,620 | +1.76% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,582 / 4,712 |
| 35 | continuation | 19,153 | economic_lot 19,022 | +0.68% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,582 / 4,712 |
| 35 | continuation_landed | 19,023 | economic_lot 18,925 | +0.52% | 1.000 | 0.0 | 943 | 0 | [None, None, None] | 3,771 | 4,582 / 4,712 |
| 47 | salvage | 26,188 | economic_lot 25,709 | +1.86% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,125 / 4,240 |
| 47 | continuation | 25,449 | economic_lot 25,274 | +0.69% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,125 / 4,240 |
| 47 | continuation_landed | 25,334 | economic_lot 25,205 | +0.51% | 1.000 | 0.0 | 847 | 0 | [None, None, None] | 3,386 | 4,125 / 4,240 |
| 52 | salvage | 28,346 | economic_lot 28,908 | -1.94% | 1.000 | 0.0 | 409 | 0 | [None, None, None] | 1,636 | 2,018 / 2,076 |
| 52 | continuation | 27,964 | economic_lot 28,077 | -0.40% | 1.000 | 0.0 | 409 | 0 | [None, None, None] | 1,636 | 2,018 / 2,076 |
| 52 | continuation_landed | 27,906 | economic_lot 27,933 | -0.10% | 1.000 | 0.0 | 409 | 0 | [None, None, None] | 1,636 | 2,018 / 2,076 |

### M_order_calendar_wednesday (valid to W = 52; legacy 12-week: salvage -0.54%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,407 | incumbent 6,256 | +2.42% | 0.948 | 57.6 | 167 | 151 | [0, 1, 1] | 1,268 | 1,578 / 1,578 |
| 11 | continuation | 6,097 | incumbent 6,039 | +0.96% | 0.948 | 57.6 | 167 | 151 | [0, 1, 1] | 1,268 | 1,578 / 1,578 |
| 11 | continuation_landed | 6,097 | incumbent 6,039 | +0.96% | 0.948 | 57.6 | 167 | 151 | [0, 1, 1] | 1,268 | 1,578 / 1,578 |
| 13 | salvage | 7,422 | incumbent 7,296 | +1.73% | 0.956 | 57.6 | 114 | 181 | [0, 0, 0] | 1,181 | 1,471 / 1,471 |
| 13 | continuation | 7,133 | incumbent 7,076 | +0.80% | 0.956 | 57.6 | 114 | 181 | [0, 0, 0] | 1,181 | 1,471 / 1,471 |
| 13 | continuation_landed | 7,133 | incumbent 7,076 | +0.80% | 0.956 | 57.6 | 114 | 181 | [0, 0, 0] | 1,181 | 1,471 / 1,471 |
| 15 | salvage | 8,424 | incumbent 8,289 | +1.63% | 0.962 | 57.6 | 100 | 196 | [0, 0, 0] | 1,182 | 1,471 / 1,471 |
| 15 | continuation | 8,135 | incumbent 8,076 | +0.73% | 0.962 | 57.6 | 100 | 196 | [0, 0, 0] | 1,182 | 1,471 / 1,471 |
| 15 | continuation_landed | 8,135 | incumbent 8,076 | +0.73% | 0.962 | 57.6 | 100 | 196 | [0, 0, 0] | 1,182 | 1,471 / 1,471 |
| 17 | salvage | 9,414 | incumbent 9,277 | +1.47% | 0.966 | 57.6 | 99 | 185 | [0, 0, 0] | 1,134 | 1,411 / 1,411 |
| 17 | continuation | 9,136 | incumbent 9,075 | +0.67% | 0.966 | 57.6 | 99 | 185 | [0, 0, 0] | 1,134 | 1,411 / 1,411 |
| 17 | continuation_landed | 9,136 | incumbent 9,075 | +0.67% | 0.966 | 57.6 | 99 | 185 | [0, 0, 0] | 1,134 | 1,411 / 1,411 |
| 19 | salvage | 10,435 | incumbent 10,349 | +0.83% | 0.970 | 57.6 | 83 | 192 | [0, 0, 0] | 1,100 | 1,370 / 1,370 |
| 19 | continuation | 10,165 | incumbent 10,136 | +0.29% | 0.970 | 57.6 | 83 | 192 | [0, 0, 0] | 1,100 | 1,370 / 1,370 |
| 19 | continuation_landed | 10,165 | incumbent 10,136 | +0.29% | 0.970 | 57.6 | 83 | 192 | [0, 0, 0] | 1,100 | 1,370 / 1,370 |
| 23 | salvage | 12,508 | incumbent 12,435 | +0.59% | 0.975 | 57.6 | 118 | 178 | [0, 0, 0] | 1,183 | 1,473 / 1,473 |
| 23 | continuation | 12,218 | incumbent 12,212 | +0.05% | 0.975 | 57.6 | 118 | 178 | [0, 0, 0] | 1,183 | 1,473 / 1,473 |
| 23 | continuation_landed | 12,218 | incumbent 12,212 | +0.05% | 0.975 | 57.6 | 118 | 178 | [0, 0, 0] | 1,183 | 1,473 / 1,473 |
| 35 | salvage | 18,525 | incumbent 18,470 | +0.30% | 0.983 | 57.6 | 97 | 198 | [0, 0, 0] | 1,178 | 1,466 / 1,466 |
| 35 | continuation | 18,237 | incumbent 18,253 | -0.09% | 0.983 | 57.6 | 97 | 198 | [0, 0, 0] | 1,178 | 1,466 / 1,466 |
| 35 | continuation_landed | 18,237 | incumbent 18,253 | -0.09% | 0.983 | 57.6 | 97 | 198 | [0, 0, 0] | 1,178 | 1,466 / 1,466 |
| 47 | salvage | 24,516 | incumbent 24,487 | +0.12% | 0.988 | 57.6 | 134 | 170 | [0, 0, 0] | 1,216 | 1,514 / 1,514 |
| 47 | continuation | 24,219 | incumbent 24,266 | -0.19% | 0.988 | 57.6 | 134 | 170 | [0, 0, 0] | 1,216 | 1,514 / 1,514 |
| 47 | continuation_landed | 24,219 | incumbent 24,266 | -0.19% | 0.988 | 57.6 | 134 | 170 | [0, 0, 0] | 1,216 | 1,514 / 1,514 |
| 52 | salvage | 27,002 | incumbent 26,979 | +0.09% | 0.989 | 57.6 | 91 | 189 | [0, 0, 0] | 1,120 | 1,394 / 1,394 |
| 52 | continuation | 26,728 | incumbent 26,773 | -0.17% | 0.989 | 57.6 | 91 | 189 | [0, 0, 0] | 1,120 | 1,394 / 1,394 |
| 52 | continuation_landed | 26,728 | incumbent 26,773 | -0.17% | 0.989 | 57.6 | 91 | 189 | [0, 0, 0] | 1,120 | 1,394 / 1,394 |

### N_long_lead_21_days (valid to W = 52; legacy 12-week: salvage -0.71%, continuation +0.42%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,106 | incumbent 6,039 | +1.10% | 0.982 | 19.6 | 24 | 291 | [0, 0, 0] | 1,258 | 1,566 / 1,566 |
| 11 | continuation | 5,798 | incumbent 5,723 | +1.31% | 0.982 | 19.6 | 24 | 291 | [0, 0, 0] | 1,258 | 1,566 / 1,566 |
| 11 | continuation_landed | 5,798 | incumbent 5,723 | +1.31% | 0.982 | 19.6 | 24 | 291 | [0, 0, 0] | 1,258 | 1,566 / 1,566 |
| 13 | salvage | 7,187 | incumbent 7,099 | +1.24% | 0.982 | 23.6 | 26 | 303 | [0, 0, 0] | 1,314 | 1,634 / 1,634 |
| 13 | continuation | 6,866 | incumbent 6,780 | +1.28% | 0.982 | 23.6 | 26 | 303 | [0, 0, 0] | 1,314 | 1,634 / 1,634 |
| 13 | continuation_landed | 6,866 | incumbent 6,780 | +1.28% | 0.982 | 23.6 | 26 | 303 | [0, 0, 0] | 1,314 | 1,634 / 1,634 |
| 15 | salvage | 8,170 | incumbent 8,091 | +0.98% | 0.984 | 23.6 | 25 | 288 | [0, 0, 0] | 1,253 | 1,559 / 1,559 |
| 15 | continuation | 7,864 | incumbent 7,779 | +1.10% | 0.984 | 23.6 | 25 | 288 | [0, 0, 0] | 1,253 | 1,559 / 1,559 |
| 15 | continuation_landed | 7,864 | incumbent 7,779 | +1.10% | 0.984 | 23.6 | 25 | 288 | [0, 0, 0] | 1,253 | 1,559 / 1,559 |
| 17 | salvage | 9,163 | incumbent 9,076 | +0.96% | 0.986 | 23.6 | 27 | 277 | [0, 0, 0] | 1,220 | 1,518 / 1,518 |
| 17 | continuation | 8,865 | incumbent 8,778 | +0.99% | 0.986 | 23.6 | 27 | 277 | [0, 0, 0] | 1,220 | 1,518 / 1,518 |
| 17 | continuation_landed | 8,865 | incumbent 8,778 | +0.99% | 0.986 | 23.6 | 27 | 277 | [0, 0, 0] | 1,220 | 1,518 / 1,518 |
| 19 | salvage | 10,301 | incumbent 10,140 | +1.58% | 0.982 | 34.6 | 25 | 303 | [0, 0, 0] | 1,314 | 1,635 / 1,635 |
| 19 | continuation | 9,980 | incumbent 9,829 | +1.53% | 0.982 | 34.6 | 25 | 303 | [0, 0, 0] | 1,314 | 1,635 / 1,635 |
| 19 | continuation_landed | 9,980 | incumbent 9,829 | +1.53% | 0.982 | 34.6 | 25 | 303 | [0, 0, 0] | 1,314 | 1,635 / 1,635 |
| 23 | salvage | 12,366 | incumbent 12,257 | +0.89% | 0.984 | 37.2 | 21 | 307 | [0, 0, 0] | 1,313 | 1,633 / 1,633 |
| 23 | continuation | 12,045 | incumbent 11,930 | +0.96% | 0.984 | 37.2 | 21 | 307 | [0, 0, 0] | 1,313 | 1,633 / 1,633 |
| 23 | continuation_landed | 12,045 | incumbent 11,930 | +0.96% | 0.984 | 37.2 | 21 | 307 | [0, 0, 0] | 1,313 | 1,633 / 1,633 |
| 35 | salvage | 18,424 | incumbent 18,298 | +0.69% | 0.987 | 44.2 | 40 | 284 | [0, 0, 0] | 1,295 | 1,611 / 1,611 |
| 35 | continuation | 18,108 | incumbent 17,979 | +0.72% | 0.987 | 44.2 | 40 | 284 | [0, 0, 0] | 1,295 | 1,611 / 1,611 |
| 35 | continuation_landed | 18,108 | incumbent 17,979 | +0.72% | 0.987 | 44.2 | 40 | 284 | [0, 0, 0] | 1,295 | 1,611 / 1,611 |
| 47 | salvage | 24,495 | incumbent 24,302 | +0.79% | 0.988 | 56.9 | 69 | 258 | [0, 0, 0] | 1,307 | 1,626 / 1,626 |
| 47 | continuation | 24,176 | incumbent 23,983 | +0.80% | 0.988 | 56.9 | 69 | 258 | [0, 0, 0] | 1,307 | 1,626 / 1,626 |
| 47 | continuation_landed | 24,176 | incumbent 23,983 | +0.80% | 0.988 | 56.9 | 69 | 258 | [0, 0, 0] | 1,307 | 1,626 / 1,626 |
| 52 | salvage | 26,977 | incumbent 26,791 | +0.69% | 0.989 | 56.9 | 23 | 280 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 52 | continuation | 26,680 | incumbent 26,488 | +0.72% | 0.989 | 56.9 | 23 | 280 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 52 | continuation_landed | 26,680 | incumbent 26,488 | +0.72% | 0.989 | 56.9 | 23 | 280 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |

### O_low_opening_stock (valid to W = 52; legacy 12-week: salvage +0.46%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,457 | reorder_point 6,399 | +0.91% | 0.924 | 83.9 | 101 | 68 | [0, None, 0] | 674 | 840 / 840 |
| 11 | continuation | 6,291 | reorder_point 6,285 | +0.10% | 0.924 | 83.9 | 101 | 68 | [0, None, 0] | 674 | 840 / 840 |
| 11 | continuation_landed | 6,291 | reorder_point 6,285 | +0.10% | 0.924 | 83.9 | 101 | 68 | [0, None, 0] | 674 | 840 / 840 |
| 13 | salvage | 7,443 | reorder_point 7,449 | -0.08% | 0.936 | 83.9 | 28 | 93 | [0, 0, 0] | 484 | 604 / 604 |
| 13 | continuation | 7,323 | reorder_point 7,332 | -0.13% | 0.936 | 83.9 | 28 | 93 | [0, 0, 0] | 484 | 604 / 604 |
| 13 | continuation_landed | 7,323 | reorder_point 7,332 | -0.13% | 0.936 | 83.9 | 28 | 93 | [0, 0, 0] | 484 | 604 / 604 |
| 15 | salvage | 8,432 | reorder_point 8,445 | -0.16% | 0.944 | 83.9 | 20 | 91 | [0, 0, 0] | 445 | 555 / 555 |
| 15 | continuation | 8,321 | reorder_point 8,332 | -0.13% | 0.944 | 83.9 | 20 | 91 | [0, 0, 0] | 445 | 555 / 555 |
| 15 | continuation_landed | 8,321 | reorder_point 8,332 | -0.13% | 0.944 | 83.9 | 20 | 91 | [0, 0, 0] | 445 | 555 / 555 |
| 17 | salvage | 9,470 | reorder_point 9,436 | +0.36% | 0.951 | 83.9 | 45 | 99 | [0, 0, None] | 576 | 718 / 718 |
| 17 | continuation | 9,328 | reorder_point 9,332 | -0.04% | 0.951 | 83.9 | 45 | 99 | [0, 0, None] | 576 | 718 / 718 |
| 17 | continuation_landed | 9,328 | reorder_point 9,332 | -0.04% | 0.951 | 83.9 | 45 | 99 | [0, 0, None] | 576 | 718 / 718 |
| 19 | salvage | 10,533 | reorder_point 10,509 | +0.23% | 0.954 | 87.8 | 45 | 105 | [0, 0, 0] | 599 | 747 / 747 |
| 19 | continuation | 10,385 | reorder_point 10,396 | -0.10% | 0.954 | 87.8 | 45 | 105 | [0, 0, 0] | 599 | 747 / 747 |
| 19 | continuation_landed | 10,385 | reorder_point 10,396 | -0.10% | 0.954 | 87.8 | 45 | 105 | [0, 0, 0] | 599 | 747 / 747 |
| 23 | salvage | 12,606 | reorder_point 12,568 | +0.30% | 0.961 | 90.6 | 93 | 60 | [0, 0, None] | 612 | 763 / 763 |
| 23 | continuation | 12,455 | reorder_point 12,449 | +0.05% | 0.961 | 90.6 | 93 | 60 | [0, 0, None] | 612 | 763 / 763 |
| 23 | continuation_landed | 12,455 | reorder_point 12,449 | +0.05% | 0.961 | 90.6 | 93 | 60 | [0, 0, None] | 612 | 763 / 763 |
| 35 | salvage | 18,673 | reorder_point 18,608 | +0.35% | 0.972 | 96.1 | 54 | 110 | [0, None, 0] | 654 | 815 / 815 |
| 35 | continuation | 18,512 | reorder_point 18,492 | +0.11% | 0.972 | 96.1 | 54 | 110 | [0, None, 0] | 654 | 815 / 815 |
| 35 | continuation_landed | 18,512 | reorder_point 18,492 | +0.11% | 0.972 | 96.1 | 54 | 110 | [0, None, 0] | 654 | 815 / 815 |
| 47 | salvage | 24,693 | reorder_point 24,621 | +0.29% | 0.978 | 102.4 | 34 | 122 | [0, 0, 0] | 624 | 779 / 779 |
| 47 | continuation | 24,539 | reorder_point 24,502 | +0.15% | 0.978 | 102.4 | 34 | 122 | [0, 0, 0] | 624 | 779 / 779 |
| 47 | continuation_landed | 24,539 | reorder_point 24,502 | +0.15% | 0.978 | 102.4 | 34 | 122 | [0, 0, 0] | 624 | 779 / 779 |
| 52 | salvage | 27,207 | reorder_point 27,114 | +0.34% | 0.980 | 102.4 | 44 | 127 | [0, 0, 0] | 682 | 850 / 850 |
| 52 | continuation | 27,039 | reorder_point 27,006 | +0.12% | 0.980 | 102.4 | 44 | 127 | [0, 0, 0] | 682 | 850 / 850 |
| 52 | continuation_landed | 27,039 | reorder_point 27,006 | +0.12% | 0.980 | 102.4 | 44 | 127 | [0, 0, 0] | 682 | 850 / 850 |

### P_high_opening_stock (valid to W = 52; legacy 12-week: salvage +0.29%, continuation +0.39%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,795 | reorder_point 5,786 | +0.14% | 0.993 | 7.6 | 56 | 64 | [0, 0, 0] | 481 | 601 / 601 |
| 11 | continuation | 5,675 | reorder_point 5,673 | +0.05% | 0.993 | 7.6 | 56 | 64 | [0, 0, 0] | 481 | 601 / 601 |
| 11 | continuation_landed | 5,675 | reorder_point 5,673 | +0.05% | 0.993 | 7.6 | 56 | 64 | [0, 0, 0] | 481 | 601 / 601 |
| 13 | salvage | 6,819 | reorder_point 6,837 | -0.26% | 0.994 | 8.4 | 9 | 95 | [0, 0, 0] | 416 | 519 / 519 |
| 13 | continuation | 6,716 | reorder_point 6,720 | -0.06% | 0.994 | 8.4 | 9 | 95 | [0, 0, 0] | 416 | 519 / 519 |
| 13 | continuation_landed | 6,716 | reorder_point 6,720 | -0.06% | 0.994 | 8.4 | 9 | 95 | [0, 0, 0] | 416 | 519 / 519 |
| 15 | salvage | 7,841 | reorder_point 7,833 | +0.11% | 0.994 | 9.7 | 21 | 94 | [0, 0, 0] | 462 | 576 / 576 |
| 15 | continuation | 7,727 | reorder_point 7,720 | +0.09% | 0.994 | 9.7 | 21 | 94 | [0, 0, 0] | 462 | 576 / 576 |
| 15 | continuation_landed | 7,727 | reorder_point 7,720 | +0.09% | 0.994 | 9.7 | 21 | 94 | [0, 0, 0] | 462 | 576 / 576 |
| 17 | salvage | 8,935 | reorder_point 8,823 | +1.26% | 0.992 | 13.6 | 48 | 126 | [0, 0, 0] | 694 | 865 / 865 |
| 17 | continuation | 8,764 | reorder_point 8,719 | +0.51% | 0.992 | 13.6 | 48 | 126 | [0, 0, 0] | 694 | 865 / 865 |
| 17 | continuation_landed | 8,764 | reorder_point 8,719 | +0.51% | 0.992 | 13.6 | 48 | 126 | [0, 0, 0] | 694 | 865 / 865 |
| 19 | salvage | 9,975 | reorder_point 9,896 | +0.79% | 0.990 | 18.6 | 50 | 99 | [0, 0, 0] | 596 | 743 / 743 |
| 19 | continuation | 9,828 | reorder_point 9,783 | +0.45% | 0.990 | 18.6 | 50 | 99 | [0, 0, 0] | 596 | 743 / 743 |
| 19 | continuation_landed | 9,828 | reorder_point 9,783 | +0.45% | 0.990 | 18.6 | 50 | 99 | [0, 0, 0] | 596 | 743 / 743 |
| 23 | salvage | 12,022 | reorder_point 11,956 | +0.55% | 0.991 | 21.8 | 56 | 71 | [None, 0, 0] | 509 | 635 / 635 |
| 23 | continuation | 11,895 | reorder_point 11,836 | +0.50% | 0.991 | 21.8 | 56 | 71 | [None, 0, 0] | 509 | 635 / 635 |
| 23 | continuation_landed | 11,895 | reorder_point 11,836 | +0.50% | 0.991 | 21.8 | 56 | 71 | [None, 0, 0] | 509 | 635 / 635 |
| 35 | salvage | 18,177 | reorder_point 17,995 | +1.01% | 0.990 | 34.5 | 64 | 103 | [0, None, 0] | 668 | 832 / 832 |
| 35 | continuation | 18,012 | reorder_point 17,880 | +0.74% | 0.990 | 34.5 | 64 | 103 | [0, None, 0] | 668 | 832 / 832 |
| 35 | continuation_landed | 18,012 | reorder_point 17,880 | +0.74% | 0.990 | 34.5 | 64 | 103 | [0, None, 0] | 668 | 832 / 832 |
| 47 | salvage | 24,340 | reorder_point 24,008 | +1.38% | 0.991 | 40.8 | 167 | 126 | [0, 0, None] | 1,175 | 1,461 / 1,461 |
| 47 | continuation | 24,054 | reorder_point 23,889 | +0.69% | 0.991 | 40.8 | 167 | 126 | [0, 0, None] | 1,175 | 1,461 / 1,461 |
| 47 | continuation_landed | 24,054 | reorder_point 23,889 | +0.69% | 0.991 | 40.8 | 167 | 126 | [0, 0, None] | 1,175 | 1,461 / 1,461 |
| 52 | salvage | 26,717 | reorder_point 26,502 | +0.81% | 0.992 | 40.8 | 25 | 144 | [0, 0, 0] | 678 | 845 / 845 |
| 52 | continuation | 26,550 | reorder_point 26,394 | +0.59% | 0.992 | 40.8 | 25 | 144 | [0, 0, 0] | 678 | 845 / 845 |
| 52 | continuation_landed | 26,550 | reorder_point 26,394 | +0.59% | 0.992 | 40.8 | 25 | 144 | [0, 0, 0] | 678 | 845 / 845 |

### Q_volatile_demand_high_target (valid to W = 52; legacy 12-week: salvage +0.85%, continuation +1.08%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,969 | incumbent 5,971 | -0.03% | 0.988 | 14.1 | 112 | 69 | [0, 0, 0] | 721 | 899 / 899 |
| 11 | continuation | 5,791 | incumbent 5,793 | -0.04% | 0.988 | 14.1 | 112 | 69 | [0, 0, 0] | 721 | 899 / 899 |
| 11 | continuation_landed | 5,791 | incumbent 5,793 | -0.04% | 0.988 | 14.1 | 112 | 69 | [0, 0, 0] | 721 | 899 / 899 |
| 13 | salvage | 7,051 | incumbent 7,052 | -0.02% | 0.990 | 14.1 | 80 | 103 | [0, 0, 0] | 733 | 914 / 914 |
| 13 | continuation | 6,870 | incumbent 6,872 | -0.03% | 0.990 | 14.1 | 80 | 103 | [0, 0, 0] | 733 | 914 / 914 |
| 13 | continuation_landed | 6,870 | incumbent 6,872 | -0.03% | 0.990 | 14.1 | 80 | 103 | [0, 0, 0] | 733 | 914 / 914 |
| 15 | salvage | 7,973 | incumbent 7,975 | -0.02% | 0.991 | 14.1 | 88 | 86 | [0, 0, 0] | 698 | 870 / 870 |
| 15 | continuation | 7,801 | incumbent 7,803 | -0.03% | 0.991 | 14.1 | 88 | 86 | [0, 0, 0] | 698 | 870 / 870 |
| 15 | continuation_landed | 7,801 | incumbent 7,803 | -0.03% | 0.991 | 14.1 | 88 | 86 | [0, 0, 0] | 698 | 870 / 870 |
| 17 | salvage | 8,895 | incumbent 8,883 | +0.14% | 0.992 | 14.1 | 102 | 48 | [0, 0, None] | 599 | 747 / 747 |
| 17 | continuation | 8,748 | incumbent 8,747 | +0.01% | 0.992 | 14.1 | 102 | 48 | [0, 0, None] | 599 | 747 / 747 |
| 17 | continuation_landed | 8,748 | incumbent 8,747 | +0.01% | 0.992 | 14.1 | 102 | 48 | [0, 0, None] | 599 | 747 / 747 |
| 19 | salvage | 10,054 | incumbent 10,053 | +0.01% | 0.986 | 26.0 | 76 | 102 | [0, 0, 0] | 712 | 888 / 888 |
| 19 | continuation | 9,878 | incumbent 9,877 | +0.01% | 0.986 | 26.0 | 76 | 102 | [0, 0, 0] | 712 | 888 / 888 |
| 19 | continuation_landed | 9,878 | incumbent 9,877 | +0.01% | 0.986 | 26.0 | 76 | 102 | [0, 0, 0] | 712 | 888 / 888 |
| 23 | salvage | 12,087 | incumbent 12,086 | +0.01% | 0.989 | 26.0 | 84 | 99 | [0, 0, 0] | 732 | 913 / 913 |
| 23 | continuation | 11,907 | incumbent 11,906 | +0.01% | 0.989 | 26.0 | 84 | 99 | [0, 0, 0] | 732 | 913 / 913 |
| 23 | continuation_landed | 11,907 | incumbent 11,906 | +0.01% | 0.989 | 26.0 | 84 | 99 | [0, 0, 0] | 732 | 913 / 913 |
| 35 | salvage | 17,687 | incumbent 17,694 | -0.04% | 0.992 | 27.9 | 50 | 102 | [0, 0, 0] | 608 | 758 / 758 |
| 35 | continuation | 17,537 | incumbent 17,536 | +0.00% | 0.992 | 27.9 | 50 | 102 | [0, 0, 0] | 608 | 758 / 758 |
| 35 | continuation_landed | 17,537 | incumbent 17,536 | +0.00% | 0.992 | 27.9 | 50 | 102 | [0, 0, 0] | 608 | 758 / 758 |
| 47 | salvage | 23,318 | incumbent 23,248 | +0.30% | 0.992 | 37.6 | 70 | 119 | [0, 0, 0] | 755 | 940 / 940 |
| 47 | continuation | 23,133 | incumbent 23,087 | +0.20% | 0.992 | 37.6 | 70 | 119 | [0, 0, 0] | 755 | 940 / 940 |
| 47 | continuation_landed | 23,133 | incumbent 23,087 | +0.20% | 0.992 | 37.6 | 70 | 119 | [0, 0, 0] | 755 | 940 / 940 |
| 52 | salvage | 25,728 | incumbent 25,685 | +0.17% | 0.991 | 45.9 | 58 | 97 | [0, 0, 0] | 618 | 771 / 771 |
| 52 | continuation | 25,575 | incumbent 25,532 | +0.17% | 0.991 | 45.9 | 58 | 97 | [0, 0, 0] | 618 | 771 / 771 |
| 52 | continuation_landed | 25,575 | incumbent 25,532 | +0.17% | 0.991 | 45.9 | 58 | 97 | [0, 0, 0] | 618 | 771 / 771 |

### R_asymmetric_prices_mov (valid to W = 52; legacy 12-week: salvage -0.05%, continuation -0.04%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 63,892 | incumbent 63,448 | +0.70% | 0.987 | 29.2 | 40 | 182 | [0, 0, 0] | 4,699 | 5,865 / 5,865 |
| 11 | continuation | 62,726 | incumbent 62,284 | +0.71% | 0.987 | 29.2 | 40 | 182 | [0, 0, 0] | 4,699 | 5,865 / 5,865 |
| 11 | continuation_landed | 62,726 | incumbent 62,284 | +0.71% | 0.987 | 29.2 | 40 | 182 | [0, 0, 0] | 4,699 | 5,865 / 5,865 |
| 13 | salvage | 75,193 | incumbent 74,755 | +0.59% | 0.988 | 30.6 | 17 | 220 | [0, 0, 0] | 5,186 | 6,472 / 6,472 |
| 13 | continuation | 73,907 | incumbent 73,470 | +0.60% | 0.988 | 30.6 | 17 | 220 | [0, 0, 0] | 5,186 | 6,472 / 6,472 |
| 13 | continuation_landed | 73,907 | incumbent 73,470 | +0.60% | 0.988 | 30.6 | 17 | 220 | [0, 0, 0] | 5,186 | 6,472 / 6,472 |
| 15 | salvage | 86,480 | incumbent 85,961 | +0.60% | 0.989 | 32.5 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 15 | continuation | 85,225 | incumbent 84,714 | +0.60% | 0.989 | 32.5 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 15 | continuation_landed | 85,225 | incumbent 84,714 | +0.60% | 0.989 | 32.5 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 17 | salvage | 97,954 | incumbent 97,463 | +0.50% | 0.990 | 34.7 | 24 | 187 | [0, 0, 0] | 4,682 | 5,843 / 5,843 |
| 17 | continuation | 96,792 | periodic:2 96,239 | +0.58% | 0.990 | 34.7 | 24 | 187 | [0, 0, 0] | 4,682 | 5,843 / 5,843 |
| 17 | continuation_landed | 96,792 | periodic:2 96,239 | +0.58% | 0.990 | 34.7 | 24 | 187 | [0, 0, 0] | 4,682 | 5,843 / 5,843 |
| 19 | salvage | 109,071 | incumbent 108,553 | +0.48% | 0.990 | 39.5 | 24 | 198 | [0, 0, 0] | 4,758 | 5,939 / 5,939 |
| 19 | continuation | 107,891 | periodic:2 107,366 | +0.49% | 0.990 | 39.5 | 24 | 198 | [0, 0, 0] | 4,758 | 5,939 / 5,939 |
| 19 | continuation_landed | 107,891 | periodic:2 107,366 | +0.49% | 0.990 | 39.5 | 24 | 198 | [0, 0, 0] | 4,758 | 5,939 / 5,939 |
| 23 | salvage | 131,522 | incumbent 131,003 | +0.40% | 0.991 | 41.2 | 48 | 187 | [0, 0, 0] | 5,014 | 6,257 / 6,257 |
| 23 | continuation | 130,278 | incumbent 129,760 | +0.40% | 0.991 | 41.2 | 48 | 187 | [0, 0, 0] | 5,014 | 6,257 / 6,257 |
| 23 | continuation_landed | 130,278 | incumbent 129,760 | +0.40% | 0.991 | 41.2 | 48 | 187 | [0, 0, 0] | 5,014 | 6,257 / 6,257 |
| 35 | salvage | 197,451 | incumbent 196,690 | +0.39% | 0.993 | 51.8 | 127 | 168 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 35 | continuation | 196,038 | incumbent 195,436 | +0.31% | 0.993 | 51.8 | 127 | 168 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 35 | continuation_landed | 196,038 | incumbent 195,436 | +0.31% | 0.993 | 51.8 | 127 | 168 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 47 | salvage | 264,511 | incumbent 263,353 | +0.44% | 0.993 | 66.0 | 36 | 200 | [0, 0, 0] | 5,146 | 6,422 / 6,422 |
| 47 | continuation | 263,235 | incumbent 262,077 | +0.44% | 0.993 | 66.0 | 36 | 200 | [0, 0, 0] | 5,146 | 6,422 / 6,422 |
| 47 | continuation_landed | 263,235 | incumbent 262,077 | +0.44% | 0.993 | 66.0 | 36 | 200 | [0, 0, 0] | 5,146 | 6,422 / 6,422 |
| 52 | salvage | 293,180 | incumbent 290,755 | +0.83% | 0.992 | 77.2 | 146 | 203 | [0, 0, 0] | 7,851 | 9,780 / 9,780 |
| 52 | continuation | 291,251 | incumbent 289,535 | +0.59% | 0.992 | 77.2 | 146 | 203 | [0, 0, 0] | 7,851 | 9,780 / 9,780 |
| 52 | continuation_landed | 291,251 | incumbent 289,535 | +0.59% | 0.992 | 77.2 | 146 | 203 | [0, 0, 0] | 7,851 | 9,780 / 9,780 |

### S_cash_constrained (valid to W = 12; legacy 12-week: salvage +0.26%, continuation +3.59%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,631 | economic_lot 6,234 | +6.36% | 1.000 | 0.0 | 300 | 0 | [None, None, None] | 1,199 | 1,491 / 1,638 |
| 11 | continuation | 6,339 | economic_lot 5,924 | +7.00% | 1.000 | 0.0 | 300 | 0 | [None, None, None] | 1,199 | 1,491 / 1,638 |
| 11 | continuation_landed | 6,191 | economic_lot 5,875 | +5.38% | 1.000 | 0.0 | 300 | 0 | [None, None, None] | 1,199 | 1,491 / 1,638 |

### T_combined_realistic (valid to W = 52; legacy 12-week: salvage -11.47%, continuation -4.21%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 16,781 | economic_lot 17,593 | -4.61% | 0.996 | 9.8 | 1788 | 0 | [None, None, None] | 7,153 | 8,721 / 10,375 |
| 11 | continuation | 15,214 | economic_lot 15,846 | -3.99% | 0.996 | 9.8 | 1788 | 0 | [None, None, None] | 7,153 | 8,721 / 10,375 |
| 11 | continuation_landed | 13,560 | economic_lot 13,782 | -1.61% | 0.996 | 9.8 | 1788 | 0 | [None, None, None] | 7,153 | 8,721 / 10,375 |
| 13 | salvage | 18,438 | economic_lot 19,258 | -4.26% | 0.996 | 9.8 | 1387 | 0 | [None, None, None] | 5,548 | 6,805 / 8,087 |
| 13 | continuation | 17,181 | economic_lot 17,807 | -3.52% | 0.996 | 9.8 | 1387 | 0 | [None, None, None] | 5,548 | 6,805 / 8,087 |
| 13 | continuation_landed | 15,898 | economic_lot 16,143 | -1.52% | 0.996 | 9.8 | 1387 | 0 | [None, None, None] | 5,548 | 6,805 / 8,087 |
| 15 | salvage | 20,066 | economic_lot 20,889 | -3.94% | 0.997 | 9.8 | 991 | 0 | [None, None, None] | 3,963 | 4,885 / 5,801 |
| 15 | continuation | 19,144 | economic_lot 19,761 | -3.13% | 0.997 | 9.8 | 991 | 0 | [None, None, None] | 3,963 | 4,885 / 5,801 |
| 15 | continuation_landed | 18,228 | economic_lot 18,492 | -1.43% | 0.997 | 9.8 | 991 | 0 | [None, None, None] | 3,963 | 4,885 / 5,801 |
| 17 | salvage | 21,702 | economic_lot 22,542 | -3.72% | 0.997 | 9.8 | 591 | 0 | [None, None, None] | 2,363 | 2,926 / 3,471 |
| 17 | continuation | 21,138 | economic_lot 21,760 | -2.86% | 0.997 | 9.8 | 591 | 0 | [None, None, None] | 2,363 | 2,926 / 3,471 |
| 17 | continuation_landed | 20,594 | economic_lot 20,889 | -1.41% | 0.997 | 9.8 | 591 | 0 | [None, None, None] | 2,363 | 2,926 / 3,471 |
| 19 | salvage | 25,853 | economic_lot 25,399 | +1.79% | 0.997 | 9.8 | 817 | 630 | [None, 0, None] | 5,785 | 7,049 / 8,384 |
| 19 | continuation | 24,589 | economic_lot 24,451 | +0.56% | 0.997 | 9.8 | 817 | 630 | [None, 0, None] | 5,785 | 7,049 / 8,384 |
| 19 | continuation_landed | 23,254 | economic_lot 23,412 | -0.67% | 0.997 | 9.8 | 817 | 630 | [None, 0, None] | 5,785 | 7,049 / 8,384 |
| 23 | salvage | 30,411 | economic_lot 31,248 | -2.68% | 0.998 | 9.8 | 1275 | 0 | [None, None, None] | 5,101 | 6,267 / 7,434 |
| 23 | continuation | 29,245 | economic_lot 29,907 | -2.21% | 0.998 | 9.8 | 1275 | 0 | [None, None, None] | 5,101 | 6,267 / 7,434 |
| 23 | continuation_landed | 28,078 | economic_lot 28,428 | -1.23% | 0.998 | 9.8 | 1275 | 0 | [None, None, None] | 5,101 | 6,267 / 7,434 |
| 35 | salvage | 43,764 | economic_lot 44,664 | -2.02% | 0.998 | 11.7 | 725 | 0 | [None, None, None] | 2,900 | 3,587 / 4,256 |
| 35 | continuation | 43,077 | economic_lot 43,725 | -1.48% | 0.998 | 11.7 | 725 | 0 | [None, None, None] | 2,900 | 3,587 / 4,256 |
| 35 | continuation_landed | 42,408 | economic_lot 42,728 | -0.75% | 0.998 | 11.7 | 725 | 0 | [None, None, None] | 2,900 | 3,587 / 4,256 |
| 47 | salvage | 60,156 | economic_lot 59,064 | +1.85% | 0.999 | 11.7 | 309 | 1230 | [0, 0, None] | 6,158 | 7,506 / 8,939 |
| 47 | continuation | 58,808 | economic_lot 58,221 | +1.01% | 0.999 | 11.7 | 309 | 1230 | [0, 0, None] | 6,158 | 7,506 / 8,939 |
| 47 | continuation_landed | 57,375 | economic_lot 57,297 | +0.14% | 0.999 | 11.7 | 309 | 1230 | [0, 0, None] | 6,158 | 7,506 / 8,939 |
| 52 | salvage | 65,422 | economic_lot 66,626 | -1.81% | 0.999 | 11.7 | 1165 | 0 | [None, None, None] | 4,662 | 5,731 / 6,834 |
| 52 | continuation | 64,353 | economic_lot 65,196 | -1.29% | 0.999 | 11.7 | 1165 | 0 | [None, None, None] | 4,662 | 5,731 / 6,834 |
| 52 | continuation_landed | 63,250 | economic_lot 63,612 | -0.57% | 0.999 | 11.7 | 1165 | 0 | [None, None, None] | 4,662 | 5,731 / 6,834 |

## Stage 4: convergence classification (section 5), both rules

| fixture | valid at 52 | rule | delta @11 (rolling) | @23 | @35 | @47 | @52 | max |delta(W)-delta(52)| over 40..52 | stable | class |
|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | salvage | +1.48% | +0.89% | +1.10% | +0.98% | +0.88% | 0.27 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation | +1.46% | +0.93% | +1.05% | +0.98% | +0.89% | 0.24 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation_landed | +1.46% | +0.93% | +1.05% | +0.98% | +0.89% | 0.24 pp | yes | A. STABLE PASS |
| B_fixed_order_cost_replace_sold | yes | salvage | +4.92% | -3.76% | +3.85% | -0.75% | +2.72% | 5.77 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation | +2.98% | -0.43% | +2.01% | +0.89% | +2.03% | 2.08 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation_landed | +0.73% | -0.58% | +1.34% | +0.92% | +1.60% | 1.55 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | salvage | +4.83% | +0.95% | +0.84% | +0.83% | +0.42% | 1.03 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | continuation | +0.92% | +0.33% | +0.27% | +0.13% | +0.13% | 0.14 pp | yes | A. STABLE PASS |
| C_moq_four_weeks | yes | continuation_landed | +0.92% | +0.33% | +0.27% | +0.13% | +0.13% | 0.14 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | salvage | -0.52% | +0.57% | +0.83% | +0.63% | +0.57% | 0.27 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation | +0.23% | +0.73% | +0.96% | +0.73% | +0.65% | 0.19 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation_landed | +0.23% | +0.73% | +0.96% | +0.73% | +0.65% | 0.19 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | salvage | +0.00% | +0.02% | +0.01% | -0.03% | -0.33% | 0.34 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation | +0.00% | -0.00% | -0.01% | -0.03% | -0.10% | 0.09 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation_landed | +0.00% | -0.01% | -0.01% | -0.03% | -0.03% | 0.09 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | salvage | +2.95% | +1.38% | +1.35% | +0.22% | +1.83% | 1.62 pp | NO | E. NON-CONVERGENT |
| F_mov_two_skus | yes | continuation | +1.10% | +0.85% | +0.83% | +0.49% | +0.75% | 0.26 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | continuation_landed | +1.10% | +0.85% | +0.83% | +0.49% | +0.75% | 0.26 pp | yes | A. STABLE PASS |
| G_freight_tiers | yes | salvage | -0.77% | -2.63% | -3.93% | -2.53% | -0.52% | 2.45 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation | +0.39% | -1.37% | -2.43% | -1.99% | -0.84% | 1.42 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation_landed | +1.18% | +0.15% | -0.55% | -1.21% | -1.02% | 0.50 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | salvage | -2.47% | -2.59% | -1.86% | -1.89% | -1.97% | 0.86 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | continuation | -2.97% | -2.50% | -1.97% | -2.04% | -1.99% | 0.36 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | continuation_landed | -2.86% | -2.26% | -1.94% | -2.05% | -1.97% | 0.17 pp | yes | A. STABLE PASS |
| I_max_pallets_ftl_cap | yes | salvage | +5.78% | +0.02% | -0.03% | +0.83% | +0.77% | 1.50 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation | +4.56% | -0.01% | -0.07% | +0.70% | +0.64% | 1.12 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation_landed | +0.16% | -0.09% | -0.17% | +0.24% | +0.24% | 0.45 pp | yes | A. STABLE PASS |
| J_net60_cost_of_capital | yes | salvage | +5.60% | +0.01% | -0.03% | -0.02% | +1.42% | 1.45 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation | +1.63% | -0.13% | -0.03% | +0.04% | +0.50% | 1.84 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation_landed | +0.88% | -0.15% | -0.03% | +0.06% | +0.34% | 1.25 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | salvage | +5.59% | +0.01% | -0.03% | -0.02% | +1.42% | 1.45 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation | +1.69% | -0.13% | -0.03% | +0.04% | +0.50% | 1.87 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation_landed | +0.94% | -0.15% | -0.03% | +0.05% | +0.34% | 1.28 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | salvage | +6.56% | +1.97% | +1.76% | +1.86% | -1.94% | 3.73 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation | +0.65% | +1.02% | +0.68% | +0.69% | -0.40% | 1.02 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation_landed | +0.60% | +0.89% | +0.52% | +0.51% | -0.10% | 0.62 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | salvage | +2.42% | +0.59% | +0.30% | +0.12% | +0.09% | 0.39 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| M_order_calendar_wednesday | yes | continuation | +0.96% | +0.05% | -0.09% | -0.19% | -0.17% | 0.11 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | continuation_landed | +0.96% | +0.05% | -0.09% | -0.19% | -0.17% | 0.11 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | salvage | +1.10% | +0.89% | +0.69% | +0.79% | +0.69% | 0.17 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation | +1.31% | +0.96% | +0.72% | +0.80% | +0.72% | 0.13 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation_landed | +1.31% | +0.96% | +0.72% | +0.80% | +0.72% | 0.13 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | salvage | +0.91% | +0.30% | +0.35% | +0.29% | +0.34% | 0.20 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation | +0.10% | +0.05% | +0.11% | +0.15% | +0.12% | 0.13 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation_landed | +0.10% | +0.05% | +0.11% | +0.15% | +0.12% | 0.13 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | salvage | +0.14% | +0.55% | +1.01% | +1.38% | +0.81% | 0.57 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | continuation | +0.05% | +0.50% | +0.74% | +0.69% | +0.59% | 0.19 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | continuation_landed | +0.05% | +0.50% | +0.74% | +0.69% | +0.59% | 0.19 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | salvage | -0.03% | +0.01% | -0.04% | +0.30% | +0.17% | 0.14 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation | -0.04% | +0.01% | +0.00% | +0.20% | +0.17% | 0.04 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation_landed | -0.04% | +0.01% | +0.00% | +0.20% | +0.17% | 0.04 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | salvage | +0.70% | +0.40% | +0.39% | +0.44% | +0.83% | 0.39 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation | +0.71% | +0.40% | +0.31% | +0.44% | +0.59% | 0.15 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation_landed | +0.71% | +0.40% | +0.31% | +0.44% | +0.59% | 0.15 pp | yes | A. STABLE PASS |
| S_cash_constrained | no (to 12) | salvage | +6.36% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation | +7.00% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation_landed | +5.38% | - | - | - | - | - | - | INVALID AT 52 |
| T_combined_realistic | yes | salvage | -4.61% | -2.68% | -2.02% | +1.85% | -1.81% | 2.59 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation | -3.99% | -2.21% | -1.48% | +1.01% | -1.29% | 1.58 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation_landed | -1.61% | -1.23% | -0.75% | +0.14% | -0.57% | 0.76 pp | yes | A. STABLE PASS |

## Section 6: boundary-sensitivity index and the selection rule

| rule | Stage 7 tests | BSI (pp per two-review shift, all ten policy pairs, valid fixtures, three seeds) | fixtures stable at 52 |
|---|---|---|---|
| salvage | fail | 1.682 | 10 / 19 |
| continuation | fail | 0.917 | 12 / 19 |
| continuation_landed | pass | 0.455 | 16 / 19 |

**Declared rule: continuation_landed** (the only rule passing the twelve tests).

BSI per rule restricted to baseline-only pairs (no ZAAD in the pair), as a check that the index is not driven by ZAAD:

* salvage: 1.391 pp
* continuation: 0.795 pp
* continuation_landed: 0.426 pp

## Section 8, Option D diagnostic: start offset s with symmetric endpoint handling (window [s, 52])

| fixture | rule | s=0 | s=4 | s=8 |
|---|---|---|---|---|
| A_no_terms_good_incumbent | salvage | +0.88% vs incumbent | +0.87% vs incumbent | +0.82% vs incumbent |
| A_no_terms_good_incumbent | continuation | +0.89% vs incumbent | +0.87% vs incumbent | +0.81% vs incumbent |
| A_no_terms_good_incumbent | continuation_landed | +0.89% vs incumbent | +0.87% vs incumbent | +0.81% vs incumbent |
| B_fixed_order_cost_replace_sold | salvage | +2.72% vs economic_lot | +6.80% vs economic_lot | +7.52% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation | +2.03% vs economic_lot | +3.19% vs economic_lot | +3.48% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation_landed | +1.60% vs economic_lot | +2.60% vs economic_lot | +2.66% vs economic_lot |
| C_moq_four_weeks | salvage | +0.42% vs reorder_point | -0.36% vs reorder_point | -1.35% vs reorder_point |
| C_moq_four_weeks | continuation | +0.13% vs reorder_point | +0.01% vs reorder_point | -0.13% vs reorder_point |
| C_moq_four_weeks | continuation_landed | +0.13% vs reorder_point | +0.01% vs reorder_point | -0.13% vs reorder_point |
| D_case_multiple | salvage | +0.57% vs incumbent | +0.62% vs incumbent | +0.57% vs incumbent |
| D_case_multiple | continuation | +0.65% vs incumbent | +0.71% vs incumbent | +0.68% vs incumbent |
| D_case_multiple | continuation_landed | +0.65% vs incumbent | +0.71% vs incumbent | +0.68% vs incumbent |
| E_pallet_multiple | salvage | -0.33% vs incumbent | -0.36% vs incumbent | -0.39% vs incumbent |
| E_pallet_multiple | continuation | -0.10% vs incumbent | -0.11% vs incumbent | -0.12% vs incumbent |
| E_pallet_multiple | continuation_landed | -0.03% vs incumbent | -0.03% vs incumbent | -0.04% vs incumbent |
| F_mov_two_skus | salvage | +1.83% vs periodic:2 | +0.71% vs periodic:2 | +0.63% vs periodic:2 |
| F_mov_two_skus | continuation | +0.75% vs periodic:2 | +0.61% vs periodic:2 | +0.50% vs periodic:2 |
| F_mov_two_skus | continuation_landed | +0.75% vs periodic:2 | +0.61% vs periodic:2 | +0.50% vs periodic:2 |
| G_freight_tiers | salvage | -0.52% vs economic_lot | -0.29% vs economic_lot | -2.74% vs economic_lot |
| G_freight_tiers | continuation | -0.84% vs economic_lot | -0.86% vs economic_lot | -2.35% vs economic_lot |
| G_freight_tiers | continuation_landed | -1.02% vs economic_lot | -1.10% vs economic_lot | -1.75% vs economic_lot |
| H_per_pallet_freight | salvage | -1.97% vs periodic:2 | -2.22% vs periodic:2 | -3.21% vs periodic:2 |
| H_per_pallet_freight | continuation | -1.99% vs periodic:2 | -2.12% vs periodic:2 | -2.45% vs periodic:2 |
| H_per_pallet_freight | continuation_landed | -1.97% vs periodic:2 | -2.06% vs periodic:2 | -2.00% vs periodic:2 |
| I_max_pallets_ftl_cap | salvage | +0.77% vs economic_lot | +0.84% vs economic_lot | +0.92% vs economic_lot |
| I_max_pallets_ftl_cap | continuation | +0.64% vs economic_lot | +0.70% vs economic_lot | +0.77% vs economic_lot |
| I_max_pallets_ftl_cap | continuation_landed | +0.24% vs economic_lot | +0.26% vs economic_lot | +0.28% vs economic_lot |
| J_net60_cost_of_capital | salvage | +1.42% vs economic_lot | +1.59% vs economic_lot | +1.70% vs economic_lot |
| J_net60_cost_of_capital | continuation | +0.50% vs economic_lot | +0.55% vs economic_lot | +0.60% vs economic_lot |
| J_net60_cost_of_capital | continuation_landed | +0.34% vs economic_lot | +0.37% vs economic_lot | +0.40% vs economic_lot |
| K_deposit_early_cash | salvage | +1.42% vs economic_lot | +1.59% vs economic_lot | +1.70% vs economic_lot |
| K_deposit_early_cash | continuation | +0.50% vs economic_lot | +0.55% vs economic_lot | +0.60% vs economic_lot |
| K_deposit_early_cash | continuation_landed | +0.34% vs economic_lot | +0.37% vs economic_lot | +0.40% vs economic_lot |
| L_high_holding_rate | salvage | -1.94% vs economic_lot | -2.43% vs economic_lot | -2.62% vs economic_lot |
| L_high_holding_rate | continuation | -0.40% vs economic_lot | -0.53% vs economic_lot | -0.57% vs economic_lot |
| L_high_holding_rate | continuation_landed | -0.10% vs economic_lot | -0.18% vs economic_lot | -0.19% vs economic_lot |
| M_order_calendar_wednesday | salvage | +0.09% vs incumbent | +0.10% vs incumbent | -0.88% vs incumbent |
| M_order_calendar_wednesday | continuation | -0.17% vs incumbent | -0.18% vs incumbent | -0.65% vs incumbent |
| M_order_calendar_wednesday | continuation_landed | -0.17% vs incumbent | -0.18% vs incumbent | -0.65% vs incumbent |
| N_long_lead_21_days | salvage | +0.69% vs incumbent | +0.68% vs incumbent | +0.66% vs incumbent |
| N_long_lead_21_days | continuation | +0.72% vs incumbent | +0.72% vs incumbent | +0.69% vs incumbent |
| N_long_lead_21_days | continuation_landed | +0.72% vs incumbent | +0.72% vs incumbent | +0.69% vs incumbent |
| O_low_opening_stock | salvage | +0.34% vs reorder_point | +0.38% vs reorder_point | -0.00% vs reorder_point |
| O_low_opening_stock | continuation | +0.12% vs reorder_point | +0.14% vs reorder_point | +0.03% vs reorder_point |
| O_low_opening_stock | continuation_landed | +0.12% vs reorder_point | +0.14% vs reorder_point | +0.03% vs reorder_point |
| P_high_opening_stock | salvage | +0.81% vs reorder_point | +0.72% vs reorder_point | +0.57% vs reorder_point |
| P_high_opening_stock | continuation | +0.59% vs reorder_point | +0.62% vs reorder_point | +0.50% vs reorder_point |
| P_high_opening_stock | continuation_landed | +0.59% vs reorder_point | +0.62% vs reorder_point | +0.50% vs reorder_point |
| Q_volatile_demand_high_target | salvage | +0.17% vs incumbent | +0.20% vs incumbent | +0.25% vs periodic:2 |
| Q_volatile_demand_high_target | continuation | +0.17% vs incumbent | +0.20% vs incumbent | +0.22% vs incumbent |
| Q_volatile_demand_high_target | continuation_landed | +0.17% vs incumbent | +0.20% vs incumbent | +0.22% vs incumbent |
| R_asymmetric_prices_mov | salvage | +0.83% vs incumbent | +0.93% vs incumbent | +0.96% vs incumbent |
| R_asymmetric_prices_mov | continuation | +0.59% vs incumbent | +0.65% vs incumbent | +0.66% vs incumbent |
| R_asymmetric_prices_mov | continuation_landed | +0.59% vs incumbent | +0.65% vs incumbent | +0.66% vs incumbent |
| T_combined_realistic | salvage | -1.81% vs economic_lot | -2.01% vs economic_lot | -2.13% vs economic_lot |
| T_combined_realistic | continuation | -1.29% vs economic_lot | -1.43% vs economic_lot | -1.53% vs economic_lot |
| T_combined_realistic | continuation_landed | -0.57% vs economic_lot | -0.62% vs economic_lot | -0.68% vs economic_lot |

## Section 8, Option E diagnostic: per-week average cost at 52 and each policy at its own cycle-minimum endpoint in [40, 52] (declared rule)

| fixture | ZAAD per week | best baseline per week | delta (same as @52) | cycle-minimum endpoints (policy: W) | delta at own cycle minima, per-week normalised |
|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 512.8 | incumbent 508.3 | +0.89% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +1.26% |
| B_fixed_order_cost_replace_sold | 540.3 | economic_lot 531.8 | +1.60% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 52, 'gated': 44} | +1.68% |
| C_moq_four_weeks | 509.0 | reorder_point 508.3 | +0.13% | {'incumbent': 40, 'reorder_point': 43, 'periodic:2': 42, 'economic_lot': 43, 'gated': 45} | -0.09% |
| D_case_multiple | 508.3 | incumbent 505.0 | +0.65% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.94% |
| E_pallet_multiple | 536.4 | incumbent 536.6 | -0.03% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | -0.02% |
| F_mov_two_skus | 1,020.3 | periodic:2 1,012.6 | +0.75% | {'incumbent': 40, 'reorder_point': 51, 'periodic:2': 44, 'economic_lot': 51, 'gated': 47} | +0.39% |
| G_freight_tiers | 1,207.2 | economic_lot 1,219.6 | -1.02% | {'incumbent': 43, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 46} | -0.92% |
| H_per_pallet_freight | 570.8 | periodic:2 582.2 | -1.97% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 41} | -2.08% |
| I_max_pallets_ftl_cap | 783.8 | economic_lot 782.0 | +0.24% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 49, 'gated': 49} | +0.25% |
| J_net60_cost_of_capital | 529.8 | economic_lot 528.0 | +0.34% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 41} | +0.05% |
| K_deposit_early_cash | 530.0 | economic_lot 528.2 | +0.34% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 41} | +0.10% |
| L_high_holding_rate | 536.7 | economic_lot 537.2 | -0.10% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 40, 'gated': 41} | +0.33% |
| M_order_calendar_wednesday | 514.0 | incumbent 514.9 | -0.17% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | -0.12% |
| N_long_lead_21_days | 513.1 | incumbent 509.4 | +0.72% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 41} | +0.61% |
| O_low_opening_stock | 520.0 | reorder_point 519.3 | +0.12% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.32% |
| P_high_opening_stock | 510.6 | reorder_point 507.6 | +0.59% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.91% |
| Q_volatile_demand_high_target | 491.8 | incumbent 491.0 | +0.17% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.20% |
| R_asymmetric_prices_mov | 5,601.0 | incumbent 5,568.0 | +0.59% | {'incumbent': 51, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 41} | +0.68% |
| T_combined_realistic | 1,216.3 | economic_lot 1,223.3 | -0.57% | {'incumbent': 40, 'reorder_point': 52, 'periodic:2': 42, 'economic_lot': 46, 'gated': 46} | +0.05% |

## Stage 9: A-T at the declared benchmark (rolling horizon, W* = 52, rule continuation_landed) beside the legacy twelve-week result

| fixture | valid | legacy delta (salvage) | rolling @11 | **declared @52** | verdict | class | service | breaches | unmet | avg inv units | terminal on-hand | in-transit | purchases | freight | ordering | carrying | financing | shortage | inventory value change | terminal credit (rule) | P1 / P0 owned | actions | abstentions | legacy first-review checks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | +0.43% | +1.46% | **+0.89%** vs incumbent | PASS | A. STABLE PASS | 0.989 | 4.7 | 57.8 | 17 | 6 | 102 | 25,723 | 0 | 0 | 13 | 0 | 723 | 315 | 543 | 153 / 3 | 46 | 21 | ok |
| B_fixed_order_cost_replace_sold | yes | -10.70% | +0.73% | **+1.60%** vs economic_lot | PASS | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 595 | 716 | 0 | 29,127 | 0 | 1,500 | 445 | 0 | 0 | -2,116 | 3,727 | 153 / 3 | 155 | 0 | ok |
| C_moq_four_weeks | yes | +3.61% | +0.92% | **+0.13%** vs reorder_point | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 287 | 398 | 185 | 28,393 | 0 | 0 | 215 | 0 | 0 | -1,584 | 2,891 | 153 / 3 | 155 | 0 | ok |
| D_case_multiple | yes | -0.58% | +0.23% | **+0.65%** vs incumbent | PASS | A. STABLE PASS | 0.995 | 2.0 | 24.7 | 31 | 20 | 94 | 25,920 | 0 | 0 | 24 | 0 | 309 | 293 | 570 | 153 / 3 | 85 | 7 | ok |
| E_pallet_multiple | yes | -0.00% | +0.00% | **-0.03%** vs incumbent | PASS | A. STABLE PASS | 1.000 | 0.0 | 2.1 | 105 | 101 | 64 | 26,333 | 1,580 | 0 | 78 | 0 | 27 | 87 | 875 | 153 / 3 | 41 | 7 | ok |
| F_mov_two_skus | yes | +0.24% | +1.10% | **+0.75%** vs periodic:2 | PASS | A. STABLE PASS | 0.998 | 1.0 | 25.0 | 431 | 593 | 280 | 55,257 | 0 | 0 | 322 | 0 | 312 | -1,993 | 4,337 | 152 / 4 | 154 | 0 | ok |
| G_freight_tiers | yes | -10.01% | +1.18% | **-1.02%** vs economic_lot | PASS | A. STABLE PASS | 0.998 | 0.7 | 17.1 | 1019 | 1262 | 0 | 57,471 | 9,533 | 667 | 762 | 0 | 214 | -3,546 | 7,371 | 151 / 5 | 155 | 0 | ok |
| H_per_pallet_freight | yes | -3.73% | -2.86% | **-1.97%** vs periodic:2 | PASS | A. STABLE PASS | 0.997 | 1.0 | 15.5 | 102 | 11 | 96 | 25,925 | 3,340 | 0 | 76 | 0 | 194 | 321 | 605 | 153 / 3 | 128 | 28 | ok |
| I_max_pallets_ftl_cap | yes | +0.53% | +0.16% | **+0.24%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 1.1 | 268 | 347 | 0 | 27,186 | 13,467 | 1,850 | 201 | 0 | 13 | -638 | 2,707 | 153 / 3 | 156 | 0 | ok |
| J_net60_cost_of_capital | yes | -11.06% | +0.88% | **+0.34%** vs economic_lot | PASS | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 580 | 355 | 328 | 28,943 | 0 | 800 | 434 | 56 | 0 | -1,980 | 3,435 | 153 / 3 | 142 | 9 | ok |
| K_deposit_early_cash | yes | -11.20% | +0.94% | **+0.34%** vs economic_lot | PASS | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 580 | 355 | 328 | 28,943 | 0 | 800 | 434 | 68 | 0 | -1,980 | 3,435 | 153 / 3 | 142 | 9 | ok |
| L_high_holding_rate | yes | -10.16% | +0.60% | **-0.10%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 582 | 409 | 0 | 27,561 | 0 | 800 | 871 | 0 | 0 | -886 | 2,076 | 153 / 3 | 156 | 0 | ok |
| M_order_calendar_wednesday | yes | -0.54% | +0.96% | **-0.17%** vs incumbent | PASS | A. STABLE PASS | 0.989 | 1.7 | 57.6 | 87 | 91 | 189 | 26,587 | 0 | 0 | 65 | 0 | 719 | -370 | 1,394 | 12 / 144 | 141 | 1 | ok |
| N_long_lead_21_days | yes | -0.71% | +1.31% | **+0.72%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.989 | 4.0 | 56.9 | 33 | 23 | 280 | 25,707 | 0 | 0 | 24 | 0 | 711 | 534 | 1,513 | 152 / 4 | 40 | 23 | ['categories'] |
| O_low_opening_stock | yes | +0.46% | +0.10% | **+0.12%** vs reorder_point | PASS | A. STABLE PASS | 0.980 | 3.3 | 102.4 | 66 | 44 | 127 | 26,460 | 0 | 0 | 49 | 0 | 1,280 | -582 | 850 | 108 / 48 | 132 | 18 | ok |
| P_high_opening_stock | yes | +0.29% | +0.05% | **+0.59%** vs reorder_point | PASS | A. STABLE PASS | 0.992 | 2.7 | 40.8 | 76 | 25 | 144 | 23,828 | 0 | 0 | 57 | 0 | 510 | 2,322 | 845 | 152 / 4 | 117 | 23 | ok |
| Q_volatile_demand_high_target | yes | +0.85% | -0.04% | **+0.17%** vs incumbent | PASS | A. STABLE PASS | 0.991 | 3.0 | 45.9 | 75 | 58 | 97 | 24,966 | 0 | 0 | 56 | 0 | 574 | 132 | 771 | 72 / 84 | 20 | 2 | ok |
| R_asymmetric_prices_mov | yes | -0.05% | +0.71% | **+0.59%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.992 | 1.7 | 77.2 | 64 | 146 | 203 | 288,084 | 0 | 0 | 256 | 0 | 4,441 | 399 | 9,780 | 153 / 3 | 38 | 38 | ['categories'] |
| S_cash_constrained | no (to 12) | +0.26% | +5.38% | **+5.46%** vs economic_lot | INVALID AT 52 (diagnostic @12: outside tolerance) | - | 1.000 | 0.0 | 0.0 | 255 | 194 | 111 | 6,968 | 0 | 667 | 44 | 5 | 0 | -472 | 1,665 | 36 / 0 | 36 | 0 | ok |
| T_combined_realistic | yes | -11.47% | -1.61% | **-0.57%** vs economic_lot | PASS | A. STABLE PASS | 0.999 | 0.3 | 11.7 | 1063 | 1165 | 0 | 56,680 | 9,267 | 1,267 | 954 | 111 | 147 | -3,162 | 6,834 | 153 / 3 | 155 | 0 | ok |

Runtime, ZAAD reviews: n 3013, p50 1.02 s, p90 4.14 s, p95 6.30 s, max 67.7 s; total wall of all cells 6,111 s.

