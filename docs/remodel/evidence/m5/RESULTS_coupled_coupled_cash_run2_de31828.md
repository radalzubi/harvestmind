# Walmart M5 Experiment B (coupled purchasing) results: `coupled_coupled_cash`

Commit `c149503e4fc49756a46951cc964c9766e8388c76`, coupling `coupled_cash` (hash `f0d394d2e349`), selection `8b6067be83a4`; 120 runs over 10 store groups, 45 complete, 75 not complete; wall 1160 s. Every figure is a modelled dollar index under declared SYNTHETIC coupled supplier terms (fixed order cost, minimum order value, pallet cap, case lots) on OBSERVED Walmart sales; none is a realized saving. Groups are the replication unit (at most ten), so the intervals are wide by construction.

## Group table (mean over completed groups)

| window | scenario | policy | complete/runs | physical failures | abstained | continuation | realized | purchase | ordering | carrying | shortage | fill | items < target | min item fill | order-weeks | lines/order-week | end stock | cancelled OW | cut OW | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 6/10 | 4 | 0 | 2633.98 | 2634.46 | 565.60 | 120.00 | 5.34 | 1656.18 | 0.431 | 4.8 | 0.170 | 3.0 | 2.94 | 34.6 | 4.5 | 14.7 |  | 0.2 |
| final | fill_only | gated | 1/10 | 0 | 9 | 760.77 | 760.77 | 135.07 | 40.00 | 2.14 | 511.57 | 0.245 | 2.0 | 0.225 | 1.0 | 2.00 | 9.3 | 0.0 | 0.0 | 0.00 | 2.9 |
| final | fill_only | periodic:1 | 7/10 | 3 | 0 | 2527.83 | 2528.24 | 526.06 | 102.86 | 3.85 | 1632.22 | 0.378 | 4.6 | 0.235 | 2.6 | 3.13 | 21.9 | 4.3 | 11.4 |  | 0.2 |
| final | fill_only | reorder_point | 7/10 | 3 | 0 | 2526.53 | 2526.94 | 527.26 | 102.86 | 3.83 | 1629.74 | 0.380 | 4.6 | 0.235 | 2.6 | 3.13 | 21.9 | 5.1 | 10.9 |  | 0.2 |
| final | mild_lead | economic_lot | 4/10 | 6 | 0 | 2143.29 | 2143.29 | 418.33 | 130.00 | 4.01 | 1354.03 | 0.428 | 5.0 | 0.139 | 3.2 | 2.67 | 27.3 | 4.0 | 15.5 |  | 0.2 |
| final | mild_lead | gated | 2/10 | 0 | 8 | 805.30 | 805.30 | 139.59 | 40.00 | 2.00 | 547.59 | 0.300 | 3.0 | 0.190 | 1.0 | 2.50 | 9.4 | 0.0 | 0.0 | 0.04 | 3.7 |
| final | mild_lead | periodic:1 | 3/10 | 7 | 0 | 2265.34 | 2265.34 | 465.57 | 80.00 | 4.27 | 1487.31 | 0.317 | 3.3 | 0.253 | 2.0 | 2.44 | 15.1 | 4.3 | 8.7 |  | 0.1 |
| final | mild_lead | reorder_point | 3/10 | 7 | 0 | 2265.34 | 2265.34 | 465.57 | 80.00 | 4.27 | 1487.31 | 0.317 | 3.3 | 0.253 | 2.0 | 2.44 | 15.1 | 4.0 | 8.7 |  | 0.1 |
| final | stable | economic_lot | 4/10 | 6 | 0 | 2143.35 | 2143.35 | 418.33 | 130.00 | 4.07 | 1354.03 | 0.428 | 5.0 | 0.139 | 3.2 | 2.67 | 29.7 | 4.2 | 15.2 |  | 0.1 |
| final | stable | gated | 2/10 | 0 | 8 | 805.40 | 805.40 | 139.59 | 40.00 | 2.10 | 547.59 | 0.300 | 3.0 | 0.190 | 1.0 | 2.50 | 10.5 | 0.0 | 0.0 | 0.04 | 4.4 |
| final | stable | periodic:1 | 3/10 | 7 | 0 | 2264.38 | 2264.38 | 465.57 | 80.00 | 3.30 | 1487.31 | 0.317 | 3.3 | 0.253 | 2.0 | 2.44 | 12.4 | 4.0 | 9.0 |  | 0.1 |
| final | stable | reorder_point | 3/10 | 7 | 0 | 2264.38 | 2264.38 | 465.57 | 80.00 | 3.30 | 1487.31 | 0.317 | 3.3 | 0.253 | 2.0 | 2.44 | 12.4 | 4.0 | 9.0 |  | 0.1 |

## Paired comparison, ZAAD minus baseline per group (continuation cost; negative favours ZAAD; groups where both completed)

| window | scenario | baseline | groups | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|
| final | mild_lead | reorder_point | 2 | -27.47 | [-53.55, -1.39] | [-53.55, -1.39] | 2 / 0 / 0 | 0.5 |
| final | mild_lead | periodic:1 | 2 | -27.47 | [-53.55, -1.39] | [-53.55, -1.39] | 2 / 0 / 0 | 0.5 |
| final | stable | reorder_point | 2 | -27.47 | [-53.55, -1.39] | [-53.55, -1.39] | 2 / 0 / 0 | 0.5 |
| final | stable | periodic:1 | 2 | -27.47 | [-53.55, -1.39] | [-53.55, -1.39] | 2 / 0 / 0 | 0.5 |

## Paired comparison on fill and inventory (ZAAD minus baseline)

| window | scenario | baseline | metric | groups | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|
| final | mild_lead | reorder_point | shortage | 2 | -26.4300 | [-48.0600, -4.8000] | 2 / 0 |
| final | mild_lead | reorder_point | avg_inventory_units | 2 | +3.0148 | [+0.9231, +5.1065] | 0 / 2 |
| final | mild_lead | reorder_point | service_unit_fill | 2 | +0.0344 | [+0.0125, +0.0563] | 2 / 0 |
| final | mild_lead | periodic:1 | shortage | 2 | -26.4300 | [-48.0600, -4.8000] | 2 / 0 |
| final | mild_lead | periodic:1 | avg_inventory_units | 2 | +3.0148 | [+0.9231, +5.1065] | 0 / 2 |
| final | mild_lead | periodic:1 | service_unit_fill | 2 | +0.0344 | [+0.0125, +0.0563] | 2 / 0 |
| final | stable | reorder_point | shortage | 2 | -26.4300 | [-48.0600, -4.8000] | 2 / 0 |
| final | stable | reorder_point | avg_inventory_units | 2 | +3.0148 | [+0.9231, +5.1065] | 0 / 2 |
| final | stable | reorder_point | service_unit_fill | 2 | +0.0344 | [+0.0125, +0.0563] | 2 / 0 |
| final | stable | periodic:1 | shortage | 2 | -26.4300 | [-48.0600, -4.8000] | 2 / 0 |
| final | stable | periodic:1 | avg_inventory_units | 2 | +3.0148 | [+0.9231, +5.1065] | 0 / 2 |
| final | stable | periodic:1 | service_unit_fill | 2 | +0.0344 | [+0.0125, +0.0563] | 2 / 0 |

## Completion and constraint breaches

Completion by policy (a run stops at the first review whose order breaks a shared constraint in settlement, PHYSICAL_FAILURE, or on which ZAAD abstains): economic_lot: 14/30 complete, 16 physical failures, 0 abstained, 0 infeasible; gated: 5/30 complete, 0 physical failures, 25 abstained, 0 infeasible; periodic:1: 13/30 complete, 17 physical failures, 0 abstained, 0 infeasible; reorder_point: 13/30 complete, 17 physical failures, 0 abstained, 0 infeasible

- final/stable store CA_1 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store CA_1 economic_lot: PHYSICAL_FAILURE after 2 reviews: insufficient dated liquidity
- final/stable store CA_1 reorder_point: PHYSICAL_FAILURE after 2 reviews: insufficient dated liquidity
- final/stable store CA_1 periodic:1: PHYSICAL_FAILURE after 2 reviews: insufficient dated liquidity
- final/mild_lead store CA_1 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/mild_lead store CA_1 economic_lot: PHYSICAL_FAILURE after 2 reviews: insufficient dated liquidity
- final/mild_lead store CA_1 reorder_point: PHYSICAL_FAILURE after 2 reviews: insufficient dated liquidity
- final/mild_lead store CA_1 periodic:1: PHYSICAL_FAILURE after 2 reviews: insufficient dated liquidity
- final/fill_only store CA_1 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store CA_3 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store CA_3 economic_lot: PHYSICAL_FAILURE after 1 reviews: insufficient dated liquidity
- final/mild_lead store CA_3 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/mild_lead store CA_3 economic_lot: PHYSICAL_FAILURE after 1 reviews: insufficient dated liquidity
- final/fill_only store CA_3 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store CA_4 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store CA_4 reorder_point: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/stable store CA_4 periodic:1: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/mild_lead store CA_4 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/mild_lead store CA_4 reorder_point: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/mild_lead store CA_4 periodic:1: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/fill_only store CA_4 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store TX_1 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store TX_1 economic_lot: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/stable store TX_1 reorder_point: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/stable store TX_1 periodic:1: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/mild_lead store TX_1 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/mild_lead store TX_1 economic_lot: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/mild_lead store TX_1 reorder_point: PHYSICAL_FAILURE after 8 reviews: insufficient dated liquidity
- final/mild_lead store TX_1 periodic:1: PHYSICAL_FAILURE after 8 reviews: insufficient dated liquidity
- final/fill_only store TX_1 gated: ABSTAIN after 0 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/fill_only store TX_1 economic_lot: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/fill_only store TX_1 reorder_point: PHYSICAL_FAILURE after 8 reviews: insufficient dated liquidity
- final/fill_only store TX_1 periodic:1: PHYSICAL_FAILURE after 8 reviews: insufficient dated liquidity
- final/stable store TX_2 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/stable store TX_2 reorder_point: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/stable store TX_2 periodic:1: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/mild_lead store TX_2 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
- final/mild_lead store TX_2 reorder_point: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/mild_lead store TX_2 periodic:1: PHYSICAL_FAILURE after 4 reviews: insufficient dated liquidity
- final/fill_only store TX_2 gated: ABSTAIN after 1 reviews: ABSTAIN; operator_declared; mode=ALLOCATE
