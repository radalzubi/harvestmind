# FMCG closed-loop counterfactuals (SYNTHETIC CALIBRATED)

runs (seeds) 3, run length 40 periods, re-plan every 4, horizon 12, train 52, scenarios 20, opening cover 5.4 wk, warehouse cap 8.0 wk, SLA 0.95

| archetype | SP vs deterministic | win | SP vs order-up-to | SP vs min/max | SP vs naive | SELECTED vs deterministic | service SP / det / OUT | avg inv SP / det / OUT | selections |
|---|---|---|---|---|---|---|---|---|---|
| A_stable | -26.75% | 33% | -28.70% | +22.11% | +30.18% | +6.64% (win 67%) | 99.9% / 98.6% / 100.0% | 47,953 / 20,876 / 37,783 | {'order_up_to': 17, 'deterministic_sp': 13} |
| B_volatile_retail | +32.64% | 100% | -21.79% | +15.73% | +5.53% | +41.58% (win 100%) | 97.3% / 91.0% / 97.8% | 83,422 / 39,990 / 66,939 | {'order_up_to': 20, 'stochastic_sp': 4, 'deterministic_sp': 6} |
| C_constrained_supplier | -5.74% | 33% | -49.99% | +17.70% | -23.31% | +27.98% (win 100%) | 99.3% / 96.2% / 99.4% | 68,124 / 22,557 / 45,267 | {'order_up_to': 24, 'stochastic_sp': 2, 'deterministic_sp': 4} |
| D_importer | +8.58% | 100% | -72.10% | -38.42% | +61.46% | +48.05% (win 100%) | 83.3% / 80.1% / 91.7% | 51,929 / 28,749 / 55,178 | {'order_up_to': 30} |
| E_mixed_portfolio | +11.84% | 100% | -33.90% | +12.79% | +6.35% | +33.67% (win 100%) | 99.4% / 95.8% / 99.7% | 161,026 / 78,552 / 124,534 | {'order_up_to': 28, 'deterministic_sp': 2} |
| F_disruption | +31.59% | 67% | -29.20% | +24.43% | +13.72% | +43.55% (win 100%) | 99.6% / 96.2% / 99.8% | 52,708 / 24,224 / 42,746 | {'order_up_to': 25, 'deterministic_sp': 5} |
