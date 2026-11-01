# Walmart M5 results: Experiment A (single-SKU weekly replenishment) and Experiment B (coupled purchasing)

Design frozen in `M5_DESIGN_FREEZE.md` before any holdout was read; corrections made after the first runs are listed in
its section 7 and in `../FRN_AUDIT_REGISTER.md` (findings 15–20). 50 store-item series selected on training-only
features (hash `8b6067be83a4`), three windows of 13 weekly reviews with an 8-week rolling horizon; `final` (origin
2016-01-02) is the holdout. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and
economics on OBSERVED Walmart sales (sales, not demand); nothing is a realized saving. Tables: `M5_CROSSTAB.md`
(every variant, window and scenario with the frozen verdict), `RESULTS_fifty_<variant>.md`, `RESULTS_coupled_<coupling>.md`.

## 1. Experiment A, primary configuration (`corrected`: target 0.95, declared `reorder_point` incumbent)

Completion 725 / 750 runs for every policy (the 25 non-complete rows are recorded BUILD_FAILED runs: four series unpriced
at the val1 origin, one series with no sales before the val2 origin); no abstention, no infeasible solve.

Holdout, series-paired continuation cost ZAAD minus `reorder_point` (49 series; negative favours ZAAD), with the
frozen verdict:

| scenario | ZAAD cost | rule cost | paired mean | 95 % bootstrap | better / worse | fill diff | inventory diff (units) | ZAAD own share | verdict |
|---|---|---|---|---|---|---|---|---|---|
| stable | 357.68 | 358.26 | −0.58 | [−1.78, +0.14] | 21 / 21 | +0.003 | +0.4 | 0.21 | INCONCLUSIVE |
| mild_lead (14 ± 3 d) | 366.66 | 369.48 | −2.83 | [−4.90, −1.04] | 25 / 22 | +0.025 | +3.9 | 0.41 | SUCCESS |
| lead_only (14 ± 7 d) | 367.63 | 371.40 | −3.77 | [−5.99, −1.75] | 27 / 21 | +0.038 | +4.4 | 0.42 | SUCCESS |
| fill_only (0.9 ± 0.1) | 392.67 | 395.53 | −2.87 | [−7.28, +0.92] | 28 / 17 | +0.019 | +10.3 | 0.40 | INCONCLUSIVE |
| uncertain (both) | 418.76 | 419.93 | −1.17 | [−6.52, +3.51] | 22 / 24 | +0.047 | +10.3 | 0.38 | INCONCLUSIVE |

Against `periodic:1` the readings are the same within 0.4 (`RESULTS_fifty_corrected.md`). The differences are small
against the cost level (0.2–1.0 % of a series-window's cost) and come from fewer shortage dollars bought with more
inventory: under lead spread ZAAD's shortage is lower by 13–17 per series with 4 more units on hand; under fill
variability and combined uncertainty the inventory it carries (+10 units) costs about what the shortage it avoids
saves.

Validation windows (same declaration, read for consistency, not for selection): val2 repeats the holdout (`lead_only`
−3.39 [−6.11, −1.12] and `mild_lead` −2.34 [−4.98, −0.26] SUCCESS; stable a tie) and adds one FAILURE, `uncertain`
+4.24 [+1.01, +7.94] with ZAAD carrying 10 more units; val1 (43 series) is inconclusive in every scenario with
`uncertain` at +3.88 [−1.16, +9.00]. So across the three windows: lead-time spread favours ZAAD consistently; stable
supply is a tie; combined lead and fill uncertainty is a wash on the holdout and against ZAAD on the validation
windows, where the PROTECT regime's inventory does not pay back.

## 2. Experiment A, predeclared variants (holdout, paired against the rule at the same declaration)

| variant | stable | mild_lead | lead_only | fill_only | uncertain | ZAAD own share (stable / uncertainty) |
|---|---|---|---|---|---|---|
| corrected | −0.58 | −2.83 S | −3.77 S | −2.87 | −1.17 | 0.21 / 0.38–0.42 |
| no_incumbent | −1.31 | −7.32 S | −7.43 S | −1.67 | −1.19 | 0.23 / 0.40–0.47 |
| target_90 | −0.81 | −6.05 S | −6.20 S | −4.70 | −4.36 | 0.18 / 0.51–0.54 |
| holding_x2 | −0.52 | −2.51 S | −2.24 S | −2.32 | −2.68 | 0.18 / 0.33–0.38 |
| cash_4w_revenue (post-freeze) | −0.42 | −2.72 S | −3.65 S | −2.53 | −2.11 | 0.22 / 0.38–0.43 |
| cash_4w (frozen; a liquidation) | underpowered: 2–4 series complete | | | | | |

S = SUCCESS under the frozen criteria; every other cell is INCONCLUSIVE. Without the declared incumbent
(`no_incumbent`) ZAAD's lead-spread advantage doubles (36 / 12 wins, sign p 0.001) at the price of 8–25 more units of
inventory and fill higher by 0.05–0.08; with the incumbent the planner retains the rule on about 60 % of reviews and
the readings are diluted toward it. Lowering the target to 0.90 lowers both policies' fill and widens ZAAD's lead-spread
margin; doubling holding does not change the sign anywhere. The frozen cash variant cannot be read (register finding
18): with no cash inflow every policy liquidates; the post-freeze variant with mean revenue declared as receivables
reproduces the primary readings with 104 abstentions out of 750 where the budget binds.

## 3. Experiment B, coupled purchasing (`coupled`: $40 fixed cost per order-week, MOV of half a week, 6-pallet cap, case lots, declared `economic_lot` incumbent)

After E3 (legal projections) every run completes: 360 / 360 across 10 store groups × 3 windows × 3 scenarios × 4
policies, zero constraint breaches, zero abstentions. (Run 1 on the frozen code, kept as
`coupled_run1_prefix_70c10db`, had the rules breaching pack, load or MOV on 23 of 159 runs and ZAAD abstaining on 13
of 53.)

Holdout, group-paired continuation cost ZAAD minus baseline (10 groups):

| scenario | vs economic_lot | vs reorder_point | vs periodic:1 | ZAAD fill / economic_lot fill | ZAAD own share |
|---|---|---|---|---|---|
| stable | −62.4 [−162.7, +5.7], 6 / 3 | −160.8 [−193.7, −124.2], 10 / 0 | −169.1, 10 / 0 | 0.939 / 0.900 | 0.29 |
| mild_lead | −25.7 [−113.5, +36.3], 5 / 4 | −138.1 [−167.4, −108.1], 10 / 0 | −148.6, 10 / 0 | 0.879 / 0.852 | 0.25 |
| fill_only | −57.6 [−136.8, −9.7], 5 / 0 (5 ties) | −99.0 [−160.9, −34.0], 7 / 3 | −103.3, 7 / 3 | 0.905 / 0.894 | 0.15 |

Validation windows against `economic_lot`: ZAAD is worse in all six cells (+3 to +33 per group), val2 stable +32.7
[+10.2, +56.4] with the interval excluding zero, val1 `mild_lead` +13.5 [−0.1, +27.2]; against `reorder_point` and
`periodic:1` ZAAD wins 9–10 of 10 groups in every window.

Reading. The large, consistent margins over `reorder_point` and `periodic:1` are the fixed order cost: those rules
place an order every week (12 order-weeks, $480 of ordering) while `economic_lot` and ZAAD consolidate to 8–9
order-weeks. Against the competent constraint-aware baseline (`economic_lot`), which is also ZAAD's declared
incumbent, the holdout favours ZAAD by 26–62 per group with intervals that include zero in two of three scenarios, the
validation windows favour `economic_lot`, and ZAAD's own candidates are 15–29 % of reviews. ZAAD's fill is higher
(+0.01 to +0.04) with more inventory (+7 to +34 units per group). Ten groups cannot settle this; the fixed cost dominates
and the pallet cap rarely binds for ZAAD (no cut or cancelled order-weeks) while the rules cut 7–18 order-weeks each.

The `coupled_cash` variant (four weeks of cash plus a one-week credit line, no receivables) is a liquidation like
`cash_4w` (every policy's fill 0.38–0.46); after E3b every run completes and ZAAD's cost is lower than the rules' by
17–37 per group, which measures who runs out of cash last. The `coupled_tight` variant (4 pallets, MOV one week) is
reported in section 6 (partial: 6 of 10 groups).

## 4. The frozen criteria, applied

Experiment A, holdout, primary configuration: SUCCESS in `mild_lead` and `lead_only`; INCONCLUSIVE in `stable`,
`fill_only` and `uncertain`; no FAILURE. The operational reading from the freeze: "a success in stable and mild_lead
would show value from the planner's own candidates" is half met (mild_lead only); "a failure in stable with retained
share near one" does not apply (stable is a tie with own share 0.21). Validation windows add one FAILURE (`uncertain`,
val2). Experiment B: ZAAD's advantage over `reorder_point`/`periodic:1` comes with no breaches, as required, but the
competent baseline is `economic_lot`, against which the holdout is inconclusive and the validation windows negative.

## 5. Economics and failure analysis

- Where ZAAD wins, it buys shortage down with inventory under lead-time spread, on weekly periods where the planner's
  lateness calibration is native. The win is 0.8–1.0 % of cost per series-window on the holdout; with the planner's
  own candidates only (`no_incumbent`) 2 %.
- Where it loses (validation `uncertain`), the PROTECT regime holds 10–20 more units per series against fill shortfalls
  that the observed sales did not produce; the continuation cost already credits that stock at asset value, so the loss is
  carrying cost and over-purchase, not salvage.
- Runtime: ZAAD 2.9–5.6 s per 13-review run on single SKUs, 29–95 s per coupled group; the rules 0.03–0.1 s.
- Sales are a lower bound on demand and no stockout flag exists, so every fill rate is service against sales; the
  supply side is declared, not observed.

## 6. `coupled_tight` (4 pallets, MOV one week; holdout only): partial, 6 of 10 groups

The run was stopped after the seventh group's `gated` run under `stable` supply had used 2 h 37 min of CPU at 100 %
without finishing (the declaration's solve budget is 40 s per solve; the planner's wall clock per review is not bounded
by it on this cell). The 72 completed rows (6 groups × 3 scenarios × 4 policies, no breaches, no abstentions) are
summarised in `RESULTS_coupled_coupled_tight.md` and read as follows. The cap binds hard for everyone: unit fill falls
to 0.62–0.73 for every policy (0.80–0.94 under the primary coupling). ZAAD against `reorder_point` / `periodic:1` is a
tie (stable +9.5, mild_lead −3.2, fill_only +2.6 per group, 3 / 3 wins, intervals of ± 60); against `economic_lot`
−26 to −65 per group with intervals that include zero (2 / 1 wins, 3 ties). ZAAD's own candidates are 13–17 % of
reviews and its runs take 120–343 s per group against 0.1–0.2 s for the rules. Under a binding shared cap the planner
neither breaches nor adds measurable value over the lot-aware rule, and its runtime is the finding (register 21).
