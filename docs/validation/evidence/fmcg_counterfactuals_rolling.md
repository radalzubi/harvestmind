# FMCG closed-loop counterfactuals (SYNTHETIC CALIBRATED)

runs (seeds) 3, run length 40 periods, re-plan every 4, horizon 12, train 52, scenarios 20, opening cover 5.4 wk, warehouse cap 8.0 wk, SLA 0.95

| archetype | SP vs deterministic | win | SP vs order-up-to | SP vs min/max | SP vs naive | SELECTED vs deterministic | service SP / det / OUT | avg inv SP / det / OUT | selections |
|---|---|---|---|---|---|---|---|---|---|
| A_stable | -30.99% | 0% | -29.92% | +21.33% | +30.78% | -3.46% (win 33%) | 99.9% / 98.7% / 100.0% | 48,576 / 21,629 / 37,968 | {'order_up_to': 20, 'deterministic_sp': 10} |
| B_volatile_retail | +13.79% | 100% | -14.14% | +20.78% | +6.74% | +34.68% (win 100%) | 98.2% / 93.4% / 98.0% | 95,297 / 46,296 / 69,462 | {'order_up_to': 19, 'stochastic_sp': 4, 'deterministic_sp': 7} |
| C_constrained_supplier | -36.32% | 0% | -38.86% | +19.54% | -14.93% | +6.65% (win 100%) | 99.5% / 97.1% / 99.3% | 69,653 / 24,905 / 45,601 | {'order_up_to': 25, 'deterministic_sp': 3, 'stochastic_sp': 2} |
| D_importer | -7.10% | 0% | -42.03% | -18.42% | +70.16% | +24.43% (win 100%) | 88.0% / 87.3% / 91.7% | 69,001 / 43,211 / 55,748 | {'order_up_to': 30} |
| E_mixed_portfolio | +9.44% | 100% | -32.91% | +11.43% | +7.49% | +31.59% (win 100%) | 99.5% / 96.1% / 99.7% | 164,720 / 81,247 / 125,921 | {'order_up_to': 28, 'deterministic_sp': 2} |
| F_disruption | +14.17% | 67% | -27.03% | +17.81% | +16.73% | +31.61% (win 100%) | 99.7% / 97.2% / 99.8% | 56,272 / 26,577 / 43,590 | {'order_up_to': 21, 'deterministic_sp': 9} |
