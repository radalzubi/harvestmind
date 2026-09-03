# FMCG counterfactuals (SYNTHETIC CALIBRATED)

seeds 5, folds/seed 6, horizon 12, train 52, scenarios 20, opening cover 5.4 wk, warehouse cap 8.0 wk, SLA 0.95

| archetype | folds | vs deterministic | win | CI95 median | vs order-up-to | vs naive | vs min/max | binding | slack | service SP / det / OUT |
|---|---|---|---|---|---|---|---|---|---|---|
| A_stable | 30 | -13.58% | 0% | [-14.38, -12.41] | -24.32% | +40.17% | -5.79% | +nan% (n=0) | -13.58% (n=30) | 100.0% / 100.0% / 99.9% |
| B_volatile_retail | 30 | -5.82% | 43% | [-23.93, +14.10] | -13.75% | +15.54% | +18.13% | +26.94% (n=18) | -32.74% (n=12) | 99.2% / 96.1% / 97.3% |
| C_constrained_supplier | 30 | -13.76% | 0% | [-14.01, -12.49] | -42.40% | +4.48% | -29.84% | +nan% (n=0) | -13.76% (n=30) | 100.0% / 100.0% / 99.7% |
| D_importer | 30 | -3.13% | 0% | [-3.60, -2.47] | -19.18% | +3.73% | -16.98% | +nan% (n=0) | -3.13% (n=30) | 99.9% / 99.9% / 99.9% |
| E_mixed_portfolio | 30 | -21.23% | 13% | [-23.18, -16.28] | -22.20% | +31.50% | +1.51% | +7.14% (n=4) | -22.17% (n=26) | 99.9% / 99.4% / 99.4% |
| F_disruption | 30 | -18.67% | 7% | [-24.15, -10.41] | -23.03% | +33.90% | +10.06% | +3.40% (n=3) | -19.83% (n=27) | 99.9% / 99.5% / 99.3% |
