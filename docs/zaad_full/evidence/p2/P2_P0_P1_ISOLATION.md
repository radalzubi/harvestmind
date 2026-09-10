# P2: frozen P0 / P1 behaviour under the P2 code

Every frozen file P2 touched (`contracts.py`, `worlds.py`, `model.py`, `settlement.py`, `planner.py`,
`replay.py`, `policies.py`, `lotsizing.py`, `terminal.py`, plus the new `correlation.py`) carries a
default-off hook or telemetry only; this file records the evidence that the frozen decisions are
unchanged.

## 1. Canonical regression (`scripts/zaad_canonical_regression.py`)

Run after every frozen-file change and at the final P2 SHA:

```
P1 B_fixed_order_cost_replace_sold  reviews 12 identical True
P1 T_combined_realistic             reviews 12 identical True
P1 Q_volatile_demand_high_target    reviews 12 identical True
P1 A_no_terms_good_incumbent        reviews 12 identical True
P0 cell 15 (router_cycle) identical True reviews 12   every review protection-owned
CANONICAL REGRESSION PASS
```

B, T, Q and A reproduce the P1 freeze record order for order and status for status over twelve
rolling reviews; P0 cell 15 reproduces the recorded arm on every decision key (state, requested and
built candidate sets, status, recovery mode, feasible set, final P0 purchases).

## 2. P0 six-cell isolation (`scripts/p1_p0_arms.py p2_meio` against `router_cycle`)

The six-cell focused set (cells 15, 16, 20, 21, 90, 108; seed 38001; the same truth and replay as
`evidence/v8/p0/final8.py`) replayed under the P2 code at product defaults and compared review by
review with the recorded P1 final-closure arm by `scripts/p1_ownership_compare.py` (keys: state,
requested, built, selected, status, recovery mode, feasible set, chosen, final P0 purchases).

### Run 1 (`p0_arm_p2_meio_run1.json`, `p0_six_cell_compare_run1.txt`) - under concurrent load

The arm ran while the corrected benchmark (four workers), the full test suite, the invariants and the
adversarial review were running on the same machine.

| cell | reviews | owner | decision-identical | cost | service | unmet |
|---|---|---|---|---|---|---|
| 15 | 12 | P0 x 12 | 12 / 12 | 1678 -> 1678 | .980 -> .980 | 5.0 -> 5.0 |
| 16 | 12 | P0 x 12 | 12 / 12 | 1515 -> 1515 | .972 -> .972 | 7.0 -> 7.0 |
| 20 | 20 | P0 x 20 | 20 / 20 | 2502 -> 2502 | .894 -> .894 | 40.9 -> 40.9 |
| 21 | 20 | P0 x 20 | 10 / 20 | 3331 -> 3366 | .760 -> .760 | 93.0 -> 93.0 |
| 90 | 26 | P0 x 26 | 26 / 26 | 3317 -> 3317 | .863 -> .863 | 70.1 -> 70.1 |
| 108 | 30 | P0 x 30 | 29 / 30 | 3665 -> 3665 | .884 -> .884 | 66.9 -> 66.9 |

109 / 120 reviews decision-identical. The two divergent cells are the two the P1 record documents as
wall-clock-limited ("cells 21 / 108 are wall-clock-limited; compare at decision level and rerun
before blaming a change"): cell 21 first diverges at review 5 with the same candidate chosen and a
different time-limited period-0 quantity (42.4 against 50.1 units, the exact variability the P1
pass-J record shows for this cell), cell 108 at review 5 where the hedged candidate timed out and
left the feasible set (the P1 two-blocker record shows the same review). Every review of the four
cells that are not wall-clock-limited is identical. Every review of every cell is P0-owned; no P1
class was added; no candidate starved.

### Run 2 (`p0_arm_p2_meio_rerun.json`) - cells 21 and 108 alone on the quiet machine

Recorded in `P2_CLOSEOUT.md` section "P0 isolation" when complete: the same code, the same
settings, the two cells replayed with nothing else running.

## 3. Why the P2 hooks cannot reach a P0-owned review

* `demand_correlation` is 0 on every frozen fixture and cell: the frozen stream is consumed exactly as
  before (bit-identical draws proved by `test_zero_correlation_is_the_frozen_draw_bit_for_bit...`).
* `Transfer.multiple` and `fixed_cost_per_dispatch` are 0: no variable or row is added.
* `incumbent_transfers` is empty and no frozen rule transfers: the incumbent projection is unchanged.
* The network continuation (echelon-demand lots, slabs at fed locations, lane premium, feeds) is
  built only inside the `lot_terminal_valuation` block of a PURCHASING_ECONOMICS-owned review; every
  review of the six cells is PROTECTION_RECOVERY-owned (the cells declare a protection mandate), and
  the P1 fixtures have one location, one source destination and no lane, for which the new code paths
  reduce to the frozen ones by construction (`_continuation_sources` keeps the first declared source
  per destination; `echelon_demand` returns `mu` unchanged without lanes; `lane_premiums` is empty).
* The settlement's flow telemetry reads the state the settlement evolves and writes new keys only;
  the pack check and dispatch fee apply only to lanes that declare them.
* The replay method registry is consulted only for names registered by the P2 baselines.
