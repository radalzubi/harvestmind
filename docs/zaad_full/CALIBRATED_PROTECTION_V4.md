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

RESULTS_PLACEHOLDER
