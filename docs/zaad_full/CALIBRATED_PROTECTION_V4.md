# Calibrated protection v4

Branch `claude/zaad-calibrated-protection-v4`, stacked on `claude/zaad-holdout3` (PR 32) →
PR 31 → PR 30 → PR 25 → PR 24 → PR 23. Nothing is merged. PR 30 is the service-reliability
reference (`gated_pr30`); PR 31 and PR 32 are preserved negative evidence. New seeds:
`development4` 29001, `validation4` 30001/30002, `holdout4` 31001/31002 (frozen before any
engine change: `docs/zaad_full/evidence/v4/holdout4/PHASE0_MANIFEST.json`, pre-tuning source
hash `a319e150…`, starting commit `8e5cdef`). No holdout was viewed or run during this cycle.

## 1. Why PR 31 failed

PR 31 attacked protection *width*: robust residuals, a calibration dead band, a bounded
young-regime mixture, event-only activity, a stress floor conditioned on evidence. On
validation3 it cut quiet-cell inventory 14% and overall 4%; on holdout3 the quiet-cell cut
shrank to 5% and the overall median rose. The calibration diagnostics of this cycle explain
why: on stable cells the fitted demand spread *under-covers* realized demand (80% intervals
cover 52%, realized RMSE is 1.5 times the predicted spread), so uncertainty width was not
what PR 30 was buying with. Narrowing the width further could not remove inventory that the
width had not created.

## 2. Exact causes of excess protection (development4 decompositions, `evidence/v4/diag_*.json`)

1. **Timing indifference in the network solve.** With holding at 1% of value per period and
   an aggregate service floor, the MILP is nearly indifferent to *when* it orders; with 3
   under-covering worlds it is also over-confident. Its period-zero action is therefore the
   first order of a lumpy horizon schedule (46, 0, 39, 0 …), re-drawn every review. Average
   inventory rises and service does not: on the balanced quiet cell PR 30 held .62 periods at
   .965 service against the frozen proxy's .37 at .973. No uncertainty component explained
   it: removing CVaR changed nothing, removing the stress weight made it worse.
2. **Gate evaluation failed legal plans.** Every network candidate on central-plus-branch
   cells was rejected because a *later-period* transfer, which depends on a purchase landing
   at the DC, was judged a physical violation on any confirmation or stress world where that
   receipt landed late. Only period-zero actions are executed; later ones are guidance. The
   network-blind proxy survived because it never buys. Every gated profile scored .49 on
   holdout3 cell 18 while the stochastic fallback reached .95.
3. **Strict SLA under stress even when the incumbent fails it worse.** When some plan could
   meet the SLA under the declared stress, the gate required the candidate to meet it in full
   and to stay inside a 5% cost cap under that stress, so a candidate at .95 fitted service
   and .50 stress service was rejected in favour of an incumbent at .49 and .43.
4. **A network-blind proxy.** `targets()` orders only at locations with direct sources; a
   central DC with no customers of its own bought nothing for its branches.
5. **Intermittent "7–10 period" cells were inherited stock, not bought protection.** Every
   method, including base stock, carried the same inventory there: the fixture's central
   excess and substitute stock, never moved because the retained proxy does not transfer.
   The one genuine defect was the raw standard deviation of a mostly-zero series with a
   historical spike in it (`intermittent_spiky`: predicted spread 0.72 of realized error,
   coverage .91 at nominal .80).
6. **Carrying the accepted schedule forward as the next incumbent made things worse** (.83
   periods on the quiet cell): it anchored the next review to the previous lumpy plan.
   Retained as adverse evidence; the switch exists and defaults off.

## 3. History versus realized calibration (`evidence/v4/calibration/`)

Development4, 1,024 review-level demand comparisons and 8 supply regimes:

| Demand pattern | 80% coverage | 95% coverage | realized RMSE / predicted sd |
|---|---|---|---|
| stable | .52 | .69 | 1.53 |
| volatile | .54 | .86 | 1.29 |
| intermittent | .75 | .75 | 1.32 |
| intermittent with one historical spike | .91 | .91 | 0.72 |
| promotion (declared) | .50 | .75 | 1.63 |
| one-week spike | .33 | .42 | 2.84 |
| decrease | .75 | .85 | 1.58 |
| all | .61 | .76 | 1.44 |

Supply: declared parameters understate every disruptive regime by design (late share .46
against a declared 0 on correlated cells, fill .61 against .97 on partial delivery); on
stable and variable-fill cells declared and realized agree. The calibration ratio can only
close the demand gap as realized errors arrive; it is a lagging correction, not a prior.

Conclusion: uncertainty is **too narrow**, not too wide, almost everywhere except sparse
series with a historical spike. The excess protection came from the conversion of
uncertainty into orders (timing lurches, gate rejections, a blind proxy), which is where
this cycle intervenes.

## 4. What changed

| Area | Change | Evidence |
|---|---|---|
| Model | Stability cost: 2% of landed unit cost per unit of period-to-period order change (reliability profile). Shortage at 11 per unit still dominates. | quiet cell .61 → .45 periods, service .965 → .980, cost 1360 → 1341 |
| Uncertainty | Calibration ratio = robust one-step residual scale / fitted spread, dead band 1.1, cap 2; feeds the scenario spread only | coverage improves as realized errors accumulate |
| Intermittent | Occurrence × capped positive size (median + 3 robust sd); zero runs at the observed rate; spread from the decomposition, not the raw sd | one-spike test: worlds never repeat the spike |
| Gate | Later-period transfers are guidance (truncated to available stock and recorded); period zero stays strict | central cell candidates evaluable |
| Selector | Strict SLA under stress preferred; otherwise not-worse-than-incumbent under the same stress inside a hedged cost cap; every gate carries a reason | cell 18: .49 → .99 |
| Proxy | Echelon demand: a location without a direct source is ordered upstream through its transfer arc | central cell incumbent .49 → .85–.98 |
| State machine | LEAN / PROTECT / RECOVER / ALLOCATE with hysteresis; flags FALSE_PROTECTION_RISK, INSUFFICIENT_CALIBRATION, INTERMITTENT_TAIL_RISK, DUPLICATED_NETWORK_BUFFER, RECOVERY_IN_PROGRESS | report `explain` |
| Placement | local service units (transfer lead × spread) versus pooled network units; duplicated-buffer flag | report `explain.placement` |
| Marginal value | chosen plan versus leanest feasible candidate: extra inventory, carrying cost, hedged shortage avoided, justified flag | report `protection_value` |
| Selective robustness | declared stress at twice the floor only when the source has no observed record, a long replenishment and no independent alternative; zero floor on short diversified lanes | `stress_credibility.floor` |
| Replay | per-review protection state recorded; purchased versus inherited units; per-review status, policy and mode | recovery study |

The optimizer is not redesigned: the same candidates, settlement, replay and recovery logic
run; the changes are in the uncertainty inputs, one cost term, gate semantics and the proxy.

## 5. Development4 (72 cells, seed 29001; `evidence/v4/dev4_b_engine.*`)

| | frozen PR 24 | PR 30 | **v4** |
|---|---|---|---|
| Breaches / avoidable | 41 / 6 | 36 / 1 | 37 / 2 |
| Median service | .930 | .957 | .957 |
| Mean priority-weighted shortfall | .092 | .074 | .072 |
| Inventory, median periods | 1.45 | 1.93 | 1.85 |
| Quiet-cell inventory | .37 | .61 | .55 |
| Saving vs base stock | +0.4% | +0.9% | +2.6% |

Paired v4 vs PR 30: cost 42 / 29, inventory lower in 45 of 71, service 22 / 34. The first
gates-only pass was stopped at 176 rows and is retained (`dev4_a_gates_stopped_partial.*`).
Carry-forward of the accepted schedule was tested and rejected on the quiet cell (.83 periods
against .45 without it; `diag_quiet_carry_29001.json`, `diag_quiet_smooth_29001.json`).

## 6. Validation4 (72 cells × seeds 30001/30002, 864 replays; `evidence/v4/val4.*`)

| Method | Complete | Breaches | Avoidable | Unavoidable | Model failure | Median service | Weighted shortfall | Inventory (periods) | Quiet cells | Disruption cells | Working capital | Saving vs base | Cost losses vs base |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base_stock (incumbent) | 144 | 104 | 40 | 21 | 43 | .880 | .128 | 1.25 | .50 | .99 | 129 | 0 | 0 |
| stochastic | 131 | 98 | 40 | 20 | 34 | .883 | .153 | 1.07 | .69 | 1.05 | 121 | +1.7% | 42 |
| robust | 96 | 50 | 14 | 17 | 18 | .954 | .093 | 2.79 | 2.92 | 1.34 | 280 | +3.7% | 35 |
| gated_pr24 (frozen) | 144 | 100 | 36 | 21 | 43 | .907 | .115 | 1.25 | .50 | 1.01 | 129 | +1.3% | 14 |
| gated_pr30 (reference) | 144 | 89 | 25 | 21 | 43 | .935 | .095 | 1.79 | .84 | 1.99 | 192 | +3.2% | 25 |
| **gated (v4)** | 144 | 90 | 26 | 21 | 43 | .934 | .099 | 1.81 | .70 | 2.00 | 193 | +2.7% | 23 |

Robust hit the 5-second solver limit in 48 of 144 replays (unsolved, never costed as zero);
stochastic in 13.

Paired on the same cell and seed:

| Pair | Cost wins / losses | Service wins / losses | Inventory lower / higher |
|---|---|---|---|
| v4 vs PR 30 | 71 / 71 | 49 / **70** | **85** / 57 |
| v4 vs PR 24 | **95** / 47 | **92** / 40 | 34 / 108 |
| PR 30 vs PR 24 | 101 / 41 | 95 / 35 | 32 / 110 |
| v4 vs base stock | 119 / 23 | 93 / 36 | 53 / 89 |
| v4 vs robust | 52 / 44 | 28 / 55 | 67 / 29 |

Regime breakdowns (median inventory in periods, breaches / runs, median service):

| Regime | frozen PR 24 | PR 30 | v4 |
|---|---|---|---|
| stable demand | .49, 39/64, .942 | .84, 38/64, .947 | .70, 37/64, .947 |
| structural increase | .38, 2/2, .888 | .67, 1/2, .923 | .70, 2/2, .920 |
| structural decrease | 6.59, 3/8, .998 | 6.78, 4/8, .929 | 6.82, 3/8, .962 |
| declared promotion / recovery | 1.25, 6/8, .866 / 1.80, 5/6, .906 | 1.91, 3/8, .958 / 2.17, 2/6, .975 | 1.92, 3/8, .952 / 2.11, 2/6, .977 |
| intermittent / with one spike | 4.25, 4/10, .980 / 6.05, 9/14, .875 | 3.77, 4/10, .971 / 5.76, 7/14, .907 | 4.02, 4/10, .999 / 6.30, 8/14, .903 |
| late supplier | 2.17, 7/10, .854 | 3.04, 4/10, .969 | 3.09, 4/10, .969 |
| variable fill | 4.45, 4/6, .954 | 4.94, 4/6, .943 | 4.64, 2/6, .973 |
| deterioration then recovery | 2.31, 12/12, .823 | 2.20, 10/12, .857 | 2.34, 11/12, .860 |
| route closure then restoration | 1.63, 8/10, .481 | 1.77, 10/10, .475 | 1.69, 9/10, .474 |
| correlated route | .68, 14/14, .680 | .72, 14/14, .679 | .76, 14/14, .700 |
| central + branches | 2.20, 18/20, .789 | 2.06, 19/20, .794 | 2.04, 18/20, .745 |
| transfer / constrained | 4.20, 9/16, .947 / 4.00, 8/14, .920 | 3.23, 11/16, .920 / 3.48, 9/14, .905 | 3.38, 12/16, .885 / 3.16, 8/14, .941 |
| target 99% | 3.55, 17/18, .907 | 3.22, 14/18, .955 | 2.96, 14/18, .942 |

Inventory in "periods of demand" on decrease and one-spike intermittent cells is a
denominator effect (realized demand of 6–7 per period against a forecast of 19–20); every
method including base stock shows it, and v4 bought fewer units than the frozen planner on
those cells (`purchased_units` in the rows).

### Recovery (40 long-horizon replays per method, from per-review protection trajectories)

| | frozen PR 24 | PR 30 | v4 |
|---|---|---|---|
| Reviews in PROTECT (median of 20) | 20 (no states) | 20 | 13 |
| Protection reduced 20% after the peak, median reviews | 2 | 2 | 2 |
| Returned to LEAN after the peak | 0 of 40 | 0 of 40 | 12 of 40 |
| Excess on hand over lean baseline at the end, median units | 18.3 | 18.8 | 15.7 |

The state machine now produces an observable unwind in 30% of long-horizon replays; the
other 70% end the 20 reviews in PROTECT or RECOVER, mostly on the closure, deterioration and
surge cells where the risk driver is still inside its evidence window at the end.

### Selector regimes (2,048 reviews per method)

| | PENDING_REVIEW | RETAIN | LEAN | PROTECT | ALLOCATE |
|---|---|---|---|---|---|
| frozen PR 24 | 386 | 1,662 | 1,714 | 0 | 334 |
| PR 30 | 1,211 | 837 | 689 | 1,023 | 336 |
| v4 | 1,150 | 898 | 1,057 | 652 | 339 |

## 7. Remaining failures (retained, not fixed here)

| Family | Evidence | Class |
|---|---|---|
| Central DC plus branches | 18 of 20 breaches for every gated profile at .75–.79; the echelon proxy lifted the demo incumbent from .49 to .85 but the validation cells still miss | AVOIDABLE / placement |
| Route closure then restoration | .47 service for every method; alternates are used but the closure is 5 periods with no early signal | MODEL_FAILURE |
| Correlated route and severe outages | 14 of 14 and 6 of 6 breaches, all methods | UNAVOIDABLE / MODEL_FAILURE |
| Intermittent with one historical spike | 8 of 14 breaches at .90; the spike no longer repeats in scenarios but a sparse SKU with one event per quarter cannot be served at 97% from a 20-unit mean | structural |
| Quiet-cell inventory | .70 against a .42–.55 target and .50 for the incumbent | false protection, reduced not removed |
| Robust tractability | 48 of 144 replays unsolved at 5 seconds | tractability |
| Transfer cells | v4 .885 service against .947 frozen on transfer-alternative cells (12/16 breaches) | regression on this regime |

## 8. Answers

**A. SERVICE.** Yes, at PR 30 level: 90 breaches against 89, 26 avoidable against 25,
median service .934 against .935, and a large margin over the frozen planner (92 / 40
paired service wins). Paired against PR 30 itself the v4 profile loses more cells than it
wins (49 / 70), so "parity" is the honest word, not "better".

**B. INVENTORY.** Quiet-state inventory fell 16% against PR 30 (.70 against .84) but not to
the .42–.55 target; overall inventory did not fall (1.81 against 1.79), although v4 holds
less in 85 of 142 paired cells. Not material.

**C. INTERMITTENT.** The 7–10 period cells were inherited stock and a denominator effect,
not bought protection; v4 buys fewer units than the frozen planner on them and the single
historical spike no longer populates the scenarios. The measurement pathology is explained;
service on sparse SKUs with one spike is unchanged (8 of 14 breaches).

**D. NETWORK.** The proxy is no longer network-blind and the gate no longer fails plans for
later-period transfers (holdout3 cell 18 pattern: .49 → .99 on the same data). On the
validation central-plus-branch cells the profile still breaches 18 of 20 at .745, no better
than PR 24; placement is reported but not yet solved.

**E. RECOVERY.** Partly: protection now demonstrably unwinds in 12 of 40 long-horizon
replays with a median 2 reviews to the first 20% reduction and less excess at the end than
either reference; 28 of 40 still end in PROTECT or RECOVER within 20 reviews.

**F. ROBUSTNESS.** Yes: late-supplier, partial-delivery and variable-fill cells keep PR 30's
protection and service (.969, .942, .973 against .854, .898, .954 frozen), and robust
planning remains the service ceiling (.954) at 2.79 periods with a third of its replays
unsolved.

**G. NEXT STEP: NEEDS FURTHER CALIBRATION ENGINEERING.**

Holdout4 (31001, 31002) remains frozen and unrun. The next cycle should start from three
findings this one established: uncertainty is too narrow rather than too wide, so the
remaining excess is in conversion (the smoothing term removed part of it); the
central-plus-branch and transfer regimes need placement logic inside the solve rather than in
the proxy; and quiet-cell inventory is still .20 periods above the incumbent for no service
gain on those cells, which is where the marginal-value gate should be made binding rather
than diagnostic.

