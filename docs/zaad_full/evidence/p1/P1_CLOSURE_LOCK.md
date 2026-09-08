# P1 closure pass — evidence lock (recorded before any code change)

Branch `claude/zaad-cycle-stock-p1`, SHA at lock `3773944`, frozen P0 parent `2e30721`.

## Fixtures (unchanged from `scripts/p1_fixtures.py` at 3773944)

- Seeds: 41001, 41002, 41003. Reviews: 11 rolling reviews of a twelve-period weekly plan (period_days 7).
- Policies: incumbent (declared rule), reorder_point, periodic:2, economic_lot, gated (ZAAD P1).
- Parity tolerance: ZAAD total modelled cost <= best baseline x (1 + 0.02). Not widened.
- C_moq_four_weeks: replace_sold incumbent, minimum 400; expect best in {gated, reorder_point, economic_lot, periodic:2}, action yes, MOQ attributed.
- O_low_opening_stock: periodic:2 incumbent, opening 20 units; expect action either, LEAD_TIME_EXPOSURE + DEMAND_CYCLE, service floor .80.
- P_high_opening_stock: replace_sold incumbent, opening 600 units; expect action yes, no categories required.
- Every other fixture, seed, horizon and expectation as committed.

## Committed result being reproduced (arm `none`)

| fixture | best baseline | ZAAD P1 | delta |
|---|---|---|---|
| C | 5,898 (reorder_point / economic_lot) | 6,115 | +3.68% |
| O | 6,399 (reorder_point / economic_lot) | 6,576 | +2.76% |
| P | 5,786 (reorder_point / economic_lot) | 5,906 | +2.06% |

## Defaults at lock

| field | fixture setting | product default |
|---|---|---|
| order_smoothing | 0 (explicit) | .02 |
| service_gate_basis | target | target |
| timing_tiebreak | 1e-4 | 1e-4 |
| materiality cost / inventory / service | .01 / .05 / .005 | same |
| engine_profile | reliability | reliability |
| scenarios | 3 | 3 |
| declared stress | nil (full fill, 0 extra days, demand x1) | request-specific |

## The five recorded deviations (P1_CLOSEOUT.md section 4)

1. review window 8 -> 11; 2. fixture S receivables; 3. nil default stress with `late` arm kept;
4. order_smoothing 0 on fixtures; 5. fixture N LEAD_TIME_EXPOSURE expectation left failing.

## Rules from here

No change to C/O/P definitions, seeds, expectations, tolerance, windows or baselines. An
expectation may change only after a written proof that it is mathematically invalid.
