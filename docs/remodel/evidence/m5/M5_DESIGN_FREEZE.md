# M5 evaluation design, frozen before the holdout runs

Recorded before any holdout result was read. Code commits: Experiment A frozen at `91445b1` (E1 and E2 included),
Experiment B at `70c10db`. Selection manifest hash `8b6067be83a4…` (50 series, training-only features before
2016-01-02). Declaration hashes are in each run manifest.

## 1. Selection (declared)

`zaad/public/m5/selection.py`: eligibility = listed every Walmart week from 2015-01-03 to 2016-05-20, mean weekly
sales ≥ 2 in the 52 weeks before 2016-01-02, no run of ≥ 8 zero weeks; strata = category × volume tercile ×
volatility (CV ≥ 0.5) × intermittency (zero weeks ≥ 10 %); proportional allocation with a seat for strata ≥ 50
series; seeded draw (20261019) preferring unseen stores and departments. 16,624 eligible of 30,490.

## 2. Chronological windows (declared)

| window | origin (Saturday) | reviews | mode | truth weeks | role |
|---|---|---|---|---|---|
| val1 | 2014-08-02 | 13 | rolling, 8-week horizon | 20 (to 2014-12-19) | internal validation |
| val2 | 2015-01-31 | 13 | rolling, 8-week horizon | 20 (to 2015-06-19) | internal validation |
| final | 2016-01-02 | 13 | rolling, 8-week horizon | 20 (to 2016-05-20) | holdout |

Tuning uses val1 and val2 only. The holdout's last reviews' horizons overlap the public Kaggle evaluation period
(d_1914..d_1941); those labels never informed development and the holdout is otherwise untouched by the pilot.
A series without 52 weeks of history or a knowable price at a validation origin is a recorded BUILD_FAILED run, not
a silent exclusion.

## 3. Assumptions (declared, SYNTHETIC)

Experiment A (`m5-declaration-1`): weekly periods, 8-week horizon, 52-week history, 3 planner worlds, 20 s solve
budget; margin 30 % (cost = 0.7 × observed price); holding 25 %/yr + capital 10 %/yr as weekly rates; salvage 0.8;
shelf life 26 weeks; opening stock 2 weeks of mean demand; service target 0.95; finite line cap 20 × mean weekly;
continuous order quantities; supply scenarios stable (14 d, no spread, full fill), uncertain (14 ± 7 d, fill
0.9 ± 0.1), lead_only, fill_only, mild_lead (14 ± 3 d, under the weekly half-period slack). ZAAD's declared
incumbent rule: reorder_point. Predeclared variants: `corrected` (primary), `no_incumbent`, `target_90`, `cash_4w`
(four weeks of purchases, no credit), `holding_x2`.

Experiment B (`m5-coupled-declaration-1`): per-store groups of the selected items (≤ 6, ≥ 2 usable at the origin),
one supplier: fixed order cost $40 per order-week, minimum order value 0.5 week of group purchases, pallet cap 6
pallets per order-week with pallet sizes of 1.5 weeks of each item's mean demand in whole cases, case multiple 6,
minimum 2 cases per line, no cash budget. ZAAD's incumbent rule: economic_lot. Variants: `coupled_tight` (4 pallets,
MOV 1 week; the rule projections are known to breach their own MOV when both bind), `coupled_cash` (4 weeks of cash
plus a 1-week credit line), `coupled_no_incumbent`; the variants run on the holdout window only. Supply scenarios
stable, mild_lead, fill_only.

## 4. Policies (frozen)

A: `gated` (production planner), `reorder_point`, `periodic:1`, `base_stock`, `order_up_to`. B: `gated`,
`economic_lot`, `reorder_point`, `periodic:1`. The baselines never receive the incumbent rule; all share the fits,
the truth and the declaration. Baseline z comes from the target (0.95 → 1.645). No parameter is tuned on results.

## 5. Primary outcomes and criteria (predefined)

Primary: per-series paired difference ZAAD minus `reorder_point` in **continuation cost** on the holdout window,
per supply scenario, with the 95 % series bootstrap; secondary: unit fill, inventory, orders placed, completion,
decision provenance (own / retained / abstained), runtime; realized cost beside continuation.

- **Success (for a scenario):** ZAAD's mean paired continuation cost is lower with the 95 % interval excluding zero,
  and its mean fill is not lower than the baseline's by more than 0.01.
- **Failure:** ZAAD's mean paired cost is higher with the interval excluding zero, or its fill is lower by more than
  0.01 with cost not lower.
- **Inconclusive:** the interval includes zero.
- **Operational reading:** a success in `stable` and `mild_lead` would show value from the planner's own candidates;
  a success only under `uncertain` with the PROTECT regime active would show value from protection, which carries
  inventory; a failure in `stable` with retained-incumbent share near one means the planner mostly re-issued the
  rule and added runtime without decisions.
- **Experiment B:** same metrics at group level plus items below target, order-weeks, lines per order-week, constraint
  breaches (physical failures) per policy; ZAAD's advantage, if any, must come with no more breaches than the rules.

## 6. What is not decided by this run

Supplier behaviour, procurement cost, demand under stockout, and anything about Walmart's own replenishment. The
holdout verdict is one period of one retailer's sales under declared supply; the GO / CONDITIONAL / NO-GO judgement
in the final report weighs it together with the corrected FreshRetailNet re-run.

## 7. Post-freeze corrections (recorded as they happened, 2026-10-19)

The first runs on the frozen code exposed defects that had to be fixed before any result could be read; each is a
structural finding (a crash or a constraint breach), not a reading of the holdout. Original partial or complete runs are
preserved under their commit hash; the corrected runs replace them for the comparison.

| change | commit | why | effect on the frozen design |
|---|---|---|---|
| E3 joint, legal rule projections | a3dd082 | the rule baselines breached pack, load and MOV constraints in settlement and ZAAD's incumbent projection was infeasible on the same groups (register finding 15) | Experiment B re-run on the fixed code; `coupled_run1_prefix_70c10db` (212 rows) kept as the record of the breaches. Experiment A requests carry no such terms: no effect (tested) |
| E4 cash residue snap, E5 ledger key | de31828 | two replay crashes on the cash variant (findings 16, 17) | `cash_4w` re-run; other Experiment A variants keep their run-1 rows, where the only affected rows are the 25 EXCEPTION rows of one zero-history series at val2, which the fix would turn into BUILD_FAILED rows |
| zero-sales history is a recorded BUILD_FAILED | de31828 | an item not yet launched at an origin has nothing to plan | same exclusion class as the declared short-history and unpriced cases |
| `cash_4w_revenue` variant | a391e99 | the frozen cash variant is a liquidation (finding 18) | added, labelled post-freeze; `cash_4w` still run and reported |

The run manifests record the commit at completion; the Experiment A variants `corrected`, `no_incumbent`, `target_90`
and `holding_x2` were started at `ae1b73c` (before E3–E5) and their results are identical to what the later code
produces for every row except the zero-history series noted above, because E3 is a no-op without lot, MOV, load or
cash terms and E4/E5 only act where a cash budget or an empty ledger exists.
