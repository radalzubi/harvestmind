# ZAAD preregistered evaluation protocol

## Frozen experiment

`scripts/run_zaad_benchmark.py --freeze` recorded a source/config SHA-256 before final future outcomes were generated. The frozen source covers every `zaad/*.py` file plus the benchmark script. The actual command then ran `--stage holdout` without a limit, using seeds9101–9105. Existing output cannot be overwritten. No source or threshold changes followed the final run. Preliminary development was only two normal cells, seed8101, retained in `evidence/development_*`; it is not final evidence.

75 cells:40 normal service-target×inventory-cover factorial;15 one-factor demand/supply/economics/scale/criticality/perishability/misallocation cells;12 disruption/false-alarm/recovery cells;7 synthetic feed-ablation contracts;1 force-unit-fill control. Eight methods per cell and five seeds yield3,000 rows. They share375 distinct operator/path cases and cannot be counted as3,000 independent operators. There are two SKUs, four source routes, one DC,12 weekly future reviews and24 training/model scenarios per stage. This is deliberately bounded, not the full all-factor enterprise matrix. Scale cases are0.4× and3× base units, not audited $6M/$15M/$50M operators.

Every run stores seed, cell, parameters, selected policy, gate status, cost components, service per SKU, inventory assets, churn, capacity breaches, forecast method, fingerprint and fallback flag. Missing/failed cases would stop the run visibly; the actual artifact contains all expected rows, no silently dropped negatives.

## Equal information and physics

Every method has training-only demand/deliveries, the same known stock and expected dated pipeline, quoted capacities, packs, budgets, costs and target. Every method uses `zaad.engine.settle`. Forecast selection uses only chronological training observations. First-review action has no current demand or future actual arrival information. No allocator may order above supplier/route/shared-edge capacity. Existing pending POs remain visible. Actual generated future demand/fill/lead is passed only after method selection and confirmation.

The benchmark incumbent is fill-aware inventory-position replenishment, not the earlier mean-demand LP strawman. Base-stock is a simpler fill-aware1σ rule. Service-target, deterministic mean-path, expected-cost, CVaR and route-aware comparisons search the same finite policy family. Some return incumbent when their candidate set is infeasible; the output flags this and does not count it as an algorithm win. It is not a vendor benchmark or legacy-SP rerun.

## Independent truth and limits

Final demand is independently sampled around known synthetic generating means, not resampled planner residuals. Future supply is independently generated too. Final disruption deliberately has longer delay/deeper fill loss than the planning stress assumptions. Some cases include unannounced promotion/structural demand increases; they test misspecification, not a promotion-informed optimizer. In-transit initial POs are fixed expected receipts; open-PO stochastic ETA is not under test.

Known final synthetic recovery appears at review7 in the runtime-visible card timeline, not in the first decision. Replenishment rules update quantities against realized stock and observed receipts, but the selected rule/forecast is fixed over the replay. Full re-estimation/reselection at every review and inference from raw real-time feeds remain future work. Synthetic feed labels port/AIS/freight/weather currently map to the same supplied severity; these are negative/positive wiring controls, not provider-specific feature ablations or predictive validation.

## Reading results

Use `statistics.median`, ranges, losing-case counts, service failures and abstentions. A savings percentage denominator is the modeled12-week economic cost, not throughput, annual spend, or total customer revenue. No stock-release dollar is counted as recurring revenue. Profit share requires audited recurring avoided costs at agreed service and a credible incumbent counterfactual.

`scripts/summarize_zaad_benchmark.py` validates3000 unique rows, reports all families/baselines, decomposes every losing row into cost components, and recreates selected traces only after asserting exact equality to the frozen stored costs. That is descriptive analysis, not retuning. The failure taxonomy in the first run is intentionally conservative; decomposition is not causal proof.

## Reproduction without overwriting evidence

In a new temporary checkout, retain the saved manifest and direct generated evidence to a separately reviewed output path by an explicit reporting-only change, or copy existing output files to an archival directory before rerunning. Do not overwrite old results or present a retuned run as the same untouched holdout. The committed scripts intentionally refuse existing primary result paths. A same-source trace replay is already included in the summary script and verifies exact saved costs.

Next experiment must fix the model using development data, then preregister **new** final seeds and permissioned historical/prospective operator observations. The current final holdout is consumed and cannot become tuning data followed by a 'fresh' claim on the same seeds.
