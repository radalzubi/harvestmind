# SAFE_SELECTED validation (SYNTHETIC CALIBRATED, frozen design, unseen seeds)

seeds 100,101,102; run 32 periods; re-plan every 4; scenarios 20; gates {'n_folds': 4, 'n_holdout_folds': 2, 'holdout': 4, 'min_history': 26, 'min_rel_improvement': 0.03, 'service_tolerance': 0.01, 'max_regret_share': 0.1, 'confidence': 0.8, 'block_length': 2, 'n_boot': 400}

Deltas are cost reductions vs the INFERRED incumbent (positive = better), median over runs; worst is the worst single run.

| regime | incumbent Δ% (worst) | order_up_to Δ% (worst) | deterministic_sp Δ% (worst) | stochastic_sp Δ% (worst) | anchored_sp Δ% (worst) | safe_selected Δ% (worst) | SAFE fill Δpt | SAFE selections | SKU regimes |
|---|---|---|---|---|---|---|---|---|---|
| calm_deep_cover | +0.0% (+0.0%) | -8.1% (-14.1%) | -7.6% (-67.1%) | -25.1% (-34.4%) | -18.4% (-36.4%) | +2.1% (-1.0%) | -0.06 | {'incumbent': 12, 'deterministic_sp': 9, 'order_up_to': 1, 'stochastic_sp': 2} | {'CALM': 23, 'PROMOTION': 1} |
| calm_thin_cover | +0.0% (+0.0%) | -3.2% (-3.8%) | +2.6% (-4.2%) | +0.1% (-9.6%) | -21.5% (-29.0%) | +0.9% (+0.8%) | -0.40 | {'incumbent': 13, 'deterministic_sp': 9, 'order_up_to': 1, 'stochastic_sp': 1} | {'CALM': 23, 'PROMOTION': 1} |
| volatile | +0.0% (+0.0%) | -5.8% (-6.3%) | -48.1% (-143.1%) | -53.1% (-67.8%) | -16.4% (-28.9%) | +0.2% (+0.0%) | -0.01 | {'incumbent': 22, 'order_up_to': 2} | {'SUPPLY_CONSTRAINED': 3, 'VOLATILE_DEMAND': 13, 'CALM': 2, 'PROMOTION': 6} |
| constrained | +0.0% (+0.0%) | -2.1% (-5.6%) | -16.3% (-24.3%) | -20.1% (-33.4%) | -20.9% (-28.2%) | +0.0% (+0.0%) | +0.00 | {'incumbent': 23, 'deterministic_sp': 1} | {'PROMOTION': 6, 'CALM': 6, 'SUPPLY_CONSTRAINED': 8, 'VOLATILE_DEMAND': 1, 'RECOVERY': 3} |
| importer | +0.0% (+0.0%) | -0.7% (-2.6%) | -4.7% (-14.1%) | -13.1% (-22.2%) | +0.0% (-21.6%) | +0.0% (+0.0%) | +0.00 | {'incumbent': 24} | {'PROMOTION': 6, 'CALM': 11, 'SUPPLY_CONSTRAINED': 6, 'VOLATILE_DEMAND': 1} |
| mixed | +0.0% (+0.0%) | -12.4% (-12.7%) | -41.6% (-67.8%) | -43.8% (-52.5%) | -34.4% (-42.5%) | +0.1% (-27.6%) | -0.40 | {'incumbent': 21, 'deterministic_sp': 3} | {'PROMOTION': 6, 'CALM': 16, 'VOLATILE_DEMAND': 2} |
| disruption | +0.0% (+0.0%) | -8.0% (-12.1%) | -34.5% (-40.8%) | -46.8% (-54.3%) | -39.1% (-60.9%) | +0.6% (+0.2%) | +0.04 | {'incumbent': 20, 'deterministic_sp': 1, 'order_up_to': 2, 'stochastic_sp': 1} | {'PROMOTION': 6, 'CALM': 18} |
| calm_high_carry | +0.0% (+0.0%) | -11.3% (-14.9%) | +62.2% (+53.6%) | +58.9% (+49.5%) | +22.3% (-13.0%) | +13.7% (+2.5%) | -0.03 | {'incumbent': 10, 'deterministic_sp': 8, 'stochastic_sp': 3, 'order_up_to': 3} | {'CALM': 23, 'PROMOTION': 1} |
| volatile_high_carry | +0.0% (+0.0%) | -12.6% (-19.1%) | -14.7% (-21.9%) | -46.1% (-48.2%) | -18.2% (-34.2%) | -3.4% (-4.4%) | +0.04 | {'incumbent': 21, 'deterministic_sp': 2, 'order_up_to': 1} | {'SUPPLY_CONSTRAINED': 3, 'VOLATILE_DEMAND': 13, 'CALM': 2, 'PROMOTION': 6} |
