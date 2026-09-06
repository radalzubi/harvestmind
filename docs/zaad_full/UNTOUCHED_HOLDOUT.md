# Untouched holdout: does the service-reliability profile generalize?

Branch `claude/zaad-holdout3`, stacked on `claude/zaad-false-protection` (PR 31) → PR 30 →
PR 25 → PR 24 → PR 23. Nothing is merged. Nothing in the engine, gates or parameters was
changed after the freeze record below was committed, and nothing was changed after the
first holdout row landed. Adverse results are reported as they are.

## 1. Freeze record

| Item | Value |
|---|---|
| Engine commit | `a104117916036ce6c79608782e146a7f92e91292` (docs-only commit `8579c40` adds the manifest; engine source identical) |
| Source hash (every `zaad/full/*.py` plus the runner) | `e36930db23731f95abb4a45c87c080ac9ba7608ffdf85a3a6bda5ff7876b2b1f` |
| Pre-registered manifest | `docs/zaad_full/evidence/holdout3/preregistered.json`, written by `--freeze` before the run; the runner refuses `--split holdout3` unless the live source hash and configuration match it exactly and no filter or limit is applied |
| Freeze record | `docs/zaad_full/evidence/holdout3/FROZEN.json` |
| Split | `holdout3`, seeds **28001, 28002** |
| Matrix | `reliability`, 56 cells (one-factor-at-a-time around a balanced centre plus 30 seeded random grid points over inventory × demand × supply × network × alternatives × service target) |
| Methods | `base_stock` (competent projected base-stock incumbent), `stochastic`, `robust` (per-world service on fitted plus stress worlds), `protected` (CVaR on fitted worlds), `gated_pr24` (frozen PR 23/24 gated planner), `gated_pr30` (PR 30 reliability profile, `protection_decay=False`), `gated` (PR 31 decay profile) |
| Request defaults | `engine_profile=reliability`, `protection_decay=True`, `service_risk_level=.5`, `stress_weight=.2`, `scenarios=3`, `horizon=12`, `max_solve_seconds=5`, `downside_cost_tolerance=.05`, `service_tolerance=.01`, one declared stress (`operator_adverse`: fill .7, +28 days, shared, 9 periods) |
| Rows | 56 cells × 2 seeds × 7 methods = 784 replays of 12 reviews each |

## 2. Proof the holdout was untouched

- `holdout3` was added to `SEEDS` on the PR 25 branch on 2026-09-06 with the note "stays
  frozen until a profile is promoted"; no run ever selected it before this one.
- A JSON-aware scan of every `*.jsonl` and `*.json` under `docs/` found **no row with seed
  28001 or 28002** before this run (`FROZEN.json`, field
  `prior_evidence_rows_with_holdout_seeds: []`). Substring matches of "28001"/"28002" in
  earlier files are digits inside cost values, not seeds.
- PR 30 development and validation used seeds 26001 and 27001/27002; the false-protection
  cycle used the same seeds; the credibility floor, dead band, regime rule and activity
  rule were chosen on 26001 and confirmed on 27001/27002 only. The surge study used its own
  seed ranges (300–339, 400–439). The frozen PR 23 evidence used 14001, 15001/15002 and
  22001–22005; the adaptation study used 23001, 24001/24002 (25001/25002 unrun).
- The holdout seeds also drive the truth generator (`seed + 410000`) and the history
  generator (`seed + 210000`), so demand history, realized demand, fills and lead times
  are all unseen.

## 3. Results (784 replays; `docs/zaad_full/evidence/holdout3/holdout3.jsonl`, summary `holdout3.holdout_summary.json`)

All 784 replays ran. 778 completed; 6 `robust` replays hit the 5-second solver time limit
(cells 22, 34, 37, 40, 50; substitution/transfer with intermittent or volatile demand) and
are counted as incomplete, never as zero cost. No physical or settlement failure occurred.

### 3.1 Service

| Method | Complete | Breaches | Avoidable | Unavoidable | Model failure | Median service [min, max] | Mean priority-weighted shortfall | Median stockout periods |
|---|---|---|---|---|---|---|---|---|
| base_stock (incumbent) | 112 | 74 | 34 | 6 | 33 | .896 [.21, 1.00] | .123 | 3 |
| stochastic | 112 | 67 | 27 | 6 | 33 | .915 [.29, 1.00] | .092 | 3 |
| robust | 106 | 41 | 3 | 6 | 32 | .980 [.41, 1.00] | .056 | 1 |
| protected (CVaR, fitted) | 112 | 78 | 38 | 6 | 33 | .913 [.26, 1.00] | .091 | 3 |
| gated_pr24 (frozen) | 112 | 73 | 33 | 6 | 33 | .904 [.30, 1.00] | .113 | 2 |
| gated_pr30 | 112 | 66 | 27 | 6 | 33 | .921 [.41, 1.00] | .100 | 2 |
| gated (PR 31 decay) | 112 | 69 | 30 | 6 | 33 | .916 [.41, 1.00] | .103 | 2 |

"Avoidable" is relative to the seven-method peer set on the same cell and seed: a breach is
avoidable when another method met the target within the 5% downside tolerance. With
`robust` in the set most breaches have such a peer, so the avoidable counts are higher than
in the four-method validation runs; the ordering between methods is what carries meaning.
OTIF, line fill and order fill are not measured here: the reliability matrix has one
unit-fill service per cell (order-level metrics are covered by unit tests, not replay).
Worst-case stress service is a planner-report quantity and is not observable in a
single-truth replay.

### 3.2 Inventory and working capital

| Method | Inventory, median periods [min, max] | Quiet-cell inventory (26 benign replays) | Quiet-cell excess vs incumbent | Disruption-cell inventory | Working capital (median) | Holding cost (median) |
|---|---|---|---|---|---|---|
| base_stock | 1.51 [.11, 10.6] | .41 | 0 | 2.86 | 138 | 13.7 |
| stochastic | 1.28 [.08, 8.4] | .55 | +.06 | 1.94 | 132 | 12.3 |
| robust | 2.62 [.32, 12.4] | 2.89 | +2.00 | 2.43 | 264 | 23.0 |
| protected | 1.23 [.19, 7.8] | .35 | -.07 | 1.93 | 118 | 11.8 |
| gated_pr24 | 1.45 [.11, 10.5] | .42 | 0 | 2.02 | 133 | 12.9 |
| gated_pr30 | 1.85 [.19, 10.4] | .72 | +.07 | 2.61 | 174 | 15.5 |
| gated (decay) | 1.88 [.17, 9.8] | .68 | +.04 | 2.40 | 174 | 14.4 |

Recovery time (first stockout to full service) is 1 period in median for every gated
profile and 2 for robust and stochastic; the 12-review horizon does not allow a measured
return to lean after a disruption, so "time to return to lean" is the planner's
`periods_to_lean` diagnostic, not a replay observation.

### 3.3 Economics

| Method | Median saving vs incumbent | Cost losses vs incumbent | Median shortage cost | Median action cost | Median regret vs best method on the cell [max] |
|---|---|---|---|---|---|
| base_stock | 0 | 0 | 308 | 0 | 10.3% [56%] |
| stochastic | +3.04% | 24 | 255 | 2.5 | 2.5% [34%] |
| robust | +6.77% | 32 | 63 | 0 | 2.4% [36%] |
| protected | +4.12% | 40 | 217 | 2.3 | 4.0% [37%] |
| gated_pr24 | +1.72% | 7 | 269 | 0 | 5.0% [45%] |
| gated_pr30 | +2.00% | 24 | 237 | .3 | 5.0% [40%] |
| gated (decay) | +2.08% | 26 | 241 | 0 | 4.6% [40%] |

Paired on the same cell and seed:

| Pair | Cost wins / losses | Service wins / losses | Inventory lower / higher |
|---|---|---|---|
| gated_pr30 vs gated_pr24 | 49 / 52 | **53 / 25** | 20 / **81** |
| gated (decay) vs gated_pr24 | 46 / 55 | 44 / 34 | 22 / 79 |
| gated (decay) vs gated_pr30 | 42 / 59 | 20 / **50** | **72** / 29 |
| gated (decay) vs base_stock | 75 / 26 | 51 / 32 | 35 / 66 |
| gated (decay) vs robust | 38 / 68 | 19 / 64 | 68 / 38 |
| robust vs stochastic | 54 / 52 | 84 / 9 | 17 / 89 |
| protected vs stochastic | 46 / 66 | 37 / 61 | 71 / 41 |

### 3.4 Regime breakdowns (median inventory in periods, breaches / runs, median service)

| Demand | gated_pr24 | gated_pr30 | gated (decay) | robust |
|---|---|---|---|---|
| stable | .41, 14/38, .970 | .72, 12/38, .978 | .68, 16/38, .963 | 2.62, 5/35, 1.000 |
| increase (structural up) | 1.03, 10/10, .896 | .69, 10/10, .909 | .69, 10/10, .904 | .80, 7/10, .888 |
| decrease (structural down) | 1.73, 5/8, .945 | 2.69, 5/8, .945 | 2.22, 5/8, .945 | 4.54, 4/8, .973 |
| promotion (declared) | 1.18, 8/8, .824 | 1.59, 6/8, .812 | 1.70, 5/8, .806 | 2.71, 2/8, 1.000 |
| unknown promotion | 3.67, 4/6, .883 | 3.86, 4/6, .899 | 3.49, 4/6, .890 | 2.48, 2/6, .983 |
| intermittent | 5.02, 8/12, .840 | 4.68, 8/12, .871 | 4.70, 8/12, .842 | 4.51, 6/11, .908 |
| one-week spike | 2.69, 8/8, .844 | 3.95, 7/8, .857 | 4.18, 7/8, .856 | 2.25, 6/8, .861 |
| temporary spike | .98, 4/4, .793 | 1.48, 4/4, .818 | 1.46, 4/4, .810 | 1.82, 2/4, .930 |
| gradual | 1.88, 7/8, .801 | 1.72, 6/8, .820 | 1.69, 6/8, .812 | 1.51, 5/7, .894 |
| volatile | 4.22, 5/10, .950 | 4.02, 4/10, .937 | 3.93, 4/10, .949 | 2.84, 2/9, .951 |

| Supply | gated_pr24 | gated_pr30 | gated (decay) | robust |
|---|---|---|---|---|
| stable | .94, 24/52, .970 | 1.25, 21/52, .966 | 1.18, 24/52, .954 | 2.84, 4/48, 1.000 |
| variable fill | 1.70, 2/8, .948 | 2.18, 2/8, .975 | 2.12, 2/8, .968 | 4.03, 1/8, .990 |
| late supplier | 2.36, 14/16, .776 | 3.01, 12/16, .853 | 2.99, 12/16, .855 | 2.40, 10/16, .911 |
| partial delivery | 1.55, 10/10, .866 | 2.63, 9/10, .904 | 1.97, 9/10, .893 | 2.46, 8/10, .900 |
| severe delay | 1.57, 12/12, .853 | 1.76, 12/12, .870 | 2.09, 12/12, .872 | 2.54, 9/12, .902 |
| correlated route failure | 2.92, 11/14, .707 | 3.85, 10/14, .711 | 3.45, 10/14, .704 | 1.72, 9/12, .788 |

| Alternatives | gated_pr24 | gated_pr30 | gated (decay) | robust |
|---|---|---|---|---|
| none | .64, 31/52, .919 | 1.11, 26/52, .934 | 1.02, 29/52, .927 | 2.87, 6/52, 1.000 |
| alternate supplier | 1.14, 14/16, .907 | 1.60, 14/16, .926 | 1.62, 13/16, .909 | .98, 9/16, .907 |
| alternate route | 2.51, 15/20, .854 | 3.41, 13/20, .883 | 3.22, 13/20, .877 | 2.15, 15/19, .855 |
| transfer | 3.83, 9/12, .765 | 4.08, 9/12, .854 | 4.04, 10/12, .825 | 4.10, 8/11, .925 |
| substitution | 3.92, 4/12, 1.000 | 5.35, 4/12, 1.000 | 5.29, 4/12, 1.000 | 3.30, 3/8, .977 |

| Target | gated_pr24 | gated_pr30 | gated (decay) | robust |
|---|---|---|---|---|
| 90% | 3.54, 8/20, .933 | 4.27, 5/20, .934 | 3.93, 5/20, .929 | 3.10, 5/18, .937 |
| 95% | .88, 32/56, .925 | 1.21, 28/56, .949 | 1.17, 31/56, .938 | 2.71, 11/53, 1.000 |
| 97% | 2.24, 14/16, .794 | 3.01, 15/16, .855 | 3.00, 15/16, .831 | 1.86, 13/15, .853 |
| 99% | 1.50, 19/20, .862 | 1.89, 18/20, .897 | 1.88, 18/20, .893 | 2.52, 12/20, .950 |

Network: central DC plus branches is the hardest structure for every gated profile
(19–20 of 22 breaches, median service .76–.79; robust 12 of 20 at .907).

### 3.5 Worst cells (decay profile)

Service: cell 14 severe delay, no alternative (.41 and .48 on the two seeds, model
failure); cell 51 gradual growth with a late supplier at 99% (.51, model failure); cell 16
correlated route failure (.49, model failure); cell 18 central-plus-branches with stable
demand and supply (.49, **avoidable**: base stock reaches .95 there).
Inventory: intermittent demand with a transfer or substitute (7 to 9.8 periods of demand at
75 to 100% service) and a post-decrease cell with a substitute (9.8 periods at 100%).

### 3.6 Selector regimes (per review, 1,344 reviews per gated method)

| Method | PENDING_REVIEW | RETAIN_INCUMBENT | LEAN | PROTECT | ALLOCATE (recovery) |
|---|---|---|---|---|---|
| gated_pr24 | 310 | 1,034 | 1,105 | 0 | 239 |
| gated_pr30 | 616 | 728 | 552 | 597 | 195 |
| gated (decay) | 621 | 723 | 786 | 351 | 207 |

The decay profile marks 30% fewer reviews as PROTECT than PR 30 (351 against 597) and the
same share as ALLOCATE (recovery when the targets are jointly infeasible). The frozen
PR 24 planner retains the incumbent in 77% of reviews; both reliability profiles intervene
in 46%. Whether each intervention was "right" cannot be judged per review from a single
realized truth; the outcome measures above are the test.

## 4. Answers to the key questions

1. **Did the service-reliability improvement survive unseen data?** Yes, modestly, for the
   PR 30 profile: 66 breaches against 73 frozen, avoidable 27 against 33, median service
   .921 against .904, paired service wins 53 / losses 25, weighted shortfall .100 against
   .113. The magnitude matches validation (69 vs 74 there). The decay profile keeps part of
   it: 69 breaches, 44 / 34 paired service wins.
2. **Did the false-protection reduction survive?** No. On validation the decay profile was
   4% leaner overall and 14% leaner on quiet cells than PR 30; on the holdout its median
   inventory is 1.88 against PR 30's 1.85 (higher), quiet-cell inventory .68 against .72
   (5% lower), and it is leaner in 72 of 101 paired cells by small margins while losing
   service in 50 of 70 decided pairs. The reduction did not generalize.
3. **Did inventory fall materially versus PR 30 without recreating avoidable failures?** No
   on both counts: inventory did not fall in median, and avoidable breaches rose from 27 to
   30 (breaches 66 to 69).
4. **Are quiet cells actually leaner?** Marginally against PR 30 (.68 vs .72); still 64%
   above the frozen planner (.42) and the incumbent (.41).
5. **Are high-risk cells still protected?** Yes. Late supplier: 12 of 16 breaches at .855
   service against 14 of 16 at .776 frozen; partial delivery .893 against .866; severe
   .872 against .853; correlated route .704 against .707 with one fewer breach. Both
   reliability profiles hold more stock there (2.4 to 2.6 periods against 2.0).
6. **Does protection unwind during recovery?** Not measurable in this replay: the horizon
   ends before the supply driver's window (six clean receipts) can retire, and median
   recovery time is one period for all gated profiles. The `periods_to_lean` diagnostic
   exists in every report but no replay observation confirms it here. This is an open
   measurement gap, not evidence either way.
7. **New failure families?** Two visible only at holdout scale: (a) intermittent demand
   combined with a transfer or substitute alternative drives every gated profile to 7 to 10
   periods of inventory (the substitute or central stock is counted as cover and the
   intermittent history is bootstrapped with zeros and doubles); (b) the central-plus-branch
   network with stable demand and supply is an avoidable miss for both reliability profiles
   (cell 18: .49 service where base stock reaches .95). Persistent: model failures (33 of
   112 per method) on spikes, unknown promotions, severe and correlated outages; 97% and
   99% targets missed 15 to 18 of 16 to 20 times by every profile except robust.
8. **Does robust/stress planning still help under misspecification?** Yes, strongly, and
   at a price: 41 breaches, .980 median service, 84 / 9 paired service wins over stochastic,
   shortage cost 63 against 255, but 2.62 periods of inventory (2.89 on quiet cells, seven
   times the incumbent), 32 cost losses against the incumbent and 6 unsolved replays at the
   5-second limit. Robust is the service ceiling here and the false-protection floor.
9. **Does the gated selector choose the right regime?** It chooses recovery (ALLOCATE) in
   15% of reviews and strict gating elsewhere; it intervenes in 46% of reviews and its
   interventions win 75 / 26 on cost and 51 / 32 on service against the incumbent, with
   26 paired cost losses. Retaining the incumbent when intervention adds no value is not
   separately observable; the 723 retained reviews include both correct restraint and the
   cell-18 avoidable miss.

## 5. Failure families (retained, not fixed here)

| Family | Evidence | Class |
|---|---|---|
| Demand surprises no history announces | 33 model-failure breaches per method: one-week spike, unknown promotion, volatile | MODEL_FAILURE |
| Severe and correlated supply outages with no alternative | cells 14, 16: service .41 to .49, every method | MODEL_FAILURE / UNAVOIDABLE |
| Central DC plus branches, calm conditions | cell 18: .49 for both reliability profiles, .95 for base stock | AVOIDABLE (selector/proxy) |
| Intermittent demand with transfer or substitute alternative | 7 to 10 periods of inventory, every gated profile | false protection, new |
| High targets (97%, 99%) with a 12-period horizon and 3 scenarios | 15 to 18 of 16 to 20 breached by all but robust | capacity of the scenario set |
| Robust solve time | 6 of 112 replays at the 5-second limit | tractability |

## 6. Commercial interpretation

The reliability profile (PR 30) is a real but modest service gain that costs about 28% more
inventory than the frozen planner and 22% more than the incumbent; the false-protection
cycle (PR 31) did not remove that cost on unseen data. Robust planning buys almost all the
service that is buyable on this matrix, at almost twice the inventory. Neither is a
commercial default yet: a buyer would see better service on late and partial suppliers and
more stock on quiet SKUs, with the intermittent-plus-alternative and central-network cells
as visible embarrassments. The right next cycle is not another buffer rule: it is the
calibration mismatch between history and truth, the intermittent-demand bootstrap, and
proxy protection placement in central networks, with a fresh untouched holdout.

## 7. Verdict

**HOLDOUT FAILED — NEW DEVELOPMENT CYCLE REQUIRED.**

The service improvement generalized; the removal of unnecessary protection did not. Nothing
was changed after these results and nothing will be tuned on this branch.

