# Evidence index

- `causal/`: final as-of-causal main experiment, every run and every cell.
- `causal/ablations/`: final paired architecture comparisons, including controls.
- `rejected/`: INVALID developmental information-leaking runs. Audit trail only.
- `service_curve.csv`, `marginal_service.csv`, `service_curve.png`: derived only
  from the final causal stable/cover2 slice; other cells remain in the raw files.
- `competitor_features.csv`:17 vendors ×51 requested features, documented or
  explicitly unverified. Unverified does not mean unavailable.
- `market_inputs.json`: geography definitions and unknown counts, not invented TAM.
- `revenue_sensitivity.csv`, `roi_sensitivity.csv`, `gainshare_sensitivity.csv`:
  clearly conditional arithmetic, not observed sales, benefit or willingness to pay.

Raw percentages use incumbent operating loss, not customer revenue. Fallback
and service breaches are retained. No production/training database is used.
There is one supplier per SKU in this new experiment; supplier-blind policies
therefore have no pro-rata allocation choice. The older Indiana pro-rata rule
is a different benchmark assumption and must not be imported into this result.
