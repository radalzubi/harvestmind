# FreshRetailNet-50K pilot: first comparative replay on public observed demand

Status: pilot complete on 50 stratified series (2026-10-19). Everything in this note is a modelled comparison of
replenishment policies on public observed retail demand under DECLARED synthetic supply and normalized-unit
economics. No figure is a realized saving, a customer outcome or operator validation. The dataset audit that
preceded this run is `docs/remodel/FRESHRETAILNET_ASSESSMENT.md`.

## 1. What was built

All new code lives under `zaad/public/freshretailnet/` plus two scripts and one test file. No production module,
migration, route, workspace adapter, staging table or optimizer file was changed.

| piece | file | role |
|---|---|---|
| loader | `zaad/public/freshretailnet/loader.py` | reconciles both Parquet files against the audited SHA-256/size/row manifest, refuses anything else, loads `frn_daily` (4.85 M rows) and `frn_hourly` (108 M rows) into a dedicated DuckDB file (git-ignored), re-checks the two audited invariants on every row |
| selection | `selection.py` | deterministic stratified sample of 50 training-only series; manifest `docs/remodel/evidence/frn/SELECTION_MANIFEST.json` |
| declaration | `declaration.py` | every SYNTHETIC input, versioned and hashed; manifest `docs/remodel/evidence/frn/ASSUMPTIONS.json` |
| recovery | `recovery.py` | track B latent-demand estimate from the pre-origin in-stock hourly profile (DERIVED) |
| request builder | `request_builder.py` | one series at one origin as a daily-period `Request` on the core contract |
| truth | `truth.py` | settlement demand from the dataset, supply drawn once per series/window/scenario through the planner's own `worlds.draw`, shared by both tracks |
| runner | `scripts/frn_pilot.py` | sequential replay of every (series, window, track, scenario, policy); one JSON line per run including failures; run manifest with commit, hashes, environment |
| summary | `scripts/frn_summarize.py` | policy tables, series-level paired bootstrap, strata, failure analysis |
| tests | `tests/unit/test_frn_pilot.py` | 13 integrity tests (section 6) |

## 2. Daily-period audit (the gate before building)

The workspace adapter plans weekly and needs 16 weeks; the dataset has 90 days. The core contract accepts
`period_days = 1`. An exhaustive sweep of the frozen core established:

- **Period-agnostic and therefore correct on daily periods:** date-to-period mapping (`worlds.dates`: with an
  all-days calendar and `as_of` at 00:00 UTC, a 1-day lead ordered in period t arrives in t+1, a 2-day lead in t+2;
  verified in `test_daily_request_units_and_knowledge_boundary`); arrivals and fills; per-period holding, capital
  and interest accrual (no `/52` or `/7` anywhere in the ledger); shelf life and expiry as period indices, decremented
  once per review; settlement conservation; the replay loop itself (advances `as_of` by `period_days`); net-day
  payments (`ceil(net_days / period_days)`); lead-time spread (`lead_sd_days / period_days`).
- **Weekly-tuned statistics that act on days here, left as they are and applied identically to every policy:** the
  estimator's observation windows (16 minimum, 26 base window, 12 scoring, 4 recent-level, 13 moving average),
  change-point thresholds, young-regime and residual windows. On daily data these are 1 to 4 weeks of days. The
  baselines consume the same fits, so no policy is advantaged.
- **One candidate that would be wrong on daily data, avoided by a declared history cap:** `seasonal_naive` uses a
  52-observation lag (annual on weekly data, 52 days here) and is enabled only above 68 observations. The declaration
  caps the planner's history at 63 days so it can never be enabled; this removes at most 27 of the 90 days from the
  final-window history and is recorded as an assumption.
- **One state rule whose meaning changes, kept and reported as a finding:** the engine treats an arrival more than
  half a period after the declared lead as late. With daily periods, a one-day lead spread makes about 31 % of
  arrivals "late", which activates the supply-risk state and the protection regime for every SKU in the `uncertain`
  scenario. This is not a bug in the arithmetic; it is a weekly-calibrated threshold meeting daily periods. The
  `uncertain_fill_only` scenario (same fill uncertainty, no lead spread) isolates its effect, and the results show it.
- **Not usable and not used:** `zaad.full.historical` (weekly-only, Monday origins). The pilot drives
  `zaad.full.replay.replay` directly.
- **Cosmetic:** `evaluation.endpoint` labels a periods quantity `weeks_to_consume_terminal`.

Hard gate verdict: daily planning is consistent in the physical and financial core without changing the
optimizer's mathematics or weakening any control. The weekly-tuned statistics and the lateness threshold are
reported, not patched. Weekly costs were never reinterpreted as daily costs: every per-period rate in the declaration
is derived from an annual assumption divided by 365.

## 3. Data and provenance

- Files: `train.parquet` (106,436,287 bytes, sha256 `6706832d…`), `eval.parquet` (8,440,124 bytes, sha256
  `1b118840…`), both verified before loading; the loader refuses any other file. Source files are untouched and
  outside git; the DuckDB derivative is git-ignored.
- Evidence classes applied throughout: OBSERVED (daily and hourly sales, hourly stock flags, calendar, discount,
  activity, weather); DERIVED (selection features, mean training demand, recovered demand, the recovery profile);
  SYNTHETIC (opening stock, lead time and spread, fill, costs, prices, holding and capital rates, shelf life, service
  target, the stress); UNAVAILABLE (prices, costs, units, purchase orders, receipts, suppliers, inventory, network).
- Knowledge rule (declared): a day's observations are knowable at 23:59:59 UTC of that day. Requests hold only
  days strictly before the origin; the contract rejects any later stamp; a test perturbs post-origin rows and shows
  the request bytes do not change.
- The historical stockout flags are the retailer's, under the retailer's policy. They enter only the selection
  strata and the track-B recovery estimate. Every policy's shortages and stockouts are its own, produced by the
  settlement from its own stock and orders. Simulated purchase orders are created by the replay and labelled as such;
  none is an observed record.

## 4. Series selection (frozen before any policy ran)

50 series from the 50,000, using the 90 training days only (the evaluation week was not read; a test tampers with
it and shows the selection hash does not move). Strata: volume tercile × stockout exposure (rare < 25 % of days,
occasional, frequent ≥ 50 %) × regularity (intermittent ≥ 25 % zero days, volatile CV ≥ 0.6, smooth) × promotion
exposure (≥ 60 % discounted days). Proportional allocation with a guaranteed seat for strata of at least 100 series;
seeded draw inside each stratum preferring unseen stores, cities and categories. Result: 50 distinct stores, all 18
cities, 28 of 32 top-level categories, 48 distinct products; 16 / 17 / 17 high / medium / low volume; 17 frequent,
21 occasional, 12 rare stockout; 26 smooth, 20 volatile, 4 intermittent; 23 promotional. Seed 20261019, selection
hash `497bf5a8741a…`.

## 5. Methodology

- **Two demand tracks.** A: observed daily sales as history and as settlement demand (censored by the retailer's
  stockouts; a lower-information sales-based counterfactual). B: recovered demand (DERIVED) as history and as
  settlement demand: on a day with k out-of-stock business hours, the sales observed in the in-stock hours are scaled
  by the share of the pre-origin in-stock hourly profile those hours represent, never below observed, capped at 3×,
  night hours kept as observed; a profile needs 7 fully in-stock days, otherwise uniform-hour scaling is used. The
  profile for any day uses only days before the origin. Recovered demand is never called observed; its uplift against
  observed and against the uniform benchmark is recorded per run.
- **Three supply scenarios (SYNTHETIC, identical for every policy):** `stable` (lead 1 day, no spread, full fill),
  `uncertain` (lead 2 days, spread 1 day, fill 0.9 ± 0.1), `uncertain_fill_only` (lead 2 days, no spread, fill
  0.9 ± 0.1). One supply realization per (series, window, scenario), seeded by a SHA-256 of those names, shared by
  both tracks and all policies.
- **Economics (SYNTHETIC indices per normalized unit):** cost 1.0, price 1.5, salvage 0.8, disposal 0.05, holding and
  capital 18 % per year as a daily rate (0.000493 per unit of value per day), service target 0.95, shelf life 7 days,
  opening stock 2 days of mean training demand, horizon 7 days, 3 planner scenarios, 20 s solve budget.
- **Policies.** `gated`: the production planner (`zaad.full.planner.plan` through `replay.choose`), with no declared
  incumbent rule (its incumbent is the engine's projected base-stock proxy). `order_up_to`: the engine's base-stock
  target solve with zero buffer. `base_stock`: the same with a 1.645 buffer (the engine's own distinction between the
  two). `reorder_point`: the projected (s, S) rule from `policies.baseline_plan` with z from the service target. All
  four consume the same demand fits; none received tuned parameters.
- **Windows.** `val1` (origin 2024-05-13) and `val2` (origin 2024-06-03): chronological internal validation inside
  the training period, rolling mode, 14 daily reviews, 7-day horizon (20 truth days each, both ending before the
  evaluation week). `final` (origin 2024-06-26): the designated evaluation week, legacy mode (the horizon shrinks by
  one day per review because no later day exists), 7 reviews. The validation windows were used to check correctness
  and failure modes on 5 series; no parameter was changed after seeing them, and nothing was tuned on the evaluation
  week.
- **Freeze.** Code, declaration (hash `eea25bb1f36d…`), selection and windows were committed before the 50-series run;
  the run manifest records the commit.
- **Fairness.** Same request per (series, window, track, scenario) for every policy; same truth World; each policy
  keeps its own stock, open orders and learned fill through `replay.replay`; no policy sees any day before it is
  settled; no incumbent rule or parameter was supplied to ZAAD that a baseline did not also have.
- **Statistics.** The series is the unit of replication. Within one (window, track, scenario) the per-series
  difference ZAAD minus baseline is summarised by its mean with 80 % and 95 % series-bootstrap intervals, the win /
  loss / tie count, and the exact sign-test p-value. Store-product-days are never treated as independent. With 50
  series the intervals are wide; that is reported as such.

## 6. Integrity tests (`tests/unit/test_frn_pilot.py`, 13 tests)

Source reconciliation (manifest refusal; audited invariants fail closed on an inconsistent panel); deterministic
selection, training-only and insensitive to the evaluation week; stockout interpretation (flag 1, hours 6..21);
recovery never lowers demand, uses only pre-origin profiles, caps, and does not change when post-origin days change;
daily-period units (daily holding rate, days as periods, one-day lead arrives next period, two-day in two); no
future information in a request (byte-identical under post-origin perturbation; refusal below 16 days); the history
cap below the seasonal candidate; one supply draw shared across tracks and reproducible by seed, with the retailer's
stockouts never in the truth; replay fairness (conservation residual zero per review, order placed at t is pending
at t, independent policy states, reproducible decisions); a failing policy is recorded with its error; the
declaration is versioned, hashed and daily. The loaded-dataset test verifies the manifest and the frozen selection
hash when the files are present and skips otherwise.

## 7. What actually ran

| stage | series | runs | complete | not complete | wall | peak RSS |
|---|---|---|---|---|---|---|
| smoke | 1 | 4 | 4 | 0 | 2 s | 225 MB |
| five (all windows, tracks, scenarios) | 5 | 360 | 312 | 48 | 161 s | 254 MB |
| fifty (all windows, tracks, scenarios) | 50 | 3,600 | 2,425 | 1,175 | 950 s wall, 1,613 s CPU | 270 MB |

Fifty = 50 series × 3 windows × 2 tracks × 3 scenarios × 4 policies, run sequentially (one solve at a time) at
commit `5c39a51` with declaration `eea25bb1f36d…` and selection `497bf5a8741a…`. Every run is one line of
`data/public/freshretailnet/results/fifty/runs.jsonl` (git-ignored, reproducible from the committed code and the two
verified files); the summaries are `docs/remodel/evidence/frn/RESULTS_fifty.{json,md}`. Mean wall time per run:
ZAAD 0.84 s (max 12.5 s), base-stock 0.11 s, order-up-to 0.08 s, reorder-point 0.02 s. The largest conservation
residual across all 2,425 complete runs is 2.8e-14 units. Nothing was tuned after the first results; the
validation windows were run on 5 series before the fifty stage, and the fifty stage ran all windows once.

"Not complete" is a policy outcome, recorded with the review at which it occurred, never a harness error: the
engine's replay stops a policy's run at the first review whose solve is INFEASIBLE or on which the planner abstains,
and fabricates nothing (in production an abstention keeps the operator's rule for the period; this pilot has no
operator rule, so an abstention ends the run).

| policy | runs | complete | INFEASIBLE | ABSTAIN |
|---|---|---|---|---|
| ZAAD (`gated`) | 900 | 436 (48 %) | 0 | 464 (52 %) |
| base_stock | 900 | 447 (50 %) | 453 | 0 |
| order_up_to | 900 | 642 (71 %) | 258 | 0 |
| reorder_point | 900 | 900 (100 %) | 0 | 0 |

## 8. Results

Every number is a modelled index per normalized unit under the declared supply and economics; "cost" is the
settled window cost (purchase + carrying + shortage + inventory value change + fees). Paired statistics use only
series where both policies completed the same (window, track, scenario); the counts of pairs are shown because the
abstentions and infeasibilities remove different series from different comparisons, which is itself a selection effect
to keep in view.

**8.1 Where ZAAD and the reorder-point rule meet.** Under `stable` supply ZAAD and the projected reorder-point rule
are indistinguishable on cost: final window, observed track, 35 pairs, mean difference +0.020 (95 % bootstrap
−0.10 to +0.17), 17 wins / 18 losses; recovered track, 39 pairs, −0.042 (−0.10 to +0.02), 20 / 19; both validation
windows the same (−0.03 to −0.10, sign-test p 0.23 to 1.0). ZAAD completed these runs by retaining its projected
base-stock proxy on 63 % of reviews (2,939 of 4,634 completed reviews), so on stable daily supply the production
planner mostly re-issued a base-stock-style decision and matched the rule that does the same thing by construction.

**8.2 Where ZAAD beats the model-based baselines.** Against `order_up_to` (zero buffer) ZAAD is cheaper in every
stable cell with narrow intervals (final/observed 35 pairs, −0.56, 95 % −0.85 to −0.26, 29 / 6; val1/recovered 28
pairs, −1.59, −2.87 to −0.84, 28 / 0): the zero-buffer target under-protects and pays shortage. Against `base_stock`
ZAAD is cheaper in the final window's stable cells (−0.31 to −0.38, 28 / 5 and 31 / 5) and equal in the validation
windows. These are wins against the weakest baselines, and the paired sets exclude the 453 runs where base_stock was
infeasible.

**8.3 Where ZAAD loses.** Under the `uncertain` scenario (lead spread one day, fill 0.9) ZAAD is more expensive than
the reorder-point rule in both validation windows: val1/observed 18 pairs, +2.53 (95 % +0.44 to +5.57), 7 / 11;
val2/recovered 17 pairs, +2.02 (+0.81 to +3.41), 5 / 12; and in the final/recovered cell, 34 pairs, +0.65 (+0.25 to
+1.13), 13 / 21. Under `uncertain_fill_only` the validation windows show the same sign (val2/recovered vs
reorder_point 16 pairs, +2.95, +0.80 to +5.98, 1 / 15; vs base_stock 9 pairs, +3.48; vs order_up_to 15 pairs,
+2.62) while the final window is mixed and small (−0.11 to −0.87, intervals crossing zero or barely not). The
mechanism is visible in the policy means: ZAAD carries 1.5 to 2.5 times the inventory of the reorder-point rule
(final window, uncertain: 3.68 vs 1.41 units observed track, 4.13 vs 1.83 recovered) for a service gain of about one
to two points of fill (0.901 vs 0.881; 0.913 vs 0.889), and under the declared economics (capital 18 % per year,
cheap holding, salvage 0.8) that extra stock does not pay back inside a 7-day horizon while the purchase and
inventory-value terms grow. The planner's state log shows why: 3,829 of its reviews ran in the PROTECT state, 1,487
in NO_ACTION, 897 in NORMAL_REPLENISHMENT. The daily-period audit predicted this: a one-day lead spread exceeds the
engine's half-period lateness slack, so the supply-risk state activates on nearly every SKU; the fill-only variant
shows the protection reaction is also driven by short deliveries, not only by lateness.

**8.4 Abstentions are the dominant ZAAD outcome on low-volume daily series.** ZAAD abstained on 464 of 900 runs:
76 % of low-volume series' runs, 58 % of medium, 19 % of high; roughly evenly across stockout and promotion classes;
more on intermittent (64 %) than smooth (47 %) series; in 47 of the 50 series at least once, in 20 series on 12 or
more of their 18 runs; typically early (mean review 4, 45 at review 0). Every abstention carried the same two
sentences: "Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service
recovery" and "Incumbent itself has no verified feasible projection; no executable fallback is fabricated"; 317 of
them were in `mode=ALLOCATE` with "Requested service targets are not jointly achievable under the modeled state".
Reading: with median demand below one normalized unit per day, a 0.95 unit-fill target over 7 daily periods, three
scenario worlds and a stress confirmation, the engine frequently finds no plan it will certify and declines. The same
infeasibility drives the 453 and 258 INFEASIBLE solves of the base-stock and order-up-to targets. Only the projected
reorder-point rule, which does not solve a target, always produces an order.

**8.5 Tracks.** Recovered demand (track B) raised the planner's demand history by a median 23 % over observed
sales (p10 6 %, p90 48 %, max 106 % across the 150 series-windows; the per-run uplift is in each row) and the
settlement demand by a median 17 % (p90 45 %). The sign of the ZAAD-minus-baseline cost difference agrees between the
two tracks in 21 of the 27 paired cells; the 6 disagreements are all cells whose intervals cross zero widely (the
`uncertain` scenarios against order_up_to in all three windows, final `uncertain` against base_stock, and the
stable final cell against reorder_point where both differences are within ±0.05). The stable-supply equivalence, the
advantage over order_up_to and the validation-window losses under uncertain supply hold on both tracks. Censoring
therefore does not explain the pattern above; it does mean that every fill figure on the observed track overstates
service against true demand by an unknown amount, and that the recovered track's own error is unmeasured.

**8.6 Strata (final window, recovered track, vs reorder_point).** Stable: frequent-stockout series −0.07 (14
pairs, 8 ZAAD better), occasional −0.05 (16, 9), rare +0.02 (9, 3). Uncertain: frequent +1.50 (11, 2), occasional
+0.42 (12, 6), rare +0.05 (11, 5); smooth +0.98 (18, 6), volatile +0.24 (13, 6), intermittent +0.46 (3, 1). ZAAD's
losses under uncertain supply concentrate on the frequent-stockout, smooth, higher-volume series where protection
buys the most inventory.

## 9. Are the results meaningful?

Statistically: the stable-supply equivalence with reorder_point and the advantage over order_up_to are tight (95 %
intervals of ±0.1 to ±0.3 on costs of 11 to 14; sign tests at or below 0.001 for order_up_to). The losses under
uncertain supply have 95 % intervals that exclude zero in four validation cells and one final cell, on 9 to 34 pairs,
but the pairs are a selected subset (series where ZAAD did not abstain), the three windows of one series are
dependent, and the final week is a single summer week after a 41 % volume climb. Operationally: the comparison is
between policies that all consume the same demand fits and the same declared supply; it says nothing about supplier
behaviour, real costs, cash or realized service, and the dataset's normalized units mean no cost can be read in
currency. What it does establish is behavioural: on real low-volume daily demand the production planner abstains
more often than it plans, and when supply is declared uncertain its protection state buys inventory that the declared
economics do not reward within the horizon.

## 10. Failure analysis

1. **Abstention without an operator rule (464 runs).** The engine's design is to retain the operator's rule when it
   cannot certify a plan. The pilot has no rule, so abstention ends the run and the series drops from paired
   comparisons. This is correct engine behaviour and a real finding about the product on this demand regime: in a
   store with no declared rule the planner would frequently produce no order. Any expansion must decide, and declare,
   what a store does on an abstention day (a documented default rule as the incumbent, which the engine then
   retains), without presenting that rule's result as ZAAD's.
2. **Service target infeasibility at low volume (ZAAD 317 ALLOCATE abstentions; 711 baseline INFEASIBLE solves).** A
   0.95 unit-fill target over seven daily periods is frequently not jointly achievable under the fitted scenarios for
   series averaging under one unit per day. The target was declared, not derived from the data; a target
   sensitivity (0.90, 0.85) is the obvious next axis.
3. **Protection regime under daily lead spread (W1).** The half-period lateness slack is weekly-calibrated; with a
   one-day spread on daily periods the supply-risk state activates everywhere and ZAAD over-stocks relative to the
   declared economics. This is a calibration gap of the risk-state rules at daily cadence, not an optimizer defect;
   it must not be patched by reinterpreting the slack for this dataset.
4. **Retained proxy (63 % of completed ZAAD reviews).** When ZAAD completes, it mostly keeps its projected base-stock
   proxy, so its stable-supply results are the proxy's results. The gated selection rarely found a candidate that
   materially improved on it at this scale and horizon.
5. **No ZAAD solve exceeded the budget**; the slowest run took 12.5 s for 14 reviews; no REQUESTED_SERVICE_INFEASIBLE
   recovery solve occurred; no exception, no physical failure, conservation residual at machine precision.

## 11. Scalability (measured, then arithmetic)

Measured: 50 series, 72 runs each, 950 s wall and 1,613 s CPU sequentially, 270 MB peak; 19 s per series across all
windows, tracks, scenarios and the four policies; ZAAD is 0.84 s per run on average because each instance is one SKU
over seven daily periods. Arithmetic, same design and declaration, sequential on one core: 500 series about 2.6 h;
5,000 about 26 h; 50,000 about 264 h. The work is independent across series, so 8 cores give roughly 0.3 h, 3.3 h and
33 h. Memory is flat. DuckDB ingestion of the whole dataset takes 5 s. The bottleneck of a full-data run is not
compute but interpretation: with ZAAD abstaining on half its runs, a 50,000-series run would mostly measure the
abstention policy. These are estimates from this pilot's shape; nothing beyond 50 series was run.

## 12. Recommendation

Do not expand yet. Correct and re-declare first, then re-run the same 50 series:

1. Decide the abstention convention for a store without an operator rule (a declared default rule as the incumbent,
   retained on abstention, reported separately from ZAAD's own decisions) so every series completes and the paired
   comparison stops being a selected subset.
2. Add a service-target sensitivity (0.85 / 0.90 / 0.95) to the declaration; the current target makes the planner and
   two baselines infeasible on low-volume daily demand.
3. Treat the daily lateness-slack behaviour as an engine calibration question for daily cadence, decided by the owner
   on the engine side, not in the dataset harness; until then report `uncertain` results as a protection-regime study.
4. Keep both demand tracks and the fill-only scenario; they separated effects cleanly.
5. Only after a complete 50-series run with these changes, expand to 500 series (hours, not days, on one machine),
   not to 50,000.

The dataset did what it was chosen for: it exposed how the production planner behaves on real low-volume, censored,
daily demand under declared uncertainty, including where it declines to act and where its protection logic spends
more than the declared economics return. It did not and cannot show a realized saving.
