# P1 extended-window benchmark: convergence, stability, selection and the declared result

Source `docs/zaad_full/evidence/p1/closure/horizon52_cycle.jsonl`: 300 cells, rolling twelve-period planning horizon, 52 reviews requested, stitched truth per seed, scored at every endpoint under both terminal rules. Pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`.

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
| S_cash_constrained | 12 | [('incumbent', 41001, 26, 'PHYSICAL_FAILURE'), ('incumbent', 41002, 24, 'PHYSICAL_FAILURE'), ('incumbent', 41003, 29, 'PHYSICAL_FAILURE'), ('reorder_point', 41001, 26, 'PHYSICAL_FAILURE'), ('reorder_point', 41002, 24, 'PHYSICAL_FAILURE'), ('reorder_point', 41003, 29, 'PHYSICAL_FAILURE'), ('economic_lot', 41001, 45, 'PHYSICAL_FAILURE'), ('economic_lot', 41002, 41, 'PHYSICAL_FAILURE'), ('economic_lot', 41003, 44, 'PHYSICAL_FAILURE'), ('gated', 41001, 19, 'ABSTAIN'), ('gated', 41002, 15, 'ABSTAIN'), ('gated', 41003, 12, 'ABSTAIN')] |
| T_combined_realistic | 52 | - |

## Stage 3: endpoint sensitivity (seed means; ZAAD against the best baseline at that endpoint)

### A_no_terms_good_incumbent (valid to W = 52; legacy 12-week: salvage +0.43%, continuation +0.46%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,907 | incumbent 5,824 | +1.43% | 0.982 | 20.4 | 25 | 93 | [0, 0, 0] | 471 | 588 / 588 |
| 11 | continuation | 5,790 | incumbent 5,710 | +1.40% | 0.982 | 20.4 | 25 | 93 | [0, 0, 0] | 471 | 588 / 588 |
| 11 | continuation_landed | 5,790 | incumbent 5,710 | +1.40% | 0.982 | 20.4 | 25 | 93 | [0, 0, 0] | 471 | 588 / 588 |
| 13 | salvage | 6,952 | incumbent 6,874 | +1.14% | 0.984 | 21.4 | 7 | 112 | [0, 0, 0] | 479 | 598 / 598 |
| 13 | continuation | 6,834 | incumbent 6,757 | +1.13% | 0.984 | 21.4 | 7 | 112 | [0, 0, 0] | 479 | 598 / 598 |
| 13 | continuation_landed | 6,834 | incumbent 6,757 | +1.13% | 0.984 | 21.4 | 7 | 112 | [0, 0, 0] | 479 | 598 / 598 |
| 15 | salvage | 7,943 | incumbent 7,870 | +0.93% | 0.986 | 21.6 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 15 | continuation | 7,835 | incumbent 7,757 | +1.00% | 0.986 | 21.6 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 15 | continuation_landed | 7,835 | incumbent 7,757 | +1.00% | 0.986 | 21.6 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 17 | salvage | 8,966 | incumbent 8,861 | +1.19% | 0.985 | 25.4 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 17 | continuation | 8,863 | incumbent 8,757 | +1.21% | 0.985 | 25.4 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 17 | continuation_landed | 8,863 | incumbent 8,757 | +1.21% | 0.985 | 25.4 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 19 | salvage | 10,042 | incumbent 9,934 | +1.09% | 0.984 | 30.3 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 19 | continuation | 9,929 | incumbent 9,821 | +1.10% | 0.984 | 30.3 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 19 | continuation_landed | 9,929 | incumbent 9,821 | +1.10% | 0.984 | 30.3 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 23 | salvage | 12,096 | incumbent 11,993 | +0.86% | 0.986 | 31.1 | 23 | 94 | [0, 0, 0] | 467 | 582 / 582 |
| 23 | continuation | 11,981 | incumbent 11,874 | +0.90% | 0.986 | 31.1 | 23 | 94 | [0, 0, 0] | 467 | 582 / 582 |
| 23 | continuation_landed | 11,981 | incumbent 11,874 | +0.90% | 0.986 | 31.1 | 23 | 94 | [0, 0, 0] | 467 | 582 / 582 |
| 35 | salvage | 18,227 | incumbent 18,033 | +1.08% | 0.987 | 46.2 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 35 | continuation | 18,103 | incumbent 17,917 | +1.03% | 0.987 | 46.2 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 35 | continuation_landed | 18,103 | incumbent 17,917 | +1.03% | 0.987 | 46.2 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 47 | salvage | 24,257 | incumbent 24,046 | +0.88% | 0.988 | 55.1 | 18 | 102 | [0, 0, 0] | 480 | 598 / 598 |
| 47 | continuation | 24,138 | incumbent 23,927 | +0.88% | 0.988 | 55.1 | 18 | 102 | [0, 0, 0] | 480 | 598 / 598 |
| 47 | continuation_landed | 24,138 | incumbent 23,927 | +0.88% | 0.988 | 55.1 | 18 | 102 | [0, 0, 0] | 480 | 598 / 598 |
| 52 | salvage | 26,750 | incumbent 26,539 | +0.79% | 0.989 | 55.1 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation | 26,642 | incumbent 26,431 | +0.80% | 0.989 | 55.1 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation_landed | 26,642 | incumbent 26,431 | +0.80% | 0.989 | 55.1 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |

### B_fixed_order_cost_replace_sold (valid to W = 52; legacy 12-week: salvage -10.70%, continuation -1.06%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,464 | economic_lot 6,995 | +6.72% | 1.000 | 0.0 | 1215 | 0 | [None, None, None] | 4,859 | 5,946 / 6,133 |
| 11 | continuation | 6,377 | economic_lot 6,182 | +3.16% | 1.000 | 0.0 | 1215 | 0 | [None, None, None] | 4,859 | 5,946 / 6,133 |
| 11 | continuation_landed | 6,191 | economic_lot 6,065 | +2.07% | 1.000 | 0.0 | 1215 | 0 | [None, None, None] | 4,859 | 5,946 / 6,133 |
| 13 | salvage | 8,307 | economic_lot 7,827 | +6.13% | 1.000 | 0.0 | 1012 | 0 | [None, None, None] | 4,047 | 4,965 / 5,121 |
| 13 | continuation | 7,389 | economic_lot 7,195 | +2.70% | 1.000 | 0.0 | 1012 | 0 | [None, None, None] | 4,047 | 4,965 / 5,121 |
| 13 | continuation_landed | 7,233 | economic_lot 7,105 | +1.79% | 1.000 | 0.0 | 1012 | 0 | [None, None, None] | 4,047 | 4,965 / 5,121 |
| 15 | salvage | 9,115 | economic_lot 8,625 | +5.68% | 1.000 | 0.0 | 816 | 0 | [None, None, None] | 3,264 | 4,011 / 4,138 |
| 15 | continuation | 8,368 | economic_lot 8,173 | +2.38% | 1.000 | 0.0 | 816 | 0 | [None, None, None] | 3,264 | 4,011 / 4,138 |
| 15 | continuation_landed | 8,241 | economic_lot 8,110 | +1.61% | 1.000 | 0.0 | 816 | 0 | [None, None, None] | 3,264 | 4,011 / 4,138 |
| 17 | salvage | 10,684 | economic_lot 9,420 | +13.41% | 1.000 | 0.0 | 620 | 629 | [None, 0, None] | 4,994 | 6,106 / 6,292 |
| 17 | continuation | 9,572 | economic_lot 9,154 | +4.57% | 1.000 | 0.0 | 620 | 629 | [None, 0, None] | 4,994 | 6,106 / 6,292 |
| 17 | continuation_landed | 9,386 | economic_lot 9,118 | +2.94% | 1.000 | 0.0 | 620 | 629 | [None, 0, None] | 4,994 | 6,106 / 6,292 |
| 19 | salvage | 11,517 | economic_lot 11,775 | -2.19% | 1.000 | 0.0 | 1048 | 0 | [None, None, None] | 4,193 | 5,139 / 5,296 |
| 19 | continuation | 10,571 | economic_lot 10,666 | -0.90% | 1.000 | 0.0 | 1048 | 0 | [None, None, None] | 4,193 | 5,139 / 5,296 |
| 19 | continuation_landed | 10,413 | economic_lot 10,494 | -0.77% | 1.000 | 0.0 | 1048 | 0 | [None, None, None] | 4,193 | 5,139 / 5,296 |
| 23 | salvage | 13,993 | economic_lot 14,233 | -1.69% | 1.000 | 0.0 | 1301 | 0 | [None, None, None] | 5,205 | 6,372 / 6,550 |
| 23 | continuation | 12,827 | economic_lot 12,892 | -0.51% | 1.000 | 0.0 | 1301 | 0 | [None, None, None] | 5,205 | 6,372 / 6,550 |
| 23 | continuation_landed | 12,649 | economic_lot 12,691 | -0.33% | 1.000 | 0.0 | 1301 | 0 | [None, None, None] | 5,205 | 6,372 / 6,550 |
| 35 | salvage | 19,689 | economic_lot 19,080 | +3.19% | 1.000 | 0.0 | 776 | 0 | [None, None, None] | 3,106 | 3,821 / 3,931 |
| 35 | continuation | 18,974 | economic_lot 18,764 | +1.12% | 1.000 | 0.0 | 776 | 0 | [None, None, None] | 3,106 | 3,821 / 3,931 |
| 35 | continuation_landed | 18,863 | economic_lot 18,720 | +0.76% | 1.000 | 0.0 | 776 | 0 | [None, None, None] | 3,106 | 3,821 / 3,931 |
| 47 | salvage | 25,727 | economic_lot 26,174 | -1.71% | 1.000 | 0.0 | 492 | 0 | [None, None, None] | 1,969 | 2,442 / 2,513 |
| 47 | continuation | 25,255 | economic_lot 25,264 | -0.04% | 1.000 | 0.0 | 492 | 0 | [None, None, None] | 1,969 | 2,442 / 2,513 |
| 47 | continuation_landed | 25,183 | economic_lot 25,133 | +0.20% | 1.000 | 0.0 | 492 | 0 | [None, None, None] | 1,969 | 2,442 / 2,513 |
| 52 | salvage | 29,253 | economic_lot 28,189 | +3.77% | 1.000 | 0.0 | 1207 | 0 | [None, None, None] | 4,827 | 5,891 / 6,067 |
| 52 | continuation | 28,189 | economic_lot 27,719 | +1.70% | 1.000 | 0.0 | 1207 | 0 | [None, None, None] | 4,827 | 5,891 / 6,067 |
| 52 | continuation_landed | 28,013 | economic_lot 27,654 | +1.30% | 1.000 | 0.0 | 1207 | 0 | [None, None, None] | 4,827 | 5,891 / 6,067 |

### C_moq_four_weeks (valid to W = 52; legacy 12-week: salvage +3.61%, continuation +0.77%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,349 | reorder_point 5,898 | +7.66% | 1.000 | 0.0 | 472 | 130 | [None, 0, None] | 2,408 | 2,980 / 2,980 |
| 11 | continuation | 5,777 | reorder_point 5,681 | +1.69% | 1.000 | 0.0 | 472 | 130 | [None, 0, None] | 2,408 | 2,980 / 2,980 |
| 11 | continuation_landed | 5,777 | reorder_point 5,681 | +1.69% | 1.000 | 0.0 | 472 | 130 | [None, 0, None] | 2,408 | 2,980 / 2,980 |
| 13 | salvage | 7,612 | reorder_point 7,147 | +6.51% | 1.000 | 0.0 | 530 | 260 | [0, 0, None] | 3,160 | 3,903 / 3,903 |
| 13 | continuation | 6,869 | reorder_point 6,749 | +1.78% | 1.000 | 0.0 | 530 | 260 | [0, 0, None] | 3,160 | 3,903 / 3,903 |
| 13 | continuation_landed | 6,869 | reorder_point 6,749 | +1.78% | 1.000 | 0.0 | 530 | 260 | [0, 0, None] | 3,160 | 3,903 / 3,903 |
| 15 | salvage | 8,413 | reorder_point 7,937 | +6.00% | 1.000 | 0.0 | 594 | 0 | [None, None, None] | 2,377 | 2,943 / 2,943 |
| 15 | continuation | 7,848 | reorder_point 7,727 | +1.57% | 1.000 | 0.0 | 594 | 0 | [None, None, None] | 2,377 | 2,943 / 2,943 |
| 15 | continuation_landed | 7,848 | reorder_point 7,727 | +1.57% | 1.000 | 0.0 | 594 | 0 | [None, None, None] | 2,377 | 2,943 / 2,943 |
| 17 | salvage | 9,212 | reorder_point 9,167 | +0.50% | 1.000 | 0.0 | 398 | 0 | [None, None, None] | 1,591 | 1,974 / 1,974 |
| 17 | continuation | 8,830 | reorder_point 8,771 | +0.67% | 1.000 | 0.0 | 398 | 0 | [None, None, None] | 1,591 | 1,974 / 1,974 |
| 17 | continuation_landed | 8,830 | reorder_point 8,771 | +0.67% | 1.000 | 0.0 | 398 | 0 | [None, None, None] | 1,591 | 1,974 / 1,974 |
| 19 | salvage | 10,203 | reorder_point 9,976 | +2.27% | 1.000 | 0.0 | 356 | 0 | [None, None, None] | 1,425 | 1,772 / 1,772 |
| 19 | continuation | 9,857 | reorder_point 9,772 | +0.87% | 1.000 | 0.0 | 356 | 0 | [None, None, None] | 1,425 | 1,772 / 1,772 |
| 19 | continuation_landed | 9,857 | reorder_point 9,772 | +0.87% | 1.000 | 0.0 | 356 | 0 | [None, None, None] | 1,425 | 1,772 / 1,772 |
| 23 | salvage | 12,284 | reorder_point 12,019 | +2.20% | 1.000 | 0.0 | 219 | 153 | [None, 0, None] | 1,485 | 1,845 / 1,845 |
| 23 | continuation | 11,923 | reorder_point 11,823 | +0.85% | 1.000 | 0.0 | 219 | 153 | [None, 0, None] | 1,485 | 1,845 / 1,845 |
| 23 | continuation_landed | 11,923 | reorder_point 11,823 | +0.85% | 1.000 | 0.0 | 219 | 153 | [None, 0, None] | 1,485 | 1,845 / 1,845 |
| 35 | salvage | 18,219 | reorder_point 18,048 | +0.94% | 1.000 | 0.0 | 271 | 0 | [None, None, None] | 1,084 | 1,350 / 1,350 |
| 35 | continuation | 17,953 | reorder_point 17,850 | +0.58% | 1.000 | 0.0 | 271 | 0 | [None, None, None] | 1,084 | 1,350 / 1,350 |
| 35 | continuation_landed | 17,953 | reorder_point 17,850 | +0.58% | 1.000 | 0.0 | 271 | 0 | [None, None, None] | 1,084 | 1,350 / 1,350 |
| 47 | salvage | 24,531 | reorder_point 24,077 | +1.89% | 1.000 | 0.0 | 382 | 130 | [None, 0, None] | 2,047 | 2,536 / 2,536 |
| 47 | continuation | 24,043 | reorder_point 23,876 | +0.70% | 1.000 | 0.0 | 382 | 130 | [None, 0, None] | 2,047 | 2,536 / 2,536 |
| 47 | continuation_landed | 24,043 | reorder_point 23,876 | +0.70% | 1.000 | 0.0 | 382 | 130 | [None, 0, None] | 2,047 | 2,536 / 2,536 |
| 52 | salvage | 26,893 | reorder_point 26,911 | -0.07% | 1.000 | 0.0 | 170 | 186 | [0, None, None] | 1,421 | 1,763 / 1,763 |
| 52 | continuation | 26,551 | reorder_point 26,431 | +0.45% | 1.000 | 0.0 | 170 | 186 | [0, None, None] | 1,421 | 1,763 / 1,763 |
| 52 | continuation_landed | 26,551 | reorder_point 26,431 | +0.45% | 1.000 | 0.0 | 170 | 186 | [0, None, None] | 1,421 | 1,763 / 1,763 |

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
| 35 | salvage | 18,074 | incumbent 17,927 | +0.82% | 0.993 | 23.9 | 34 | 94 | [0, 0, 0] | 511 | 637 / 637 |
| 35 | continuation | 17,948 | incumbent 17,778 | +0.95% | 0.993 | 23.9 | 34 | 94 | [0, 0, 0] | 511 | 637 / 637 |
| 35 | continuation_landed | 17,948 | incumbent 17,778 | +0.95% | 0.993 | 23.9 | 34 | 94 | [0, 0, 0] | 511 | 637 / 637 |
| 47 | salvage | 24,062 | incumbent 23,910 | +0.64% | 0.995 | 24.7 | 40 | 94 | [0, 0, 0] | 538 | 671 / 671 |
| 47 | continuation | 23,929 | incumbent 23,755 | +0.73% | 0.995 | 24.7 | 40 | 94 | [0, 0, 0] | 538 | 671 / 671 |
| 47 | continuation_landed | 23,929 | incumbent 23,755 | +0.73% | 0.995 | 24.7 | 40 | 94 | [0, 0, 0] | 538 | 671 / 671 |
| 52 | salvage | 26,547 | incumbent 26,396 | +0.57% | 0.995 | 24.7 | 20 | 94 | [0, 0, 0] | 456 | 569 / 569 |
| 52 | continuation | 26,434 | incumbent 26,261 | +0.66% | 0.995 | 24.7 | 20 | 94 | [0, 0, 0] | 456 | 569 / 569 |
| 52 | continuation_landed | 26,434 | incumbent 26,261 | +0.66% | 0.995 | 24.7 | 20 | 94 | [0, 0, 0] | 456 | 569 / 569 |

### E_pallet_multiple (valid to W = 52; legacy 12-week: salvage -0.00%, continuation +0.00%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,242 | incumbent 6,239 | +0.04% | 1.000 | 0.0 | 155 | 66 | [0, None, None] | 884 | 1,102 / 1,168 |
| 11 | continuation | 6,024 | incumbent 6,021 | +0.04% | 1.000 | 0.0 | 155 | 66 | [0, None, None] | 884 | 1,102 / 1,168 |
| 11 | continuation_landed | 5,958 | incumbent 5,955 | +0.04% | 1.000 | 0.0 | 155 | 66 | [0, None, None] | 884 | 1,102 / 1,168 |
| 13 | salvage | 7,334 | incumbent 7,331 | +0.05% | 1.000 | 0.0 | 84 | 130 | [0, 0, None] | 854 | 1,065 / 1,129 |
| 13 | continuation | 7,124 | incumbent 7,120 | +0.06% | 1.000 | 0.0 | 84 | 130 | [0, 0, None] | 854 | 1,065 / 1,129 |
| 13 | continuation_landed | 7,060 | incumbent 7,056 | +0.06% | 1.000 | 0.0 | 84 | 130 | [0, 0, None] | 854 | 1,065 / 1,129 |
| 15 | salvage | 8,412 | incumbent 8,400 | +0.14% | 0.999 | 1.7 | 85 | 130 | [0, 0, None] | 861 | 1,072 / 1,137 |
| 15 | continuation | 8,200 | incumbent 8,191 | +0.11% | 0.999 | 1.7 | 85 | 130 | [0, 0, None] | 861 | 1,072 / 1,137 |
| 15 | continuation_landed | 8,135 | incumbent 8,127 | +0.11% | 0.999 | 1.7 | 85 | 130 | [0, 0, None] | 861 | 1,072 / 1,137 |
| 17 | salvage | 9,480 | incumbent 9,469 | +0.12% | 0.999 | 1.7 | 149 | 65 | [0, None, None] | 856 | 1,066 / 1,131 |
| 17 | continuation | 9,270 | incumbent 9,261 | +0.10% | 0.999 | 1.7 | 149 | 65 | [0, None, None] | 856 | 1,066 / 1,131 |
| 17 | continuation_landed | 9,206 | incumbent 9,197 | +0.09% | 0.999 | 1.7 | 149 | 65 | [0, None, None] | 856 | 1,066 / 1,131 |
| 19 | salvage | 10,568 | incumbent 10,557 | +0.11% | 0.999 | 1.7 | 78 | 130 | [0, None, 0] | 831 | 1,035 / 1,098 |
| 19 | continuation | 10,364 | incumbent 10,354 | +0.09% | 0.999 | 1.7 | 78 | 130 | [0, None, 0] | 831 | 1,035 / 1,098 |
| 19 | continuation_landed | 10,301 | incumbent 10,293 | +0.09% | 0.999 | 1.7 | 78 | 130 | [0, None, 0] | 831 | 1,035 / 1,098 |
| 23 | salvage | 12,727 | incumbent 12,719 | +0.06% | 0.999 | 1.7 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 23 | continuation | 12,530 | incumbent 12,526 | +0.03% | 0.999 | 1.7 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 23 | continuation_landed | 12,470 | incumbent 12,467 | +0.03% | 0.999 | 1.7 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 35 | salvage | 19,112 | incumbent 19,106 | +0.03% | 1.000 | 1.7 | 133 | 65 | [None, None, 0] | 793 | 988 / 1,047 |
| 35 | continuation | 18,917 | incumbent 18,915 | +0.01% | 1.000 | 1.7 | 133 | 65 | [None, None, 0] | 793 | 988 / 1,047 |
| 35 | continuation_landed | 18,858 | incumbent 18,856 | +0.01% | 1.000 | 1.7 | 133 | 65 | [None, None, 0] | 793 | 988 / 1,047 |
| 47 | salvage | 25,473 | incumbent 25,484 | -0.04% | 1.000 | 1.8 | 138 | 65 | [None, None, 0] | 812 | 1,012 / 1,073 |
| 47 | continuation | 25,273 | incumbent 25,285 | -0.05% | 1.000 | 1.8 | 138 | 65 | [None, None, 0] | 812 | 1,012 / 1,073 |
| 47 | continuation_landed | 25,213 | incumbent 25,224 | -0.05% | 1.000 | 1.8 | 138 | 65 | [None, None, 0] | 812 | 1,012 / 1,073 |
| 52 | salvage | 28,103 | incumbent 28,199 | -0.34% | 1.000 | 1.8 | 102 | 64 | [None, None, 0] | 664 | 827 / 877 |
| 52 | continuation | 27,940 | incumbent 27,971 | -0.11% | 1.000 | 1.8 | 102 | 64 | [None, None, 0] | 664 | 827 / 877 |
| 52 | continuation_landed | 27,890 | incumbent 27,901 | -0.04% | 1.000 | 1.8 | 102 | 64 | [None, None, 0] | 664 | 827 / 877 |

### F_mov_two_skus (valid to W = 52; legacy 12-week: salvage +0.24%, continuation +0.28%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 12,293 | periodic:2 11,766 | +4.48% | 0.998 | 3.5 | 637 | 262 | [0, None, 0] | 3,594 | 4,459 / 4,459 |
| 11 | continuation | 11,429 | periodic:2 11,311 | +1.04% | 0.998 | 3.5 | 637 | 262 | [0, None, 0] | 3,594 | 4,459 / 4,459 |
| 11 | continuation_landed | 11,429 | periodic:2 11,311 | +1.04% | 0.998 | 3.5 | 637 | 262 | [0, None, 0] | 3,594 | 4,459 / 4,459 |
| 13 | salvage | 14,383 | periodic:2 13,812 | +4.14% | 0.999 | 3.5 | 631 | 312 | [0, 0, None] | 3,769 | 4,673 / 4,673 |
| 13 | continuation | 13,480 | periodic:2 13,360 | +0.89% | 0.999 | 3.5 | 631 | 312 | [0, 0, None] | 3,769 | 4,673 / 4,673 |
| 13 | continuation_landed | 13,480 | periodic:2 13,360 | +0.89% | 0.999 | 3.5 | 631 | 312 | [0, 0, None] | 3,769 | 4,673 / 4,673 |
| 15 | salvage | 16,416 | periodic:2 15,828 | +3.71% | 0.999 | 3.5 | 676 | 263 | [None, 0, 0] | 3,757 | 4,662 / 4,662 |
| 15 | continuation | 15,511 | periodic:2 15,380 | +0.85% | 0.999 | 3.5 | 676 | 263 | [None, 0, 0] | 3,757 | 4,662 / 4,662 |
| 15 | continuation_landed | 15,511 | periodic:2 15,380 | +0.85% | 0.999 | 3.5 | 676 | 263 | [None, 0, 0] | 3,757 | 4,662 / 4,662 |
| 17 | salvage | 18,191 | periodic:2 17,878 | +1.76% | 0.999 | 3.5 | 667 | 0 | [None, None, None] | 2,668 | 3,312 / 3,312 |
| 17 | continuation | 17,548 | periodic:2 17,437 | +0.64% | 0.999 | 3.5 | 667 | 0 | [None, None, None] | 2,668 | 3,312 / 3,312 |
| 17 | continuation_landed | 17,548 | periodic:2 17,437 | +0.64% | 0.999 | 3.5 | 667 | 0 | [None, None, None] | 2,668 | 3,312 / 3,312 |
| 19 | salvage | 20,366 | periodic:2 19,910 | +2.29% | 0.999 | 3.5 | 533 | 261 | [0, None, 0] | 3,175 | 3,937 / 3,937 |
| 19 | continuation | 19,604 | periodic:2 19,470 | +0.69% | 0.999 | 3.5 | 533 | 261 | [0, None, 0] | 3,175 | 3,937 / 3,937 |
| 19 | continuation_landed | 19,604 | periodic:2 19,470 | +0.69% | 0.999 | 3.5 | 533 | 261 | [0, None, 0] | 3,175 | 3,937 / 3,937 |
| 23 | salvage | 24,605 | periodic:2 24,003 | +2.51% | 0.999 | 3.5 | 651 | 272 | [None, 0, 0] | 3,694 | 4,581 / 4,581 |
| 23 | continuation | 23,718 | periodic:2 23,555 | +0.69% | 0.999 | 3.5 | 651 | 272 | [None, 0, 0] | 3,694 | 4,581 / 4,581 |
| 23 | continuation_landed | 23,718 | periodic:2 23,555 | +0.69% | 0.999 | 3.5 | 651 | 272 | [None, 0, 0] | 3,694 | 4,581 / 4,581 |
| 35 | salvage | 36,610 | periodic:2 36,021 | +1.64% | 0.999 | 3.5 | 736 | 131 | [None, 0, None] | 3,468 | 4,307 / 4,307 |
| 35 | continuation | 35,771 | periodic:2 35,555 | +0.61% | 0.999 | 3.5 | 736 | 131 | [None, 0, None] | 3,468 | 4,307 / 4,307 |
| 35 | continuation_landed | 35,771 | periodic:2 35,555 | +0.61% | 0.999 | 3.5 | 736 | 131 | [None, 0, None] | 3,468 | 4,307 / 4,307 |
| 47 | salvage | 48,764 | periodic:2 48,127 | +1.32% | 1.000 | 3.5 | 585 | 299 | [0, 0, None] | 3,536 | 4,379 / 4,379 |
| 47 | continuation | 47,921 | periodic:2 47,664 | +0.54% | 1.000 | 3.5 | 585 | 299 | [0, 0, None] | 3,536 | 4,379 / 4,379 |
| 47 | continuation_landed | 47,921 | periodic:2 47,664 | +0.54% | 1.000 | 3.5 | 585 | 299 | [0, 0, None] | 3,536 | 4,379 / 4,379 |
| 52 | salvage | 54,043 | periodic:2 52,929 | +2.11% | 1.000 | 3.5 | 819 | 260 | [None, 0, 0] | 4,314 | 5,340 / 5,340 |
| 52 | continuation | 53,017 | periodic:2 52,657 | +0.68% | 1.000 | 3.5 | 819 | 260 | [None, 0, 0] | 4,314 | 5,340 / 5,340 |
| 52 | continuation_landed | 53,017 | periodic:2 52,657 | +0.68% | 1.000 | 3.5 | 819 | 260 | [None, 0, 0] | 4,314 | 5,340 / 5,340 |

### G_freight_tiers (valid to W = 52; legacy 12-week: salvage -10.01%, continuation -0.41%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 16,798 | economic_lot 16,720 | +0.47% | 1.000 | 0.5 | 1280 | 610 | [None, None, 0] | 7,561 | 9,320 / 11,048 |
| 11 | continuation | 15,039 | economic_lot 14,837 | +1.36% | 1.000 | 0.5 | 1280 | 610 | [None, None, 0] | 7,561 | 9,320 / 11,048 |
| 11 | continuation_landed | 13,311 | economic_lot 13,211 | +0.76% | 1.000 | 0.5 | 1280 | 610 | [None, None, 0] | 7,561 | 9,320 / 11,048 |
| 13 | salvage | 18,449 | economic_lot 18,375 | +0.40% | 1.000 | 0.5 | 1489 | 0 | [None, None, None] | 5,956 | 7,364 / 8,727 |
| 13 | continuation | 17,041 | economic_lot 16,838 | +1.21% | 1.000 | 0.5 | 1489 | 0 | [None, None, None] | 5,956 | 7,364 / 8,727 |
| 13 | continuation_landed | 15,678 | economic_lot 15,532 | +0.94% | 1.000 | 0.5 | 1489 | 0 | [None, None, None] | 5,956 | 7,364 / 8,727 |
| 15 | salvage | 20,068 | economic_lot 19,998 | +0.35% | 1.000 | 0.5 | 1093 | 0 | [None, None, None] | 4,371 | 5,419 / 6,420 |
| 15 | continuation | 19,021 | economic_lot 18,818 | +1.08% | 1.000 | 0.5 | 1093 | 0 | [None, None, None] | 4,371 | 5,419 / 6,420 |
| 15 | continuation_landed | 18,019 | economic_lot 17,829 | +1.07% | 1.000 | 0.5 | 1093 | 0 | [None, None, None] | 4,371 | 5,419 / 6,420 |
| 17 | salvage | 22,942 | economic_lot 21,625 | +6.09% | 1.000 | 0.5 | 693 | 654 | [0, None, None] | 5,387 | 6,643 / 7,829 |
| 17 | continuation | 21,686 | economic_lot 20,816 | +4.18% | 1.000 | 0.5 | 693 | 654 | [0, None, None] | 5,387 | 6,643 / 7,829 |
| 17 | continuation_landed | 20,500 | economic_lot 20,147 | +1.75% | 1.000 | 0.5 | 693 | 654 | [0, None, None] | 5,387 | 6,643 / 7,829 |
| 19 | salvage | 24,562 | economic_lot 23,231 | +5.73% | 1.000 | 0.5 | 949 | 0 | [None, None, None] | 3,797 | 4,689 / 5,517 |
| 19 | continuation | 23,671 | economic_lot 22,800 | +3.82% | 1.000 | 0.5 | 949 | 0 | [None, None, None] | 3,797 | 4,689 / 5,517 |
| 19 | continuation_landed | 22,843 | economic_lot 22,449 | +1.75% | 1.000 | 0.5 | 949 | 0 | [None, None, None] | 3,797 | 4,689 / 5,517 |
| 23 | salvage | 30,365 | economic_lot 30,982 | -1.99% | 1.000 | 0.5 | 1452 | 0 | [None, None, None] | 5,810 | 7,187 / 8,462 |
| 23 | continuation | 28,988 | economic_lot 29,370 | -1.30% | 1.000 | 0.5 | 1452 | 0 | [None, None, None] | 5,810 | 7,187 / 8,462 |
| 23 | continuation_landed | 27,713 | economic_lot 27,867 | -0.55% | 1.000 | 0.5 | 1452 | 0 | [None, None, None] | 5,810 | 7,187 / 8,462 |
| 35 | salvage | 43,678 | economic_lot 45,568 | -4.15% | 1.000 | 0.5 | 987 | 0 | [None, None, None] | 3,950 | 4,900 / 5,756 |
| 35 | continuation | 42,727 | economic_lot 44,103 | -3.12% | 1.000 | 0.5 | 987 | 0 | [None, None, None] | 3,950 | 4,900 / 5,756 |
| 35 | continuation_landed | 41,871 | economic_lot 42,583 | -1.67% | 1.000 | 0.5 | 987 | 0 | [None, None, None] | 3,950 | 4,900 / 5,756 |
| 47 | salvage | 58,584 | economic_lot 60,213 | -2.70% | 0.999 | 7.4 | 597 | 657 | [0, None, None] | 5,018 | 6,197 / 7,286 |
| 47 | continuation | 57,405 | economic_lot 58,896 | -2.53% | 0.999 | 7.4 | 597 | 657 | [0, None, None] | 5,018 | 6,197 / 7,286 |
| 47 | continuation_landed | 56,317 | economic_lot 57,487 | -2.04% | 0.999 | 7.4 | 597 | 657 | [0, None, None] | 5,018 | 6,197 / 7,286 |
| 52 | salvage | 65,153 | economic_lot 65,440 | -0.44% | 0.999 | 7.4 | 1574 | 0 | [None, None, None] | 6,297 | 7,778 / 9,154 |
| 52 | continuation | 63,671 | economic_lot 64,438 | -1.19% | 0.999 | 7.4 | 1574 | 0 | [None, None, None] | 6,297 | 7,778 / 9,154 |
| 52 | continuation_landed | 62,296 | economic_lot 63,421 | -1.77% | 0.999 | 7.4 | 1574 | 0 | [None, None, None] | 6,297 | 7,778 / 9,154 |

### H_per_pallet_freight (valid to W = 52; legacy 12-week: salvage -3.73%, continuation -2.29%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,716 | periodic:2 6,826 | -1.61% | 1.000 | 0.0 | 248 | 31 | [None, None, 0] | 1,116 | 1,389 / 1,557 |
| 11 | continuation | 6,443 | periodic:2 6,610 | -2.53% | 1.000 | 0.0 | 248 | 31 | [None, None, 0] | 1,116 | 1,389 / 1,557 |
| 11 | continuation_landed | 6,275 | periodic:2 6,448 | -2.69% | 1.000 | 0.0 | 248 | 31 | [None, None, 0] | 1,116 | 1,389 / 1,557 |
| 13 | salvage | 7,678 | periodic:2 8,027 | -4.35% | 1.000 | 0.0 | 103 | 50 | [0, None, 0] | 615 | 768 / 862 |
| 13 | continuation | 7,526 | periodic:2 7,810 | -3.64% | 1.000 | 0.0 | 103 | 50 | [0, None, 0] | 615 | 768 / 862 |
| 13 | continuation_landed | 7,431 | periodic:2 7,645 | -2.80% | 1.000 | 0.0 | 103 | 50 | [0, None, 0] | 615 | 768 / 862 |
| 15 | salvage | 8,810 | periodic:2 9,162 | -3.84% | 1.000 | 0.0 | 49 | 97 | [0, 0, 0] | 583 | 728 / 819 |
| 15 | continuation | 8,666 | periodic:2 8,951 | -3.18% | 1.000 | 0.0 | 49 | 97 | [0, 0, 0] | 583 | 728 / 819 |
| 15 | continuation_landed | 8,575 | periodic:2 8,791 | -2.47% | 1.000 | 0.0 | 49 | 97 | [0, 0, 0] | 583 | 728 / 819 |
| 17 | salvage | 10,006 | periodic:2 10,293 | -2.79% | 1.000 | 0.0 | 78 | 97 | [0, 0, None] | 703 | 876 / 986 |
| 17 | continuation | 9,832 | periodic:2 10,093 | -2.58% | 1.000 | 0.0 | 78 | 97 | [0, 0, None] | 703 | 876 / 986 |
| 17 | continuation_landed | 9,722 | periodic:2 9,942 | -2.21% | 1.000 | 0.0 | 78 | 97 | [0, 0, None] | 703 | 876 / 986 |
| 19 | salvage | 11,149 | periodic:2 11,559 | -3.54% | 0.997 | 5.6 | 46 | 90 | [0, 0, 0] | 545 | 680 / 768 |
| 19 | continuation | 11,014 | periodic:2 11,343 | -2.90% | 0.997 | 5.6 | 46 | 90 | [0, 0, 0] | 545 | 680 / 768 |
| 19 | continuation_landed | 10,926 | periodic:2 11,179 | -2.26% | 0.997 | 5.6 | 46 | 90 | [0, 0, 0] | 545 | 680 / 768 |
| 23 | salvage | 13,539 | periodic:2 13,931 | -2.82% | 0.998 | 5.6 | 157 | 32 | [None, 0, None] | 756 | 942 / 1,062 |
| 23 | continuation | 13,353 | periodic:2 13,709 | -2.59% | 0.998 | 5.6 | 157 | 32 | [None, 0, None] | 756 | 942 / 1,062 |
| 23 | continuation_landed | 13,233 | periodic:2 13,540 | -2.27% | 0.998 | 5.6 | 157 | 32 | [None, 0, None] | 756 | 942 / 1,062 |
| 35 | salvage | 20,403 | periodic:2 20,838 | -2.09% | 0.998 | 7.2 | 137 | 96 | [0, None, 0] | 931 | 1,160 / 1,308 |
| 35 | continuation | 20,174 | periodic:2 20,622 | -2.17% | 0.998 | 7.2 | 137 | 96 | [0, None, 0] | 931 | 1,160 / 1,308 |
| 35 | continuation_landed | 20,027 | periodic:2 20,460 | -2.12% | 0.998 | 7.2 | 137 | 96 | [0, None, 0] | 931 | 1,160 / 1,308 |
| 47 | salvage | 27,221 | periodic:2 27,796 | -2.07% | 0.997 | 13.0 | 196 | 65 | [0, 0, None] | 1,047 | 1,302 / 1,466 |
| 47 | continuation | 26,966 | periodic:2 27,578 | -2.22% | 0.997 | 13.0 | 196 | 65 | [0, 0, None] | 1,047 | 1,302 / 1,466 |
| 47 | continuation_landed | 26,802 | periodic:2 27,413 | -2.23% | 0.997 | 13.0 | 196 | 65 | [0, 0, None] | 1,047 | 1,302 / 1,466 |
| 52 | salvage | 29,876 | periodic:2 30,455 | -1.90% | 0.997 | 13.0 | 126 | 27 | [0, None, None] | 612 | 764 / 861 |
| 52 | continuation | 29,725 | periodic:2 30,353 | -2.07% | 0.997 | 13.0 | 126 | 27 | [0, None, None] | 612 | 764 / 861 |
| 52 | continuation_landed | 29,628 | periodic:2 30,277 | -2.14% | 0.997 | 13.0 | 126 | 27 | [0, None, None] | 612 | 764 / 861 |

### I_max_pallets_ftl_cap (valid to W = 52; legacy 12-week: salvage +0.53%, continuation +3.05%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 9,855 | economic_lot 9,814 | +0.42% | 1.000 | 0.0 | 365 | 0 | [None, None, None] | 1,460 | 1,815 / 2,829 |
| 11 | continuation | 9,500 | economic_lot 9,456 | +0.47% | 1.000 | 0.0 | 365 | 0 | [None, None, None] | 1,460 | 1,815 / 2,829 |
| 11 | continuation_landed | 8,486 | economic_lot 8,433 | +0.63% | 1.000 | 0.0 | 365 | 0 | [None, None, None] | 1,460 | 1,815 / 2,829 |
| 13 | salvage | 10,674 | economic_lot 10,632 | +0.39% | 1.000 | 0.0 | 162 | 0 | [None, None, None] | 648 | 808 / 1,258 |
| 13 | continuation | 10,514 | economic_lot 10,469 | +0.42% | 1.000 | 0.0 | 162 | 0 | [None, None, None] | 648 | 808 / 1,258 |
| 13 | continuation_landed | 10,064 | economic_lot 10,011 | +0.53% | 1.000 | 0.0 | 162 | 0 | [None, None, None] | 648 | 808 / 1,258 |
| 15 | salvage | 13,212 | economic_lot 13,171 | +0.31% | 1.000 | 0.0 | 258 | 145 | [0, None, None] | 1,614 | 2,006 / 3,126 |
| 15 | continuation | 12,821 | economic_lot 12,776 | +0.35% | 1.000 | 0.0 | 258 | 145 | [0, None, None] | 1,614 | 2,006 / 3,126 |
| 15 | continuation_landed | 11,700 | economic_lot 11,647 | +0.45% | 1.000 | 0.0 | 258 | 145 | [0, None, None] | 1,614 | 2,006 / 3,126 |
| 17 | salvage | 15,164 | economic_lot 13,964 | +8.59% | 1.000 | 0.0 | 354 | 148 | [None, 0, None] | 2,005 | 2,485 / 3,878 |
| 17 | continuation | 14,684 | economic_lot 13,758 | +6.73% | 1.000 | 0.0 | 354 | 148 | [None, 0, None] | 2,005 | 2,485 / 3,878 |
| 17 | continuation_landed | 13,291 | economic_lot 13,174 | +0.89% | 1.000 | 0.0 | 354 | 148 | [None, 0, None] | 2,005 | 2,485 / 3,878 |
| 19 | salvage | 16,560 | economic_lot 16,522 | +0.23% | 1.000 | 0.0 | 447 | 0 | [None, None, None] | 1,788 | 2,221 / 3,463 |
| 19 | continuation | 16,127 | economic_lot 16,090 | +0.23% | 1.000 | 0.0 | 447 | 0 | [None, None, None] | 1,788 | 2,221 / 3,463 |
| 19 | continuation_landed | 14,885 | economic_lot 14,850 | +0.24% | 1.000 | 0.0 | 447 | 0 | [None, None, None] | 1,788 | 2,221 / 3,463 |
| 23 | salvage | 19,925 | economic_lot 19,879 | +0.23% | 1.000 | 0.0 | 339 | 146 | [0, None, None] | 1,942 | 2,411 / 3,760 |
| 23 | continuation | 19,456 | economic_lot 19,410 | +0.24% | 1.000 | 0.0 | 339 | 146 | [0, None, None] | 1,942 | 2,411 / 3,760 |
| 23 | continuation_landed | 18,107 | economic_lot 18,060 | +0.26% | 1.000 | 0.0 | 339 | 146 | [0, None, None] | 1,942 | 2,411 / 3,760 |
| 35 | salvage | 28,140 | economic_lot 28,093 | +0.17% | 1.000 | 0.0 | 195 | 0 | [None, None, None] | 779 | 971 / 1,512 |
| 35 | continuation | 27,948 | economic_lot 27,903 | +0.16% | 1.000 | 0.0 | 195 | 0 | [None, None, None] | 779 | 971 / 1,512 |
| 35 | continuation_landed | 27,407 | economic_lot 27,367 | +0.15% | 1.000 | 0.0 | 195 | 0 | [None, None, None] | 779 | 971 / 1,512 |
| 47 | salvage | 38,703 | economic_lot 38,052 | +1.71% | 0.999 | 6.1 | 357 | 146 | [None, 0, None] | 2,013 | 2,495 / 3,892 |
| 47 | continuation | 38,221 | economic_lot 37,721 | +1.33% | 0.999 | 6.1 | 357 | 146 | [None, 0, None] | 2,013 | 2,495 / 3,892 |
| 47 | continuation_landed | 36,823 | economic_lot 36,778 | +0.12% | 0.999 | 6.1 | 357 | 146 | [None, 0, None] | 2,013 | 2,495 / 3,892 |
| 52 | salvage | 41,854 | economic_lot 41,758 | +0.23% | 0.999 | 6.1 | 306 | 0 | [None, None, None] | 1,223 | 1,522 / 2,371 |
| 52 | continuation | 41,555 | economic_lot 41,472 | +0.20% | 0.999 | 6.1 | 306 | 0 | [None, None, None] | 1,223 | 1,522 / 2,371 |
| 52 | continuation_landed | 40,706 | economic_lot 40,662 | +0.11% | 0.999 | 6.1 | 306 | 0 | [None, None, None] | 1,223 | 1,522 / 2,371 |

### J_net60_cost_of_capital (valid to W = 52; legacy 12-week: salvage -11.06%, continuation -3.52%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,096 | periodic:2 6,850 | +3.59% | 1.000 | 0.0 | 1003 | 0 | [None, None, None] | 4,011 | 4,853 / 4,980 |
| 11 | continuation | 6,254 | economic_lot 6,182 | +1.17% | 1.000 | 0.0 | 1003 | 0 | [None, None, None] | 4,011 | 4,853 / 4,980 |
| 11 | continuation_landed | 6,126 | economic_lot 6,071 | +0.92% | 1.000 | 0.0 | 1003 | 0 | [None, None, None] | 4,011 | 4,853 / 4,980 |
| 13 | salvage | 7,933 | periodic:2 8,044 | -1.38% | 1.000 | 0.0 | 800 | 0 | [None, None, None] | 3,198 | 3,889 / 3,992 |
| 13 | continuation | 7,242 | economic_lot 7,317 | -1.02% | 1.000 | 0.0 | 800 | 0 | [None, None, None] | 3,198 | 3,889 / 3,992 |
| 13 | continuation_landed | 7,140 | economic_lot 7,186 | -0.64% | 1.000 | 0.0 | 800 | 0 | [None, None, None] | 3,198 | 3,889 / 3,992 |
| 15 | salvage | 8,925 | economic_lot 8,948 | -0.25% | 1.000 | 0.0 | 720 | 0 | [None, None, None] | 2,880 | 3,520 / 3,617 |
| 15 | continuation | 8,285 | economic_lot 8,277 | +0.10% | 1.000 | 0.0 | 720 | 0 | [None, None, None] | 2,880 | 3,520 / 3,617 |
| 15 | continuation_landed | 8,188 | economic_lot 8,174 | +0.18% | 1.000 | 0.0 | 720 | 0 | [None, None, None] | 2,880 | 3,520 / 3,617 |
| 17 | salvage | 10,014 | economic_lot 9,751 | +2.70% | 1.000 | 0.0 | 523 | 214 | [None, 0, None] | 2,948 | 3,613 / 3,723 |
| 17 | continuation | 9,350 | economic_lot 9,245 | +1.13% | 1.000 | 0.0 | 523 | 214 | [None, 0, None] | 2,948 | 3,613 / 3,723 |
| 17 | continuation_landed | 9,239 | economic_lot 9,169 | +0.77% | 1.000 | 0.0 | 523 | 214 | [None, 0, None] | 2,948 | 3,613 / 3,723 |
| 19 | salvage | 10,838 | economic_lot 10,564 | +2.60% | 1.000 | 0.0 | 537 | 0 | [None, None, None] | 2,147 | 2,645 / 2,725 |
| 19 | continuation | 10,340 | economic_lot 10,235 | +1.03% | 1.000 | 0.0 | 537 | 0 | [None, None, None] | 2,147 | 2,645 / 2,725 |
| 19 | continuation_landed | 10,260 | economic_lot 10,186 | +0.72% | 1.000 | 0.0 | 537 | 0 | [None, None, None] | 2,147 | 2,645 / 2,725 |
| 23 | salvage | 12,746 | economic_lot 13,565 | -6.04% | 1.000 | 0.0 | 137 | 214 | [0, None, None] | 1,406 | 1,732 / 1,785 |
| 23 | continuation | 12,420 | economic_lot 12,674 | -2.01% | 1.000 | 0.0 | 137 | 214 | [0, None, None] | 1,406 | 1,732 / 1,785 |
| 23 | continuation_landed | 12,366 | economic_lot 12,533 | -1.33% | 1.000 | 0.0 | 137 | 214 | [0, None, None] | 1,406 | 1,732 / 1,785 |
| 35 | salvage | 19,195 | economic_lot 19,713 | -2.63% | 0.999 | 2.1 | 442 | 0 | [None, None, None] | 1,767 | 2,176 / 2,248 |
| 35 | continuation | 18,786 | economic_lot 18,888 | -0.54% | 0.999 | 2.1 | 442 | 0 | [None, None, None] | 1,767 | 2,176 / 2,248 |
| 35 | continuation_landed | 18,714 | economic_lot 18,758 | -0.24% | 0.999 | 2.1 | 442 | 0 | [None, None, None] | 1,767 | 2,176 / 2,248 |
| 47 | salvage | 25,490 | economic_lot 25,850 | -1.40% | 1.000 | 2.1 | 406 | 0 | [None, None, None] | 1,623 | 2,003 / 2,070 |
| 47 | continuation | 25,109 | economic_lot 25,085 | +0.10% | 1.000 | 2.1 | 406 | 0 | [None, None, None] | 1,623 | 2,003 / 2,070 |
| 47 | continuation_landed | 25,042 | economic_lot 24,967 | +0.30% | 1.000 | 2.1 | 406 | 0 | [None, None, None] | 1,623 | 2,003 / 2,070 |
| 52 | salvage | 28,795 | economic_lot 27,857 | +3.37% | 1.000 | 2.1 | 539 | 460 | [0, None, None] | 3,997 | 4,807 / 4,968 |
| 52 | continuation | 27,985 | economic_lot 27,505 | +1.74% | 1.000 | 2.1 | 539 | 460 | [0, None, None] | 3,997 | 4,807 / 4,968 |
| 52 | continuation_landed | 27,824 | economic_lot 27,454 | +1.35% | 1.000 | 2.1 | 539 | 460 | [0, None, None] | 3,997 | 4,807 / 4,968 |

### K_deposit_early_cash (valid to W = 52; legacy 12-week: salvage -11.20%, continuation -3.64%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,165 | periodic:2 6,862 | +4.41% | 1.000 | 0.0 | 700 | 365 | [0, None, None] | 4,261 | 5,177 / 5,332 |
| 11 | continuation | 6,249 | economic_lot 6,190 | +0.95% | 1.000 | 0.0 | 700 | 365 | [0, None, None] | 4,261 | 5,177 / 5,332 |
| 11 | continuation_landed | 6,094 | economic_lot 6,079 | +0.24% | 1.000 | 0.0 | 700 | 365 | [0, None, None] | 4,261 | 5,177 / 5,332 |
| 13 | salvage | 8,003 | periodic:2 8,056 | -0.65% | 1.000 | 0.0 | 862 | 0 | [None, None, None] | 3,449 | 4,213 / 4,338 |
| 13 | continuation | 7,239 | economic_lot 7,329 | -1.23% | 1.000 | 0.0 | 862 | 0 | [None, None, None] | 3,449 | 4,213 / 4,338 |
| 13 | continuation_landed | 7,113 | economic_lot 7,198 | -1.18% | 1.000 | 0.0 | 862 | 0 | [None, None, None] | 3,449 | 4,213 / 4,338 |
| 15 | salvage | 8,807 | economic_lot 8,960 | -1.71% | 1.000 | 0.0 | 666 | 0 | [None, None, None] | 2,666 | 3,272 / 3,369 |
| 15 | continuation | 8,200 | economic_lot 8,290 | -1.08% | 1.000 | 0.0 | 666 | 0 | [None, None, None] | 2,666 | 3,272 / 3,369 |
| 15 | continuation_landed | 8,103 | economic_lot 8,186 | -1.01% | 1.000 | 0.0 | 666 | 0 | [None, None, None] | 2,666 | 3,272 / 3,369 |
| 17 | salvage | 9,608 | economic_lot 9,763 | -1.59% | 1.000 | 0.0 | 470 | 0 | [None, None, None] | 1,880 | 2,319 / 2,387 |
| 17 | continuation | 9,169 | economic_lot 9,257 | -0.96% | 1.000 | 0.0 | 470 | 0 | [None, None, None] | 1,880 | 2,319 / 2,387 |
| 17 | continuation_landed | 9,101 | economic_lot 9,181 | -0.88% | 1.000 | 0.0 | 470 | 0 | [None, None, None] | 1,880 | 2,319 / 2,387 |
| 19 | salvage | 10,848 | economic_lot 10,577 | +2.57% | 1.000 | 0.0 | 269 | 322 | [None, None, 0] | 2,365 | 2,894 / 2,982 |
| 19 | continuation | 10,320 | economic_lot 10,247 | +0.71% | 1.000 | 0.0 | 269 | 322 | [None, None, 0] | 2,365 | 2,894 / 2,982 |
| 19 | continuation_landed | 10,232 | economic_lot 10,199 | +0.32% | 1.000 | 0.0 | 269 | 322 | [None, None, 0] | 2,365 | 2,894 / 2,982 |
| 23 | salvage | 13,264 | economic_lot 13,578 | -2.31% | 1.000 | 0.0 | 790 | 0 | [None, None, None] | 3,159 | 3,866 / 3,984 |
| 23 | continuation | 12,557 | economic_lot 12,687 | -1.03% | 1.000 | 0.0 | 790 | 0 | [None, None, None] | 3,159 | 3,866 / 3,984 |
| 23 | continuation_landed | 12,439 | economic_lot 12,546 | -0.85% | 1.000 | 0.0 | 790 | 0 | [None, None, None] | 3,159 | 3,866 / 3,984 |
| 35 | salvage | 19,210 | economic_lot 19,726 | -2.61% | 1.000 | 0.0 | 512 | 0 | [None, None, None] | 2,047 | 2,518 / 2,595 |
| 35 | continuation | 18,739 | economic_lot 18,900 | -0.86% | 1.000 | 0.0 | 512 | 0 | [None, None, None] | 2,047 | 2,518 / 2,595 |
| 35 | continuation_landed | 18,662 | economic_lot 18,771 | -0.58% | 1.000 | 0.0 | 512 | 0 | [None, None, None] | 2,047 | 2,518 / 2,595 |
| 47 | salvage | 25,584 | economic_lot 25,863 | -1.08% | 1.000 | 0.0 | 286 | 341 | [None, 0, None] | 2,509 | 3,069 / 3,166 |
| 47 | continuation | 25,024 | economic_lot 25,097 | -0.29% | 1.000 | 0.0 | 286 | 341 | [None, 0, None] | 2,509 | 3,069 / 3,166 |
| 47 | continuation_landed | 24,928 | economic_lot 24,979 | -0.21% | 1.000 | 0.0 | 286 | 341 | [None, 0, None] | 2,509 | 3,069 / 3,166 |
| 52 | salvage | 28,374 | economic_lot 27,870 | +1.81% | 1.000 | 0.0 | 763 | 0 | [None, None, None] | 3,052 | 3,736 / 3,853 |
| 52 | continuation | 27,690 | economic_lot 27,518 | +0.63% | 1.000 | 0.0 | 763 | 0 | [None, None, None] | 3,052 | 3,736 / 3,853 |
| 52 | continuation_landed | 27,573 | economic_lot 27,467 | +0.39% | 1.000 | 0.0 | 763 | 0 | [None, None, None] | 3,052 | 3,736 / 3,853 |

### L_high_holding_rate (valid to W = 52; legacy 12-week: salvage -10.16%, continuation -4.74%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,206 | periodic:2 6,856 | +5.11% | 1.000 | 0.0 | 698 | 365 | [0, None, None] | 4,249 | 5,147 / 5,301 |
| 11 | continuation | 6,309 | economic_lot 6,332 | -0.36% | 1.000 | 0.0 | 698 | 365 | [0, None, None] | 4,249 | 5,147 / 5,301 |
| 11 | continuation_landed | 6,154 | economic_lot 6,177 | -0.38% | 1.000 | 0.0 | 698 | 365 | [0, None, None] | 4,249 | 5,147 / 5,301 |
| 13 | salvage | 8,071 | periodic:2 8,048 | +0.28% | 1.000 | 0.0 | 859 | 0 | [None, None, None] | 3,437 | 4,188 / 4,313 |
| 13 | continuation | 7,320 | economic_lot 7,342 | -0.30% | 1.000 | 0.0 | 859 | 0 | [None, None, None] | 3,437 | 4,188 / 4,313 |
| 13 | continuation_landed | 7,195 | economic_lot 7,217 | -0.31% | 1.000 | 0.0 | 859 | 0 | [None, None, None] | 3,437 | 4,188 / 4,313 |
| 15 | salvage | 8,895 | economic_lot 8,910 | -0.17% | 1.000 | 0.0 | 663 | 0 | [None, None, None] | 2,654 | 3,251 / 3,348 |
| 15 | continuation | 8,297 | economic_lot 8,320 | -0.27% | 1.000 | 0.0 | 663 | 0 | [None, None, None] | 2,654 | 3,251 / 3,348 |
| 15 | continuation_landed | 8,201 | economic_lot 8,224 | -0.28% | 1.000 | 0.0 | 663 | 0 | [None, None, None] | 2,654 | 3,251 / 3,348 |
| 17 | salvage | 9,711 | economic_lot 9,725 | -0.15% | 1.000 | 0.0 | 467 | 0 | [None, None, None] | 1,868 | 2,301 / 2,369 |
| 17 | continuation | 9,277 | economic_lot 9,301 | -0.25% | 1.000 | 0.0 | 467 | 0 | [None, None, None] | 1,868 | 2,301 / 2,369 |
| 17 | continuation_landed | 9,210 | economic_lot 9,234 | -0.26% | 1.000 | 0.0 | 467 | 0 | [None, None, None] | 1,868 | 2,301 / 2,369 |
| 19 | salvage | 10,764 | economic_lot 10,545 | +2.08% | 1.000 | 0.0 | 267 | 157 | [None, None, 0] | 1,694 | 2,090 / 2,159 |
| 19 | continuation | 10,368 | economic_lot 10,299 | +0.67% | 1.000 | 0.0 | 267 | 157 | [None, None, 0] | 1,694 | 2,090 / 2,159 |
| 19 | continuation_landed | 10,299 | economic_lot 10,262 | +0.37% | 1.000 | 0.0 | 267 | 157 | [None, None, 0] | 1,694 | 2,090 / 2,159 |
| 23 | salvage | 12,963 | economic_lot 13,462 | -3.71% | 1.000 | 0.0 | 428 | 0 | [None, None, None] | 1,713 | 2,111 / 2,183 |
| 23 | continuation | 12,564 | economic_lot 12,704 | -1.10% | 1.000 | 0.0 | 428 | 0 | [None, None, None] | 1,713 | 2,111 / 2,183 |
| 23 | continuation_landed | 12,493 | economic_lot 12,578 | -0.68% | 1.000 | 0.0 | 428 | 0 | [None, None, None] | 1,713 | 2,111 / 2,183 |
| 35 | salvage | 19,589 | economic_lot 19,620 | -0.16% | 1.000 | 0.0 | 332 | 307 | [0, None, None] | 2,554 | 3,121 / 3,233 |
| 35 | continuation | 19,021 | economic_lot 19,022 | -0.00% | 1.000 | 0.0 | 332 | 307 | [0, None, None] | 2,554 | 3,121 / 3,233 |
| 35 | continuation_landed | 18,910 | economic_lot 18,925 | -0.08% | 1.000 | 0.0 | 332 | 307 | [0, None, None] | 2,554 | 3,121 / 3,233 |
| 47 | salvage | 25,793 | economic_lot 25,709 | +0.33% | 1.000 | 0.0 | 500 | 0 | [None, None, None] | 2,001 | 2,463 / 2,550 |
| 47 | continuation | 25,332 | economic_lot 25,274 | +0.23% | 1.000 | 0.0 | 500 | 0 | [None, None, None] | 2,001 | 2,463 / 2,550 |
| 47 | continuation_landed | 25,244 | economic_lot 25,205 | +0.16% | 1.000 | 0.0 | 500 | 0 | [None, None, None] | 2,001 | 2,463 / 2,550 |
| 52 | salvage | 28,574 | economic_lot 28,908 | -1.16% | 1.000 | 0.0 | 613 | 0 | [None, None, None] | 2,451 | 2,995 / 3,103 |
| 52 | continuation | 28,030 | economic_lot 28,077 | -0.17% | 1.000 | 0.0 | 613 | 0 | [None, None, None] | 2,451 | 2,995 / 3,103 |
| 52 | continuation_landed | 27,922 | economic_lot 27,933 | -0.04% | 1.000 | 0.0 | 613 | 0 | [None, None, None] | 2,451 | 2,995 / 3,103 |

### M_order_calendar_wednesday (valid to W = 52; legacy 12-week: salvage -0.54%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,416 | incumbent 6,256 | +2.56% | 0.944 | 62.5 | 99 | 189 | [0, 1, 0] | 1,152 | 1,434 / 1,434 |
| 11 | continuation | 6,134 | incumbent 6,039 | +1.57% | 0.944 | 62.5 | 99 | 189 | [0, 1, 0] | 1,152 | 1,434 / 1,434 |
| 11 | continuation_landed | 6,134 | incumbent 6,039 | +1.57% | 0.944 | 62.5 | 99 | 189 | [0, 1, 0] | 1,152 | 1,434 / 1,434 |
| 13 | salvage | 7,453 | incumbent 7,296 | +2.16% | 0.951 | 64.1 | 86 | 191 | [0, 0, 0] | 1,108 | 1,379 / 1,379 |
| 13 | continuation | 7,182 | incumbent 7,076 | +1.49% | 0.951 | 64.1 | 86 | 191 | [0, 0, 0] | 1,108 | 1,379 / 1,379 |
| 13 | continuation_landed | 7,182 | incumbent 7,076 | +1.49% | 0.951 | 64.1 | 86 | 191 | [0, 0, 0] | 1,108 | 1,379 / 1,379 |
| 15 | salvage | 8,460 | incumbent 8,289 | +2.07% | 0.958 | 64.1 | 81 | 201 | [0, 0, 0] | 1,129 | 1,406 / 1,406 |
| 15 | continuation | 8,184 | incumbent 8,076 | +1.34% | 0.958 | 64.1 | 81 | 201 | [0, 0, 0] | 1,129 | 1,406 / 1,406 |
| 15 | continuation_landed | 8,184 | incumbent 8,076 | +1.34% | 0.958 | 64.1 | 81 | 201 | [0, 0, 0] | 1,129 | 1,406 / 1,406 |
| 17 | salvage | 9,464 | incumbent 9,277 | +2.01% | 0.962 | 64.1 | 86 | 198 | [0, 0, 0] | 1,134 | 1,412 / 1,412 |
| 17 | continuation | 9,186 | incumbent 9,075 | +1.23% | 0.962 | 64.1 | 86 | 198 | [0, 0, 0] | 1,134 | 1,412 / 1,412 |
| 17 | continuation_landed | 9,186 | incumbent 9,075 | +1.23% | 0.962 | 64.1 | 86 | 198 | [0, 0, 0] | 1,134 | 1,412 / 1,412 |
| 19 | salvage | 10,485 | incumbent 10,349 | +1.31% | 0.966 | 64.1 | 83 | 192 | [0, 0, 0] | 1,101 | 1,371 / 1,371 |
| 19 | continuation | 10,216 | incumbent 10,136 | +0.79% | 0.966 | 64.1 | 83 | 192 | [0, 0, 0] | 1,101 | 1,371 / 1,371 |
| 19 | continuation_landed | 10,216 | incumbent 10,136 | +0.79% | 0.966 | 64.1 | 83 | 192 | [0, 0, 0] | 1,101 | 1,371 / 1,371 |
| 23 | salvage | 12,558 | incumbent 12,435 | +0.99% | 0.972 | 64.1 | 118 | 178 | [0, 0, 0] | 1,185 | 1,476 / 1,476 |
| 23 | continuation | 12,268 | incumbent 12,212 | +0.46% | 0.972 | 64.1 | 118 | 178 | [0, 0, 0] | 1,185 | 1,476 / 1,476 |
| 23 | continuation_landed | 12,268 | incumbent 12,212 | +0.46% | 0.972 | 64.1 | 118 | 178 | [0, 0, 0] | 1,185 | 1,476 / 1,476 |
| 35 | salvage | 18,575 | incumbent 18,470 | +0.57% | 0.982 | 64.1 | 97 | 198 | [0, 0, 0] | 1,179 | 1,467 / 1,467 |
| 35 | continuation | 18,287 | incumbent 18,253 | +0.19% | 0.982 | 64.1 | 97 | 198 | [0, 0, 0] | 1,179 | 1,467 / 1,467 |
| 35 | continuation_landed | 18,287 | incumbent 18,253 | +0.19% | 0.982 | 64.1 | 97 | 198 | [0, 0, 0] | 1,179 | 1,467 / 1,467 |
| 47 | salvage | 24,567 | incumbent 24,487 | +0.33% | 0.986 | 64.1 | 134 | 170 | [0, 0, 0] | 1,217 | 1,514 / 1,514 |
| 47 | continuation | 24,269 | incumbent 24,266 | +0.01% | 0.986 | 64.1 | 134 | 170 | [0, 0, 0] | 1,217 | 1,514 / 1,514 |
| 47 | continuation_landed | 24,269 | incumbent 24,266 | +0.01% | 0.986 | 64.1 | 134 | 170 | [0, 0, 0] | 1,217 | 1,514 / 1,514 |
| 52 | salvage | 27,052 | incumbent 26,979 | +0.27% | 0.988 | 64.1 | 91 | 189 | [0, 0, 0] | 1,121 | 1,395 / 1,395 |
| 52 | continuation | 26,778 | incumbent 26,773 | +0.02% | 0.988 | 64.1 | 91 | 189 | [0, 0, 0] | 1,121 | 1,395 / 1,395 |
| 52 | continuation_landed | 26,778 | incumbent 26,773 | +0.02% | 0.988 | 64.1 | 91 | 189 | [0, 0, 0] | 1,121 | 1,395 / 1,395 |

### N_long_lead_21_days (valid to W = 52; legacy 12-week: salvage -0.71%, continuation +0.42%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,056 | incumbent 6,039 | +0.28% | 0.988 | 13.3 | 17 | 299 | [0, 0, 0] | 1,264 | 1,573 / 1,573 |
| 11 | continuation | 5,747 | incumbent 5,723 | +0.42% | 0.988 | 13.3 | 17 | 299 | [0, 0, 0] | 1,264 | 1,573 / 1,573 |
| 11 | continuation_landed | 5,747 | incumbent 5,723 | +0.42% | 0.988 | 13.3 | 17 | 299 | [0, 0, 0] | 1,264 | 1,573 / 1,573 |
| 13 | salvage | 7,141 | incumbent 7,099 | +0.59% | 0.987 | 17.7 | 32 | 299 | [0, 0, 0] | 1,322 | 1,644 / 1,644 |
| 13 | continuation | 6,818 | incumbent 6,780 | +0.57% | 0.987 | 17.7 | 32 | 299 | [0, 0, 0] | 1,322 | 1,644 / 1,644 |
| 13 | continuation_landed | 6,818 | incumbent 6,780 | +0.57% | 0.987 | 17.7 | 32 | 299 | [0, 0, 0] | 1,322 | 1,644 / 1,644 |
| 15 | salvage | 8,129 | incumbent 8,091 | +0.47% | 0.988 | 17.7 | 25 | 295 | [0, 0, 0] | 1,277 | 1,589 / 1,589 |
| 15 | continuation | 7,817 | incumbent 7,779 | +0.49% | 0.988 | 17.7 | 25 | 295 | [0, 0, 0] | 1,277 | 1,589 / 1,589 |
| 15 | continuation_landed | 7,817 | incumbent 7,779 | +0.49% | 0.988 | 17.7 | 25 | 295 | [0, 0, 0] | 1,277 | 1,589 / 1,589 |
| 17 | salvage | 9,114 | incumbent 9,076 | +0.42% | 0.990 | 17.7 | 27 | 278 | [0, 0, 0] | 1,221 | 1,519 / 1,519 |
| 17 | continuation | 8,816 | incumbent 8,778 | +0.44% | 0.990 | 17.7 | 27 | 278 | [0, 0, 0] | 1,221 | 1,519 / 1,519 |
| 17 | continuation_landed | 8,816 | incumbent 8,778 | +0.44% | 0.990 | 17.7 | 27 | 278 | [0, 0, 0] | 1,221 | 1,519 / 1,519 |
| 19 | salvage | 10,178 | incumbent 10,140 | +0.38% | 0.989 | 20.3 | 23 | 295 | [0, 0, 0] | 1,273 | 1,584 / 1,584 |
| 19 | continuation | 9,867 | incumbent 9,829 | +0.39% | 0.989 | 20.3 | 23 | 295 | [0, 0, 0] | 1,273 | 1,584 / 1,584 |
| 19 | continuation_landed | 9,867 | incumbent 9,829 | +0.39% | 0.989 | 20.3 | 23 | 295 | [0, 0, 0] | 1,273 | 1,584 / 1,584 |
| 23 | salvage | 12,295 | incumbent 12,257 | +0.31% | 0.988 | 27.4 | 16 | 319 | [0, 0, 0] | 1,339 | 1,666 / 1,666 |
| 23 | continuation | 11,969 | incumbent 11,930 | +0.32% | 0.988 | 27.4 | 16 | 319 | [0, 0, 0] | 1,339 | 1,666 / 1,666 |
| 23 | continuation_landed | 11,969 | incumbent 11,930 | +0.32% | 0.988 | 27.4 | 16 | 319 | [0, 0, 0] | 1,339 | 1,666 / 1,666 |
| 35 | salvage | 18,429 | incumbent 18,298 | +0.72% | 0.990 | 34.0 | 36 | 363 | [0, 0, 0] | 1,599 | 1,986 / 1,986 |
| 35 | continuation | 18,042 | incumbent 17,979 | +0.35% | 0.990 | 34.0 | 36 | 363 | [0, 0, 0] | 1,599 | 1,986 / 1,986 |
| 35 | continuation_landed | 18,042 | incumbent 17,979 | +0.35% | 0.990 | 34.0 | 36 | 363 | [0, 0, 0] | 1,599 | 1,986 / 1,986 |
| 47 | salvage | 24,408 | incumbent 24,302 | +0.44% | 0.990 | 45.0 | 65 | 262 | [0, 0, 0] | 1,307 | 1,626 / 1,626 |
| 47 | continuation | 24,089 | incumbent 23,983 | +0.44% | 0.990 | 45.0 | 65 | 262 | [0, 0, 0] | 1,307 | 1,626 / 1,626 |
| 47 | continuation_landed | 24,089 | incumbent 23,983 | +0.44% | 0.990 | 45.0 | 65 | 262 | [0, 0, 0] | 1,307 | 1,626 / 1,626 |
| 52 | salvage | 26,890 | incumbent 26,791 | +0.37% | 0.991 | 45.0 | 23 | 280 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 52 | continuation | 26,593 | incumbent 26,488 | +0.40% | 0.991 | 45.0 | 23 | 280 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 52 | continuation_landed | 26,593 | incumbent 26,488 | +0.40% | 0.991 | 45.0 | 23 | 280 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |

### O_low_opening_stock (valid to W = 52; legacy 12-week: salvage +0.46%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,467 | reorder_point 6,399 | +1.07% | 0.926 | 81.6 | 101 | 95 | [0, None, 0] | 784 | 977 / 977 |
| 11 | continuation | 6,274 | reorder_point 6,285 | -0.17% | 0.926 | 81.6 | 101 | 95 | [0, None, 0] | 784 | 977 / 977 |
| 11 | continuation_landed | 6,274 | reorder_point 6,285 | -0.17% | 0.926 | 81.6 | 101 | 95 | [0, None, 0] | 784 | 977 / 977 |
| 13 | salvage | 7,445 | reorder_point 7,449 | -0.06% | 0.935 | 84.7 | 43 | 78 | [0, 0, 0] | 484 | 604 / 604 |
| 13 | continuation | 7,325 | reorder_point 7,332 | -0.10% | 0.935 | 84.7 | 43 | 78 | [0, 0, 0] | 484 | 604 / 604 |
| 13 | continuation_landed | 7,325 | reorder_point 7,332 | -0.10% | 0.935 | 84.7 | 43 | 78 | [0, 0, 0] | 484 | 604 / 604 |
| 15 | salvage | 8,438 | reorder_point 8,445 | -0.09% | 0.944 | 84.7 | 20 | 95 | [0, 0, 0] | 460 | 574 / 574 |
| 15 | continuation | 8,324 | reorder_point 8,332 | -0.10% | 0.944 | 84.7 | 20 | 95 | [0, 0, 0] | 460 | 574 / 574 |
| 15 | continuation_landed | 8,324 | reorder_point 8,332 | -0.10% | 0.944 | 84.7 | 20 | 95 | [0, 0, 0] | 460 | 574 / 574 |
| 17 | salvage | 9,475 | reorder_point 9,436 | +0.42% | 0.950 | 84.7 | 82 | 63 | [0, 0, None] | 579 | 722 / 722 |
| 17 | continuation | 9,332 | reorder_point 9,332 | +0.00% | 0.950 | 84.7 | 82 | 63 | [0, 0, None] | 579 | 722 / 722 |
| 17 | continuation_landed | 9,332 | reorder_point 9,332 | +0.00% | 0.950 | 84.7 | 82 | 63 | [0, 0, None] | 579 | 722 / 722 |
| 19 | salvage | 10,602 | reorder_point 10,509 | +0.89% | 0.952 | 91.8 | 40 | 144 | [0, 0, 0] | 737 | 919 / 919 |
| 19 | continuation | 10,420 | reorder_point 10,396 | +0.24% | 0.952 | 91.8 | 40 | 144 | [0, 0, 0] | 737 | 919 / 919 |
| 19 | continuation_landed | 10,420 | reorder_point 10,396 | +0.24% | 0.952 | 91.8 | 40 | 144 | [0, 0, 0] | 737 | 919 / 919 |
| 23 | salvage | 12,662 | reorder_point 12,568 | +0.75% | 0.958 | 96.9 | 99 | 60 | [0, 0, None] | 637 | 795 / 795 |
| 23 | continuation | 12,505 | reorder_point 12,449 | +0.45% | 0.958 | 96.9 | 99 | 60 | [0, 0, None] | 637 | 795 / 795 |
| 23 | continuation_landed | 12,505 | reorder_point 12,449 | +0.45% | 0.958 | 96.9 | 99 | 60 | [0, 0, None] | 637 | 795 / 795 |
| 35 | salvage | 18,729 | reorder_point 18,608 | +0.65% | 0.971 | 99.8 | 53 | 140 | [0, None, 0] | 774 | 965 / 965 |
| 35 | continuation | 18,538 | reorder_point 18,492 | +0.25% | 0.971 | 99.8 | 53 | 140 | [0, None, 0] | 774 | 965 / 965 |
| 35 | continuation_landed | 18,538 | reorder_point 18,492 | +0.25% | 0.971 | 99.8 | 53 | 140 | [0, None, 0] | 774 | 965 / 965 |
| 47 | salvage | 24,844 | reorder_point 24,621 | +0.91% | 0.977 | 108.6 | 134 | 121 | [0, 0, None] | 1,017 | 1,266 / 1,266 |
| 47 | continuation | 24,595 | reorder_point 24,502 | +0.38% | 0.977 | 108.6 | 134 | 121 | [0, 0, None] | 1,017 | 1,266 / 1,266 |
| 47 | continuation_landed | 24,595 | reorder_point 24,502 | +0.38% | 0.977 | 108.6 | 134 | 121 | [0, 0, None] | 1,017 | 1,266 / 1,266 |
| 52 | salvage | 27,251 | reorder_point 27,114 | +0.51% | 0.979 | 108.6 | 44 | 124 | [0, 0, None] | 670 | 834 / 834 |
| 52 | continuation | 27,087 | reorder_point 27,006 | +0.30% | 0.979 | 108.6 | 44 | 124 | [0, 0, None] | 670 | 834 / 834 |
| 52 | continuation_landed | 27,087 | reorder_point 27,006 | +0.30% | 0.979 | 108.6 | 44 | 124 | [0, 0, None] | 670 | 834 / 834 |

### P_high_opening_stock (valid to W = 52; legacy 12-week: salvage +0.29%, continuation +0.39%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,869 | reorder_point 5,786 | +1.43% | 1.000 | 0.0 | 137 | 96 | [0, 0, None] | 933 | 1,162 / 1,162 |
| 11 | continuation | 5,640 | reorder_point 5,673 | -0.57% | 1.000 | 0.0 | 137 | 96 | [0, 0, None] | 933 | 1,162 / 1,162 |
| 11 | continuation_landed | 5,640 | reorder_point 5,673 | -0.57% | 1.000 | 0.0 | 137 | 96 | [0, 0, None] | 933 | 1,162 / 1,162 |
| 13 | salvage | 6,783 | reorder_point 6,837 | -0.78% | 1.000 | 0.0 | 52 | 69 | [None, 0, 0] | 482 | 601 / 601 |
| 13 | continuation | 6,664 | reorder_point 6,720 | -0.83% | 1.000 | 0.0 | 52 | 69 | [None, 0, 0] | 482 | 601 / 601 |
| 13 | continuation_landed | 6,664 | reorder_point 6,720 | -0.83% | 1.000 | 0.0 | 52 | 69 | [None, 0, 0] | 482 | 601 / 601 |
| 15 | salvage | 7,776 | reorder_point 7,833 | -0.72% | 1.000 | 0.0 | 19 | 95 | [0, 0, 0] | 456 | 570 / 570 |
| 15 | continuation | 7,663 | reorder_point 7,720 | -0.73% | 1.000 | 0.0 | 19 | 95 | [0, 0, 0] | 456 | 570 / 570 |
| 15 | continuation_landed | 7,663 | reorder_point 7,720 | -0.73% | 1.000 | 0.0 | 19 | 95 | [0, 0, 0] | 456 | 570 / 570 |
| 17 | salvage | 8,805 | reorder_point 8,823 | -0.21% | 1.000 | 0.0 | 19 | 120 | [0, 0, 0] | 560 | 698 / 698 |
| 17 | continuation | 8,667 | reorder_point 8,719 | -0.60% | 1.000 | 0.0 | 19 | 120 | [0, 0, 0] | 560 | 698 / 698 |
| 17 | continuation_landed | 8,667 | reorder_point 8,719 | -0.60% | 1.000 | 0.0 | 19 | 120 | [0, 0, 0] | 560 | 698 / 698 |
| 19 | salvage | 9,898 | reorder_point 9,896 | +0.01% | 0.998 | 3.1 | 76 | 99 | [None, 0, 0] | 699 | 872 / 872 |
| 19 | continuation | 9,725 | reorder_point 9,783 | -0.59% | 0.998 | 3.1 | 76 | 99 | [None, 0, 0] | 699 | 872 / 872 |
| 19 | continuation_landed | 9,725 | reorder_point 9,783 | -0.59% | 0.998 | 3.1 | 76 | 99 | [None, 0, 0] | 699 | 872 / 872 |
| 23 | salvage | 11,962 | reorder_point 11,956 | +0.05% | 0.997 | 6.9 | 125 | 35 | [None, 0, None] | 640 | 799 / 799 |
| 23 | continuation | 11,803 | reorder_point 11,836 | -0.28% | 0.997 | 6.9 | 125 | 35 | [None, 0, None] | 640 | 799 / 799 |
| 23 | continuation_landed | 11,803 | reorder_point 11,836 | -0.28% | 0.997 | 6.9 | 125 | 35 | [None, 0, None] | 640 | 799 / 799 |
| 35 | salvage | 18,063 | reorder_point 17,995 | +0.38% | 0.995 | 18.1 | 60 | 103 | [0, None, 0] | 653 | 814 / 814 |
| 35 | continuation | 17,902 | reorder_point 17,880 | +0.12% | 0.995 | 18.1 | 60 | 103 | [0, None, 0] | 653 | 814 / 814 |
| 35 | continuation_landed | 17,902 | reorder_point 17,880 | +0.12% | 0.995 | 18.1 | 60 | 103 | [0, None, 0] | 653 | 814 / 814 |
| 47 | salvage | 24,072 | reorder_point 24,008 | +0.27% | 0.994 | 26.6 | 42 | 93 | [0, 0, 0] | 539 | 672 / 672 |
| 47 | continuation | 23,939 | reorder_point 23,889 | +0.21% | 0.994 | 26.6 | 42 | 93 | [0, 0, 0] | 539 | 672 / 672 |
| 47 | continuation_landed | 23,939 | reorder_point 23,889 | +0.21% | 0.994 | 26.6 | 42 | 93 | [0, 0, 0] | 539 | 672 / 672 |
| 52 | salvage | 26,660 | reorder_point 26,502 | +0.60% | 0.994 | 28.6 | 62 | 131 | [0, None, 0] | 773 | 962 / 962 |
| 52 | continuation | 26,470 | reorder_point 26,394 | +0.29% | 0.994 | 28.6 | 62 | 131 | [0, None, 0] | 773 | 962 / 962 |
| 52 | continuation_landed | 26,470 | reorder_point 26,394 | +0.29% | 0.994 | 28.6 | 62 | 131 | [0, None, 0] | 773 | 962 / 962 |

### Q_volatile_demand_high_target (valid to W = 52; legacy 12-week: salvage +0.85%, continuation +1.08%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,974 | incumbent 5,971 | +0.05% | 0.988 | 14.0 | 112 | 69 | [0, 0, 0] | 721 | 899 / 899 |
| 11 | continuation | 5,796 | incumbent 5,793 | +0.05% | 0.988 | 14.0 | 112 | 69 | [0, 0, 0] | 721 | 899 / 899 |
| 11 | continuation_landed | 5,796 | incumbent 5,793 | +0.05% | 0.988 | 14.0 | 112 | 69 | [0, 0, 0] | 721 | 899 / 899 |
| 13 | salvage | 7,056 | incumbent 7,052 | +0.05% | 0.990 | 14.0 | 80 | 103 | [0, 0, 0] | 733 | 914 / 914 |
| 13 | continuation | 6,875 | incumbent 6,872 | +0.05% | 0.990 | 14.0 | 80 | 103 | [0, 0, 0] | 733 | 914 / 914 |
| 13 | continuation_landed | 6,875 | incumbent 6,872 | +0.05% | 0.990 | 14.0 | 80 | 103 | [0, 0, 0] | 733 | 914 / 914 |
| 15 | salvage | 7,978 | incumbent 7,975 | +0.04% | 0.991 | 14.0 | 88 | 86 | [0, 0, 0] | 698 | 870 / 870 |
| 15 | continuation | 7,806 | incumbent 7,803 | +0.04% | 0.991 | 14.0 | 88 | 86 | [0, 0, 0] | 698 | 870 / 870 |
| 15 | continuation_landed | 7,806 | incumbent 7,803 | +0.04% | 0.991 | 14.0 | 88 | 86 | [0, 0, 0] | 698 | 870 / 870 |
| 17 | salvage | 8,900 | incumbent 8,883 | +0.19% | 0.992 | 14.0 | 102 | 48 | [0, 0, None] | 599 | 747 / 747 |
| 17 | continuation | 8,753 | incumbent 8,747 | +0.07% | 0.992 | 14.0 | 102 | 48 | [0, 0, None] | 599 | 747 / 747 |
| 17 | continuation_landed | 8,753 | incumbent 8,747 | +0.07% | 0.992 | 14.0 | 102 | 48 | [0, 0, None] | 599 | 747 / 747 |
| 19 | salvage | 10,059 | incumbent 10,053 | +0.07% | 0.986 | 25.9 | 76 | 102 | [0, 0, 0] | 712 | 888 / 888 |
| 19 | continuation | 9,884 | incumbent 9,877 | +0.06% | 0.986 | 25.9 | 76 | 102 | [0, 0, 0] | 712 | 888 / 888 |
| 19 | continuation_landed | 9,884 | incumbent 9,877 | +0.06% | 0.986 | 25.9 | 76 | 102 | [0, 0, 0] | 712 | 888 / 888 |
| 23 | salvage | 12,092 | incumbent 12,086 | +0.05% | 0.989 | 25.9 | 84 | 99 | [0, 0, 0] | 732 | 913 / 913 |
| 23 | continuation | 11,912 | incumbent 11,906 | +0.05% | 0.989 | 25.9 | 84 | 99 | [0, 0, 0] | 732 | 913 / 913 |
| 23 | continuation_landed | 11,912 | incumbent 11,906 | +0.05% | 0.989 | 25.9 | 84 | 99 | [0, 0, 0] | 732 | 913 / 913 |
| 35 | salvage | 17,692 | incumbent 17,694 | -0.01% | 0.992 | 27.9 | 50 | 102 | [0, 0, 0] | 608 | 758 / 758 |
| 35 | continuation | 17,542 | incumbent 17,536 | +0.03% | 0.992 | 27.9 | 50 | 102 | [0, 0, 0] | 608 | 758 / 758 |
| 35 | continuation_landed | 17,542 | incumbent 17,536 | +0.03% | 0.992 | 27.9 | 50 | 102 | [0, 0, 0] | 608 | 758 / 758 |
| 47 | salvage | 23,323 | incumbent 23,248 | +0.32% | 0.992 | 37.6 | 70 | 119 | [0, 0, 0] | 755 | 940 / 940 |
| 47 | continuation | 23,138 | incumbent 23,087 | +0.22% | 0.992 | 37.6 | 70 | 119 | [0, 0, 0] | 755 | 940 / 940 |
| 47 | continuation_landed | 23,138 | incumbent 23,087 | +0.22% | 0.992 | 37.6 | 70 | 119 | [0, 0, 0] | 755 | 940 / 940 |
| 52 | salvage | 25,733 | incumbent 25,685 | +0.19% | 0.991 | 45.9 | 58 | 97 | [0, 0, 0] | 618 | 771 / 771 |
| 52 | continuation | 25,581 | incumbent 25,532 | +0.19% | 0.991 | 45.9 | 58 | 97 | [0, 0, 0] | 618 | 771 / 771 |
| 52 | continuation_landed | 25,581 | incumbent 25,532 | +0.19% | 0.991 | 45.9 | 58 | 97 | [0, 0, 0] | 618 | 771 / 771 |

### R_asymmetric_prices_mov (valid to W = 52; legacy 12-week: salvage -0.05%, continuation -0.04%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 63,809 | incumbent 63,448 | +0.57% | 0.989 | 24.7 | 29 | 197 | [0, 0, 0] | 4,859 | 6,064 / 6,064 |
| 11 | continuation | 62,604 | incumbent 62,284 | +0.51% | 0.989 | 24.7 | 29 | 197 | [0, 0, 0] | 4,859 | 6,064 / 6,064 |
| 11 | continuation_landed | 62,604 | incumbent 62,284 | +0.51% | 0.989 | 24.7 | 29 | 197 | [0, 0, 0] | 4,859 | 6,064 / 6,064 |
| 13 | salvage | 75,060 | incumbent 74,755 | +0.41% | 0.990 | 26.2 | 25 | 211 | [0, 0, 0] | 5,180 | 6,465 / 6,465 |
| 13 | continuation | 73,775 | incumbent 73,470 | +0.42% | 0.990 | 26.2 | 25 | 211 | [0, 0, 0] | 5,180 | 6,465 / 6,465 |
| 13 | continuation_landed | 73,775 | incumbent 73,470 | +0.42% | 0.990 | 26.2 | 25 | 211 | [0, 0, 0] | 5,180 | 6,465 / 6,465 |
| 15 | salvage | 86,691 | incumbent 85,961 | +0.85% | 0.991 | 26.6 | 32 | 263 | [0, 0, 0] | 6,556 | 8,176 / 8,176 |
| 15 | continuation | 85,071 | incumbent 84,714 | +0.42% | 0.991 | 26.6 | 32 | 263 | [0, 0, 0] | 6,556 | 8,176 / 8,176 |
| 15 | continuation_landed | 85,071 | incumbent 84,714 | +0.42% | 0.991 | 26.6 | 32 | 263 | [0, 0, 0] | 6,556 | 8,176 / 8,176 |
| 17 | salvage | 97,910 | incumbent 97,463 | +0.46% | 0.992 | 28.0 | 215 | 155 | [0, 0, 0] | 5,310 | 6,620 / 6,620 |
| 17 | continuation | 96,599 | periodic:2 96,239 | +0.37% | 0.992 | 28.0 | 215 | 155 | [0, 0, 0] | 5,310 | 6,620 / 6,620 |
| 17 | continuation_landed | 96,599 | periodic:2 96,239 | +0.37% | 0.992 | 28.0 | 215 | 155 | [0, 0, 0] | 5,310 | 6,620 / 6,620 |
| 19 | salvage | 108,915 | incumbent 108,553 | +0.33% | 0.993 | 28.0 | 141 | 165 | [0, 0, 0] | 5,094 | 6,355 / 6,355 |
| 19 | continuation | 107,654 | periodic:2 107,366 | +0.27% | 0.993 | 28.0 | 141 | 165 | [0, 0, 0] | 5,094 | 6,355 / 6,355 |
| 19 | continuation_landed | 107,654 | periodic:2 107,366 | +0.27% | 0.993 | 28.0 | 141 | 165 | [0, 0, 0] | 5,094 | 6,355 / 6,355 |
| 23 | salvage | 131,339 | incumbent 131,003 | +0.26% | 0.994 | 29.5 | 130 | 122 | [0, 0, None] | 5,311 | 6,627 / 6,627 |
| 23 | continuation | 130,023 | incumbent 129,760 | +0.20% | 0.994 | 29.5 | 130 | 122 | [0, 0, None] | 5,311 | 6,627 / 6,627 |
| 23 | continuation_landed | 130,023 | incumbent 129,760 | +0.20% | 0.994 | 29.5 | 130 | 122 | [0, 0, None] | 5,311 | 6,627 / 6,627 |
| 35 | salvage | 197,151 | incumbent 196,690 | +0.23% | 0.995 | 34.5 | 123 | 171 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 35 | continuation | 195,738 | incumbent 195,436 | +0.15% | 0.995 | 34.5 | 123 | 171 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 35 | continuation_landed | 195,738 | incumbent 195,436 | +0.15% | 0.995 | 34.5 | 123 | 171 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 47 | salvage | 264,145 | incumbent 263,353 | +0.30% | 0.994 | 53.2 | 36 | 200 | [0, 0, 0] | 5,146 | 6,422 / 6,422 |
| 47 | continuation | 262,869 | incumbent 262,077 | +0.30% | 0.994 | 53.2 | 36 | 200 | [0, 0, 0] | 5,146 | 6,422 / 6,422 |
| 47 | continuation_landed | 262,869 | incumbent 262,077 | +0.30% | 0.994 | 53.2 | 36 | 200 | [0, 0, 0] | 5,146 | 6,422 / 6,422 |
| 52 | salvage | 292,565 | incumbent 290,755 | +0.62% | 0.994 | 58.3 | 229 | 181 | [0, 0, 0] | 8,094 | 10,081 / 10,081 |
| 52 | continuation | 290,577 | incumbent 289,535 | +0.36% | 0.994 | 58.3 | 229 | 181 | [0, 0, 0] | 8,094 | 10,081 / 10,081 |
| 52 | continuation_landed | 290,577 | incumbent 289,535 | +0.36% | 0.994 | 58.3 | 229 | 181 | [0, 0, 0] | 8,094 | 10,081 / 10,081 |

### S_cash_constrained (valid to W = 12; legacy 12-week: salvage +0.26%, continuation +3.59%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,469 | economic_lot 6,234 | +3.77% | 1.000 | 0.0 | 150 | 190 | [0, None, None] | 1,363 | 1,692 / 1,795 |
| 11 | continuation | 6,140 | economic_lot 5,924 | +3.65% | 1.000 | 0.0 | 150 | 190 | [0, None, None] | 1,363 | 1,692 / 1,795 |
| 11 | continuation_landed | 6,037 | economic_lot 5,875 | +2.75% | 1.000 | 0.0 | 150 | 190 | [0, None, None] | 1,363 | 1,692 / 1,795 |

### T_combined_realistic (valid to W = 52; legacy 12-week: salvage -11.47%, continuation -4.21%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 16,885 | economic_lot 17,593 | -4.02% | 1.000 | 0.0 | 1840 | 0 | [None, None, None] | 7,361 | 8,972 / 10,639 |
| 11 | continuation | 15,275 | economic_lot 15,846 | -3.60% | 1.000 | 0.0 | 1840 | 0 | [None, None, None] | 7,361 | 8,972 / 10,639 |
| 11 | continuation_landed | 13,608 | economic_lot 13,782 | -1.26% | 1.000 | 0.0 | 1840 | 0 | [None, None, None] | 7,361 | 8,972 / 10,639 |
| 13 | salvage | 18,550 | economic_lot 19,258 | -3.68% | 1.000 | 0.0 | 1439 | 0 | [None, None, None] | 5,756 | 7,058 / 8,362 |
| 13 | continuation | 17,248 | economic_lot 17,807 | -3.14% | 1.000 | 0.0 | 1439 | 0 | [None, None, None] | 5,756 | 7,058 / 8,362 |
| 13 | continuation_landed | 15,944 | economic_lot 16,143 | -1.23% | 1.000 | 0.0 | 1439 | 0 | [None, None, None] | 5,756 | 7,058 / 8,362 |
| 15 | salvage | 20,174 | economic_lot 20,889 | -3.42% | 1.000 | 0.0 | 1043 | 0 | [None, None, None] | 4,171 | 5,141 / 6,086 |
| 15 | continuation | 19,204 | economic_lot 19,761 | -2.82% | 1.000 | 0.0 | 1043 | 0 | [None, None, None] | 4,171 | 5,141 / 6,086 |
| 15 | continuation_landed | 18,260 | economic_lot 18,492 | -1.26% | 1.000 | 0.0 | 1043 | 0 | [None, None, None] | 4,171 | 5,141 / 6,086 |
| 17 | salvage | 21,812 | economic_lot 22,542 | -3.24% | 1.000 | 0.0 | 643 | 0 | [None, None, None] | 2,571 | 3,185 / 3,768 |
| 17 | continuation | 21,198 | economic_lot 21,760 | -2.58% | 1.000 | 0.0 | 643 | 0 | [None, None, None] | 2,571 | 3,185 / 3,768 |
| 17 | continuation_landed | 20,615 | economic_lot 20,889 | -1.31% | 1.000 | 0.0 | 643 | 0 | [None, None, None] | 2,571 | 3,185 / 3,768 |
| 19 | salvage | 25,121 | economic_lot 25,399 | -1.09% | 1.000 | 0.0 | 245 | 733 | [0, 0, None] | 3,912 | 4,782 / 5,697 |
| 19 | continuation | 24,252 | economic_lot 24,451 | -0.82% | 1.000 | 0.0 | 245 | 733 | [0, 0, None] | 3,912 | 4,782 / 5,697 |
| 19 | continuation_landed | 23,337 | economic_lot 23,412 | -0.32% | 1.000 | 0.0 | 245 | 733 | [0, 0, None] | 3,912 | 4,782 / 5,697 |
| 23 | salvage | 30,876 | economic_lot 31,248 | -1.19% | 1.000 | 0.0 | 1379 | 0 | [None, None, None] | 5,514 | 6,764 / 8,086 |
| 23 | continuation | 29,626 | economic_lot 29,907 | -0.94% | 1.000 | 0.0 | 1379 | 0 | [None, None, None] | 5,514 | 6,764 / 8,086 |
| 23 | continuation_landed | 28,304 | economic_lot 28,428 | -0.44% | 1.000 | 0.0 | 1379 | 0 | [None, None, None] | 5,514 | 6,764 / 8,086 |
| 35 | salvage | 44,382 | economic_lot 44,664 | -0.63% | 1.000 | 0.0 | 906 | 0 | [None, None, None] | 3,623 | 4,471 / 5,328 |
| 35 | continuation | 43,533 | economic_lot 43,725 | -0.44% | 1.000 | 0.0 | 906 | 0 | [None, None, None] | 3,623 | 4,471 / 5,328 |
| 35 | continuation_landed | 42,677 | economic_lot 42,728 | -0.12% | 1.000 | 0.0 | 906 | 0 | [None, None, None] | 3,623 | 4,471 / 5,328 |
| 47 | salvage | 60,698 | economic_lot 59,064 | +2.77% | 1.000 | 0.0 | 1113 | 568 | [None, 0, None] | 6,723 | 8,195 / 9,785 |
| 47 | continuation | 59,227 | economic_lot 58,221 | +1.73% | 1.000 | 0.0 | 1113 | 568 | [None, 0, None] | 6,723 | 8,195 / 9,785 |
| 47 | continuation_landed | 57,636 | economic_lot 57,297 | +0.59% | 1.000 | 0.0 | 1113 | 568 | [None, 0, None] | 6,723 | 8,195 / 9,785 |
| 52 | salvage | 66,000 | economic_lot 66,626 | -0.94% | 1.000 | 0.0 | 1327 | 0 | [None, None, None] | 5,309 | 6,496 / 7,783 |
| 52 | continuation | 64,813 | economic_lot 65,196 | -0.59% | 1.000 | 0.0 | 1327 | 0 | [None, None, None] | 5,309 | 6,496 / 7,783 |
| 52 | continuation_landed | 63,526 | economic_lot 63,612 | -0.13% | 1.000 | 0.0 | 1327 | 0 | [None, None, None] | 5,309 | 6,496 / 7,783 |

## Stage 4: convergence classification (section 5), both rules

| fixture | valid at 52 | rule | delta @11 (rolling) | @23 | @35 | @47 | @52 | max |delta(W)-delta(52)| over 40..52 | stable | class |
|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | salvage | +1.43% | +0.86% | +1.08% | +0.88% | +0.79% | 0.26 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation | +1.40% | +0.90% | +1.03% | +0.88% | +0.80% | 0.22 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation_landed | +1.40% | +0.90% | +1.03% | +0.88% | +0.80% | 0.22 pp | yes | A. STABLE PASS |
| B_fixed_order_cost_replace_sold | yes | salvage | +6.72% | -1.69% | +3.19% | -1.71% | +3.77% | 7.42 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation | +3.16% | -0.51% | +1.12% | -0.04% | +1.70% | 2.56 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation_landed | +2.07% | -0.33% | +0.76% | +0.20% | +1.30% | 1.71 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | salvage | +7.66% | +2.20% | +0.94% | +1.89% | -0.07% | 1.43 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | continuation | +1.69% | +0.85% | +0.58% | +0.70% | +0.45% | 0.24 pp | yes | A. STABLE PASS |
| C_moq_four_weeks | yes | continuation_landed | +1.69% | +0.85% | +0.58% | +0.70% | +0.45% | 0.24 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | salvage | -0.52% | +0.57% | +0.82% | +0.64% | +0.57% | 0.26 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation | +0.23% | +0.73% | +0.95% | +0.73% | +0.66% | 0.18 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation_landed | +0.23% | +0.73% | +0.95% | +0.73% | +0.66% | 0.18 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | salvage | +0.04% | +0.06% | +0.03% | -0.04% | -0.34% | 0.36 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation | +0.04% | +0.03% | +0.01% | -0.05% | -0.11% | 0.11 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation_landed | +0.04% | +0.03% | +0.01% | -0.05% | -0.04% | 0.09 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | salvage | +4.48% | +2.51% | +1.64% | +1.32% | +2.11% | 0.18 pp | NO | E. NON-CONVERGENT |
| F_mov_two_skus | yes | continuation | +1.04% | +0.69% | +0.61% | +0.54% | +0.68% | 0.17 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | continuation_landed | +1.04% | +0.69% | +0.61% | +0.54% | +0.68% | 0.17 pp | yes | A. STABLE PASS |
| G_freight_tiers | yes | salvage | +0.47% | -1.99% | -4.15% | -2.70% | -0.44% | 2.09 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation | +1.36% | -1.30% | -3.12% | -2.53% | -1.19% | 1.13 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation_landed | +0.76% | -0.55% | -1.67% | -2.04% | -1.77% | 0.52 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | salvage | -1.61% | -2.82% | -2.09% | -2.07% | -1.90% | 1.00 pp | NO | E. NON-CONVERGENT |
| H_per_pallet_freight | yes | continuation | -2.53% | -2.59% | -2.17% | -2.22% | -2.07% | 0.52 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | continuation_landed | -2.69% | -2.27% | -2.12% | -2.23% | -2.14% | 0.16 pp | yes | A. STABLE PASS |
| I_max_pallets_ftl_cap | yes | salvage | +0.42% | +0.23% | +0.17% | +1.71% | +0.23% | 1.70 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation | +0.47% | +0.24% | +0.16% | +1.33% | +0.20% | 1.30 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation_landed | +0.63% | +0.26% | +0.15% | +0.12% | +0.11% | 0.18 pp | yes | A. STABLE PASS |
| J_net60_cost_of_capital | yes | salvage | +3.59% | -6.04% | -2.63% | -1.40% | +3.37% | 1.80 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation | +1.17% | -2.01% | -0.54% | +0.10% | +1.74% | 1.70 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation_landed | +0.92% | -1.33% | -0.24% | +0.30% | +1.35% | 1.13 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | salvage | +4.41% | -2.31% | -2.61% | -1.08% | +1.81% | 1.08 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation | +0.95% | -1.03% | -0.86% | -0.29% | +0.63% | 1.62 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation_landed | +0.24% | -0.85% | -0.58% | -0.21% | +0.39% | 1.10 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | salvage | +5.11% | -3.71% | -0.16% | +0.33% | -1.16% | 2.86 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation | -0.36% | -1.10% | -0.00% | +0.23% | -0.17% | 0.87 pp | yes | A. STABLE PASS |
| L_high_holding_rate | yes | continuation_landed | -0.38% | -0.68% | -0.08% | +0.16% | -0.04% | 0.49 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | salvage | +2.56% | +0.99% | +0.57% | +0.33% | +0.27% | 0.43 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| M_order_calendar_wednesday | yes | continuation | +1.57% | +0.46% | +0.19% | +0.01% | +0.02% | 0.16 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | continuation_landed | +1.57% | +0.46% | +0.19% | +0.01% | +0.02% | 0.16 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | salvage | +0.28% | +0.31% | +0.72% | +0.44% | +0.37% | 0.13 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation | +0.42% | +0.32% | +0.35% | +0.44% | +0.40% | 0.13 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation_landed | +0.42% | +0.32% | +0.35% | +0.44% | +0.40% | 0.13 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | salvage | +1.07% | +0.75% | +0.65% | +0.91% | +0.51% | 0.40 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation | -0.17% | +0.45% | +0.25% | +0.38% | +0.30% | 0.08 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation_landed | -0.17% | +0.45% | +0.25% | +0.38% | +0.30% | 0.08 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | salvage | +1.43% | +0.05% | +0.38% | +0.27% | +0.60% | 0.44 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | continuation | -0.57% | -0.28% | +0.12% | +0.21% | +0.29% | 0.18 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | continuation_landed | -0.57% | -0.28% | +0.12% | +0.21% | +0.29% | 0.18 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | salvage | +0.05% | +0.05% | -0.01% | +0.32% | +0.19% | 0.14 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation | +0.05% | +0.05% | +0.03% | +0.22% | +0.19% | 0.04 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation_landed | +0.05% | +0.05% | +0.03% | +0.22% | +0.19% | 0.04 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | salvage | +0.57% | +0.26% | +0.23% | +0.30% | +0.62% | 0.32 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation | +0.51% | +0.20% | +0.15% | +0.30% | +0.36% | 0.06 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation_landed | +0.51% | +0.20% | +0.15% | +0.30% | +0.36% | 0.06 pp | yes | A. STABLE PASS |
| S_cash_constrained | no (to 12) | salvage | +3.77% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation | +3.65% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation_landed | +2.75% | - | - | - | - | - | - | INVALID AT 52 |
| T_combined_realistic | yes | salvage | -4.02% | -1.19% | -0.63% | +2.77% | -0.94% | 2.91 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation | -3.60% | -0.94% | -0.44% | +1.73% | -0.59% | 1.74 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation_landed | -1.26% | -0.44% | -0.12% | +0.59% | -0.13% | 0.84 pp | yes | A. STABLE PASS |

## Section 6: boundary-sensitivity index and the selection rule

| rule | Stage 7 tests | BSI (pp per two-review shift, all ten policy pairs, valid fixtures, three seeds) | fixtures stable at 52 |
|---|---|---|---|
| salvage | fail | 1.698 | 9 / 19 |
| continuation | fail | 0.924 | 13 / 19 |
| continuation_landed | pass | 0.461 | 16 / 19 |

**Declared rule: continuation_landed** (declared on the command line).

BSI per rule restricted to baseline-only pairs (no ZAAD in the pair), as a check that the index is not driven by ZAAD:

* salvage: 1.391 pp
* continuation: 0.795 pp
* continuation_landed: 0.426 pp

## Section 8, Option D diagnostic: start offset s with symmetric endpoint handling (window [s, 52])

| fixture | rule | s=0 | s=4 | s=8 |
|---|---|---|---|---|
| A_no_terms_good_incumbent | salvage | +0.79% vs incumbent | +0.79% vs incumbent | +0.73% vs incumbent |
| A_no_terms_good_incumbent | continuation | +0.80% vs incumbent | +0.79% vs incumbent | +0.72% vs incumbent |
| A_no_terms_good_incumbent | continuation_landed | +0.80% vs incumbent | +0.79% vs incumbent | +0.72% vs incumbent |
| B_fixed_order_cost_replace_sold | salvage | +3.77% vs economic_lot | +5.59% vs economic_lot | +2.72% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation | +1.70% vs economic_lot | +2.11% vs economic_lot | +1.20% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation_landed | +1.30% vs economic_lot | +1.62% vs economic_lot | +1.03% vs economic_lot |
| C_moq_four_weeks | salvage | -0.07% vs reorder_point | -2.15% vs reorder_point | -1.87% vs reorder_point |
| C_moq_four_weeks | continuation | +0.45% vs reorder_point | +0.13% vs reorder_point | +0.21% vs reorder_point |
| C_moq_four_weeks | continuation_landed | +0.45% vs reorder_point | +0.13% vs reorder_point | +0.21% vs reorder_point |
| D_case_multiple | salvage | +0.57% vs incumbent | +0.62% vs incumbent | +0.57% vs incumbent |
| D_case_multiple | continuation | +0.66% vs incumbent | +0.71% vs incumbent | +0.68% vs incumbent |
| D_case_multiple | continuation_landed | +0.66% vs incumbent | +0.71% vs incumbent | +0.68% vs incumbent |
| E_pallet_multiple | salvage | -0.34% vs incumbent | -0.37% vs incumbent | -0.80% vs incumbent |
| E_pallet_multiple | continuation | -0.11% vs incumbent | -0.12% vs incumbent | -0.26% vs incumbent |
| E_pallet_multiple | continuation_landed | -0.04% vs incumbent | -0.05% vs incumbent | -0.09% vs incumbent |
| F_mov_two_skus | salvage | +2.11% vs periodic:2 | +0.96% vs periodic:2 | +1.68% vs periodic:2 |
| F_mov_two_skus | continuation | +0.68% vs periodic:2 | +0.52% vs periodic:2 | +0.57% vs periodic:2 |
| F_mov_two_skus | continuation_landed | +0.68% vs periodic:2 | +0.52% vs periodic:2 | +0.57% vs periodic:2 |
| G_freight_tiers | salvage | -0.44% vs economic_lot | -0.33% vs economic_lot | -2.58% vs economic_lot |
| G_freight_tiers | continuation | -1.19% vs economic_lot | -1.29% vs economic_lot | -2.56% vs economic_lot |
| G_freight_tiers | continuation_landed | -1.77% vs economic_lot | -1.92% vs economic_lot | -2.34% vs economic_lot |
| H_per_pallet_freight | salvage | -1.90% vs periodic:2 | -2.75% vs periodic:2 | -3.36% vs periodic:2 |
| H_per_pallet_freight | continuation | -2.07% vs periodic:2 | -2.47% vs periodic:2 | -2.65% vs periodic:2 |
| H_per_pallet_freight | continuation_landed | -2.14% vs periodic:2 | -2.30% vs periodic:2 | -2.23% vs periodic:2 |
| I_max_pallets_ftl_cap | salvage | +0.23% vs economic_lot | -4.35% vs economic_lot | -3.13% vs economic_lot |
| I_max_pallets_ftl_cap | continuation | +0.20% vs economic_lot | -3.32% vs economic_lot | -2.40% vs economic_lot |
| I_max_pallets_ftl_cap | continuation_landed | +0.11% vs economic_lot | -0.25% vs economic_lot | -0.19% vs economic_lot |
| J_net60_cost_of_capital | salvage | +3.37% vs economic_lot | +3.80% vs economic_lot | +1.87% vs economic_lot |
| J_net60_cost_of_capital | continuation | +1.74% vs economic_lot | +1.88% vs economic_lot | +1.20% vs economic_lot |
| J_net60_cost_of_capital | continuation_landed | +1.35% vs economic_lot | +1.43% vs economic_lot | +0.94% vs economic_lot |
| K_deposit_early_cash | salvage | +1.81% vs economic_lot | +2.49% vs economic_lot | +2.69% vs economic_lot |
| K_deposit_early_cash | continuation | +0.63% vs economic_lot | +0.82% vs economic_lot | +0.87% vs economic_lot |
| K_deposit_early_cash | continuation_landed | +0.39% vs economic_lot | +0.54% vs economic_lot | +0.54% vs economic_lot |
| L_high_holding_rate | salvage | -1.16% vs economic_lot | -0.92% vs economic_lot | -0.95% vs economic_lot |
| L_high_holding_rate | continuation | -0.17% vs economic_lot | -0.06% vs economic_lot | -0.07% vs economic_lot |
| L_high_holding_rate | continuation_landed | -0.04% vs economic_lot | +0.07% vs economic_lot | +0.05% vs economic_lot |
| M_order_calendar_wednesday | salvage | +0.27% vs incumbent | +0.27% vs incumbent | -0.05% vs incumbent |
| M_order_calendar_wednesday | continuation | +0.02% vs incumbent | -0.01% vs incumbent | -0.30% vs incumbent |
| M_order_calendar_wednesday | continuation_landed | +0.02% vs incumbent | -0.01% vs incumbent | -0.30% vs incumbent |
| N_long_lead_21_days | salvage | +0.37% vs incumbent | +0.42% vs incumbent | +0.39% vs incumbent |
| N_long_lead_21_days | continuation | +0.40% vs incumbent | +0.45% vs incumbent | +0.41% vs incumbent |
| N_long_lead_21_days | continuation_landed | +0.40% vs incumbent | +0.45% vs incumbent | +0.41% vs incumbent |
| O_low_opening_stock | salvage | +0.51% vs reorder_point | +0.24% vs reorder_point | +0.28% vs reorder_point |
| O_low_opening_stock | continuation | +0.30% vs reorder_point | +0.28% vs reorder_point | +0.32% vs reorder_point |
| O_low_opening_stock | continuation_landed | +0.30% vs reorder_point | +0.28% vs reorder_point | +0.32% vs reorder_point |
| P_high_opening_stock | salvage | +0.60% vs reorder_point | +0.19% vs reorder_point | -0.40% vs reorder_point |
| P_high_opening_stock | continuation | +0.29% vs reorder_point | +0.26% vs reorder_point | +0.25% vs reorder_point |
| P_high_opening_stock | continuation_landed | +0.29% vs reorder_point | +0.26% vs reorder_point | +0.25% vs reorder_point |
| Q_volatile_demand_high_target | salvage | +0.19% vs incumbent | +0.19% vs incumbent | +0.25% vs periodic:2 |
| Q_volatile_demand_high_target | continuation | +0.19% vs incumbent | +0.19% vs incumbent | +0.22% vs incumbent |
| Q_volatile_demand_high_target | continuation_landed | +0.19% vs incumbent | +0.19% vs incumbent | +0.22% vs incumbent |
| R_asymmetric_prices_mov | salvage | +0.62% vs incumbent | +0.69% vs incumbent | +0.68% vs incumbent |
| R_asymmetric_prices_mov | continuation | +0.36% vs incumbent | +0.38% vs incumbent | +0.37% vs incumbent |
| R_asymmetric_prices_mov | continuation_landed | +0.36% vs incumbent | +0.38% vs incumbent | +0.37% vs incumbent |
| T_combined_realistic | salvage | -0.94% vs economic_lot | -1.05% vs economic_lot | -3.46% vs economic_lot |
| T_combined_realistic | continuation | -0.59% vs economic_lot | -0.66% vs economic_lot | -2.19% vs economic_lot |
| T_combined_realistic | continuation_landed | -0.13% vs economic_lot | -0.16% vs economic_lot | -0.65% vs economic_lot |

## Section 8, Option E diagnostic: per-week average cost at 52 and each policy at its own cycle-minimum endpoint in [40, 52] (declared rule)

| fixture | ZAAD per week | best baseline per week | delta (same as @52) | cycle-minimum endpoints (policy: W) | delta at own cycle minima, per-week normalised |
|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 512.3 | incumbent 508.3 | +0.80% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +1.15% |
| B_fixed_order_cost_replace_sold | 538.7 | economic_lot 531.8 | +1.30% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 52, 'gated': 47} | +0.76% |
| C_moq_four_weeks | 510.6 | reorder_point 508.3 | +0.45% | {'incumbent': 40, 'reorder_point': 43, 'periodic:2': 42, 'economic_lot': 43, 'gated': 40} | +0.32% |
| D_case_multiple | 508.3 | incumbent 505.0 | +0.66% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.93% |
| E_pallet_multiple | 536.3 | incumbent 536.6 | -0.04% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | -0.01% |
| F_mov_two_skus | 1,019.6 | periodic:2 1,012.6 | +0.68% | {'incumbent': 40, 'reorder_point': 51, 'periodic:2': 44, 'economic_lot': 51, 'gated': 46} | +0.47% |
| G_freight_tiers | 1,198.0 | economic_lot 1,219.6 | -1.77% | {'incumbent': 43, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 46} | -1.81% |
| H_per_pallet_freight | 569.8 | periodic:2 582.2 | -2.14% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 41} | -2.35% |
| I_max_pallets_ftl_cap | 782.8 | economic_lot 782.0 | +0.11% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 49, 'gated': 43} | +0.33% |
| J_net60_cost_of_capital | 535.1 | economic_lot 528.0 | +1.35% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 49} | +0.71% |
| K_deposit_early_cash | 530.3 | economic_lot 528.2 | +0.39% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 46} | -0.01% |
| L_high_holding_rate | 537.0 | economic_lot 537.2 | -0.04% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 40, 'gated': 49} | +0.16% |
| M_order_calendar_wednesday | 515.0 | incumbent 514.9 | +0.02% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.11% |
| N_long_lead_21_days | 511.4 | incumbent 509.4 | +0.40% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 41} | +0.10% |
| O_low_opening_stock | 520.9 | reorder_point 519.3 | +0.30% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 49} | -0.29% |
| P_high_opening_stock | 509.0 | reorder_point 507.6 | +0.29% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 50} | -0.07% |
| Q_volatile_demand_high_target | 491.9 | incumbent 491.0 | +0.19% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.22% |
| R_asymmetric_prices_mov | 5,588.0 | incumbent 5,568.0 | +0.36% | {'incumbent': 51, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 42} | +0.46% |
| T_combined_realistic | 1,221.7 | economic_lot 1,223.3 | -0.13% | {'incumbent': 40, 'reorder_point': 52, 'periodic:2': 42, 'economic_lot': 46, 'gated': 45} | +0.02% |

## Stage 9: A-T at the declared benchmark (rolling horizon, W* = 52, rule continuation_landed) beside the legacy twelve-week result

| fixture | valid | legacy delta (salvage) | rolling @11 | **declared @52** | verdict | class | service | breaches | unmet | avg inv units | terminal on-hand | in-transit | purchases | freight | ordering | carrying | financing | shortage | inventory value change | terminal credit (rule) | P1 / P0 owned | actions | abstentions | legacy first-review checks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | +0.43% | +1.40% | **+0.80%** vs incumbent | PASS | A. STABLE PASS | 0.989 | 4.3 | 55.1 | 17 | 6 | 102 | 25,733 | 0 | 0 | 13 | 0 | 689 | 315 | 543 | 153 / 3 | 41 | 17 | ok |
| B_fixed_order_cost_replace_sold | yes | -10.70% | +2.07% | **+1.30%** vs economic_lot | PASS | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 985 | 1207 | 0 | 31,677 | 0 | 917 | 736 | 0 | 0 | -4,077 | 6,067 | 153 / 3 | 156 | 0 | ok |
| C_moq_four_weeks | yes | +3.61% | +1.69% | **+0.45%** vs reorder_point | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 340 | 170 | 186 | 27,310 | 0 | 0 | 254 | 0 | 0 | -671 | 1,763 | 153 / 3 | 147 | 0 | ok |
| D_case_multiple | yes | -0.58% | +0.23% | **+0.66%** vs incumbent | PASS | A. STABLE PASS | 0.995 | 2.0 | 24.7 | 32 | 20 | 94 | 25,920 | 0 | 0 | 24 | 0 | 309 | 294 | 569 | 153 / 3 | 78 | 6 | ok |
| E_pallet_multiple | yes | -0.00% | +0.04% | **-0.04%** vs incumbent | PASS | A. STABLE PASS | 1.000 | 0.0 | 1.8 | 109 | 102 | 64 | 26,333 | 1,580 | 0 | 81 | 0 | 22 | 86 | 877 | 153 / 3 | 40 | 7 | ok |
| F_mov_two_skus | yes | +0.24% | +1.04% | **+0.68%** vs periodic:2 | PASS | A. STABLE PASS | 1.000 | 0.0 | 3.5 | 662 | 819 | 260 | 56,317 | 0 | 0 | 495 | 0 | 44 | -2,814 | 5,340 | 153 / 3 | 124 | 0 | ok |
| G_freight_tiers | yes | -10.01% | +0.76% | **-1.77%** vs economic_lot | PASS | A. STABLE PASS | 0.999 | 0.3 | 7.4 | 1166 | 1574 | 0 | 58,785 | 9,533 | 667 | 872 | 0 | 93 | -4,797 | 9,154 | 153 / 3 | 155 | 0 | ok |
| H_per_pallet_freight | yes | -3.73% | -2.69% | **-2.14%** vs periodic:2 | PASS | A. STABLE PASS | 0.997 | 0.7 | 13.0 | 125 | 126 | 27 | 26,162 | 3,320 | 0 | 93 | 0 | 163 | 138 | 861 | 153 / 3 | 127 | 28 | ok |
| I_max_pallets_ftl_cap | yes | +0.53% | +0.63% | **+0.11%** vs economic_lot | PASS | A. STABLE PASS | 0.999 | 0.3 | 6.1 | 334 | 306 | 0 | 27,000 | 13,200 | 1,800 | 250 | 0 | 76 | -473 | 2,371 | 153 / 3 | 156 | 0 | ok |
| J_net60_cost_of_capital | yes | -11.06% | +0.92% | **+1.35%** vs economic_lot | PASS | E. NON-CONVERGENT | 1.000 | 0.0 | 2.1 | 557 | 539 | 460 | 30,540 | 0 | 1,000 | 417 | 58 | 26 | -3,247 | 4,968 | 153 / 3 | 138 | 0 | ok |
| K_deposit_early_cash | yes | -11.20% | +0.24% | **+0.39%** vs economic_lot | PASS | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 548 | 763 | 0 | 29,296 | 0 | 900 | 410 | 69 | 0 | -2,302 | 3,853 | 153 / 3 | 154 | 0 | ok |
| L_high_holding_rate | yes | -10.16% | -0.38% | **-0.04%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 469 | 613 | 0 | 28,574 | 0 | 1,000 | 702 | 0 | 0 | -1,701 | 3,103 | 153 / 3 | 156 | 0 | ok |
| M_order_calendar_wednesday | yes | -0.54% | +1.57% | **+0.02%** vs incumbent | PASS | A. STABLE PASS | 0.988 | 2.3 | 64.1 | 83 | 91 | 189 | 26,560 | 0 | 0 | 62 | 0 | 801 | -371 | 1,395 | 14 / 142 | 135 | 3 | ok |
| N_long_lead_21_days | yes | -0.71% | +0.42% | **+0.40%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.991 | 3.3 | 45.0 | 36 | 23 | 280 | 25,767 | 0 | 0 | 27 | 0 | 562 | 534 | 1,513 | 152 / 4 | 20 | 45 | ['categories'] |
| O_low_opening_stock | yes | +0.46% | -0.17% | **+0.30%** vs reorder_point | PASS | A. STABLE PASS | 0.979 | 4.0 | 108.6 | 79 | 44 | 124 | 26,404 | 0 | 0 | 59 | 0 | 1,358 | -570 | 834 | 119 / 37 | 126 | 24 | ok |
| P_high_opening_stock | yes | +0.29% | -0.57% | **+0.29%** vs reorder_point | PASS | A. STABLE PASS | 0.994 | 2.3 | 28.6 | 95 | 62 | 131 | 24,003 | 0 | 0 | 71 | 0 | 358 | 2,227 | 962 | 152 / 4 | 107 | 29 | ok |
| Q_volatile_demand_high_target | yes | +0.85% | +0.05% | **+0.19%** vs incumbent | PASS | A. STABLE PASS | 0.991 | 3.0 | 45.9 | 73 | 58 | 97 | 24,973 | 0 | 0 | 55 | 0 | 574 | 132 | 771 | 72 / 84 | 19 | 0 | ok |
| R_asymmetric_prices_mov | yes | -0.05% | +0.51% | **+0.36%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.994 | 0.7 | 58.3 | 75 | 229 | 181 | 288,741 | 0 | 0 | 246 | 0 | 3,422 | 156 | 10,081 | 152 / 4 | 26 | 93 | ['categories'] |
| S_cash_constrained | no (to 12) | +0.26% | +2.75% | **+3.72%** vs economic_lot | INVALID AT 52 (diagnostic @12: outside tolerance) | - | 1.000 | 0.0 | 0.0 | 238 | 235 | 12 | 6,666 | 0 | 500 | 41 | 6 | 0 | -238 | 1,306 | 36 / 0 | 15 | 0 | ok |
| T_combined_realistic | yes | -11.47% | -1.26% | **-0.13%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 1132 | 1327 | 0 | 57,640 | 9,533 | 1,333 | 1,016 | 120 | 0 | -3,809 | 7,783 | 153 / 3 | 154 | 0 | ok |

Runtime, ZAAD reviews: n 3010, p50 1.29 s, p90 4.19 s, p95 5.87 s, max 79.3 s; total wall of all cells 6,427 s.

