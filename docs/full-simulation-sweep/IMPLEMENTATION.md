# Full Synthetic Simulation Sweep — Implementation

## Deliverables

1. Controlled Indiana generator inputs: mean accepted fill, Kendall tau and
   zero-demand product-week rate.
2. Leakage-safe benchmark support for a `SupplyRiskPolicy`, a common cost-ratio
   override, Croston routing diagnostics and correct zero-demand settlement.
3. A reproducible runner for Grid A, Grid B and forced-unit-fill controls.
4. Machine-readable JSON/CSV and a decision report listing every run.
5. Unit, regression, lint and end-to-end verification.

## Output contract

Each run records grid, factor, level, seed, fill target and observed fill,
spot regime, tau, intermittency, cost ratio, scale, training weeks, SP edges
against all baselines, service, gate result, Croston-route count and correlation
diagnostics. Summaries use `statistics.median` and always include ranges,
failure counts and the individual run table.

The headline is the SP-vs-LP edge by mean fill at fixed 1.30x/30% spot. The
report must explicitly test whether the edge decays near 0.99 reliability.

## Guardrails

- Synthetic evidence is never described as validation or realized savings.
- All policies share one settlement function and identical economic inputs.
- Fill fallbacks and supplier shares use training-window observations only.
- `force_unit_fills=True` is diagnostic and cannot pass the gate.
- Correlation value is discussed only from the wired B.1 cells.
- Unexpectedly favorable results trigger regression and invariance checks.
