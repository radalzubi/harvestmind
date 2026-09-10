# P1 extended-window benchmark: convergence, stability, selection and the declared result

Source `docs/zaad_full/evidence/p1/closure/horizon52.jsonl`: 300 cells, rolling twelve-period planning horizon, 52 reviews requested, stitched truth per seed, scored at every endpoint under both terminal rules. Pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`.

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
| 11 | salvage | 5,919 | incumbent 5,824 | +1.63% | 0.980 | 22.3 | 20 | 93 | [0, 0, 0] | 452 | 564 / 564 |
| 11 | continuation | 5,807 | incumbent 5,710 | +1.70% | 0.980 | 22.3 | 20 | 93 | [0, 0, 0] | 452 | 564 / 564 |
| 11 | continuation_landed | 5,807 | incumbent 5,710 | +1.70% | 0.980 | 22.3 | 20 | 93 | [0, 0, 0] | 452 | 564 / 564 |
| 13 | salvage | 6,984 | incumbent 6,874 | +1.60% | 0.981 | 25.4 | 13 | 105 | [0, 0, 0] | 472 | 589 / 589 |
| 13 | continuation | 6,867 | incumbent 6,757 | +1.62% | 0.981 | 25.4 | 13 | 105 | [0, 0, 0] | 472 | 589 / 589 |
| 13 | continuation_landed | 6,867 | incumbent 6,757 | +1.62% | 0.981 | 25.4 | 13 | 105 | [0, 0, 0] | 472 | 589 / 589 |
| 15 | salvage | 7,977 | incumbent 7,870 | +1.36% | 0.983 | 25.7 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 15 | continuation | 7,868 | incumbent 7,757 | +1.43% | 0.983 | 25.7 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 15 | continuation_landed | 7,868 | incumbent 7,757 | +1.43% | 0.983 | 25.7 | 13 | 97 | [0, 0, 0] | 439 | 548 / 548 |
| 17 | salvage | 8,999 | incumbent 8,861 | +1.57% | 0.983 | 29.5 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 17 | continuation | 8,896 | incumbent 8,757 | +1.59% | 0.983 | 29.5 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 17 | continuation_landed | 8,896 | incumbent 8,757 | +1.59% | 0.983 | 29.5 | 9 | 95 | [0, 0, 0] | 417 | 521 / 521 |
| 19 | salvage | 10,075 | incumbent 9,934 | +1.42% | 0.982 | 34.4 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 19 | continuation | 9,962 | incumbent 9,821 | +1.44% | 0.982 | 34.4 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 19 | continuation_landed | 9,962 | incumbent 9,821 | +1.44% | 0.982 | 34.4 | 10 | 104 | [0, 0, 0] | 456 | 570 / 570 |
| 23 | salvage | 12,134 | incumbent 11,993 | +1.18% | 0.985 | 35.2 | 23 | 98 | [0, 0, 0] | 482 | 601 / 601 |
| 23 | continuation | 12,015 | incumbent 11,874 | +1.19% | 0.985 | 35.2 | 23 | 98 | [0, 0, 0] | 482 | 601 / 601 |
| 23 | continuation_landed | 12,015 | incumbent 11,874 | +1.19% | 0.985 | 35.2 | 23 | 98 | [0, 0, 0] | 482 | 601 / 601 |
| 35 | salvage | 18,232 | incumbent 18,033 | +1.10% | 0.987 | 46.4 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 35 | continuation | 18,108 | incumbent 17,917 | +1.06% | 0.987 | 46.4 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 35 | continuation_landed | 18,108 | incumbent 17,917 | +1.06% | 0.987 | 46.4 | 60 | 66 | [0, None, 0] | 501 | 625 / 625 |
| 47 | salvage | 24,274 | incumbent 24,046 | +0.95% | 0.988 | 57.0 | 13 | 106 | [0, 0, 0] | 479 | 598 / 598 |
| 47 | continuation | 24,156 | incumbent 23,927 | +0.96% | 0.988 | 57.0 | 13 | 106 | [0, 0, 0] | 479 | 598 / 598 |
| 47 | continuation_landed | 24,156 | incumbent 23,927 | +0.96% | 0.988 | 57.0 | 13 | 106 | [0, 0, 0] | 479 | 598 / 598 |
| 52 | salvage | 26,768 | incumbent 26,539 | +0.86% | 0.989 | 57.0 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation | 26,660 | incumbent 26,431 | +0.87% | 0.989 | 57.0 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation_landed | 26,660 | incumbent 26,431 | +0.87% | 0.989 | 57.0 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |

### B_fixed_order_cost_replace_sold (valid to W = 52; legacy 12-week: salvage -10.70%, continuation -1.06%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,398 | economic_lot 6,995 | +5.77% | 1.000 | 0.0 | 592 | 286 | [0, None, None] | 3,512 | 4,325 / 4,639 |
| 11 | continuation | 6,585 | economic_lot 6,182 | +6.52% | 1.000 | 0.0 | 592 | 286 | [0, None, None] | 3,512 | 4,325 / 4,639 |
| 11 | continuation_landed | 6,272 | economic_lot 6,065 | +3.41% | 1.000 | 0.0 | 592 | 286 | [0, None, None] | 3,512 | 4,325 / 4,639 |
| 13 | salvage | 8,231 | economic_lot 7,827 | +5.16% | 1.000 | 0.0 | 675 | 0 | [None, None, None] | 2,700 | 3,332 / 3,555 |
| 13 | continuation | 7,599 | economic_lot 7,195 | +5.62% | 1.000 | 0.0 | 675 | 0 | [None, None, None] | 2,700 | 3,332 / 3,555 |
| 13 | continuation_landed | 7,376 | economic_lot 7,105 | +3.81% | 1.000 | 0.0 | 675 | 0 | [None, None, None] | 2,700 | 3,332 / 3,555 |
| 15 | salvage | 9,524 | economic_lot 8,625 | +10.42% | 1.000 | 0.0 | 855 | 0 | [None, None, None] | 3,421 | 4,221 / 4,549 |
| 15 | continuation | 8,723 | economic_lot 8,173 | +6.73% | 1.000 | 0.0 | 855 | 0 | [None, None, None] | 3,421 | 4,221 / 4,549 |
| 15 | continuation_landed | 8,396 | economic_lot 8,110 | +3.53% | 1.000 | 0.0 | 855 | 0 | [None, None, None] | 3,421 | 4,221 / 4,549 |
| 17 | salvage | 10,330 | economic_lot 9,420 | +9.66% | 1.000 | 0.0 | 659 | 0 | [None, None, None] | 2,635 | 3,258 / 3,515 |
| 17 | continuation | 9,707 | economic_lot 9,154 | +6.03% | 1.000 | 0.0 | 659 | 0 | [None, None, None] | 2,635 | 3,258 / 3,515 |
| 17 | continuation_landed | 9,450 | economic_lot 9,118 | +3.65% | 1.000 | 0.0 | 659 | 0 | [None, None, None] | 2,635 | 3,258 / 3,515 |
| 19 | salvage | 11,147 | economic_lot 11,775 | -5.33% | 1.000 | 0.0 | 458 | 0 | [None, None, None] | 1,833 | 2,273 / 2,457 |
| 19 | continuation | 10,707 | economic_lot 10,666 | +0.38% | 1.000 | 0.0 | 458 | 0 | [None, None, None] | 1,833 | 2,273 / 2,457 |
| 19 | continuation_landed | 10,523 | economic_lot 10,494 | +0.27% | 1.000 | 0.0 | 458 | 0 | [None, None, None] | 1,833 | 2,273 / 2,457 |
| 23 | salvage | 13,785 | economic_lot 14,233 | -3.15% | 1.000 | 0.0 | 798 | 0 | [None, None, None] | 3,193 | 3,940 / 4,182 |
| 23 | continuation | 13,038 | economic_lot 12,892 | +1.14% | 1.000 | 0.0 | 798 | 0 | [None, None, None] | 3,193 | 3,940 / 4,182 |
| 23 | continuation_landed | 12,796 | economic_lot 12,691 | +0.83% | 1.000 | 0.0 | 798 | 0 | [None, None, None] | 3,193 | 3,940 / 4,182 |
| 35 | salvage | 20,443 | economic_lot 19,080 | +7.14% | 1.000 | 0.0 | 628 | 349 | [None, None, 0] | 3,906 | 4,809 / 5,109 |
| 35 | continuation | 19,540 | economic_lot 18,764 | +4.14% | 1.000 | 0.0 | 628 | 349 | [None, None, 0] | 3,906 | 4,809 / 5,109 |
| 35 | continuation_landed | 19,240 | economic_lot 18,720 | +2.78% | 1.000 | 0.0 | 628 | 349 | [None, None, 0] | 3,906 | 4,809 / 5,109 |
| 47 | salvage | 26,768 | economic_lot 26,174 | +2.27% | 1.000 | 0.0 | 843 | 0 | [None, None, None] | 3,373 | 4,161 / 4,431 |
| 47 | continuation | 25,980 | economic_lot 25,264 | +2.83% | 1.000 | 0.0 | 843 | 0 | [None, None, None] | 3,373 | 4,161 / 4,431 |
| 47 | continuation_landed | 25,710 | economic_lot 25,133 | +2.30% | 1.000 | 0.0 | 843 | 0 | [None, None, None] | 3,373 | 4,161 / 4,431 |
| 52 | salvage | 29,229 | economic_lot 28,189 | +3.69% | 1.000 | 0.0 | 352 | 351 | [0, None, None] | 2,811 | 3,472 / 3,697 |
| 52 | continuation | 28,568 | economic_lot 27,719 | +3.06% | 1.000 | 0.0 | 352 | 351 | [0, None, None] | 2,811 | 3,472 / 3,697 |
| 52 | continuation_landed | 28,343 | economic_lot 27,654 | +2.49% | 1.000 | 0.0 | 352 | 351 | [0, None, None] | 2,811 | 3,472 / 3,697 |

### C_moq_four_weeks (valid to W = 52; legacy 12-week: salvage +3.61%, continuation +0.77%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,478 | reorder_point 5,898 | +9.84% | 1.000 | 0.0 | 444 | 260 | [0, None, 0] | 2,815 | 3,480 / 3,480 |
| 11 | continuation | 5,813 | reorder_point 5,681 | +2.32% | 1.000 | 0.0 | 444 | 260 | [0, None, 0] | 2,815 | 3,480 / 3,480 |
| 11 | continuation_landed | 5,813 | reorder_point 5,681 | +2.32% | 1.000 | 0.0 | 444 | 260 | [0, None, 0] | 2,815 | 3,480 / 3,480 |
| 13 | salvage | 7,451 | reorder_point 7,147 | +4.26% | 1.000 | 0.0 | 501 | 130 | [None, 0, None] | 2,523 | 3,125 / 3,125 |
| 13 | continuation | 6,850 | reorder_point 6,749 | +1.49% | 1.000 | 0.0 | 501 | 130 | [None, 0, None] | 2,523 | 3,125 / 3,125 |
| 13 | continuation_landed | 6,850 | reorder_point 6,749 | +1.49% | 1.000 | 0.0 | 501 | 130 | [None, 0, None] | 2,523 | 3,125 / 3,125 |
| 15 | salvage | 8,248 | reorder_point 7,937 | +3.92% | 1.000 | 0.0 | 435 | 0 | [None, None, None] | 1,740 | 2,161 / 2,161 |
| 15 | continuation | 7,828 | reorder_point 7,727 | +1.31% | 1.000 | 0.0 | 435 | 0 | [None, None, None] | 1,740 | 2,161 / 2,161 |
| 15 | continuation_landed | 7,828 | reorder_point 7,727 | +1.31% | 1.000 | 0.0 | 435 | 0 | [None, None, None] | 1,740 | 2,161 / 2,161 |
| 17 | salvage | 9,489 | reorder_point 9,167 | +3.52% | 1.000 | 0.0 | 239 | 411 | [0, 0, 0] | 2,600 | 3,217 / 3,217 |
| 17 | continuation | 8,872 | reorder_point 8,771 | +1.15% | 1.000 | 0.0 | 239 | 411 | [0, 0, 0] | 2,600 | 3,217 / 3,217 |
| 17 | continuation_landed | 8,872 | reorder_point 8,771 | +1.15% | 1.000 | 0.0 | 239 | 411 | [0, 0, 0] | 2,600 | 3,217 / 3,217 |
| 19 | salvage | 10,450 | reorder_point 9,976 | +4.75% | 1.000 | 0.0 | 450 | 130 | [0, None, None] | 2,320 | 2,875 / 2,875 |
| 19 | continuation | 9,895 | reorder_point 9,772 | +1.26% | 1.000 | 0.0 | 450 | 130 | [0, None, None] | 2,320 | 2,875 / 2,875 |
| 19 | continuation_landed | 9,895 | reorder_point 9,772 | +1.26% | 1.000 | 0.0 | 450 | 130 | [0, None, None] | 2,320 | 2,875 / 2,875 |
| 23 | salvage | 12,214 | reorder_point 12,019 | +1.62% | 1.000 | 0.0 | 180 | 130 | [0, None, None] | 1,242 | 1,542 / 1,542 |
| 23 | continuation | 11,914 | reorder_point 11,823 | +0.77% | 1.000 | 0.0 | 180 | 130 | [0, None, None] | 1,242 | 1,542 / 1,542 |
| 23 | continuation_landed | 11,914 | reorder_point 11,823 | +0.77% | 1.000 | 0.0 | 180 | 130 | [0, None, None] | 1,242 | 1,542 / 1,542 |
| 35 | salvage | 18,303 | reorder_point 18,048 | +1.41% | 0.999 | 2.1 | 327 | 0 | [None, None, None] | 1,310 | 1,629 / 1,629 |
| 35 | continuation | 17,983 | reorder_point 17,850 | +0.74% | 0.999 | 2.1 | 327 | 0 | [None, None, None] | 1,310 | 1,629 / 1,629 |
| 35 | continuation_landed | 17,983 | reorder_point 17,850 | +0.74% | 0.999 | 2.1 | 327 | 0 | [None, None, None] | 1,310 | 1,629 / 1,629 |
| 47 | salvage | 24,447 | reorder_point 24,077 | +1.54% | 1.000 | 2.1 | 439 | 0 | [None, None, None] | 1,758 | 2,183 / 2,183 |
| 47 | continuation | 24,022 | reorder_point 23,876 | +0.61% | 1.000 | 2.1 | 439 | 0 | [None, None, None] | 1,758 | 2,183 / 2,183 |
| 47 | continuation_landed | 24,022 | reorder_point 23,876 | +0.61% | 1.000 | 2.1 | 439 | 0 | [None, None, None] | 1,758 | 2,183 / 2,183 |
| 52 | salvage | 26,846 | reorder_point 26,911 | -0.24% | 1.000 | 2.1 | 212 | 132 | [0, None, None] | 1,377 | 1,712 / 1,712 |
| 52 | continuation | 26,511 | reorder_point 26,431 | +0.30% | 1.000 | 2.1 | 212 | 132 | [0, None, None] | 1,377 | 1,712 / 1,712 |
| 52 | continuation_landed | 26,511 | reorder_point 26,431 | +0.30% | 1.000 | 2.1 | 212 | 132 | [0, None, None] | 1,377 | 1,712 / 1,712 |

### D_case_multiple (valid to W = 52; legacy 12-week: salvage -0.58%, continuation +0.17%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,752 | incumbent 5,807 | -0.94% | 1.000 | 0.0 | 49 | 62 | [0, 0, 0] | 443 | 553 / 553 |
| 11 | continuation | 5,642 | incumbent 5,651 | -0.16% | 1.000 | 0.0 | 49 | 62 | [0, 0, 0] | 443 | 553 / 553 |
| 11 | continuation_landed | 5,642 | incumbent 5,651 | -0.16% | 1.000 | 0.0 | 49 | 62 | [0, 0, 0] | 443 | 553 / 553 |
| 13 | salvage | 6,814 | incumbent 6,845 | -0.45% | 0.998 | 2.9 | 36 | 78 | [0, 0, 0] | 458 | 572 / 572 |
| 13 | continuation | 6,701 | incumbent 6,689 | +0.18% | 0.998 | 2.9 | 36 | 78 | [0, 0, 0] | 458 | 572 / 572 |
| 13 | continuation_landed | 6,701 | incumbent 6,689 | +0.18% | 0.998 | 2.9 | 36 | 78 | [0, 0, 0] | 458 | 572 / 572 |
| 15 | salvage | 7,842 | incumbent 7,820 | +0.27% | 0.998 | 2.9 | 28 | 110 | [0, 0, 0] | 551 | 687 / 687 |
| 15 | continuation | 7,706 | incumbent 7,687 | +0.24% | 0.998 | 2.9 | 28 | 110 | [0, 0, 0] | 551 | 687 / 687 |
| 15 | continuation_landed | 7,706 | incumbent 7,687 | +0.24% | 0.998 | 2.9 | 28 | 110 | [0, 0, 0] | 551 | 687 / 687 |
| 17 | salvage | 8,834 | incumbent 8,813 | +0.24% | 0.998 | 2.9 | 36 | 94 | [0, 0, 0] | 520 | 648 / 648 |
| 17 | continuation | 8,706 | incumbent 8,687 | +0.21% | 0.998 | 2.9 | 36 | 94 | [0, 0, 0] | 520 | 648 / 648 |
| 17 | continuation_landed | 8,706 | incumbent 8,687 | +0.21% | 0.998 | 2.9 | 36 | 94 | [0, 0, 0] | 520 | 648 / 648 |
| 19 | salvage | 9,867 | incumbent 9,861 | +0.05% | 0.998 | 2.9 | 7 | 125 | [0, 0, 0] | 528 | 659 / 659 |
| 19 | continuation | 9,736 | incumbent 9,718 | +0.18% | 0.998 | 2.9 | 7 | 125 | [0, 0, 0] | 528 | 659 / 659 |
| 19 | continuation_landed | 9,736 | incumbent 9,718 | +0.18% | 0.998 | 2.9 | 7 | 125 | [0, 0, 0] | 528 | 659 / 659 |
| 23 | salvage | 11,927 | incumbent 11,917 | +0.08% | 0.998 | 5.7 | 48 | 78 | [0, 0, 0] | 505 | 630 / 630 |
| 23 | continuation | 11,802 | incumbent 11,767 | +0.30% | 0.998 | 5.7 | 48 | 78 | [0, 0, 0] | 505 | 630 / 630 |
| 23 | continuation_landed | 11,802 | incumbent 11,767 | +0.30% | 0.998 | 5.7 | 48 | 78 | [0, 0, 0] | 505 | 630 / 630 |
| 35 | salvage | 18,044 | incumbent 17,927 | +0.65% | 0.995 | 18.0 | 44 | 94 | [0, 0, 0] | 549 | 685 / 685 |
| 35 | continuation | 17,908 | incumbent 17,778 | +0.73% | 0.995 | 18.0 | 44 | 94 | [0, 0, 0] | 549 | 685 / 685 |
| 35 | continuation_landed | 17,908 | incumbent 17,778 | +0.73% | 0.995 | 18.0 | 44 | 94 | [0, 0, 0] | 549 | 685 / 685 |
| 47 | salvage | 24,052 | incumbent 23,910 | +0.60% | 0.995 | 23.4 | 39 | 94 | [0, 0, 0] | 534 | 666 / 666 |
| 47 | continuation | 23,920 | incumbent 23,755 | +0.70% | 0.995 | 23.4 | 39 | 94 | [0, 0, 0] | 534 | 666 / 666 |
| 47 | continuation_landed | 23,920 | incumbent 23,755 | +0.70% | 0.995 | 23.4 | 39 | 94 | [0, 0, 0] | 534 | 666 / 666 |
| 52 | salvage | 26,553 | incumbent 26,396 | +0.59% | 0.995 | 23.4 | 19 | 110 | [0, 0, 0] | 516 | 643 / 643 |
| 52 | continuation | 26,425 | incumbent 26,261 | +0.63% | 0.995 | 23.4 | 19 | 110 | [0, 0, 0] | 516 | 643 / 643 |
| 52 | continuation_landed | 26,425 | incumbent 26,261 | +0.63% | 0.995 | 23.4 | 19 | 110 | [0, 0, 0] | 516 | 643 / 643 |

### E_pallet_multiple (valid to W = 52; legacy 12-week: salvage -0.00%, continuation +0.00%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,242 | incumbent 6,239 | +0.04% | 1.000 | 0.0 | 155 | 66 | [0, None, None] | 884 | 1,102 / 1,168 |
| 11 | continuation | 6,024 | incumbent 6,021 | +0.04% | 1.000 | 0.0 | 155 | 66 | [0, None, None] | 884 | 1,102 / 1,168 |
| 11 | continuation_landed | 5,958 | incumbent 5,955 | +0.04% | 1.000 | 0.0 | 155 | 66 | [0, None, None] | 884 | 1,102 / 1,168 |
| 13 | salvage | 7,333 | incumbent 7,331 | +0.03% | 1.000 | 0.0 | 149 | 65 | [0, None, None] | 856 | 1,067 / 1,131 |
| 13 | continuation | 7,122 | incumbent 7,120 | +0.04% | 1.000 | 0.0 | 149 | 65 | [0, None, None] | 856 | 1,067 / 1,131 |
| 13 | continuation_landed | 7,058 | incumbent 7,056 | +0.04% | 1.000 | 0.0 | 149 | 65 | [0, None, None] | 856 | 1,067 / 1,131 |
| 15 | salvage | 8,406 | incumbent 8,400 | +0.07% | 0.999 | 1.1 | 85 | 130 | [0, 0, None] | 861 | 1,072 / 1,137 |
| 15 | continuation | 8,195 | incumbent 8,191 | +0.05% | 0.999 | 1.1 | 85 | 130 | [0, 0, None] | 861 | 1,072 / 1,137 |
| 15 | continuation_landed | 8,130 | incumbent 8,127 | +0.04% | 0.999 | 1.1 | 85 | 130 | [0, 0, None] | 861 | 1,072 / 1,137 |
| 17 | salvage | 9,475 | incumbent 9,469 | +0.06% | 0.999 | 1.1 | 149 | 65 | [0, None, None] | 856 | 1,066 / 1,131 |
| 17 | continuation | 9,264 | incumbent 9,261 | +0.04% | 0.999 | 1.1 | 149 | 65 | [0, None, None] | 856 | 1,066 / 1,131 |
| 17 | continuation_landed | 9,200 | incumbent 9,197 | +0.03% | 0.999 | 1.1 | 149 | 65 | [0, None, None] | 856 | 1,066 / 1,131 |
| 19 | salvage | 10,563 | incumbent 10,557 | +0.06% | 0.999 | 1.1 | 78 | 130 | [0, None, 0] | 831 | 1,035 / 1,098 |
| 19 | continuation | 10,358 | incumbent 10,354 | +0.04% | 0.999 | 1.1 | 78 | 130 | [0, None, 0] | 831 | 1,035 / 1,098 |
| 19 | continuation_landed | 10,296 | incumbent 10,293 | +0.03% | 0.999 | 1.1 | 78 | 130 | [0, None, 0] | 831 | 1,035 / 1,098 |
| 23 | salvage | 12,721 | incumbent 12,719 | +0.01% | 1.000 | 1.1 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 23 | continuation | 12,524 | incumbent 12,526 | -0.01% | 1.000 | 1.1 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 23 | continuation_landed | 12,464 | incumbent 12,467 | -0.02% | 1.000 | 1.1 | 134 | 66 | [None, None, 0] | 798 | 995 / 1,055 |
| 35 | salvage | 19,106 | incumbent 19,106 | -0.00% | 1.000 | 1.2 | 134 | 65 | [None, None, 0] | 796 | 992 / 1,051 |
| 35 | continuation | 18,910 | incumbent 18,915 | -0.03% | 1.000 | 1.2 | 134 | 65 | [None, None, 0] | 796 | 992 / 1,051 |
| 35 | continuation_landed | 18,850 | incumbent 18,856 | -0.03% | 1.000 | 1.2 | 134 | 65 | [None, None, 0] | 796 | 992 / 1,051 |
| 47 | salvage | 25,469 | incumbent 25,484 | -0.06% | 1.000 | 1.3 | 138 | 65 | [None, None, 0] | 812 | 1,012 / 1,073 |
| 47 | continuation | 25,269 | incumbent 25,285 | -0.06% | 1.000 | 1.3 | 138 | 65 | [None, None, 0] | 812 | 1,012 / 1,073 |
| 47 | continuation_landed | 25,208 | incumbent 25,224 | -0.06% | 1.000 | 1.3 | 138 | 65 | [None, None, 0] | 812 | 1,012 / 1,073 |
| 52 | salvage | 28,089 | incumbent 28,199 | -0.39% | 1.000 | 1.3 | 104 | 64 | [None, None, 0] | 672 | 837 / 888 |
| 52 | continuation | 27,923 | incumbent 27,971 | -0.17% | 1.000 | 1.3 | 104 | 64 | [None, None, 0] | 672 | 837 / 888 |
| 52 | continuation_landed | 27,873 | incumbent 27,901 | -0.10% | 1.000 | 1.3 | 104 | 64 | [None, None, 0] | 672 | 837 / 888 |

### F_mov_two_skus (valid to W = 52; legacy 12-week: salvage +0.24%, continuation +0.28%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 12,292 | periodic:2 11,766 | +4.46% | 0.998 | 3.5 | 740 | 131 | [0, None, None] | 3,481 | 4,317 / 4,317 |
| 11 | continuation | 11,455 | periodic:2 11,311 | +1.28% | 0.998 | 3.5 | 740 | 131 | [0, None, None] | 3,481 | 4,317 / 4,317 |
| 11 | continuation_landed | 11,455 | periodic:2 11,311 | +1.28% | 0.998 | 3.5 | 740 | 131 | [0, None, None] | 3,481 | 4,317 / 4,317 |
| 13 | salvage | 14,509 | periodic:2 13,812 | +5.05% | 0.999 | 3.5 | 601 | 414 | [0, 0, 0] | 4,059 | 5,031 / 5,031 |
| 13 | continuation | 13,537 | periodic:2 13,360 | +1.32% | 0.999 | 3.5 | 601 | 414 | [0, 0, 0] | 4,059 | 5,031 / 5,031 |
| 13 | continuation_landed | 13,537 | periodic:2 13,360 | +1.32% | 0.999 | 3.5 | 601 | 414 | [0, 0, 0] | 4,059 | 5,031 / 5,031 |
| 15 | salvage | 16,544 | periodic:2 15,828 | +4.52% | 0.999 | 3.5 | 749 | 263 | [None, 0, 0] | 4,047 | 5,018 / 5,018 |
| 15 | continuation | 15,572 | periodic:2 15,380 | +1.25% | 0.999 | 3.5 | 749 | 263 | [None, 0, 0] | 4,047 | 5,018 / 5,018 |
| 15 | continuation_landed | 15,572 | periodic:2 15,380 | +1.25% | 0.999 | 3.5 | 749 | 263 | [None, 0, 0] | 4,047 | 5,018 / 5,018 |
| 17 | salvage | 18,620 | periodic:2 17,878 | +4.15% | 0.999 | 3.5 | 999 | 0 | [None, None, None] | 3,996 | 4,950 / 4,950 |
| 17 | continuation | 17,666 | periodic:2 17,437 | +1.32% | 0.999 | 3.5 | 999 | 0 | [None, None, None] | 3,996 | 4,950 / 4,950 |
| 17 | continuation_landed | 17,666 | periodic:2 17,437 | +1.32% | 0.999 | 3.5 | 999 | 0 | [None, None, None] | 3,996 | 4,950 / 4,950 |
| 19 | salvage | 20,803 | periodic:2 19,910 | +4.48% | 0.999 | 3.5 | 734 | 392 | [0, 0, 0] | 4,503 | 5,574 / 5,574 |
| 19 | continuation | 19,732 | periodic:2 19,470 | +1.35% | 0.999 | 3.5 | 734 | 392 | [0, 0, 0] | 4,503 | 5,574 / 5,574 |
| 19 | continuation_landed | 19,732 | periodic:2 19,470 | +1.35% | 0.999 | 3.5 | 734 | 392 | [0, 0, 0] | 4,503 | 5,574 / 5,574 |
| 23 | salvage | 25,045 | periodic:2 24,003 | +4.34% | 0.999 | 3.5 | 854 | 400 | [0, 0, 0] | 5,014 | 6,205 / 6,205 |
| 23 | continuation | 23,853 | periodic:2 23,555 | +1.27% | 0.999 | 3.5 | 854 | 400 | [0, 0, 0] | 5,014 | 6,205 / 6,205 |
| 23 | continuation_landed | 23,853 | periodic:2 23,555 | +1.27% | 0.999 | 3.5 | 854 | 400 | [0, 0, 0] | 5,014 | 6,205 / 6,205 |
| 35 | salvage | 36,581 | periodic:2 36,021 | +1.55% | 0.999 | 3.5 | 754 | 0 | [None, None, None] | 3,017 | 3,747 / 3,747 |
| 35 | continuation | 35,851 | periodic:2 35,555 | +0.83% | 0.999 | 3.5 | 754 | 0 | [None, None, None] | 3,017 | 3,747 / 3,747 |
| 35 | continuation_landed | 35,851 | periodic:2 35,555 | +0.83% | 0.999 | 3.5 | 754 | 0 | [None, None, None] | 3,017 | 3,747 / 3,747 |
| 47 | salvage | 48,701 | periodic:2 48,127 | +1.19% | 1.000 | 4.1 | 625 | 131 | [0, None, None] | 3,025 | 3,758 / 3,758 |
| 47 | continuation | 47,968 | periodic:2 47,664 | +0.64% | 1.000 | 4.1 | 625 | 131 | [0, None, None] | 3,025 | 3,758 / 3,758 |
| 47 | continuation_landed | 47,968 | periodic:2 47,664 | +0.64% | 1.000 | 4.1 | 625 | 131 | [0, None, None] | 3,025 | 3,758 / 3,758 |
| 52 | salvage | 53,859 | periodic:2 52,929 | +1.76% | 1.000 | 4.1 | 721 | 130 | [None, None, 0] | 3,403 | 4,226 / 4,226 |
| 52 | continuation | 53,036 | periodic:2 52,657 | +0.72% | 1.000 | 4.1 | 721 | 130 | [None, None, 0] | 3,403 | 4,226 / 4,226 |
| 52 | continuation_landed | 53,036 | periodic:2 52,657 | +0.72% | 1.000 | 4.1 | 721 | 130 | [None, None, 0] | 3,403 | 4,226 / 4,226 |

### G_freight_tiers (valid to W = 52; legacy 12-week: salvage -10.01%, continuation -0.41%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 18,158 | economic_lot 16,720 | +8.60% | 0.999 | 2.6 | 248 | 1309 | [0, 0, 0] | 6,228 | 7,665 / 9,721 |
| 11 | continuation | 16,721 | economic_lot 14,837 | +12.70% | 0.999 | 2.6 | 248 | 1309 | [0, 0, 0] | 6,228 | 7,665 / 9,721 |
| 11 | continuation_landed | 14,665 | economic_lot 13,211 | +11.01% | 0.999 | 2.6 | 248 | 1309 | [0, 0, 0] | 6,228 | 7,665 / 9,721 |
| 13 | salvage | 20,971 | economic_lot 18,375 | +14.13% | 0.999 | 2.6 | 1782 | 0 | [None, None, None] | 7,127 | 8,795 / 11,191 |
| 13 | continuation | 19,302 | economic_lot 16,838 | +14.63% | 0.999 | 2.6 | 1782 | 0 | [None, None, None] | 7,127 | 8,795 / 11,191 |
| 13 | continuation_landed | 16,906 | economic_lot 15,532 | +8.84% | 0.999 | 2.6 | 1782 | 0 | [None, None, None] | 7,127 | 8,795 / 11,191 |
| 15 | salvage | 22,598 | economic_lot 19,998 | +13.00% | 0.999 | 2.6 | 1385 | 0 | [None, None, None] | 5,542 | 6,858 / 8,721 |
| 15 | continuation | 21,282 | economic_lot 18,818 | +13.10% | 0.999 | 2.6 | 1385 | 0 | [None, None, None] | 5,542 | 6,858 / 8,721 |
| 15 | continuation_landed | 19,419 | economic_lot 17,829 | +8.91% | 0.999 | 2.6 | 1385 | 0 | [None, None, None] | 5,542 | 6,858 / 8,721 |
| 17 | salvage | 24,983 | economic_lot 21,625 | +15.53% | 0.999 | 2.6 | 1115 | 0 | [None, None, None] | 4,461 | 5,529 / 7,139 |
| 17 | continuation | 23,914 | economic_lot 20,816 | +14.89% | 0.999 | 2.6 | 1115 | 0 | [None, None, None] | 4,461 | 5,529 / 7,139 |
| 17 | continuation_landed | 22,305 | economic_lot 20,147 | +10.71% | 0.999 | 2.6 | 1115 | 0 | [None, None, None] | 4,461 | 5,529 / 7,139 |
| 19 | salvage | 26,965 | economic_lot 23,231 | +16.07% | 0.999 | 2.6 | 718 | 65 | [0, None, None] | 3,132 | 3,891 / 5,060 |
| 19 | continuation | 26,205 | economic_lot 22,800 | +14.94% | 0.999 | 2.6 | 718 | 65 | [0, None, None] | 3,132 | 3,891 / 5,060 |
| 19 | continuation_landed | 25,036 | economic_lot 22,449 | +11.52% | 0.999 | 2.6 | 718 | 65 | [0, None, None] | 3,132 | 3,891 / 5,060 |
| 23 | salvage | 33,672 | economic_lot 30,982 | +8.68% | 0.999 | 2.6 | 735 | 652 | [0, None, 0] | 5,547 | 6,849 / 8,770 |
| 23 | continuation | 32,370 | economic_lot 29,370 | +10.21% | 0.999 | 2.6 | 735 | 652 | [0, None, 0] | 5,547 | 6,849 / 8,770 |
| 23 | continuation_landed | 30,449 | economic_lot 27,867 | +9.27% | 0.999 | 2.6 | 735 | 652 | [0, None, 0] | 5,547 | 6,849 / 8,770 |
| 35 | salvage | 47,701 | economic_lot 45,568 | +4.68% | 1.000 | 2.6 | 988 | 108 | [None, None, 0] | 4,385 | 5,431 / 6,836 |
| 35 | continuation | 46,655 | economic_lot 44,103 | +5.79% | 1.000 | 2.6 | 988 | 108 | [None, None, 0] | 4,385 | 5,431 / 6,836 |
| 35 | continuation_landed | 45,250 | economic_lot 42,583 | +6.26% | 1.000 | 2.6 | 988 | 108 | [None, None, 0] | 4,385 | 5,431 / 6,836 |
| 47 | salvage | 63,603 | economic_lot 60,213 | +5.63% | 1.000 | 2.6 | 1134 | 12 | [None, None, 0] | 4,585 | 5,667 / 7,165 |
| 47 | continuation | 62,520 | economic_lot 58,896 | +6.15% | 1.000 | 2.6 | 1134 | 12 | [None, None, 0] | 4,585 | 5,667 / 7,165 |
| 47 | continuation_landed | 61,022 | economic_lot 57,487 | +6.15% | 1.000 | 2.6 | 1134 | 12 | [None, None, 0] | 4,585 | 5,667 / 7,165 |
| 52 | salvage | 70,715 | economic_lot 65,440 | +8.06% | 1.000 | 2.6 | 869 | 612 | [None, 0, None] | 5,924 | 7,315 / 9,299 |
| 52 | continuation | 69,324 | economic_lot 64,438 | +7.58% | 1.000 | 2.6 | 869 | 612 | [None, 0, None] | 5,924 | 7,315 / 9,299 |
| 52 | continuation_landed | 67,340 | economic_lot 63,421 | +6.18% | 1.000 | 2.6 | 869 | 612 | [None, 0, None] | 5,924 | 7,315 / 9,299 |

### H_per_pallet_freight (valid to W = 52; legacy 12-week: salvage -3.73%, continuation -2.29%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,682 | periodic:2 6,826 | -2.11% | 0.999 | 0.7 | 206 | 32 | [None, None, 0] | 953 | 1,187 / 1,339 |
| 11 | continuation | 6,448 | periodic:2 6,610 | -2.45% | 0.999 | 0.7 | 206 | 32 | [None, None, 0] | 953 | 1,187 / 1,339 |
| 11 | continuation_landed | 6,296 | periodic:2 6,448 | -2.36% | 0.999 | 0.7 | 206 | 32 | [None, None, 0] | 953 | 1,187 / 1,339 |
| 13 | salvage | 7,741 | periodic:2 8,027 | -3.56% | 1.000 | 0.7 | 58 | 107 | [0, 0, 0] | 660 | 823 / 931 |
| 13 | continuation | 7,578 | periodic:2 7,810 | -2.96% | 1.000 | 0.7 | 58 | 107 | [0, 0, 0] | 660 | 823 / 931 |
| 13 | continuation_landed | 7,471 | periodic:2 7,645 | -2.28% | 1.000 | 0.7 | 58 | 107 | [0, 0, 0] | 660 | 823 / 931 |
| 15 | salvage | 8,795 | periodic:2 9,162 | -4.01% | 0.999 | 0.9 | 58 | 64 | [0, 0, None] | 489 | 610 / 689 |
| 15 | continuation | 8,674 | periodic:2 8,951 | -3.09% | 0.999 | 0.9 | 58 | 64 | [0, 0, None] | 489 | 610 / 689 |
| 15 | continuation_landed | 8,594 | periodic:2 8,791 | -2.25% | 0.999 | 0.9 | 58 | 64 | [0, 0, None] | 489 | 610 / 689 |
| 17 | salvage | 10,034 | periodic:2 10,293 | -2.52% | 0.997 | 5.3 | 73 | 88 | [0, 0, None] | 645 | 804 / 910 |
| 17 | continuation | 9,875 | periodic:2 10,093 | -2.16% | 0.997 | 5.3 | 73 | 88 | [0, 0, None] | 645 | 804 / 910 |
| 17 | continuation_landed | 9,769 | periodic:2 9,942 | -1.74% | 0.997 | 5.3 | 73 | 88 | [0, 0, None] | 645 | 804 / 910 |
| 19 | salvage | 11,267 | periodic:2 11,559 | -2.52% | 0.994 | 11.5 | 15 | 146 | [0, 0, 0] | 642 | 801 / 908 |
| 19 | continuation | 11,109 | periodic:2 11,343 | -2.07% | 0.994 | 11.5 | 15 | 146 | [0, 0, 0] | 642 | 801 / 908 |
| 19 | continuation_landed | 11,001 | periodic:2 11,179 | -1.60% | 0.994 | 11.5 | 15 | 146 | [0, 0, 0] | 642 | 801 / 908 |
| 23 | salvage | 13,596 | periodic:2 13,931 | -2.41% | 0.995 | 11.5 | 146 | 31 | [None, 0, None] | 709 | 884 / 1,002 |
| 23 | continuation | 13,422 | periodic:2 13,709 | -2.10% | 0.995 | 11.5 | 146 | 31 | [None, 0, None] | 709 | 884 / 1,002 |
| 23 | continuation_landed | 13,303 | periodic:2 13,540 | -1.75% | 0.995 | 11.5 | 146 | 31 | [None, 0, None] | 709 | 884 / 1,002 |
| 35 | salvage | 20,530 | periodic:2 20,838 | -1.48% | 0.995 | 18.7 | 172 | 32 | [0, None, None] | 817 | 1,018 / 1,155 |
| 35 | continuation | 20,329 | periodic:2 20,622 | -1.42% | 0.995 | 18.7 | 172 | 32 | [0, None, None] | 817 | 1,018 / 1,155 |
| 35 | continuation_landed | 20,192 | periodic:2 20,460 | -1.31% | 0.995 | 18.7 | 172 | 32 | [0, None, None] | 817 | 1,018 / 1,155 |
| 47 | salvage | 27,624 | periodic:2 27,796 | -0.62% | 0.994 | 26.3 | 305 | 45 | [0, 0, None] | 1,399 | 1,739 / 1,971 |
| 47 | continuation | 27,285 | periodic:2 27,578 | -1.06% | 0.994 | 26.3 | 305 | 45 | [0, 0, None] | 1,399 | 1,739 / 1,971 |
| 47 | continuation_landed | 27,052 | periodic:2 27,413 | -1.32% | 0.994 | 26.3 | 305 | 45 | [0, 0, None] | 1,399 | 1,739 / 1,971 |
| 52 | salvage | 30,129 | periodic:2 30,455 | -1.07% | 0.995 | 26.3 | 80 | 63 | [0, 0, None] | 570 | 711 / 806 |
| 52 | continuation | 29,989 | periodic:2 30,353 | -1.20% | 0.995 | 26.3 | 80 | 63 | [0, 0, None] | 570 | 711 / 806 |
| 52 | continuation_landed | 29,893 | periodic:2 30,277 | -1.27% | 0.995 | 26.3 | 80 | 63 | [0, 0, None] | 570 | 711 / 806 |

### I_max_pallets_ftl_cap (valid to W = 52; legacy 12-week: salvage +0.53%, continuation +3.05%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 10,245 | economic_lot 9,814 | +4.39% | 1.000 | 0.0 | 221 | 65 | [None, 0, None] | 1,145 | 1,425 / 2,377 |
| 11 | continuation | 9,965 | economic_lot 9,456 | +5.38% | 1.000 | 0.0 | 221 | 65 | [None, 0, None] | 1,145 | 1,425 / 2,377 |
| 11 | continuation_landed | 9,013 | economic_lot 8,433 | +6.87% | 1.000 | 0.0 | 221 | 65 | [None, 0, None] | 1,145 | 1,425 / 2,377 |
| 13 | salvage | 11,946 | economic_lot 10,632 | +12.35% | 1.000 | 0.0 | 205 | 17 | [None, None, 0] | 887 | 1,104 / 1,939 |
| 13 | continuation | 11,729 | economic_lot 10,469 | +12.03% | 1.000 | 0.0 | 205 | 17 | [None, None, 0] | 887 | 1,104 / 1,939 |
| 13 | continuation_landed | 10,894 | economic_lot 10,011 | +8.82% | 1.000 | 0.0 | 205 | 17 | [None, None, 0] | 887 | 1,104 / 1,939 |
| 15 | salvage | 13,812 | economic_lot 13,171 | +4.86% | 1.000 | 0.0 | 258 | 0 | [None, None, None] | 1,030 | 1,283 / 2,177 |
| 15 | continuation | 13,559 | economic_lot 12,776 | +6.13% | 1.000 | 0.0 | 258 | 0 | [None, None, None] | 1,030 | 1,283 / 2,177 |
| 15 | continuation_landed | 12,665 | economic_lot 11,647 | +8.74% | 1.000 | 0.0 | 258 | 0 | [None, None, None] | 1,030 | 1,283 / 2,177 |
| 17 | salvage | 15,550 | economic_lot 13,964 | +11.35% | 1.000 | 0.0 | 251 | 0 | [None, None, None] | 1,005 | 1,250 / 2,158 |
| 17 | continuation | 15,304 | economic_lot 13,758 | +11.24% | 1.000 | 0.0 | 251 | 0 | [None, None, None] | 1,005 | 1,250 / 2,158 |
| 17 | continuation_landed | 14,396 | economic_lot 13,174 | +9.28% | 1.000 | 0.0 | 251 | 0 | [None, None, None] | 1,005 | 1,250 / 2,158 |
| 19 | salvage | 17,317 | economic_lot 16,522 | +4.81% | 1.000 | 0.0 | 246 | 0 | [None, None, None] | 986 | 1,227 / 2,144 |
| 19 | continuation | 17,075 | economic_lot 16,090 | +6.12% | 1.000 | 0.0 | 246 | 0 | [None, None, None] | 986 | 1,227 / 2,144 |
| 19 | continuation_landed | 16,158 | economic_lot 14,850 | +8.81% | 1.000 | 0.0 | 246 | 0 | [None, None, None] | 986 | 1,227 / 2,144 |
| 23 | salvage | 21,358 | economic_lot 19,879 | +7.44% | 1.000 | 0.0 | 340 | 0 | [None, None, None] | 1,361 | 1,692 / 2,879 |
| 23 | continuation | 21,027 | economic_lot 19,410 | +8.33% | 1.000 | 0.0 | 340 | 0 | [None, None, None] | 1,361 | 1,692 / 2,879 |
| 23 | continuation_landed | 19,840 | economic_lot 18,060 | +9.85% | 1.000 | 0.0 | 340 | 0 | [None, None, None] | 1,361 | 1,692 / 2,879 |
| 35 | salvage | 31,699 | economic_lot 28,093 | +12.84% | 1.000 | 0.0 | 244 | 286 | [0, None, 0] | 2,121 | 2,631 / 4,413 |
| 35 | continuation | 31,189 | economic_lot 27,903 | +11.78% | 1.000 | 0.0 | 244 | 286 | [0, None, 0] | 2,121 | 2,631 / 4,413 |
| 35 | continuation_landed | 29,407 | economic_lot 27,367 | +7.46% | 1.000 | 0.0 | 244 | 286 | [0, None, 0] | 2,121 | 2,631 / 4,413 |
| 47 | salvage | 41,735 | economic_lot 38,052 | +9.68% | 1.000 | 2.1 | 272 | 267 | [0, 0, None] | 2,156 | 2,674 / 4,478 |
| 47 | continuation | 41,217 | economic_lot 37,721 | +9.27% | 1.000 | 2.1 | 272 | 267 | [0, 0, None] | 2,156 | 2,674 / 4,478 |
| 47 | continuation_landed | 39,413 | economic_lot 36,778 | +7.16% | 1.000 | 2.1 | 272 | 267 | [0, 0, None] | 2,156 | 2,674 / 4,478 |
| 52 | salvage | 45,225 | economic_lot 41,758 | +8.30% | 1.000 | 2.1 | 95 | 286 | [0, 0, None] | 1,527 | 1,895 / 3,186 |
| 52 | continuation | 44,857 | economic_lot 41,472 | +8.16% | 1.000 | 2.1 | 95 | 286 | [0, 0, None] | 1,527 | 1,895 / 3,186 |
| 52 | continuation_landed | 43,566 | economic_lot 40,662 | +7.14% | 1.000 | 2.1 | 95 | 286 | [0, 0, None] | 1,527 | 1,895 / 3,186 |

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
| 35 | salvage | 19,738 | economic_lot 19,713 | +0.13% | 1.000 | 0.0 | 975 | 0 | [None, None, None] | 3,899 | 4,747 / 4,879 |
| 35 | continuation | 18,890 | economic_lot 18,888 | +0.01% | 1.000 | 0.0 | 975 | 0 | [None, None, None] | 3,899 | 4,747 / 4,879 |
| 35 | continuation_landed | 18,757 | economic_lot 18,758 | -0.01% | 1.000 | 0.0 | 975 | 0 | [None, None, None] | 3,899 | 4,747 / 4,879 |
| 47 | salvage | 25,811 | economic_lot 25,850 | -0.15% | 1.000 | 0.0 | 865 | 0 | [None, None, None] | 3,461 | 4,224 / 4,341 |
| 47 | continuation | 25,048 | economic_lot 25,085 | -0.15% | 1.000 | 0.0 | 865 | 0 | [None, None, None] | 3,461 | 4,224 / 4,341 |
| 47 | continuation_landed | 24,930 | economic_lot 24,967 | -0.14% | 1.000 | 0.0 | 865 | 0 | [None, None, None] | 3,461 | 4,224 / 4,341 |
| 52 | salvage | 28,220 | economic_lot 27,857 | +1.30% | 1.000 | 0.0 | 374 | 328 | [0, None, None] | 2,805 | 3,430 / 3,528 |
| 52 | continuation | 27,594 | economic_lot 27,505 | +0.33% | 1.000 | 0.0 | 374 | 328 | [0, None, None] | 2,805 | 3,430 / 3,528 |
| 52 | continuation_landed | 27,496 | economic_lot 27,454 | +0.15% | 1.000 | 0.0 | 374 | 328 | [0, None, None] | 2,805 | 3,430 / 3,528 |

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
| 35 | salvage | 19,751 | economic_lot 19,726 | +0.13% | 1.000 | 0.0 | 975 | 0 | [None, None, None] | 3,899 | 4,747 / 4,879 |
| 35 | continuation | 18,902 | economic_lot 18,900 | +0.01% | 1.000 | 0.0 | 975 | 0 | [None, None, None] | 3,899 | 4,747 / 4,879 |
| 35 | continuation_landed | 18,770 | economic_lot 18,771 | -0.01% | 1.000 | 0.0 | 975 | 0 | [None, None, None] | 3,899 | 4,747 / 4,879 |
| 47 | salvage | 25,823 | economic_lot 25,863 | -0.15% | 1.000 | 0.0 | 865 | 0 | [None, None, None] | 3,461 | 4,224 / 4,341 |
| 47 | continuation | 25,060 | economic_lot 25,097 | -0.15% | 1.000 | 0.0 | 865 | 0 | [None, None, None] | 3,461 | 4,224 / 4,341 |
| 47 | continuation_landed | 24,943 | economic_lot 24,979 | -0.15% | 1.000 | 0.0 | 865 | 0 | [None, None, None] | 3,461 | 4,224 / 4,341 |
| 52 | salvage | 28,232 | economic_lot 27,870 | +1.30% | 1.000 | 0.0 | 374 | 328 | [0, None, None] | 2,805 | 3,430 / 3,528 |
| 52 | continuation | 27,607 | economic_lot 27,518 | +0.32% | 1.000 | 0.0 | 374 | 328 | [0, None, None] | 2,805 | 3,430 / 3,528 |
| 52 | continuation_landed | 27,508 | economic_lot 27,467 | +0.15% | 1.000 | 0.0 | 374 | 328 | [0, None, None] | 2,805 | 3,430 / 3,528 |

### L_high_holding_rate (valid to W = 52; legacy 12-week: salvage -10.16%, continuation -4.74%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 7,194 | periodic:2 6,856 | +4.93% | 1.000 | 0.0 | 592 | 286 | [0, None, None] | 3,512 | 4,260 / 4,448 |
| 11 | continuation | 6,446 | economic_lot 6,332 | +1.80% | 1.000 | 0.0 | 592 | 286 | [0, None, None] | 3,512 | 4,260 / 4,448 |
| 11 | continuation_landed | 6,258 | economic_lot 6,177 | +1.30% | 1.000 | 0.0 | 592 | 286 | [0, None, None] | 3,512 | 4,260 / 4,448 |
| 13 | salvage | 8,429 | periodic:2 8,048 | +4.72% | 1.000 | 0.0 | 972 | 0 | [None, None, None] | 3,889 | 4,727 / 4,953 |
| 13 | continuation | 7,590 | economic_lot 7,342 | +3.38% | 1.000 | 0.0 | 972 | 0 | [None, None, None] | 3,889 | 4,727 / 4,953 |
| 13 | continuation_landed | 7,364 | economic_lot 7,217 | +2.04% | 1.000 | 0.0 | 972 | 0 | [None, None, None] | 3,889 | 4,727 / 4,953 |
| 15 | salvage | 9,259 | economic_lot 8,910 | +3.91% | 1.000 | 0.0 | 776 | 0 | [None, None, None] | 3,106 | 3,795 / 3,977 |
| 15 | continuation | 8,570 | economic_lot 8,320 | +3.01% | 1.000 | 0.0 | 776 | 0 | [None, None, None] | 3,106 | 3,795 / 3,977 |
| 15 | continuation_landed | 8,388 | economic_lot 8,224 | +1.99% | 1.000 | 0.0 | 776 | 0 | [None, None, None] | 3,106 | 3,795 / 3,977 |
| 17 | salvage | 10,164 | economic_lot 9,725 | +4.51% | 1.000 | 0.0 | 580 | 31 | [None, None, 0] | 2,444 | 2,998 / 3,158 |
| 17 | continuation | 9,611 | economic_lot 9,301 | +3.34% | 1.000 | 0.0 | 580 | 31 | [None, None, 0] | 2,444 | 2,998 / 3,158 |
| 17 | continuation_landed | 9,450 | economic_lot 9,234 | +2.34% | 1.000 | 0.0 | 580 | 31 | [None, None, 0] | 2,444 | 2,998 / 3,158 |
| 19 | salvage | 10,992 | economic_lot 10,545 | +4.25% | 1.000 | 0.0 | 411 | 0 | [None, None, None] | 1,642 | 2,026 / 2,138 |
| 19 | continuation | 10,609 | economic_lot 10,299 | +3.01% | 1.000 | 0.0 | 411 | 0 | [None, None, None] | 1,642 | 2,026 / 2,138 |
| 19 | continuation_landed | 10,497 | economic_lot 10,262 | +2.29% | 1.000 | 0.0 | 411 | 0 | [None, None, None] | 1,642 | 2,026 / 2,138 |
| 23 | salvage | 13,987 | economic_lot 13,462 | +3.90% | 1.000 | 0.0 | 751 | 330 | [None, None, 0] | 4,321 | 5,238 / 5,473 |
| 23 | continuation | 13,070 | economic_lot 12,704 | +2.88% | 1.000 | 0.0 | 751 | 330 | [None, None, 0] | 4,321 | 5,238 / 5,473 |
| 23 | continuation_landed | 12,835 | economic_lot 12,578 | +2.04% | 1.000 | 0.0 | 751 | 330 | [None, None, 0] | 4,321 | 5,238 / 5,473 |
| 35 | salvage | 20,195 | economic_lot 19,620 | +2.93% | 1.000 | 0.0 | 941 | 0 | [None, None, None] | 3,766 | 4,576 / 4,762 |
| 35 | continuation | 19,385 | economic_lot 19,022 | +1.90% | 1.000 | 0.0 | 941 | 0 | [None, None, None] | 3,766 | 4,576 / 4,762 |
| 35 | continuation_landed | 19,199 | economic_lot 18,925 | +1.45% | 1.000 | 0.0 | 941 | 0 | [None, None, None] | 3,766 | 4,576 / 4,762 |
| 47 | salvage | 26,436 | economic_lot 25,709 | +2.83% | 1.000 | 0.0 | 842 | 0 | [None, None, None] | 3,368 | 4,104 / 4,259 |
| 47 | continuation | 25,700 | economic_lot 25,274 | +1.69% | 1.000 | 0.0 | 842 | 0 | [None, None, None] | 3,368 | 4,104 / 4,259 |
| 47 | continuation_landed | 25,545 | economic_lot 25,205 | +1.35% | 1.000 | 0.0 | 842 | 0 | [None, None, None] | 3,368 | 4,104 / 4,259 |
| 52 | salvage | 28,876 | economic_lot 28,908 | -0.11% | 1.000 | 0.0 | 351 | 326 | [0, None, None] | 2,707 | 3,303 / 3,424 |
| 52 | continuation | 28,280 | economic_lot 28,077 | +0.72% | 1.000 | 0.0 | 351 | 326 | [0, None, None] | 2,707 | 3,303 / 3,424 |
| 52 | continuation_landed | 28,159 | economic_lot 27,933 | +0.81% | 1.000 | 0.0 | 351 | 326 | [0, None, None] | 2,707 | 3,303 / 3,424 |

### M_order_calendar_wednesday (valid to W = 52; legacy 12-week: salvage -0.54%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,384 | incumbent 6,256 | +2.04% | 0.948 | 58.0 | 28 | 266 | [0, 0, 0] | 1,176 | 1,463 / 1,463 |
| 11 | continuation | 6,096 | incumbent 6,039 | +0.94% | 0.948 | 58.0 | 28 | 266 | [0, 0, 0] | 1,176 | 1,463 / 1,463 |
| 11 | continuation_landed | 6,096 | incumbent 6,039 | +0.94% | 0.948 | 58.0 | 28 | 266 | [0, 0, 0] | 1,176 | 1,463 / 1,463 |
| 13 | salvage | 7,461 | incumbent 7,296 | +2.26% | 0.950 | 65.9 | 99 | 178 | [0, 0, 0] | 1,107 | 1,378 / 1,378 |
| 13 | continuation | 7,190 | incumbent 7,076 | +1.60% | 0.950 | 65.9 | 99 | 178 | [0, 0, 0] | 1,107 | 1,378 / 1,378 |
| 13 | continuation_landed | 7,190 | incumbent 7,076 | +1.60% | 0.950 | 65.9 | 99 | 178 | [0, 0, 0] | 1,107 | 1,378 / 1,378 |
| 15 | salvage | 8,468 | incumbent 8,289 | +2.16% | 0.956 | 65.9 | 81 | 201 | [0, 0, 0] | 1,129 | 1,406 / 1,406 |
| 15 | continuation | 8,192 | incumbent 8,076 | +1.44% | 0.956 | 65.9 | 81 | 201 | [0, 0, 0] | 1,129 | 1,406 / 1,406 |
| 15 | continuation_landed | 8,192 | incumbent 8,076 | +1.44% | 0.956 | 65.9 | 81 | 201 | [0, 0, 0] | 1,129 | 1,406 / 1,406 |
| 17 | salvage | 9,472 | incumbent 9,277 | +2.10% | 0.961 | 65.9 | 86 | 198 | [0, 0, 0] | 1,133 | 1,411 / 1,411 |
| 17 | continuation | 9,194 | incumbent 9,075 | +1.31% | 0.961 | 65.9 | 86 | 198 | [0, 0, 0] | 1,133 | 1,411 / 1,411 |
| 17 | continuation_landed | 9,194 | incumbent 9,075 | +1.31% | 0.961 | 65.9 | 86 | 198 | [0, 0, 0] | 1,133 | 1,411 / 1,411 |
| 19 | salvage | 10,493 | incumbent 10,349 | +1.39% | 0.965 | 65.9 | 83 | 192 | [0, 0, 0] | 1,100 | 1,369 / 1,369 |
| 19 | continuation | 10,224 | incumbent 10,136 | +0.87% | 0.965 | 65.9 | 83 | 192 | [0, 0, 0] | 1,100 | 1,369 / 1,369 |
| 19 | continuation_landed | 10,224 | incumbent 10,136 | +0.87% | 0.965 | 65.9 | 83 | 192 | [0, 0, 0] | 1,100 | 1,369 / 1,369 |
| 23 | salvage | 12,565 | incumbent 12,435 | +1.05% | 0.971 | 65.9 | 117 | 178 | [0, 0, 0] | 1,181 | 1,470 / 1,470 |
| 23 | continuation | 12,276 | incumbent 12,212 | +0.53% | 0.971 | 65.9 | 117 | 178 | [0, 0, 0] | 1,181 | 1,470 / 1,470 |
| 23 | continuation_landed | 12,276 | incumbent 12,212 | +0.53% | 0.971 | 65.9 | 117 | 178 | [0, 0, 0] | 1,181 | 1,470 / 1,470 |
| 35 | salvage | 18,582 | incumbent 18,470 | +0.61% | 0.981 | 65.9 | 95 | 198 | [0, 0, 0] | 1,172 | 1,459 / 1,459 |
| 35 | continuation | 18,295 | incumbent 18,253 | +0.23% | 0.981 | 65.9 | 95 | 198 | [0, 0, 0] | 1,172 | 1,459 / 1,459 |
| 35 | continuation_landed | 18,295 | incumbent 18,253 | +0.23% | 0.981 | 65.9 | 95 | 198 | [0, 0, 0] | 1,172 | 1,459 / 1,459 |
| 47 | salvage | 24,574 | incumbent 24,487 | +0.36% | 0.986 | 65.9 | 134 | 170 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 47 | continuation | 24,277 | incumbent 24,266 | +0.04% | 0.986 | 65.9 | 134 | 170 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 47 | continuation_landed | 24,277 | incumbent 24,266 | +0.04% | 0.986 | 65.9 | 134 | 170 | [0, 0, 0] | 1,216 | 1,513 / 1,513 |
| 52 | salvage | 27,060 | incumbent 26,979 | +0.30% | 0.987 | 65.9 | 91 | 189 | [0, 0, 0] | 1,120 | 1,394 / 1,394 |
| 52 | continuation | 26,786 | incumbent 26,773 | +0.05% | 0.987 | 65.9 | 91 | 189 | [0, 0, 0] | 1,120 | 1,394 / 1,394 |
| 52 | continuation_landed | 26,786 | incumbent 26,773 | +0.05% | 0.987 | 65.9 | 91 | 189 | [0, 0, 0] | 1,120 | 1,394 / 1,394 |

### N_long_lead_21_days (valid to W = 52; legacy 12-week: salvage -0.71%, continuation +0.42%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,104 | incumbent 6,039 | +1.07% | 0.989 | 12.0 | 163 | 198 | [0, 1, 0] | 1,446 | 1,798 / 1,798 |
| 11 | continuation | 5,752 | incumbent 5,723 | +0.50% | 0.989 | 12.0 | 163 | 198 | [0, 1, 0] | 1,446 | 1,798 / 1,798 |
| 11 | continuation_landed | 5,752 | incumbent 5,723 | +0.50% | 0.989 | 12.0 | 163 | 198 | [0, 1, 0] | 1,446 | 1,798 / 1,798 |
| 13 | salvage | 7,120 | incumbent 7,099 | +0.29% | 0.991 | 12.0 | 59 | 284 | [0, 0, 1] | 1,371 | 1,705 / 1,705 |
| 13 | continuation | 6,786 | incumbent 6,780 | +0.09% | 0.991 | 12.0 | 59 | 284 | [0, 0, 1] | 1,371 | 1,705 / 1,705 |
| 13 | continuation_landed | 6,786 | incumbent 6,780 | +0.09% | 0.991 | 12.0 | 59 | 284 | [0, 0, 1] | 1,371 | 1,705 / 1,705 |
| 15 | salvage | 8,145 | incumbent 8,091 | +0.67% | 0.992 | 12.0 | 17 | 353 | [0, 0, 0] | 1,481 | 1,841 / 1,841 |
| 15 | continuation | 7,785 | incumbent 7,779 | +0.08% | 0.992 | 12.0 | 17 | 353 | [0, 0, 0] | 1,481 | 1,841 / 1,841 |
| 15 | continuation_landed | 7,785 | incumbent 7,779 | +0.08% | 0.992 | 12.0 | 17 | 353 | [0, 0, 0] | 1,481 | 1,841 / 1,841 |
| 17 | salvage | 9,200 | incumbent 9,076 | +1.36% | 0.990 | 17.4 | 44 | 336 | [0, 0, 0] | 1,521 | 1,890 / 1,890 |
| 17 | continuation | 8,830 | incumbent 8,778 | +0.60% | 0.990 | 17.4 | 44 | 336 | [0, 0, 0] | 1,521 | 1,890 / 1,890 |
| 17 | continuation_landed | 8,830 | incumbent 8,778 | +0.60% | 0.990 | 17.4 | 44 | 336 | [0, 0, 0] | 1,521 | 1,890 / 1,890 |
| 19 | salvage | 10,223 | incumbent 10,140 | +0.82% | 0.986 | 26.0 | 100 | 216 | [0, 0, 2] | 1,264 | 1,573 / 1,573 |
| 19 | continuation | 9,914 | incumbent 9,829 | +0.87% | 0.986 | 26.0 | 100 | 216 | [0, 0, 2] | 1,264 | 1,573 / 1,573 |
| 19 | continuation_landed | 9,914 | incumbent 9,829 | +0.87% | 0.986 | 26.0 | 100 | 216 | [0, 0, 2] | 1,264 | 1,573 / 1,573 |
| 23 | salvage | 12,383 | incumbent 12,257 | +1.03% | 0.983 | 39.9 | 26 | 300 | [0, 0, 0] | 1,304 | 1,623 / 1,623 |
| 23 | continuation | 12,065 | incumbent 11,930 | +1.13% | 0.983 | 39.9 | 26 | 300 | [0, 0, 0] | 1,304 | 1,623 / 1,623 |
| 23 | continuation_landed | 12,065 | incumbent 11,930 | +1.13% | 0.983 | 39.9 | 26 | 300 | [0, 0, 0] | 1,304 | 1,623 / 1,623 |
| 35 | salvage | 18,488 | incumbent 18,298 | +1.04% | 0.987 | 46.5 | 45 | 315 | [0, 0, 0] | 1,437 | 1,787 / 1,787 |
| 35 | continuation | 18,138 | incumbent 17,979 | +0.89% | 0.987 | 46.5 | 45 | 315 | [0, 0, 0] | 1,437 | 1,787 / 1,787 |
| 35 | continuation_landed | 18,138 | incumbent 17,979 | +0.89% | 0.987 | 46.5 | 45 | 315 | [0, 0, 0] | 1,437 | 1,787 / 1,787 |
| 47 | salvage | 24,564 | incumbent 24,302 | +1.08% | 0.986 | 66.2 | 79 | 236 | [0, 0, 0] | 1,258 | 1,566 / 1,566 |
| 47 | continuation | 24,256 | incumbent 23,983 | +1.14% | 0.986 | 66.2 | 79 | 236 | [0, 0, 0] | 1,258 | 1,566 / 1,566 |
| 47 | continuation_landed | 24,256 | incumbent 23,983 | +1.14% | 0.986 | 66.2 | 79 | 236 | [0, 0, 0] | 1,258 | 1,566 / 1,566 |
| 52 | salvage | 27,058 | incumbent 26,791 | +1.00% | 0.987 | 67.8 | 17 | 277 | [0, 0, 0] | 1,178 | 1,466 / 1,466 |
| 52 | continuation | 26,770 | incumbent 26,488 | +1.07% | 0.987 | 67.8 | 17 | 277 | [0, 0, 0] | 1,178 | 1,466 / 1,466 |
| 52 | continuation_landed | 26,770 | incumbent 26,488 | +1.07% | 0.987 | 67.8 | 17 | 277 | [0, 0, 0] | 1,178 | 1,466 / 1,466 |

### O_low_opening_stock (valid to W = 52; legacy 12-week: salvage +0.46%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,492 | reorder_point 6,399 | +1.46% | 0.928 | 79.8 | 163 | 72 | [0, None, 0] | 939 | 1,169 / 1,169 |
| 11 | continuation | 6,262 | reorder_point 6,285 | -0.37% | 0.928 | 79.8 | 163 | 72 | [0, None, 0] | 939 | 1,169 / 1,169 |
| 11 | continuation_landed | 6,262 | reorder_point 6,285 | -0.37% | 0.928 | 79.8 | 163 | 72 | [0, None, 0] | 939 | 1,169 / 1,169 |
| 13 | salvage | 7,407 | reorder_point 7,449 | -0.56% | 0.939 | 79.9 | 70 | 53 | [None, 0, 0] | 491 | 612 / 612 |
| 13 | continuation | 7,285 | reorder_point 7,332 | -0.64% | 0.939 | 79.9 | 70 | 53 | [None, 0, 0] | 491 | 612 / 612 |
| 13 | continuation_landed | 7,285 | reorder_point 7,332 | -0.64% | 0.939 | 79.9 | 70 | 53 | [None, 0, 0] | 491 | 612 / 612 |
| 15 | salvage | 8,437 | reorder_point 8,445 | -0.10% | 0.947 | 80.0 | 15 | 132 | [0, 0, 0] | 587 | 732 / 732 |
| 15 | continuation | 8,292 | reorder_point 8,332 | -0.48% | 0.947 | 80.0 | 15 | 132 | [0, 0, 0] | 587 | 732 / 732 |
| 15 | continuation_landed | 8,292 | reorder_point 8,332 | -0.48% | 0.947 | 80.0 | 15 | 132 | [0, 0, 0] | 587 | 732 / 732 |
| 17 | salvage | 9,502 | reorder_point 9,436 | +0.71% | 0.953 | 80.3 | 47 | 153 | [0, 0, 0] | 800 | 997 / 997 |
| 17 | continuation | 9,306 | reorder_point 9,332 | -0.28% | 0.953 | 80.3 | 47 | 153 | [0, 0, 0] | 800 | 997 / 997 |
| 17 | continuation_landed | 9,306 | reorder_point 9,332 | -0.28% | 0.953 | 80.3 | 47 | 153 | [0, 0, 0] | 800 | 997 / 997 |
| 19 | salvage | 10,478 | reorder_point 10,509 | -0.29% | 0.957 | 81.1 | 72 | 74 | [0, 0, 0] | 584 | 728 / 728 |
| 19 | continuation | 10,333 | reorder_point 10,396 | -0.60% | 0.957 | 81.1 | 72 | 74 | [0, 0, 0] | 584 | 728 / 728 |
| 19 | continuation_landed | 10,333 | reorder_point 10,396 | -0.60% | 0.957 | 81.1 | 72 | 74 | [0, 0, 0] | 584 | 728 / 728 |
| 23 | salvage | 12,590 | reorder_point 12,568 | +0.17% | 0.962 | 87.8 | 95 | 60 | [0, 0, None] | 622 | 775 / 775 |
| 23 | continuation | 12,436 | reorder_point 12,449 | -0.10% | 0.962 | 87.8 | 95 | 60 | [0, 0, None] | 622 | 775 / 775 |
| 23 | continuation_landed | 12,436 | reorder_point 12,449 | -0.10% | 0.962 | 87.8 | 95 | 60 | [0, 0, None] | 622 | 775 / 775 |
| 35 | salvage | 18,640 | reorder_point 18,608 | +0.17% | 0.973 | 92.2 | 56 | 106 | [0, None, 0] | 649 | 810 / 810 |
| 35 | continuation | 18,479 | reorder_point 18,492 | -0.07% | 0.973 | 92.2 | 56 | 106 | [0, None, 0] | 649 | 810 / 810 |
| 35 | continuation_landed | 18,479 | reorder_point 18,492 | -0.07% | 0.973 | 92.2 | 56 | 106 | [0, None, 0] | 649 | 810 / 810 |
| 47 | salvage | 24,711 | reorder_point 24,621 | +0.37% | 0.978 | 102.6 | 121 | 61 | [0, 0, None] | 726 | 905 / 905 |
| 47 | continuation | 24,532 | reorder_point 24,502 | +0.12% | 0.978 | 102.6 | 121 | 61 | [0, 0, None] | 726 | 905 / 905 |
| 47 | continuation_landed | 24,532 | reorder_point 24,502 | +0.12% | 0.978 | 102.6 | 121 | 61 | [0, 0, None] | 726 | 905 / 905 |
| 52 | salvage | 27,195 | reorder_point 27,114 | +0.30% | 0.980 | 102.6 | 43 | 124 | [0, 0, None] | 667 | 831 / 831 |
| 52 | continuation | 27,031 | reorder_point 27,006 | +0.09% | 0.980 | 102.6 | 43 | 124 | [0, 0, None] | 667 | 831 / 831 |
| 52 | continuation_landed | 27,031 | reorder_point 27,006 | +0.09% | 0.980 | 102.6 | 43 | 124 | [0, 0, None] | 667 | 831 / 831 |

### P_high_opening_stock (valid to W = 52; legacy 12-week: salvage +0.29%, continuation +0.39%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,933 | reorder_point 5,786 | +2.54% | 1.000 | 0.0 | 161 | 131 | [0, 0, None] | 1,167 | 1,452 / 1,452 |
| 11 | continuation | 5,648 | reorder_point 5,673 | -0.43% | 1.000 | 0.0 | 161 | 131 | [0, 0, None] | 1,167 | 1,452 / 1,452 |
| 11 | continuation_landed | 5,648 | reorder_point 5,673 | -0.43% | 1.000 | 0.0 | 161 | 131 | [0, 0, None] | 1,167 | 1,452 / 1,452 |
| 13 | salvage | 6,804 | reorder_point 6,837 | -0.47% | 1.000 | 0.0 | 103 | 36 | [None, None, 0] | 557 | 695 / 695 |
| 13 | continuation | 6,666 | reorder_point 6,720 | -0.79% | 1.000 | 0.0 | 103 | 36 | [None, None, 0] | 557 | 695 / 695 |
| 13 | continuation_landed | 6,666 | reorder_point 6,720 | -0.79% | 1.000 | 0.0 | 103 | 36 | [None, None, 0] | 557 | 695 / 695 |
| 15 | salvage | 7,780 | reorder_point 7,833 | -0.67% | 1.000 | 0.0 | 36 | 81 | [0, 0, 0] | 466 | 581 / 581 |
| 15 | continuation | 7,665 | reorder_point 7,720 | -0.71% | 1.000 | 0.0 | 36 | 81 | [0, 0, 0] | 466 | 581 / 581 |
| 15 | continuation_landed | 7,665 | reorder_point 7,720 | -0.71% | 1.000 | 0.0 | 36 | 81 | [0, 0, 0] | 466 | 581 / 581 |
| 17 | salvage | 8,880 | reorder_point 8,823 | +0.64% | 1.000 | 0.0 | 51 | 156 | [0, 0, 0] | 828 | 1,031 / 1,031 |
| 17 | continuation | 8,677 | reorder_point 8,719 | -0.49% | 1.000 | 0.0 | 51 | 156 | [0, 0, 0] | 828 | 1,031 / 1,031 |
| 17 | continuation_landed | 8,677 | reorder_point 8,719 | -0.49% | 1.000 | 0.0 | 51 | 156 | [0, 0, 0] | 828 | 1,031 / 1,031 |
| 19 | salvage | 9,903 | reorder_point 9,896 | +0.07% | 0.998 | 3.1 | 79 | 99 | [0, 0, 0] | 714 | 890 / 890 |
| 19 | continuation | 9,727 | reorder_point 9,783 | -0.57% | 0.998 | 3.1 | 79 | 99 | [0, 0, 0] | 714 | 890 / 890 |
| 19 | continuation_landed | 9,727 | reorder_point 9,783 | -0.57% | 0.998 | 3.1 | 79 | 99 | [0, 0, 0] | 714 | 890 / 890 |
| 23 | salvage | 11,956 | reorder_point 11,956 | +0.00% | 0.997 | 6.3 | 93 | 64 | [0, 0, None] | 627 | 781 / 781 |
| 23 | continuation | 11,801 | reorder_point 11,836 | -0.29% | 0.997 | 6.3 | 93 | 64 | [0, 0, None] | 627 | 781 / 781 |
| 23 | continuation_landed | 11,801 | reorder_point 11,836 | -0.29% | 0.997 | 6.3 | 93 | 64 | [0, 0, None] | 627 | 781 / 781 |
| 35 | salvage | 18,014 | reorder_point 17,995 | +0.11% | 0.995 | 17.0 | 55 | 76 | [0, None, 0] | 527 | 657 / 657 |
| 35 | continuation | 17,884 | reorder_point 17,880 | +0.02% | 0.995 | 17.0 | 55 | 76 | [0, None, 0] | 527 | 657 / 657 |
| 35 | continuation_landed | 17,884 | reorder_point 17,880 | +0.02% | 0.995 | 17.0 | 55 | 76 | [0, None, 0] | 527 | 657 / 657 |
| 47 | salvage | 24,132 | reorder_point 24,008 | +0.52% | 0.995 | 23.9 | 149 | 65 | [0, 0, None] | 856 | 1,066 / 1,066 |
| 47 | continuation | 23,922 | reorder_point 23,889 | +0.14% | 0.995 | 23.9 | 149 | 65 | [0, 0, None] | 856 | 1,066 / 1,066 |
| 47 | continuation_landed | 23,922 | reorder_point 23,889 | +0.14% | 0.995 | 23.9 | 149 | 65 | [0, 0, None] | 856 | 1,066 / 1,066 |
| 52 | salvage | 26,632 | reorder_point 26,502 | +0.49% | 0.995 | 23.9 | 78 | 121 | [0, 0, 0] | 798 | 994 / 994 |
| 52 | continuation | 26,436 | reorder_point 26,394 | +0.16% | 0.995 | 23.9 | 78 | 121 | [0, 0, 0] | 798 | 994 / 994 |
| 52 | continuation_landed | 26,436 | reorder_point 26,394 | +0.16% | 0.995 | 23.9 | 78 | 121 | [0, 0, 0] | 798 | 994 / 994 |

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
| 11 | salvage | 63,877 | incumbent 63,448 | +0.68% | 0.988 | 26.5 | 30 | 191 | [0, 0, 0] | 4,690 | 5,853 / 5,853 |
| 11 | continuation | 62,714 | incumbent 62,284 | +0.69% | 0.988 | 26.5 | 30 | 191 | [0, 0, 0] | 4,690 | 5,853 / 5,853 |
| 11 | continuation_landed | 62,714 | incumbent 62,284 | +0.69% | 0.988 | 26.5 | 30 | 191 | [0, 0, 0] | 4,690 | 5,853 / 5,853 |
| 13 | salvage | 75,184 | incumbent 74,755 | +0.57% | 0.989 | 28.2 | 25 | 211 | [0, 0, 0] | 5,185 | 6,470 / 6,470 |
| 13 | continuation | 73,899 | incumbent 73,470 | +0.58% | 0.989 | 28.2 | 25 | 211 | [0, 0, 0] | 5,185 | 6,470 / 6,470 |
| 13 | continuation_landed | 73,899 | incumbent 73,470 | +0.58% | 0.989 | 28.2 | 25 | 211 | [0, 0, 0] | 5,185 | 6,470 / 6,470 |
| 15 | salvage | 86,471 | incumbent 85,961 | +0.59% | 0.990 | 30.1 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 15 | continuation | 85,216 | incumbent 84,714 | +0.59% | 0.990 | 30.1 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 15 | continuation_landed | 85,216 | incumbent 84,714 | +0.59% | 0.990 | 30.1 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 17 | salvage | 97,963 | incumbent 97,463 | +0.51% | 0.991 | 32.3 | 24 | 190 | [0, 0, 0] | 4,747 | 5,925 / 5,925 |
| 17 | continuation | 96,786 | periodic:2 96,239 | +0.57% | 0.991 | 32.3 | 24 | 190 | [0, 0, 0] | 4,747 | 5,925 / 5,925 |
| 17 | continuation_landed | 96,786 | periodic:2 96,239 | +0.57% | 0.991 | 32.3 | 24 | 190 | [0, 0, 0] | 4,747 | 5,925 / 5,925 |
| 19 | salvage | 109,053 | incumbent 108,553 | +0.46% | 0.991 | 36.0 | 23 | 199 | [0, 0, 0] | 4,758 | 5,938 / 5,938 |
| 19 | continuation | 107,873 | periodic:2 107,366 | +0.47% | 0.991 | 36.0 | 23 | 199 | [0, 0, 0] | 4,758 | 5,938 / 5,938 |
| 19 | continuation_landed | 107,873 | periodic:2 107,366 | +0.47% | 0.991 | 36.0 | 23 | 199 | [0, 0, 0] | 4,758 | 5,938 / 5,938 |
| 23 | salvage | 131,453 | incumbent 131,003 | +0.34% | 0.992 | 37.7 | 46 | 180 | [0, 0, 0] | 4,830 | 6,028 / 6,028 |
| 23 | continuation | 130,255 | incumbent 129,760 | +0.38% | 0.992 | 37.7 | 46 | 180 | [0, 0, 0] | 4,830 | 6,028 / 6,028 |
| 23 | continuation_landed | 130,255 | incumbent 129,760 | +0.38% | 0.992 | 37.7 | 46 | 180 | [0, 0, 0] | 4,830 | 6,028 / 6,028 |
| 35 | salvage | 197,380 | incumbent 196,690 | +0.35% | 0.993 | 51.0 | 39 | 173 | [0, 0, 0] | 4,607 | 5,750 / 5,750 |
| 35 | continuation | 196,237 | incumbent 195,436 | +0.41% | 0.993 | 51.0 | 39 | 173 | [0, 0, 0] | 4,607 | 5,750 / 5,750 |
| 35 | continuation_landed | 196,237 | incumbent 195,436 | +0.41% | 0.993 | 51.0 | 39 | 173 | [0, 0, 0] | 4,607 | 5,750 / 5,750 |
| 47 | salvage | 264,743 | incumbent 263,353 | +0.53% | 0.992 | 72.5 | 123 | 170 | [0, 0, 0] | 5,372 | 6,703 / 6,703 |
| 47 | continuation | 263,413 | incumbent 262,077 | +0.51% | 0.992 | 72.5 | 123 | 170 | [0, 0, 0] | 5,372 | 6,703 / 6,703 |
| 47 | continuation_landed | 263,413 | incumbent 262,077 | +0.51% | 0.992 | 72.5 | 123 | 170 | [0, 0, 0] | 5,372 | 6,703 / 6,703 |
| 52 | salvage | 292,633 | incumbent 290,755 | +0.65% | 0.991 | 88.8 | 23 | 197 | [0, 0, 0] | 4,882 | 6,093 / 6,093 |
| 52 | continuation | 291,422 | incumbent 289,535 | +0.65% | 0.991 | 88.8 | 23 | 197 | [0, 0, 0] | 4,882 | 6,093 / 6,093 |
| 52 | continuation_landed | 291,422 | incumbent 289,535 | +0.65% | 0.991 | 88.8 | 23 | 197 | [0, 0, 0] | 4,882 | 6,093 / 6,093 |

### S_cash_constrained (valid to W = 12; legacy 12-week: salvage +0.26%, continuation +3.59%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,508 | economic_lot 6,234 | +4.39% | 1.000 | 0.0 | 241 | 37 | [0, None, None] | 1,113 | 1,385 / 1,498 |
| 11 | continuation | 6,236 | economic_lot 5,924 | +5.27% | 1.000 | 0.0 | 241 | 37 | [0, None, None] | 1,113 | 1,385 / 1,498 |
| 11 | continuation_landed | 6,123 | economic_lot 5,875 | +4.21% | 1.000 | 0.0 | 241 | 37 | [0, None, None] | 1,113 | 1,385 / 1,498 |

### T_combined_realistic (valid to W = 52; legacy 12-week: salvage -11.47%, continuation -4.21%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 18,145 | economic_lot 17,593 | +3.14% | 0.999 | 2.1 | 1613 | 0 | [None, None, None] | 6,452 | 7,879 / 10,071 |
| 11 | continuation | 16,718 | economic_lot 15,846 | +5.51% | 0.999 | 2.1 | 1613 | 0 | [None, None, None] | 6,452 | 7,879 / 10,071 |
| 11 | continuation_landed | 14,526 | economic_lot 13,782 | +5.40% | 0.999 | 2.1 | 1613 | 0 | [None, None, None] | 6,452 | 7,879 / 10,071 |
| 13 | salvage | 19,797 | economic_lot 19,258 | +2.80% | 0.999 | 2.1 | 1212 | 0 | [None, None, None] | 4,847 | 5,952 / 7,587 |
| 13 | continuation | 18,692 | economic_lot 17,807 | +4.97% | 0.999 | 2.1 | 1212 | 0 | [None, None, None] | 4,847 | 5,952 / 7,587 |
| 13 | continuation_landed | 17,056 | economic_lot 16,143 | +5.66% | 0.999 | 2.1 | 1212 | 0 | [None, None, None] | 4,847 | 5,952 / 7,587 |
| 15 | salvage | 21,425 | economic_lot 20,889 | +2.57% | 0.999 | 2.1 | 815 | 0 | [None, None, None] | 3,262 | 4,024 / 5,108 |
| 15 | continuation | 20,663 | economic_lot 19,761 | +4.56% | 0.999 | 2.1 | 815 | 0 | [None, None, None] | 3,262 | 4,024 / 5,108 |
| 15 | continuation_landed | 19,579 | economic_lot 18,492 | +5.88% | 0.999 | 2.1 | 815 | 0 | [None, None, None] | 3,262 | 4,024 / 5,108 |
| 17 | salvage | 24,765 | economic_lot 22,542 | +9.86% | 0.999 | 2.1 | 516 | 590 | [None, None, 0] | 4,425 | 5,408 / 7,051 |
| 17 | continuation | 23,783 | economic_lot 21,760 | +9.30% | 0.999 | 2.1 | 516 | 590 | [None, None, 0] | 4,425 | 5,408 / 7,051 |
| 17 | continuation_landed | 22,139 | economic_lot 20,889 | +5.99% | 0.999 | 2.1 | 516 | 590 | [None, None, 0] | 4,425 | 5,408 / 7,051 |
| 19 | salvage | 27,573 | economic_lot 25,399 | +8.56% | 0.999 | 2.1 | 1288 | 0 | [None, None, None] | 5,151 | 6,299 / 7,976 |
| 19 | continuation | 26,425 | economic_lot 24,451 | +8.07% | 0.999 | 2.1 | 1288 | 0 | [None, None, None] | 5,151 | 6,299 / 7,976 |
| 19 | continuation_landed | 24,749 | economic_lot 23,412 | +5.71% | 0.999 | 2.1 | 1288 | 0 | [None, None, None] | 5,151 | 6,299 / 7,976 |
| 23 | salvage | 31,506 | economic_lot 31,248 | +0.82% | 0.999 | 2.6 | 704 | 0 | [None, None, None] | 2,816 | 3,480 / 4,409 |
| 23 | continuation | 30,842 | economic_lot 29,907 | +3.13% | 0.999 | 2.6 | 704 | 0 | [None, None, None] | 2,816 | 3,480 / 4,409 |
| 23 | continuation_landed | 29,913 | economic_lot 28,428 | +5.22% | 0.999 | 2.6 | 704 | 0 | [None, None, None] | 2,816 | 3,480 / 4,409 |
| 35 | salvage | 48,881 | economic_lot 44,664 | +9.44% | 1.000 | 2.6 | 830 | 610 | [0, None, None] | 5,759 | 7,041 / 9,009 |
| 35 | continuation | 47,600 | economic_lot 43,725 | +8.86% | 1.000 | 2.6 | 830 | 610 | [0, None, None] | 5,759 | 7,041 / 9,009 |
| 35 | continuation_landed | 45,632 | economic_lot 42,728 | +6.80% | 1.000 | 2.6 | 830 | 610 | [0, None, None] | 5,759 | 7,041 / 9,009 |
| 47 | salvage | 63,236 | economic_lot 59,064 | +7.06% | 1.000 | 2.6 | 760 | 0 | [None, None, None] | 3,038 | 3,753 / 4,795 |
| 47 | continuation | 62,522 | economic_lot 58,221 | +7.39% | 1.000 | 2.6 | 760 | 0 | [None, None, None] | 3,038 | 3,753 / 4,795 |
| 47 | continuation_landed | 61,480 | economic_lot 57,297 | +7.30% | 1.000 | 2.6 | 760 | 0 | [None, None, None] | 3,038 | 3,753 / 4,795 |
| 52 | salvage | 71,863 | economic_lot 66,626 | +7.86% | 1.000 | 2.6 | 1625 | 101 | [None, 0, None] | 6,907 | 8,424 / 10,786 |
| 52 | continuation | 70,347 | economic_lot 65,196 | +7.90% | 1.000 | 2.6 | 1625 | 101 | [None, 0, None] | 6,907 | 8,424 / 10,786 |
| 52 | continuation_landed | 67,984 | economic_lot 63,612 | +6.87% | 1.000 | 2.6 | 1625 | 101 | [None, 0, None] | 6,907 | 8,424 / 10,786 |

## Stage 4: convergence classification (section 5), both rules

| fixture | valid at 52 | rule | delta @11 (rolling) | @23 | @35 | @47 | @52 | max |delta(W)-delta(52)| over 40..52 | stable | class |
|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | salvage | +1.63% | +1.18% | +1.10% | +0.95% | +0.86% | 0.25 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation | +1.70% | +1.19% | +1.06% | +0.96% | +0.87% | 0.23 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation_landed | +1.70% | +1.19% | +1.06% | +0.96% | +0.87% | 0.23 pp | yes | A. STABLE PASS |
| B_fixed_order_cost_replace_sold | yes | salvage | +5.77% | -3.15% | +7.14% | +2.27% | +3.69% | 5.67 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation | +6.52% | +1.14% | +4.14% | +2.83% | +3.06% | 1.93 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation_landed | +3.41% | +0.83% | +2.78% | +2.30% | +2.49% | 1.44 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | salvage | +9.84% | +1.62% | +1.41% | +1.54% | -0.24% | 1.18 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | continuation | +2.32% | +0.77% | +0.74% | +0.61% | +0.30% | 0.36 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| C_moq_four_weeks | yes | continuation_landed | +2.32% | +0.77% | +0.74% | +0.61% | +0.30% | 0.36 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| D_case_multiple | yes | salvage | -0.94% | +0.08% | +0.65% | +0.60% | +0.59% | 0.20 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation | -0.16% | +0.30% | +0.73% | +0.70% | +0.63% | 0.17 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation_landed | -0.16% | +0.30% | +0.73% | +0.70% | +0.63% | 0.17 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | salvage | +0.04% | +0.01% | -0.00% | -0.06% | -0.39% | 0.39 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation | +0.04% | -0.01% | -0.03% | -0.06% | -0.17% | 0.15 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation_landed | +0.04% | -0.02% | -0.03% | -0.06% | -0.10% | 0.07 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | salvage | +4.46% | +4.34% | +1.55% | +1.19% | +1.76% | 0.56 pp | NO | E. NON-CONVERGENT |
| F_mov_two_skus | yes | continuation | +1.28% | +1.27% | +0.83% | +0.64% | +0.72% | 0.08 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | continuation_landed | +1.28% | +1.27% | +0.83% | +0.64% | +0.72% | 0.08 pp | yes | A. STABLE PASS |
| G_freight_tiers | yes | salvage | +8.60% | +8.68% | +4.68% | +5.63% | +8.06% | 2.47 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation | +12.70% | +10.21% | +5.79% | +6.15% | +7.58% | 1.68 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation_landed | +11.01% | +9.27% | +6.26% | +6.15% | +6.18% | 0.83 pp | yes | D. BOUNDARY-SENSITIVE -> FAIL |
| H_per_pallet_freight | yes | salvage | -2.11% | -2.41% | -1.48% | -0.62% | -1.07% | 1.34 pp | NO | E. NON-CONVERGENT |
| H_per_pallet_freight | yes | continuation | -2.45% | -2.10% | -1.42% | -1.06% | -1.20% | 0.54 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | continuation_landed | -2.36% | -1.75% | -1.31% | -1.32% | -1.27% | 0.19 pp | yes | A. STABLE PASS |
| I_max_pallets_ftl_cap | yes | salvage | +4.39% | +7.44% | +12.84% | +9.68% | +8.30% | 2.78 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation | +5.38% | +8.33% | +11.78% | +9.27% | +8.16% | 2.26 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation_landed | +6.87% | +9.85% | +7.46% | +7.16% | +7.14% | 0.68 pp | yes | D. BOUNDARY-SENSITIVE -> FAIL |
| J_net60_cost_of_capital | yes | salvage | +5.60% | +0.01% | +0.13% | -0.15% | +1.30% | 1.18 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation | +1.63% | -0.13% | +0.01% | -0.15% | +0.33% | 1.03 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation_landed | +0.88% | -0.15% | -0.01% | -0.14% | +0.15% | 0.65 pp | yes | A. STABLE PASS |
| K_deposit_early_cash | yes | salvage | +5.59% | +0.01% | +0.13% | -0.15% | +1.30% | 1.17 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation | +1.69% | -0.13% | +0.01% | -0.15% | +0.32% | 1.05 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation_landed | +0.94% | -0.15% | -0.01% | -0.15% | +0.15% | 0.67 pp | yes | A. STABLE PASS |
| L_high_holding_rate | yes | salvage | +4.93% | +3.90% | +2.93% | +2.83% | -0.11% | 2.96 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation | +1.80% | +2.88% | +1.90% | +1.69% | +0.72% | 1.01 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation_landed | +1.30% | +2.04% | +1.45% | +1.35% | +0.81% | 0.60 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | salvage | +2.04% | +1.05% | +0.61% | +0.36% | +0.30% | 0.43 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| M_order_calendar_wednesday | yes | continuation | +0.94% | +0.53% | +0.23% | +0.04% | +0.05% | 0.17 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | continuation_landed | +0.94% | +0.53% | +0.23% | +0.04% | +0.05% | 0.17 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | salvage | +1.07% | +1.03% | +1.04% | +1.08% | +1.00% | 0.28 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation | +0.50% | +1.13% | +0.89% | +1.14% | +1.07% | 0.18 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation_landed | +0.50% | +1.13% | +0.89% | +1.14% | +1.07% | 0.18 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | salvage | +1.46% | +0.17% | +0.17% | +0.37% | +0.30% | 0.24 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation | -0.37% | -0.10% | -0.07% | +0.12% | +0.09% | 0.13 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation_landed | -0.37% | -0.10% | -0.07% | +0.12% | +0.09% | 0.13 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | salvage | +2.54% | +0.00% | +0.11% | +0.52% | +0.49% | 0.44 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| P_high_opening_stock | yes | continuation | -0.43% | -0.29% | +0.02% | +0.14% | +0.16% | 0.11 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | continuation_landed | -0.43% | -0.29% | +0.02% | +0.14% | +0.16% | 0.11 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | salvage | +0.05% | +0.05% | -0.01% | +0.32% | +0.19% | 0.14 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation | +0.05% | +0.05% | +0.03% | +0.22% | +0.19% | 0.04 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation_landed | +0.05% | +0.05% | +0.03% | +0.22% | +0.19% | 0.04 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | salvage | +0.68% | +0.34% | +0.35% | +0.53% | +0.65% | 0.39 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation | +0.69% | +0.38% | +0.41% | +0.51% | +0.65% | 0.18 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation_landed | +0.69% | +0.38% | +0.41% | +0.51% | +0.65% | 0.18 pp | yes | A. STABLE PASS |
| S_cash_constrained | no (to 12) | salvage | +4.39% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation | +5.27% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation_landed | +4.21% | - | - | - | - | - | - | INVALID AT 52 |
| T_combined_realistic | yes | salvage | +3.14% | +0.82% | +9.44% | +7.06% | +7.86% | 2.00 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation | +5.51% | +3.13% | +8.86% | +7.39% | +7.90% | 1.30 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation_landed | +5.40% | +5.22% | +6.80% | +7.30% | +6.87% | 0.96 pp | yes | D. BOUNDARY-SENSITIVE -> FAIL |

## Section 6: boundary-sensitivity index and the selection rule

| rule | Stage 7 tests | BSI (pp per two-review shift, all ten policy pairs, valid fixtures, three seeds) | fixtures stable at 52 |
|---|---|---|---|
| salvage | fail | 1.635 | 9 / 19 |
| continuation | fail | 0.904 | 12 / 19 |
| continuation_landed | pass | 0.477 | 18 / 19 |

**Declared rule: continuation_landed** (the only rule passing the twelve tests).

BSI per rule restricted to baseline-only pairs (no ZAAD in the pair), as a check that the index is not driven by ZAAD:

* salvage: 1.391 pp
* continuation: 0.795 pp
* continuation_landed: 0.426 pp

## Section 8, Option D diagnostic: start offset s with symmetric endpoint handling (window [s, 52])

| fixture | rule | s=0 | s=4 | s=8 |
|---|---|---|---|---|
| A_no_terms_good_incumbent | salvage | +0.86% vs incumbent | +0.85% vs incumbent | +0.73% vs incumbent |
| A_no_terms_good_incumbent | continuation | +0.87% vs incumbent | +0.85% vs incumbent | +0.73% vs incumbent |
| A_no_terms_good_incumbent | continuation_landed | +0.87% vs incumbent | +0.85% vs incumbent | +0.73% vs incumbent |
| B_fixed_order_cost_replace_sold | salvage | +3.69% vs economic_lot | +6.93% vs economic_lot | +7.10% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation | +3.06% vs economic_lot | +3.60% vs economic_lot | +3.53% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation_landed | +2.49% vs economic_lot | +3.38% vs economic_lot | +3.09% vs economic_lot |
| C_moq_four_weeks | salvage | -0.24% vs reorder_point | -2.26% vs reorder_point | -2.14% vs reorder_point |
| C_moq_four_weeks | continuation | +0.30% vs reorder_point | -0.01% vs reorder_point | -0.03% vs reorder_point |
| C_moq_four_weeks | continuation_landed | +0.30% vs reorder_point | -0.01% vs reorder_point | -0.03% vs reorder_point |
| D_case_multiple | salvage | +0.59% vs incumbent | +0.65% vs incumbent | +0.72% vs incumbent |
| D_case_multiple | continuation | +0.63% vs incumbent | +0.68% vs incumbent | +0.75% vs incumbent |
| D_case_multiple | continuation_landed | +0.63% vs incumbent | +0.68% vs incumbent | +0.75% vs incumbent |
| E_pallet_multiple | salvage | -0.39% vs incumbent | -0.43% vs incumbent | -0.86% vs incumbent |
| E_pallet_multiple | continuation | -0.17% vs incumbent | -0.19% vs incumbent | -0.33% vs incumbent |
| E_pallet_multiple | continuation_landed | -0.10% vs incumbent | -0.11% vs incumbent | -0.16% vs incumbent |
| F_mov_two_skus | salvage | +1.76% vs periodic:2 | +0.35% vs periodic:2 | +0.89% vs periodic:2 |
| F_mov_two_skus | continuation | +0.72% vs periodic:2 | +0.52% vs periodic:2 | +0.51% vs periodic:2 |
| F_mov_two_skus | continuation_landed | +0.72% vs periodic:2 | +0.52% vs periodic:2 | +0.51% vs periodic:2 |
| G_freight_tiers | salvage | +8.06% vs economic_lot | +6.12% vs economic_lot | +6.48% vs economic_lot |
| G_freight_tiers | continuation | +7.58% vs economic_lot | +5.54% vs economic_lot | +5.96% vs economic_lot |
| G_freight_tiers | continuation_landed | +6.18% vs economic_lot | +5.79% vs economic_lot | +5.34% vs economic_lot |
| H_per_pallet_freight | salvage | -1.07% vs periodic:2 | -1.62% vs periodic:2 | -2.69% vs periodic:2 |
| H_per_pallet_freight | continuation | -1.20% vs periodic:2 | -1.46% vs periodic:2 | -1.84% vs periodic:2 |
| H_per_pallet_freight | continuation_landed | -1.27% vs periodic:2 | -1.35% vs periodic:2 | -1.29% vs periodic:2 |
| I_max_pallets_ftl_cap | salvage | +8.30% vs economic_lot | +8.23% vs economic_lot | +7.44% vs economic_lot |
| I_max_pallets_ftl_cap | continuation | +8.16% vs economic_lot | +8.06% vs economic_lot | +7.59% vs economic_lot |
| I_max_pallets_ftl_cap | continuation_landed | +7.14% vs economic_lot | +7.33% vs economic_lot | +7.68% vs economic_lot |
| J_net60_cost_of_capital | salvage | +1.30% vs economic_lot | +1.46% vs economic_lot | +1.56% vs economic_lot |
| J_net60_cost_of_capital | continuation | +0.33% vs economic_lot | +0.36% vs economic_lot | +0.39% vs economic_lot |
| J_net60_cost_of_capital | continuation_landed | +0.15% vs economic_lot | +0.17% vs economic_lot | +0.18% vs economic_lot |
| K_deposit_early_cash | salvage | +1.30% vs economic_lot | +1.46% vs economic_lot | +1.56% vs economic_lot |
| K_deposit_early_cash | continuation | +0.32% vs economic_lot | +0.35% vs economic_lot | +0.38% vs economic_lot |
| K_deposit_early_cash | continuation_landed | +0.15% vs economic_lot | +0.16% vs economic_lot | +0.18% vs economic_lot |
| L_high_holding_rate | salvage | -0.11% vs economic_lot | -1.05% vs economic_lot | -1.55% vs economic_lot |
| L_high_holding_rate | continuation | +0.72% vs economic_lot | +0.22% vs economic_lot | -0.03% vs economic_lot |
| L_high_holding_rate | continuation_landed | +0.81% vs economic_lot | +0.63% vs economic_lot | +0.41% vs economic_lot |
| M_order_calendar_wednesday | salvage | +0.30% vs incumbent | +0.14% vs incumbent | -0.22% vs incumbent |
| M_order_calendar_wednesday | continuation | +0.05% vs incumbent | -0.00% vs incumbent | -0.28% vs incumbent |
| M_order_calendar_wednesday | continuation_landed | +0.05% vs incumbent | -0.00% vs incumbent | -0.28% vs incumbent |
| N_long_lead_21_days | salvage | +1.00% vs incumbent | +0.90% vs incumbent | +0.23% vs incumbent |
| N_long_lead_21_days | continuation | +1.07% vs incumbent | +1.11% vs incumbent | +0.93% vs incumbent |
| N_long_lead_21_days | continuation_landed | +1.07% vs incumbent | +1.11% vs incumbent | +0.93% vs incumbent |
| O_low_opening_stock | salvage | +0.30% vs reorder_point | +0.17% vs reorder_point | -0.64% vs reorder_point |
| O_low_opening_stock | continuation | +0.09% vs reorder_point | +0.07% vs reorder_point | -0.02% vs reorder_point |
| O_low_opening_stock | continuation_landed | +0.09% vs reorder_point | +0.07% vs reorder_point | -0.02% vs reorder_point |
| P_high_opening_stock | salvage | +0.49% vs reorder_point | +0.09% vs reorder_point | -0.04% vs reorder_point |
| P_high_opening_stock | continuation | +0.16% vs reorder_point | +0.12% vs reorder_point | +0.15% vs reorder_point |
| P_high_opening_stock | continuation_landed | +0.16% vs reorder_point | +0.12% vs reorder_point | +0.15% vs reorder_point |
| Q_volatile_demand_high_target | salvage | +0.19% vs incumbent | +0.19% vs incumbent | +0.25% vs periodic:2 |
| Q_volatile_demand_high_target | continuation | +0.19% vs incumbent | +0.19% vs incumbent | +0.22% vs incumbent |
| Q_volatile_demand_high_target | continuation_landed | +0.19% vs incumbent | +0.19% vs incumbent | +0.22% vs incumbent |
| R_asymmetric_prices_mov | salvage | +0.65% vs incumbent | +0.72% vs incumbent | +0.72% vs incumbent |
| R_asymmetric_prices_mov | continuation | +0.65% vs incumbent | +0.71% vs incumbent | +0.73% vs incumbent |
| R_asymmetric_prices_mov | continuation_landed | +0.65% vs incumbent | +0.71% vs incumbent | +0.73% vs incumbent |
| T_combined_realistic | salvage | +7.86% vs economic_lot | +7.35% vs economic_lot | +2.32% vs economic_lot |
| T_combined_realistic | continuation | +7.90% vs economic_lot | +6.85% vs economic_lot | +3.82% vs economic_lot |
| T_combined_realistic | continuation_landed | +6.87% vs economic_lot | +6.59% vs economic_lot | +5.83% vs economic_lot |

## Section 8, Option E diagnostic: per-week average cost at 52 and each policy at its own cycle-minimum endpoint in [40, 52] (declared rule)

| fixture | ZAAD per week | best baseline per week | delta (same as @52) | cycle-minimum endpoints (policy: W) | delta at own cycle minima, per-week normalised |
|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 512.7 | incumbent 508.3 | +0.87% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +1.23% |
| B_fixed_order_cost_replace_sold | 545.1 | economic_lot 531.8 | +2.49% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 52, 'gated': 51} | +2.50% |
| C_moq_four_weeks | 509.8 | reorder_point 508.3 | +0.30% | {'incumbent': 40, 'reorder_point': 43, 'periodic:2': 42, 'economic_lot': 43, 'gated': 49} | +0.20% |
| D_case_multiple | 508.2 | incumbent 505.0 | +0.63% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 51} | +0.36% |
| E_pallet_multiple | 536.0 | incumbent 536.6 | -0.10% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | -0.03% |
| F_mov_two_skus | 1,019.9 | periodic:2 1,012.6 | +0.72% | {'incumbent': 40, 'reorder_point': 51, 'periodic:2': 44, 'economic_lot': 51, 'gated': 44} | +0.68% |
| G_freight_tiers | 1,295.0 | economic_lot 1,219.6 | +6.18% | {'incumbent': 43, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 41} | +6.04% |
| H_per_pallet_freight | 574.9 | periodic:2 582.2 | -1.27% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 52} | -1.55% |
| I_max_pallets_ftl_cap | 837.8 | economic_lot 782.0 | +7.14% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 49, 'gated': 51} | +7.40% |
| J_net60_cost_of_capital | 528.8 | economic_lot 528.0 | +0.15% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 41} | +0.06% |
| K_deposit_early_cash | 529.0 | economic_lot 528.2 | +0.15% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 41} | +0.11% |
| L_high_holding_rate | 541.5 | economic_lot 537.2 | +0.81% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 40, 'gated': 41} | +1.29% |
| M_order_calendar_wednesday | 515.1 | incumbent 514.9 | +0.05% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.15% |
| N_long_lead_21_days | 514.8 | incumbent 509.4 | +1.07% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 52} | +0.49% |
| O_low_opening_stock | 519.8 | reorder_point 519.3 | +0.09% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.30% |
| P_high_opening_stock | 508.4 | reorder_point 507.6 | +0.16% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.31% |
| Q_volatile_demand_high_target | 491.9 | incumbent 491.0 | +0.19% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.22% |
| R_asymmetric_prices_mov | 5,604.3 | incumbent 5,568.0 | +0.65% | {'incumbent': 51, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 50} | +0.42% |
| T_combined_realistic | 1,307.4 | economic_lot 1,223.3 | +6.87% | {'incumbent': 40, 'reorder_point': 52, 'periodic:2': 42, 'economic_lot': 46, 'gated': 47} | +7.66% |

## Stage 9: A-T at the declared benchmark (rolling horizon, W* = 52, rule continuation_landed) beside the legacy twelve-week result

| fixture | valid | legacy delta (salvage) | rolling @11 | **declared @52** | verdict | class | service | breaches | unmet | avg inv units | terminal on-hand | in-transit | purchases | freight | ordering | carrying | financing | shortage | inventory value change | terminal credit (rule) | P1 / P0 owned | actions | abstentions | legacy first-review checks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | +0.43% | +1.70% | **+0.87%** vs incumbent | PASS | A. STABLE PASS | 0.989 | 4.7 | 57.0 | 15 | 6 | 102 | 25,729 | 0 | 0 | 11 | 0 | 712 | 315 | 543 | 138 / 18 | 38 | 11 | ok |
| B_fixed_order_cost_replace_sold | yes | -10.70% | +3.41% | **+2.49%** vs economic_lot | FAIL | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 621 | 352 | 351 | 28,993 | 0 | 1,833 | 464 | 0 | 0 | -2,061 | 3,697 | 137 / 19 | 150 | 0 | ok |
| C_moq_four_weeks | yes | +3.61% | +2.32% | **+0.30%** vs reorder_point | PASS | C. BOUNDARY-SENSITIVE -> PASS | 1.000 | 0.0 | 2.1 | 340 | 212 | 132 | 27,191 | 0 | 0 | 255 | 0 | 26 | -627 | 1,712 | 139 / 17 | 139 | 0 | ok |
| D_case_multiple | yes | -0.58% | -0.16% | **+0.63%** vs incumbent | PASS | A. STABLE PASS | 0.995 | 2.0 | 23.4 | 34 | 19 | 110 | 26,000 | 0 | 0 | 26 | 0 | 293 | 234 | 643 | 138 / 18 | 70 | 13 | ok |
| E_pallet_multiple | yes | -0.00% | +0.04% | **-0.10%** vs incumbent | PASS | A. STABLE PASS | 1.000 | 0.0 | 1.3 | 109 | 104 | 64 | 26,333 | 1,580 | 0 | 81 | 0 | 16 | 78 | 888 | 139 / 17 | 39 | 4 | ok |
| F_mov_two_skus | yes | +0.24% | +1.28% | **+0.72%** vs periodic:2 | PASS | A. STABLE PASS | 1.000 | 0.0 | 4.1 | 682 | 721 | 130 | 55,200 | 0 | 0 | 510 | 0 | 51 | -1,903 | 4,226 | 123 / 33 | 118 | 0 | ok |
| G_freight_tiers | yes | -10.01% | +11.01% | **+6.18%** vs economic_lot | FAIL | D. BOUNDARY-SENSITIVE -> FAIL | 1.000 | 0.0 | 2.6 | 959 | 869 | 612 | 58,356 | 14,667 | 1,367 | 717 | 0 | 33 | -4,424 | 9,299 | 124 / 32 | 144 | 0 | ok |
| H_per_pallet_freight | yes | -3.73% | -2.36% | **-1.27%** vs periodic:2 | PASS | A. STABLE PASS | 0.995 | 1.7 | 26.3 | 125 | 80 | 63 | 26,027 | 3,500 | 0 | 94 | 0 | 329 | 180 | 806 | 138 / 18 | 117 | 11 | ok |
| I_max_pallets_ftl_cap | yes | +0.53% | +6.87% | **+7.14%** vs economic_lot | FAIL | D. BOUNDARY-SENSITIVE -> FAIL | 1.000 | 0.0 | 2.1 | 245 | 95 | 286 | 27,409 | 16,033 | 2,350 | 183 | 0 | 27 | -777 | 3,186 | 138 / 18 | 138 | 0 | ok |
| J_net60_cost_of_capital | yes | -11.06% | +0.88% | **+0.15%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 582 | 374 | 328 | 28,983 | 0 | 800 | 435 | 56 | 0 | -2,055 | 3,528 | 136 / 20 | 142 | 5 | ok |
| K_deposit_early_cash | yes | -11.20% | +0.94% | **+0.15%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 582 | 374 | 328 | 28,983 | 0 | 800 | 435 | 69 | 0 | -2,055 | 3,528 | 136 / 20 | 142 | 5 | ok |
| L_high_holding_rate | yes | -10.16% | +1.30% | **+0.81%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 612 | 351 | 326 | 28,868 | 0 | 1,050 | 915 | 0 | 0 | -1,957 | 3,424 | 137 / 19 | 151 | 0 | ok |
| M_order_calendar_wednesday | yes | -0.54% | +0.94% | **+0.05%** vs incumbent | PASS | A. STABLE PASS | 0.987 | 2.0 | 65.9 | 88 | 91 | 189 | 26,540 | 0 | 0 | 66 | 0 | 824 | -370 | 1,394 | 13 / 143 | 144 | 0 | ok |
| N_long_lead_21_days | yes | -0.71% | +0.50% | **+1.07%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.987 | 4.0 | 67.8 | 64 | 17 | 277 | 25,591 | 0 | 0 | 48 | 0 | 847 | 572 | 1,466 | 133 / 23 | 124 | 5 | ['categories'] |
| O_low_opening_stock | yes | +0.46% | -0.37% | **+0.09%** vs reorder_point | PASS | A. STABLE PASS | 0.980 | 2.7 | 102.6 | 88 | 43 | 124 | 26,415 | 0 | 0 | 66 | 0 | 1,282 | -567 | 831 | 99 / 57 | 151 | 2 | ok |
| P_high_opening_stock | yes | +0.29% | -0.43% | **+0.16%** vs reorder_point | PASS | A. STABLE PASS | 0.995 | 1.7 | 23.9 | 111 | 78 | 121 | 24,048 | 0 | 0 | 83 | 0 | 298 | 2,202 | 994 | 138 / 18 | 128 | 9 | ok |
| Q_volatile_demand_high_target | yes | +0.85% | +0.05% | **+0.19%** vs incumbent | PASS | A. STABLE PASS | 0.991 | 3.0 | 45.9 | 73 | 58 | 97 | 24,973 | 0 | 0 | 55 | 0 | 574 | 132 | 771 | 69 / 87 | 19 | 0 | ok |
| R_asymmetric_prices_mov | yes | -0.05% | +0.69% | **+0.65%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.991 | 2.3 | 88.8 | 42 | 23 | 197 | 283,780 | 0 | 0 | 150 | 0 | 5,334 | 3,368 | 6,093 | 123 / 33 | 27 | 9 | ['categories'] |
| S_cash_constrained | no (to 12) | +0.26% | +4.21% | **+4.61%** vs economic_lot | INVALID AT 52 (diagnostic @12: outside tolerance) | - | 1.000 | 0.0 | 0.0 | 274 | 173 | 135 | 6,975 | 0 | 600 | 47 | 6 | 0 | -481 | 1,664 | 36 / 0 | 36 | 0 | ok |
| T_combined_realistic | yes | -11.47% | +5.40% | **+6.87%** vs economic_lot | FAIL | D. BOUNDARY-SENSITIVE -> FAIL | 1.000 | 0.0 | 2.6 | 975 | 1625 | 101 | 59,760 | 13,700 | 2,467 | 875 | 127 | 33 | -5,407 | 10,786 | 124 / 32 | 141 | 0 | ok |

Runtime, ZAAD reviews: n 3013, p50 0.99 s, p90 5.85 s, p95 11.38 s, max 79.2 s; total wall of all cells 8,775 s.

