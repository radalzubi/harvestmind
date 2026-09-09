# P1 benchmark / horizon closure pass: pre-registration

Written at `de4e771` BEFORE any extended-window run. Nothing in this file is changed after the runs;
corrections, if any, are appended in a dated section at the end and never edited in place.

## 0. What is fixed during this pass

Planner ownership router, candidate request matrix, selector, solver objective, materiality, stochastic
candidate mathematics, order smoothing, freight and MOQ economics, P0 behaviour, fixture arguments,
seeds (41001-41003, truth seed + 10000), the 2% tolerance (3% where declared on Q and S), the N / R
proven-invalid classification. The legacy replay path (shrinking horizon, realised ledger, salvage
terminal) is not modified: every change below is an opt-in evaluation mode. The legacy twelve-week
results already recorded (`P1_RESULT_TABLE_none_product_defaults*.md`, `closure/router_targeted.json`,
`closure/stage1_lock_P.json`) stay the legacy record.

## 1. The benchmark pathology, stated

The legacy benchmark scores eleven rolling reviews of a twelve-period plan whose horizon shrinks by one
period per review (H-1 convention), charges every ledger component inside the window and credits the
stock and in-transit units left at the end at the declared salvage (`terminal_value`, 80% of the unit
price). Two boundary effects follow:

* **Terminal haircut.** A lot that lands shortly before the window end is charged in full and credited
  at 80%; a policy whose lot lands one review after the end pays nothing. On a 400-unit lot at $5 the
  swing is $400, which is 6.8% of C's eleven-week cost and 4% of I's. It is symmetric: the salvage rule
  penalises whichever policy happens to hold the late lot; the continuation rule removes that penalty
  and so favours whichever policy holds it.
* **Shrinking planning horizon.** Every policy (ZAAD and baselines alike) sees the end of the world
  approaching: the baselines cover only to `req.horizon` and ZAAD's objective haircuts end-of-plan stock
  at salvage. Late-window decisions are therefore closure decisions, not steady-state purchasing
  decisions. This was recorded as a benchmark property (memory: replay shrinking horizon) and is not an
  engine bug.

Useful continuing inventory is stock that the fitted demand consumes before it expires; uneconomic
excess is stock that expires, or that demand does not absorb, or whose carrying and capital cost until
consumption exceeds the purchase it avoids. The evaluation must value the first near the purchase it
avoids (less carrying) and the second at salvage, for every policy by the same rule.

## 2. Horizon inventory (Stage 2; from fixture arguments and the recorded legacy evidence, no new runs)

Planning horizon 12 periods and evaluation window 11 reviews on every fixture. Lead, next order
opportunity and lot cycle per fixture:

| fixture | plan H | eval window (reviews) | lead (periods) | next order opp. | MOQ | EOQ (units) | full load | lot cycle by policy (weeks of demand per order, legacy) | terminal units at wk 11 by policy (legacy) | legacy delta salvage / continuation |
|---|---|---|---|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 1.0; reor 1.0; peri 2.0; econ 1.0; gate 1.0 | 115/115/220/115/114 | +0.43% / +0.46% |
| B_fixed_order_cost_replace_sold | 12 | 11 | 1 | 2 | 0 | 1864 | - | incu 1.0; reor 1.0; peri 2.0; econ 18.5; gate 7.3 | 120/115/220/867/131 | -10.70% / -1.06% |
| C_moq_four_weeks | 12 | 11 | 1 | 2 | 400 | 0 | - | incu 4.0; reor 4.0; peri 4.0; econ 4.0; gate 4.6 | 3348/221/479/221/399 | +3.61% / +0.77% |
| D_case_multiple | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 1.0; reor 1.0; peri 2.1; econ 1.0; gate 1.0 | 157/157/252/157/113 | -0.58% / +0.17% |
| E_pallet_multiple | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 2.0; reor 2.0; peri 2.2; econ 2.0; gate 2.0 | 221/221/350/221/221 | -0.00% / +0.00% |
| F_mov_two_skus | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 4.0; reor 6.9; peri 4.0; econ 6.9; gate 4.7 | 2407/452/464/452/462 | +0.24% / +0.28% |
| G_freight_tiers | 12 | 11 | 1 | 2 | 0 | 1179 | 2000 | incu 2.0; reor 2.0; peri 3.9; econ 20.0; gate 8.4 | 239/221/430/2033/273 | -10.01% / -0.41% |
| H_per_pallet_freight | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 1.0; reor 1.0; peri 2.0; econ 1.0; gate 1.4 | 115/115/220/115/114 | -3.73% / -2.29% |
| I_max_pallets_ftl_cap | 12 | 11 | 1 | 2 | 0 | 1444 (capped by the 450 load) | 450 | incu 1.0; reor 1.0; peri 2.0; econ 4.5; gate 3.0 | 115/115/220/368/123 | +0.53% / +3.05% |
| J_net60_cost_of_capital | 12 | 11 | 1 | 2 | 0 | 1076 | - | incu 1.0; reor 1.0; peri 2.0; econ 10.7; gate 7.3 | 115/115/220/796/131 | -11.06% / -3.52% |
| K_deposit_early_cash | 12 | 11 | 1 | 2 | 0 | 1076 | - | incu 1.0; reor 1.0; peri 2.0; econ 10.7; gate 7.3 | 115/115/220/796/131 | -11.20% / -3.64% |
| L_high_holding_rate | 12 | 11 | 1 | 2 | 0 | 1021 | - | incu 1.0; reor 1.0; peri 2.0; econ 10.2; gate 7.3 | 120/115/220/1051/131 | -10.16% / -4.74% |
| M_order_calendar_wednesday | 12 | 11 | 2 | 3 | 0 | 0 | - | incu 1.0; reor 1.0; peri 2.1; econ 1.0; gate 1.3 | 220/220/317/220/158 | -0.54% / +0.44% |
| N_long_lead_21_days | 12 | 11 | 3 | 4 | 0 | 0 | - | incu 1.0; reor 1.0; peri 2.0; econ 1.0; gate 1.3 | 234/234/223/234/166 | -0.71% / +0.42% |
| O_low_opening_stock | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 2.1; reor 1.0; peri 2.1; econ 1.0; gate 1.3 | 220/115/220/115/117 | +0.46% / +0.44% |
| P_high_opening_stock | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 1.0; reor 0.9; peri 1.8; econ 0.9; gate 1.0 | 568/115/220/115/109 | +0.29% / +0.39% |
| Q_volatile_demand_high_target | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 1.0; reor 1.0; peri 2.1; econ 1.0; gate 1.0 | 180/180/298/180/168 | +0.85% / +1.08% |
| R_asymmetric_prices_mov | 12 | 11 | 1 | 2 | 0 | 0 | - | incu 2.0; reor 2.0; peri 3.9; econ 2.0; gate 2.0 | 221/221/430/221/219 | -0.05% / -0.04% |
| S_cash_constrained | 12 | 11 | 1 | 2 | 0 | 1179 | - | incu 1.0; reor 1.0; peri 2.0; econ 6.5; gate 2.4 | 115/115/220/318/115 | +0.26% / +3.59% |
| T_combined_realistic | 12 | 11 | 1 | 2 | 0 | 1221 | 1920 | incu 3.1; reor 5.5; peri 4.0; econ 20.0; gate 8.4 | 1459/536/442/2033/410 | -11.47% / -4.21% |

(Terminal units and lot cycles: incumbent / reorder_point / periodic:2 / economic_lot / gated. Lot cycle
for two-SKU fixtures is per line.) Reading: on B, G, J, K, L and T the EOQ-style baseline's lot cycle
(10-20 weeks of demand) is LONGER than the whole evaluation window, and on C, F and I it is 4-7 weeks,
i.e. the window ends 1.5-3 cycles in. Lead-time exposure is one period except M (2) and N (3). The
twelve-week window is therefore not long relative to the economic cycle for half the family, and the
terminal rule decides C, I and S (legacy salvage / continuation deltas: +3.61 / +0.77, +0.53 / +3.05,
+0.26 / +3.59).

S in particular: its declared receivables (450 / week) are below every policy's cash-out (525-609 /
week in the legacy run), so its 3,000 of cash plus credit is exhausted after 19-40 weeks depending on the
policy. S is a transient cash-squeeze fixture by construction.

## 3. Extension mechanics (Stage 3; pre-registered before running)

* **Planning horizon**: 12 periods, CONSTANT and rolling: at every review each policy replans on a fresh
  twelve-period snapshot, exactly as production replanning does (the replay's own `horizon_note`). This is
  an opt-in replay mode (`rolling=True`); the legacy shrinking mode is untouched and remains the P0 path.
  Period-indexed declared data roll forward by repeating the last declared value (capacity, dated
  receivables); committed future payments roll into `other_payments` at their due period, none dropped.
* **Truth**: one path per seed, stitched from twelve-period draws (`long_truth`): segment k is drawn from
  the fixture request with `as_of` advanced by 12k periods and seed `+10000+k`; segment 0 is the legacy
  truth bit for bit. Demand is i.i.d. per period in the sampler and supply shocks are per period, so the
  stitched path has the fitted distribution in every period. Validation and holdout seeds are not used.
* **Evaluation endpoints**: the same run is scored at every endpoint W (reviews scored) from 1 to 52; the
  reported grid is W in {11, 13, 15, 17, 19, 23, 35, 47, 52} = legacy length + {0, 2, 4, 6, 8, 12}, three
  and four planning horizons, and one commercial year. Scoring at W uses the first W reviews' ledgers, the
  opening assets of review 0 and the terminal state at review W-1; this reconstruction is identical to a
  replay stopped at W (unit-tested, "identical physical trajectory, same result").
* **Terminal rules compared at every endpoint** (same rule for every policy, no policy or fixture term):
  * **A salvage**: the realised ledger (declared `terminal_value` on on-hand and in-transit units).
  * **B continuation**: A plus the finite-horizon continuation adjustment of `zaad/full/terminal.py`
    (each residual unit worth the purchase it avoids when consumed at the fitted mean rate, less carrying
    and cost of capital until then, floored at salvage, capped at unit value; expiring or never-consumed
    units at salvage).
* Service, breaches and unmet are measured inside the window only; nothing after W is ever scored for
  service. Purchases are charged when ordered, as the ledger does; a lot ordered inside the window and
  landing after it is charged in full and its in-transit units are valued by the terminal rule.
* Runtime budget: 60 cells x 52 reviews at full-horizon solve cost, four workers; expected 30-60 minutes,
  far below the 8-hour approval line.

## 4. Stability criterion (Stage 6 "preferred property"; pre-registered)

Declared verdict endpoint W* = 52 reviews (one commercial year; 13 four-week cycles, 2.6 of the longest
EOQ cycle in the family, 4.3 planning horizons).

A fixture's result is **horizon-stable** under a terminal rule when, over the endpoints W in [40, 52]:

1. the ZAAD-versus-best-baseline delta stays within +/- 1.0 percentage point of its value at W* = 52, and
2. the PASS / FAIL verdict at the declared tolerance is identical at every W in the range.

**Boundary-sensitivity index (BSI)** of a terminal rule, used to choose between rules without reference
to ZAAD: the mean over fixtures, seeds, all ten unordered policy pairs and endpoints W in the grid of
`|delta(W+2) - delta(W)|`, where delta is the pairwise percentage cost difference. It measures how much
moving the cutoff by two reviews moves any policy-versus-policy conclusion. Lower is better.

Neither threshold is tuned after the runs.

## 5. Stage 4 classification rule (pre-registered)

Per fixture, under the declared rule, with the legacy endpoint W = 11 (rolling mode) and W* = 52:

* **A. STABLE PASS**: passes at 11 and at 52, stable per section 4, and the delta range over the grid from
  23 to 52 is at most 2 pp.
* **B. STABLE FAIL**: fails at 11 and at 52, stable, same range condition.
* **C. BOUNDARY-SENSITIVE, CONVERGES TO PASS**: verdict differs between 11 and 52 or the range over the
  grid exceeds 2 pp, and the fixture is stable per section 4 with PASS at 52.
* **D. BOUNDARY-SENSITIVE, CONVERGES TO FAIL**: as C with FAIL at 52.
* **E. NON-CONVERGENT / POLICY CYCLING**: not stable per section 4 at 52.

## 6. Method selection rule (Stage 6; pre-registered, outcome-blind)

The declared P1 evaluation is: constant rolling twelve-period planning horizon, realised ledger scored at
W* = 52 reviews, with the terminal rule chosen as follows:

1. A rule must pass the twelve benchmark validation tests of Stage 7 (`tests/unit/test_zaad_benchmark_horizon.py`).
2. Among the rules that pass, the one with the lower BSI (section 4) over the whole fixture family is
   declared.
3. If both rules pass and their BSI differ by less than 10% of the larger, the continuation rule is
   declared, because it is the only one whose value of a unit is monotone in the time to its consumption
   (test 3) and in carrying and capital (tests 5, 6); the salvage rule treats a unit consumed next week
   and one never consumed identically.

A-priori expectation, recorded so that it can be falsified: the salvage rule is expected to fail test 2
(residual consumed immediately after the cutoff is not economically lost) and the continuation rule to
pass all twelve; the continuation rule is expected to have the lower BSI. If the runs contradict this,
the rule that satisfies 1-3 is declared regardless.

No policy-specific terminal rule, no fixture-specific horizon, no C- or I-specific treatment. The rule
applies identically to ZAAD and to the four baselines.

## 7. Validity at the declared endpoint

A fixture is valid at W* only if all five policies complete W* reviews (the existing
`all_policies_completed` check). A fixture whose declared inputs cannot carry any policy to W* (expected
for S, section 2) is **proven invalid at the declared benchmark**, reported as such beside N and R, keeps
its legacy verdict as a legacy record, and is additionally shown as a diagnostic curve to the last endpoint
at which all five policies are complete. That diagnostic is not a verdict and is not used for the freeze
gate.

## 8. Options A-E of Stage 5 and how each is assessed here

* A fixed window + salvage: the legacy record, plus the rolling-mode curve under rule A.
* B continuation: rule B on the same curve; approximation error measured against the actual extension
  (the continuation value of the residual at W compared with what the realised ledger later shows over
  the next lot cycle, tested on C in `test_zaad_terminal` test 7 and on the curves here).
* C extended realised evaluation: the endpoint grid itself, with every policy continuing to decide on the
  same constant horizon (no policy frozen while another operates).
* D warm-up + scored window + settled tail: assessed with a start-offset diagnostic on the same curves:
  the window [s, 52] for s in {0, 4, 8}, opening stock at s valued by the same rule as the terminal stock
  (symmetric endpoint handling). Not implemented as a benchmark unless it is more stable than C+B.
* E lot-cycle normalisation: the per-week average cost of the curve, and the endpoint at each policy's
  cycle minimum, reported as a diagnostic only, because a policy-specific endpoint is not a common benchmark.

## Correction 1 (2026-09-09, before any extended-window ZAAD result was read)

Found by Stage 7 test 8 (complete lot cycle: finite window and extended evaluation converge) on a
baseline-only pair, fixture I, EOQ policy, 40 rolling reviews, no ZAAD cell involved. Between two
endpoints with the same physical state the salvage and continuation window costs agree to 0.1% (the
terminal credits cancel), but the window's cost per unit of demand is 3.3% below the 40-review
continuation value. Cause: rule B as pre-registered credits a residual unit at the bare unit price
(`asset_value`, $5 on I), while the purchase that unit avoids costs the policy its landed price: on I a
full load adds $1,100 freight and $150 order cost to 450 units ($2.78 per unit, 56% of the price). An
endpoint that falls just after a load therefore charges that load's freight and ordering with no
offsetting credit. That is the salvage artifact in a milder form and it is absent on fixtures without
freight or order costs (C), which is why it did not show in the pass-I C diagnostics.

Correction: a third candidate rule, **B' continuation at landed cost**: each SKU's avoided purchase is
its unit price plus the freight, ordering and receiving cost per unit that the policy itself incurred
over the window (its own ledger to W divided by the units it bought; zero when it bought nothing);
carrying and cost of capital until consumption stay on the asset value, as the ledger charges them;
salvage floor, unit cap (at the landed price), expiry and zero-demand impairment unchanged. The same
formula applies to every policy; its inputs are the policy's own ledger, exactly as the residual units
are. `zaad/full/terminal.py` gains an optional `landed` argument (default: the unit price, bit-identical
to before; its nine tests unchanged); `zaad/full/evaluation.py` reports `continuation_landed` beside
`continuation` at every endpoint.

Consequences for the pre-registration: section 6 now selects among three rules (A, B, B') by the same
rule (tests, then BSI, then the monotone rule on a tie among the continuation forms). Test 8 asserts
the property on B' and records that B fails it on I. The first run of the benchmark (started 11:01,
no cell completed) was stopped and restarted at 11:21 with all three rules scored on identical
trajectories; no ZAAD extended-window number had been produced or read.

(Time correction to the paragraph above, appended rather than edited: the first run started at 11:01
and the restart was at 11:08 local time.)
