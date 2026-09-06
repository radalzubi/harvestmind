# Frozen mechanism experiment and coverage limits

The final causal experiment uses 89 cells × 5 seeds × 9 policies = **4,005
policy runs**. Five selected cells × 5 seeds × 12 policies add **300 ablation
runs**, including repeated controls. These are not 4,305 independent operators.
There are five seed paths, reused across cells. Every individual result, failure
and fallback is retained in JSON/CSV; descriptive cell ranges and exploratory
bootstrap intervals are generated without outcome filtering.

## Factors

Full factorial: target .85/.90/.93/.95/.97/.98/.99/.995/1.0 × opening cover
0/.5/1/2/3/4/6/8. Extra targets .94/.96/.999 at cover2 permit the requested
marginal service discussion. These are **configured targets**, not a claim
that baseline realized service was independently set to each percentage.

At target .97, cover2, vary one factor at a time: mild/moderate/severe disruption;
seasonality/intermittency/promotion/structural demand shift; variable/heavy-tail/
closure leads; variable/common-failure supply; low/high contribution margin.
No full high-dimensional interaction grid is claimed. The common-failure cell
is a correlated **realized-path stress**, not an ablation proving copula value:
this small one-source-per-SKU test does not exercise feasible source diversification.

All input series are generated, not calibrated Indiana/Jordan customer records.
Two SKUs, one supplier each, mean demand100/40, unit cost$5, fixed capacity150/60,
unit packs, weekly 0.5% holding, baseline margin$2/unit. No warehouse limit,
spot/expedite, expiry or transfers. Known initial pipeline is an explicit common
assumption. Later pending POs have expected quantities/dates distinct from private
realized arrivals; supplier evidence becomes available upon receipt. An overdue
unreceived order is provisionally due now, not assigned its eventual true ETA.

Training trails52 weeks. Main evaluation seeds401–405, 8 scenarios, 12 realized
weeks from week60, horizon12 and reviews every4. The comparison is a short
mechanism test, not long-run inventory-policy validation; the fixed horizon can
be inadequate in long-lead stress. All policies see the same realized paths
but retain their own inventories and open orders. Terminal cash/salvage is not
valued. No public signals are used as leading indicators.

## Policies and causal comparisons

- `incumbent`: configured fill-aware inventory-position rule, cover2/review1,
  not an actual operator's reconstructed purchasing history.
- `order_up_to`: the existing statistical safety-stock rule.
- `deterministic_sp`: the same planning formulation with point scenarios.
- `legacy_sp`: hides pipeline **only from the planner**, isolating that defect;
  it is not a byte-for-byte rerun of the entire old product or old data harness.
- `stochastic_sp`: pipeline-aware distributional candidate.
- `service_target`: aggregate controllable-horizon target, no shortage reward.
- `service_periodic`: same candidate plus expected fill in every controllable period.
- `anchored_sp`: existing L1 anchoring and CVaR relative to incumbent.
- `safe_selected`: hardened confirmation/live gates with explicit candidates
  order_up_to, deterministic_sp, service_target and stochastic_sp. The new
  per-period candidate is **not promoted into this gate/default product**.

Additional ablations: `anchored_no_cvar` isolates the CVaR penalty; `adaptive_sp`
tests the existing state-conditioned package; `stochastic_open_loop` removes
replanning over the same realized window. The adaptive package changes multiple
knobs, so its result cannot separately establish value from detection, CVaR,
trust region or route state. Segmentation, independent route signals, MEIO,
DRO and source-switch economics are not separately validated here and no
incremental benefit is claimed for them.

An unusable or relaxed solve executes the incumbent and records the failure.
Its mixed result is **candidate-with-fallback**, not an unqualified solver win.
The incumbent may itself miss a target when supply is insufficient. This is
reported, not silently transformed into a guarantee.

## What the ledger measures

Total = holding + missed contribution + disposal + SLA. This experiment's
last two are zero; spot/expedite and financing cash flows are not modeled.
Gross contribution is served units × common contribution/unit minus carry and
disposal, not sales revenue. Inventory is average physical stock value, not
PO cash commitments or full working capital. Average stock units = value/5;
period inventory turns = served units×5 / average stock value. Neither is
annualized from a 12-week stress episode.

Unit fill and unmet units are available; customer-order OTIF is unavailable.
The cell summary includes empirical upper-tail cost CVaR90, which at five seeds
is just the worst seed, not a well-estimated extreme tail. Percent savings use
incumbent operating loss as denominator, not revenue or all procurement costs.
The largest negative percentages can therefore have small dollar denominators.

The frontier and marginal table report realized service, carry, shortage and
inventory. Flat/decreasing realized service means there is no meaningful
positive marginal price for that observed step; no smoothed frontier is invented.
Exploratory bootstrap intervals with five seeds are not calibrated service
guarantees. This is developmental testing after inspecting earlier results,
not a pristine blind validation set.

## Reproduce

```bash
python3 scripts/run_commercial_remodel_audit.py
python3 scripts/run_commercial_remodel_audit.py --ablations
python3 scripts/summarize_commercial_remodel.py
```

Defaults write only `docs/remodel/evidence/causal/`. The rejected directory is
historical and excluded from all headline summaries. No production database,
operator vault or training pool is touched.

Environment used: Python3.14.3, NumPy2.4.2, SciPy1.17.1, pandas2.3.3,
Pyomo6.10.0, HiGHS/highspy1.14.0. Solver tolerances and package versions can
change tie solutions. Check quantity balances and paired costs, not just a
rounded headline. Additional tests pin pipeline conservation, no lookahead,
service-window behavior, hard gating and exact simple-problem solutions.
