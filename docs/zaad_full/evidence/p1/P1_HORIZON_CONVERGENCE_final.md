# P1 extended-window benchmark: convergence, stability, selection and the declared result

Source `docs/zaad_full/evidence/p1/closure/horizon52_final.jsonl`: 300 cells, rolling twelve-period planning horizon, 52 reviews requested, stitched truth per seed, scored at every endpoint under both terminal rules. Pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`.

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
| 47 | salvage | 24,261 | incumbent 24,046 | +0.89% | 0.988 | 55.1 | 13 | 106 | [0, 0, 0] | 479 | 598 / 598 |
| 47 | continuation | 24,142 | incumbent 23,927 | +0.90% | 0.988 | 55.1 | 13 | 106 | [0, 0, 0] | 479 | 598 / 598 |
| 47 | continuation_landed | 24,142 | incumbent 23,927 | +0.90% | 0.988 | 55.1 | 13 | 106 | [0, 0, 0] | 479 | 598 / 598 |
| 52 | salvage | 26,753 | incumbent 26,539 | +0.81% | 0.989 | 55.1 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation | 26,645 | incumbent 26,431 | +0.81% | 0.989 | 55.1 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |
| 52 | continuation_landed | 26,645 | incumbent 26,431 | +0.81% | 0.989 | 55.1 | 6 | 102 | [0, 0, 0] | 435 | 543 / 543 |

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
| 11 | salvage | 6,435 | reorder_point 5,898 | +9.11% | 1.000 | 0.0 | 399 | 260 | [0, None, 0] | 2,635 | 3,257 / 3,257 |
| 11 | continuation | 5,812 | reorder_point 5,681 | +2.31% | 1.000 | 0.0 | 399 | 260 | [0, None, 0] | 2,635 | 3,257 / 3,257 |
| 11 | continuation_landed | 5,812 | reorder_point 5,681 | +2.31% | 1.000 | 0.0 | 399 | 260 | [0, None, 0] | 2,635 | 3,257 / 3,257 |
| 13 | salvage | 7,262 | reorder_point 7,147 | +1.60% | 1.000 | 0.0 | 456 | 0 | [None, None, None] | 1,822 | 2,260 / 2,260 |
| 13 | continuation | 6,824 | reorder_point 6,749 | +1.12% | 1.000 | 0.0 | 456 | 0 | [None, None, None] | 1,822 | 2,260 / 2,260 |
| 13 | continuation_landed | 6,824 | reorder_point 6,749 | +1.12% | 1.000 | 0.0 | 456 | 0 | [None, None, None] | 1,822 | 2,260 / 2,260 |
| 15 | salvage | 8,209 | reorder_point 7,937 | +3.42% | 1.000 | 0.0 | 388 | 0 | [None, None, None] | 1,553 | 1,929 / 1,929 |
| 15 | continuation | 7,833 | reorder_point 7,727 | +1.37% | 1.000 | 0.0 | 388 | 0 | [None, None, None] | 1,553 | 1,929 / 1,929 |
| 15 | continuation_landed | 7,833 | reorder_point 7,727 | +1.37% | 1.000 | 0.0 | 388 | 0 | [None, None, None] | 1,553 | 1,929 / 1,929 |
| 17 | salvage | 9,499 | reorder_point 9,167 | +3.62% | 1.000 | 0.0 | 192 | 458 | [0, 0, 0] | 2,599 | 3,216 / 3,216 |
| 17 | continuation | 8,882 | reorder_point 8,771 | +1.26% | 1.000 | 0.0 | 192 | 458 | [0, 0, 0] | 2,599 | 3,216 / 3,216 |
| 17 | continuation_landed | 8,882 | reorder_point 8,771 | +1.26% | 1.000 | 0.0 | 192 | 458 | [0, 0, 0] | 2,599 | 3,216 / 3,216 |
| 19 | salvage | 10,315 | reorder_point 9,976 | +3.40% | 1.000 | 0.0 | 449 | 0 | [None, None, None] | 1,797 | 2,230 / 2,230 |
| 19 | continuation | 9,882 | reorder_point 9,772 | +1.13% | 1.000 | 0.0 | 449 | 0 | [None, None, None] | 1,797 | 2,230 / 2,230 |
| 19 | continuation_landed | 9,882 | reorder_point 9,772 | +1.13% | 1.000 | 0.0 | 449 | 0 | [None, None, None] | 1,797 | 2,230 / 2,230 |
| 23 | salvage | 12,265 | reorder_point 12,019 | +2.05% | 1.000 | 0.0 | 350 | 0 | [None, None, None] | 1,400 | 1,737 / 1,737 |
| 23 | continuation | 11,928 | reorder_point 11,823 | +0.89% | 1.000 | 0.0 | 350 | 0 | [None, None, None] | 1,400 | 1,737 / 1,737 |
| 23 | continuation_landed | 11,928 | reorder_point 11,823 | +0.89% | 1.000 | 0.0 | 350 | 0 | [None, None, None] | 1,400 | 1,737 / 1,737 |
| 35 | salvage | 18,384 | reorder_point 18,048 | +1.86% | 0.999 | 2.4 | 265 | 133 | [0, None, None] | 1,594 | 1,981 / 1,981 |
| 35 | continuation | 17,997 | reorder_point 17,850 | +0.82% | 0.999 | 2.4 | 265 | 133 | [0, None, None] | 1,594 | 1,981 / 1,981 |
| 35 | continuation_landed | 17,997 | reorder_point 17,850 | +0.82% | 0.999 | 2.4 | 265 | 133 | [0, None, None] | 1,594 | 1,981 / 1,981 |
| 47 | salvage | 24,525 | reorder_point 24,077 | +1.86% | 0.999 | 2.4 | 497 | 0 | [None, None, None] | 1,989 | 2,469 / 2,469 |
| 47 | continuation | 24,045 | reorder_point 23,876 | +0.71% | 0.999 | 2.4 | 497 | 0 | [None, None, None] | 1,989 | 2,469 / 2,469 |
| 47 | continuation_landed | 24,045 | reorder_point 23,876 | +0.71% | 0.999 | 2.4 | 497 | 0 | [None, None, None] | 1,989 | 2,469 / 2,469 |
| 52 | salvage | 26,997 | reorder_point 26,911 | +0.32% | 1.000 | 2.4 | 327 | 132 | [0, None, None] | 1,835 | 2,279 / 2,279 |
| 52 | continuation | 26,553 | reorder_point 26,431 | +0.46% | 1.000 | 2.4 | 327 | 132 | [0, None, None] | 1,835 | 2,279 / 2,279 |
| 52 | continuation_landed | 26,553 | reorder_point 26,431 | +0.46% | 1.000 | 2.4 | 327 | 132 | [0, None, None] | 1,835 | 2,279 / 2,279 |

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
| 35 | salvage | 19,110 | incumbent 19,106 | +0.02% | 1.000 | 1.5 | 132 | 65 | [None, None, 0] | 790 | 984 / 1,043 |
| 35 | continuation | 18,915 | incumbent 18,915 | +0.00% | 1.000 | 1.5 | 132 | 65 | [None, None, 0] | 790 | 984 / 1,043 |
| 35 | continuation_landed | 18,856 | incumbent 18,856 | -0.00% | 1.000 | 1.5 | 132 | 65 | [None, None, 0] | 790 | 984 / 1,043 |
| 47 | salvage | 25,480 | incumbent 25,484 | -0.02% | 1.000 | 2.2 | 136 | 65 | [None, None, 0] | 806 | 1,004 / 1,065 |
| 47 | continuation | 25,282 | incumbent 25,285 | -0.01% | 1.000 | 2.2 | 136 | 65 | [None, None, 0] | 806 | 1,004 / 1,065 |
| 47 | continuation_landed | 25,221 | incumbent 25,224 | -0.01% | 1.000 | 2.2 | 136 | 65 | [None, None, 0] | 806 | 1,004 / 1,065 |
| 52 | salvage | 28,109 | incumbent 28,199 | -0.32% | 1.000 | 2.2 | 100 | 64 | [None, None, 0] | 658 | 820 / 869 |
| 52 | continuation | 27,948 | incumbent 27,971 | -0.08% | 1.000 | 2.2 | 100 | 64 | [None, None, 0] | 658 | 820 / 869 |
| 52 | continuation_landed | 27,898 | incumbent 27,901 | -0.01% | 1.000 | 2.2 | 100 | 64 | [None, None, 0] | 658 | 820 / 869 |

### F_mov_two_skus (valid to W = 52; legacy 12-week: salvage +0.24%, continuation +0.28%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 12,437 | periodic:2 11,766 | +5.69% | 0.998 | 3.5 | 735 | 262 | [0, None, 0] | 3,990 | 4,935 / 4,935 |
| 11 | continuation | 11,491 | periodic:2 11,311 | +1.60% | 0.998 | 3.5 | 735 | 262 | [0, None, 0] | 3,990 | 4,935 / 4,935 |
| 11 | continuation_landed | 11,491 | periodic:2 11,311 | +1.60% | 0.998 | 3.5 | 735 | 262 | [0, None, 0] | 3,990 | 4,935 / 4,935 |
| 13 | salvage | 14,636 | periodic:2 13,812 | +5.97% | 0.999 | 3.5 | 728 | 396 | [0, 0, 0] | 4,496 | 5,566 / 5,566 |
| 13 | continuation | 13,566 | periodic:2 13,360 | +1.54% | 0.999 | 3.5 | 728 | 396 | [0, 0, 0] | 4,496 | 5,566 / 5,566 |
| 13 | continuation_landed | 13,566 | periodic:2 13,360 | +1.54% | 0.999 | 3.5 | 728 | 396 | [0, 0, 0] | 4,496 | 5,566 / 5,566 |
| 15 | salvage | 16,527 | periodic:2 15,828 | +4.42% | 0.999 | 3.5 | 728 | 263 | [None, 0, 0] | 3,962 | 4,912 / 4,912 |
| 15 | continuation | 15,577 | periodic:2 15,380 | +1.28% | 0.999 | 3.5 | 728 | 263 | [None, 0, 0] | 3,962 | 4,912 / 4,912 |
| 15 | continuation_landed | 15,577 | periodic:2 15,380 | +1.28% | 0.999 | 3.5 | 728 | 263 | [None, 0, 0] | 3,962 | 4,912 / 4,912 |
| 17 | salvage | 18,615 | periodic:2 17,878 | +4.12% | 0.999 | 3.5 | 857 | 133 | [None, None, 0] | 3,960 | 4,908 / 4,908 |
| 17 | continuation | 17,667 | periodic:2 17,437 | +1.32% | 0.999 | 3.5 | 857 | 133 | [None, None, 0] | 3,960 | 4,908 / 4,908 |
| 17 | continuation_landed | 17,667 | periodic:2 17,437 | +1.32% | 0.999 | 3.5 | 857 | 133 | [None, None, 0] | 3,960 | 4,908 / 4,908 |
| 19 | salvage | 20,363 | periodic:2 19,910 | +2.27% | 0.999 | 3.5 | 593 | 132 | [0, None, None] | 2,899 | 3,592 / 3,592 |
| 19 | continuation | 19,669 | periodic:2 19,470 | +1.02% | 0.999 | 3.5 | 593 | 132 | [0, None, None] | 2,899 | 3,592 / 3,592 |
| 19 | continuation_landed | 19,669 | periodic:2 19,470 | +1.02% | 0.999 | 3.5 | 593 | 132 | [0, None, None] | 2,899 | 3,592 / 3,592 |
| 23 | salvage | 24,764 | periodic:2 24,003 | +3.17% | 0.999 | 3.5 | 853 | 131 | [None, None, 0] | 3,936 | 4,882 / 4,882 |
| 23 | continuation | 23,819 | periodic:2 23,555 | +1.12% | 0.999 | 3.5 | 853 | 131 | [None, None, 0] | 3,936 | 4,882 / 4,882 |
| 23 | continuation_landed | 23,819 | periodic:2 23,555 | +1.12% | 0.999 | 3.5 | 853 | 131 | [None, None, 0] | 3,936 | 4,882 / 4,882 |
| 35 | salvage | 36,463 | periodic:2 36,021 | +1.23% | 0.999 | 3.5 | 657 | 0 | [None, None, None] | 2,630 | 3,271 / 3,271 |
| 35 | continuation | 35,822 | periodic:2 35,555 | +0.75% | 0.999 | 3.5 | 657 | 0 | [None, None, None] | 2,630 | 3,271 / 3,271 |
| 35 | continuation_landed | 35,822 | periodic:2 35,555 | +0.75% | 0.999 | 3.5 | 657 | 0 | [None, None, None] | 2,630 | 3,271 / 3,271 |
| 47 | salvage | 48,676 | periodic:2 48,127 | +1.14% | 1.000 | 3.5 | 733 | 0 | [None, None, None] | 2,932 | 3,644 / 3,644 |
| 47 | continuation | 47,965 | periodic:2 47,664 | +0.63% | 1.000 | 3.5 | 733 | 0 | [None, None, None] | 2,932 | 3,644 / 3,644 |
| 47 | continuation_landed | 47,965 | periodic:2 47,664 | +0.63% | 1.000 | 3.5 | 733 | 0 | [None, None, None] | 2,932 | 3,644 / 3,644 |
| 52 | salvage | 53,891 | periodic:2 52,929 | +1.82% | 1.000 | 3.5 | 726 | 172 | [None, 0, None] | 3,591 | 4,458 / 4,458 |
| 52 | continuation | 53,024 | periodic:2 52,657 | +0.70% | 1.000 | 3.5 | 726 | 172 | [None, 0, None] | 3,591 | 4,458 / 4,458 |
| 52 | continuation_landed | 53,024 | periodic:2 52,657 | +0.70% | 1.000 | 3.5 | 726 | 172 | [None, 0, None] | 3,591 | 4,458 / 4,458 |

### G_freight_tiers (valid to W = 52; legacy 12-week: salvage -10.01%, continuation -0.41%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 17,795 | economic_lot 16,720 | +6.43% | 1.000 | 0.0 | 1124 | 1293 | [0, None, 0] | 9,668 | 11,846 / 13,895 |
| 11 | continuation | 15,617 | economic_lot 14,837 | +5.25% | 1.000 | 0.0 | 1124 | 1293 | [0, None, 0] | 9,668 | 11,846 / 13,895 |
| 11 | continuation_landed | 13,568 | economic_lot 13,211 | +2.71% | 1.000 | 0.0 | 1124 | 1293 | [0, None, 0] | 9,668 | 11,846 / 13,895 |
| 13 | salvage | 19,461 | economic_lot 18,375 | +5.91% | 1.000 | 0.0 | 2016 | 0 | [None, None, None] | 8,063 | 9,910 / 11,621 |
| 13 | continuation | 17,614 | economic_lot 16,838 | +4.61% | 1.000 | 0.0 | 2016 | 0 | [None, None, None] | 8,063 | 9,910 / 11,621 |
| 13 | continuation_landed | 15,903 | economic_lot 15,532 | +2.39% | 1.000 | 0.0 | 2016 | 0 | [None, None, None] | 8,063 | 9,910 / 11,621 |
| 15 | salvage | 21,095 | economic_lot 19,998 | +5.49% | 1.000 | 0.0 | 1620 | 0 | [None, None, None] | 6,478 | 7,977 / 9,353 |
| 15 | continuation | 19,596 | economic_lot 18,818 | +4.14% | 1.000 | 0.0 | 1620 | 0 | [None, None, None] | 6,478 | 7,977 / 9,353 |
| 15 | continuation_landed | 18,220 | economic_lot 17,829 | +2.19% | 1.000 | 0.0 | 1620 | 0 | [None, None, None] | 6,478 | 7,977 / 9,353 |
| 17 | salvage | 22,734 | economic_lot 21,625 | +5.13% | 1.000 | 0.0 | 1219 | 0 | [None, None, None] | 4,878 | 6,014 / 7,053 |
| 17 | continuation | 21,598 | economic_lot 20,816 | +3.76% | 1.000 | 0.0 | 1219 | 0 | [None, None, None] | 4,878 | 6,014 / 7,053 |
| 17 | continuation_landed | 20,558 | economic_lot 20,147 | +2.04% | 1.000 | 0.0 | 1219 | 0 | [None, None, None] | 4,878 | 6,014 / 7,053 |
| 19 | salvage | 25,583 | economic_lot 23,231 | +10.12% | 1.000 | 0.0 | 1483 | 0 | [None, None, None] | 5,931 | 7,310 / 8,564 |
| 19 | continuation | 24,204 | economic_lot 22,800 | +6.16% | 1.000 | 0.0 | 1483 | 0 | [None, None, None] | 5,931 | 7,310 / 8,564 |
| 19 | continuation_landed | 22,950 | economic_lot 22,449 | +2.23% | 1.000 | 0.0 | 1483 | 0 | [None, None, None] | 5,931 | 7,310 / 8,564 |
| 23 | salvage | 30,868 | economic_lot 30,982 | -0.37% | 1.000 | 0.0 | 1332 | 70 | [None, None, 0] | 5,608 | 6,938 / 8,258 |
| 23 | continuation | 29,537 | economic_lot 29,370 | +0.57% | 1.000 | 0.0 | 1332 | 70 | [None, None, 0] | 5,608 | 6,938 / 8,258 |
| 23 | continuation_landed | 28,218 | economic_lot 27,867 | +1.26% | 1.000 | 0.0 | 1332 | 70 | [None, None, 0] | 5,608 | 6,938 / 8,258 |
| 35 | salvage | 44,188 | economic_lot 45,568 | -3.03% | 1.000 | 0.0 | 949 | 0 | [None, None, None] | 3,797 | 4,713 / 5,582 |
| 35 | continuation | 43,272 | economic_lot 44,103 | -1.88% | 1.000 | 0.0 | 949 | 0 | [None, None, None] | 3,797 | 4,713 / 5,582 |
| 35 | continuation_landed | 42,403 | economic_lot 42,583 | -0.42% | 1.000 | 0.0 | 949 | 0 | [None, None, None] | 3,797 | 4,713 / 5,582 |
| 47 | salvage | 59,812 | economic_lot 60,213 | -0.66% | 1.000 | 0.0 | 600 | 606 | [0, None, None] | 4,822 | 5,954 / 7,091 |
| 47 | continuation | 58,681 | economic_lot 58,896 | -0.37% | 1.000 | 0.0 | 600 | 606 | [0, None, None] | 4,822 | 5,954 / 7,091 |
| 47 | continuation_landed | 57,543 | economic_lot 57,487 | +0.10% | 1.000 | 0.0 | 600 | 606 | [0, None, None] | 4,822 | 5,954 / 7,091 |
| 52 | salvage | 66,689 | economic_lot 65,440 | +1.91% | 1.000 | 0.0 | 1557 | 0 | [None, None, None] | 6,228 | 7,694 / 9,203 |
| 52 | continuation | 65,223 | economic_lot 64,438 | +1.22% | 1.000 | 0.0 | 1557 | 0 | [None, None, None] | 6,228 | 7,694 / 9,203 |
| 52 | continuation_landed | 63,714 | economic_lot 63,421 | +0.46% | 1.000 | 0.0 | 1557 | 0 | [None, None, None] | 6,228 | 7,694 / 9,203 |

### H_per_pallet_freight (valid to W = 52; legacy 12-week: salvage -3.73%, continuation -2.29%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,658 | periodic:2 6,826 | -2.47% | 1.000 | 0.0 | 249 | 0 | [None, None, None] | 998 | 1,242 / 1,392 |
| 11 | continuation | 6,414 | periodic:2 6,610 | -2.97% | 1.000 | 0.0 | 249 | 0 | [None, None, None] | 998 | 1,242 / 1,392 |
| 11 | continuation_landed | 6,263 | periodic:2 6,448 | -2.86% | 1.000 | 0.0 | 249 | 0 | [None, None, None] | 998 | 1,242 / 1,392 |
| 13 | salvage | 7,682 | periodic:2 8,027 | -4.30% | 1.000 | 0.0 | 112 | 51 | [0, None, 0] | 651 | 811 / 910 |
| 13 | continuation | 7,521 | periodic:2 7,810 | -3.69% | 1.000 | 0.0 | 112 | 51 | [0, None, 0] | 651 | 811 / 910 |
| 13 | continuation_landed | 7,422 | periodic:2 7,645 | -2.92% | 1.000 | 0.0 | 112 | 51 | [0, None, 0] | 651 | 811 / 910 |
| 15 | salvage | 8,787 | periodic:2 9,162 | -4.09% | 1.000 | 0.0 | 35 | 98 | [0, 0, 0] | 532 | 663 / 747 |
| 15 | continuation | 8,656 | periodic:2 8,951 | -3.30% | 1.000 | 0.0 | 35 | 98 | [0, 0, 0] | 532 | 663 / 747 |
| 15 | continuation_landed | 8,572 | periodic:2 8,791 | -2.50% | 1.000 | 0.0 | 35 | 98 | [0, 0, 0] | 532 | 663 / 747 |
| 17 | salvage | 9,971 | periodic:2 10,293 | -3.13% | 1.000 | 0.0 | 67 | 84 | [0, 0, None] | 605 | 755 / 852 |
| 17 | continuation | 9,821 | periodic:2 10,093 | -2.69% | 1.000 | 0.0 | 67 | 84 | [0, 0, None] | 605 | 755 / 852 |
| 17 | continuation_landed | 9,724 | periodic:2 9,942 | -2.19% | 1.000 | 0.0 | 67 | 84 | [0, 0, None] | 605 | 755 / 852 |
| 19 | salvage | 11,175 | periodic:2 11,559 | -3.32% | 0.998 | 4.6 | 85 | 67 | [None, 0, 0] | 608 | 759 / 858 |
| 19 | continuation | 11,024 | periodic:2 11,343 | -2.81% | 0.998 | 4.6 | 85 | 67 | [None, 0, 0] | 608 | 759 / 858 |
| 19 | continuation_landed | 10,925 | periodic:2 11,179 | -2.28% | 0.998 | 4.6 | 85 | 67 | [None, 0, 0] | 608 | 759 / 858 |
| 23 | salvage | 13,571 | periodic:2 13,931 | -2.58% | 0.998 | 4.6 | 143 | 64 | [0, 0, None] | 829 | 1,033 / 1,166 |
| 23 | continuation | 13,367 | periodic:2 13,709 | -2.49% | 0.998 | 4.6 | 143 | 64 | [0, 0, None] | 829 | 1,033 / 1,166 |
| 23 | continuation_landed | 13,235 | periodic:2 13,540 | -2.25% | 0.998 | 4.6 | 143 | 64 | [0, 0, None] | 829 | 1,033 / 1,166 |
| 35 | salvage | 20,653 | periodic:2 20,838 | -0.89% | 0.998 | 8.1 | 120 | 214 | [0, None, 0] | 1,337 | 1,663 / 1,880 |
| 35 | continuation | 20,327 | periodic:2 20,622 | -1.43% | 0.998 | 8.1 | 120 | 214 | [0, None, 0] | 1,337 | 1,663 / 1,880 |
| 35 | continuation_landed | 20,110 | periodic:2 20,460 | -1.71% | 0.998 | 8.1 | 120 | 214 | [0, None, 0] | 1,337 | 1,663 / 1,880 |
| 47 | salvage | 27,497 | periodic:2 27,796 | -1.08% | 0.997 | 14.7 | 291 | 59 | [0, 0, None] | 1,399 | 1,738 / 1,964 |
| 47 | continuation | 27,158 | periodic:2 27,578 | -1.52% | 0.997 | 14.7 | 291 | 59 | [0, 0, None] | 1,399 | 1,738 / 1,964 |
| 47 | continuation_landed | 26,931 | periodic:2 27,413 | -1.76% | 0.997 | 14.7 | 291 | 59 | [0, 0, None] | 1,399 | 1,738 / 1,964 |
| 52 | salvage | 29,950 | periodic:2 30,455 | -1.66% | 0.997 | 14.7 | 10 | 97 | [0, 0, 0] | 432 | 539 / 610 |
| 52 | continuation | 29,843 | periodic:2 30,353 | -1.68% | 0.997 | 14.7 | 10 | 97 | [0, 0, 0] | 432 | 539 / 610 |
| 52 | continuation_landed | 29,772 | periodic:2 30,277 | -1.67% | 0.997 | 14.7 | 10 | 97 | [0, 0, 0] | 432 | 539 / 610 |

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
| 35 | salvage | 28,102 | economic_lot 28,093 | +0.03% | 1.000 | 1.1 | 199 | 0 | [None, None, None] | 797 | 993 / 1,547 |
| 35 | continuation | 27,906 | economic_lot 27,903 | +0.01% | 1.000 | 1.1 | 199 | 0 | [None, None, None] | 797 | 993 / 1,547 |
| 35 | continuation_landed | 27,353 | economic_lot 27,367 | -0.05% | 1.000 | 1.1 | 199 | 0 | [None, None, None] | 797 | 993 / 1,547 |
| 47 | salvage | 38,366 | economic_lot 38,052 | +0.83% | 1.000 | 1.1 | 356 | 0 | [None, None, None] | 1,422 | 1,768 / 2,780 |
| 47 | continuation | 38,020 | economic_lot 37,721 | +0.79% | 1.000 | 1.1 | 356 | 0 | [None, None, None] | 1,422 | 1,768 / 2,780 |
| 47 | continuation_landed | 37,008 | economic_lot 36,778 | +0.63% | 1.000 | 1.1 | 356 | 0 | [None, None, None] | 1,422 | 1,768 / 2,780 |
| 52 | salvage | 42,072 | economic_lot 41,758 | +0.75% | 1.000 | 1.1 | 309 | 0 | [None, None, None] | 1,235 | 1,536 / 2,412 |
| 52 | continuation | 41,771 | economic_lot 41,472 | +0.72% | 1.000 | 1.1 | 309 | 0 | [None, None, None] | 1,235 | 1,536 / 2,412 |
| 52 | continuation_landed | 40,895 | economic_lot 40,662 | +0.57% | 1.000 | 1.1 | 309 | 0 | [None, None, None] | 1,235 | 1,536 / 2,412 |

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
| 11 | salvage | 6,108 | incumbent 6,039 | +1.14% | 0.982 | 19.6 | 24 | 293 | [0, 0, 0] | 1,265 | 1,575 / 1,575 |
| 11 | continuation | 5,799 | incumbent 5,723 | +1.33% | 0.982 | 19.6 | 24 | 293 | [0, 0, 0] | 1,265 | 1,575 / 1,575 |
| 11 | continuation_landed | 5,799 | incumbent 5,723 | +1.33% | 0.982 | 19.6 | 24 | 293 | [0, 0, 0] | 1,265 | 1,575 / 1,575 |
| 13 | salvage | 7,177 | incumbent 7,099 | +1.09% | 0.983 | 22.3 | 28 | 299 | [0, 0, 0] | 1,309 | 1,628 / 1,628 |
| 13 | continuation | 6,857 | incumbent 6,780 | +1.14% | 0.983 | 22.3 | 28 | 299 | [0, 0, 0] | 1,309 | 1,628 / 1,628 |
| 13 | continuation_landed | 6,857 | incumbent 6,780 | +1.14% | 0.983 | 22.3 | 28 | 299 | [0, 0, 0] | 1,309 | 1,628 / 1,628 |
| 15 | salvage | 8,161 | incumbent 8,091 | +0.87% | 0.985 | 22.3 | 24 | 289 | [0, 0, 0] | 1,253 | 1,559 / 1,559 |
| 15 | continuation | 7,855 | incumbent 7,779 | +0.98% | 0.985 | 22.3 | 24 | 289 | [0, 0, 0] | 1,253 | 1,559 / 1,559 |
| 15 | continuation_landed | 7,855 | incumbent 7,779 | +0.98% | 0.985 | 22.3 | 24 | 289 | [0, 0, 0] | 1,253 | 1,559 / 1,559 |
| 17 | salvage | 9,154 | incumbent 9,076 | +0.86% | 0.987 | 22.3 | 27 | 277 | [0, 0, 0] | 1,220 | 1,518 / 1,518 |
| 17 | continuation | 8,856 | incumbent 8,778 | +0.89% | 0.987 | 22.3 | 27 | 277 | [0, 0, 0] | 1,220 | 1,518 / 1,518 |
| 17 | continuation_landed | 8,856 | incumbent 8,778 | +0.89% | 0.987 | 22.3 | 27 | 277 | [0, 0, 0] | 1,220 | 1,518 / 1,518 |
| 19 | salvage | 10,291 | incumbent 10,140 | +1.49% | 0.982 | 33.3 | 25 | 303 | [0, 0, 0] | 1,314 | 1,635 / 1,635 |
| 19 | continuation | 9,971 | incumbent 9,829 | +1.44% | 0.982 | 33.3 | 25 | 303 | [0, 0, 0] | 1,314 | 1,635 / 1,635 |
| 19 | continuation_landed | 9,971 | incumbent 9,829 | +1.44% | 0.982 | 33.3 | 25 | 303 | [0, 0, 0] | 1,314 | 1,635 / 1,635 |
| 23 | salvage | 12,357 | incumbent 12,257 | +0.81% | 0.984 | 35.9 | 21 | 307 | [0, 0, 0] | 1,313 | 1,633 / 1,633 |
| 23 | continuation | 12,036 | incumbent 11,930 | +0.89% | 0.984 | 35.9 | 21 | 307 | [0, 0, 0] | 1,313 | 1,633 / 1,633 |
| 23 | continuation_landed | 12,036 | incumbent 11,930 | +0.89% | 0.984 | 35.9 | 21 | 307 | [0, 0, 0] | 1,313 | 1,633 / 1,633 |
| 35 | salvage | 18,409 | incumbent 18,298 | +0.61% | 0.988 | 42.9 | 40 | 278 | [0, 0, 0] | 1,269 | 1,579 / 1,579 |
| 35 | continuation | 18,099 | incumbent 17,979 | +0.67% | 0.988 | 42.9 | 40 | 278 | [0, 0, 0] | 1,269 | 1,579 / 1,579 |
| 35 | continuation_landed | 18,099 | incumbent 17,979 | +0.67% | 0.988 | 42.9 | 40 | 278 | [0, 0, 0] | 1,269 | 1,579 / 1,579 |
| 47 | salvage | 24,457 | incumbent 24,302 | +0.64% | 0.989 | 52.6 | 67 | 253 | [0, 0, 0] | 1,280 | 1,593 / 1,593 |
| 47 | continuation | 24,145 | incumbent 23,983 | +0.67% | 0.989 | 52.6 | 67 | 253 | [0, 0, 0] | 1,280 | 1,593 / 1,593 |
| 47 | continuation_landed | 24,145 | incumbent 23,983 | +0.67% | 0.989 | 52.6 | 67 | 253 | [0, 0, 0] | 1,280 | 1,593 / 1,593 |
| 52 | salvage | 26,939 | incumbent 26,791 | +0.55% | 0.990 | 52.6 | 17 | 280 | [0, 0, 0] | 1,190 | 1,481 / 1,481 |
| 52 | continuation | 26,648 | incumbent 26,488 | +0.61% | 0.990 | 52.6 | 17 | 280 | [0, 0, 0] | 1,190 | 1,481 / 1,481 |
| 52 | continuation_landed | 26,648 | incumbent 26,488 | +0.61% | 0.990 | 52.6 | 17 | 280 | [0, 0, 0] | 1,190 | 1,481 / 1,481 |

### O_low_opening_stock (valid to W = 52; legacy 12-week: salvage +0.46%, continuation +0.44%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,457 | reorder_point 6,399 | +0.91% | 0.924 | 83.9 | 101 | 68 | [0, None, 0] | 674 | 840 / 840 |
| 11 | continuation | 6,291 | reorder_point 6,285 | +0.10% | 0.924 | 83.9 | 101 | 68 | [0, None, 0] | 674 | 840 / 840 |
| 11 | continuation_landed | 6,291 | reorder_point 6,285 | +0.10% | 0.924 | 83.9 | 101 | 68 | [0, None, 0] | 674 | 840 / 840 |
| 13 | salvage | 7,443 | reorder_point 7,449 | -0.08% | 0.936 | 83.9 | 28 | 93 | [0, 0, 0] | 484 | 604 / 604 |
| 13 | continuation | 7,323 | reorder_point 7,332 | -0.13% | 0.936 | 83.9 | 28 | 93 | [0, 0, 0] | 484 | 604 / 604 |
| 13 | continuation_landed | 7,323 | reorder_point 7,332 | -0.13% | 0.936 | 83.9 | 28 | 93 | [0, 0, 0] | 484 | 604 / 604 |
| 15 | salvage | 8,438 | reorder_point 8,445 | -0.09% | 0.944 | 83.9 | 20 | 97 | [0, 0, 0] | 466 | 582 / 582 |
| 15 | continuation | 8,322 | reorder_point 8,332 | -0.12% | 0.944 | 83.9 | 20 | 97 | [0, 0, 0] | 466 | 582 / 582 |
| 15 | continuation_landed | 8,322 | reorder_point 8,332 | -0.12% | 0.944 | 83.9 | 20 | 97 | [0, 0, 0] | 466 | 582 / 582 |
| 17 | salvage | 9,473 | reorder_point 9,436 | +0.39% | 0.951 | 83.9 | 82 | 63 | [0, 0, None] | 578 | 721 / 721 |
| 17 | continuation | 9,330 | reorder_point 9,332 | -0.02% | 0.951 | 83.9 | 82 | 63 | [0, 0, None] | 578 | 721 / 721 |
| 17 | continuation_landed | 9,330 | reorder_point 9,332 | -0.02% | 0.951 | 83.9 | 82 | 63 | [0, 0, None] | 578 | 721 / 721 |
| 19 | salvage | 10,536 | reorder_point 10,509 | +0.25% | 0.954 | 87.8 | 45 | 105 | [0, 0, 0] | 599 | 747 / 747 |
| 19 | continuation | 10,387 | reorder_point 10,396 | -0.08% | 0.954 | 87.8 | 45 | 105 | [0, 0, 0] | 599 | 747 / 747 |
| 19 | continuation_landed | 10,387 | reorder_point 10,396 | -0.08% | 0.954 | 87.8 | 45 | 105 | [0, 0, 0] | 599 | 747 / 747 |
| 23 | salvage | 12,609 | reorder_point 12,568 | +0.32% | 0.961 | 90.6 | 93 | 60 | [0, 0, None] | 612 | 763 / 763 |
| 23 | continuation | 12,458 | reorder_point 12,449 | +0.07% | 0.961 | 90.6 | 93 | 60 | [0, 0, None] | 612 | 763 / 763 |
| 23 | continuation_landed | 12,458 | reorder_point 12,449 | +0.07% | 0.961 | 90.6 | 93 | 60 | [0, 0, None] | 612 | 763 / 763 |
| 35 | salvage | 18,676 | reorder_point 18,608 | +0.37% | 0.972 | 96.1 | 56 | 108 | [0, None, 0] | 654 | 815 / 815 |
| 35 | continuation | 18,515 | reorder_point 18,492 | +0.12% | 0.972 | 96.1 | 56 | 108 | [0, None, 0] | 654 | 815 / 815 |
| 35 | continuation_landed | 18,515 | reorder_point 18,492 | +0.12% | 0.972 | 96.1 | 56 | 108 | [0, None, 0] | 654 | 815 / 815 |
| 47 | salvage | 24,709 | reorder_point 24,621 | +0.36% | 0.977 | 104.9 | 34 | 115 | [0, 0, 0] | 596 | 744 / 744 |
| 47 | continuation | 24,562 | reorder_point 24,502 | +0.24% | 0.977 | 104.9 | 34 | 115 | [0, 0, 0] | 596 | 744 / 744 |
| 47 | continuation_landed | 24,562 | reorder_point 24,502 | +0.24% | 0.977 | 104.9 | 34 | 115 | [0, 0, 0] | 596 | 744 / 744 |
| 52 | salvage | 27,230 | reorder_point 27,114 | +0.43% | 0.980 | 104.9 | 44 | 127 | [0, 0, 0] | 682 | 850 / 850 |
| 52 | continuation | 27,062 | reorder_point 27,006 | +0.21% | 0.980 | 104.9 | 44 | 127 | [0, 0, 0] | 682 | 850 / 850 |
| 52 | continuation_landed | 27,062 | reorder_point 27,006 | +0.21% | 0.980 | 104.9 | 44 | 127 | [0, 0, 0] | 682 | 850 / 850 |

### P_high_opening_stock (valid to W = 52; legacy 12-week: salvage +0.29%, continuation +0.39%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 5,945 | reorder_point 5,786 | +2.74% | 0.997 | 2.9 | 192 | 96 | [0, 0, None] | 1,152 | 1,434 / 1,434 |
| 11 | continuation | 5,663 | reorder_point 5,673 | -0.17% | 0.997 | 2.9 | 192 | 96 | [0, 0, None] | 1,152 | 1,434 / 1,434 |
| 11 | continuation_landed | 5,663 | reorder_point 5,673 | -0.17% | 0.997 | 2.9 | 192 | 96 | [0, 0, None] | 1,152 | 1,434 / 1,434 |
| 13 | salvage | 6,816 | reorder_point 6,837 | -0.31% | 0.998 | 2.9 | 100 | 36 | [None, None, 0] | 543 | 677 / 677 |
| 13 | continuation | 6,681 | reorder_point 6,720 | -0.57% | 0.998 | 2.9 | 100 | 36 | [None, None, 0] | 543 | 677 / 677 |
| 13 | continuation_landed | 6,681 | reorder_point 6,720 | -0.57% | 0.998 | 2.9 | 100 | 36 | [None, None, 0] | 543 | 677 / 677 |
| 15 | salvage | 7,797 | reorder_point 7,833 | -0.46% | 0.998 | 2.9 | 34 | 84 | [0, 0, 0] | 471 | 588 / 588 |
| 15 | continuation | 7,680 | reorder_point 7,720 | -0.52% | 0.998 | 2.9 | 34 | 84 | [0, 0, 0] | 471 | 588 / 588 |
| 15 | continuation_landed | 7,680 | reorder_point 7,720 | -0.52% | 0.998 | 2.9 | 34 | 84 | [0, 0, 0] | 471 | 588 / 588 |
| 17 | salvage | 8,888 | reorder_point 8,823 | +0.74% | 0.996 | 6.9 | 46 | 127 | [0, 0, 0] | 693 | 863 / 863 |
| 17 | continuation | 8,718 | reorder_point 8,719 | -0.02% | 0.996 | 6.9 | 46 | 127 | [0, 0, 0] | 693 | 863 / 863 |
| 17 | continuation_landed | 8,718 | reorder_point 8,719 | -0.02% | 0.996 | 6.9 | 46 | 127 | [0, 0, 0] | 693 | 863 / 863 |
| 19 | salvage | 9,929 | reorder_point 9,896 | +0.33% | 0.994 | 11.9 | 52 | 97 | [0, 0, 0] | 595 | 742 / 742 |
| 19 | continuation | 9,782 | reorder_point 9,783 | -0.01% | 0.994 | 11.9 | 52 | 97 | [0, 0, 0] | 595 | 742 / 742 |
| 19 | continuation_landed | 9,782 | reorder_point 9,783 | -0.01% | 0.994 | 11.9 | 52 | 97 | [0, 0, 0] | 595 | 742 / 742 |
| 23 | salvage | 11,976 | reorder_point 11,956 | +0.17% | 0.993 | 15.1 | 56 | 71 | [None, 0, 0] | 509 | 635 / 635 |
| 23 | continuation | 11,850 | reorder_point 11,836 | +0.11% | 0.993 | 15.1 | 56 | 71 | [None, 0, 0] | 509 | 635 / 635 |
| 23 | continuation_landed | 11,850 | reorder_point 11,836 | +0.11% | 0.993 | 15.1 | 56 | 71 | [None, 0, 0] | 509 | 635 / 635 |
| 35 | salvage | 18,095 | reorder_point 17,995 | +0.55% | 0.992 | 28.4 | 55 | 76 | [0, None, 0] | 527 | 658 / 658 |
| 35 | continuation | 17,964 | reorder_point 17,880 | +0.47% | 0.992 | 28.4 | 55 | 76 | [0, None, 0] | 527 | 658 / 658 |
| 35 | continuation_landed | 17,964 | reorder_point 17,880 | +0.47% | 0.992 | 28.4 | 55 | 76 | [0, None, 0] | 527 | 658 / 658 |
| 47 | salvage | 24,184 | reorder_point 24,008 | +0.73% | 0.993 | 34.3 | 140 | 62 | [0, 0, None] | 807 | 1,005 / 1,005 |
| 47 | continuation | 23,985 | reorder_point 23,889 | +0.40% | 0.993 | 34.3 | 140 | 62 | [0, 0, None] | 807 | 1,005 / 1,005 |
| 47 | continuation_landed | 23,985 | reorder_point 23,889 | +0.40% | 0.993 | 34.3 | 140 | 62 | [0, 0, None] | 807 | 1,005 / 1,005 |
| 52 | salvage | 26,609 | reorder_point 26,502 | +0.41% | 0.993 | 34.3 | 33 | 93 | [0, 0, 0] | 502 | 627 / 627 |
| 52 | continuation | 26,485 | reorder_point 26,394 | +0.35% | 0.993 | 34.3 | 33 | 93 | [0, 0, 0] | 502 | 627 / 627 |
| 52 | continuation_landed | 26,485 | reorder_point 26,394 | +0.35% | 0.993 | 34.3 | 33 | 93 | [0, 0, 0] | 502 | 627 / 627 |

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
| 11 | salvage | 63,873 | incumbent 63,448 | +0.67% | 0.988 | 26.5 | 41 | 180 | [0, 0, 0] | 4,695 | 5,859 / 5,859 |
| 11 | continuation | 62,709 | incumbent 62,284 | +0.68% | 0.988 | 26.5 | 41 | 180 | [0, 0, 0] | 4,695 | 5,859 / 5,859 |
| 11 | continuation_landed | 62,709 | incumbent 62,284 | +0.68% | 0.988 | 26.5 | 41 | 180 | [0, 0, 0] | 4,695 | 5,859 / 5,859 |
| 13 | salvage | 75,179 | incumbent 74,755 | +0.57% | 0.989 | 28.2 | 25 | 211 | [0, 0, 0] | 5,185 | 6,470 / 6,470 |
| 13 | continuation | 73,894 | incumbent 73,470 | +0.58% | 0.989 | 28.2 | 25 | 211 | [0, 0, 0] | 5,185 | 6,470 / 6,470 |
| 13 | continuation_landed | 73,894 | incumbent 73,470 | +0.58% | 0.989 | 28.2 | 25 | 211 | [0, 0, 0] | 5,185 | 6,470 / 6,470 |
| 15 | salvage | 86,466 | incumbent 85,961 | +0.59% | 0.990 | 30.1 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 15 | continuation | 85,211 | incumbent 84,714 | +0.59% | 0.990 | 30.1 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 15 | continuation_landed | 85,211 | incumbent 84,714 | +0.59% | 0.990 | 30.1 | 25 | 205 | [0, 0, 0] | 5,061 | 6,316 / 6,316 |
| 17 | salvage | 97,940 | incumbent 97,463 | +0.49% | 0.991 | 32.3 | 24 | 187 | [0, 0, 0] | 4,682 | 5,843 / 5,843 |
| 17 | continuation | 96,779 | periodic:2 96,239 | +0.56% | 0.991 | 32.3 | 24 | 187 | [0, 0, 0] | 4,682 | 5,843 / 5,843 |
| 17 | continuation_landed | 96,779 | periodic:2 96,239 | +0.56% | 0.991 | 32.3 | 24 | 187 | [0, 0, 0] | 4,682 | 5,843 / 5,843 |
| 19 | salvage | 109,057 | incumbent 108,553 | +0.46% | 0.990 | 37.1 | 24 | 198 | [0, 0, 0] | 4,758 | 5,939 / 5,939 |
| 19 | continuation | 107,877 | periodic:2 107,366 | +0.48% | 0.990 | 37.1 | 24 | 198 | [0, 0, 0] | 4,758 | 5,939 / 5,939 |
| 19 | continuation_landed | 107,877 | periodic:2 107,366 | +0.48% | 0.990 | 37.1 | 24 | 198 | [0, 0, 0] | 4,758 | 5,939 / 5,939 |
| 23 | salvage | 131,458 | incumbent 131,003 | +0.35% | 0.992 | 38.8 | 48 | 178 | [0, 0, 0] | 4,830 | 6,028 / 6,028 |
| 23 | continuation | 130,259 | incumbent 129,760 | +0.38% | 0.992 | 38.8 | 48 | 178 | [0, 0, 0] | 4,830 | 6,028 / 6,028 |
| 23 | continuation_landed | 130,259 | incumbent 129,760 | +0.38% | 0.992 | 38.8 | 48 | 178 | [0, 0, 0] | 4,830 | 6,028 / 6,028 |
| 35 | salvage | 197,430 | incumbent 196,690 | +0.38% | 0.993 | 47.9 | 127 | 168 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 35 | continuation | 196,017 | incumbent 195,436 | +0.30% | 0.993 | 47.9 | 127 | 168 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 35 | continuation_landed | 196,017 | incumbent 195,436 | +0.30% | 0.993 | 47.9 | 127 | 168 | [0, 0, 0] | 5,707 | 7,120 / 7,120 |
| 47 | salvage | 264,346 | incumbent 263,353 | +0.38% | 0.993 | 62.1 | 126 | 170 | [0, 0, 0] | 5,385 | 6,719 / 6,719 |
| 47 | continuation | 263,012 | incumbent 262,077 | +0.36% | 0.993 | 62.1 | 126 | 170 | [0, 0, 0] | 5,385 | 6,719 / 6,719 |
| 47 | continuation_landed | 263,012 | incumbent 262,077 | +0.36% | 0.993 | 62.1 | 126 | 170 | [0, 0, 0] | 5,385 | 6,719 / 6,719 |
| 52 | salvage | 292,340 | incumbent 290,755 | +0.55% | 0.992 | 79.6 | 26 | 194 | [0, 0, 0] | 4,883 | 6,093 / 6,093 |
| 52 | continuation | 291,129 | incumbent 289,535 | +0.55% | 0.992 | 79.6 | 26 | 194 | [0, 0, 0] | 4,883 | 6,093 / 6,093 |
| 52 | continuation_landed | 291,129 | incumbent 289,535 | +0.55% | 0.992 | 79.6 | 26 | 194 | [0, 0, 0] | 4,883 | 6,093 / 6,093 |

### S_cash_constrained (valid to W = 12; legacy 12-week: salvage +0.26%, continuation +3.59%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 6,633 | economic_lot 6,234 | +6.40% | 1.000 | 0.0 | 299 | 37 | [0, None, None] | 1,345 | 1,672 / 1,823 |
| 11 | continuation | 6,306 | economic_lot 5,924 | +6.45% | 1.000 | 0.0 | 299 | 37 | [0, None, None] | 1,345 | 1,672 / 1,823 |
| 11 | continuation_landed | 6,155 | economic_lot 5,875 | +4.77% | 1.000 | 0.0 | 299 | 37 | [0, None, None] | 1,345 | 1,672 / 1,823 |

### T_combined_realistic (valid to W = 52; legacy 12-week: salvage -11.47%, continuation -4.21%)

| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | salvage | 17,235 | economic_lot 17,593 | -2.04% | 0.996 | 9.8 | 1263 | 625 | [None, None, 0] | 7,553 | 9,193 / 11,068 |
| 11 | continuation | 15,595 | economic_lot 15,846 | -1.58% | 0.996 | 9.8 | 1263 | 625 | [None, None, 0] | 7,553 | 9,193 / 11,068 |
| 11 | continuation_landed | 13,720 | economic_lot 13,782 | -0.45% | 0.996 | 9.8 | 1263 | 625 | [None, None, 0] | 7,553 | 9,193 / 11,068 |
| 13 | salvage | 18,895 | economic_lot 19,258 | -1.89% | 0.996 | 9.8 | 1487 | 0 | [None, None, None] | 5,948 | 7,283 / 8,763 |
| 13 | continuation | 17,559 | economic_lot 17,807 | -1.39% | 0.996 | 9.8 | 1487 | 0 | [None, None, None] | 5,948 | 7,283 / 8,763 |
| 13 | continuation_landed | 16,079 | economic_lot 16,143 | -0.40% | 0.996 | 9.8 | 1487 | 0 | [None, None, None] | 5,948 | 7,283 / 8,763 |
| 15 | salvage | 20,526 | economic_lot 20,889 | -1.74% | 0.997 | 9.8 | 1091 | 0 | [None, None, None] | 4,363 | 5,368 / 6,458 |
| 15 | continuation | 19,521 | economic_lot 19,761 | -1.21% | 0.997 | 9.8 | 1091 | 0 | [None, None, None] | 4,363 | 5,368 / 6,458 |
| 15 | continuation_landed | 18,431 | economic_lot 18,492 | -0.33% | 0.997 | 9.8 | 1091 | 0 | [None, None, None] | 4,363 | 5,368 / 6,458 |
| 17 | salvage | 22,167 | economic_lot 22,542 | -1.66% | 0.997 | 9.8 | 691 | 0 | [None, None, None] | 2,763 | 3,414 / 4,110 |
| 17 | continuation | 21,516 | economic_lot 21,760 | -1.12% | 0.997 | 9.8 | 691 | 0 | [None, None, None] | 2,763 | 3,414 / 4,110 |
| 17 | continuation_landed | 20,820 | economic_lot 20,889 | -0.33% | 0.997 | 9.8 | 691 | 0 | [None, None, None] | 2,763 | 3,414 / 4,110 |
| 19 | salvage | 26,321 | economic_lot 25,399 | +3.63% | 0.997 | 9.8 | 916 | 630 | [None, 0, None] | 6,185 | 7,542 / 9,005 |
| 19 | continuation | 24,964 | economic_lot 24,451 | +2.10% | 0.997 | 9.8 | 916 | 630 | [None, 0, None] | 6,185 | 7,542 / 9,005 |
| 19 | continuation_landed | 23,500 | economic_lot 23,412 | +0.38% | 0.997 | 9.8 | 916 | 630 | [None, 0, None] | 6,185 | 7,542 / 9,005 |
| 23 | salvage | 30,962 | economic_lot 31,248 | -0.92% | 0.998 | 9.8 | 980 | 103 | [None, None, 0] | 4,330 | 5,332 / 6,490 |
| 23 | continuation | 29,960 | economic_lot 29,907 | +0.18% | 0.998 | 9.8 | 980 | 103 | [None, None, 0] | 4,330 | 5,332 / 6,490 |
| 23 | continuation_landed | 28,801 | economic_lot 28,428 | +1.31% | 0.998 | 9.8 | 980 | 103 | [None, None, 0] | 4,330 | 5,332 / 6,490 |
| 35 | salvage | 44,793 | economic_lot 44,664 | +0.29% | 0.999 | 9.8 | 714 | 0 | [None, None, None] | 2,858 | 3,538 / 4,318 |
| 35 | continuation | 44,114 | economic_lot 43,725 | +0.89% | 0.999 | 9.8 | 714 | 0 | [None, None, None] | 2,858 | 3,538 / 4,318 |
| 35 | continuation_landed | 43,333 | economic_lot 42,728 | +1.42% | 0.999 | 9.8 | 714 | 0 | [None, None, None] | 2,858 | 3,538 / 4,318 |
| 47 | salvage | 59,624 | economic_lot 59,064 | +0.95% | 0.999 | 9.8 | 397 | 103 | [0, None, None] | 1,999 | 2,482 / 3,037 |
| 47 | continuation | 59,141 | economic_lot 58,221 | +1.58% | 0.999 | 9.8 | 397 | 103 | [0, None, None] | 1,999 | 2,482 / 3,037 |
| 47 | continuation_landed | 58,585 | economic_lot 57,297 | +2.25% | 0.999 | 9.8 | 397 | 103 | [0, None, None] | 1,999 | 2,482 / 3,037 |
| 52 | salvage | 67,905 | economic_lot 66,626 | +1.92% | 0.999 | 9.8 | 1484 | 0 | [None, None, None] | 5,934 | 7,265 / 8,920 |
| 52 | continuation | 66,574 | economic_lot 65,196 | +2.11% | 0.999 | 9.8 | 1484 | 0 | [None, None, None] | 5,934 | 7,265 / 8,920 |
| 52 | continuation_landed | 64,919 | economic_lot 63,612 | +2.06% | 0.999 | 9.8 | 1484 | 0 | [None, None, None] | 5,934 | 7,265 / 8,920 |

## Stage 4: convergence classification (section 5), both rules

| fixture | valid at 52 | rule | delta @11 (rolling) | @23 | @35 | @47 | @52 | max |delta(W)-delta(52)| over 40..52 | stable | class |
|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | salvage | +1.48% | +0.89% | +1.10% | +0.89% | +0.81% | 0.26 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation | +1.46% | +0.93% | +1.05% | +0.90% | +0.81% | 0.22 pp | yes | A. STABLE PASS |
| A_no_terms_good_incumbent | yes | continuation_landed | +1.46% | +0.93% | +1.05% | +0.90% | +0.81% | 0.22 pp | yes | A. STABLE PASS |
| B_fixed_order_cost_replace_sold | yes | salvage | +5.77% | -3.15% | +7.14% | +2.27% | +3.69% | 5.67 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation | +6.52% | +1.14% | +4.14% | +2.83% | +3.06% | 1.93 pp | NO | E. NON-CONVERGENT |
| B_fixed_order_cost_replace_sold | yes | continuation_landed | +3.41% | +0.83% | +2.78% | +2.30% | +2.49% | 1.44 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | salvage | +9.11% | +2.05% | +1.86% | +1.86% | +0.32% | 1.56 pp | NO | E. NON-CONVERGENT |
| C_moq_four_weeks | yes | continuation | +2.31% | +0.89% | +0.82% | +0.71% | +0.46% | 0.29 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| C_moq_four_weeks | yes | continuation_landed | +2.31% | +0.89% | +0.82% | +0.71% | +0.46% | 0.29 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| D_case_multiple | yes | salvage | -0.52% | +0.57% | +0.82% | +0.64% | +0.57% | 0.26 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation | +0.23% | +0.73% | +0.95% | +0.73% | +0.66% | 0.18 pp | yes | A. STABLE PASS |
| D_case_multiple | yes | continuation_landed | +0.23% | +0.73% | +0.95% | +0.73% | +0.66% | 0.18 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | salvage | +0.00% | +0.02% | +0.02% | -0.02% | -0.32% | 0.34 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation | +0.00% | -0.00% | +0.00% | -0.01% | -0.08% | 0.09 pp | yes | A. STABLE PASS |
| E_pallet_multiple | yes | continuation_landed | +0.00% | -0.01% | -0.00% | -0.01% | -0.01% | 0.08 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | salvage | +5.69% | +3.17% | +1.23% | +1.14% | +1.82% | 0.24 pp | NO | E. NON-CONVERGENT |
| F_mov_two_skus | yes | continuation | +1.60% | +1.12% | +0.75% | +0.63% | +0.70% | 0.15 pp | yes | A. STABLE PASS |
| F_mov_two_skus | yes | continuation_landed | +1.60% | +1.12% | +0.75% | +0.63% | +0.70% | 0.15 pp | yes | A. STABLE PASS |
| G_freight_tiers | yes | salvage | +6.43% | -0.37% | -3.03% | -0.66% | +1.91% | 1.66 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation | +5.25% | +0.57% | -1.88% | -0.37% | +1.22% | 2.12 pp | NO | E. NON-CONVERGENT |
| G_freight_tiers | yes | continuation_landed | +2.71% | +1.26% | -0.42% | +0.10% | +0.46% | 0.88 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| H_per_pallet_freight | yes | salvage | -2.47% | -2.58% | -0.89% | -1.08% | -1.66% | 1.40 pp | NO | E. NON-CONVERGENT |
| H_per_pallet_freight | yes | continuation | -2.97% | -2.49% | -1.43% | -1.52% | -1.68% | 0.54 pp | yes | A. STABLE PASS |
| H_per_pallet_freight | yes | continuation_landed | -2.86% | -2.25% | -1.71% | -1.76% | -1.67% | 0.17 pp | yes | A. STABLE PASS |
| I_max_pallets_ftl_cap | yes | salvage | +5.78% | +0.02% | +0.03% | +0.83% | +0.75% | 1.41 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation | +4.56% | -0.01% | +0.01% | +0.79% | +0.72% | 1.09 pp | NO | E. NON-CONVERGENT |
| I_max_pallets_ftl_cap | yes | continuation_landed | +0.16% | -0.09% | -0.05% | +0.63% | +0.57% | 0.14 pp | yes | A. STABLE PASS |
| J_net60_cost_of_capital | yes | salvage | +5.60% | +0.01% | +0.13% | -0.15% | +1.30% | 1.18 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation | +1.63% | -0.13% | +0.01% | -0.15% | +0.33% | 1.03 pp | NO | E. NON-CONVERGENT |
| J_net60_cost_of_capital | yes | continuation_landed | +0.88% | -0.15% | -0.01% | -0.14% | +0.15% | 0.65 pp | yes | A. STABLE PASS |
| K_deposit_early_cash | yes | salvage | +5.59% | +0.01% | +0.13% | -0.15% | +1.30% | 1.17 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation | +1.69% | -0.13% | +0.01% | -0.15% | +0.32% | 1.05 pp | NO | E. NON-CONVERGENT |
| K_deposit_early_cash | yes | continuation_landed | +0.94% | -0.15% | -0.01% | -0.15% | +0.15% | 0.67 pp | yes | A. STABLE PASS |
| L_high_holding_rate | yes | salvage | +4.93% | +3.90% | +2.93% | +2.83% | -0.11% | 2.96 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation | +1.80% | +2.88% | +1.90% | +1.69% | +0.72% | 1.01 pp | NO | E. NON-CONVERGENT |
| L_high_holding_rate | yes | continuation_landed | +1.30% | +2.04% | +1.45% | +1.35% | +0.81% | 0.60 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | salvage | +2.42% | +0.59% | +0.30% | +0.12% | +0.09% | 0.39 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| M_order_calendar_wednesday | yes | continuation | +0.96% | +0.05% | -0.09% | -0.19% | -0.17% | 0.11 pp | yes | A. STABLE PASS |
| M_order_calendar_wednesday | yes | continuation_landed | +0.96% | +0.05% | -0.09% | -0.19% | -0.17% | 0.11 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | salvage | +1.14% | +0.81% | +0.61% | +0.64% | +0.55% | 0.20 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation | +1.33% | +0.89% | +0.67% | +0.67% | +0.61% | 0.13 pp | yes | A. STABLE PASS |
| N_long_lead_21_days | yes | continuation_landed | +1.33% | +0.89% | +0.67% | +0.67% | +0.61% | 0.13 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | salvage | +0.91% | +0.32% | +0.37% | +0.36% | +0.43% | 0.19 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation | +0.10% | +0.07% | +0.12% | +0.24% | +0.21% | 0.08 pp | yes | A. STABLE PASS |
| O_low_opening_stock | yes | continuation_landed | +0.10% | +0.07% | +0.12% | +0.24% | +0.21% | 0.08 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | salvage | +2.74% | +0.17% | +0.55% | +0.73% | +0.41% | 0.58 pp | yes | C. BOUNDARY-SENSITIVE -> PASS |
| P_high_opening_stock | yes | continuation | -0.17% | +0.11% | +0.47% | +0.40% | +0.35% | 0.27 pp | yes | A. STABLE PASS |
| P_high_opening_stock | yes | continuation_landed | -0.17% | +0.11% | +0.47% | +0.40% | +0.35% | 0.27 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | salvage | -0.03% | +0.01% | -0.04% | +0.30% | +0.17% | 0.14 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation | -0.04% | +0.01% | +0.00% | +0.20% | +0.17% | 0.04 pp | yes | A. STABLE PASS |
| Q_volatile_demand_high_target | yes | continuation_landed | -0.04% | +0.01% | +0.00% | +0.20% | +0.17% | 0.04 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | salvage | +0.67% | +0.35% | +0.38% | +0.38% | +0.55% | 0.19 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation | +0.68% | +0.38% | +0.30% | +0.36% | +0.55% | 0.19 pp | yes | A. STABLE PASS |
| R_asymmetric_prices_mov | yes | continuation_landed | +0.68% | +0.38% | +0.30% | +0.36% | +0.55% | 0.19 pp | yes | A. STABLE PASS |
| S_cash_constrained | no (to 12) | salvage | +6.40% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation | +6.45% | - | - | - | - | - | - | INVALID AT 52 |
| S_cash_constrained | no (to 12) | continuation_landed | +4.77% | - | - | - | - | - | - | INVALID AT 52 |
| T_combined_realistic | yes | salvage | -2.04% | -0.92% | +0.29% | +0.95% | +1.92% | 1.83 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation | -1.58% | +0.18% | +0.89% | +1.58% | +2.11% | 1.07 pp | NO | E. NON-CONVERGENT |
| T_combined_realistic | yes | continuation_landed | -0.45% | +1.31% | +1.42% | +2.25% | +2.06% | 0.38 pp | yes | D. BOUNDARY-SENSITIVE -> FAIL |

## Section 6: boundary-sensitivity index and the selection rule

| rule | Stage 7 tests | BSI (pp per two-review shift, all ten policy pairs, valid fixtures, three seeds) | fixtures stable at 52 |
|---|---|---|---|
| salvage | fail | 1.661 | 9 / 19 |
| continuation | fail | 0.919 | 12 / 19 |
| continuation_landed | pass | 0.452 | 18 / 19 |

**Declared rule: continuation_landed** (the only rule passing the twelve tests).

BSI per rule restricted to baseline-only pairs (no ZAAD in the pair), as a check that the index is not driven by ZAAD:

* salvage: 1.391 pp
* continuation: 0.795 pp
* continuation_landed: 0.426 pp

## Section 8, Option D diagnostic: start offset s with symmetric endpoint handling (window [s, 52])

| fixture | rule | s=0 | s=4 | s=8 |
|---|---|---|---|---|
| A_no_terms_good_incumbent | salvage | +0.81% vs incumbent | +0.79% vs incumbent | +0.73% vs incumbent |
| A_no_terms_good_incumbent | continuation | +0.81% vs incumbent | +0.79% vs incumbent | +0.73% vs incumbent |
| A_no_terms_good_incumbent | continuation_landed | +0.81% vs incumbent | +0.79% vs incumbent | +0.73% vs incumbent |
| B_fixed_order_cost_replace_sold | salvage | +3.69% vs economic_lot | +6.93% vs economic_lot | +7.10% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation | +3.06% vs economic_lot | +3.60% vs economic_lot | +3.53% vs economic_lot |
| B_fixed_order_cost_replace_sold | continuation_landed | +2.49% vs economic_lot | +3.38% vs economic_lot | +3.09% vs economic_lot |
| C_moq_four_weeks | salvage | +0.32% vs reorder_point | -2.22% vs reorder_point | -1.92% vs reorder_point |
| C_moq_four_weeks | continuation | +0.46% vs reorder_point | +0.09% vs reorder_point | +0.09% vs reorder_point |
| C_moq_four_weeks | continuation_landed | +0.46% vs reorder_point | +0.09% vs reorder_point | +0.09% vs reorder_point |
| D_case_multiple | salvage | +0.57% vs incumbent | +0.62% vs incumbent | +0.57% vs incumbent |
| D_case_multiple | continuation | +0.66% vs incumbent | +0.71% vs incumbent | +0.68% vs incumbent |
| D_case_multiple | continuation_landed | +0.66% vs incumbent | +0.71% vs incumbent | +0.68% vs incumbent |
| E_pallet_multiple | salvage | -0.32% vs incumbent | -0.35% vs incumbent | -0.38% vs incumbent |
| E_pallet_multiple | continuation | -0.08% vs incumbent | -0.09% vs incumbent | -0.10% vs incumbent |
| E_pallet_multiple | continuation_landed | -0.01% vs incumbent | -0.01% vs incumbent | -0.01% vs incumbent |
| F_mov_two_skus | salvage | +1.82% vs periodic:2 | +0.64% vs periodic:2 | +0.61% vs periodic:2 |
| F_mov_two_skus | continuation | +0.70% vs periodic:2 | +0.52% vs periodic:2 | +0.43% vs periodic:2 |
| F_mov_two_skus | continuation_landed | +0.70% vs periodic:2 | +0.52% vs periodic:2 | +0.43% vs periodic:2 |
| G_freight_tiers | salvage | +1.91% vs economic_lot | +2.43% vs economic_lot | +0.15% vs economic_lot |
| G_freight_tiers | continuation | +1.22% vs economic_lot | +1.39% vs economic_lot | +0.08% vs economic_lot |
| G_freight_tiers | continuation_landed | +0.46% vs economic_lot | +0.50% vs economic_lot | -0.02% vs economic_lot |
| H_per_pallet_freight | salvage | -1.66% vs periodic:2 | -1.89% vs periodic:2 | -2.84% vs periodic:2 |
| H_per_pallet_freight | continuation | -1.68% vs periodic:2 | -1.78% vs periodic:2 | -2.08% vs periodic:2 |
| H_per_pallet_freight | continuation_landed | -1.67% vs periodic:2 | -1.74% vs periodic:2 | -1.64% vs periodic:2 |
| I_max_pallets_ftl_cap | salvage | +0.75% vs economic_lot | +0.82% vs economic_lot | +0.90% vs economic_lot |
| I_max_pallets_ftl_cap | continuation | +0.72% vs economic_lot | +0.78% vs economic_lot | +0.86% vs economic_lot |
| I_max_pallets_ftl_cap | continuation_landed | +0.57% vs economic_lot | +0.61% vs economic_lot | +0.67% vs economic_lot |
| J_net60_cost_of_capital | salvage | +1.30% vs economic_lot | +1.46% vs economic_lot | +1.56% vs economic_lot |
| J_net60_cost_of_capital | continuation | +0.33% vs economic_lot | +0.36% vs economic_lot | +0.39% vs economic_lot |
| J_net60_cost_of_capital | continuation_landed | +0.15% vs economic_lot | +0.17% vs economic_lot | +0.18% vs economic_lot |
| K_deposit_early_cash | salvage | +1.30% vs economic_lot | +1.46% vs economic_lot | +1.56% vs economic_lot |
| K_deposit_early_cash | continuation | +0.32% vs economic_lot | +0.35% vs economic_lot | +0.38% vs economic_lot |
| K_deposit_early_cash | continuation_landed | +0.15% vs economic_lot | +0.16% vs economic_lot | +0.18% vs economic_lot |
| L_high_holding_rate | salvage | -0.11% vs economic_lot | -1.05% vs economic_lot | -1.55% vs economic_lot |
| L_high_holding_rate | continuation | +0.72% vs economic_lot | +0.22% vs economic_lot | -0.03% vs economic_lot |
| L_high_holding_rate | continuation_landed | +0.81% vs economic_lot | +0.63% vs economic_lot | +0.41% vs economic_lot |
| M_order_calendar_wednesday | salvage | +0.09% vs incumbent | +0.10% vs incumbent | -0.88% vs incumbent |
| M_order_calendar_wednesday | continuation | -0.17% vs incumbent | -0.18% vs incumbent | -0.65% vs incumbent |
| M_order_calendar_wednesday | continuation_landed | -0.17% vs incumbent | -0.18% vs incumbent | -0.65% vs incumbent |
| N_long_lead_21_days | salvage | +0.55% vs incumbent | +0.53% vs incumbent | +0.49% vs incumbent |
| N_long_lead_21_days | continuation | +0.61% vs incumbent | +0.59% vs incumbent | +0.55% vs incumbent |
| N_long_lead_21_days | continuation_landed | +0.61% vs incumbent | +0.59% vs incumbent | +0.55% vs incumbent |
| O_low_opening_stock | salvage | +0.43% vs reorder_point | +0.48% vs reorder_point | +0.10% vs reorder_point |
| O_low_opening_stock | continuation | +0.21% vs reorder_point | +0.24% vs reorder_point | +0.13% vs reorder_point |
| O_low_opening_stock | continuation_landed | +0.21% vs reorder_point | +0.24% vs reorder_point | +0.13% vs reorder_point |
| P_high_opening_stock | salvage | +0.41% vs reorder_point | -0.17% vs reorder_point | -0.30% vs reorder_point |
| P_high_opening_stock | continuation | +0.35% vs reorder_point | +0.29% vs reorder_point | +0.37% vs reorder_point |
| P_high_opening_stock | continuation_landed | +0.35% vs reorder_point | +0.29% vs reorder_point | +0.37% vs reorder_point |
| Q_volatile_demand_high_target | salvage | +0.17% vs incumbent | +0.20% vs incumbent | +0.25% vs periodic:2 |
| Q_volatile_demand_high_target | continuation | +0.17% vs incumbent | +0.20% vs incumbent | +0.22% vs incumbent |
| Q_volatile_demand_high_target | continuation_landed | +0.17% vs incumbent | +0.20% vs incumbent | +0.22% vs incumbent |
| R_asymmetric_prices_mov | salvage | +0.55% vs incumbent | +0.61% vs incumbent | +0.60% vs incumbent |
| R_asymmetric_prices_mov | continuation | +0.55% vs incumbent | +0.60% vs incumbent | +0.61% vs incumbent |
| R_asymmetric_prices_mov | continuation_landed | +0.55% vs incumbent | +0.60% vs incumbent | +0.61% vs incumbent |
| T_combined_realistic | salvage | +1.92% vs economic_lot | +2.17% vs economic_lot | +2.30% vs economic_lot |
| T_combined_realistic | continuation | +2.11% vs economic_lot | +2.33% vs economic_lot | +2.49% vs economic_lot |
| T_combined_realistic | continuation_landed | +2.06% vs economic_lot | +2.22% vs economic_lot | +2.40% vs economic_lot |

## Section 8, Option E diagnostic: per-week average cost at 52 and each policy at its own cycle-minimum endpoint in [40, 52] (declared rule)

| fixture | ZAAD per week | best baseline per week | delta (same as @52) | cycle-minimum endpoints (policy: W) | delta at own cycle minima, per-week normalised |
|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 512.4 | incumbent 508.3 | +0.81% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +1.17% |
| B_fixed_order_cost_replace_sold | 545.1 | economic_lot 531.8 | +2.49% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 52, 'gated': 51} | +2.50% |
| C_moq_four_weeks | 510.6 | reorder_point 508.3 | +0.46% | {'incumbent': 40, 'reorder_point': 43, 'periodic:2': 42, 'economic_lot': 43, 'gated': 49} | +0.29% |
| D_case_multiple | 508.3 | incumbent 505.0 | +0.66% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.93% |
| E_pallet_multiple | 536.5 | incumbent 536.6 | -0.01% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.01% |
| F_mov_two_skus | 1,019.7 | periodic:2 1,012.6 | +0.70% | {'incumbent': 40, 'reorder_point': 51, 'periodic:2': 44, 'economic_lot': 51, 'gated': 47} | +0.53% |
| G_freight_tiers | 1,225.3 | economic_lot 1,219.6 | +0.46% | {'incumbent': 43, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 46} | +0.43% |
| H_per_pallet_freight | 572.5 | periodic:2 582.2 | -1.67% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 52} | -1.95% |
| I_max_pallets_ftl_cap | 786.4 | economic_lot 782.0 | +0.57% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 49, 'gated': 48} | +0.72% |
| J_net60_cost_of_capital | 528.8 | economic_lot 528.0 | +0.15% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 41} | +0.06% |
| K_deposit_early_cash | 529.0 | economic_lot 528.2 | +0.15% | {'incumbent': 41, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 43, 'gated': 41} | +0.11% |
| L_high_holding_rate | 541.5 | economic_lot 537.2 | +0.81% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 40, 'gated': 41} | +1.29% |
| M_order_calendar_wednesday | 514.0 | incumbent 514.9 | -0.17% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | -0.12% |
| N_long_lead_21_days | 512.5 | incumbent 509.4 | +0.61% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 41} | +0.38% |
| O_low_opening_stock | 520.4 | reorder_point 519.3 | +0.21% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 42} | +0.41% |
| P_high_opening_stock | 509.3 | reorder_point 507.6 | +0.35% | {'incumbent': 42, 'reorder_point': 41, 'periodic:2': 42, 'economic_lot': 41, 'gated': 52} | +0.05% |
| Q_volatile_demand_high_target | 491.8 | incumbent 491.0 | +0.17% | {'incumbent': 42, 'reorder_point': 42, 'periodic:2': 42, 'economic_lot': 42, 'gated': 42} | +0.20% |
| R_asymmetric_prices_mov | 5,598.6 | incumbent 5,568.0 | +0.55% | {'incumbent': 51, 'reorder_point': 51, 'periodic:2': 52, 'economic_lot': 51, 'gated': 50} | +0.32% |
| T_combined_realistic | 1,248.5 | economic_lot 1,223.3 | +2.06% | {'incumbent': 40, 'reorder_point': 52, 'periodic:2': 42, 'economic_lot': 46, 'gated': 47} | +2.59% |

## Stage 9: A-T at the declared benchmark (rolling horizon, W* = 52, rule continuation_landed) beside the legacy twelve-week result

| fixture | valid | legacy delta (salvage) | rolling @11 | **declared @52** | verdict | class | service | breaches | unmet | avg inv units | terminal on-hand | in-transit | purchases | freight | ordering | carrying | financing | shortage | inventory value change | terminal credit (rule) | P1 / P0 owned | actions | abstentions | legacy first-review checks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | yes | +0.43% | +1.46% | **+0.81%** vs incumbent | PASS | A. STABLE PASS | 0.989 | 4.3 | 55.1 | 17 | 6 | 102 | 25,737 | 0 | 0 | 13 | 0 | 689 | 315 | 543 | 138 / 18 | 41 | 18 | ok |
| B_fixed_order_cost_replace_sold | yes | -10.70% | +3.41% | **+2.49%** vs economic_lot | FAIL | E. NON-CONVERGENT | 1.000 | 0.0 | 0.0 | 621 | 352 | 351 | 28,993 | 0 | 1,833 | 464 | 0 | 0 | -2,061 | 3,697 | 137 / 19 | 150 | 0 | ok |
| C_moq_four_weeks | yes | +3.61% | +2.31% | **+0.46%** vs reorder_point | PASS | C. BOUNDARY-SENSITIVE -> PASS | 1.000 | 0.3 | 2.4 | 364 | 327 | 132 | 27,780 | 0 | 0 | 272 | 0 | 30 | -1,085 | 2,279 | 137 / 19 | 140 | 0 | ok |
| D_case_multiple | yes | -0.58% | +0.23% | **+0.66%** vs incumbent | PASS | A. STABLE PASS | 0.995 | 2.0 | 24.7 | 32 | 20 | 94 | 25,920 | 0 | 0 | 24 | 0 | 309 | 294 | 569 | 138 / 18 | 78 | 7 | ok |
| E_pallet_multiple | yes | -0.00% | +0.00% | **-0.01%** vs incumbent | PASS | A. STABLE PASS | 1.000 | 0.0 | 2.2 | 102 | 100 | 64 | 26,333 | 1,580 | 0 | 76 | 0 | 28 | 92 | 869 | 139 / 17 | 36 | 7 | ok |
| F_mov_two_skus | yes | +0.24% | +1.60% | **+0.70%** vs periodic:2 | PASS | A. STABLE PASS | 1.000 | 0.0 | 3.5 | 676 | 726 | 172 | 55,433 | 0 | 0 | 505 | 0 | 44 | -2,091 | 4,458 | 125 / 31 | 122 | 0 | ok |
| G_freight_tiers | yes | -10.01% | +2.71% | **+0.46%** vs economic_lot | PASS | C. BOUNDARY-SENSITIVE -> PASS | 1.000 | 0.0 | 0.0 | 1186 | 1557 | 0 | 59,130 | 10,600 | 800 | 887 | 0 | 0 | -4,728 | 9,203 | 125 / 31 | 151 | 0 | ok |
| H_per_pallet_freight | yes | -3.73% | -2.86% | **-1.67%** vs periodic:2 | PASS | A. STABLE PASS | 0.997 | 1.0 | 14.7 | 121 | 10 | 97 | 25,958 | 3,400 | 0 | 90 | 0 | 184 | 318 | 610 | 138 / 18 | 124 | 30 | ok |
| I_max_pallets_ftl_cap | yes | +0.53% | +0.16% | **+0.57%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 1.1 | 276 | 309 | 0 | 27,021 | 13,467 | 1,850 | 206 | 0 | 13 | -485 | 2,412 | 137 / 19 | 155 | 0 | ok |
| J_net60_cost_of_capital | yes | -11.06% | +0.88% | **+0.15%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 582 | 374 | 328 | 28,983 | 0 | 800 | 435 | 56 | 0 | -2,055 | 3,528 | 136 / 20 | 142 | 8 | ok |
| K_deposit_early_cash | yes | -11.20% | +0.94% | **+0.15%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 582 | 374 | 328 | 28,983 | 0 | 800 | 435 | 69 | 0 | -2,055 | 3,528 | 136 / 20 | 142 | 8 | ok |
| L_high_holding_rate | yes | -10.16% | +1.30% | **+0.81%** vs economic_lot | PASS | A. STABLE PASS | 1.000 | 0.0 | 0.0 | 612 | 351 | 326 | 28,868 | 0 | 1,050 | 915 | 0 | 0 | -1,957 | 3,424 | 137 / 19 | 151 | 0 | ok |
| M_order_calendar_wednesday | yes | -0.54% | +0.96% | **-0.17%** vs incumbent | PASS | A. STABLE PASS | 0.989 | 1.7 | 57.6 | 87 | 91 | 189 | 26,587 | 0 | 0 | 65 | 0 | 719 | -370 | 1,394 | 12 / 144 | 141 | 1 | ok |
| N_long_lead_21_days | yes | -0.71% | +1.33% | **+0.61%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.990 | 3.7 | 52.6 | 32 | 17 | 280 | 25,699 | 0 | 0 | 24 | 0 | 657 | 560 | 1,481 | 133 / 23 | 41 | 21 | ['categories'] |
| O_low_opening_stock | yes | +0.46% | +0.10% | **+0.21%** vs reorder_point | PASS | A. STABLE PASS | 0.980 | 3.7 | 104.9 | 64 | 44 | 127 | 26,453 | 0 | 0 | 48 | 0 | 1,311 | -582 | 850 | 96 / 60 | 133 | 17 | ok |
| P_high_opening_stock | yes | +0.29% | -0.17% | **+0.35%** vs reorder_point | PASS | A. STABLE PASS | 0.993 | 2.7 | 34.3 | 100 | 33 | 93 | 23,608 | 0 | 0 | 75 | 0 | 428 | 2,498 | 627 | 138 / 18 | 114 | 18 | ok |
| Q_volatile_demand_high_target | yes | +0.85% | -0.04% | **+0.17%** vs incumbent | PASS | A. STABLE PASS | 0.991 | 3.0 | 45.9 | 75 | 58 | 97 | 24,966 | 0 | 0 | 56 | 0 | 574 | 132 | 771 | 69 / 87 | 20 | 1 | ok |
| R_asymmetric_prices_mov | yes | -0.05% | +0.68% | **+0.55%** vs incumbent | proven invalid (legacy N/R classification kept); cost within tolerance | A. STABLE PASS | 0.992 | 2.0 | 79.6 | 56 | 26 | 194 | 283,972 | 0 | 0 | 181 | 0 | 4,820 | 3,367 | 6,093 | 123 / 33 | 31 | 28 | ['categories'] |
| S_cash_constrained | no (to 12) | +0.26% | +4.77% | **+5.16%** vs economic_lot | INVALID AT 52 (diagnostic @12: outside tolerance) | - | 1.000 | 0.0 | 0.0 | 268 | 231 | 135 | 7,268 | 0 | 667 | 46 | 5 | 0 | -713 | 1,987 | 36 / 0 | 36 | 0 | ok |
| T_combined_realistic | yes | -11.47% | -0.45% | **+2.06%** vs economic_lot | FAIL | D. BOUNDARY-SENSITIVE -> FAIL | 0.999 | 0.3 | 9.8 | 1037 | 1484 | 0 | 58,320 | 10,900 | 1,733 | 931 | 116 | 123 | -4,434 | 8,920 | 124 / 32 | 149 | 0 | ok |

Runtime, ZAAD reviews: n 3013, p50 0.96 s, p90 4.32 s, p95 6.53 s, max 79.3 s; total wall of all cells 5,974 s.

