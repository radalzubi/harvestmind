# FreshRetailNet re-run: original pilot, corrected benchmark and predeclared variants

Scope. The same 50 series, three windows (val1, val2 rolling with a 7-day horizon; the final public week in legacy mode),
two demand tracks (observed sales, recovered demand) and the same seeded supply draws as PR #114's pilot. Six
configurations ran on the corrected code (`frn-declaration-2`, commits dd9282f…257dcff): `reference_v1` (finite line
caps, no incumbent rule), `corrected` (primary: finite caps plus the declared `reorder_point` incumbent), `target_90`,
`target_85`, `holding_x4`, `margin_x2`. Every figure is a modelled index in normalized units under declared SYNTHETIC
supply; nothing is a realized saving. Full tables: `RESULTS_fifty_<variant>.md`, `FRN_COMPARISON.md` (within-stage and
cross-stage pairings); the original stays in `RESULTS_fifty.md`.

## 1. What the corrections did (original → reference_v1 → corrected)

| | original (PR #114) | reference_v1 | corrected |
|---|---|---|---|
| ZAAD completion | 436 / 900 (464 abstentions) | 1,200 / 1,200 (0 abstentions) | 1,200 / 1,200 |
| base_stock / order_up_to completion | 447 / 900, 642 / 900 (INFEASIBLE) | 1,200 / 1,200 each | 1,200 / 1,200 each |
| planner history length | grew to 76 observations | capped at 63 | capped at 63 |
| `seasonal_naive` selected | 197 reviews | never (E1) | never (E1) |
| ZAAD's cost on the series the original completed (final, observed, stable; later minus earlier) | — | +0.005 [−0.017, +0.032], 35 series | — |

Every abstention and every INFEASIBLE baseline in the original came from the 1e6 line-capacity sentinel entering the
undeclared-storage big-M (register finding 3): with finite caps there is not one abstention or infeasible solve in 7,200
runs across the six configurations. On the series the original did complete, ZAAD's own cost is unchanged within noise
(cross-stage pairing, every cell's 95 % interval includes zero), so the original's within-series readings were not
wrong; its completion subset was.

The declared incumbent rule (reference_v1 → corrected) is not free: on the holdout week ZAAD's own cost rises by
+0.036 [+0.008, +0.075] under stable supply and +0.083 [+0.012, +0.192] under lead spread, with fill lower by 0.006
and 0.016, because the planner now retains the operator's reorder point on 70–89 % of reviews (own-candidate share
0.11 stable, 0.30–0.34 under uncertainty) instead of running its own protection. On the validation windows the
incumbent helps under combined uncertainty (val1 `uncertain` −0.92 [−1.92, −0.26]) by stopping the planner from
over-protecting. Neither direction is large relative to the cost level (≈ 10–27 per series-window).

## 2. Corrected benchmark: ZAAD against the projected reorder point (paired, continuation cost)

Holdout week (final, observed sales; 50 series each; negative favours ZAAD):

| scenario | ZAAD | reorder_point | paired mean | 95 % | better / worse | ZAAD fill − rule fill | ZAAD own share |
|---|---|---|---|---|---|---|---|
| stable | 10.214 | 10.214 | +0.001 | [−0.008, +0.011] | 16 / 7 (27 ties) | +0.000 | 0.11 |
| uncertain_lead_only | 10.853 | 10.891 | −0.038 | [−0.082, −0.003] | 33 / 11 | +0.008 | 0.32 |
| uncertain_fill_only | 11.348 | 11.487 | −0.139 | [−0.491, +0.094] | 25 / 21 | +0.004 | 0.34 |
| uncertain | 12.124 | 12.173 | −0.049 | [−0.217, +0.083] | 25 / 21 | +0.006 | 0.30 |

Validation windows (observed track): stable −0.017 and −0.012 (intervals touch zero); `uncertain_lead_only` −0.058 and
−0.117 (intervals include zero); `uncertain_fill_only` +0.467 [+0.085, +0.958] in val1 (ZAAD worse) and +0.139 in
val2; `uncertain` −0.057 (val1) and +0.329 [+0.037, +0.694] (val2, ZAAD worse). The recovered-demand track reads the
same way with wider intervals (`RESULTS_fifty_corrected.md`).

Reading. On daily periods with the operator's reorder point declared, ZAAD mostly re-issues that rule under stable
supply (ties on 27 of 50 series) and adds nothing measurable. Under lead-time spread it is slightly cheaper with
higher fill, consistently across windows, through the PROTECT regime (finding 7: the half-period slack classes a
one-day spread as frequent lateness). Under fill variability and combined uncertainty the sign flips between windows,
and the two cells where the interval excludes zero on the validation windows are against ZAAD, with the inventory it
carries (1.3–1.5× the rule's average units) not paying back on a 7-day horizon.

## 3. Predeclared variants (holdout week, observed, paired against the rule at the same declaration)

| variant | stable | uncertain_lead_only | uncertain_fill_only | uncertain |
|---|---|---|---|---|
| corrected (target .95) | +0.001 | −0.038 [−0.082, −0.003] | −0.139 | −0.049 |
| target_90 | +0.001 | −0.048 [−0.108, +0.003] | −0.210 [−0.542, +0.015] | −0.006 |
| target_85 (rules use z for .90) | +0.003 | −0.049 | −0.270 [−0.603, −0.040] | +0.101 |
| holding_x4 | +0.003 | −0.058 [−0.124, −0.007] | −0.164 | −0.039 |
| margin_x2 | +0.002 | −0.097 [−0.201, −0.013] | −0.110 | +0.001 |

The target and economics do not change the picture: stable is a tie at every target, lead spread favours ZAAD by a few
hundredths, fill variability is noisy, and combined uncertainty is a wash. The lower targets mostly lower both policies'
fill together (0.978 → 0.960 at `stable`).

## 4. What this re-run settles and what it does not

Settled: the original's 52 % abstention rate was a benchmark artifact, not a planner property; the corrected benchmark
has full completion for every policy; the service-target and economics sensitivities do not reverse any reading. Not
settled by FreshRetailNet: whether the planner's protection pays on daily periods, because the lateness slack
calibration (finding 7) is an owner decision and because 7-day windows end inside the inventory cycle the protection
builds (the continuation cost already credits that stock at asset value). The weekly-period test on Walmart M5
(`../m5/M5_RESULTS.md`) is where the planner runs on its own calibration.
