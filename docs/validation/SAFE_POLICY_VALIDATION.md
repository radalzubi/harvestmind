# SAFE_SELECTED validation

**Classification: SYNTHETIC CALIBRATED.** Every number below is written by `scripts/fill_safe_validation_doc.py` from `artifacts/safe_policy_validation.json`, produced by `scripts/run_safe_policy_validation.py`. Nothing here is a realised saving; no real operator's data has been evaluated.

## Question

Does SAFE_SELECTED avoid the standalone stochastic optimizer's easy-period downside while retaining its value when conditions bind?

## Methodology

- Frozen design: gates `{'n_folds': 4, 'n_holdout_folds': 2, 'holdout': 4, 'min_history': 26, 'min_rel_improvement': 0.03, 'service_tolerance': 0.01, 'max_regret_share': 0.1, 'confidence': 0.8, 'block_length': 2, 'n_boot': 400}`, scenarios 20, review 4, horizon 12, train 52, run 32 periods, evaluation seeds [100, 101, 102] (never used while building or tuning). Elapsed 748.4 s.
- Closed loop: every policy re-plans every review period with its own state on identical realised paths through one settlement; supplier capacity binds every policy.
- The incumbent is INFERRED from the simulated operator's own PO log and is the reference for every delta.
- Leakage: each inner selection fold trains on history strictly before its origin (demand AND recorded supplier events) and is scored on what followed; hold-out folds are used only to confirm a winner (`tests/unit/test_safe_selector.py`).
- No fold or run is filtered on its outcome. Strata are reported, never removed.
- Inference within the selector is a moving-block bootstrap over overlapping folds.

## Results by regime

Δ% = (incumbent cost − policy cost) / incumbent cost, median over runs; (worst) = worst single run. Positive is better than the incumbent.

| regime | archetype | cover wk | carry/wk | incumbent Δ% (worst) | order_up_to Δ% (worst) | deterministic_sp Δ% (worst) | stochastic_sp Δ% (worst) | anchored_sp Δ% (worst) | safe_selected Δ% (worst) | SAFE fill Δpt | SAFE avg inv / incumbent | SAFE plan change | SAFE selections |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| calm_deep_cover | A_stable | 5.4 | 0.0046 | +0.0% (+0.0%) | -8.1% (-14.1%) | -7.6% (-67.1%) | -25.1% (-34.4%) | -18.4% (-36.4%) | +2.1% (-1.0%) | -0.06 | 0.98 | 0.20 | {'incumbent': 12, 'deterministic_sp': 9, 'order_up_to': 1, 'stochastic_sp': 2} |
| calm_thin_cover | A_stable | 0.5 | 0.0046 | +0.0% (+0.0%) | -3.2% (-3.8%) | +2.6% (-4.2%) | +0.1% (-9.6%) | -21.5% (-29.0%) | +0.9% (+0.8%) | -0.40 | 0.81 | 0.22 | {'incumbent': 13, 'deterministic_sp': 9, 'order_up_to': 1, 'stochastic_sp': 1} |
| volatile | B_volatile_retail | 2.0 | 0.0046 | +0.0% (+0.0%) | -5.8% (-6.3%) | -48.1% (-143.1%) | -53.1% (-67.8%) | -16.4% (-28.9%) | +0.2% (+0.0%) | -0.01 | 1.00 | 0.40 | {'incumbent': 22, 'order_up_to': 2} |
| constrained | C_constrained_supplier | 2.0 | 0.0046 | +0.0% (+0.0%) | -2.1% (-5.6%) | -16.3% (-24.3%) | -20.1% (-33.4%) | -20.9% (-28.2%) | +0.0% (+0.0%) | +0.00 | 0.99 | 0.25 | {'incumbent': 23, 'deterministic_sp': 1} |
| importer | D_importer | 3.0 | 0.0046 | +0.0% (+0.0%) | -0.7% (-2.6%) | -4.7% (-14.1%) | -13.1% (-22.2%) | +0.0% (-21.6%) | +0.0% (+0.0%) | +0.00 | 1.00 | 0.53 | {'incumbent': 24} |
| mixed | E_mixed_portfolio | 2.0 | 0.0046 | +0.0% (+0.0%) | -12.4% (-12.7%) | -41.6% (-67.8%) | -43.8% (-52.5%) | -34.4% (-42.5%) | +0.1% (-27.6%) | -0.40 | 0.96 | 0.25 | {'incumbent': 21, 'deterministic_sp': 3} |
| disruption | F_disruption | 2.0 | 0.0046 | +0.0% (+0.0%) | -8.0% (-12.1%) | -34.5% (-40.8%) | -46.8% (-54.3%) | -39.1% (-60.9%) | +0.6% (+0.2%) | +0.04 | 1.01 | 0.23 | {'incumbent': 20, 'deterministic_sp': 1, 'order_up_to': 2, 'stochastic_sp': 1} |
| calm_high_carry | A_stable | 2.0 | 0.0460 | +0.0% (+0.0%) | -11.3% (-14.9%) | +62.2% (+53.6%) | +58.9% (+49.5%) | +22.3% (-13.0%) | +13.7% (+2.5%) | -0.03 | 0.88 | 0.19 | {'incumbent': 10, 'deterministic_sp': 8, 'stochastic_sp': 3, 'order_up_to': 3} |
| volatile_high_carry | B_volatile_retail | 2.0 | 0.0460 | +0.0% (+0.0%) | -12.6% (-19.1%) | -14.7% (-21.9%) | -46.1% (-48.2%) | -18.2% (-34.2%) | -3.4% (-4.4%) | +0.04 | 1.03 | 0.45 | {'incumbent': 21, 'deterministic_sp': 2, 'order_up_to': 1} |

## Strata

| stratum | regimes | SP median Δ% | SP worst | SAFE median Δ% | SAFE worst | anchored median Δ% |
|---|---|---|---|---|---|---|
| easy/slack | calm_deep_cover | -25.1% | -34.4% | +2.1% | -1.0% | -18.4% |
| stable | calm_deep_cover, calm_thin_cover, calm_high_carry | +11.3% | -34.4% | +5.6% | -1.0% | -5.9% |
| volatile | volatile, volatile_high_carry, mixed | -47.7% | -67.8% | -1.0% | -27.6% | -23.0% |
| binding | calm_thin_cover, constrained, importer | -11.0% | -33.4% | +0.3% | +0.0% | -14.2% |
| disruption | disruption | -46.8% | -54.3% | +0.6% | +0.2% | -39.1% |
| low carry cost | calm_deep_cover, calm_thin_cover, volatile, constrained, importer, mixed, disruption | -28.8% | -67.8% | +0.6% | -27.6% | -21.5% |
| high carry cost | calm_high_carry, volatile_high_carry | +6.4% | -48.2% | +5.1% | -4.4% | +2.1% |

## Mode-selection frequency (SAFE_SELECTED, all regimes)

| mode run | re-plans |
|---|---|
| incumbent | 166 |
| deterministic_sp | 33 |
| order_up_to | 10 |
| stochastic_sp | 7 |

## Reading the result

- The desired behaviour is not 'stochastic always wins'. In easy/slack regimes SAFE_SELECTED should stay close to or choose the incumbent; where uncertainty has economic value it may activate a candidate. Judge it by the SAFE worst-run column against the stochastic worst-run column.
- Negative SAFE medians in any regime are reported as they are. They mean the gate let a candidate through that then lost, or that the incumbent inferred from the PO log is a stronger policy than any candidate at this carrying cost — both are findings.
- The incumbent here is the simulator's own order-up-to with safety stock, a competent planner. A real operator's incumbent may be weaker or stronger; that is what the first real-operator backtest measures.
