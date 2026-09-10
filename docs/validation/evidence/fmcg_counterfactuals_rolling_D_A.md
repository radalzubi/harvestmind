# FMCG closed-loop counterfactuals (SYNTHETIC CALIBRATED)

runs (seeds) 3, run length 40 periods, re-plan every 4, horizon 12, train 52, scenarios 20, opening cover 5.4 wk, warehouse cap 8.0 wk, SLA 0.95

| archetype | SP vs deterministic | win | SP vs order-up-to | SP vs min/max | SP vs naive | SELECTED vs deterministic | service SP / det / OUT | avg inv SP / det / OUT | selections |
|---|---|---|---|---|---|---|---|---|---|
| D_importer | +0.00% | 0% | +0.00% | +19.57% | +77.61% | +0.00% (win 0%) | 91.7% / 91.7% / 91.7% | 55,178 / 55,178 / 55,178 | {'order_up_to': 30} |
| A_stable | +7.27% | 100% | +0.33% | +40.60% | +44.16% | +6.96% (win 100%) | 99.9% / 99.7% / 100.0% | 36,877 / 36,786 / 37,783 | {'order_up_to': 30} |
