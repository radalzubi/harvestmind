# Walmart M5 Experiment B (coupled purchasing) results: `coupled_coupled_tight`

Commit `None`, coupling `coupled_tight` (hash ``), selection ``; 72 runs over 6 store groups, 72 complete, 0 not complete; wall 0 s. Every figure is a modelled dollar index under declared SYNTHETIC coupled supplier terms (fixed order cost, minimum order value, pallet cap, case lots) on OBSERVED Walmart sales; none is a realized saving. Groups are the replication unit (at most ten), so the intervals are wide by construction.

## Group table (mean over completed groups)

| window | scenario | policy | complete/runs | physical failures | abstained | continuation | realized | purchase | ordering | carrying | shortage | fill | items < target | min item fill | order-weeks | lines/order-week | end stock | cancelled OW | cut OW | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 6/6 | 0 | 0 | 2785.81 | 2864.74 | 1622.93 | 293.33 | 16.43 | 985.34 | 0.723 | 3.7 | 0.463 | 7.3 | 1.85 | 97.6 | 2.2 | 18.7 |  | 0.1 |
| final | fill_only | gated | 6/6 | 0 | 0 | 2720.61 | 2814.62 | 1852.50 | 320.00 | 16.18 | 745.20 | 0.727 | 4.2 | 0.431 | 8.0 | 2.21 | 99.0 | 0.0 | 0.0 | 0.14 | 343.0 |
| final | fill_only | periodic:1 | 6/6 | 0 | 0 | 2725.47 | 2779.54 | 1512.37 | 306.67 | 10.34 | 890.57 | 0.664 | 4.5 | 0.354 | 7.7 | 1.90 | 73.1 | 2.2 | 15.0 |  | 0.1 |
| final | fill_only | reorder_point | 6/6 | 0 | 0 | 2717.98 | 2769.81 | 1498.55 | 300.00 | 10.34 | 890.57 | 0.664 | 4.5 | 0.354 | 7.5 | 1.88 | 73.1 | 3.5 | 13.3 |  | 0.1 |
| final | mild_lead | economic_lot | 6/6 | 0 | 0 | 2595.16 | 2677.37 | 1374.52 | 260.00 | 17.08 | 1095.66 | 0.664 | 4.3 | 0.413 | 6.5 | 1.85 | 102.8 | 2.7 | 18.3 |  | 0.1 |
| final | mild_lead | gated | 6/6 | 0 | 0 | 2569.30 | 2658.79 | 1540.84 | 286.67 | 19.91 | 910.77 | 0.676 | 4.3 | 0.410 | 7.2 | 2.09 | 110.6 | 0.0 | 0.0 | 0.13 | 119.9 |
| final | mild_lead | periodic:1 | 6/6 | 0 | 0 | 2572.52 | 2634.55 | 1306.65 | 266.67 | 10.88 | 1028.11 | 0.620 | 4.7 | 0.342 | 6.7 | 1.84 | 78.0 | 3.7 | 12.7 |  | 0.2 |
| final | mild_lead | reorder_point | 6/6 | 0 | 0 | 2572.52 | 2634.55 | 1306.65 | 266.67 | 10.88 | 1028.11 | 0.620 | 4.7 | 0.342 | 6.7 | 1.84 | 78.0 | 4.3 | 12.0 |  | 0.2 |
| final | stable | economic_lot | 6/6 | 0 | 0 | 2589.87 | 2691.58 | 1561.92 | 280.00 | 17.59 | 996.13 | 0.707 | 4.0 | 0.433 | 7.0 | 1.80 | 110.4 | 2.3 | 18.5 |  | 0.2 |
| final | stable | gated | 6/6 | 0 | 0 | 2548.94 | 2647.07 | 1727.32 | 320.00 | 22.20 | 718.41 | 0.727 | 3.7 | 0.475 | 8.0 | 2.01 | 121.3 | 0.0 | 0.0 | 0.17 | 259.5 |
| final | stable | periodic:1 | 6/6 | 0 | 0 | 2539.59 | 2596.43 | 1415.42 | 293.33 | 11.81 | 829.32 | 0.689 | 4.2 | 0.385 | 7.3 | 1.85 | 83.0 | 3.5 | 12.3 |  | 0.2 |
| final | stable | reorder_point | 6/6 | 0 | 0 | 2539.47 | 2596.60 | 1416.49 | 293.33 | 11.76 | 829.32 | 0.689 | 4.2 | 0.385 | 7.3 | 1.82 | 82.8 | 4.2 | 11.7 |  | 0.2 |

## Paired comparison, ZAAD minus baseline per group (continuation cost; negative favours ZAAD; groups where both completed)

| window | scenario | baseline | groups | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 6 | -65.21 | [-126.83, -16.27] | [-156.37, +11.19] | 2 / 1 / 3 | 1.0 |
| final | fill_only | reorder_point | 6 | +2.62 | [-49.68, +57.31] | [-71.89, +84.61] | 3 / 3 / 0 | 1.0 |
| final | fill_only | periodic:1 | 6 | -4.86 | [-54.59, +45.69] | [-78.52, +77.78] | 4 / 2 / 0 | 0.688 |
| final | mild_lead | economic_lot | 6 | -25.86 | [-57.93, +6.04] | [-87.87, +8.33] | 1 / 2 / 3 | 1.0 |
| final | mild_lead | reorder_point | 6 | -3.23 | [-55.84, +50.31] | [-82.64, +76.19] | 3 / 3 / 0 | 1.0 |
| final | mild_lead | periodic:1 | 6 | -3.23 | [-56.77, +49.04] | [-85.24, +76.19] | 3 / 3 / 0 | 1.0 |
| final | stable | economic_lot | 6 | -40.93 | [-91.54, +7.40] | [-134.75, +17.07] | 2 / 1 / 3 | 1.0 |
| final | stable | reorder_point | 6 | +9.47 | [-20.36, +39.85] | [-36.55, +57.74] | 3 / 3 / 0 | 1.0 |
| final | stable | periodic:1 | 6 | +9.35 | [-19.93, +39.52] | [-37.04, +57.74] | 3 / 3 / 0 | 1.0 |

## Paired comparison on fill and inventory (ZAAD minus baseline)

| window | scenario | baseline | metric | groups | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | shortage | 6 | -240.1411 | [-795.3529, +57.7120] | 1 / 2 |
| final | fill_only | economic_lot | avg_inventory_units | 6 | +1.4052 | [-11.4960, +15.6546] | 1 / 2 |
| final | fill_only | economic_lot | service_unit_fill | 6 | +0.0044 | [-0.0371, +0.0537] | 1 / 2 |
| final | fill_only | reorder_point | shortage | 6 | -145.3683 | [-409.5949, +96.5422] | 3 / 3 |
| final | fill_only | reorder_point | avg_inventory_units | 6 | +25.9245 | [+1.1376, +49.9756] | 1 / 5 |
| final | fill_only | reorder_point | service_unit_fill | 6 | +0.0629 | [-0.0485, +0.1909] | 4 / 2 |
| final | fill_only | periodic:1 | shortage | 6 | -145.3683 | [-393.1759, +97.7487] | 3 / 3 |
| final | fill_only | periodic:1 | avg_inventory_units | 6 | +25.9245 | [-0.4348, +50.3511] | 1 / 5 |
| final | fill_only | periodic:1 | service_unit_fill | 6 | +0.0629 | [-0.0586, +0.1922] | 4 / 2 |
| final | mild_lead | economic_lot | shortage | 6 | -184.8917 | [-589.9200, +28.8050] | 1 / 2 |
| final | mild_lead | economic_lot | avg_inventory_units | 6 | +7.8718 | [+1.3590, +16.7436] | 0 / 3 |
| final | mild_lead | economic_lot | service_unit_fill | 6 | +0.0120 | [-0.0100, +0.0479] | 1 / 2 |
| final | mild_lead | reorder_point | shortage | 6 | -117.3417 | [-464.5467, +238.7300] | 4 / 2 |
| final | mild_lead | reorder_point | avg_inventory_units | 6 | +32.6538 | [+0.1026, +65.1538] | 1 / 5 |
| final | mild_lead | reorder_point | service_unit_fill | 6 | +0.0557 | [-0.1015, +0.2110] | 5 / 1 |
| final | mild_lead | periodic:1 | shortage | 6 | -117.3417 | [-464.5467, +229.8633] | 4 / 2 |
| final | mild_lead | periodic:1 | avg_inventory_units | 6 | +32.6538 | [+0.1026, +64.9487] | 1 / 5 |
| final | mild_lead | periodic:1 | service_unit_fill | 6 | +0.0557 | [-0.0982, +0.2128] | 5 / 1 |
| final | stable | economic_lot | shortage | 6 | -277.7200 | [-809.6133, +0.0000] | 2 / 0 |
| final | stable | economic_lot | avg_inventory_units | 6 | +10.8905 | [+0.0000, +23.9024] | 0 / 2 |
| final | stable | economic_lot | service_unit_fill | 6 | +0.0207 | [+0.0000, +0.0587] | 2 / 0 |
| final | stable | reorder_point | shortage | 6 | -110.9081 | [-415.2418, +134.7133] | 3 / 3 |
| final | stable | reorder_point | avg_inventory_units | 6 | +38.4433 | [+3.5000, +72.0074] | 1 / 5 |
| final | stable | reorder_point | service_unit_fill | 6 | +0.0387 | [-0.0891, +0.1896] | 3 / 3 |
| final | stable | periodic:1 | shortage | 6 | -110.9081 | [-412.3365, +140.6913] | 3 / 3 |
| final | stable | periodic:1 | avg_inventory_units | 6 | +38.2894 | [+3.2722, +71.5843] | 1 / 5 |
| final | stable | periodic:1 | service_unit_fill | 6 | +0.0387 | [-0.0852, +0.1892] | 3 / 3 |

## Completion and constraint breaches

Completion by policy (a run stops at the first review whose order breaks a shared constraint in settlement, PHYSICAL_FAILURE, or on which ZAAD abstains): economic_lot: 18/18 complete, 0 physical failures, 0 abstained, 0 infeasible; gated: 18/18 complete, 0 physical failures, 0 abstained, 0 infeasible; periodic:1: 18/18 complete, 0 physical failures, 0 abstained, 0 infeasible; reorder_point: 18/18 complete, 0 physical failures, 0 abstained, 0 infeasible

