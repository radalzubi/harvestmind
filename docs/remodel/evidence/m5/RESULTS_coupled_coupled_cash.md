# Walmart M5 Experiment B (coupled purchasing) results: `coupled_coupled_cash`

Commit `da1ad314a31ec96a24e562e1e80297602aba5cdd`, coupling `coupled_cash` (hash `f0d394d2e349`), selection `8b6067be83a4`; 120 runs over 10 store groups, 120 complete, 0 not complete; wall 1277 s. Every figure is a modelled dollar index under declared SYNTHETIC coupled supplier terms (fixed order cost, minimum order value, pallet cap, case lots) on OBSERVED Walmart sales; none is a realized saving. Groups are the replication unit (at most ten), so the intervals are wide by construction.

## Group table (mean over completed groups)

| window | scenario | policy | complete/runs | physical failures | abstained | continuation | realized | purchase | ordering | carrying | shortage | fill | items < target | min item fill | order-weeks | lines/order-week | end stock | cancelled OW | cut OW | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 10/10 | 0 | 0 | 2245.66 | 2246.56 | 433.33 | 104.00 | 4.62 | 1473.74 | 0.436 | 4.6 | 0.166 | 2.6 | 2.69 | 72.8 | 1.8 | 15.0 |  | 0.1 |
| final | fill_only | gated | 10/10 | 0 | 0 | 2227.52 | 2228.42 | 447.12 | 96.00 | 4.99 | 1449.44 | 0.440 | 4.6 | 0.187 | 2.4 | 2.78 | 76.6 | 0.0 | 0.0 | 0.02 | 37.4 |
| final | fill_only | periodic:1 | 10/10 | 0 | 0 | 2244.27 | 2244.73 | 432.51 | 112.00 | 3.49 | 1464.01 | 0.383 | 4.6 | 0.214 | 2.8 | 2.72 | 38.5 | 1.4 | 12.0 |  | 0.1 |
| final | fill_only | reorder_point | 10/10 | 0 | 0 | 2244.75 | 2245.21 | 431.82 | 112.00 | 3.53 | 1465.14 | 0.386 | 4.6 | 0.215 | 2.8 | 2.72 | 39.2 | 1.4 | 11.7 |  | 0.1 |
| final | mild_lead | economic_lot | 10/10 | 0 | 0 | 2191.67 | 2193.27 | 436.71 | 104.00 | 5.71 | 1419.16 | 0.462 | 4.6 | 0.187 | 2.6 | 2.62 | 84.6 | 1.8 | 15.3 |  | 0.1 |
| final | mild_lead | gated | 10/10 | 0 | 0 | 2169.69 | 2171.38 | 456.05 | 88.00 | 6.07 | 1396.18 | 0.455 | 4.6 | 0.223 | 2.2 | 2.86 | 89.8 | 0.0 | 0.0 | 0.05 | 41.7 |
| final | mild_lead | periodic:1 | 10/10 | 0 | 0 | 2206.35 | 2207.04 | 411.59 | 112.00 | 3.89 | 1447.84 | 0.385 | 4.6 | 0.216 | 2.8 | 2.66 | 41.2 | 2.9 | 10.5 |  | 0.1 |
| final | mild_lead | reorder_point | 10/10 | 0 | 0 | 2206.28 | 2206.98 | 411.69 | 112.00 | 3.87 | 1447.70 | 0.389 | 4.6 | 0.214 | 2.8 | 2.61 | 40.2 | 3.3 | 10.3 |  | 0.1 |
| final | stable | economic_lot | 10/10 | 0 | 0 | 2191.24 | 2192.75 | 436.71 | 104.00 | 5.55 | 1418.36 | 0.463 | 4.6 | 0.187 | 2.6 | 2.62 | 85.0 | 1.8 | 15.1 |  | 0.1 |
| final | stable | gated | 10/10 | 0 | 0 | 2174.82 | 2176.32 | 457.78 | 96.00 | 6.15 | 1388.26 | 0.460 | 4.6 | 0.210 | 2.4 | 2.62 | 88.7 | 0.0 | 0.0 | 0.05 | 47.2 |
| final | stable | periodic:1 | 10/10 | 0 | 0 | 2205.91 | 2206.50 | 411.59 | 112.00 | 3.70 | 1447.04 | 0.386 | 4.6 | 0.216 | 2.8 | 2.66 | 40.7 | 2.8 | 10.8 |  | 0.1 |
| final | stable | reorder_point | 10/10 | 0 | 0 | 2205.86 | 2206.45 | 411.69 | 112.00 | 3.70 | 1446.90 | 0.390 | 4.6 | 0.214 | 2.8 | 2.61 | 41.1 | 3.3 | 10.5 |  | 0.1 |

## Paired comparison, ZAAD minus baseline per group (continuation cost; negative favours ZAAD; groups where both completed)

| window | scenario | baseline | groups | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 10 | -18.14 | [-36.28, +0.00] | [-54.42, +0.00] | 1 / 0 / 9 | 1.0 |
| final | fill_only | reorder_point | 10 | -17.23 | [-27.55, -7.25] | [-32.47, -2.15] | 8 / 2 / 0 | 0.109 |
| final | fill_only | periodic:1 | 10 | -16.75 | [-26.45, -6.61] | [-31.63, -1.35] | 8 / 2 / 0 | 0.109 |
| final | mild_lead | economic_lot | 10 | -21.98 | [-46.50, +0.30] | [-65.73, +6.02] | 5 / 1 / 4 | 0.219 |
| final | mild_lead | reorder_point | 10 | -36.60 | [-51.50, -21.51] | [-59.00, -14.26] | 9 / 1 / 0 | 0.021 |
| final | mild_lead | periodic:1 | 10 | -36.66 | [-51.85, -22.33] | [-58.95, -14.25] | 9 / 1 / 0 | 0.021 |
| final | stable | economic_lot | 10 | -16.43 | [-28.78, -4.08] | [-37.82, -1.43] | 4 / 0 / 6 | 0.125 |
| final | stable | reorder_point | 10 | -31.05 | [-44.58, -17.54] | [-50.81, -10.63] | 9 / 1 / 0 | 0.021 |
| final | stable | periodic:1 | 10 | -31.09 | [-45.04, -17.49] | [-51.73, -10.66] | 9 / 1 / 0 | 0.021 |

## Paired comparison on fill and inventory (ZAAD minus baseline)

| window | scenario | baseline | metric | groups | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | shortage | 10 | -24.2970 | [-72.8910, +0.0000] | 1 / 0 |
| final | fill_only | economic_lot | avg_inventory_units | 10 | +3.7487 | [+0.0000, +11.2460] | 0 / 1 |
| final | fill_only | economic_lot | service_unit_fill | 10 | +0.0038 | [+0.0000, +0.0113] | 1 / 0 |
| final | fill_only | reorder_point | shortage | 10 | -15.7008 | [-42.6601, +14.2379] | 7 / 3 |
| final | fill_only | reorder_point | avg_inventory_units | 10 | +37.4298 | [+3.7664, +91.4524] | 1 / 9 |
| final | fill_only | reorder_point | service_unit_fill | 10 | +0.0534 | [+0.0024, +0.1170] | 7 / 3 |
| final | fill_only | periodic:1 | shortage | 10 | -14.5725 | [-44.4114, +16.6235] | 7 / 3 |
| final | fill_only | periodic:1 | avg_inventory_units | 10 | +38.0679 | [+4.1757, +93.9042] | 1 / 9 |
| final | fill_only | periodic:1 | service_unit_fill | 10 | +0.0566 | [+0.0025, +0.1283] | 6 / 4 |
| final | mild_lead | economic_lot | shortage | 10 | -22.9740 | [-87.2655, +30.0690] | 4 / 2 |
| final | mild_lead | economic_lot | avg_inventory_units | 10 | +5.2775 | [-1.9705, +13.9065] | 1 / 5 |
| final | mild_lead | economic_lot | service_unit_fill | 10 | -0.0073 | [-0.0515, +0.0271] | 3 / 3 |
| final | mild_lead | reorder_point | shortage | 10 | -51.5160 | [-100.4040, -3.1054] | 8 / 2 |
| final | mild_lead | reorder_point | avg_inventory_units | 10 | +49.6272 | [+10.4395, +116.7796] | 0 / 10 |
| final | mild_lead | reorder_point | service_unit_fill | 10 | +0.0657 | [+0.0162, +0.1284] | 7 / 3 |
| final | mild_lead | periodic:1 | shortage | 10 | -51.6600 | [-101.0194, -4.5459] | 8 / 2 |
| final | mild_lead | periodic:1 | avg_inventory_units | 10 | +48.6195 | [+10.4696, +113.8116] | 0 / 10 |
| final | mild_lead | periodic:1 | service_unit_fill | 10 | +0.0695 | [+0.0157, +0.1421] | 7 / 3 |
| final | stable | economic_lot | shortage | 10 | -30.0960 | [-59.4360, -5.7840] | 4 / 0 |
| final | stable | economic_lot | avg_inventory_units | 10 | +3.6861 | [+0.7142, +7.6127] | 0 / 4 |
| final | stable | economic_lot | service_unit_fill | 10 | -0.0031 | [-0.0418, +0.0240] | 3 / 1 |
| final | stable | reorder_point | shortage | 10 | -58.6380 | [-93.9666, -18.4188] | 9 / 1 |
| final | stable | reorder_point | avg_inventory_units | 10 | +47.5864 | [+10.2174, +112.7076] | 0 / 10 |
| final | stable | reorder_point | service_unit_fill | 10 | +0.0699 | [+0.0237, +0.1289] | 9 / 1 |
| final | stable | periodic:1 | shortage | 10 | -58.7820 | [-93.8582, -18.8894] | 9 / 1 |
| final | stable | periodic:1 | avg_inventory_units | 10 | +47.9710 | [+9.4373, +114.2138] | 0 / 10 |
| final | stable | periodic:1 | service_unit_fill | 10 | +0.0737 | [+0.0203, +0.1441] | 9 / 1 |

## Completion and constraint breaches

Completion by policy (a run stops at the first review whose order breaks a shared constraint in settlement, PHYSICAL_FAILURE, or on which ZAAD abstains): economic_lot: 30/30 complete, 0 physical failures, 0 abstained, 0 infeasible; gated: 30/30 complete, 0 physical failures, 0 abstained, 0 infeasible; periodic:1: 30/30 complete, 0 physical failures, 0 abstained, 0 infeasible; reorder_point: 30/30 complete, 0 physical failures, 0 abstained, 0 infeasible

