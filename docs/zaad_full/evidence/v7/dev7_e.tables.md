# rows 99  cells 33  seeds [36001]

## SERVICE / INVENTORY / COST
| method | runs | complete | timeout/abstain | error | svc median | svc p10 | breaches | inv periods | quiet inv | cost median |
|---|---|---|---|---|---|---|---|---|---|---|
| gated | 33 | 33 | 0 | 0 | 0.960 | 0.796 | 15 | 1.71 | 1.07 | 2780 |
| gated_v6 | 33 | 33 | 0 | 0 | 0.955 | 0.797 | 16 | 1.67 | 1.08 | 2847 |
| echelon_base_stock | 33 | 32 | 1 | 0 | 0.924 | 0.726 | 19 | 1.21 | 1.18 | 2854 |

## STATUS (every non-complete row kept)
- gated: all 33 complete
- gated_v6: all 33 complete
- echelon_base_stock: {'COMPLETE': 32, 'TIME_LIMIT': 1}

## NETWORK (central_branches, central_two_branches, two_locations)
| method | runs | svc median | breaches | inv periods |
|---|---|---|---|---|
| gated | 18 | 0.970 | 6 | 2.42 |
| gated_v6 | 18 | 0.959 | 6 | 2.42 |
| echelon_base_stock | 17 | 0.955 | 8 | 2.19 |

## CAPITAL (v7 fields; blank for methods that do not compute them)
| method | unexplained share | stale share | dup v7 units | pooling excess | premature units | cash days advanced | reconciles |
|---|---|---|---|---|---|---|---|
| gated | 0.035 | 0.000 | 0.0 | 1.6 | 937 | 308 | True |
| gated_v6 | - | - | - | - | 0 | 0 | True |
| echelon_base_stock | - | - | - | - | - | - | True |

## RECOVERY (long-horizon temporary-risk cells, horizon >= 20)
| method | cells | lean share (service rows) | lean share (all rows) | reviews-to-lean median | dup v6 | inv periods |
|---|---|---|---|---|---|---|
| gated | 15 | 0.600 | 0.600 | 0.0 | 0.0 | 1.71 |
| gated_v6 | 15 | 0.600 | 0.600 | 0.0 | 0.0 | 1.73 |
| echelon_base_stock | 14 | - | - | - | - | 1.14 |

## FAST-ARC POOLING (v7 cells 97-101 by transfer lead)
- lead 1 capacity 15.0: n=1 svc=0.809 inv=1.10 pooled=14.9 local=28.2
- lead 1 capacity 50.0: n=6 svc=0.970 inv=2.08 pooled=19.5 local=24.3
- lead 2 capacity 50.0: n=1 svc=0.977 inv=1.53 pooled=0.0 local=44.8
- lead 3 capacity 15.0: n=1 svc=0.726 inv=0.90 pooled=0.0 local=43.8
- lead 3 capacity 50.0: n=1 svc=0.896 inv=1.77 pooled=0.0 local=43.8

## PAIRED gated vs gated_v6 (same cell and seed, both complete)
- paired cells: 33
- service: v7 0.960 vs v6 0.955; mean delta 0.003
- inventory periods: v7 1.71 vs v6 1.67; mean delta -0.08
- cost: mean delta -17.9
- breaches: v7 15 vs v6 16

| cell | demand | supply | network | H | v7 svc | v6 svc | d svc | v7 inv | v6 inv | d inv |
|---|---|---|---|---|---|---|---|---|---|---|
| 20 | stable | deterioration_recovery | single | 20 | 0.796 | 0.797 | -0.000 | 0.88 | 1.99 | -1.12 |
| 15 | stable | fill | single | 12 | 1.000 | 1.000 | 0.000 | 2.10 | 3.05 | -0.94 |
| 89 | intermittent | stable | central_two_branches | 12 | 0.977 | 0.955 | 0.022 | 12.78 | 13.39 | -0.61 |
| 107 | intermittent | stable | central_two_branches | 12 | 0.977 | 0.955 | 0.022 | 12.78 | 13.39 | -0.61 |
| 16 | stable | lead | single | 12 | 0.928 | 0.928 | 0.000 | 1.27 | 1.67 | -0.40 |
| 121 | stable | false_signal | single | 26 | 0.961 | 0.938 | 0.023 | 0.67 | 1.00 | -0.34 |
| 0 | stable | stable | single | 12 | 0.923 | 0.927 | -0.004 | 0.44 | 0.58 | -0.14 |
| 21 | stable | closure_recovery | single | 20 | 0.743 | 0.731 | 0.012 | 1.21 | 1.33 | -0.13 |
| 110 | stable | closure_recovery | single | 30 | 0.806 | 0.797 | 0.009 | 0.57 | 0.66 | -0.09 |
| 90 | stable | deterioration_recovery | single | 26 | 0.851 | 0.853 | -0.002 | 2.49 | 2.58 | -0.09 |
| 87 | decrease | stable | central_two_branches | 26 | 1.000 | 1.000 | 0.000 | 5.35 | 5.40 | -0.05 |
| 1 | stable | stable | single | 12 | 0.968 | 0.968 | 0.000 | 0.62 | 0.65 | -0.03 |
| 2 | stable | stable | single | 12 | 0.969 | 0.969 | 0.000 | 1.04 | 1.07 | -0.03 |
| 116 | decrease | stable | single | 30 | 1.000 | 1.000 | 0.000 | 1.63 | 1.65 | -0.02 |
| 96 | temporary_spike | stable | single | 26 | 0.910 | 0.907 | 0.002 | 1.71 | 1.73 | -0.02 |
| 46 | stable | lead | single | 12 | 0.792 | 0.792 | 0.000 | 1.70 | 1.70 | 0.00 |
| 85 | promotion_recovery | stable | central_two_branches | 26 | 0.906 | 0.906 | 0.000 | 3.87 | 3.87 | 0.00 |
| 88 | volatile | stable | central_two_branches | 12 | 0.935 | 0.935 | 0.000 | 2.42 | 2.42 | 0.00 |
| 99 | stable | stable | central_two_branches | 12 | 0.896 | 0.896 | 0.000 | 1.77 | 1.77 | 0.00 |
| 100 | stable | stable | central_two_branches | 12 | 0.809 | 0.809 | 0.000 | 1.10 | 1.10 | 0.00 |
| 101 | stable | stable | central_two_branches | 12 | 0.726 | 0.726 | 0.000 | 0.90 | 0.90 | 0.00 |
| 106 | volatile | stable | central_two_branches | 12 | 0.935 | 0.935 | 0.000 | 2.42 | 2.42 | 0.00 |
| 112 | promotion_recovery | stable | single | 28 | 0.983 | 0.983 | 0.000 | 1.60 | 1.60 | 0.00 |
| 122 | stable | false_signal | central_two_branches | 26 | 0.969 | 0.969 | 0.000 | 1.41 | 1.41 | 0.00 |
| 59 | promotion_recovery | lead | two_locations | 20 | 0.960 | 0.960 | 0.000 | 3.96 | 3.93 | 0.04 |
| 117 | decrease | stable | central_two_branches | 30 | 0.991 | 0.991 | -0.000 | 4.81 | 4.76 | 0.05 |
| 104 | stable | stable | central_two_branches | 12 | 0.958 | 0.958 | 0.000 | 1.05 | 0.96 | 0.09 |
| 72 | stable | stable | central_two_branches | 12 | 0.971 | 0.971 | 0.000 | 1.74 | 1.64 | 0.10 |
| 97 | stable | stable | central_two_branches | 12 | 0.971 | 0.971 | 0.000 | 1.74 | 1.64 | 0.10 |
| 35 | intermittent | stable | central_branches | 12 | 1.000 | 1.000 | 0.000 | 7.40 | 7.26 | 0.14 |
| 98 | stable | stable | central_two_branches | 12 | 0.977 | 0.977 | 0.000 | 1.53 | 1.31 | 0.22 |
| 57 | intermittent_spiky | closure_recovery | central_branches | 20 | 1.000 | 1.000 | 0.000 | 8.30 | 7.97 | 0.33 |
| 108 | stable | deterioration_recovery | single | 30 | 0.869 | 0.869 | -0.000 | 1.80 | 0.80 | 1.00 |
